import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from unittest.mock import patch

from src.ball_tracking.annotations import SourceVideo
from src.ball_tracking.detections import BallDetection, BallDetectionRun
from src.ball_tracking.detector_experiments import (
    EXPECTED_DETECTOR_SETTINGS,
    DetectorSpecification,
    ExperimentWindow,
    build_model_provenance,
)
from src.ball_tracking.run_detector_experiment import (
    DetectorExperimentIncompleteError,
    DetectorExperimentRunnerError,
    GitSnapshot,
    RunnerDependencies,
    _initial_run,
    _replace_frame,
    _reject_symlink_components,
    atomic_write_detection_run,
    inspect_cuda_runtime_device,
    parse_args,
    preflight_detector_experiment,
    run_detector_experiment,
)


HEAD = "a" * 40
RUNTIME_DEVICE = (
    "cuda:0 | gpu=Synthetic GPU; torch=2.7.1+cu128; "
    "cuda_runtime=12.8; cudnn=90701"
)


class FakeExperiment:
    def __init__(self, detector, ready_windows, all_windows=None):
        self.detector = detector
        self._ready_windows = tuple(ready_windows)
        self.windows_for_inference_calls = 0
        self.windows = tuple(
            ready_windows if all_windows is None else all_windows
        )

    def windows_for_inference(self):
        self.windows_for_inference_calls += 1
        return self._ready_windows


class FakeCapture:
    def __init__(self, *, fail_at=None, opened=True, raise_at=None):
        self.fail_at = fail_at
        self.opened = opened
        self.raise_at = raise_at
        self.read_calls = 0
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        frame_index = self.read_calls
        self.read_calls += 1

        if self.raise_at == frame_index:
            raise RuntimeError(f"decode explosion {frame_index}")

        if self.fail_at == frame_index:
            return False, None

        return True, ("bgr", frame_index)

    def release(self):
        self.released = True


class FakeAdapter:
    def __init__(self, behaviors=None):
        self.behaviors = {} if behaviors is None else dict(behaviors)
        self.calls = []

    def predict_frame(self, frame_rgb):
        self.calls.append(frame_rgb)
        frame_index = frame_rgb[1]
        behavior = self.behaviors.get(frame_index)

        if isinstance(behavior, BaseException):
            raise behavior

        if behavior is not None:
            return behavior

        return (
            BallDetection(
                candidate_index=0,
                class_id=37,
                class_name="sports ball",
                confidence=0.5,
                bbox_xyxy_px=(1.0, 1.0, 3.0, 3.0),
                center_xy_px=(2.0, 2.0),
            ),
        )


class RecordingWriter:
    def __init__(self):
        self.calls = []

    def __call__(self, run, output_path):
        snapshot = BallDetectionRun.from_mapping(run.to_dict())
        self.calls.append((snapshot, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(snapshot.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )


def make_context(root, *, start=2, end=26):
    root = root.resolve()
    manifest_path = (
        root
        / "configs"
        / "ball_tracking"
        / "experiments"
        / "ball_detector_experiment_v0_1.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}\n", encoding="utf-8")
    manifest_relative = PurePosixPath(
        manifest_path.relative_to(root).as_posix()
    )
    detector = DetectorSpecification.from_mapping(
        dict(EXPECTED_DETECTOR_SETTINGS)
    )
    source_video = SourceVideo.from_mapping(
        {
            "path": "data/clips/synthetic.mp4",
            "sha256": "b" * 64,
            "width_px": 100,
            "height_px": 90,
            "fps": 25.0,
            "frame_count": 60,
        }
    )
    window = ExperimentWindow(
        window_id="synthetic_pilot",
        annotation_set_id="synthetic_pilot_annotations_v0_1",
        detection_run_id="synthetic_pilot_rfdetr_v0_1",
        possession_id="synthetic_possession",
        source_video=source_video,
        start_frame_index=start,
        end_frame_index=end,
        selection_purpose="protocol_adjudication",
        execution_status="ready_for_inference",
        selection_rationale="Synthetic prediction-blind test window.",
        output_path=PurePosixPath(
            "data/outputs/ball_tracking/detections/test/run.json"
        ),
    )
    experiment = FakeExperiment(detector, [window])
    weights_path = root / "weights" / detector.weights_identifier
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    weights_path.write_bytes(b"synthetic weights")
    capture = FakeCapture()
    adapter = FakeAdapter()
    writer = RecordingWriter()
    state = SimpleNamespace(
        root=root,
        manifest_path=manifest_path,
        manifest_relative=manifest_relative,
        detector=detector,
        source_video=source_video,
        window=window,
        experiment=experiment,
        weights_path=weights_path,
        capture=capture,
        adapter=adapter,
        writer=writer,
        source_calls=[],
        runtime_calls=[],
        ignore_calls=[],
        adapter_factory_calls=[],
        capture_calls=[],
    )

    def verify_source(source, repository_root):
        state.source_calls.append((source, repository_root))
        return {"status": "verified_source_video"}

    def ignored(repository_root, relative_path):
        state.ignore_calls.append((repository_root, relative_path))
        return True

    def inspect_runtime_device():
        state.runtime_calls.append(True)
        return RUNTIME_DEVICE

    def create_adapter(weights_path, export_floor):
        state.adapter_factory_calls.append((weights_path, export_floor))
        return state.adapter

    def open_capture(source_path):
        state.capture_calls.append(source_path)
        return state.capture

    def load_run(path):
        return BallDetectionRun.from_mapping(
            json.loads(path.read_text(encoding="utf-8"))
        )

    dependencies = RunnerDependencies(
        load_experiment=lambda path: state.experiment,
        inspect_git=lambda repository_root, relative_manifest: GitSnapshot(
            repository_root=root,
            head=HEAD,
            clean=True,
            manifest_tracked=True,
            tracked_experiment_manifests=(state.manifest_relative,),
        ),
        read_package_version=lambda package_name: detector.package_version,
        inspect_runtime_device=inspect_runtime_device,
        resolve_weights_path=lambda specification: state.weights_path,
        hash_file=lambda path: detector.weights_sha256,
        verify_source=verify_source,
        is_git_ignored=ignored,
        load_run=load_run,
        build_provenance=build_model_provenance,
        create_adapter=create_adapter,
        open_capture=open_capture,
        bgr_to_rgb=lambda frame: ("rgb", frame[1]),
        write_run=writer,
    )
    state.dependencies = dependencies
    return state


def make_existing_output(state, run):
    output_path = state.root.joinpath(*state.window.output_path.parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(run.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def expected_provenance(state):
    return build_model_provenance(
        state.detector,
        code_commit=HEAD,
        runtime_device=RUNTIME_DEVICE,
    )


def complete_run(state):
    run = _initial_run(state.window, expected_provenance(state))

    for frame_index in range(
        state.window.start_frame_index,
        state.window.end_frame_index + 1,
    ):
        run = _replace_frame(
            run,
            frame_index,
            inference_status="completed",
            failure_reason=None,
            detections=(),
        )

    return run


class CliContractTests(unittest.TestCase):
    def test_cli_exposes_only_experiment_root_and_dry_run(self):
        args = parse_args(
            [
                "--experiment",
                "configs/experiment.json",
                "--repository-root",
                ".",
                "--dry-run",
            ]
        )
        self.assertEqual(args.experiment, Path("configs/experiment.json"))
        self.assertEqual(args.repository_root, Path("."))
        self.assertTrue(args.dry_run)

        forbidden_arguments = (
            ["--threshold", "0.5"],
            ["--class-id", "32"],
            ["--start-frame", "10"],
            ["--dry"],
        )

        for extra in forbidden_arguments:
            with self.subTest(extra=extra):
                with self.assertRaises(SystemExit):
                    parse_args(
                        [
                            "--experiment",
                            "configs/experiment.json",
                            "--repository-root",
                            ".",
                            *extra,
                        ]
                    )


class RuntimeInspectionTests(unittest.TestCase):
    def test_cuda_inspector_persists_exact_observed_runtime_format(self):
        fake_torch = SimpleNamespace(
            __version__="2.7.1+cu128",
            version=SimpleNamespace(cuda="12.8"),
            cuda=SimpleNamespace(
                is_available=lambda: True,
                current_device=lambda: 2,
                get_device_name=lambda index: f"Synthetic GPU {index}",
            ),
            backends=SimpleNamespace(
                cudnn=SimpleNamespace(version=lambda: 90701),
            ),
        )

        with patch.dict(sys.modules, {"torch": fake_torch}):
            observed = inspect_cuda_runtime_device()

        self.assertEqual(
            observed,
            "cuda:2 | gpu=Synthetic GPU 2; torch=2.7.1+cu128; "
            "cuda_runtime=12.8; cudnn=90701",
        )

    def test_cuda_inspector_refuses_unavailable_cuda(self):
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: False),
        )

        with patch.dict(sys.modules, {"torch": fake_torch}):
            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "CUDA must be available",
            ):
                inspect_cuda_runtime_device()


class PreflightTests(unittest.TestCase):
    def test_dry_run_is_read_only_and_uses_only_authorized_windows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            embargoed = replace(
                state.window,
                window_id="embargoed_holdout",
                annotation_set_id="embargoed_annotations",
                detection_run_id="embargoed_run",
                selection_purpose="test_holdout",
                execution_status="annotation_pending_prediction_embargo",
                output_path=PurePosixPath("../../must_not_be_touched.json"),
            )
            state.experiment = FakeExperiment(
                state.detector,
                [state.window],
                [state.window, embargoed],
            )

            summary = run_detector_experiment(
                state.manifest_path,
                root,
                dry_run=True,
                dependencies=state.dependencies,
            )

            self.assertTrue(summary.dry_run)
            self.assertEqual(summary.window_count, 1)
            self.assertEqual(
                state.experiment.windows_for_inference_calls,
                1,
            )
            self.assertEqual(summary.completed_frame_count, 0)
            self.assertEqual(summary.incomplete_frame_count, 25)
            self.assertEqual(len(state.source_calls), 1)
            self.assertEqual(state.runtime_calls, [True])
            self.assertEqual(
                [call[1] for call in state.ignore_calls],
                [state.window.output_path],
            )
            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.capture_calls, [])
            self.assertEqual(state.writer.calls, [])
            self.assertFalse(
                (root / "data" / "outputs" / "ball_tracking").exists()
            )

    def test_manifest_must_be_tracked_and_under_experiment_registry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            untracked = replace(
                state.dependencies,
                inspect_git=lambda repository_root, manifest: GitSnapshot(
                    repository_root=root.resolve(),
                    head=HEAD,
                    clean=True,
                    manifest_tracked=False,
                ),
            )

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "committed",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=untracked,
                )

            outside_path = root / "configs" / "detector_experiment.json"
            outside_path.write_text("{}\n", encoding="utf-8")

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "configs/ball_tracking/experiments",
            ):
                preflight_detector_experiment(
                    outside_path,
                    root,
                    dependencies=state.dependencies,
                )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_second_tracked_manifest_cannot_reuse_run_or_output_claim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            state = make_context(root)
            second_path = (
                root
                / "configs"
                / "ball_tracking"
                / "experiments"
                / "second_experiment.json"
            )
            second_path.write_text("{}\n", encoding="utf-8")
            second_relative = PurePosixPath(
                second_path.relative_to(root).as_posix()
            )

            cases = (
                (
                    "detection_run_id",
                    state.window.detection_run_id,
                    PurePosixPath(
                        "data/outputs/ball_tracking/detections/test/second.json"
                    ),
                ),
                (
                    "output_path",
                    "second_detection_run",
                    state.window.output_path,
                ),
            )

            for expected_field, detection_run_id, output_path in cases:
                with self.subTest(field=expected_field):
                    second_window = replace(
                        state.window,
                        window_id="second_window",
                        annotation_set_id="second_annotations",
                        detection_run_id=detection_run_id,
                        output_path=output_path,
                    )
                    second_experiment = FakeExperiment(
                        state.detector,
                        [second_window],
                    )
                    dependencies = replace(
                        state.dependencies,
                        load_experiment=lambda path: (
                            state.experiment
                            if path == state.manifest_path
                            else second_experiment
                        ),
                        inspect_git=lambda repository_root, manifest: GitSnapshot(
                            repository_root=root,
                            head=HEAD,
                            clean=True,
                            manifest_tracked=True,
                            tracked_experiment_manifests=(
                                state.manifest_relative,
                                second_relative,
                            ),
                        ),
                    )

                    with self.assertRaisesRegex(
                        DetectorExperimentRunnerError,
                        f"globally unique {expected_field}",
                    ):
                        preflight_detector_experiment(
                            state.manifest_path,
                            root,
                            dependencies=dependencies,
                        )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_git_snapshot_must_be_exact_clean_tracked_head(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            cases = (
                GitSnapshot(root / "other", HEAD, True, True),
                GitSnapshot(root.resolve(), "abc", True, True),
                GitSnapshot(root.resolve(), "A" * 40, True, True),
                GitSnapshot(root.resolve(), HEAD, False, True),
                GitSnapshot(root.resolve(), HEAD, True, False),
                GitSnapshot(root.resolve(), HEAD, True, True, False),
            )

            for snapshot in cases:
                with self.subTest(snapshot=snapshot):
                    dependencies = replace(
                        state.dependencies,
                        inspect_git=(
                            lambda repository_root, manifest, value=snapshot: value
                        ),
                    )

                    with self.assertRaises(DetectorExperimentRunnerError):
                        preflight_detector_experiment(
                            state.manifest_path,
                            root,
                            dependencies=dependencies,
                        )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_git_state_is_rechecked_after_long_preflight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            state = make_context(root)
            snapshots = iter(
                (
                    GitSnapshot(
                        repository_root=root,
                        head=HEAD,
                        clean=True,
                        manifest_tracked=True,
                        tracked_experiment_manifests=(
                            state.manifest_relative,
                        ),
                    ),
                    GitSnapshot(
                        repository_root=root,
                        head=HEAD,
                        clean=False,
                        manifest_tracked=True,
                        tracked_experiment_manifests=(
                            state.manifest_relative,
                        ),
                    ),
                )
            )
            dependencies = replace(
                state.dependencies,
                inspect_git=lambda repository_root, manifest: next(snapshots),
            )

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "exactly clean",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=dependencies,
                )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_package_version_weight_presence_and_hash_are_preflight_gates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            wrong_version = replace(
                state.dependencies,
                read_package_version=lambda package: "9.9.9",
            )

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "version",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=wrong_version,
                )

            wrong_hash = replace(
                state.dependencies,
                hash_file=lambda path: "0" * 64,
            )

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "SHA-256",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=wrong_hash,
                )

            state.weights_path.unlink()

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "weights",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=state.dependencies,
                )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_weight_file_or_parent_symlink_is_a_preflight_gate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            original_is_symlink = Path.is_symlink

            for unsafe_component in (
                state.weights_path,
                state.weights_path.parent,
            ):
                with self.subTest(unsafe_component=unsafe_component):
                    def fake_is_symlink(path, target=unsafe_component):
                        if path == target:
                            return True
                        return original_is_symlink(path)

                    with patch.object(
                        Path,
                        "is_symlink",
                        autospec=True,
                        side_effect=fake_is_symlink,
                    ):
                        with self.assertRaisesRegex(
                            DetectorExperimentRunnerError,
                            "weights path must not traverse a symlink",
                        ):
                            preflight_detector_experiment(
                                state.manifest_path,
                                root,
                                dependencies=state.dependencies,
                            )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_manifest_alias_is_checked_before_symlink_resolution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            state = make_context(root)
            alias_path = state.manifest_path.with_name("alias.json")
            original_resolve = Path.resolve
            original_is_symlink = Path.is_symlink

            def fake_resolve(path, *args, **kwargs):
                if path == alias_path:
                    return state.manifest_path
                return original_resolve(path, *args, **kwargs)

            def fake_is_symlink(path):
                if path == alias_path:
                    return True
                return original_is_symlink(path)

            with patch.object(
                Path,
                "resolve",
                autospec=True,
                side_effect=fake_resolve,
            ), patch.object(
                Path,
                "is_symlink",
                autospec=True,
                side_effect=fake_is_symlink,
            ):
                with self.assertRaisesRegex(
                    DetectorExperimentRunnerError,
                    "must not traverse a symlink",
                ):
                    preflight_detector_experiment(
                        alias_path,
                        root,
                        dependencies=state.dependencies,
                    )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_source_contract_and_git_ignore_fail_before_model_or_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            bad_source = replace(
                state.dependencies,
                verify_source=lambda source, repository_root: (_ for _ in ()).throw(
                    ValueError("bad source hash")
                ),
            )

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "Source-video preflight",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=bad_source,
                )

            not_ignored = replace(
                state.dependencies,
                is_git_ignored=lambda repository_root, path: False,
            )

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "not ignored",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=not_ignored,
                )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_cuda_runtime_observation_is_a_preflight_gate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            unavailable = replace(
                state.dependencies,
                inspect_runtime_device=lambda: (_ for _ in ()).throw(
                    RuntimeError("CUDA unavailable")
                ),
            )

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "CUDA runtime preflight",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=unavailable,
                )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_output_escape_and_symlink_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "normalized repository-relative",
            ):
                _reject_symlink_components(
                    root,
                    PurePosixPath("../../escape.json"),
                    label="test output",
                )

            real_dir = root / "real"
            real_dir.mkdir()
            link_dir = root / "linked"

            try:
                os.symlink(real_dir, link_dir, target_is_directory=True)
            except OSError:
                self.skipTest("Directory symlinks are unavailable")

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "symlink",
            ):
                _reject_symlink_components(
                    root,
                    PurePosixPath("linked/run.json"),
                    label="test output",
                )

    def test_non_directory_output_parent_refuses_before_model_or_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            blocking_parent = (
                root
                / "data"
                / "outputs"
                / "ball_tracking"
                / "detections"
            )
            blocking_parent.parent.mkdir(parents=True, exist_ok=True)
            blocking_parent.write_text("not a directory\n", encoding="utf-8")

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "non-directory parent",
            ):
                preflight_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=state.dependencies,
                )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_conflicting_existing_binding_or_provenance_refuses_preflight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            run = complete_run(state)
            cases = (
                (
                    "detection_run_id",
                    lambda payload: payload.__setitem__(
                        "detection_run_id",
                        "conflicting_run",
                    ),
                ),
                (
                    "source_video",
                    lambda payload: payload["source_video"].__setitem__(
                        "sha256",
                        "c" * 64,
                    ),
                ),
                (
                    "model_provenance",
                    lambda payload: payload["model_provenance"].__setitem__(
                        "code_commit",
                        "c" * 40,
                    ),
                ),
            )

            for field, mutate in cases:
                with self.subTest(field=field):
                    payload = run.to_dict()
                    mutate(payload)
                    conflicting = BallDetectionRun.from_mapping(payload)
                    make_existing_output(state, conflicting)

                    with self.assertRaisesRegex(
                        DetectorExperimentRunnerError,
                        "conflicts",
                    ):
                        preflight_detector_experiment(
                            state.manifest_path,
                            root,
                            dependencies=state.dependencies,
                        )

            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_output_created_after_preflight_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            concurrent_run = _initial_run(
                state.window,
                expected_provenance(state),
            )

            def create_adapter_with_concurrent_output(weights_path, floor):
                state.adapter_factory_calls.append((weights_path, floor))
                make_existing_output(state, concurrent_run)
                return state.adapter

            dependencies = replace(
                state.dependencies,
                create_adapter=create_adapter_with_concurrent_output,
            )

            with self.assertRaisesRegex(
                DetectorExperimentRunnerError,
                "appeared after preflight",
            ):
                run_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=dependencies,
                )

            self.assertEqual(state.writer.calls, [])


class ExecutionTests(unittest.TestCase):
    def test_new_run_is_initialized_then_persisted_after_every_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            state.adapter.behaviors[3] = ()

            summary = run_detector_experiment(
                state.manifest_path,
                root,
                dependencies=state.dependencies,
            )

            self.assertFalse(summary.dry_run)
            self.assertEqual(summary.completed_frame_count, 25)
            self.assertEqual(summary.incomplete_frame_count, 0)
            self.assertEqual(
                state.adapter_factory_calls,
                [(state.weights_path.resolve(), 0.01)],
            )
            self.assertEqual(state.capture.read_calls, 27)
            self.assertTrue(state.capture.released)
            self.assertEqual(
                state.adapter.calls,
                [("rgb", frame) for frame in range(2, 27)],
            )
            self.assertEqual(len(state.writer.calls), 26)
            initial = state.writer.calls[0][0]
            self.assertEqual(
                {frame.inference_status for frame in initial.frames},
                {"not_run"},
            )
            final = state.writer.calls[-1][0]
            self.assertEqual(
                {frame.inference_status for frame in final.frames},
                {"completed"},
            )
            self.assertEqual(
                final.model_provenance.device,
                RUNTIME_DEVICE,
            )
            self.assertEqual(final.frame_by_index()[3].detections, ())

    def test_fully_complete_exact_output_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            make_existing_output(state, complete_run(state))

            summary = run_detector_experiment(
                state.manifest_path,
                root,
                dependencies=state.dependencies,
            )

            self.assertEqual(summary.completed_frame_count, 25)
            self.assertEqual(summary.incomplete_frame_count, 0)
            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.capture_calls, [])
            self.assertEqual(state.writer.calls, [])

    def test_resume_attempts_only_not_run_and_preserves_completed_and_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            run = _initial_run(state.window, expected_provenance(state))
            run = _replace_frame(
                run,
                2,
                inference_status="completed",
                failure_reason=None,
                detections=(),
            )
            run = _replace_frame(
                run,
                3,
                inference_status="inference_failed",
                failure_reason="prior detector failure",
                detections=None,
            )
            make_existing_output(state, run)

            with self.assertRaises(DetectorExperimentIncompleteError):
                run_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=state.dependencies,
                )

            self.assertEqual(
                state.adapter.calls,
                [("rgb", frame) for frame in range(4, 27)],
            )
            self.assertEqual(len(state.writer.calls), 23)
            final = state.writer.calls[-1][0]
            self.assertEqual(
                final.frame_by_index()[2].inference_status,
                "completed",
            )
            self.assertEqual(
                final.frame_by_index()[3].inference_status,
                "inference_failed",
            )
            self.assertEqual(
                final.frame_by_index()[3].failure_reason,
                "prior detector failure",
            )

    def test_inference_exception_is_persisted_and_later_targets_continue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            state.adapter.behaviors[4] = RuntimeError("synthetic inference")

            with self.assertRaises(DetectorExperimentIncompleteError):
                run_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=state.dependencies,
                )

            self.assertEqual(len(state.adapter.calls), 25)
            final = state.writer.calls[-1][0]
            self.assertEqual(
                final.frame_by_index()[4].inference_status,
                "inference_failed",
            )
            self.assertIn(
                "synthetic inference",
                final.frame_by_index()[4].failure_reason,
            )
            self.assertEqual(
                final.frame_by_index()[5].inference_status,
                "completed",
            )

    def test_decode_failure_marks_one_target_leaves_later_not_run_and_stops(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            state.capture = FakeCapture(fail_at=3)

            with self.assertRaises(DetectorExperimentIncompleteError):
                run_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=state.dependencies,
                )

            self.assertEqual(state.capture.read_calls, 4)
            self.assertEqual(state.adapter.calls, [("rgb", 2)])
            self.assertEqual(len(state.writer.calls), 3)
            final = state.writer.calls[-1][0]
            frames = final.frame_by_index()
            self.assertEqual(frames[2].inference_status, "completed")
            self.assertEqual(frames[3].inference_status, "decode_failed")
            self.assertEqual(frames[4].inference_status, "not_run")
            self.assertTrue(state.capture.released)

    def test_decode_exception_before_window_marks_next_target_and_stops(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            state.capture = FakeCapture(raise_at=1)

            with self.assertRaises(DetectorExperimentIncompleteError):
                run_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=state.dependencies,
                )

            self.assertEqual(state.capture.read_calls, 2)
            self.assertEqual(state.adapter.calls, [])
            final = state.writer.calls[-1][0]
            frames = final.frame_by_index()
            self.assertEqual(frames[2].inference_status, "decode_failed")
            self.assertIn("source frame 1", frames[2].failure_reason)
            self.assertEqual(frames[3].inference_status, "not_run")
            self.assertTrue(state.capture.released)

    def test_unopened_capture_marks_first_pending_decode_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            state.capture = FakeCapture(opened=False)

            with self.assertRaises(DetectorExperimentIncompleteError):
                run_detector_experiment(
                    state.manifest_path,
                    root,
                    dependencies=state.dependencies,
                )

            final = state.writer.calls[-1][0]
            frames = final.frame_by_index()
            self.assertEqual(frames[2].inference_status, "decode_failed")
            self.assertEqual(frames[3].inference_status, "not_run")
            self.assertEqual(state.adapter.calls, [])

    def test_atomic_writer_round_trips_and_replaces_without_temp_residue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = make_context(root)
            output_path = root / "ignored" / "run.json"
            run = _initial_run(state.window, expected_provenance(state))

            atomic_write_detection_run(run, output_path)
            loaded = BallDetectionRun.from_mapping(
                json.loads(output_path.read_text(encoding="utf-8"))
            )
            self.assertEqual(loaded, run)
            updated = _replace_frame(
                run,
                2,
                inference_status="completed",
                failure_reason=None,
                detections=(),
            )
            atomic_write_detection_run(updated, output_path)
            loaded_updated = BallDetectionRun.from_mapping(
                json.loads(output_path.read_text(encoding="utf-8"))
            )
            self.assertEqual(loaded_updated, updated)
            self.assertEqual(
                [path for path in output_path.parent.iterdir()],
                [output_path],
            )


if __name__ == "__main__":
    unittest.main()

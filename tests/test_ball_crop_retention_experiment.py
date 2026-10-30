"""Synthetic retention I/O, provenance, reuse, and pre-execution guard tests."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_retention_experiment as experiment
from src.ball_tracking import crop_motion_factorial as old_selector
from src.ball_tracking.crop_retention import ARMS, STEPS, RankingConfig, iter_ranked_frames
from src.ball_tracking.crop_retention_resources import BudgetJournal
from src.ball_tracking.development_experiments import canonical_sha256, sha256_file
from src.ball_tracking.tiled_candidates import candidate_run, crop_views, make_frame, make_output
from test_ball_temporal_association import fixture
from test_ball_tiled_comparison import crop_result


COMMIT = "e" * 40


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def candidate_fixture(root):
    """Construct a complete synthetic crop output, without any video file."""
    _, base = fixture([[] for _ in range(25)])
    model = replace(base.model_provenance, code_commit=experiment.RF_COMMIT,
                    target_class_id=37, target_class_name="sports ball", export_confidence_floor=.01)
    base = replace(base, model_provenance=model)
    source = base.source_video.to_dict()
    window = {"window_id": "synthetic_development_window", "purpose": "representative_evaluation",
              "possession_id": base.possession_id, "source_video": source,
              "start_frame_index": 0, "end_frame_index": 24,
              "annotation_set_id": base.annotation_set_id}
    stored = []
    for index in range(25):
        clutter = [(500+index*20, 100+j*20, .8) for j in range(20)]
        views = [crop_result(v) for v in crop_views()]
        views[0] = crop_result(crop_views()[0], [*clutter, (100, 100, .7)])
        stored.append(make_frame(index, views, base.source_video, model))
    header = {"window": {**window, "detection_run_id": base.detection_run_id},
              "per_view_model_provenance": model.to_dict(), "crop_views": crop_views()}
    value = make_output(header, stored)
    path = root / "data/outputs/synthetic_candidates.json"
    write_json(path, value)
    window["crop_candidates"] = experiment.file_binding(root, path)
    return window, candidate_run(base, value), value, path


def synthetic_context(root):
    window, source_run, value, path = candidate_fixture(root)
    c = RankingConfig(ARMS[0], .01, None, *STEPS[ARMS[0]])
    unit = {"comparison_unit_id": "synthetic_unit", "window_id": window["window_id"],
            "config": {**c.to_dict(), "retention_policy": "all_threshold_qualified_saved_candidates"}}
    limits = {"maximum_cumulative_seconds": 300., "maximum_seconds_per_unit": 30.,
              "maximum_worker_memory_bytes": 1024**3, "maximum_total_new_output_bytes": 1024**3,
              "minimum_free_disk_bytes": 0, "workers": 1}
    context = {"root": root, "commit": COMMIT, "spec_sha256": "f"*64,
               "output_root": root / experiment.OUTPUT_ROOT,
               "inputs": {window["window_id"]: (source_run, value["content_sha256"])},
               "proposal": {"new_selection_units": [unit], "windows": [window], "resource_limits": limits}}
    return context, unit, source_run


def complete_receipt(context, bindings, *, commit=COMMIT, success=True, unit_key="select:synthetic_unit"):
    target = context["output_root"]
    journal = BudgetJournal(target, context["proposal"]["resource_limits"])
    attempt, _ = journal.reserve(unit_key, True)
    path = target / "worker_results" / (attempt + ".json")
    experiment.persist_new(path, {"commit": commit, "spec_sha256": context["spec_sha256"], "artifacts": bindings})
    receipt = {"path": path.relative_to(target).as_posix(), "sha256": sha256_file(path)}
    journal.append("finished", attempt_id=attempt, elapsed_seconds=.01, success=success, worker_result=receipt)
    return path


def metadata_fixture(root):
    design = root / "docs/synthetic_retention.md"
    design.parent.mkdir(parents=True)
    design.write_text("Synthetic approval contract only.\n", encoding="utf-8")
    proposal = {"design": experiment.file_binding(root, design), "proposed_output_root": experiment.OUTPUT_ROOT,
                "new_selection_units": [{"id": i} for i in range(24)],
                "original_embargo_paths": [f"data/outputs/embargo_{i}.json" for i in range(9)],
                "sealed_holdouts_metadata_only": [["p1", 1, 2], ["p2", 3, 4], ["p3", 5, 6]]}
    pp = root / "configs/ball_tracking/proposals/synthetic_retention.json"
    write_json(pp, proposal)
    p_binding = experiment.file_binding(root, pp)
    approval = {"proposal": p_binding, "design": proposal["design"], "approved_by": "ryan",
                "implementation_authorized": True, "execution_authorized": True,
                "git_mutations_authorized": False, "training_authorized": False}
    ap = root / "configs/ball_tracking/reviews/synthetic_retention.json"
    write_json(ap, approval)
    a_binding = experiment.file_binding(root, ap)
    manifest = {"schema_version": "ball_crop_candidate_retention_experiment/v0.1",
                "experiment_id": experiment.EXPERIMENT_ID, "proposal": p_binding,
                "authorization": a_binding, "output_root": experiment.OUTPUT_ROOT,
                "implementation_validation": None, "selected_method": None,
                "selected_operating_point": None, "quality_gate": None}
    mp = root / "configs/ball_tracking/crop_retention_experiments/synthetic.json"
    write_json(mp, manifest)
    return mp, manifest


class CandidateInputTests(unittest.TestCase):
    def test_frozen_window_shape_loads_and_preserves_crop_mapping_without_old_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            window, expected, _, _ = candidate_fixture(root)
            self.assertNotIn("detection_run_id", window)
            with patch.object(old_selector, "rank_candidates", side_effect=AssertionError("old selector invoked")), \
                    patch.object(old_selector, "validate_observations", side_effect=AssertionError("old validator invoked")):
                actual, _ = experiment._candidate_input(root, window)
            self.assertEqual(actual.to_dict(), expected.to_dict())
            self.assertEqual(actual.frames[0].detections[20].candidate_index, 20)
            self.assertEqual(actual.model_provenance.code_commit, experiment.RF_COMMIT)
            self.assertFalse((root / actual.source_video.path).exists())

    def test_local_global_mapping_tamper_rejected_even_with_recomputed_content_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            window, _, value, path = candidate_fixture(root)
            value["frames"][0]["candidates"][0]["view_ordinal"] = 1
            value["content_sha256"] = canonical_sha256({"header": value["header"], "frames": value["frames"]})
            write_json(path, value)
            window["crop_candidates"] = experiment.file_binding(root, path)
            with self.assertRaises(ValueError):
                experiment._candidate_input(root, window)

    def test_header_source_identity_must_match_frozen_window(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            window, _, value, path = candidate_fixture(root)
            value["header"]["window"]["possession_id"] = "possession_002"
            value["content_sha256"] = canonical_sha256({"header": value["header"], "frames": value["frames"]})
            write_json(path, value)
            window["crop_candidates"] = experiment.file_binding(root, path)
            with self.assertRaises(ValueError):
                experiment._candidate_input(root, window)

    def test_input_byte_and_canonical_hash_tampering_are_separate_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            window, _, value, path = candidate_fixture(root)
            path.write_text(path.read_text() + " ", encoding="utf-8")
            with self.assertRaises(ValueError):
                experiment._candidate_input(root, window)
            window["crop_candidates"] = experiment.file_binding(root, path)
            value["content_sha256"] = "0"*64
            write_json(path, value)
            window["crop_candidates"] = experiment.file_binding(root, path)
            with self.assertRaises(ValueError):
                experiment._candidate_input(root, window)


class SelectionSerializationTests(unittest.TestCase):
    def test_write_read_complete_lossless_frames_and_original_indices_with_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, unit, source_run = synthetic_context(root)
            expected = list(iter_ranked_frames(source_run, experiment._config(unit)))
            before = copy.deepcopy(source_run.to_dict())
            binding = experiment.write_selection(root, context, unit)
            complete_receipt(context, [binding])
            with patch.object(experiment, "iter_ranked_frames", side_effect=AssertionError("selection rerun during load")), \
                    patch.object(old_selector, "rank_candidates", side_effect=AssertionError("old selector invoked")):
                observations = experiment.load_new_observations(root, context, unit)
                full = [experiment.read_trace(root, f) for f in observations["frames"]]
            self.assertEqual(full, expected)
            self.assertEqual(source_run.to_dict(), before)
            self.assertEqual(observations["detector_code_commit"], experiment.RF_COMMIT)
            self.assertEqual(observations["ranking_code_commit"], COMMIT)
            self.assertEqual(observations["variant_id"], experiment._config(unit).variant_id)
            self.assertEqual(observations["frames"][-1]["emitted_candidate_indices"], [20])
            self.assertEqual(len(list(experiment.unit_directory(context, unit).glob("frame_*.json.gz"))), 25)

    def test_variants_are_stable_across_windows_and_outputs_are_create_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, unit, _ = synthetic_context(root)
            other = {**unit, "window_id": "second_synthetic_window"}
            self.assertEqual(experiment._config(unit).variant_id, experiment._config(other).variant_id)
            bound = experiment.write_selection(root, context, unit)
            with self.assertRaises(ValueError):
                experiment.write_selection(root, context, unit)
            self.assertEqual(experiment.file_binding(root, root/bound["path"]), bound)

    def test_manifest_or_failed_attempt_without_success_receipt_is_not_resumable_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, unit, _ = synthetic_context(root)
            binding = experiment.write_selection(root, context, unit)
            with self.assertRaisesRegex(ValueError, "completion receipt"):
                experiment.load_new_observations(root, context, unit)
            complete_receipt(context, [binding], success=False)
            with self.assertRaisesRegex(ValueError, "completion receipt"):
                experiment.load_new_observations(root, context, unit)
            self.assertEqual(experiment.file_binding(root, root/binding["path"]), binding)

    def test_completed_receipt_rejects_different_execution_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, unit, _ = synthetic_context(root)
            binding = experiment.write_selection(root, context, unit)
            complete_receipt(context, [binding], commit="d"*40)
            with self.assertRaisesRegex(ValueError, "another source checkpoint"):
                experiment.load_new_observations(root, context, unit)

    def test_manifest_canonical_hash_and_trace_bytes_are_both_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, unit, _ = synthetic_context(root)
            binding = experiment.write_selection(root, context, unit)
            path = root/binding["path"]
            wrapper = json.loads(path.read_text())
            wrapper["observations"]["score_semantics"] = "tampered"
            write_json(path, wrapper)
            complete_receipt(context, [experiment.file_binding(root, path)])
            with self.assertRaisesRegex(ValueError, "provenance changed"):
                experiment.load_new_observations(root, context, unit)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, unit, _ = synthetic_context(root)
            binding = experiment.write_selection(root, context, unit)
            complete_receipt(context, [binding])
            first = next(experiment.unit_directory(context, unit).glob("frame_*.json.gz"))
            first.write_bytes(first.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "trace changed"):
                experiment.load_new_observations(root, context, unit)

    def test_compact_trace_disagreement_is_rejected_without_ranking_reexecution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, unit, _ = synthetic_context(root)
            binding = experiment.write_selection(root, context, unit)
            wrapper = json.loads((root/binding["path"]).read_text())
            compact = wrapper["observations"]["frames"][0]
            compact["ranking"]["winner"]["score"] += .1
            with patch.object(experiment, "iter_ranked_frames", side_effect=AssertionError("selector invoked")), \
                    self.assertRaisesRegex(ValueError, "compact observation disagree"):
                experiment.read_trace(root, compact)

    def test_real_unit_dispatch_rejects_caps_and_higher_thresholds(self):
        good = {"config": {**RankingConfig(ARMS[0], .01, None, *STEPS[ARMS[0]]).to_dict(),
                           "retention_policy": "all_threshold_qualified_saved_candidates"}}
        for changes in ({"confidence_threshold": .2}, {"confidence_threshold": .35},
                        {"candidate_cap": 20}, {"retention_policy": "top_twenty"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                experiment._config({"config": {**good["config"], **changes}})

    def test_interrupted_unit_retry_preserves_partial_and_previously_completed_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, first_unit, source_run = synthetic_context(root)
            first_binding = experiment.write_selection(root, context, first_unit)
            complete_receipt(context, [first_binding])
            second_unit = {"comparison_unit_id": "second_synthetic_unit", "window_id": first_unit["window_id"],
                           "config": {**RankingConfig(ARMS[1], .01, None, *STEPS[ARMS[1]]).to_dict(),
                                      "retention_policy": "all_threshold_qualified_saved_candidates"}}
            context["proposal"]["new_selection_units"].append(second_unit)
            journal = BudgetJournal(context["output_root"], context["proposal"]["resource_limits"])
            attempt, _ = journal.reserve("select:second_synthetic_unit", True)
            def interrupted(_run, settings):
                yield next(iter_ranked_frames(_run, settings))
                raise RuntimeError("synthetic interrupted attempt")
            with patch.object(experiment, "iter_ranked_frames", side_effect=interrupted), \
                    self.assertRaisesRegex(RuntimeError, "interrupted attempt"):
                experiment.write_selection(root, context, second_unit)
            journal.append("finished", attempt_id=attempt, elapsed_seconds=.25, success=False, worker_result=None)
            partials = list((context["output_root"] / ".pending_selection").rglob("frame_*.json.gz"))
            self.assertEqual(len(partials), 1)
            original_partial = partials[0].read_bytes()
            self.assertFalse(experiment.unit_directory(context, second_unit).exists())
            second_binding = experiment.write_selection(root, context, second_unit)
            complete_receipt(context, [second_binding], unit_key="select:second_synthetic_unit")
            self.assertEqual(partials[0].read_bytes(), original_partial)
            self.assertEqual(experiment.file_binding(root, root/first_binding["path"]), first_binding)
            self.assertEqual(len(experiment.load_new_observations(root, context, second_unit)["frames"]), 25)
            ledger = BudgetJournal(context["output_root"], context["proposal"]["resource_limits"])
            self.assertGreaterEqual(ledger.consumed(), .27)
            self.assertGreaterEqual(ledger.consumed("select:second_synthetic_unit"), .26)


class SavedReuseAndGuardTests(unittest.TestCase):
    def test_saved_control_is_loaded_byte_for_byte_without_old_selector_or_validator(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            _, source_run, _, _ = candidate_fixture(root)
            config = RankingConfig(ARMS[0], .2, 20, *STEPS[ARMS[0]])
            # This is synthetic saved JSON, never generated by an old selector.
            obs = {"config": config.to_dict(), "variant_id": config.variant_id,
                   "ranking_code_commit": experiment.MOTION_COMMIT, "detector_code_commit": experiment.RF_COMMIT,
                   "input_candidate_content_sha256": canonical_sha256(source_run.to_dict()),
                   "source_video": source_run.source_video.to_dict(), "window": source_run.window.to_dict(),
                   "possession_id": source_run.possession_id,
                   "frames": [{"frame_index": f.frame_index, "synthetic_saved_payload": "preserve"} for f in source_run.frames]}
            path = root/"data/outputs/synthetic_saved_control.json"
            write_json(path, {"observations": obs})
            record = {"file": experiment.file_binding(root, path), "observations_content_sha256": canonical_sha256(obs),
                      "config": config.to_dict(), "variant_id": config.variant_id,
                      "original_selection_commit": experiment.MOTION_COMMIT,
                      "original_detector_commit": experiment.RF_COMMIT}
            before = path.read_bytes()
            with patch.object(old_selector, "rank_candidates", side_effect=AssertionError("old selector invoked")), \
                    patch.object(old_selector, "validate_observations", side_effect=AssertionError("old validator invoked")):
                self.assertEqual(experiment.load_saved_control(root, record, source_run), obs)
            self.assertEqual(path.read_bytes(), before)
            record["observations_content_sha256"] = "0"*64
            with self.assertRaises(ValueError):
                experiment.load_saved_control(root, record, source_run)

    def test_dirty_or_staged_execution_fails_before_metadata_inputs_or_outputs(self):
        for dirty, staged in ((" M src/synthetic.py", ""), ("", "src/synthetic.py")):
            with self.subTest(dirty=dirty, staged=staged), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                path = root/"configs/ball_tracking/crop_retention_experiments/missing.json"
                def git(_root, *args):
                    return {("branch", "--show-current"): "codex/ball-detector-baseline",
                            ("status", "--porcelain=v1"): dirty,
                            ("diff", "--cached", "--name-only"): staged}[args]
                with patch.object(experiment, "_git", side_effect=git), \
                        patch.object(experiment, "read_json", side_effect=AssertionError("metadata read before guard")), \
                        patch.object(experiment, "run_supervised", side_effect=AssertionError("worker dispatched")), \
                        self.assertRaises(ValueError):
                    experiment.run_experiment(root, path)
                self.assertFalse((root/experiment.OUTPUT_ROOT).exists())

    def test_missing_implementation_certificate_blocks_clean_execution_without_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path, manifest = metadata_fixture(root)
            with patch.object(experiment, "PROPOSAL_SHA256", manifest["proposal"]["sha256"]), \
                    patch.object(experiment, "APPROVAL_SHA256", manifest["authorization"]["sha256"]), \
                    patch.object(experiment, "_clean_checkpoint", return_value=COMMIT), \
                    patch.object(experiment.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()), \
                    patch.object(experiment, "run_supervised", side_effect=AssertionError("worker dispatched")), \
                    self.assertRaisesRegex(ValueError, "validation is not complete"):
                experiment.run_experiment(root, path)
            self.assertFalse((root/experiment.OUTPUT_ROOT).exists())

    def test_certificate_requires_all_validation_flags_and_current_source_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root/"src/ball_tracking/crop_retention.py"
            source.parent.mkdir(parents=True)
            source.write_text("# Synthetic source binding.\n", encoding="utf-8")
            requirements = root/"requirements.txt"
            requirements.write_text("# Synthetic dependency binding.\n", encoding="utf-8")
            certificate = {"focused_tests_passed": True, "full_suite_passed": True,
                           "synthetic_dense_400_by_25_passed": True, "synthetic_sparse_400_by_25_passed": True,
                           "resource_abort_and_resume_tests_passed": True, "proposal_sha256": experiment.PROPOSAL_SHA256,
                           "source_bindings": [experiment.file_binding(root, p) for p in (source, requirements)],
                           "evidence_bindings": []}
            target = root/"data/outputs/synthetic_validation.json"
            for flag in ("focused_tests_passed", "full_suite_passed", "synthetic_dense_400_by_25_passed",
                         "synthetic_sparse_400_by_25_passed", "resource_abort_and_resume_tests_passed"):
                write_json(target, {**certificate, flag: False})
                with self.subTest(flag=flag), self.assertRaises(ValueError):
                    experiment._validate_implementation(root, {"implementation_validation": experiment.file_binding(root, target)})
            write_json(target, certificate)
            bound = experiment.file_binding(root, target)
            experiment._validate_implementation(root, {"implementation_validation": bound})
            source.write_text("# Changed synthetic source.\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                experiment._validate_implementation(root, {"implementation_validation": bound})

    def test_certificate_covers_all_dependencies_tests_and_requirement_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            names = ("src/ball_tracking/crop_retention.py", "src/common/nested/dependency.py",
                     "tests/nested/test_dependency.py", "requirements.txt")
            for name in names:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# Synthetic immutable validation input.\n", encoding="utf-8")
            certificate = {"focused_tests_passed": True, "full_suite_passed": True,
                           "synthetic_dense_400_by_25_passed": True, "synthetic_sparse_400_by_25_passed": True,
                           "resource_abort_and_resume_tests_passed": True, "proposal_sha256": experiment.PROPOSAL_SHA256,
                           "source_bindings": [experiment.file_binding(root, root/name) for name in names],
                           "evidence_bindings": []}
            target = root/"data/outputs/synthetic_validation.json"
            for missing in names[1:]:
                incomplete = {**certificate, "source_bindings": [b for b in certificate["source_bindings"]
                                                               if b["path"] != missing]}
                write_json(target, incomplete)
                with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "omits production dependencies or test inputs"):
                    experiment._validate_implementation(root, {"implementation_validation": experiment.file_binding(root, target)})
            write_json(target, certificate)
            manifest = {"implementation_validation": experiment.file_binding(root, target)}
            experiment._validate_implementation(root, manifest)
            for changed in names[1:]:
                path = root/changed
                original = path.read_bytes()
                path.write_bytes(original + b"# Synthetic changed input.\n")
                with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "Changed bound file"):
                    experiment._validate_implementation(root, manifest)
                path.write_bytes(original)
            # A newly added production dependency also invalidates old coverage.
            (root/"src/common/new_dependency.py").write_text("# New synthetic input.\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "omits production dependencies or test inputs"):
                experiment._validate_implementation(root, manifest)


if __name__ == "__main__":
    unittest.main()

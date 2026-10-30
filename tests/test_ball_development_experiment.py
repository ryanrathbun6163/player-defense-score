"""Development authorization and synthetic evaluation; never run a real model."""

import copy
import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath
from unittest.mock import patch

from src.ball_tracking import development_release as release
from src.ball_tracking.annotations import load_annotations
from src.ball_tracking.detections import load_detection_run
from src.ball_tracking.development_experiments import (
    EXPERIMENT_ID, EXPERIMENT_ROOT, PARENT_FILENAME, PARENT_SHA256, PURPOSES,
    REVIEW_ROOT, DevelopmentExperiment, canonical_sha256, development_windows,
    execution_spec_sha256, portable_path, read_json, sha256_file,
)
from src.ball_tracking.detector_experiments import (
    DetectorExperimentValidationError, ExperimentWindow, PREDICTION_EMBARGO, load_detector_experiment,
)
from src.ball_tracking.prepare_detection_visual_review import (
    DEVELOPMENT_SCHEMA_VERSION, DetectionVisualReviewError,
    load_detection_review_plan, prepare_detection_visual_review,
    validate_detection_visual_review_bundle_integrity,
)
from src.ball_tracking.run_detector_experiment import run_detector_experiment
from src.ball_tracking.score_detector_experiment import (
    DEVELOPMENT_POOL_SCHEMA, DetectorExperimentScoringError, PreparedPilot,
    ScoringDependencies, atomic_write_new_scoring_report, build_scoring_report,
    load_scoring_report, score_detector_experiment, validate_scoring_report,
)
from src.ball_tracking.evaluation import evaluate_detections, aggregate_evaluation_reports
from test_ball_detection_visual_review import (
    REAL_MANIFEST, SyntheticVisualContext, reviewed_annotation_payload,
    detection_payload, write_json, SCORER_HEAD,
)
from test_ball_detector_experiment_runner import make_context, FakeCapture, HEAD


def manifest_fixture(root):
    parent_path = root / EXPERIMENT_ROOT / PARENT_FILENAME
    parent_path.parent.mkdir(parents=True, exist_ok=True)
    parent_path.write_bytes(REAL_MANIFEST.read_bytes())
    parent = load_detector_experiment(parent_path)
    payload = release.execution_spec(parent)
    payload["release_authorization"] = {"path": f"{REVIEW_ROOT}/test_release.json", "sha256": "a" * 64}
    path = root / EXPERIMENT_ROOT / f"{EXPERIMENT_ID}.json"
    write_json(path, payload)
    return path, payload, parent


class DevelopmentManifestTests(unittest.TestCase):
    def test_exact_six_and_parent_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path, payload, parent = manifest_fixture(Path(directory))
            experiment = load_detector_experiment(path)
            self.assertEqual(len(experiment.windows_for_inference()), 6)
            self.assertEqual([w.selection_purpose for w in experiment.windows].count(PURPOSES[0]), 3)
            self.assertEqual(sha256_file(path.parent / PARENT_FILENAME), PARENT_SHA256)
            self.assertEqual(len(parent.windows_for_inference()), 3)
            self.assertEqual(sum(w.execution_status == PREDICTION_EMBARGO for w in parent.windows), 9)
            self.assertTrue({w.window_id for w in parent.windows}.isdisjoint(w.window_id for w in experiment.windows))
            self.assertTrue({w.detection_run_id for w in parent.windows}.isdisjoint(w.detection_run_id for w in experiment.windows))

    def test_all_contract_substitutions_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, original, parent = manifest_fixture(Path(directory))
            bad = []
            for field, value in (("selection_purpose", "test_holdout"), ("selection_purpose", "protocol_adjudication"),
                                 ("start_frame_index", 51), ("window_id", "alias"),
                                 ("detection_run_id", "alias"), ("output_path", parent.windows[0].output_path.as_posix())):
                p = copy.deepcopy(original); p["windows"][0][field] = value; bad.append(p)
            for key in ("windows", "sealed_holdouts"):
                p = copy.deepcopy(original); p[key].pop(); bad.append(p)
            p = copy.deepcopy(original); p["windows"].append(p["windows"][0]); bad.append(p)
            p = copy.deepcopy(original); p["windows"][0]["source_video"]["sha256"] = "a" * 64; bad.append(p)
            p = copy.deepcopy(original); p["parent_experiment"]["sha256"] = "a" * 64; bad.append(p)
            p = copy.deepcopy(original); p["detector"]["export_floor"] = 0.2; bad.append(p)
            p = copy.deepcopy(original); p["scoring_grid"]["confidence_thresholds"].pop(); bad.append(p)
            p = copy.deepcopy(original); del p["release_authorization"]; bad.append(p)
            p = copy.deepcopy(original); p["force"] = True; bad.append(p)
            for index, payload in enumerate(bad):
                with self.subTest(index=index):
                    write_json(path, payload)
                    with self.assertRaises(DetectorExperimentValidationError):
                        load_detector_experiment(path)
            write_json(path, original)
            parent_path = path.parent / PARENT_FILENAME
            parent_path.write_bytes(parent_path.read_bytes() + b" ")
            with self.assertRaisesRegex(DetectorExperimentValidationError, "binding mismatch"):
                load_detector_experiment(path)

    def test_paths_reject_aliases_and_windows_devices(self):
        for value in ("../x.json", "a//b.json", "a/./b.json", "a\\b.json", "C:/x.json", "a/NUL.json", "a/x?.json", "a./b.json"):
            with self.subTest(value=value), self.assertRaises(DetectorExperimentValidationError):
                portable_path(value)

    def test_release_denial_happens_before_model_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            state = make_context(Path(directory))
            path, _, _ = manifest_fixture(state.root)
            state.experiment = load_detector_experiment(path)
            state.manifest_path = path
            state.manifest_relative = PurePosixPath(path.relative_to(state.root).as_posix())
            with patch.object(release, "_clean_head", return_value=HEAD):
                with self.assertRaisesRegex(DetectorExperimentValidationError, "binding mismatch"):
                    run_detector_experiment(path, state.root, dependencies=state.dependencies)
            self.assertEqual(state.adapter_factory_calls, [])
            self.assertEqual(state.writer.calls, [])
            self.assertEqual(state.source_calls, [])

    def test_only_six_windows_infer_and_resume_is_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            state = make_context(Path(directory))
            path, _, parent = manifest_fixture(state.root)
            state.experiment = load_detector_experiment(path)
            state.manifest_path = path
            state.manifest_relative = PurePosixPath(path.relative_to(state.root).as_posix())
            deps = replace(state.dependencies, open_capture=lambda path: FakeCapture())
            with patch.object(release, "validate_development_release") as permit:
                run_detector_experiment(path, state.root, dependencies=deps)
                self.assertGreaterEqual(permit.call_count, 2)
                expected = [i for w in state.experiment.windows for i in range(w.start_frame_index, w.end_frame_index + 1)]
                self.assertEqual([f[1] for f in state.adapter.calls], expected)
                self.assertEqual(len(expected), 150)
                calls = len(state.writer.calls)
                run_detector_experiment(path, state.root, dependencies=deps)
                self.assertEqual(len(state.writer.calls), calls)
                self.assertEqual(len(state.adapter.calls), 150)
                self.assertEqual(len(state.adapter_factory_calls), 1)
            self.assertFalse(any((state.root / w.output_path).exists() for w in parent.windows))


class ReleaseMetadataTests(unittest.TestCase):
    """Real Git trees in disposable fixture repos; no user-repository mutations."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        path, _, self.parent = manifest_fixture(self.root)
        path.unlink()  # Activation must create this, after the evidence checkpoint.
        self.git("init", "-q")
        (self.root / ".gitignore").write_text("data/\n", encoding="utf-8")
        for name in release._label_paths(self.parent) | {"src/ball_tracking/example.py", "tests/example.py"}:
            p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("{}\n", encoding="utf-8")
        self.proposal_path = self.root / "configs/ball_tracking/proposals/fixture.json"
        write_json(self.proposal_path, {"schema_version": "ball_detector_development_release_proposal/v0.1",
                    "parent_experiment": release.execution_spec(self.parent)["parent_experiment"]})
        self.approval_path = self.root / REVIEW_ROOT / "experiment_approval.json"
        write_json(self.approval_path, {
            "schema_version": release.APPROVAL_SCHEMA,
            "proposal": {"path": self.proposal_path.relative_to(self.root).as_posix(), "sha256": sha256_file(self.proposal_path)},
            "approved_by": "ryan", "approved_at_utc": "2026-09-19T12:00:00Z",
            "statement": "Synthetic approval fixture", "scope": "six_development_windows_only",
            "git_mutations_authorized": False,
        })
        self.commit()
        with patch.object(release, "verify_annotation_evidence"):
            self.evidence = release.prepare_release_evidence(self.proposal_path, self.approval_path, self.root,
                test_runner=lambda root: {"returncode": 0, "tests_run": 42, "output_sha256": "b" * 64})
        self.report_path = self.root / release.EVIDENCE_ROOT / "fixture/validation.json"
        write_json(self.report_path, self.evidence)

    def git(self, *args):
        result = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "user.name=Fixture",
                                 "-c", "user.email=fixture@example.invalid", *args], cwd=self.root,
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "-qm", "Disposable test fixture")
        return self.git("rev-parse", "HEAD")

    def activate(self):
        paths = release.prepare_activation(self.report_path, self.root)
        self.assertEqual(len(paths), 5)
        self.assertFalse((self.root / "data/outputs/ball_tracking/detections").exists())
        self.commit()
        return load_detector_experiment(paths[2])

    def test_activation_binds_prior_commit_and_runtime_never_opens_labels(self):
        experiment = self.activate()
        self.assertNotEqual(self.evidence["evidence_commit"], self.git("rev-parse", "HEAD"))
        original_open = Path.open
        def guarded_open(path, *args, **kwargs):
            self.assertNotIn("annotations", path.parts)
            self.assertNotIn("annotation_visual_review", path.parts)
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", guarded_open):
            release.validate_development_release(experiment, self.root, self.git("rev-parse", "HEAD"))
        for purpose in PURPOSES:
            plan = release.development_review_plan(purpose)
            load_detection_review_plan(self.root / REVIEW_ROOT / f"{plan['review_id']}.json")

    def test_dirty_or_newly_committed_label_or_code_invalidates_evidence(self):
        experiment = self.activate()
        for name in (next(iter(release._label_paths(self.parent))), "src/ball_tracking/example.py"):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.assertRaisesRegex(DetectorExperimentValidationError, "clean committed"):
                release.validate_development_release(experiment, self.root, self.git("rev-parse", "HEAD"))
            self.commit()
            with self.assertRaisesRegex(DetectorExperimentValidationError, "Git blob changed"):
                release.validate_development_release(experiment, self.root, self.git("rev-parse", "HEAD"))
            path.write_bytes(original); self.commit()

    def test_incomplete_failed_forged_and_nonancestor_evidence_refused(self):
        changes = [lambda p: p["protected_files"].pop(),
                   lambda p: p["validation"].update(returncode=1),
                   lambda p: p["validation"].update(tests_run=0),
                   lambda p: p.update(execution_spec_sha256="c" * 64),
                   lambda p: p.update(evidence_commit="c" * 40),
                   lambda p: p["development_windows"][0].update(selection_purpose="test_holdout"),
                   lambda p: p["experiment_approval"].update(sha256="c" * 64)]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                report = copy.deepcopy(self.evidence); change(report)
                write_json(self.report_path, report)
                with self.assertRaises(DetectorExperimentValidationError):
                    release.prepare_activation(self.report_path, self.root)
                self.assertFalse((self.root / EXPERIMENT_ROOT / f"{EXPERIMENT_ID}.json").exists())

    def test_missing_and_rehashed_receipts_and_sealed_output_refused(self):
        experiment = self.activate()
        receipt = self.root / experiment.payload["release_authorization"]["path"]
        receipt.write_bytes(receipt.read_bytes() + b" ")
        self.commit()
        with self.assertRaisesRegex(DetectorExperimentValidationError, "binding mismatch"):
            release.validate_development_release(experiment, self.root, self.git("rev-parse", "HEAD"))
        receipt.unlink()
        with self.assertRaises(DetectorExperimentValidationError):
            release.validate_development_release(experiment, self.root, self.git("rev-parse", "HEAD"))
        embargo = next(w for w in self.parent.windows if w.selection_purpose == "test_holdout")
        output = self.root / embargo.output_path
        output.parent.mkdir(parents=True, exist_ok=True); output.write_text("{}")
        with self.assertRaisesRegex(DetectorExperimentValidationError, "embargo output"):
            release._check_sealed_outputs(self.root, self.parent)

    def test_create_only_publication_preserves_existing_bytes(self):
        p = self.root / release.EVIDENCE_ROOT / "atomic.json"
        release.publish_new_json(p, {"value": 1})
        original = p.read_bytes()
        with self.assertRaises(FileExistsError):
            release.publish_new_json(p, {"value": 2})
        self.assertEqual(original, p.read_bytes())
        self.assertEqual(list(p.parent.glob("*.tmp")), [])


class SyntheticDevelopmentContext(SyntheticVisualContext):
    def __init__(self, root):
        super().__init__(root)
        parent = self.experiment  # Small, artificial source frames for rendering.
        payload = release.execution_spec(parent)
        payload["release_authorization"] = {"path": f"{REVIEW_ROOT}/synthetic_release.json", "sha256": "a" * 64}
        windows = tuple(ExperimentWindow.from_mapping(w, i, development=True) for i, w in enumerate(payload["windows"]))
        self.experiment = DevelopmentExperiment(payload, parent, windows)
        self.experiment_relative = PurePosixPath(EXPERIMENT_ROOT, f"{EXPERIMENT_ID}.json")
        self.experiment_path = root / self.experiment_relative
        self.experiment_bytes = write_json(self.experiment_path, payload)
        self.prepared = []
        for w in windows:
            annotation_path = root / f"configs/ball_tracking/annotations/{w.annotation_set_id}.json"
            a = reviewed_annotation_payload(w, w.source_video)
            a["window"]["selection_purpose"] = w.selection_purpose
            # All centers visible except the five explicitly hidden P003 challenge frames.
            for row in a["annotations"]:
                index = row["frame_index"]
                row.update(copy.deepcopy(a["annotations"][4])); row["frame_index"] = index
                if w.possession_id == "possession_003" and w.selection_purpose == PURPOSES[1] and 165 <= index <= 169:
                    row.update(visibility="not_visible", absence_reason="occluded", geometry=None, localization_eligible=False)
            ab = write_json(annotation_path, a); annotations = load_annotations(annotation_path)
            detection_path = root / w.output_path
            db = write_json(detection_path, detection_payload(self.experiment, w, w.source_video, annotations))
            detections = load_detection_run(detection_path)
            self.prepared.append(PreparedPilot(w, annotation_path, ab, annotations, detection_path, db, detections))
        self.reports = {}
        for purpose in PURPOSES:
            pool = [p for p in self.prepared if p.window.selection_purpose == purpose]
            self.reports[purpose] = build_scoring_report(self.experiment, self.experiment_relative,
                self.experiment_bytes, SCORER_HEAD, pool, selection_purpose=purpose)

    def choose_pool(self, purpose):
        plan = release.development_review_plan(purpose)
        self.report_relative = PurePosixPath(plan["scoring_report_path"])
        self.report_path = self.root / self.report_relative
        write_json(self.report_path, self.reports[purpose])
        self.plan_relative = PurePosixPath(REVIEW_ROOT, f"{plan['review_id']}.json")
        self.plan_path = self.root / self.plan_relative
        self.plan_bytes = write_json(self.plan_path, plan)
        self.snapshots = [self.snapshot(), self.snapshot()]

    def scoring_dependencies(self):
        return ScoringDependencies(
            load_experiment=lambda path: self.experiment, inspect_git=lambda *args: self.snapshot(),
            verify_tracked_file=lambda *args: None, verify_commit_ancestor=lambda *args: None,
            verify_source=self.verify_source, is_git_ignored=lambda *args: True,
            load_annotation=load_annotations, load_detection=load_detection_run,
            evaluate=evaluate_detections, aggregate=aggregate_evaluation_reports,
            write_report=atomic_write_new_scoring_report,
        )


class DevelopmentScoringTests(unittest.TestCase):
    def test_two_pools_270_reports_hidden_frames_and_no_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            s = SyntheticDevelopmentContext(Path(directory))
            self.assertEqual(sum(r["evaluation_report_count"] for r in s.reports.values()), 270)
            for purpose, r in s.reports.items():
                self.assertEqual(r["schema_version"], DEVELOPMENT_POOL_SCHEMA)
                self.assertEqual(r["window_count"], 3)
                self.assertEqual(r["grid_cell_count"], 45)
                self.assertIsNone(r["selected_operating_point"])
                self.assertIsNone(r["quality_gate"])
                self.assertEqual({e["selection_purpose"] for e in r["evaluation_reports"]}, {purpose})
                expected_hidden = 5 if purpose == PURPOSES[1] else 0
                self.assertEqual(sum(e["not_visible_frame_count"] for e in r["evaluation_reports"][:3]), expected_hidden)
                self.assertEqual(sum(e["eligible_frame_count"] for e in r["evaluation_reports"][:3]), 75 - expected_hidden)
            hidden = [row for p in s.prepared for row in p.annotations.annotations if row.geometry is None]
            self.assertEqual([row.frame_index for row in hidden], list(range(165, 170)))
            deps = s.scoring_dependencies()
            with patch("src.ball_tracking.development_scoring.validate_development_release"):
                first = score_detector_experiment(s.experiment_path, s.root, dependencies=deps)
                second = score_detector_experiment(s.experiment_path, s.root, dependencies=deps)
                self.assertEqual(first.evaluation_report_count, 270)
                self.assertFalse(first.reused_existing)
                self.assertTrue(second.reused_existing)

    def test_tamper_mixed_pool_and_failed_frame_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            s = SyntheticDevelopmentContext(Path(directory))
            for field, value in (("quality_gate", "pass"), ("selected_operating_point", {}),
                                 ("selection_purpose", "test_holdout"), ("window_count", 2),
                                 ("evaluation_report_count", 134)):
                r = copy.deepcopy(s.reports[PURPOSES[0]]); r[field] = value
                with self.subTest(field=field), self.assertRaises(DetectorExperimentScoringError):
                    validate_scoring_report(r)
            with self.assertRaisesRegex(DetectorExperimentScoringError, "mix window purposes"):
                build_scoring_report(s.experiment, s.experiment_relative, s.experiment_bytes,
                                     SCORER_HEAD, s.prepared[:3], selection_purpose=PURPOSES[0])
            p = s.prepared[0].detection_path
            value = read_json(p); value["frames"][0].update(inference_status="not_run", failure_reason="Synthetic interruption", detections=None)
            write_json(p, value)
            with patch("src.ball_tracking.development_scoring.validate_development_release"):
                with self.assertRaises(DetectorExperimentScoringError):
                    score_detector_experiment(s.experiment_path, s.root, dependencies=s.scoring_dependencies())
            self.assertFalse((s.root / f"data/outputs/ball_tracking/evaluations/{EXPERIMENT_ID}").exists())

    def test_cross_pool_provenance_conflicts_and_existing_reports_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            s = SyntheticDevelopmentContext(Path(directory))
            deps = s.scoring_dependencies()
            with patch("src.ball_tracking.development_scoring.validate_development_release"):
                p = s.prepared[-1].detection_path
                original = p.read_bytes()
                value = read_json(p); value["model_provenance"]["device"] = "cuda:1 | synthetic mismatch"
                write_json(p, value)
                with self.assertRaises(DetectorExperimentScoringError):
                    score_detector_experiment(s.experiment_path, s.root, dependencies=deps)
                p.write_bytes(original)
                summary = score_detector_experiment(s.experiment_path, s.root, dependencies=deps)
                report_path = summary.output_path / f"{PURPOSES[0]}_grid_v0_2.json"
                bad = read_json(report_path); bad["quality_gate"] = "invented"
                write_json(report_path, bad); previous_bytes = report_path.read_bytes()
                with self.assertRaises(DetectorExperimentScoringError):
                    score_detector_experiment(s.experiment_path, s.root, dependencies=deps)
                self.assertEqual(report_path.read_bytes(), previous_bytes)

    def test_visual_review_both_pools_every_final_frame_and_strict_plans(self):
        with tempfile.TemporaryDirectory() as directory:
            s = SyntheticDevelopmentContext(Path(directory))
            with patch.object(release, "validate_development_release"):
                for purpose in PURPOSES:
                    s.choose_pool(purpose)
                    summary = prepare_detection_visual_review(s.plan_path, s.root, dependencies=s.dependencies())
                    manifest = validate_detection_visual_review_bundle_integrity(summary.output_dir)
                    self.assertEqual(manifest["schema_version"], DEVELOPMENT_SCHEMA_VERSION)
                    self.assertEqual(manifest["aggregate_grid"]["selection_purpose"], purpose)
                    self.assertEqual(len(manifest["windows"]), 3)
                    self.assertIsNone(manifest["safeguards"]["quality_gate"])
                    for row in manifest["windows"]:
                        self.assertEqual(row["window"]["frame_count"], 25)
                        self.assertTrue(row["final_frame_included"])
                        self.assertEqual(row["comparison_frames"][-1]["frame_index"], row["window"]["end_frame_index"])
            self.assertEqual(len(s.decode_calls), 6)
            plan = read_json(s.plan_path)
            for change in (lambda p: p["render_scope"].update(selection_purpose="test_holdout"),
                           lambda p: p["views"][0].update(confidence_threshold=0.4),
                           lambda p: p["interpretation"].update(selected_operating_point={})):
                bad = copy.deepcopy(plan); change(bad); write_json(s.plan_path, bad)
                with self.assertRaises(DetectionVisualReviewError):
                    load_detection_review_plan(s.plan_path)


if __name__ == "__main__":
    unittest.main()

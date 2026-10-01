"""Synthetic runner/scoring checks; controls are never rerun by the new pipeline."""
import copy
import csv
import shutil
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from src.ball_tracking import crop_player_context as core
from src.ball_tracking import crop_player_context_experiment as experiment
from src.ball_tracking import crop_player_context_evaluation as evaluation
from src.ball_tracking import crop_player_context_review as review
from src.ball_tracking import crop_motion_experiment as prior_experiment
from src.ball_tracking import crop_motion_evaluation as prior_evaluation
from src.ball_tracking import crop_motion_review as prior_review
from src.ball_tracking import crop_motion_factorial as controls
from src.ball_tracking import crop_ranking as legacy
from src.ball_tracking import crop_ranking_evaluation as legacy_evaluation
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.temporal_experiment import file_binding, spec_digest
from test_ball_crop_motion_factorial import motion_setup, execution_patches as old_execution_patches
from test_ball_detection_visual_review import write_json

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "c" * 40


def context_window(window, root):
    rows = []
    for frame in range(window["start_frame_index"], window["end_frame_index"]+1):
        if frame == window["end_frame_index"]:
            continue  # Explicit absent context must survive selection and scoring.
        rows.append({"frame_index": frame, "timestamp_sec": frame/25.0, "track_id": 1, "confidence": .9,
                     "x1": 50.0, "y1": 50.0, "x2": 200.0, "y2": 200.0, "floor_x": 125.0, "floor_y": 200.0,
                     "team_label": "dark", "segment_id": "t1_s1", "baseline_player_id": "dark_p1",
                     "player_id": "dark_p1", "reconciled_team": "dark", "identity_status": "active",
                     "identity_review_reason": "", "duplicate_detection_count": 1,
                     "source_track_ids": "1", "source_segment_ids": "t1_s1"})
    original = [{k: str(v) for k, v in row.items()} for row in rows]
    target = root/f"data/outputs/identity/{window['window_id']}_tracks.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=core.COLUMNS)
        writer.writeheader()
        writer.writerows(original)
    counts = {str(f): int(f != window["end_frame_index"]) for f in range(window["start_frame_index"], window["end_frame_index"]+1)}
    return {**{k: window[k] for k in ("window_id", "possession_id", "purpose", "start_frame_index", "end_frame_index", "source_video")},
            "source_video_binding_status": "Synthetic metadata only", "player_tracks": file_binding(root, target),
            "columns": list(core.COLUMNS), "per_frame_box_counts": counts, "box_rows": len(rows),
            "frames_with_any_box": len(rows), "frames_with_ten_boxes": 0,
            "missing_box_slots_relative_to_ten": 250-len(rows), "rows_collapsing_duplicate_detections": 0,
            "raw_and_reconciled_team_disagreements": 0, "selected_rows_sha256": canonical_sha256(rows),
            "prior_feasibility_selected_rows_sha256": canonical_sha256(rows), "rows": rows,
            "original_csv_records": original, "original_csv_records_sha256": canonical_sha256(original)}


def bind_manifest(root, proposal):
    target = root/"configs/ball_tracking/proposals/synthetic_context.json"
    write_json(target, proposal)
    m = {"schema_version": "ball_crop_player_context_experiment/v0.1", "experiment_id": experiment.EXPERIMENT_ID,
         "proposal": file_binding(root, target), "output_root": experiment.OUTPUT_ROOT,
         "authorization": None, "selected_operating_point": None, "quality_gate": None}
    auth = {"schema_version": "ball_crop_player_context_approval/v0.1", "experiment_spec_sha256": spec_digest(m),
            "proposal": m["proposal"], "approved_by": "ryan", "statement": "Synthetic exact-scope approval only",
            "recorded_at_utc": "2026-10-01T00:00:00Z", "timestamp_semantics": "Synthetic fixture",
            "scope": experiment.APPROVAL_SCOPE, "git_mutations_authorized": False}
    target = root/"configs/ball_tracking/reviews/synthetic_context_approval.json"
    write_json(target, auth)
    m["authorization"] = file_binding(root, target)
    path = root/experiment.CONFIG_ROOT/"synthetic.json"
    write_json(path, m)
    return path, m


def context_setup(root):
    """Generate saved controls once using synthetic data before no-rerun guards."""
    prior_path, prior_m, prior_p = motion_setup(root)
    with ExitStack() as stack:
        old_execution_patches(stack, prior_experiment, experiment.PRIOR_COMMIT)
        prior_experiment.run_experiment(root, prior_path)
        scores = prior_evaluation.score_experiment(root, prior_path)
    p = read_json(ROOT/"configs/ball_tracking/proposals/rfdetr_medium_crop_player_context_v0_1.json")
    p["prior_motion_manifest"] = file_binding(root, prior_path)
    p["prior_motion_proposal"] = prior_m["proposal"]
    p["windows"], p["scoring_labels"] = prior_p["windows"], prior_p["scoring_labels"]
    p["saved_control_outputs"] = [file_binding(root, prior_experiment.output_path(root, w, c))
                                  for w in p["windows"] for c in controls.experiment_grid()]
    p["saved_control_scoring_reports"] = scores["reports"]
    for key in ("design", "rationale"):
        target = root/p[key]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Synthetic context document only.\n", encoding="utf-8")
        p[key] = file_binding(root, target)
    target = root/p["prior_review_manifest"]["path"]
    write_json(target, {"header": {"windows": p["windows"], "scoring_reports": scores["reports"]}, "assets": []})
    p["prior_review_manifest"] = file_binding(root, target)
    execution = {"commit": experiment.PRIOR_COMMIT, "manifest": p["prior_motion_manifest"],
                 "spec_sha256": spec_digest(prior_m), "derived_outputs": p["saved_control_outputs"],
                 "scoring": {"reports": scores["reports"]}, "review_manifest": p["prior_review_manifest"],
                 "original_embargo_paths_absent": p["original_embargo_paths"]}
    target = root/p["prior_motion_execution"]["path"]
    write_json(target, execution)
    p["prior_motion_execution"] = file_binding(root, target)
    target = root/p["motion_review_receipt"]["path"]
    write_json(target, {"human_visual_review": {"status": "completed", "reviewer_id": "ryan"},
                        "bound_evidence": {"execution_commit": experiment.PRIOR_COMMIT,
                                           "experiment_manifest": p["prior_motion_manifest"],
                                           "execution_record": p["prior_motion_execution"],
                                           "scoring_reports": scores["reports"]}})
    p["motion_review_receipt"] = file_binding(root, target)
    windows = [context_window(w, root) for w in p["windows"]]
    snapshot = {k: {} for k in experiment.SNAPSHOT_FIELDS}
    snapshot.update(schema_version="ball_observed_player_context_inputs/v0.1", source_experiment_commit=experiment.PRIOR_COMMIT,
                    windows=windows, scope={"window_count": 6, "source_frame_count": 150, "observed_row_count": 144},
                    all_window_rows_canonical_sha256=canonical_sha256([{"window_id": w["window_id"], "rows": w["rows"]} for w in windows]),
                    selected_method=None, selected_operating_point=None, quality_gate=None)
    target = root/p["player_context"]["snapshot"]["path"]
    write_json(target, snapshot)
    p["player_context"]["snapshot"] = file_binding(root, target)
    p["player_context"]["selected_rows"] = 144
    return (*bind_manifest(root, p), p)


def execution_patches(stack, proposal_digest):
    old_execution_patches(stack, experiment, COMMIT)
    stack.enter_context(patch.object(experiment, "APPROVED_PROPOSAL_SHA256", proposal_digest))
    # Inherited fixed parent contracts use real source hashes. These fixture files contain no media;
    # independent source-byte guard tests below exercise the real hash checker on dummy bytes.
    stack.enter_context(patch.object(experiment, "verify_source_files"))


def forbid_control_execution(stack):
    for module, names in ((controls, ("rank_candidates", "validate_observations")),
                          (legacy, ("rank_candidates", "validate_observations")),
                          (prior_experiment, ("run_experiment",)),
                          (prior_evaluation, ("score_experiment", "evaluate_observations", "_evaluate_validated")),
                          (legacy_evaluation, ("score_experiment", "evaluate_observations", "_evaluate_validated"))):
        for name in names:
            if hasattr(module, name):
                stack.enter_context(patch.object(module, name, side_effect=AssertionError("Saved controls were recomputed")))


class ContextExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.template.cleanup)
        context_setup(Path(cls.template.name))

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        shutil.copytree(self.template.name, self.root, dirs_exist_ok=True)
        self.path = self.root/experiment.CONFIG_ROOT/"synthetic.json"
        self.m = read_json(self.path)
        self.p = read_json(self.root/self.m["proposal"]["path"])
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        execution_patches(self.stack, self.m["proposal"]["sha256"])

    def test_selection_is_label_and_score_blind_and_never_reruns_controls(self):
        original = Path.open
        def guarded(path, *args, **kwargs):
            if "/annotations/" in path.as_posix() or "/evaluation/" in path.as_posix() or path.suffix in (".png", ".npz"):
                raise AssertionError("Selection opened forbidden evidence")
            return original(path, *args, **kwargs)
        with ExitStack() as stack:
            forbid_control_execution(stack)
            stack.enter_context(patch.object(Path, "open", guarded))
            result = experiment.run_experiment(self.root, self.path, dry_run=True)
        self.assertEqual((result["source_frames"], result["new_outputs"], result["reused_outputs"]), (150, 216, 378))
        self.assertFalse((self.root/experiment.OUTPUT_ROOT).exists())

    def test_dirty_execution_stops_before_input_or_output(self):
        with patch.object(experiment, "clean_commit", side_effect=ValueError("dirty")), patch.object(experiment, "load_inputs") as inputs:
            with self.assertRaisesRegex(ValueError, "dirty"):
                experiment.run_experiment(self.root, self.path)
            inputs.assert_not_called()
        self.assertFalse((self.root/experiment.OUTPUT_ROOT).exists())

    def test_exact_proposal_and_approval_cannot_be_rebound(self):
        p = copy.deepcopy(self.p)
        p["context_term"]["coefficient"] = .5
        path, _ = bind_manifest(self.root, p)
        with self.assertRaisesRegex(ValueError, "exact approved"):
            experiment.load_manifest(self.root, path)
        bind_manifest(self.root, self.p)
        auth = self.root/self.m["authorization"]["path"]
        auth.write_bytes(auth.read_bytes()+b" ")
        with self.assertRaises(ValueError):
            experiment.load_manifest(self.root, self.path)

    def test_all_nine_original_prediction_embargoes(self):
        for name in self.p["original_embargo_paths"]:
            target = self.root/name
            write_json(target, {})
            try:
                with self.assertRaisesRegex(ValueError, "embargo"):
                    experiment.load_manifest(self.root, self.path)
            finally:
                target.unlink()

    def test_changed_or_missing_player_source_and_snapshot_are_rejected(self):
        loaded = experiment.load_manifest(self.root, self.path)
        snapshot_path = self.root/self.p["player_context"]["snapshot"]["path"]
        snapshot = read_json(snapshot_path)
        csv_path = self.root/snapshot["windows"][0]["player_tracks"]["path"]
        original = csv_path.read_bytes()
        csv_path.write_bytes(original+b" ")
        with self.assertRaisesRegex(ValueError, "CSV source"):
            experiment.load_inputs(self.root, loaded)
        csv_path.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            experiment.load_inputs(self.root, loaded)
        csv_path.write_bytes(original)
        snapshot_path.write_bytes(snapshot_path.read_bytes()+b" ")
        with self.assertRaises(ValueError):
            experiment.load_inputs(self.root, loaded)

    def test_snapshot_source_frame_and_digest_guards(self):
        loaded = experiment.load_manifest(self.root, self.path)
        prior = prior_experiment.load_inputs(self.root, loaded[2:])
        path = self.root/self.p["player_context"]["snapshot"]["path"]
        original = read_json(path)
        variants = []
        x = copy.deepcopy(original); x["windows"][0]["source_video"]["sha256"] = "a"*64; variants.append(x)
        x = copy.deepcopy(original); x["windows"][0]["rows"][0]["frame_index"] = 300; variants.append(x)
        x = copy.deepcopy(original); x["windows"].pop(); variants.append(x)
        x = copy.deepcopy(original); x["all_window_rows_canonical_sha256"] = "a"*64; variants.append(x)
        for value in variants:
            write_json(path, value)
            p = copy.deepcopy(self.p); p["player_context"]["snapshot"] = file_binding(self.root, path)
            with self.subTest(value=value), self.assertRaises(ValueError):
                experiment.load_context(self.root, p, [run for _, run, _ in prior])

    def test_saved_control_crop_provenance_even_after_outer_rebinding(self):
        binding = self.p["saved_control_outputs"][0]
        target = self.root/binding["path"]
        value = read_json(target); value["crop_content_sha256"] = "0"*64
        write_json(target, value)
        p = copy.deepcopy(self.p); p["saved_control_outputs"][0] = file_binding(self.root, target)
        with self.assertRaisesRegex(ValueError, "provenance"):
            experiment.load_saved_control(self.root, p, p["windows"][0], controls.experiment_grid()[0])

    def test_all_new_outputs_resume_and_saved_reports_are_exactly_reused(self):
        preserved = {b["path"]: (self.root/b["path"]).read_bytes()
                     for b in [*self.p["saved_control_outputs"], *self.p["saved_control_scoring_reports"]]}
        with ExitStack() as stack:
            forbid_control_execution(stack)
            persist = experiment.persist_once
            count = 0
            def interrupted(target, payload):
                nonlocal count
                count += 1
                if count == 5:
                    raise RuntimeError("synthetic interruption")
                return persist(target, payload)
            with patch.object(experiment, "persist_once", side_effect=interrupted), self.assertRaisesRegex(RuntimeError, "interruption"):
                experiment.run_experiment(self.root, self.path)
            self.assertEqual(experiment.run_experiment(self.root, self.path)["created_outputs"], 212)
            self.assertEqual(experiment.run_experiment(self.root, self.path)["created_outputs"], 0)
            result = evaluation.score_experiment(self.root, self.path)
            self.assertEqual((result["per_window_reports"], result["aggregate_cells_per_pool"]), (2970, 495))
            self.assertEqual((result["saved_controls_reranked"], result["saved_controls_rescored"]), (0, 0))
            with patch.object(evaluation, "evaluate_detections", side_effect=AssertionError("Review loader rescored")), \
                    patch.object(evaluation, "score_experiment", side_effect=AssertionError("Review invoked scoring stage")), \
                    patch.object(core, "rank_candidates", side_effect=AssertionError("Review loader ranked")), \
                    patch.object(experiment, "rank_candidates", side_effect=AssertionError("Review selected")), \
                    patch.object(prior_review, "render_experiment", side_effect=AssertionError("Review rerendered old controls")), \
                    patch.object(review, "load_reused_assets", return_value=[]):
                pools = evaluation.load_scoring_pools(self.root, self.m, self.p, COMMIT)
                prepared = review._prepare_review(self.root, self.path)
                self.assertEqual(len(prepared.windows), 6)
                for item in prepared.windows:
                    frames = [f.frame_index for f in item["run"].frames]
                    self.assertEqual(len(frames), 25)
                    self.assertEqual(len(item["observations"]), 22)
                    self.assertEqual(set(item["observations"]), set(item["reports"]))
                    for key, obs in item["observations"].items():
                        self.assertEqual([f["frame_index"] for f in obs["frames"]], frames)
                        self.assertEqual([f["frame_index"] for f in item["reports"][key]["frame_results"]], frames)
            for purpose, pool in pools.items():
                saved_binding = next(b for b in self.p["saved_control_scoring_reports"] if b["path"].endswith(purpose+".json"))
                saved = read_json(self.root/saved_binding["path"])
                self.assertEqual(pool["evaluation_reports"][:945], saved["evaluation_reports"])
                self.assertEqual(pool["aggregate_results"][:315], saved["aggregate_results"])
                self.assertEqual((len(pool["evaluation_reports"]), len(pool["aggregate_results"]), len(pool["paired_differences"])), (1485, 495, 540))
                self.assertEqual(len(pool["aggregate_paired_differences"]), 180)
                for paired in pool["paired_differences"]:
                    w = next(w for w in self.p["windows"] if w["purpose"] == purpose and w["possession_id"] == paired["possession_id"])
                    frames = set(range(w["start_frame_index"], w["end_frame_index"]+1))
                    self.assertTrue(set(paired["changed_emission_frames"]) <= frames)
                    self.assertTrue({f["frame_index"] for f in paired["changed_path_support"]} <= frames)
                    self.assertEqual(paired["control_ranking_commit"], experiment.PRIOR_COMMIT)
                    self.assertEqual(paired["context_ranking_commit"], COMMIT)
                for new in pool["evaluation_reports"][945:]:
                    self.assertEqual(new["context_metrics"]["frames_without_observed_boxes"], [new["window"]["end_frame_index"]])
                changed = copy.deepcopy(pool)
                changed["evaluation_reports"][0]["metrics"]["true_positive_count"] += 1
                changed["content_sha256"] = evaluation._pool_digest(changed)
                target = self.root/experiment.OUTPUT_ROOT/"evaluation"/f"{purpose}.json"
                original = target.read_bytes(); write_json(target, changed)
                with self.assertRaisesRegex(ValueError, "saved controls"):
                    evaluation.load_scoring_pools(self.root, self.m, self.p, COMMIT)
                target.write_bytes(original)
            self.assertEqual(preserved, {name: (self.root/name).read_bytes() for name in preserved})
            first = experiment.output_path(self.root, self.p["windows"][0], core.experiment_grid()[0])
            missing = experiment.output_path(self.root, self.p["windows"][-1], core.experiment_grid()[-1])
            value = read_json(first); value["observations"]["frames"][0]["ranking"]["winner"]["score"] += 1
            value["observations_content_sha256"] = canonical_sha256(value["observations"])
            write_json(first, value); missing.unlink()
            with self.assertRaises(ValueError):
                experiment.run_experiment(self.root, self.path)
            self.assertFalse(missing.exists())


class SourceBindingTests(unittest.TestCase):
    def test_opaque_source_hash_rejects_change_and_missing_without_video_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root/"data/clips/possession_001.mp4"
            target.parent.mkdir(parents=True); target.write_bytes(b"not video; hash fixture")
            p = {"windows": [{"source_video": file_binding(root, target)}]*2}
            experiment.verify_source_files(root, p)
            target.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "source-video"):
                experiment.verify_source_files(root, p)
            target.unlink()
            with self.assertRaises((ValueError, FileNotFoundError)):
                experiment.verify_source_files(root, p)


if __name__ == "__main__":
    unittest.main()

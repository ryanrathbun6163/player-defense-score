"""Synthetic crop/runner/scoring/review checks; no real inference or clip access."""
import copy
import json
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.ball_tracking import tiled_experiment as experiment
from src.ball_tracking import tiled_evaluation as evaluation
from src.ball_tracking import tiled_review as review
from src.ball_tracking.annotations import load_annotations
from src.ball_tracking.detections import BallDetection, load_detection_run
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.evaluation import evaluate_detections
from src.ball_tracking.temporal_experiment import file_binding, spec_digest
from src.ball_tracking.tiled_candidates import (
    candidate_run, combine_views, crop_views, make_frame, make_output, select_run, validate_output,
)
from test_ball_detection_visual_review import write_json
from test_ball_temporal_association import manifest_setup, fixture

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "e" * 40


def crop_result(view, points=()):
    detections = [BallDetection(i, 37, "sports ball", score, (x-2, y-2, x+2, y+2), (x, y)).to_dict()
                  for i, (x, y, score) in enumerate(points)]
    return {"view": view, "candidates": detections, "elapsed_seconds": .001, "cuda_peak_allocated_bytes": 128}


def setup_manifest(root):
    temporal_path, temporal = manifest_setup(root)
    proposal = read_json(ROOT / "configs/ball_tracking/proposals/rfdetr_medium_tiled_development_comparison_v0_1.json")
    proposal["windows"] = temporal["windows"]
    proposal["scoring_labels"] = temporal["scoring_labels"]
    proposal["saved_control_manifest"] = temporal["baseline"]
    proposal["frozen_detector_contract_source"] = temporal["baseline"]
    for key in ("design", "rationale"):
        path = root / proposal[key]["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic test document.\n")
        proposal[key] = file_binding(root, path)
    receipt_path = root / proposal["temporal_review_receipt"]["path"]
    write_json(receipt_path, {"human_visual_review": {"status": "completed", "reviewer_id": "ryan"},
                            "bound_evidence": {"experiment_manifest": file_binding(root, temporal_path)}})
    proposal["temporal_review_receipt"] = file_binding(root, receipt_path)
    proposal_path = root / "configs/ball_tracking/proposals/synthetic_crops.json"
    write_json(proposal_path, proposal)
    auth_path = root / "configs/ball_tracking/reviews/synthetic_crop_approval.json"
    m, approval = experiment.prepare_manifest_payloads(root, proposal_path, temporal_path, auth_path,
                                                      "Synthetic approval", "2026-09-19T12:00:00Z")
    write_json(auth_path, approval)
    path = root / "configs/ball_tracking/tiled_experiments/synthetic.json"
    write_json(path, m)
    return path, m, proposal


class FakeAdapter:
    def __init__(self, fail_at=None):
        self.calls = 0
        self.fail_at = fail_at

    def predict_frame(self, pixels):
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("synthetic interruption")
        assert pixels.shape == (648, 1152, 3) and pixels.dtype == np.uint8
        return (BallDetection(0, 37, "sports ball", .8, (80.25, 70.5, 84.25, 74.5), (82.25, 72.5)),)


def patches(root, path, stack, adapter=None):
    m, p, temporal, baseline = experiment.load_manifest(root, path)
    model = experiment.build_model_provenance(baseline.detector, code_commit=COMMIT, runtime_device="cuda:0 | synthetic")
    stack.enter_context(patch.object(experiment, "clean_commit", return_value=COMMIT))
    stack.enter_context(patch.object(experiment, "_tracked"))
    stack.enter_context(patch.object(experiment.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()))
    stack.enter_context(patch.object(experiment, "verify_source_video_contract"))
    stack.enter_context(patch.object(experiment, "inspect_runtime", return_value=(root / "synthetic.pth", model)))
    stack.enter_context(patch.object(experiment, "synchronize"))
    stack.enter_context(patch.object(experiment, "peak_memory", return_value=128))
    rgb = np.zeros((1080, 1920, 3), dtype=np.uint8)
    stack.enter_context(patch.object(experiment, "frames_from_video", side_effect=lambda root, run, wanted: ((f, rgb) for f in sorted(wanted))))
    fake = adapter or FakeAdapter()
    stack.enter_context(patch.object(experiment, "create_adapter", return_value=fake))
    return m, p, model, fake


class GeometryTests(unittest.TestCase):
    def setUp(self):
        _, raw = fixture([[(100, 100)]])
        self.raw = replace(raw, model_provenance=replace(raw.model_provenance,
                           target_class_id=37, target_class_name="sports ball", export_confidence_floor=.01))

    def test_complete_fixed_grid_and_no_label_access(self):
        coverage = np.zeros((1080, 1920), dtype=np.uint8)
        for view in crop_views():
            x0, y0, x1, y1 = view["xyxy_half_open_px"]
            coverage[y0:y1, x0:x1] += 1
        self.assertTrue(np.all(coverage >= 1))
        self.assertEqual(int(coverage[500, 900]), 4)
        records = [crop_result(v, [(10, 10, .8)]) for v in crop_views()]
        with patch.object(Path, "open", side_effect=AssertionError("geometry opened file")):
            value = combine_views(records, self.raw.source_video, self.raw.model_provenance)
        self.assertEqual([c["detection"]["center_xy_px"] for c in value], [[10., 10.], [10., 442.], [778., 10.], [778., 442.]])

    def test_duplicates_preserved_and_view_ties_deterministic(self):
        records = []
        for view in crop_views():
            x0, y0, _, _ = view["xyxy_half_open_px"]
            records.append(crop_result(view, [(900-x0, 500-y0, .8)]))
        result = combine_views(records, self.raw.source_video, self.raw.model_provenance)
        self.assertEqual(len(result), 4)
        self.assertEqual([r["view_ordinal"] for r in result], [0, 1, 2, 3])
        self.assertEqual([r["detection"]["candidate_index"] for r in result], [0, 1, 2, 3])
        self.assertTrue(all(r["detection"]["center_xy_px"] == [900., 500.] for r in result))

    def test_empty_views_and_right_bottom_boundary(self):
        records = [crop_result(v) for v in crop_views()]
        self.assertEqual(combine_views(records, self.raw.source_video, self.raw.model_provenance), [])
        records[3] = crop_result(crop_views()[3], [(1150, 646, .01)])
        result = combine_views(records, self.raw.source_video, self.raw.model_provenance)
        self.assertEqual(result[0]["detection"]["bbox_xyxy_px"], [1916., 1076., 1920., 1080.])

    def test_reject_invalid_crop_candidate_and_timing(self):
        records = [crop_result(v, [(10, 10, .8)]) for v in crop_views()]
        bad = []
        r = copy.deepcopy(records); r[1]["view"]["xyxy_half_open_px"][0] += 1; bad.append(r)
        r = copy.deepcopy(records); r.pop(); bad.append(r)
        r = copy.deepcopy(records); r[0]["candidates"][0]["confidence"] = .009; bad.append(r)
        r = copy.deepcopy(records); r[0]["candidates"][0]["center_xy_px"] = [200, 200]; bad.append(r)
        r = copy.deepcopy(records); r[0]["candidates"][0]["candidate_index"] = 2; bad.append(r)
        r = copy.deepcopy(records); r[0]["elapsed_seconds"] = float("nan"); bad.append(r)
        r = copy.deepcopy(records); r[0]["cuda_peak_allocated_bytes"] = True; bad.append(r)
        for r in bad:
            with self.subTest(r=r), self.assertRaises(ValueError):
                combine_views(r, self.raw.source_video, self.raw.model_provenance)

    def test_output_tampering_and_per_view_provenance(self):
        header = {"per_view_model_provenance": self.raw.model_provenance.to_dict()}
        records = [crop_result(v, [(10, 10, .8)]) for v in crop_views()]
        output = make_output(header, [make_frame(0, records, self.raw.source_video, self.raw.model_provenance)])
        validate_output(output, header, self.raw)
        view = candidate_run(self.raw, output)
        self.assertTrue(view.model_provenance.tiling_enabled)
        self.assertFalse(self.raw.model_provenance.tiling_enabled)
        broken = copy.deepcopy(output); broken["frames"][0]["candidates"][0]["detection"]["center_xy_px"][0] += 1
        broken["content_sha256"] = canonical_sha256({"header": header, "frames": broken["frames"]})
        with self.assertRaises(ValueError):
            validate_output(broken, header, self.raw)

    def test_top_one_preserves_original_index_and_threshold(self):
        labels, raw = fixture([[(400, 400, .5), (100, 100, .9)]])
        selected = select_run(raw, "top_one", .9)
        self.assertEqual(selected.frames[0].detections[0].candidate_index, 1)
        score = evaluation.score_one(labels, raw, "saved_whole_frame", "top_one", .5, 10., None, COMMIT)
        self.assertEqual(score["frame_results"][0]["matched_candidate_index"], 1)
        self.assertEqual(len(select_run(raw, "top_one", .95).frames[0].detections), 0)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path, self.m, self.p = setup_manifest(self.root)

    def test_exact_bound_manifest_and_label_blind_load(self):
        original = Path.open

        def guarded(path, *args, **kwargs):
            if "configs/ball_tracking/annotations" in path.as_posix():
                raise AssertionError("Inference loader opened labels")
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", guarded):
            loaded = experiment.load_manifest(self.root, self.path)
            inputs = experiment.load_inputs(self.root, loaded[2])
        self.assertEqual(len(inputs), 6)

    def test_tampered_approval(self):
        approval_path = self.root / self.m["authorization"]["path"]
        approval_path.write_text(approval_path.read_text() + " ")
        with self.assertRaises(ValueError):
            experiment.load_manifest(self.root, self.path)

    def test_holdout_or_new_grid_rejected_even_with_rebound_approval(self):
        proposal_path = self.root / self.m["proposal"]["path"]
        variants = []
        p = copy.deepcopy(self.p); p["windows"][0]["purpose"] = "test_holdout"; variants.append(p)
        p = copy.deepcopy(self.p); p["windows"][0]["start_frame_index"] += 1; variants.append(p)
        p = copy.deepcopy(self.p); p["crop_views"][0]["xyxy_half_open_px"][2] = 1200; variants.append(p)
        p = copy.deepcopy(self.p); p["confidence_thresholds"].pop(); variants.append(p)
        p = copy.deepcopy(self.p); p["selected_operating_point"] = .35; variants.append(p)
        for p in variants:
            write_json(proposal_path, p)
            auth_path = self.root / self.m["authorization"]["path"]
            m, auth = experiment.prepare_manifest_payloads(self.root, proposal_path, self.root / self.m["temporal_baseline"]["path"], auth_path, "Synthetic", "2026-09-19T12:00:00Z")
            write_json(auth_path, auth); write_json(self.path, m)
            with self.subTest(p=p), self.assertRaises(ValueError):
                experiment.load_manifest(self.root, self.path)

    def test_dirty_worktree_stops_before_source_runtime_or_inference(self):
        with patch.object(experiment, "clean_commit", side_effect=ValueError("dirty")), patch.object(experiment, "inspect_runtime") as runtime, patch.object(experiment, "verify_source_video_contract") as source:
            with self.assertRaisesRegex(ValueError, "dirty"):
                experiment.run_experiment(self.root, self.path)
            runtime.assert_not_called(); source.assert_not_called()
        self.assertFalse((self.root / experiment.OUTPUT_ROOT).exists())

    def test_dry_run_performs_no_inference_or_output(self):
        with ExitStack() as stack:
            _, _, _, fake = patches(self.root, self.path, stack)
            stack.enter_context(patch.object(experiment, "git", return_value=COMMIT))
            result = experiment.run_experiment(self.root, self.path, dry_run=True)
            self.assertEqual(result["new_model_calls"], 600)
            self.assertEqual(fake.calls, 0)
        self.assertFalse((self.root / experiment.OUTPUT_ROOT).exists())

    def test_nine_original_embargo_paths_are_enforced(self):
        parent = read_json(self.root / "configs/ball_tracking/experiments/rfdetr_medium_image_only_baseline_v0_1.json")
        for window in [w for w in parent["windows"] if w["execution_status"] == "annotation_pending_prediction_embargo"]:
            path = self.root / window["output_path"]
            write_json(path, {})
            try:
                with self.assertRaisesRegex(ValueError, "embargo"):
                    experiment.load_manifest(self.root, self.path)
            finally:
                path.unlink()


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path, self.m, self.p = setup_manifest(self.root)

    def test_600_calls_resume_scoring_and_control_parity(self):
        with ExitStack() as stack:
            m, p, model, fake = patches(self.root, self.path, stack)
            result = experiment.run_experiment(self.root, self.path)
            self.assertEqual(result["new_model_calls"], 600)
            self.assertEqual(fake.calls, 600)
            snapshot = {f: sha256_file(f) for f in (self.root / experiment.OUTPUT_ROOT).rglob("*.json")}
            self.assertEqual(experiment.run_experiment(self.root, self.path)["new_model_calls"], 0)
            self.assertEqual(fake.calls, 600)
            self.assertTrue(all(sha256_file(f) == digest for f, digest in snapshot.items()))
            scored = evaluation.score_experiment(self.root, self.path)
            self.assertEqual(scored["per_window_reports"], 1080)
            for binding in scored["reports"]:
                grid = read_json(self.root / binding["path"])
                self.assertEqual(len(grid["evaluation_reports"]), 540)
                self.assertEqual(len(grid["aggregate_results"]), 180)
                self.assertEqual(len(grid["paired_differences"]), 270)
                for r in grid["evaluation_reports"]:
                    c = r["config"]
                    if c["image_arm"] != "saved_whole_frame":
                        continue
                    w = next(w for w in p["windows"] if w["possession_id"] == r["possession_id"] and w["purpose"] == r["selection_purpose"])
                    label = next(l for l in p["scoring_labels"] if l["window_id"] == w["window_id"])
                    labels = load_annotations(self.root / label["annotation"]["path"])
                    raw = load_detection_run(self.root / w["detection"]["path"])
                    expected = evaluate_detections(labels, select_run(raw, c["selector"], c["confidence_threshold"]), confidence_threshold=c["confidence_threshold"], localization_radius_px=c["localization_radius_px"])
                    self.assertEqual(r["metrics"], {k: expected[k] for k in evaluation.METRICS})
                    self.assertEqual(r["frame_results"], expected["frame_results"])
            self.assertEqual(evaluation.score_experiment(self.root, self.path), scored)

    def test_partial_resume_and_tampered_checkpoint_refused_before_calls(self):
        fake = FakeAdapter(fail_at=3)
        with ExitStack() as stack:
            _, p, _, _ = patches(self.root, self.path, stack, fake)
            with self.assertRaisesRegex(RuntimeError, "interruption"):
                experiment.run_experiment(self.root, self.path)
            self.assertEqual(len(list((self.root / experiment.OUTPUT_ROOT).rglob("frame_*.json"))), 2)
            fake.fail_at = None
            self.assertEqual(experiment.run_experiment(self.root, self.path)["new_model_calls"], 598)
            path = experiment.checkpoint_path(self.root, p["windows"][0], p["windows"][0]["start_frame_index"], crop_views()[0])
            value = read_json(path); value["result"]["elapsed_seconds"] += 1; write_json(path, value)
            calls = fake.calls
            with self.assertRaisesRegex(ValueError, "checkpoint"):
                experiment.run_experiment(self.root, self.path)
            self.assertEqual(fake.calls, calls)

    def test_missing_source_frame_leaves_only_completed_checkpoints(self):
        with ExitStack() as stack:
            patches(self.root, self.path, stack)
            with patch.object(experiment, "frames_from_video", return_value=iter(())):
                with self.assertRaisesRegex(ValueError, "Incomplete source"):
                    experiment.run_experiment(self.root, self.path)
            self.assertFalse(any((self.root / experiment.OUTPUT_ROOT).rglob("candidates.json")))

    def test_scoring_tampered_global_mapping_rejected(self):
        with ExitStack() as stack:
            _, p, _, _ = patches(self.root, self.path, stack)
            experiment.run_experiment(self.root, self.path)
            path = experiment.output_path(self.root, p["windows"][0])
            value = read_json(path); value["frames"][0]["candidates"][0]["view_ordinal"] = 3
            value["content_sha256"] = canonical_sha256({"header": value["header"], "frames": value["frames"]})
            write_json(path, value)
            with self.assertRaises(ValueError):
                evaluation.score_experiment(self.root, self.path)

    def test_changed_execution_commit_is_not_accepted_as_resume(self):
        with ExitStack() as stack:
            _, _, model, _ = patches(self.root, self.path, stack)
            experiment.run_experiment(self.root, self.path)
            with patch.object(experiment, "inspect_runtime", return_value=(self.root / "synthetic.pth", replace(model, code_commit="f"*40))):
                with self.assertRaisesRegex(ValueError, "checkpoint"):
                    experiment.run_experiment(self.root, self.path)

    def test_complete_synthetic_review_and_final_frames(self):
        import cv2

        class FakeCapture:
            def __init__(self, path):
                self.index = 0
            def isOpened(self):
                return True
            def set(self, key, value):
                self.index = int(value); return True
            def get(self, key):
                return self.index
            def read(self):
                self.index += 1
                frame = np.zeros((1080, 1920, 3), np.uint8)
                cv2.circle(frame, (82, 72), 8, (0, 150, 240), -1)
                return True, frame
            def release(self):
                pass

        real_capture = cv2.VideoCapture
        with ExitStack() as stack:
            patches(self.root, self.path, stack)
            experiment.run_experiment(self.root, self.path)
            stack.enter_context(patch.object(cv2, "VideoCapture", side_effect=lambda path: FakeCapture(path) if "data/clips" in str(path).replace("\\", "/") else real_capture(path)))
            result = review.render_experiment(self.root, self.path)
            bundle = Path(result["bundle"])
            manifest = read_json(bundle / "manifest.json")
            self.assertEqual(len(manifest["assets"]), 1962)
            self.assertEqual(len(manifest["final_frames"]), 6)
            self.assertTrue(review.render_experiment(self.root, self.path)["reused"])
            first = bundle / manifest["assets"][0]["path"]
            first.write_bytes(first.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                review.validate_review_bundle(bundle, manifest["header"])


if __name__ == "__main__":
    unittest.main()

"""Synthetic-only temporal tests. No model or user source video is opened."""
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.ball_tracking import temporal_experiment as experiment
from src.ball_tracking import temporal_review as review
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.detections import BallDetectionRun
from src.ball_tracking.development_experiments import canonical_sha256, sha256_file
from src.ball_tracking.detector_experiments import load_detector_experiment
from src.ball_tracking.evaluation import evaluate_detections
from src.ball_tracking.temporal_association import AssociationConfig, associate, experiment_grid, validate_observations
from src.ball_tracking.temporal_evaluation import aggregate_temporal_reports, evaluate_observations
from test_ball_annotation_foundation import (
    detection, not_visible_frame, observed_frame, parse_detection_run, parse_reviewed_annotations,
)
from test_ball_detection_visual_review import reviewed_annotation_payload, detection_payload, write_json
from test_ball_development_experiment import manifest_fixture

COMMIT = "d" * 40


def fixture(points, labels=None):
    if labels is None:
        labels = parse_reviewed_annotations([observed_frame(i) for i in range(len(points))])
    raw = parse_detection_run(labels, {i: [detection(*p) for p in frame] for i, frame in enumerate(points)})
    return labels, raw


def manifest_setup(root):
    baseline_path, _, _ = manifest_fixture(root)
    baseline = load_detector_experiment(baseline_path)
    reviewed_windows = []
    for w in baseline.windows:
        payload = reviewed_annotation_payload(w, w.source_video)
        payload["window"]["selection_purpose"] = w.selection_purpose
        labels = BallAnnotationSet.from_mapping(payload)
        write_json(root / f"configs/ball_tracking/annotations/{w.annotation_set_id}.json", payload)
        path = root / w.output_path
        write_json(path, detection_payload(baseline, w, w.source_video, labels))
        reviewed_windows.append({"window_id": w.window_id, "purpose": w.selection_purpose,
                                 "possession_id": w.possession_id, "start_frame_index": w.start_frame_index,
                                 "end_frame_index": w.end_frame_index,
                                 "detection": experiment.file_binding(root, path)})
    visual_path = root / "configs/ball_tracking/reviews/temporal_synthetic_review.json"
    write_json(visual_path, {"schema_version": "ball_detection_development_visual_review_record/v0.1",
                            "experiment_id": baseline.experiment_id,
                            "human_visual_approval": {"status": "approved", "approved_by": "ryan"},
                            "bound_evidence": {"experiment_manifest": experiment.file_binding(root, baseline_path),
                                               "windows": reviewed_windows}})
    design = root / "docs/synthetic_design.md"
    design.parent.mkdir()
    design.write_text("Synthetic design fixture only.\n")
    approval = root / "configs/ball_tracking/reviews/temporal_synthetic_approval.json"
    m, auth = experiment.prepare_manifest_payloads(root, baseline_path, visual_path, design, approval,
                                                  "Synthetic test authorization", "2026-09-19T12:00:00Z")
    path = root / "configs/ball_tracking/temporal_experiments/synthetic.json"
    experiment.persist_once(approval, auth)
    experiment.persist_once(path, m)
    return path, m


class AssociationTests(unittest.TestCase):
    def test_full_grid_preserves_all_variants(self):
        grid = experiment_grid()
        self.assertEqual(len(grid), 54)
        self.assertEqual(len({c.variant_id for c in grid}), 54)
        self.assertEqual(sum(c.arm == "tracklets" for c in grid), 36)

    def test_confirmation_is_causal_and_singletons_expire(self):
        _, raw = fixture([[(100, 100, .8), (300, 300, .9)], [(102, 100, .8)], []])
        result = associate(raw, AssociationConfig("tracklets", .2, .01, 2), COMMIT)
        self.assertEqual([f["emitted_candidate_indices"] for f in result["frames"]], [[], [0], []])
        self.assertEqual(result["frames"][1]["confirmed_tracklet_ids"], [0])
        self.assertIn(1, result["frames"][2]["expired_tracklet_ids"])
        self.assertEqual(result["frames"][2]["output_state"], "no_accepted_observation")
        self.assertEqual(raw.frames[0].detections[1].center_xy_px, (300, 300))

    def test_short_gap_reconnects_without_coordinates_in_gap(self):
        _, raw = fixture([[(100, 100)], [(102, 100)], [], [], [(104, 100)]])
        result = associate(raw, AssociationConfig("tracklets", .2, .01, 2), COMMIT)
        self.assertEqual([f["emitted_candidate_indices"] for f in result["frames"]], [[], [0], [], [], [0]])
        self.assertEqual(result["frames"][-1]["associations"][0]["elapsed_frames"], 3)
        self.assertEqual(result["frames"][-1]["candidate_decisions"][0]["tracklet_id"], 0)

    def test_expired_gap_and_window_reset_need_confirmation(self):
        _, raw = fixture([[(100, 100)], [(101, 100)], [], [], [], [(104, 100)]])
        config = AssociationConfig("tracklets", .2, .01, 2)
        first = associate(raw, config, COMMIT)
        self.assertEqual(first["frames"][-1]["emitted_candidate_indices"], [])
        self.assertEqual(first["frames"][-1]["candidate_decisions"][0]["tracklet_id"], 1)
        self.assertEqual(associate(raw, config, COMMIT), first)

    def test_provisional_gap_does_not_confirm(self):
        _, raw = fixture([[(100, 100)], [], [(101, 100)]])
        value = associate(raw, AssociationConfig("tracklets", .2, .01, 2), COMMIT)
        self.assertTrue(all(not f["emitted_candidate_indices"] for f in value["frames"]))

    def test_ties_and_competing_edges_are_one_to_one(self):
        _, raw = fixture([[(90, 100), (110, 100)], [(100, 100), (100, 100)]])
        value = associate(raw, AssociationConfig("tracklets", .2, .01, 0), COMMIT)
        edges = value["frames"][1]["associations"]
        self.assertEqual([(e["tracklet_id"], e["candidate_index"]) for e in edges], [(0, 0), (1, 1)])
        self.assertEqual(value["frames"][1]["emitted_candidate_indices"], [0, 1])

    def test_inclusive_confidence_and_top_one_ties(self):
        _, raw = fixture([[(100, 100, .2), (200, 100, .2), (300, 100, .19)]])
        control = associate(raw, AssociationConfig("top_one", .2), COMMIT)
        self.assertEqual(control["frames"][0]["emitted_candidate_indices"], [0])
        self.assertEqual([d["disposition"] for d in control["frames"][0]["candidate_decisions"]],
                         ["emitted", "control_suppressed", "below_threshold"])

    def test_no_labels_in_association_and_wrong_high_confidence_control(self):
        labels, raw = fixture([[(400, 400, .95), (100, 100, .7)], [(900, 900, .95), (101, 100, .7)]])
        config = AssociationConfig("tracklets", .2, .01, 0)
        with patch.object(Path, "open", side_effect=AssertionError("Association opened a file")):
            value = associate(raw, config, COMMIT)
        tracked = evaluate_observations(labels, raw, value, 10, COMMIT)
        top = evaluate_observations(labels, raw, associate(raw, AssociationConfig("top_one", .2), COMMIT), 10, COMMIT)
        self.assertEqual(tracked["metrics"]["true_positive_count"], 1)
        self.assertEqual(top["metrics"]["true_positive_count"], 0)

    def test_hidden_frame_false_alarm_not_suppressed_with_label_knowledge(self):
        labels = parse_reviewed_annotations([observed_frame(0), not_visible_frame(1)])
        _, raw = fixture([[(100, 100)], [(100, 100)]], labels)
        value = associate(raw, AssociationConfig("tracklets", .2, .01, 0), COMMIT)
        report = evaluate_observations(labels, raw, value, 10, COMMIT)
        self.assertEqual(report["metrics"]["non_visible_false_alarm_count"], 1)
        self.assertIsNone(labels.annotations[1].geometry)

    def test_uncertainty_does_not_relax_radius(self):
        labels = parse_reviewed_annotations([observed_frame(0, uncertainty=9)])
        _, raw = fixture([[(115, 100)]], labels)
        report = evaluate_observations(labels, raw, associate(raw, AssociationConfig("raw", .2), COMMIT), 10, COMMIT)
        self.assertEqual(report["metrics"]["false_negative_count"], 1)

    def test_raw_arm_matches_existing_evaluator_and_empty_output_is_not_success(self):
        labels, raw = fixture([[(100, 100, .8), (300, 300, .4)], [], [(101, 100, .1)]])
        for radius in (5, 10, 30):
            report = evaluate_observations(labels, raw, associate(raw, AssociationConfig("raw", .2), COMMIT), radius, COMMIT)
            expected = evaluate_detections(labels, raw, confidence_threshold=.2, localization_radius_px=radius)
            for key in ("precision", "recall", "true_positive_count", "false_positive_count", "false_negative_count"):
                self.assertEqual(report["metrics"][key], expected[key])
        empty = evaluate_observations(labels, raw, associate(raw, AssociationConfig("raw", 1), COMMIT), 10, COMMIT)
        self.assertIsNone(empty["metrics"]["precision"])
        self.assertEqual(empty["metrics"]["recall"], 0)
        self.assertEqual(empty["temporal_metrics"]["longest_consecutive_missed_eligible_run"], 3)

    def test_malformed_configs_inputs_and_provenance_rejected(self):
        for args in (("bad", .2), ("raw", float("nan")), ("raw", True),
                     ("raw", .2, .01, 0), ("tracklets", .2, .01, True), ("tracklets", .2, 0, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                AssociationConfig(*args)
        _, raw = fixture([[(100, 100)]])
        with self.assertRaises(ValueError):
            associate(raw, AssociationConfig("raw", .2), "dirty")
        incomplete = replace(raw, frames=(replace(raw.frames[0], inference_status="not_run", failure_reason="pending", detections=None),))
        with self.assertRaisesRegex(ValueError, "complete"):
            associate(incomplete, AssociationConfig("raw", .2), COMMIT)

    def test_tampered_decisions_or_unknown_fields_are_rejected(self):
        _, raw = fixture([[(100, 100)], [(101, 100)]])
        good = associate(raw, AssociationConfig("tracklets", .2, .01, 0), COMMIT)
        for change in (lambda v: v["frames"][0]["emitted_candidate_indices"].append(0),
                       lambda v: v.update(extra=True),
                       lambda v: v.update(raw_detector_code_commit="a" * 40),
                       lambda v: v["frames"][1]["associations"][0].update(distance_px=0)):
            bad = copy.deepcopy(good)
            change(bad)
            with self.assertRaises(ValueError):
                validate_observations(bad, raw)

    def test_aggregate_rejects_duplicate_windows_and_mixed_pools(self):
        labels, raw = fixture([[(100, 100)]])
        r = evaluate_observations(labels, raw, associate(raw, AssociationConfig("raw", .2), COMMIT), 10, COMMIT)
        with self.assertRaises(ValueError):
            aggregate_temporal_reports([r, r])
        other = copy.deepcopy(r)
        other["selection_purpose"] = "challenge_evaluation"
        with self.assertRaises(ValueError):
            aggregate_temporal_reports([r, other])

    def test_future_frames_cannot_change_earlier_decisions(self):
        _, raw = fixture([[(100, 100)], [(101, 100)], [(102, 100)]])
        payload = raw.to_dict()
        payload["frames"][-1]["detections"][0]["center_xy_px"] = [800, 800]
        payload["frames"][-1]["detections"][0]["bbox_xyxy_px"] = [799, 799, 801, 801]
        changed = BallDetectionRun.from_mapping(payload)
        config = AssociationConfig("tracklets", .2, .01, 0)
        self.assertEqual(associate(raw, config, COMMIT)["frames"][:2], associate(changed, config, COMMIT)["frames"][:2])


class ManifestAndRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path, self.manifest = manifest_setup(self.root)

    def test_exact_scope_and_runtime_does_not_open_annotations(self):
        original = Path.open
        def guarded(path, *args, **kwargs):
            self.assertNotIn("annotations", path.parts)
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", guarded):
            m = experiment.load_manifest(self.root, self.path)
            runs = experiment.load_inputs(self.root, m)
        self.assertEqual(len(runs), 6)
        self.assertEqual(sum(len(r.frames) for r in runs), 150)

    def test_manifest_substitutions_are_rejected(self):
        changes = (lambda m: m["windows"].pop(),
                   lambda m: m["windows"][0].update(purpose="test_holdout"),
                   lambda m: m["windows"][0].update(start_frame_index=51),
                   lambda m: m["windows"][0]["detection"].update(path="../escape.json"),
                   lambda m: m["variants"].pop(),
                   lambda m: m.update(output_root="data/outputs/unapproved"),
                   lambda m: m.update(selected_operating_point=.35),
                   lambda m: m.update(extra=True))
        for change in changes:
            m = copy.deepcopy(self.manifest)
            change(m)
            write_json(self.path, m)
            with self.assertRaises(ValueError):
                experiment.load_manifest(self.root, self.path)

    def test_revoked_approval_changed_design_and_embargo_output_are_rejected(self):
        approval = self.root / self.manifest["authorization"]["path"]
        original = approval.read_bytes()
        approval.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            experiment.load_manifest(self.root, self.path)
        approval.write_bytes(original)
        parent = load_detector_experiment(self.root / self.manifest["baseline"]["path"]).parent
        sealed = next(w for w in parent.windows if w.selection_purpose == "test_holdout")
        write_json(self.root / sealed.output_path, {})
        with self.assertRaisesRegex(ValueError, "embargo"):
            experiment.load_manifest(self.root, self.path)

    def test_tampered_input_bytes_rejected(self):
        path = self.root / self.manifest["windows"][0]["detection"]["path"]
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            experiment.load_inputs(self.root, self.manifest)

    def test_runner_resume_and_tamper_refusal(self):
        runs = experiment.load_inputs(self.root, self.manifest)
        with patch.object(experiment, "preflight", return_value=(self.manifest, runs, COMMIT)), patch.object(experiment, "clean_commit", return_value=COMMIT):
            first = experiment.run_experiment(self.root, self.path)
            self.assertEqual(first["created_outputs"], 324)
            self.assertEqual(experiment.run_experiment(self.root, self.path)["created_outputs"], 0)
            path = experiment.output_path(self.root, self.manifest, self.manifest["windows"][0], experiment_grid()[0])
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.assertRaisesRegex(ValueError, "Refusing"):
                experiment.run_experiment(self.root, self.path)
            self.assertEqual(path.read_bytes(), original + b" ")

    def test_dirty_worktree_denied_before_association(self):
        with patch.object(experiment, "clean_commit", side_effect=ValueError("clean committed checkpoint")), patch.object(experiment, "associate") as call:
            with self.assertRaisesRegex(ValueError, "clean committed"):
                experiment.run_experiment(self.root, self.path)
            call.assert_not_called()
        self.assertFalse((self.root / experiment.OUTPUT_ROOT).exists())

    def test_six_window_scoring_and_raw_baseline_compatibility(self):
        runs = experiment.load_inputs(self.root, self.manifest)
        with patch.object(experiment, "preflight", return_value=(self.manifest, runs, COMMIT)), patch.object(experiment, "clean_commit", return_value=COMMIT):
            experiment.run_experiment(self.root, self.path)
        with patch.object(review, "preflight", return_value=(self.manifest, runs, COMMIT)), patch.object(review, "clean_commit", return_value=COMMIT):
            result = review.score_experiment(self.root, self.path)
        self.assertEqual(result["per_window_reports"], 1620)
        self.assertEqual(len(result["reports"]), 2)
        for binding in result["reports"]:
            report = json.loads((self.root / binding["path"]).read_text())
            self.assertEqual(len(report["aggregate_results"]), 270)
            self.assertEqual(len(report["evaluation_reports"]), 810)
            self.assertTrue(all(r["selection_purpose"] == report["selection_purpose"] for r in report["evaluation_reports"]))
            self.assertIsNone(report["quality_gate"])


class VisualTests(unittest.TestCase):
    def test_complete_synthetic_video_bundle_resume_and_corruption(self):
        import cv2
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "data/clips/possession_001.mp4"
            path.parent.mkdir(parents=True)
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (320, 180))
            self.assertTrue(writer.isOpened())
            for i in range(3):
                writer.write(np.full((180, 320, 3), 40 + i * 10, dtype=np.uint8))
            writer.release()
            labels = parse_reviewed_annotations([observed_frame(0), not_visible_frame(1), observed_frame(2)],
                                                width_px=320, height_px=180, frame_count=3,
                                                source_sha256=sha256_file(path))
            labels = replace(labels, window=replace(labels.window, selection_purpose="representative_evaluation"))
            _, raw = fixture([[(100, 100)], [(101, 100)], [(102, 100)]], labels)
            label_path = root / "configs/ball_tracking/annotations/synthetic.json"
            write_json(label_path, labels.to_dict())
            raw_path = root / "data/outputs/ball_tracking/detections/synthetic.json"
            write_json(raw_path, raw.to_dict())
            window = {"window_id": "synthetic", "purpose": "representative_evaluation",
                      "start_frame_index": 0, "end_frame_index": 2,
                      "detection": experiment.file_binding(root, raw_path)}
            manifest = {"windows": [window], "scoring_labels": [{"window_id": "synthetic", "annotation": experiment.file_binding(root, label_path)}],
                        "output_root": experiment.OUTPUT_ROOT, "authorization": None}
            reports = []
            for config in experiment_grid():
                if config.confidence_threshold not in (.2, .35):
                    continue
                obs = associate(raw, config, COMMIT)
                write_json(experiment.output_path(root, manifest, window, config),
                           {"experiment_spec_sha256": experiment.spec_digest(manifest), "input_detection_file": window["detection"], "observations": obs})
                reports.append(evaluate_observations(labels, raw, obs, 10.0, COMMIT))
            for purpose in ("representative_evaluation", "challenge_evaluation"):
                write_json(root / experiment.OUTPUT_ROOT / "evaluation" / f"{purpose}.json",
                           {"experiment_spec_sha256": experiment.spec_digest(manifest), "code_commit": COMMIT,
                            "evaluation_reports": reports if purpose == "representative_evaluation" else []})
            with patch.object(review, "preflight", return_value=(manifest, [raw], COMMIT)), patch.object(review, "_unchanged"):
                result = review.render_experiment(root, root / "synthetic_manifest.json")
                bundle = Path(result["bundle"])
                saved = json.loads((bundle / "manifest.json").read_text())
                self.assertEqual(len(saved["assets"]), 50)  # 3 frames x 8 PNGs x 2 views + 2 videos.
                self.assertEqual(saved["final_frames"][0]["frame_index"], 2)
                self.assertTrue(review.render_experiment(root, root / "synthetic_manifest.json")["reused"])
                asset = bundle / saved["assets"][0]["path"]
                asset.write_bytes(asset.read_bytes() + b"tampered")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    review.render_experiment(root, root / "synthetic_manifest.json")

    def test_all_six_panels_include_explicit_gaps_and_preserve_source(self):
        labels, raw = fixture([[(100, 100)], [(101, 100)]])
        source = np.full((1080, 1920, 3), 80, dtype=np.uint8)
        original = source.copy()
        variants = []
        for config in experiment_grid():
            if config.confidence_threshold != .2:
                continue
            value = associate(raw, config, COMMIT)
            score = evaluate_observations(labels, raw, value, 10, COMMIT)
            variants.append((config, value["frames"][1], score["frame_results"][1]))
        comparison, overlays, closeups = review.render_frame(source, labels.annotations[1], raw.frames[1], variants)
        self.assertEqual(comparison.shape, (840, 2400, 3))
        self.assertEqual(len(overlays), 6)
        self.assertTrue(all(o.shape[0] == 1128 for o in overlays))
        self.assertGreater(closeups.shape[0], 0)
        np.testing.assert_array_equal(source, original)

    def test_review_integrity_rejects_missing_final_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            header = {"windows": [{"window_id": "synthetic", "start_frame_index": 0, "end_frame_index": 0}]}
            write_json(path / "manifest.json", {"header": header, "assets": [], "final_frames": [], "human_visual_review": "pending"})
            with self.assertRaisesRegex(ValueError, "missing final"):
                review.validate_review_bundle(path, header)


if __name__ == "__main__":
    unittest.main()

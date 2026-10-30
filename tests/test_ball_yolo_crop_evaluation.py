"""Synthetic detector comparison: saved controls, full grids, accounting, resume."""
import copy
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from src.ball_tracking import crop_motion_evaluation as old_evaluation
from src.ball_tracking import crop_motion_factorial as old_selectors
from src.ball_tracking import yolo_crop_candidates as selectors
from src.ball_tracking import yolo_crop_evaluation as evaluation
from src.ball_tracking import yolo_crop_experiment as experiment
from src.ball_tracking import yolo11x_adapter as adapter
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.detections import BallDetectionRun
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.temporal_association import RADII, THRESHOLDS
from src.ball_tracking.temporal_experiment import file_binding, persist_once, spec_digest
from src.ball_tracking import tiled_candidates as tiled
from test_ball_annotation_foundation import (
    detection_run_payload, indeterminate_frame, not_visible_frame, observed_frame,
    parse_reviewed_annotations,
)
from test_ball_detection_visual_review import write_json
from test_ball_tiled_comparison import crop_result

COMMIT = "f" * 40
PURPOSES = ["representative_evaluation", "challenge_evaluation"]


def _points(offset, challenger, purpose):
    if offset == 2:
        return [(100, 100, .8)] if challenger else []
    if offset == 3:
        return [(100, 100, .03)]
    if offset == 4:
        return [(350, 150, .8)] if challenger else [(340, 150, .9), (350, 150, .8)]
    if offset == 5:
        return [(350, 150, .8)]
    if offset == 6:
        return [(106 if challenger else 103, 100, .8)]
    if offset == 7:
        return [] if challenger else [(100, 100, .8)]
    if offset == 8:
        return [(300+i*4, 160, .8) for i in range(21)] + [(100, 100, .4)]
    if offset == 1:
        return [(350, 150, .9), (100, 100, .8)]
    if purpose == PURPOSES[1] and offset == 10:
        return [(100, 100, .8)] if challenger else []
    return [(100, 100, .8), (101, 100, .6)]


def synthetic_setup(root):
    """Create only synthetic JSON; no source media, runtime or model is opened."""
    p = {"pool_separation": PURPOSES, "windows": [], "scoring_labels": [],
         "saved_control_outputs": [], "saved_control_scoring_reports": [], "inference_source_frames": []}
    runtime = root / "data/outputs/ball_tracking/synthetic_runtime.json"
    write_json(runtime, {"synthetic_only": True})
    proposal = root / "configs/ball_tracking/proposals/synthetic_yolo.json"
    native_manifest = root / "data/outputs/ball_tracking/synthetic_native_manifest.json"
    write_json(proposal, {"synthetic_only": True})
    write_json(native_manifest, {"synthetic_only": True})
    p["reused_native_review_manifest"] = file_binding(root, native_manifest)
    m = {"runtime": file_binding(root, runtime), "output_root": experiment.OUTPUT_ROOT,
         "proposal": file_binding(root, proposal), "authorization": {"synthetic_only": True}}
    path = root / "configs/ball_tracking/yolo_crop_experiments/synthetic.json"
    write_json(path, m)
    saved = {purpose: [] for purpose in PURPOSES}
    models = {}
    for number, start, end in ((1, 50, 74), (1, 200, 224), (2, 250, 274),
                               (2, 25, 49), (3, 300, 324), (3, 150, 174)):
        purpose = PURPOSES[len(p["windows"]) % 2]
        pid = f"possession_{number:03d}"
        identity = f"{pid}_{start}_{purpose}"
        annotations = [not_visible_frame(i) if i-start == 4 else indeterminate_frame(i) if i-start == 9
                       else observed_frame(i, uncertainty=4) for i in range(start, end+1)]
        labels = parse_reviewed_annotations(annotations, possession_id=pid, annotation_set_id=identity)
        label_payload = labels.to_dict()
        label_payload["window"]["selection_purpose"] = purpose
        labels = BallAnnotationSet.from_mapping(label_payload)
        label_path = root / f"configs/ball_tracking/annotations/{identity}.json"
        write_json(label_path, label_payload)
        raw = BallDetectionRun.from_mapping(detection_run_payload(labels, model_overrides={
            "target_class_id": 37, "target_class_name": "sports ball", "export_confidence_floor": .01}))
        raw_path = root / f"data/outputs/ball_tracking/detections/{identity}.json"
        write_json(raw_path, raw.to_dict())
        old_frames = []
        for frame in range(start, end+1):
            records = [crop_result(v, _points(frame-start, False, purpose) if i == 0 else ())
                       for i, v in enumerate(tiled.crop_views())]
            old_frames.append(tiled.make_frame(frame, records, raw.source_video, raw.model_provenance))
        old_payload = tiled.make_output({"per_view_model_provenance": raw.model_provenance.to_dict()}, old_frames)
        crop_path = root / f"data/outputs/ball_tracking/tiled_development/{identity}/candidates.json"
        write_json(crop_path, old_payload)
        old_run = tiled.candidate_run(raw, old_payload)
        w = {"window_id": identity, "purpose": purpose, "possession_id": pid,
             "source_video": raw.source_video.to_dict(), "start_frame_index": start, "end_frame_index": end,
             "annotation_set_id": identity, "detection_run_id": raw.detection_run_id,
             "detection": file_binding(root, raw_path), "crop_candidates": file_binding(root, crop_path)}
        p["windows"].append(w)
        p["scoring_labels"].append({"window_id": identity, "annotation": file_binding(root, label_path)})
        for c in old_selectors.experiment_grid():
            obs = old_selectors.rank_candidates(old_run, c, experiment.PRIOR_COMMIT)
            if c.arm in evaluation.CONTROL_ARMS:
                target = root / f"data/outputs/ball_tracking/crop_motion_factorial/synthetic/{identity}/{c.variant_id}.json"
                write_json(target, {"observations": obs})
                p["saved_control_outputs"].append(file_binding(root, target))
            for radius in RADII:
                saved[purpose].append(old_evaluation._evaluate_validated(labels, old_run, obs, radius, experiment.PRIOR_COMMIT))
        model = replace(raw.model_provenance, model_name=adapter.MODEL_NAME, package_name="ultralytics", package_version=adapter.PACKAGE_VERSION,
                        code_commit=COMMIT, input_width_px=640, input_height_px=640, resize_mode=adapter.RESIZE_MODE,
                        weights_identifier=adapter.WEIGHTS_IDENTIFIER, weights_sha256=adapter.WEIGHTS_SHA256,
                        precision="float32", device="cuda:0 | synthetic test", postprocessing_description=adapter.POSTPROCESSING)
        models[identity] = model
        source_frames = [{"window_id": identity, "frame_index": f,
                          "source_png": {"path": f"data/outputs/ball_tracking/synthetic/{identity}/unmarked_source/frame_{f:06d}.png", "sha256": "a"*64}}
                         for f in range(start, end+1)]
        p["inference_source_frames"].extend(source_frames)
        header = experiment.make_header(m, w, model, source_frames)
        frames = []
        for record in source_frames:
            f = record["frame_index"]
            views = []
            for i, view in enumerate(tiled.crop_views()):
                points = [(float(x), float(y), float(score)) for x, y, score in _points(f-start, True, purpose)] if i == 0 else ()
                result = crop_result(view, points)
                candidates = result["candidates"]
                prediction = {"candidates": candidates, "postprocessing": {
                    "source_class_id": 32, "returned_candidates": [{"postprocessor_index": j,
                        "bbox_xyxy_px": c["bbox_xyxy_px"], "confidence": c["confidence"], "source_class_id": 32}
                        for j, c in enumerate(candidates)],
                    "exported_candidate_sources": [{"candidate_index": j, "postprocessor_index": j} for j in range(len(candidates))],
                    "cap_saturated": False, "input_transform": adapter.INPUT_TRANSFORM},
                    "forward_accounting": {"synthetic_forwards": 1, "project_attempts": 1,
                        "project_forwards": 1, "this_project_attempt_forwards": 1, "preparation_complete": True}}
                views.append({"view": view, "prediction": prediction,
                              "elapsed_seconds": .001, "cuda_peak_allocated_bytes": 128, "attempt_id": f"synthetic-{identity}-{f}-{i}"})
            frames.append(selectors.make_frame(f, record["source_png"], views, raw.source_video, model))
        payload = selectors.make_output(header, frames)
        persist_once(experiment.candidate_path(root, w), payload)
        run = selectors.candidate_run(payload)
        for c in selectors.experiment_grid():
            obs = selectors.select_candidates(run, c, COMMIT)
            persist_once(experiment.output_path(root, w, c), {"experiment_spec_sha256": spec_digest(m),
                "input_candidates": file_binding(root, experiment.candidate_path(root, w)),
                "candidate_content_sha256": payload["content_sha256"], "observations_content_sha256": canonical_sha256(obs),
                "observations": obs})
    for purpose, reports in saved.items():
        aggregates = [old_evaluation.aggregate([r for r in reports if r["variant_id"] == c.variant_id and r["localization_radius_px"] == radius])
                      for c in old_selectors.experiment_grid() for radius in RADII]
        target = root / f"data/outputs/ball_tracking/crop_motion_factorial/synthetic/evaluation/{purpose}.json"
        write_json(target, {"schema_version": "ball_crop_motion_pool/v0.1", "purpose": purpose,
                           "code_commit": experiment.PRIOR_COMMIT, "evaluation_reports": reports, "aggregate_results": aggregates,
                           "selected_operating_point": None, "quality_gate": None})
        p["saved_control_scoring_reports"].append(file_binding(root, target))
    return path, m, p, next(iter(models.values()))


def evaluation_patches(root, path, m, p, model, stack):
    stack.enter_context(patch.object(evaluation, "preflight", return_value=(m, p, [], COMMIT)))
    stack.enter_context(patch.object(evaluation, "unchanged"))
    stack.enter_context(patch.object(experiment, "inspect_runtime", return_value=(root / "synthetic.pt", model)))


def forbid_legacy(stack):
    stack.enter_context(patch.object(old_selectors, "rank_candidates", side_effect=AssertionError("old selector called")))
    stack.enter_context(patch.object(old_selectors, "validate_observations", side_effect=AssertionError("old selector validator called")))
    stack.enter_context(patch.object(old_evaluation, "evaluate_observations", side_effect=AssertionError("old score called")))
    stack.enter_context(patch.object(old_evaluation, "_evaluate_validated", side_effect=AssertionError("old score called")))
    stack.enter_context(patch.object(experiment, "create_adapter", side_effect=AssertionError("model constructed")))
    stack.enter_context(patch.object(experiment, "read_source_png", side_effect=AssertionError("image opened")))
    stack.enter_context(patch.object(selectors, "select_candidates", side_effect=AssertionError("selection repeated")))


class FullSavedComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.path, cls.m, cls.p, cls.model = synthetic_setup(cls.root)
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        evaluation_patches(cls.root, cls.path, cls.m, cls.p, cls.model, cls.stack)
        forbid_legacy(cls.stack)
        cls.saved_bytes = {b["path"]: (cls.root/b["path"]).read_bytes()
                           for b in [*cls.p["saved_control_outputs"], *cls.p["saved_control_scoring_reports"]]}
        with patch.object(evaluation, "evaluate_detections", wraps=evaluation.evaluate_detections) as scorer:
            cls.summary = evaluation.score_experiment(cls.root, cls.path)
            cls.score_calls = scorer.call_count
        cls.pools = evaluation.load_scoring_pools(cls.root, cls.m, cls.p, COMMIT)

    @classmethod
    def tearDownClass(cls):
        cls.stack.close()
        cls.temp.cleanup()

    def test_full_grid_counts_810_new_810_reused_and_270_aggregates_per_pool(self):
        self.assertEqual(self.score_calls, 810)
        self.assertEqual(self.summary["per_window_reports"], 1620)
        self.assertEqual(self.summary["aggregate_cells_per_pool"], 270)
        self.assertEqual(self.summary["saved_controls_reranked"], 0)
        self.assertEqual(self.summary["saved_controls_rescored"], 0)
        self.assertEqual(len(self.p["saved_control_outputs"]), 162)
        self.assertEqual(len(list((self.root/experiment.OUTPUT_ROOT).glob("*/*.json"))), 170)
        for pool in self.pools.values():
            self.assertEqual(len(pool["evaluation_reports"]), 810)
            self.assertEqual(len(pool["aggregate_results"]), 270)
            self.assertEqual(len(pool["paired_differences"]), 405)
            self.assertEqual(len(pool["loss_decomposition"]), 810)
            self.assertEqual(len(pool["aggregate_paired_differences"]), 135)
            self.assertEqual({r["config"]["confidence_threshold"] for r in pool["evaluation_reports"]}, set(THRESHOLDS))
            self.assertEqual({r["localization_radius_px"] for r in pool["evaluation_reports"]}, set(RADII))

    def test_saved_control_bytes_reports_and_original_commits_preserved(self):
        for path, content in self.saved_bytes.items():
            self.assertEqual((self.root/path).read_bytes(), content)
        for purpose, pool in self.pools.items():
            original = read_json(self.root / next(b["path"] for b in self.p["saved_control_scoring_reports"] if purpose in b["path"]))
            self.assertEqual(pool["evaluation_reports"][:405], [r for r in original["evaluation_reports"] if r["config"]["arm"] in evaluation.CONTROL_ARMS])
            self.assertEqual(pool["aggregate_results"][:135], [r for r in original["aggregate_results"] if r["config"]["arm"] in evaluation.CONTROL_ARMS])
            self.assertEqual({r["evaluator_code_commit"] for r in pool["evaluation_reports"][:405]}, {experiment.PRIOR_COMMIT})
            self.assertEqual({r["evaluator_code_commit"] for r in pool["evaluation_reports"][405:]}, {COMMIT})

    def test_mapped_yolo_model_provenance_and_uncertainty_are_diagnostic(self):
        report = next(r for r in self.pools[PURPOSES[0]]["evaluation_reports"] if r["config"]["arm"] == selectors.ARMS[0]
                      and r["config"]["confidence_threshold"] == .2 and r["localization_radius_px"] == 5)
        self.assertEqual(report["input_model_provenance"]["target_class_id"], 37)
        self.assertEqual(report["input_model_provenance"]["package_name"], "ultralytics")
        self.assertIn("class32 sports ball mapped to COCO category37", report["input_model_provenance"]["postprocessing_description"])
        frame = report["frame_results"][6]
        self.assertEqual(frame["false_negative_count"], 1)  # raw distance 6 > 5, despite uncertainty 4
        other = next(r for r in self.pools[PURPOSES[0]]["evaluation_reports"] if r["variant_id"] == report["variant_id"]
                     and r["possession_id"] == report["possession_id"] and r["localization_radius_px"] == 10)
        self.assertEqual(other["frame_results"][6]["matched_center_error_px"], 6)
        self.assertEqual(other["frame_results"][6]["matched_effective_center_error_px"], 2)

    def test_losses_separate_floor_confidence_selector_and_hidden_states(self):
        pool = self.pools[PURPOSES[0]]
        loss = next(r for r in pool["loss_decomposition"] if r["possession_id"] == "possession_001"
                    and r["config"]["arm"] == selectors.ARMS[2] and r["config"]["confidence_threshold"] == .2 and r["radius_px"] == 10)
        self.assertEqual(loss["confidence_filter_lost_frames"], [53])
        self.assertEqual(loss["selector_lost_frames"], [58])
        self.assertEqual(loss["no_exported_candidate_at_floor_frames"], [55, 57])
        self.assertEqual(loss["hidden_false_alarm_frames"], [54])
        self.assertEqual(loss["false_negative_frames"], [53, 55, 57, 58])
        self.assertNotIn(59, loss["false_negative_frames"])  # indeterminate is unscored
        self.assertIn("cannot be separated", loss["unavailability_semantics"])

    def test_paired_gains_losses_hidden_duplicates_and_localization_have_correct_sign(self):
        pair = next(r for r in self.pools[PURPOSES[0]]["paired_differences"] if r["possession_id"] == "possession_001"
                    and r["config"]["arm"] == selectors.ARMS[0] and r["config"]["confidence_threshold"] == .2 and r["radius_px"] == 10)
        self.assertEqual(pair["newly_recovered_frames"], [52])
        self.assertEqual(pair["newly_lost_frames"], [57])
        self.assertEqual(pair["true_positive_delta"], 0)
        self.assertEqual(pair["hidden_false_alarm_delta"], -1)
        self.assertEqual(next(f for f in pair["shared_match_localization_changes"] if f["frame_index"] == 56)["center_error_delta_px"], 3)
        self.assertEqual(len(pair["frame_comparisons"]), 25)
        self.assertNotIn("changed_candidate_indices", pair)  # IDs are model-scoped

    def test_pool_window_identity_prevents_representative_challenge_collision(self):
        combined = [r for pool in self.pools.values() for r in pool["evaluation_reports"]]
        pairs, losses = evaluation.paired_differences(combined)
        self.assertEqual((len(pairs), len(losses)), (810, 1620))
        challenge = next(r for r in pairs if r["possession_id"] == "possession_001" and r["selection_purpose"] == PURPOSES[1]
                         and r["config"]["arm"] == selectors.ARMS[0] and r["config"]["confidence_threshold"] == .2 and r["radius_px"] == 10)
        self.assertEqual(challenge["newly_recovered_frames"], [202, 210])
        self.assertEqual(challenge["newly_lost_frames"], [207])

    def test_complete_resume_and_review_load_call_no_scorer_or_selector(self):
        before = [sha256_file(self.root/b["path"]) for b in self.summary["reports"]]
        with patch.object(evaluation, "evaluate_detections", side_effect=AssertionError("unexpected rescoring")):
            self.assertEqual(evaluation.score_experiment(self.root, self.path), self.summary)
            self.assertEqual(evaluation.load_scoring_pools(self.root, self.m, self.p, COMMIT), self.pools)
        self.assertEqual(before, [sha256_file(self.root/b["path"]) for b in self.summary["reports"]])

    def test_actual_review_preparation_joins_saved_reports_and_six_window_outputs(self):
        from src.ball_tracking import yolo_crop_review as review
        import cv2
        inputs = [{"window": w, "model": self.model} for w in self.p["windows"]]
        with patch.object(experiment, "preflight", return_value=(self.m, self.p, inputs, COMMIT)), \
                patch.object(experiment, "unchanged"), patch.object(review, "load_reused_assets", return_value=[]), \
                patch.object(evaluation, "evaluate_detections", side_effect=AssertionError("review scored")), \
                patch.object(evaluation, "score_experiment", side_effect=AssertionError("review scored")), \
                patch.object(cv2, "VideoCapture", side_effect=AssertionError("review decoded video")):
            prepared = review._prepare_review(self.root, self.path)
        self.assertEqual(len(prepared.windows), 6)
        self.assertEqual(prepared.header["confidence_views"], [.2, .35])
        for row in prepared.windows:
            self.assertEqual(len(row["run"].frames), 25)
            self.assertEqual(len(row["reports"]), 12)
            self.assertEqual(set(row["reports"]), set(row["observations"]))
            for key, report in row["reports"].items():
                self.assertEqual(report["observations_content_sha256"], canonical_sha256(row["observations"][key]))
                self.assertEqual(len(report["frame_results"]), 25)

    def test_partial_resume_scores_only_missing_pool(self):
        target = evaluation._pool_path(self.root, PURPOSES[1])
        original = target.read_bytes()
        target.unlink()
        try:
            with patch.object(evaluation, "evaluate_detections", wraps=evaluation.evaluate_detections) as scorer:
                result = evaluation.score_experiment(self.root, self.path)
            self.assertEqual(scorer.call_count, 405)
            self.assertEqual(result, self.summary)
            self.assertEqual(target.read_bytes(), original)
        finally:
            target.write_bytes(original)

    def test_tampered_existing_pool_rejected_before_missing_output_or_scoring(self):
        first, second = [evaluation._pool_path(self.root, purpose) for purpose in PURPOSES]
        originals = [first.read_bytes(), second.read_bytes()]
        value = read_json(first)
        value["evaluation_reports"][405]["temporal_metrics"]["missing_frame_count"] += 1
        value["content_sha256"] = evaluation._pool_digest(value)
        write_json(first, value)
        second.unlink()
        try:
            with patch.object(evaluation, "evaluate_detections", side_effect=AssertionError("scored before tamper rejection")):
                with self.assertRaisesRegex(ValueError, "missing runs"):
                    evaluation.score_experiment(self.root, self.path)
            self.assertFalse(second.exists())
        finally:
            first.write_bytes(originals[0])
            second.write_bytes(originals[1])

    def test_missing_duplicate_mixed_label_and_invalid_loss_cells_rejected(self):
        reports = self.pools[PURPOSES[0]]["evaluation_reports"]
        for broken in (reports[:-1], [*reports, reports[-1]]):
            with self.assertRaises(ValueError):
                evaluation.paired_differences(broken)
        broken = copy.deepcopy(reports)
        broken[405]["annotation_content_sha256"] = "e"*64
        with self.assertRaisesRegex(ValueError, "annotations"):
            evaluation.paired_differences(broken)
        broken = copy.deepcopy(reports)
        top_one = next(r for r in broken if r["config"]["arm"] == selectors.ARMS[1] and r["localization_radius_px"] == 5)
        top_one["frame_results"][5]["matched_candidate_index"] = 0
        top_one["frame_results"][5]["false_negative_count"] = 0
        with self.assertRaisesRegex(ValueError, "exceed"):
            evaluation.paired_differences(broken)

    def test_tampered_control_binding_new_observation_and_annotation_rejected(self):
        files = [self.root/self.p["saved_control_outputs"][0]["path"],
                 experiment.output_path(self.root, self.p["windows"][0], selectors.experiment_grid()[0]),
                 self.root/self.p["scoring_labels"][0]["annotation"]["path"]]
        for target in files:
            original = target.read_bytes()
            try:
                value = read_json(target)
                value["tampered"] = True
                write_json(target, value)
                with self.assertRaises(ValueError):
                    evaluation.load_scoring_pools(self.root, self.m, self.p, COMMIT)
            finally:
                target.write_bytes(original)

    def test_rebound_empty_or_lower_ranked_saved_selection_rejected_without_reselection(self):
        w = self.p["windows"][0]
        run, _, digest = experiment.load_candidate_run(self.root, self.m, self.p, w, COMMIT, model=self.model)
        for arm in selectors.ARMS[1:]:
            config = selectors.SelectorConfig(arm, .2)
            target = experiment.output_path(self.root, w, config)
            original = target.read_bytes()
            for indices in ([], [1]):
                value = read_json(target)
                frame = value["observations"]["frames"][0]
                frame["emitted_candidate_indices"] = indices
                frame["output_state"] = "tentative_observation" if indices else "no_accepted_observation"
                frame["decision_reason"] = "simple_selector_emitted" if indices else "no_qualifying_candidate"
                for decision in frame["candidate_decisions"]:
                    decision["disposition"] = "emitted" if decision["candidate_index"] in indices else "outside_selector_cap"
                value["observations_content_sha256"] = canonical_sha256(value["observations"])
                write_json(target, value)
                try:
                    with self.assertRaisesRegex(ValueError, "exact qualifying confidence prefix"):
                        experiment.load_observations(self.root, self.m, self.p, w, run, digest, config, COMMIT, rederive=False)
                finally:
                    target.write_bytes(original)

    def test_changed_aggregate_pair_partition_and_gate_rejected_even_with_new_digest(self):
        target = evaluation._pool_path(self.root, PURPOSES[0])
        original = target.read_bytes()
        def aggregate_change(value):
            value["aggregate_results"][135]["per_window"].append(value["aggregate_results"][135]["per_window"][0])
        def pair_change(value):
            value["paired_differences"][0]["newly_recovered_frames"] = []
        def partition_change(value):
            value["loss_decomposition"][405]["false_negative_frames"] = []
        def gate_change(value):
            value["selected_operating_point"] = .2
        for change in (aggregate_change, pair_change, partition_change, gate_change):
            value = read_json(target)
            change(value)
            value["content_sha256"] = evaluation._pool_digest(value)
            write_json(target, value)
            try:
                with self.assertRaises(ValueError):
                    evaluation.load_scoring_pools(self.root, self.m, self.p, COMMIT)
            finally:
                target.write_bytes(original)

    def test_new_saved_report_candidate_provenance_and_frame_binding_rejected(self):
        value = copy.deepcopy(self.pools[PURPOSES[0]]["evaluation_reports"][405])
        saved = evaluation._saved_pools(self.root, self.p)
        evidence = evaluation._load_evidence(self.root, self.m, self.p, COMMIT, saved)
        labels, run, observations, _ = evidence[self.p["windows"][0]["window_id"]]
        obs = observations[value["variant_id"]]
        value["input_candidate_content_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "provenance"):
            evaluation._bind_report(value, labels, run, obs)
        value["input_candidate_content_sha256"] = obs["input_candidate_content_sha256"]
        value["frame_results"][0]["matched_candidate_index"] = 999
        with self.assertRaisesRegex(ValueError, "selected observations"):
            evaluation._bind_report(value, labels, run, obs)


if __name__ == "__main__":
    unittest.main()

"""Artificial-only checks for fixed geometric corroboration, with no file IO."""
import copy
import math
import unittest
from dataclasses import replace
from unittest.mock import patch

from src.ball_tracking import crop_cross_detector_corroboration as corroboration
from src.ball_tracking.development_experiments import canonical_sha256
from test_ball_annotation_foundation import (
    detection, observed_frame, parse_detection_run, parse_reviewed_annotations,
)

COMMIT = "d" * 40


def run_fixture(points, detector="rfdetr", start=0, labels=None):
    """Build only artificial typed inputs; point=(x,y,confidence[,half_size])."""
    if labels is None:
        labels = parse_reviewed_annotations(
            [observed_frame(start + i) for i in range(len(points))],
            source_path="data/synthetic/corroboration.mp4")
    if detector not in ("rfdetr", "yolo"):
        raise ValueError("Unknown artificial detector namespace")
    records = {}
    for offset, frame in enumerate(points):
        records[start + offset] = []
        for point in sorted(frame, key=lambda p: -p[2]):
            value = detection(*point[:3], half_size=point[3] if len(point) == 4 else 5.0)
            value.update(class_id=37, class_name="sports ball")
            records[start + offset].append(value)
    return parse_detection_run(labels, records, detection_run_id="synthetic_" + detector,
                               model_overrides={
        "model_name": "RF-DETR Medium COCO" if detector == "rfdetr" else "Ultralytics YOLO11x Detect COCO",
        "package_name": "rfdetr" if detector == "rfdetr" else "ultralytics",
        "weights_identifier": "artificial_no_model_loaded_" + detector,
        "weights_sha256": ("b" if detector == "rfdetr" else "e") * 64,
        "target_class_id": 37, "target_class_name": "sports ball", "tiling_enabled": True,
        "export_confidence_floor": 0.0,
        "postprocessing_description": "Artificial fixtures; no detector runtime or scientific pixels",
    })


def fixture(rf_points, yolo_points, start=0, labels=None):
    return (run_fixture(rf_points, "rfdetr", start, labels),
            run_fixture(yolo_points, "yolo", start, labels))


def reseal(value):
    """A self digest alone is not authentication; use for adversarial structure checks."""
    value["content_sha256"] = canonical_sha256({k: v for k, v in value.items() if k != "content_sha256"})
    return value


class CorroborationSelectorTests(unittest.TestCase):
    def select(self, rf_points, yolo_points):
        rf, yolo = fixture(rf_points, yolo_points)
        result = corroboration.select_candidates(rf, yolo, COMMIT)
        corroboration.validate_observations(result, rf, yolo)
        return rf, yolo, result

    def test_exact_half_iou_inclusive_and_no_plus_one(self):
        self.assertEqual(corroboration.box_iou((0, 0, 3, 2), (1, 0, 4, 2)), .5)
        self.assertLess(corroboration.box_iou((0, 0, 3, 2),
                                            (math.nextafter(1.0, math.inf), 0, 4, 2)), .5)
        rf, yolo = fixture([[(100, 100, .9)]], [[(100, 100, .9)]])
        r = replace(rf.frames[0].detections[0], bbox_xyxy_px=(0., 0., 3., 2.), center_xy_px=(1.5, 1.))
        y = replace(yolo.frames[0].detections[0], bbox_xyxy_px=(1., 0., 4., 2.), center_xy_px=(2.5, 1.))
        rf = replace(rf, frames=(replace(rf.frames[0], detections=(r,)),))
        yolo = replace(yolo, frames=(replace(yolo.frames[0], detections=(y,)),))
        result = corroboration.select_candidates(rf, yolo, COMMIT)
        self.assertEqual(result["frames"][0]["emitted_candidate_indices"], [0])
        self.assertEqual(result["frames"][0]["candidate_decisions"][0]["maximum_iou"], .5)

    def test_disjoint_touching_identical_and_contained_geometry(self):
        self.assertEqual(corroboration.box_iou((0, 0, 2, 2), (2, 0, 4, 2)), 0.)
        self.assertEqual(corroboration.box_iou((0, 0, 2, 2), (5, 5, 6, 6)), 0.)
        self.assertEqual(corroboration.box_iou((0, 0, 2, 2), (0, 0, 2, 2)), 1.)
        self.assertEqual(corroboration.box_iou((0, 0, 4, 4), (1, 1, 3, 3)), .25)

    def test_empty_yolo_is_missing_not_visibility(self):
        _, _, result = self.select([[(100, 100, .9)]], [[]])
        frame = result["frames"][0]
        decision = frame["candidate_decisions"][0]
        self.assertEqual(frame["emitted_candidate_indices"], [])
        self.assertEqual(frame["output_state"], "no_accepted_observation")
        self.assertEqual((decision["maximum_iou"], decision["witness_yolo_original_index"],
                          decision["supporter_count"], decision["supported"]), (None, None, 0, False))
        self.assertIn("not a visibility label", result["score_semantics"])

    def test_empty_rf_and_both_empty(self):
        for yolo in ([], [(100, 100, .5)]):
            _, _, result = self.select([[]], [yolo])
            self.assertEqual(result["frames"][0]["candidate_decisions"], [])
            self.assertEqual(result["frames"][0]["emitted_candidates"], [])

    def test_both_inclusive_confidence_floors(self):
        _, _, result = self.select([[(100, 100, .01), (300, 100, .009)]],
                                   [[(100, 100, .01), (300, 100, .009)]])
        frame = result["frames"][0]
        self.assertEqual(frame["emitted_candidate_indices"], [0])
        self.assertEqual(frame["candidate_decisions"][1]["disposition"], "below_threshold")
        _, _, result = self.select([[(100, 100, .9)]], [[(100, 100, .009)]])
        self.assertEqual(result["frames"][0]["emitted_candidate_indices"], [])

    def test_supported_candidate_below_rank_twenty_is_retained(self):
        points = [(100 + 25 * i, 100, .9 - .02 * i) for i in range(25)]
        _, _, result = self.select([points], [[(700, 100, .8)]])
        frame = result["frames"][0]
        self.assertEqual(len(frame["candidate_decisions"]), 25)
        self.assertEqual(frame["emitted_candidate_indices"], [24])
        self.assertEqual(frame["supported_candidate_indices"], [24])

    def test_yolo_below_rank_twenty_also_supplies_support(self):
        points = [(100 + 25 * i, 100, .9 - .02 * i) for i in range(25)]
        _, _, result = self.select([[(700, 100, .1)]], [points])
        decision = result["frames"][0]["candidate_decisions"][0]
        self.assertEqual(decision["witness_yolo_original_index"], 24)
        self.assertTrue(decision["supported"])

    def test_replacement_and_withholding_are_distinct(self):
        _, _, result = self.select([[(100, 100, .9), (300, 100, .5)],
                                    [(100, 100, .9), (300, 100, .5)]],
                                   [[(300, 100, .1)], [(500, 100, .1)]])
        self.assertEqual([f["emitted_candidate_indices"] for f in result["frames"]], [[1], []])

    def test_rf_confidence_then_original_index_not_yolo_confidence(self):
        _, _, result = self.select([[(100, 100, .8), (300, 100, .8), (500, 100, .7)]],
                                   [[(300, 100, .99), (500, 100, .98), (100, 100, .01)]])
        self.assertEqual(result["frames"][0]["emitted_candidate_indices"], [0])
        # This is an exact comparison, not a tolerance around equal confidence.
        _, _, result = self.select([[(100, 100, .8), (300, 100, math.nextafter(.8, 1.))]],
                                   [[(100, 100, .1), (300, 100, .1)]])
        self.assertEqual(result["frames"][0]["emitted_candidates"][0]["center_xy_px"], [300., 100.])

    def test_witness_maximum_and_exact_tie_lowest_original_index(self):
        _, _, result = self.select([[(100, 100, .8)]],
                                   [[(102, 100, .9), (100, 100, .8), (100, 100, .7)]])
        decision = result["frames"][0]["candidate_decisions"][0]
        self.assertEqual((decision["maximum_iou"], decision["witness_yolo_original_index"],
                          decision["supporter_count"]), (1., 1, 3))

    def test_duplicate_yolo_support_gets_no_ranking_reward(self):
        _, _, result = self.select([[(100, 100, .8), (300, 100, .7)]],
                                   [[(100, 100, .01)] + [(300, 100, .01)] * 25])
        frame = result["frames"][0]
        self.assertEqual(frame["emitted_candidate_indices"], [0])
        self.assertEqual(frame["candidate_decisions"][1]["supporter_count"], 25)

    def test_original_rf_box_center_index_confidence_unchanged(self):
        rf, yolo, result = self.select([[(100, 100, .9), (300, 200, .51, 7)]],
                                      [[(301, 200, .99, 8)]])
        original = rf.to_dict(), yolo.to_dict()
        self.assertEqual(result["frames"][0]["emitted_candidates"], [rf.frames[0].detections[1].to_dict()])
        result["frames"][0]["emitted_candidates"][0]["center_xy_px"][0] = 999
        self.assertEqual((rf.to_dict(), yolo.to_dict()), original)

    def test_startup_immediate_loss_and_reacquisition_without_memory(self):
        _, _, result = self.select([[(100, 100, .8)]] * 4,
                                   [[(100, 100, .8)], [], [(100, 100, .8)], [(100, 100, .8)]])
        self.assertEqual([f["emitted_candidate_indices"] for f in result["frames"]], [[0], [], [0], [0]])

    def test_later_valid_candidates_do_not_change_an_earlier_decision(self):
        rf, yolo = fixture([[(100, 100, .8)], [(300, 100, .8)]],
                           [[(100, 100, .8)], [(500, 100, .8)]])
        first = corroboration.select_candidates(rf, yolo, COMMIT)["frames"][0]
        changed = replace(yolo, frames=(yolo.frames[0], replace(yolo.frames[1], detections=())))
        second = corroboration.select_candidates(rf, changed, COMMIT)["frames"][0]
        # Whole-input binding changes; the scientific first-frame decision does not.
        for frame in (first, second):
            for decision in frame["candidate_decisions"]:
                decision["reference"].pop("input_binding")
        self.assertEqual(first, second)

    def test_shared_wrong_object_is_still_supported_not_identity_certified(self):
        # Artificial actual ball is (100,100); both detectors point to a shoe at (600,400).
        _, _, result = self.select([[(600, 400, .9)]], [[(600, 400, .99)]])
        self.assertEqual(result["frames"][0]["emitted_candidates"][0]["center_xy_px"], [600., 400.])
        self.assertIn("not semantic ball identity", result["score_semantics"])
        self.assertIsNone(result["quality_gate"])
        self.assertIsNone(result["selected_operating_point"])

    def test_namespaces_and_original_bound_inputs_preserved(self):
        rf, yolo, result = self.select([[(100, 100, .8)]], [[(300, 100, .9)]])
        self.assertEqual(result["input_bindings"]["rfdetr"]["content_sha256"], canonical_sha256(rf.to_dict()))
        self.assertEqual(result["input_bindings"]["yolo"]["content_sha256"], canonical_sha256(yolo.to_dict()))
        self.assertNotEqual(result["input_bindings"]["rfdetr"], result["input_bindings"]["yolo"])
        # Same original index 0 across detectors is not an object correspondence.
        self.assertEqual(result["frames"][0]["emitted_candidate_indices"], [])
        with self.assertRaises(ValueError):
            corroboration.select_candidates(yolo, rf, COMMIT)

    def test_source_hash_dimensions_window_frame_provenance_mismatches_fail(self):
        rf, yolo = fixture([[(100, 100, .8)]], [[(100, 100, .8)]])
        variants = [replace(yolo, source_video=replace(yolo.source_video, sha256="f" * 64)),
                    replace(yolo, source_video=replace(yolo.source_video, width_px=2000)),
                    replace(yolo, annotation_set_id="different_annotation"),
                    replace(yolo, possession_id="possession_002"),
                    replace(yolo, window=replace(yolo.window, end_frame_index=1)),
                    replace(yolo, frames=(replace(yolo.frames[0], frame_index=1),)),
                    replace(yolo, model_provenance=replace(yolo.model_provenance, weights_sha256="")),
                    replace(yolo, model_provenance=replace(yolo.model_provenance, code_commit="")),
                    replace(yolo, model_provenance=replace(yolo.model_provenance, export_confidence_floor=.2)),
                    replace(yolo, model_provenance=replace(yolo.model_provenance, tiling_enabled=False))]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                corroboration.select_candidates(rf, value, COMMIT)

    def test_invalid_final_candidate_fails_before_streamed_first_frame(self):
        rf, yolo = fixture([[(100, 100, .8)]] * 2, [[(100, 100, .8)]] * 2)
        broken = replace(rf.frames[1].detections[0], bbox_xyxy_px=(1., 1., math.nan, 2.))
        rf = replace(rf, frames=(rf.frames[0], replace(rf.frames[1], detections=(broken,))))
        with self.assertRaises(ValueError):
            next(corroboration.iter_selected_frames(rf, yolo))

    def test_invalid_excluded_candidates_are_not_silently_dropped(self):
        rf, yolo = fixture([[(100, 100, .009)]], [[(100, 100, .9)]])
        bad = replace(rf.frames[0].detections[0], bbox_xyxy_px=(1., 1., 1., 2.))
        with self.assertRaises(ValueError):
            corroboration.select_candidates(replace(rf, frames=(replace(rf.frames[0], detections=(bad,)),)),
                                              yolo, COMMIT)

    def test_invalid_boxes_nonfinite_area_and_union_rejected(self):
        for box in ((0, 0, 0, 1), (0, 0, math.inf, 1), (False, 0, 1, 1),
                    (0, 0, 1e-300, 1e-300), (0, 0, 1e200, 1e200), (2, 2, 1, 3)):
            with self.subTest(box=box), self.assertRaises(ValueError):
                corroboration.box_iou(box, (0, 0, 1, 1))
        with self.assertRaises(ValueError):
            corroboration.box_iou((0, 0, 1e154, 1e154), (0, 0, 1e154, 1e154))

    def test_failed_inference_and_invalid_confidence_order_fail(self):
        rf, yolo = fixture([[(100, 100, .9), (300, 100, .8)]], [[(100, 100, .9)]])
        failed = replace(yolo.frames[0], inference_status="inference_failed", failure_reason="artificial",
                         detections=None)
        with self.assertRaises(ValueError):
            corroboration.select_candidates(rf, replace(yolo, frames=(failed,)), COMMIT)
        wrong = (replace(rf.frames[0].detections[0], confidence=.1), rf.frames[0].detections[1])
        with self.assertRaises(ValueError):
            corroboration.select_candidates(replace(rf, frames=(replace(rf.frames[0], detections=wrong),)),
                                              yolo, COMMIT)

    def test_linear_trace_size_and_bounded_pair_cancellation(self):
        rf, yolo = fixture([[(100, 100, .8)] * 40], [[(100, 100, .9)] * 50])
        actual_iou = corroboration.box_iou
        calls, last, intervals = 0, 0, []

        def counted(*args):
            nonlocal calls
            calls += 1
            return actual_iou(*args)

        def progress():
            nonlocal last
            intervals.append(calls - last)
            last = calls
            if calls >= 512:
                raise RuntimeError("artificial cancellation")

        with patch.object(corroboration, "box_iou", side_effect=counted), self.assertRaisesRegex(RuntimeError, "cancellation"):
            corroboration.select_candidates(rf, yolo, COMMIT, progress)
        self.assertEqual(calls, 512)
        self.assertLessEqual(max(intervals), corroboration.PAIR_CHECK_INTERVAL)
        result = corroboration.select_candidates(rf, yolo, COMMIT)
        self.assertEqual(len(result["frames"][0]["candidate_decisions"]), 40)
        self.assertTrue(all(set(d) == corroboration.DECISION_FIELDS for d in result["frames"][0]["candidate_decisions"]))
        self.assertNotIn("pairs", result["frames"][0])

    def test_structural_validation_does_not_rerun_any_selector_or_iou(self):
        rf, yolo, result = self.select([[(100, 100, .8)]], [[(100, 100, .9)]])
        with patch.object(corroboration, "select_candidates", side_effect=AssertionError("selection replay")), \
                patch.object(corroboration, "box_iou", side_effect=AssertionError("pair replay")):
            self.assertEqual(corroboration.validate_observations(result, rf, yolo), corroboration.CONFIG)

    def test_structural_validation_rejects_resealed_bad_records(self):
        rf, yolo, result = self.select([[(100, 100, .8), (300, 100, .7)]],
                                      [[(100, 100, .9), (300, 100, .8)]])
        mutations = [lambda x: x.update(config={**x["config"], "iou_threshold": .49}),
                     lambda x: x["frames"][0].update(emitted_candidate_indices=[1]),
                     lambda x: x["frames"][0].update(supported_candidate_indices=[0]),
                     lambda x: x["frames"][0].update(output_state="hidden"),
                     lambda x: x["frames"][0].update(horizon_start=True),
                     lambda x: x["frames"][0]["emitted_candidates"][0].update(confidence=.7),
                     lambda x: x["frames"][0]["candidate_decisions"][0].update(supporter_count=True),
                     lambda x: x["frames"][0]["candidate_decisions"][0].update(supporter_count=99),
                     lambda x: x["frames"][0]["candidate_decisions"][0].update(maximum_iou=.4),
                     lambda x: x["frames"][0]["candidate_decisions"][0].update(witness_yolo_original_index=99),
                     lambda x: x["frames"][0]["candidate_decisions"][0].update(supported=False),
                     lambda x: x["frames"][0]["candidate_decisions"][0].update(inclusion=1),
                     lambda x: x["frames"][0]["candidate_decisions"][0]["reference"].update(detector="yolo"),
                     lambda x: x["frames"][0]["candidate_decisions"][0]["reference"].update(original_candidate_index=False),
                     lambda x: x["frames"][0]["candidate_decisions"][0].update(extra="unapproved"),
                     lambda x: x.update(extra="unapproved")]
        for mutate in mutations:
            bad = copy.deepcopy(result)
            mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                corroboration.validate_observations(reseal(bad), rf, yolo)

    def test_input_changes_and_unsealed_output_are_rejected(self):
        rf, yolo, result = self.select([[(100, 100, .8)]], [[(100, 100, .9)]])
        bad = copy.deepcopy(result)
        bad["frames"][0]["decision_reason"] = "forged"
        with self.assertRaises(ValueError):
            corroboration.validate_observations(bad, rf, yolo)
        changed = replace(yolo, model_provenance=replace(yolo.model_provenance, weights_identifier="changed"))
        with self.assertRaises(ValueError):
            corroboration.validate_observations(result, rf, changed)


if __name__ == "__main__":
    unittest.main()

"""Point scoring must preserve the reviewed evaluator's scientific rules."""
import copy
import math
import unittest

from src.ball_tracking.evaluation import evaluate_detections
from src.ball_tracking.point_evaluation import (
    POINT_RUN_SCHEMA_VERSION, PointEvaluationError, evaluate_points, validate_point_run,
)
from test_ball_annotation_foundation import (
    ambiguous_visible_frame, detection, excluded_frame, indeterminate_frame,
    not_visible_frame, observed_frame, parse_annotations, parse_detection_run,
    parse_reviewed_annotations, partial_frame,
)


def point_run(labels, raw_run=None):
    """Project an actual parsed detector fixture, without manufacturing boxes."""
    raw_run = raw_run or parse_detection_run(labels)
    return {
        "schema_version": POINT_RUN_SCHEMA_VERSION,
        "point_run_id": "artificial_temporal_points",
        "annotation_set_id": labels.annotation_set_id,
        "possession_id": labels.possession_id,
        "source_video": raw_run.source_video.to_dict(),
        "window": raw_run.window.to_dict(),
        "model_provenance": {
            "model": "artificial_point_producer", "native_score_definition": "unbounded component mass",
            "context": "synthetic; no real model or media accessed",
        },
        "frames": [{
            "frame_index": frame.frame_index, "inference_status": "completed", "failure_reason": None,
            "candidates": [{
                "candidate_index": candidate.candidate_index,
                "center_xy_px": list(candidate.center_xy_px),
                # Strictly monotone transform tests values above one without changing ranking.
                "native_score": candidate.confidence * 100,
            } for candidate in frame.detections],
        } for frame in raw_run.frames],
    }


class PointEvaluationTests(unittest.TestCase):
    def test_actual_detector_evaluator_parity_across_visibility_and_duplicate_rules(self):
        labels = parse_reviewed_annotations([
            observed_frame(0), partial_frame(1, uncertainty=4), not_visible_frame(2),
            ambiguous_visible_frame(3), indeterminate_frame(4), excluded_frame(5),
            partial_frame(6, with_geometry=False), not_visible_frame(7, certainty="ambiguous"),
            observed_frame(8), observed_frame(9),
        ])
        raw = parse_detection_run(labels, {
            0: [detection(103, 104, .9), detection(100, 101, .8), detection(150, 100, .7)],
            1: [detection(107, 100, .8)], 2: [detection(100, 100), detection(200, 200)],
            3: [detection(100, 100)], 4: [detection(100, 100)], 5: [detection(100, 100)],
            6: [detection(100, 100)], 7: [detection(100, 100)], 9: [detection(111, 100)],
        })
        points = point_run(labels, raw)
        for radius in (0, 4.999, 5, 7, 10, 15, 20, 30):
            with self.subTest(radius=radius):
                reference = evaluate_detections(labels, raw, confidence_threshold=0,
                                                localization_radius_px=radius)
                actual = evaluate_points(labels, points, localization_radius_px=radius)
                # Compare actual independent consumers, not a second handwritten metric oracle.
                self.assertEqual(actual["frame_results"], reference["frame_results"])
                for field in reference:
                    if field.endswith("_count") or field in {
                        "precision", "recall", "non_visible_false_alarm_rate",
                        "non_visible_false_alarms_per_100_frames", "matched_center_error_px",
                        "matched_effective_center_error_px",
                    }:
                        self.assertEqual(actual[field], reference[field], field)
                self.assertNotIn("confidence_threshold", actual)

    def test_inclusive_radius_and_uncertainty_do_not_convert_a_miss(self):
        labels = parse_reviewed_annotations([partial_frame(0, uncertainty=4)])
        run = point_run(labels, parse_detection_run(labels, {0: [detection(107, 100)]}))
        at_edge = evaluate_points(labels, run, localization_radius_px=7)
        outside = evaluate_points(labels, run, localization_radius_px=6.999)
        self.assertEqual(at_edge["true_positive_count"], 1)
        self.assertEqual(at_edge["matched_center_error_px"]["mean"], 7)
        self.assertEqual(at_edge["matched_effective_center_error_px"]["mean"], 3)
        self.assertEqual((outside["false_positive_count"], outside["false_negative_count"]), (1, 1))

    def test_native_scores_preserve_centroids_and_original_index_namespace(self):
        labels = parse_reviewed_annotations([observed_frame(0)])
        run = point_run(labels)
        run["frames"][0]["candidates"] = [
            {"candidate_index": 9, "center_xy_px": [100.25, 101.125], "native_score": 12.5},
            {"candidate_index": 4, "center_xy_px": [101.5, 102.375], "native_score": 12.5},
            {"candidate_index": 2, "center_xy_px": [300, 100], "native_score": 500},
        ]
        before = copy.deepcopy(run)
        actual = evaluate_points(labels, run, localization_radius_px=10)
        self.assertEqual(actual["frame_results"][0]["matched_candidate_index"], 4)
        self.assertEqual(actual["duplicate_false_positive_count"], 1)
        self.assertEqual(actual["false_positive_count"], 2)
        self.assertEqual(run, before)
        self.assertEqual(validate_point_run(labels, run), run)
        self.assertNotIn("bbox_xyxy_px", run["frames"][0]["candidates"][0])

    def test_empty_completed_inference_is_abstention_zero_native_score_is_output(self):
        labels = parse_reviewed_annotations([observed_frame(0), not_visible_frame(1)])
        run = point_run(labels)
        empty = evaluate_points(labels, run, localization_radius_px=10)
        self.assertEqual((empty["false_negative_count"], empty["false_positive_count"]), (1, 0))
        self.assertIsNone(empty["precision"])
        run["frames"][0]["candidates"] = [
            {"candidate_index": 0, "center_xy_px": [100, 100], "native_score": 0},
        ]
        actual = evaluate_points(labels, run, localization_radius_px=0)
        self.assertEqual(actual["true_positive_count"], 1)

    def test_out_of_source_coordinates_remain_errors_even_near_truth(self):
        labels = parse_reviewed_annotations([observed_frame(0, center=(0, 10))])
        run = point_run(labels)
        run["frames"][0]["candidates"] = [
            {"candidate_index": 5, "center_xy_px": [-.1, 10], "native_score": 200},
        ]
        actual = evaluate_points(labels, run, localization_radius_px=10)
        self.assertEqual((actual["true_positive_count"], actual["false_positive_count"],
                          actual["false_negative_count"]), (0, 1, 1))
        self.assertEqual(actual["input_detection_count"], 1)
        self.assertEqual(run["frames"][0]["candidates"][0]["center_xy_px"], [-.1, 10])

    def test_reports_bind_actual_point_and_model_content(self):
        labels = parse_reviewed_annotations([observed_frame(0)])
        run = point_run(labels)
        first = evaluate_points(labels, run, localization_radius_px=10)
        run["model_provenance"]["context"] = "different actual context"
        changed = evaluate_points(labels, run, localization_radius_px=10)
        self.assertNotEqual(first["model_run_signature"], changed["model_run_signature"])
        self.assertNotEqual(first["point_run_content_sha256"], changed["point_run_content_sha256"])
        self.assertEqual(first["annotation_content_sha256"], changed["annotation_content_sha256"])


class PointRunValidationTests(unittest.TestCase):
    def setUp(self):
        self.labels = parse_reviewed_annotations([observed_frame(0), observed_frame(1)])
        self.run = point_run(self.labels, parse_detection_run(self.labels, {0: [detection(100, 100)]}))

    def test_missing_failed_unrun_duplicate_reordered_and_extra_frames_refused(self):
        variants = []
        for status in ("failed", "not_run"):
            run = copy.deepcopy(self.run)
            run["frames"][0].update(inference_status=status, failure_reason="actual failure", candidates=None)
            variants.append(run)
        for frames in (self.run["frames"][:1], self.run["frames"] * 2,
                       list(reversed(self.run["frames"])), [self.run["frames"][0]] * 2):
            variants.append({**self.run, "frames": frames})
        run = copy.deepcopy(self.run)
        run["frames"][0]["frame_index"] = False
        variants.append(run)
        run = copy.deepcopy(self.run)
        run["frames"][0]["candidates"] = None
        variants.append(run)
        run = copy.deepcopy(self.run)
        run["frames"][0]["failure_reason"] = "cannot be completed and failed"
        variants.append(run)
        for run in variants:
            with self.subTest(run=run), self.assertRaises(ValueError):
                validate_point_run(self.labels, run)

    def test_source_dimensions_hash_metadata_window_and_annotation_binding_refused(self):
        changes = [
            ("annotation_set_id", "different"), ("possession_id", "different"),
            ("schema_version", "ball_detection_evaluation/v0.1"), ("point_run_id", ""),
            ("window", {"start_frame_index": 0, "end_frame_index": 0}),
            ("window", {"start_frame_index": False, "end_frame_index": 1}),
        ]
        for field in ("width_px", "height_px", "fps", "frame_count", "sha256", "path"):
            source = copy.deepcopy(self.run["source_video"])
            source[field] = ("d" * 64 if field == "sha256" else "data/clips/different.mp4"
                             if field == "path" else source[field] + 1)
            changes.append(("source_video", source))
        for field, value in changes:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_point_run(self.labels, {**self.run, field: value})

    def test_exact_fields_and_finite_unbounded_scores_are_enforced(self):
        mutations = [
            lambda r: r.update(extra=True),
            lambda r: r["frames"][0].update(extra=True),
            lambda r: r["frames"][0]["candidates"][0].update(confidence=.5),
            lambda r: r["frames"][0]["candidates"][0].pop("native_score"),
            lambda r: r["frames"][0]["candidates"].append(copy.deepcopy(r["frames"][0]["candidates"][0])),
        ]
        for key, values in {
            "native_score": (-1, math.nan, math.inf, True, "12", 10 ** 1000),
            "center_xy_px": ([math.nan, 100], [100, math.inf], [True, 100], [100], "100,100"),
            "candidate_index": (-1, True, 1.5),
        }.items():
            for value in values:
                mutations.append(lambda r, key=key, value=value: r["frames"][0]["candidates"][0].update({key: value}))
        for mutate in mutations:
            run = copy.deepcopy(self.run)
            mutate(run)
            with self.subTest(run=run), self.assertRaises(ValueError):
                validate_point_run(self.labels, run)

    def test_non_json_or_empty_model_provenance_and_draft_annotations_refused(self):
        for provenance in ({}, None, [], {"score": math.nan}, {"bad": object()}, {1: "number key"}):
            with self.subTest(provenance=provenance), self.assertRaises(ValueError):
                validate_point_run(self.labels, {**self.run, "model_provenance": provenance})
        draft = parse_annotations([observed_frame(0), observed_frame(1)])
        with self.assertRaisesRegex(PointEvaluationError, "reviewed"):
            validate_point_run(draft, point_run(draft))

    def test_invalid_radius_refused(self):
        for radius in (-1, math.inf, math.nan, True, "10"):
            with self.subTest(radius=radius), self.assertRaises(ValueError):
                evaluate_points(self.labels, self.run, localization_radius_px=radius)


if __name__ == "__main__":
    unittest.main()

"""Artificial pixels and supplied decisions verify corroboration review output."""
import copy
import json
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from src.ball_tracking import crop_cross_detector_corroboration_review as review
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.development_experiments import canonical_sha256
from test_ball_annotation_foundation import detection, not_visible_frame, observed_frame, parse_detection_run, parse_reviewed_annotations

ARM, TOP, ARMS = review.ARM, review.TOP, review.ARMS
COMMIT = "d" * 40


def fixture(count=25, start=0):
    """Hand-specified artificial decisions/results: no selector/evaluator calls."""
    labels = parse_reviewed_annotations([
        not_visible_frame(i) if i - start == 3 else observed_frame(i, center=(32, 30))
        for i in range(start, start + count)], width_px=160, height_px=90)
    payload = labels.to_dict()
    payload["window"]["selection_purpose"] = "representative_evaluation"
    labels = BallAnnotationSet.from_mapping(payload)
    run = parse_detection_run(labels, {i: [detection(32, 30, .8), detection(110, 55, .6)]
                                      for i in range(start, start + count)})
    observations, reports = {}, {}
    for arm in ARMS:
        config = {"arm": arm, "confidence_threshold": .01}
        if arm == ARM:
            config["iou_threshold"] = .5
        else:
            config.update(candidate_cap=None, edge_step=None, cost_step=None)
        rows, results = [], []
        for offset, frame in enumerate(run.frames):
            chosen = None if offset == 2 else 1 if offset in (1, 5, 6) else 0
            if arm == ARM:
                chosen = None if offset in (2, 4, 6, 24) else 0 if offset == 5 else 1 if offset == 7 else chosen
            emitted = [] if chosen is None else [chosen]
            annotation = labels.annotation_by_frame()[frame.frame_index]
            row = {"frame_index": frame.frame_index, "emitted_candidate_indices": emitted,
                   "decision_reason": "no_supported_rf_candidate" if not emitted else "supported_rf_candidate"}
            if arm == ARM:
                row["emitted_candidates"] = [frame.detections[i].to_dict() for i in emitted]
            rows.append(row)
            hidden = annotation.visibility == "not_visible"
            matched = chosen == 0 and not hidden
            results.append({"frame_index": frame.frame_index, "accepted_detection_count": len(emitted),
                            "matched_candidate_index": 0 if matched else None,
                            "scoring_status": "not_visible_negative" if hidden else "localization_eligible",
                            "visibility": annotation.visibility, "annotation_status": annotation.annotation_status,
                            "matched_center_error_px": 0.0 if matched else None})
        observation = {"variant_id": arm + "_synthetic", "config": config, "frames": rows,
                       "ranking_code_commit": COMMIT, "possession_id": run.possession_id,
                       "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
                       "input_candidate_content_sha256": canonical_sha256(run.to_dict())}
        if arm == ARM:
            observation["input_bindings"] = {
                "rfdetr": {"detector": "rfdetr", "detection_run_id": run.detection_run_id,
                           "content_sha256": canonical_sha256(run.to_dict()), "model_provenance": run.model_provenance.to_dict()},
                "yolo": {"detector": "yolo", "detection_run_id": "artificial_yolo",
                         "content_sha256": "e" * 64, "model_provenance": run.model_provenance.to_dict()}}
        observations[arm] = observation
        report = {"variant_id": observation["variant_id"], "config": copy.deepcopy(config),
                  "frame_results": results, "localization_radius_px": 10.0,
                  "ranking_code_commit": COMMIT, "evaluator_code_commit": COMMIT,
                  "selection_purpose": labels.window.selection_purpose,
                  "possession_id": run.possession_id, "source_video": run.source_video.to_dict(),
                  "window": run.window.to_dict(), "input_model_provenance": run.model_provenance.to_dict(),
                  "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
                  "observations_content_sha256": canonical_sha256(observation),
                  "annotation_content_sha256": canonical_sha256(labels.to_dict()),
                  "matching_rule": "raw center distance; uncertainty diagnostic only"}
        if arm == ARM:
            report["input_bindings"] = copy.deepcopy(observation["input_bindings"])
        reports[arm] = report
    window = {"window_id": "artificial_review", "start_frame_index": start, "end_frame_index": start + count - 1,
              "purpose": labels.window.selection_purpose, "possession_id": run.possession_id,
              "source_video": run.source_video.to_dict()}
    return labels, run, observations, reports, window


def source_pixels():
    pixels = np.zeros((90, 160, 3), dtype=np.uint8)
    pixels[:, :, 0] = np.arange(160, dtype=np.uint8)
    pixels[:, :, 1] = np.arange(90, dtype=np.uint8)[:, None]
    return pixels


class MemoryWriter:
    def __init__(self):
        self.shapes, self.released = [], False

    def write(self, pixels):
        self.shapes.append(pixels.shape)

    def release(self):
        self.released = True


def fast_frame(source, annotation, frame, observations, reports):
    # Preserve all meaningful decision validation while avoiding 25 big layouts.
    details, _ = review._frame_details(annotation, frame, observations, reports)
    composite = np.full((review.TILE_HEIGHT, review.TILE_WIDTH * 3, 3), frame.frame_index % 255, dtype=np.uint8)
    native = {review.VIEW_NAMES[a]: np.vstack((np.zeros((review.NATIVE_HEADER, source.shape[1], 3), dtype=np.uint8), source))
              for a in ARMS}
    return composite, native, details


class CorroborationReviewTests(unittest.TestCase):
    def frame(self, offset=0):
        labels, run, observations, reports, _ = fixture()
        return (source_pixels(), labels.annotation_by_frame()[offset], run.frames[offset],
                {a: observations[a]["frames"][offset] for a in ARMS},
                {a: reports[a]["frame_results"][offset] for a in ARMS})

    def test_three_panels_native_scale_and_unchanged_source_original_geometry(self):
        args = self.frame()
        before = args[0].copy()
        composite, native, details = review.render_frame(*args)
        self.assertEqual(composite.shape, (review.TILE_HEIGHT, review.TILE_WIDTH * 3, 3))
        self.assertEqual(set(native), {"saved_top_one", "new_corroborated"})
        self.assertTrue(all(p.shape == (230, 160, 3) for p in native.values()))
        self.assertTrue(np.array_equal(before, args[0]))
        for row in details.values():
            self.assertEqual(row["original_rf_center_xy_px"], [32, 30])
            self.assertEqual(row["original_rf_confidence"], .8)
            self.assertIsNone(row["semantic_identity"])

    def test_missing_output_is_disclosed_without_invented_prediction(self):
        with patch.object(cv2, "drawMarker", wraps=cv2.drawMarker) as markers:
            _, _, details = review.render_frame(*self.frame(2))
        self.assertTrue(all(d["state"] == "missing" and "MISSING" in d["selection_text"] for d in details.values()))
        self.assertTrue(all(d["original_rf_center_xy_px"] is None for d in details.values()))
        self.assertEqual(len(markers.call_args_list), 2)  # reviewed reference only
        self.assertTrue(all(call.args[3] == cv2.MARKER_CROSS for call in markers.call_args_list))

    def test_hidden_has_no_reference_marker_and_no_invented_geometry(self):
        with patch.object(cv2, "drawMarker", wraps=cv2.drawMarker) as markers:
            _, _, details = review.render_frame(*self.frame(3))
        self.assertEqual(len(markers.call_args_list), 2)  # supplied predictions only
        self.assertTrue(all(call.args[3] == cv2.MARKER_TILTED_CROSS for call in markers.call_args_list))
        self.assertTrue(all(d["state"] == "alarm" for d in details.values()))

    def test_unsynchronized_unknown_and_mutated_geometry_refused(self):
        for change, message in ((lambda a: a[3][ARM].update(frame_index=5), "synchronized"),
                                (lambda a: a[3][ARM].update(emitted_candidate_indices=[99]), "Unknown"),
                                (lambda a: a[3][ARM]["emitted_candidates"][0].update(confidence=.9), "geometry"),
                                (lambda a: a[4][ARM].update(scoring_status="not_visible_negative"), "annotation")):
            args = list(self.frame())
            change(args)
            with self.assertRaisesRegex(ValueError, message):
                review.render_frame(*args)

    def test_all_frames_final_lost_correct_and_all_changed_decisions_indexed(self):
        labels, run, observations, reports, window = fixture(start=150)
        before = copy.deepcopy((observations, reports))
        reads, written, writer, verified = [], {}, MemoryWriter(), []

        def read(index):
            reads.append(index)
            return source_pixels()

        def write(relative, payload):
            self.assertNotIn(relative, written)
            written[relative] = payload
            return {"path": relative, "sha256": "a" * 64, "size_bytes": len(payload)}

        def open_video(relative, fps, size):
            self.assertTrue(relative.endswith("/comparison.mp4"))
            self.assertEqual((fps, size), (5.0, (review.TILE_WIDTH * 3, review.TILE_HEIGHT)))
            return writer

        def verify(relative, count, fps, size):
            self.assertTrue(writer.released)
            self.assertEqual(count, len(writer.shapes))
            self.assertEqual((count, fps), (25, 5.0))
            verified.append(relative)
            return {"path": relative, "sha256": "b" * 64, "size_bytes": 1}

        with patch.object(review, "render_frame", side_effect=fast_frame), \
                patch.object(cv2, "VideoCapture", side_effect=AssertionError("Source-video decoding forbidden")):
            result = review.render_window(window, run, labels, observations, reports,
                read_source=read, write_bytes=write, open_video=open_video, verify_video=verify)
        index = result["index"]
        self.assertEqual(reads, list(range(150, 175)))
        self.assertEqual(len(written), 53)  # 50 native + first + last + index
        self.assertEqual(index["native_overlay_count"], 50)
        self.assertEqual(index["final_frame_index"], 174)
        self.assertEqual(index["changed_emission_frame_indices"], [154, 155, 156, 157, 174])
        self.assertEqual(index["lost_correct_choice_frame_indices"], [154, 157, 174])
        self.assertEqual(index["error_suppressed_frame_indices"], [156])
        self.assertEqual(index["match_recovered_frame_indices"], [155])
        self.assertEqual(index["wrong_replacement_frame_indices"], [157])
        self.assertEqual(index["frames"][-1]["comparison"]["new_state"], "missing")
        self.assertEqual(index["human_final_frame_review"], "pending")
        self.assertFalse(index["old_reviews_reopened"])
        self.assertEqual(index["selection_calls"], 0)
        self.assertEqual(index["evaluation_calls"], 0)
        self.assertEqual(len(verified), 1)
        self.assertEqual(json.loads(written[result["index_binding"]["path"]]), index)
        self.assertEqual((observations, reports), before)

    def test_provenance_labels_source_and_final_report_fail_before_any_read(self):
        for mutate in (
            lambda w, o, r: w["source_video"].update(sha256="f" * 64),
            lambda w, o, r: w.update(purpose="challenge_evaluation"),
            lambda w, o, r: w.update(window_id="../unsafe"),
            lambda w, o, r: r[TOP].update(annotation_content_sha256="f" * 64),
            lambda w, o, r: o[ARM]["input_bindings"]["rfdetr"].update(detector="yolo"),
            lambda w, o, r: r[ARM]["frame_results"][-1].update(frame_index=99),
        ):
            labels, run, observations, reports, window = fixture()
            mutate(window, observations, reports)
            with self.assertRaises(ValueError):
                review.render_window(window, run, labels, observations, reports,
                    read_source=lambda *_: self.fail("No image read before complete validation"),
                    write_bytes=lambda *_: self.fail("No output before validation"),
                    open_video=lambda *_: self.fail("No video before validation"), verify_video=lambda *_: None)

    def test_incomplete_window_rejected_before_read(self):
        labels, run, observations, reports, window = fixture(24)
        with self.assertRaisesRegex(ValueError, "complete 25"):
            review.render_window(window, run, labels, observations, reports,
                read_source=lambda *_: self.fail("No source read"), write_bytes=lambda *_: None,
                open_video=lambda *_: None, verify_video=lambda *_: None)

    def test_phase_denial_releases_writer_without_adopting_partial_video(self):
        labels, run, observations, reports, window = fixture()
        writer, calls = MemoryWriter(), []

        def read(index):
            calls.append(index)
            if index == 1:
                raise PermissionError("pixel phase refused")
            return source_pixels()

        with patch.object(review, "render_frame", side_effect=fast_frame), self.assertRaisesRegex(PermissionError, "phase refused"):
            review.render_window(window, run, labels, observations, reports,
                read_source=read, write_bytes=lambda name, payload: {"path": name}, open_video=lambda *_: writer,
                verify_video=lambda *_: self.fail("Partial video cannot be adopted"))
        self.assertEqual(calls, [0, 1])
        self.assertTrue(writer.released)


if __name__ == "__main__":
    unittest.main()

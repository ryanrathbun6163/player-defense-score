"""Synthetic producer-to-point-evaluator transport and development boundaries."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from src.ball_tracking import wasb_development_observation as producer
from src.ball_tracking import wasb_motion_evaluation as comparison
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.point_evaluation import evaluate_points
from test_ball_annotation_foundation import not_visible_frame, observed_frame, parse_reviewed_annotations
from test_ball_point_evaluation import point_run


def set_selection(row, arm, candidate_index):
    prefix = "baseline_" if arm == "baseline" else ""
    row["baseline_candidate_index" if prefix else "selected_candidate_index"] = candidate_index
    selected = next((c for c in row["candidates"] if c["candidate_index"] == candidate_index), None)
    row[prefix + "center_xy_px"] = None if selected is None else [selected["center_x"], selected["center_y"]]
    row[prefix + "native_score"] = None if selected is None else selected["native_score"]
    if not prefix:
        row["state"] = "missing" if selected is None else "observed"


class MotionEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.labels_root = self.root / "configs/ball_tracking/annotations"
        self.labels_root.mkdir(parents=True)
        self.split = {"schema_version": "ball_detector_experiment/v0.2", "windows": [], "sealed_holdouts": []}
        self.timelines = {}
        self.labels = {}
        for number in range(1, 4):
            pid = f"synthetic_{number}"
            source = {"path": f"data/clips/{pid}.mp4", "sha256": str(number) * 64,
                      "width_px": 512, "height_px": 288, "fps": 25.0, "frame_count": 200}
            # Candidates and native masses come from the real observation producer.
            heatmaps = np.zeros((1, 288, 512), dtype=np.float32)
            heatmaps[0, 100:103, 100:103] = .8
            heatmaps[0, 100:103, 300:303] = .4
            produced = producer.observed_frames(heatmaps, [1], 0, source, .3)[0]
            frames = []
            for index in range(source["frame_count"]):
                row = copy.deepcopy(produced)
                row.update(frame_index=index, is_training_frame=index >= 150)
                set_selection(row, "baseline", 0)
                if 75 <= index <= 149:
                    set_selection(row, "baseline", None)
                    set_selection(row, "motion", None)
                    row.update(state="withheld", candidates=[])
                frames.append(row)
            self.timelines[pid] = {"source_video": source, "frames": frames}
            self.split["sealed_holdouts"].append({"possession_id": pid, "source_video": source,
                "start_frame_index": 100, "end_frame_index": 124, "selection_purpose": "test_holdout"})
            for purpose, start in zip(comparison.POOLS, (0, 25), strict=True):
                aid = pid + "_" + purpose
                annotations = []
                for index in range(start, start + 25):
                    if number == 3 and 45 <= index <= 49:
                        annotations.append(not_visible_frame(index))
                        set_selection(frames[index], "baseline", None)
                        set_selection(frames[index], "motion", None)
                    else:
                        annotations.append(observed_frame(index, center=frames[index]["center_xy_px"]))
                payload = parse_reviewed_annotations(annotations, annotation_set_id=aid, possession_id=pid,
                    frame_count=200, source_sha256=source["sha256"], width_px=512, height_px=288).to_dict()
                payload["window"]["selection_purpose"] = purpose
                labels = BallAnnotationSet.from_mapping(payload)
                self.labels[aid] = labels
                self.write_labels(aid, labels.to_dict())
                self.split["windows"].append({"window_id": aid + "_window", "annotation_set_id": aid,
                    "possession_id": pid, "source_video": source, "start_frame_index": start,
                    "end_frame_index": start + 24, "selection_purpose": purpose,
                    "execution_status": "ready_for_inference"})

    def write_labels(self, aid, value):
        (self.labels_root / (aid + ".json")).write_text(json.dumps(value), encoding="utf-8")

    def evaluate(self):
        return comparison.evaluate_comparison(self.root, self.split, self.timelines)

    def test_actual_observation_producer_and_point_contract_parity(self):
        before = copy.deepcopy((self.split, self.timelines))
        with mock.patch.object(producer.cv2, "VideoCapture", side_effect=AssertionError("No media access")):
            result = self.evaluate()
        self.assertEqual(before, (self.split, self.timelines))
        json.dumps(result, allow_nan=False)
        self.assertEqual(result["summary"]["baseline"], result["summary"]["motion"])
        self.assertEqual((result["summary"]["baseline"]["frame_count"], result["summary"]["baseline"]["eligible"],
                          result["summary"]["baseline"]["hidden"]), (150, 145, 5))
        self.assertEqual(result["summary"]["baseline"]["true_positive_count"], 145)
        self.assertEqual(result["pools"]["representative_evaluation"]["baseline"]["eligible"], 75)
        self.assertEqual(result["pools"]["challenge_evaluation"]["baseline"]["eligible"], 70)
        for window in result["windows"]:
            aid = window["baseline_report"]["annotation_set_id"]
            labels = self.labels[aid]
            # Existing point fixture builds valid schema from the detector producer contract.
            independent = point_run(labels)
            for frame in independent["frames"]:
                row = self.timelines[labels.possession_id]["frames"][frame["frame_index"]]
                if row["baseline_candidate_index"] is not None:
                    frame["candidates"] = [{"candidate_index": row["baseline_candidate_index"],
                        "center_xy_px": row["baseline_center_xy_px"], "native_score": row["baseline_native_score"]}]
            expected = evaluate_points(labels, independent, localization_radius_px=10)
            self.assertEqual(window["baseline_report"]["frame_results"], expected["frame_results"])
            self.assertEqual(window["annotation"]["sha256"], hashlib.sha256(
                (self.labels_root / (aid + ".json")).read_bytes()).hexdigest())
        self.assertEqual(result["training_frames_scored"], 0)
        self.assertEqual(result["withheld_frames_scored"], 0)

    def test_gains_losses_and_hidden_alarms_are_paired_by_frame(self):
        rows = self.timelines["synthetic_1"]["frames"]
        set_selection(rows[0], "baseline", 1)  # Motion recovers truth.
        set_selection(rows[1], "motion", 1)  # Motion loses truth.
        hidden = self.timelines["synthetic_3"]["frames"]
        set_selection(hidden[45], "motion", 0)
        set_selection(hidden[46], "baseline", 0)
        result = self.evaluate()
        self.assertEqual(result["summary"]["changes"], {"recovered": 1, "lost": 1, "shared": 143,
                         "hidden_alarm_added": 1, "hidden_alarm_removed": 1, "shared_hidden_alarm": 0})
        changes = result["windows"][0]["changes"]
        self.assertEqual(changes["recovered_frame_indices"], [0])
        self.assertEqual(changes["lost_frame_indices"], [1])
        self.assertEqual(changes["frame_changes"][0]["baseline_outcome"], "wrong_present")
        self.assertTrue(changes["frame_changes"][0]["match_gained"])
        self.assertEqual(result["summary"]["motion"]["false_positive_count"], 2)

    def test_wrong_present_missing_and_inclusive_radius_keep_existing_semantics(self):
        row = self.timelines["synthetic_1"]["frames"][0]
        aid = self.split["windows"][0]["annotation_set_id"]
        payload = self.labels[aid].to_dict()
        payload["annotations"][0]["geometry"]["center_xy_px"][0] += 10
        self.write_labels(aid, payload)
        at_edge = self.evaluate()
        self.assertEqual(at_edge["summary"]["motion"]["true_positive_count"], 145)
        payload["annotations"][0]["geometry"]["center_xy_px"][0] += .01
        payload["annotations"][0]["geometry"]["uncertainty_radius_px"] = 20
        self.write_labels(aid, payload)
        set_selection(row, "motion", None)
        result = self.evaluate()
        self.assertEqual(result["summary"]["baseline"]["wrong_present"], 1)
        self.assertEqual(result["summary"]["motion"]["missing"], 1)
        self.assertEqual(result["summary"]["baseline"]["false_negative_count"], 1)
        self.assertEqual(result["summary"]["motion"]["false_negative_count"], 1)

    def test_invalid_timeline_scope_rejected_before_any_annotation_read(self):
        mutations = [
            lambda t, s: t["synthetic_1"]["frames"].pop(),
            lambda t, s: t["synthetic_1"]["frames"].append(t["synthetic_1"]["frames"][0]),
            lambda t, s: t["synthetic_1"]["frames"][0].update(frame_index=True),
            lambda t, s: t["synthetic_1"]["frames"][0].update(is_training_frame=True),
            lambda t, s: t["synthetic_1"]["frames"][0].update(state="withheld"),
            lambda t, s: t["synthetic_1"]["frames"][100].update(state="missing"),
            lambda t, s: t["synthetic_1"]["source_video"].update(sha256="f" * 64),
            lambda t, s: s["windows"][0].update(selection_purpose="test_holdout"),
            lambda t, s: s["windows"][0].update(start_frame_index=100, end_frame_index=124),
            lambda t, s: s["windows"].append(s["windows"][0]),
            lambda t, s: s["windows"][0].update(annotation_set_id=s["windows"][1]["annotation_set_id"]),
        ]
        for mutate in mutations:
            timelines, split = copy.deepcopy(self.timelines), copy.deepcopy(self.split)
            mutate(timelines, split)
            with self.subTest(mutation=mutate), mock.patch.object(Path, "read_bytes") as read, self.assertRaises(ValueError):
                comparison.evaluate_comparison(self.root, split, timelines)
            read.assert_not_called()

    def test_missing_candidate_indices_mutation_and_nonfinite_masses_are_refused(self):
        mutations = [lambda r: r.pop("baseline_candidate_index"),
            lambda r: r.update(selected_candidate_index=99),
            lambda r: r.update(center_xy_px=[1, 2]),
            lambda r: r.update(native_score=.123),
            lambda r: r.update(native_score=float("nan")),
            lambda r: r.update(baseline_native_score=None),
            lambda r: r.update(selected_candidate_index=None),
            lambda r: r.update(is_training_frame=0)]
        for mutate in mutations:
            timelines = copy.deepcopy(self.timelines)
            mutate(timelines["synthetic_1"]["frames"][0])
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                comparison.evaluate_comparison(self.root, self.split, timelines)

    def test_label_source_review_and_145_5_partition_are_required(self):
        aid = self.split["windows"][0]["annotation_set_id"]
        original = self.labels[aid].to_dict()
        mutations = [lambda p: p["source_video"].update(sha256="f" * 64),
            lambda p: p["window"].update(selection_purpose="challenge_evaluation"),
            lambda p: p["review"].update(status="draft", reviewer_id=None, reviewed_at_utc=None),
            lambda p: p["annotations"].__setitem__(0, not_visible_frame(0))]
        for mutate in mutations:
            payload = copy.deepcopy(original)
            mutate(payload)
            self.write_labels(aid, payload)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.evaluate()


if __name__ == "__main__":
    unittest.main()

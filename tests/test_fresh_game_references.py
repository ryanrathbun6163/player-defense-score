"""Bounded synthetic pending-reference, timeline, and emitted-review checks."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import cv2
import numpy as np

from src.ball_tracking import fresh_game_references as references


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def unknown(index):
    return {"frame_index": index, "annotation_status": "labeled", "visibility": "indeterminate",
            "absence_reason": None, "game_ball_identity_certainty": "ambiguous", "geometry": None,
            "localization_eligible": False, "difficulty_tags": [],
            "notes": "Source pixels do not support a confident center."}


class FreshGameReferencesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.base = self.root / references.BASE
        self.folder = self.base / "sources/clip01"
        self.selection_path = self.root / references.SELECTION
        self.selection = {"schema_version": "fresh_game_source_selection/v0.1",
                          "status": "frozen_before_new_pixels_labels_and_predictions",
                          "training_eligible": False, "checkpoint_selection_eligible": False,
                          "prediction_blind_labels": True, "game_id": "fresh_game", "role": references.ROLE,
                          "selected_clips": [{"clip_id": "clip01", "catalog_path": "clips/clip01.mp4",
                                              "window_seconds_half_open": [0, 2]}]}
        save(self.selection_path, self.selection)
        source = self.root / "data/raw/nba/fresh_game_diagnostic_v0_1/clips/clip01.mp4"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"Synthetic source binding; never decoded")
        image = np.full((120, 160, 3), [35, 80, 120], dtype=np.uint8)
        ok, encoded = cv2.imencode(".png", image)
        assert ok
        rgb_hash = hashlib.sha256(cv2.cvtColor(image, cv2.COLOR_BGR2RGB).tobytes()).hexdigest()
        self.frame_map = [{"source_frame_index": i, "native_pts_ticks": i * 256,
                           "native_time_base": "1/15360", "seconds": i / 60} for i in range(181)]
        self.frames = []
        (self.folder / "frames").mkdir(parents=True)
        for i in range(120):
            path = self.folder / "frames" / f"{i:06d}.png"
            path.write_bytes(encoded.tobytes())
            self.frames.append({**self.frame_map[i], "source_png": {
                **references.binding(self.root, path), "rgb_sha256": rgb_hash}})
        save(self.folder / "frame_map.json", self.frame_map)
        save(self.folder / "source_frames.json", self.frames)
        self.preparation = {"status": "source_only_extraction_complete", "model_calls": 0,
            "selection": references.binding(self.root, self.selection_path), "game_id": "fresh_game",
            "clip_id": "clip01", "role": references.ROLE, "source": references.binding(self.root, source),
            "width": 160, "height": 120, "average_rate": "60", "time_base": "1/15360",
            "decoded_frame_count": 181, "selected_frame_count": 120, "first_selected_frame": 0,
            "last_selected_frame": 119, "frames": references.binding(self.root, self.folder / "source_frames.json"),
            "frame_map": references.binding(self.root, self.folder / "frame_map.json")}
        self.preparation_path = self.folder / "preparation.json"
        save(self.preparation_path, self.preparation)
        evidence = self.base / "inspected_contact.png"
        evidence.write_bytes(encoded.tobytes())
        self.proposal = {"schema_version": "fresh_game_reference_proposal/v0.1", "clip_id": "clip01",
            "game_id": "fresh_game", "role": references.ROLE, "annotation_origin": "assistant_visual_proposal",
            "annotator_id": "synthetic_test", "status": references.STATUS, "human_acceptance": None,
            "training_eligible": False, "checkpoint_selection_eligible": False,
            "annotations": [unknown(i) for i in range(120)],
            "inspection_evidence": [references.binding(self.root, evidence)]}
        self.proposal["annotations"][6].update(visibility="fully_visible", game_ball_identity_certainty="certain",
            geometry={"center_xy_px": [72.5, 52.25], "source": "observed_complete_ball_center", "uncertainty_radius_px": 2},
            localization_eligible=True, notes="Visible synthetic point.")
        self.proposal["annotations"][11].update(visibility="not_visible", absence_reason="occluded",
            game_ball_identity_certainty="certain", notes="Ball hidden by player.")
        self.proposal_path = self.base / "proposals/clip01.json"
        save(self.proposal_path, self.proposal)

    def validate(self):
        return references.validate(self.root, self.proposal_path)

    def refresh_registry(self, key, rows):
        name = "source_frames.json" if key == "frames" else "frame_map.json"
        save(self.folder / name, rows)
        self.preparation[key] = references.binding(self.root, self.folder / name)
        save(self.preparation_path, self.preparation)

    def test_complete_new_role_preserves_unknown_hidden_and_pending_status(self):
        result = self.validate()
        self.assertEqual(result["frame_count"], 120)
        self.assertEqual(result["null_centers"], 119)
        self.assertEqual(result["eligible_centers"], 1)
        self.assertEqual(result["frames"][119]["native_duration_ticks"], 256)
        self.assertEqual(result["frames"][119]["native_pts_ticks"], 119 * 256)
        self.assertEqual(result["status"], references.STATUS)
        self.assertIsNone(result["human_acceptance"])
        self.assertFalse(result["training_eligible"])
        self.assertFalse(result["validation"]["independent_video_decode_pixel_audit_performed"])
        self.assertIn("actual_selected_final_frame", result["exceptions"][-1]["reasons"])
        self.assertIsNone(result["frames"][11]["annotation"]["geometry"])

    def test_rejects_false_acceptance_training_old_role_and_unknown_fields(self):
        for field, value in (("human_acceptance", "accepted"), ("training_eligible", True),
                ("checkpoint_selection_eligible", True), ("role", "training"),
                ("status", "accepted"), ("unknown_field", 1)):
            with self.subTest(field=field):
                proposal = deepcopy(self.proposal)
                proposal[field] = value
                save(self.proposal_path, proposal)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_selected_window_and_prediction_blind_eligibility_cannot_change(self):
        for change in ("window", "eligibility", "predictions"):
            selection = deepcopy(self.selection)
            if change == "window":
                selection["selected_clips"][0]["window_seconds_half_open"] = [1, 3]
            elif change == "eligibility":
                selection["training_eligible"] = True
            else:
                selection["prediction_blind_labels"] = False
            with self.subTest(change=change), self.assertRaises(ValueError):
                references.validate_proposal(self.proposal, selection)

    def test_rejects_hidden_center_and_unknown_eligible_geometry(self):
        for index in (0, 11):
            proposal = deepcopy(self.proposal)
            proposal["annotations"][index]["geometry"] = deepcopy(self.proposal["annotations"][6]["geometry"])
            save(self.proposal_path, proposal)
            with self.assertRaises(ValueError):
                self.validate()

    def test_annotation_gap_duplicate_and_unlabeled_rejected(self):
        for change in ("gap", "duplicate", "unlabeled"):
            proposal = deepcopy(self.proposal)
            if change == "gap":
                proposal["annotations"].pop(20)
            elif change == "duplicate":
                proposal["annotations"][21] = deepcopy(proposal["annotations"][20])
            else:
                proposal["annotations"][0].update(annotation_status="unlabeled", visibility=None,
                    game_ball_identity_certainty=None)
            save(self.proposal_path, proposal)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate()

    def test_frame_gap_and_fake_seconds_rejected(self):
        for field, value in (("source_frame_index", 29), ("seconds", 0.123)):
            rows = deepcopy(self.frame_map)
            rows[30][field] = value
            self.refresh_registry("frame_map", rows)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate()

    def test_lineage_and_source_pts_mismatch_rejected(self):
        frames = deepcopy(self.frames)
        frames[3]["native_pts_ticks"] += 1
        self.refresh_registry("frames", frames)
        with self.assertRaisesRegex(ValueError, "lineage/PTS"):
            self.validate()
        self.refresh_registry("frames", self.frames)
        self.preparation["source"]["path"] = "data/raw/nba/different.mp4"
        save(self.preparation_path, self.preparation)
        with self.assertRaisesRegex(ValueError, "catalog"):
            self.validate()

    def test_actual_next_pts_required_for_final_duration_and_variable_cadence_rejected(self):
        short = deepcopy(self.frame_map[:120])
        prep = {**self.preparation, "decoded_frame_count": 120}
        with self.assertRaisesRegex(ValueError, "next-frame PTS"):
            references.join_frames(prep, short, self.frames)
        timeline, frames = deepcopy(self.frame_map), deepcopy(self.frames)
        timeline[30]["native_pts_ticks"] += 1
        timeline[30]["seconds"] = timeline[30]["native_pts_ticks"] / 15360
        frames[30].update(timeline[30])
        with self.assertRaisesRegex(ValueError, "Variable cadence"):
            references.join_frames(self.preparation, timeline, frames)

    def test_byte_hash_rgb_hash_and_dimension_change_rejected(self):
        path = self.folder / "frames/000000.png"
        original = path.read_bytes()
        path.write_bytes(original + b"changed")
        with self.assertRaisesRegex(ValueError, "binding changed"):
            self.validate()
        path.write_bytes(original)
        frames = deepcopy(self.frames)
        frames[0]["source_png"]["rgb_sha256"] = "0" * 64
        self.refresh_registry("frames", frames)
        with self.assertRaisesRegex(ValueError, "RGB hash"):
            self.validate()
        self.refresh_registry("frames", self.frames)
        self.preparation["width"] = 161
        save(self.preparation_path, self.preparation)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            self.validate()

    def test_inspection_binding_and_selection_changes_rejected(self):
        evidence = self.root / self.proposal["inspection_evidence"][0]["path"]
        evidence.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "inspection evidence binding changed"):
            self.validate()
        self.selection["new_metadata"] = "changed after preparation"
        save(self.selection_path, self.selection)
        with self.assertRaisesRegex(ValueError, "lineage"):
            self.validate()

    def test_null_canvas_no_marker_and_html_escaping(self):
        result = self.validate()
        null_canvas = references.canvas(self.root, result["frames"][0], result)
        self.assertFalse(np.any(np.all(null_canvas[40:340, 970:1270] == (0, 255, 255), axis=2)))
        marked = references.canvas(self.root, result["frames"][6], result)
        self.assertGreater(np.all(marked[40:340, 970:1270] == (0, 255, 255), axis=2).sum(), 20)
        result["frames"][0]["annotation"]["notes"] = "</script><script>bad()</script>"
        output = self.base / "viewer"
        output.mkdir()
        references.write_viewer(output, result)
        page = (output / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("</script><script>bad()", page)
        self.assertIn("\\u003c/script", page)
        self.assertIn('overlays/000119.png', page)

    def test_actual_two_frame_encoding_census_rates_markers_and_final(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg and ffprobe required for bounded real encoding check")
        manifest = self.validate()
        manifest["frames"] = [manifest["frames"][0], manifest["frames"][6]]
        manifest["frame_count"] = 2
        output = self.base / "encoding"
        output.mkdir()
        for rate in (60, 10):
            result = references.encode_review(self.root, manifest, output, f"review{rate}.mp4", rate, "bt709", "bt709")
            self.assertEqual(result["frame_count"], 2)
            self.assertEqual(result["fps"], rate)
            self.assertEqual(result["emitted_frame_checks"][-1]["source_frame_index"], 6)
            self.assertIsNotNone(result["emitted_frame_checks"][-1]["marker_pixel_error"])
            self.assertTrue((self.root / result["actual_final"]["path"]).is_file())


if __name__ == "__main__":
    unittest.main()

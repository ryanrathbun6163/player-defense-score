"""Assisted artifacts remain separate, bound to real schema producer fixtures."""
import copy
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from src.ball_tracking.prepare_nba_assisted_review import (
    SCHEMA_VERSION, prepare_review, render_frame, validate_proposal,
)
from tests.test_nba_annotations import build_fixture, observed


class AssistedReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nba_assisted_review_")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.annotation_path, self.original = build_fixture(self.root)
        self.original_bytes = self.annotation_path.read_bytes()
        self.sha = hashlib.sha256(self.original_bytes).hexdigest()
        frames = self.original["frames"]
        rows = [observed(frame["source_frame_index"]) for frame in frames]
        rows[1].update(visibility="not_visible", absence_reason="occluded", geometry=None,
                       localization_eligible=False, notes="Synthetic occlusion fixture")
        rows[2].update(visibility="partially_visible", game_ball_identity_certainty="probable",
                       notes="Synthetic partial ball fixture")
        rows[2]["geometry"].update(source="human_amodal_estimate", uncertainty_radius_px=2.0)
        self.proposal = {
            "schema_version": SCHEMA_VERSION, "candidate_id": self.original["candidate_id"],
            "source_annotation_binding": {"path": "draft.json", "sha256": self.sha},
            "origin": {"kind": "assistant_visual_proposal", "actor_id": "codex_test",
                       "method": "direct_visual_inspection_of_native_rgb_pngs",
                       "detector_predictions_used": False, "interpolation_used": False,
                       "created_at_utc": "2026-10-18T00:00:00+00:00"},
            "annotations": rows,
            "review_priority": [{"frame_index": frames[-1]["source_frame_index"],
                                 "reason": "Partial <script>alert(1)</script> fixture"}],
            "frame_inspections": [{"frame_index": f["source_frame_index"],
                                   "source_png_sha256": f["png"]["sha256"],
                                   "evidence_paths": [f["png"]["path"]],
                                   "notes": "Synthetic image inspected for test fixture"} for f in frames],
            "human_review": {"status": "pending", "reviewer_id": None, "reviewed_at_utc": None},
        }
        self.proposal_path = self.root / "assisted.json"
        self.proposal_path.write_text(json.dumps(self.proposal), encoding="utf-8")

    def validate(self, proposal=None):
        return validate_proposal(proposal or self.proposal, self.original,
                                 self.annotation_path, self.sha, self.root)

    def test_actual_schema_fixture_inventory_and_inspection_bindings(self):
        result = self.validate()
        self.assertEqual([row["frame_index"] for row in result["rows"]], [660, 661, 662])
        self.assertEqual(len(result["evidence"]), 3)
        self.assertEqual(self.annotation_path.read_bytes(), self.original_bytes)

    def test_changed_binding_inspection_or_frame_order_fails(self):
        cases = []
        changed = copy.deepcopy(self.proposal)
        changed["source_annotation_binding"]["sha256"] = "0" * 64
        cases.append(changed)
        changed = copy.deepcopy(self.proposal)
        changed["frame_inspections"][1]["source_png_sha256"] = "0" * 64
        cases.append(changed)
        changed = copy.deepcopy(self.proposal)
        changed["annotations"].reverse()
        cases.append(changed)
        changed = copy.deepcopy(self.proposal)
        changed["frame_inspections"][1]["evidence_paths"] = ["../outside.png"]
        cases.append(changed)
        for changed in cases:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.validate(changed)

    def test_human_acceptance_interpolation_and_invalid_geometry_rejected(self):
        for kind in ("review", "interpolation", "geometry"):
            changed = copy.deepcopy(self.proposal)
            if kind == "review":
                changed["human_review"]["status"] = "accepted"
            elif kind == "interpolation":
                changed["origin"]["interpolation_used"] = True
            else:
                changed["annotations"][0]["geometry"]["center_xy_px"] = [100.0, 100.0]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.validate(changed)

    def test_overlay_point_maps_source_pixels_and_missing_has_no_point(self):
        source = Image.new("RGB", (8, 6), (20, 30, 40))
        frame = self.original["frames"][0]
        image, geometry = render_frame(source, frame, self.proposal["annotations"][0])
        x, y = self.proposal["annotations"][0]["geometry"]["center_xy_px"]
        rect = geometry["source_view_rect"]
        self.assertEqual(image.getpixel((round(x * rect[2] / 8), round(78 + y * rect[3] / 6))), (0, 255, 255))
        _, missing = render_frame(source, self.original["frames"][1], self.proposal["annotations"][1])
        self.assertIsNone(missing["point_source_pixels"])
        self.assertIsNone(missing["source_crop_box"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "Installed FFmpeg/ffprobe required")
    def test_real_render_emits_every_frame_and_encoded_final_hold(self):
        ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
        output = self.root / "data/outputs/assisted"
        result = prepare_review(self.root, self.annotation_path, self.proposal_path, output, ffmpeg)
        directory = output / self.original["candidate_id"]
        self.assertEqual(result["counts"]["frames"], 3)
        self.assertEqual(result["counts"]["with_point"], 2)
        self.assertEqual(result["counts"]["exception_frames"], 2)
        self.assertEqual(result["final_source_frame_included"], 662)
        self.assertEqual(self.annotation_path.read_bytes(), self.original_bytes)
        self.assertEqual((directory / "proposal.json").read_bytes(), self.proposal_path.read_bytes())
        overlays = sorted((directory / "frames").glob("*.png"))
        self.assertEqual(len(overlays), 3)
        probe = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=nb_frames,width,height", "-of", "json",
                                str(directory / "review.mp4")], capture_output=True, check=True, timeout=30)
        video = json.loads(probe.stdout)["streams"][0]
        self.assertEqual((video["width"], video["height"], int(video["nb_frames"])), (1280, 720, 9))
        # Decode inside the actual one-second tail hold, not a manifest assertion.
        final = subprocess.run([ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error",
                                "-sseof", "-0.4", "-i", str(directory / "review.mp4"),
                                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                               capture_output=True, check=True, timeout=30)
        self.assertEqual(len(final.stdout), 1280 * 720 * 3)
        decoded = Image.frombytes("RGB", (1280, 720), final.stdout)
        with Image.open(overlays[-1]) as last:
            self.assertLess(max(ImageStat.Stat(ImageChops.difference(decoded, last)).mean), 5.0)
        page = (directory / "index.html").read_text(encoding="utf-8")
        self.assertIn("Human review pending", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)
        with self.assertRaisesRegex(ValueError, "Existing review preserved"):
            prepare_review(self.root, self.annotation_path, self.proposal_path, output, ffmpeg)
        self.assertEqual(self.annotation_path.read_bytes(), self.original_bytes)


if __name__ == "__main__":
    unittest.main()

"""SAC transport regressions using captured source records and emitted media.

No source video or model is decoded. Missing local campaign artifacts are
explicit skips; the final campaign validation requires zero skips. Test media
and failures are retained under ignored data/outputs/t.
"""
import copy
from fractions import Fraction
import hashlib
import os
from pathlib import Path
import tempfile
import traceback
import unittest
from unittest import mock

import cv2
import numpy as np

from src.ball_tracking.completion_references import read_json, write_new, binding
from src.ball_tracking import completion_sac_references as sac


class _ActualSACRecords:
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = Path(os.environ.get("SAC_REFERENCE_CONFIG", str(cls.root /
            "configs/ball_tracking/completion_campaign/nba_reference_batch_19_v0_1.json")))
        if not cls.config_path.is_file():
            raise unittest.SkipTest("Actual SAC config unavailable")
        cls.config = read_json(cls.config_path)
        cls.roles = read_json(cls.root / cls.config["source_roles"]["path"])
        sac._check_binding(cls.root, cls.config["source_roles"], "Fixed source roles")
        cls.episode = sac.guard_episode(cls.config, cls.roles)
        cls.folder = cls.root / cls.config["output_root"]
        paths = [cls.root / cls.episode["frame_list"]["path"], cls.folder / "source_frames.json",
                 cls.folder / "source_timing.json", cls.folder / "source_packet_timing.json"]
        if not all(p.is_file() for p in paths):
            raise unittest.SkipTest("Actual completed SAC producer records unavailable")
        sac._check_binding(cls.root, cls.episode["frame_list"], "Fixed frame list")
        cls.fixed, cls.pngs, cls.timing, cls.packets = [read_json(p) for p in paths]

    def join(self, **overrides):
        args = {"episode": self.episode, "fixed_frames": self.fixed, "source_frames": self.pngs,
                "source_timing": self.timing, "packet_timing": self.packets}
        args.update(overrides)
        return sac.join_native_frames(**args)


class SACSourceTransportTests(_ActualSACRecords, unittest.TestCase):
    def test_actual_packet_and_presentation_durations_remain_distinct(self):
        frames = self.join()
        self.assertEqual(len(frames), self.episode["new_frame_judgments"])
        self.assertEqual([f["native_pts_ticks"] for f in frames], [r["pts"] for r in self.fixed])
        self.assertEqual({f["presentation_duration_ticks"] for f in frames}, {1440, 1530})
        self.assertTrue(any(f["raw_packet_duration_ticks"] != f["presentation_duration_ticks"] for f in frames))
        self.assertTrue(any(p.get("duration") is None for p in self.packets["packets"]))
        self.assertEqual(frames[0]["batch_relative_seconds"], 0)
        self.assertNotEqual(frames[0]["native_pts_seconds"], frames[0]["clip_relative_seconds"])
        self.assertNotEqual(frames[-1]["source_frame_index"], self.episode["source"]["decoded_frames"] - 1)

    def test_fixed_role_pending_flags_and_native_timing_cannot_change(self):
        for key, value in (("role", "checkpoint_validation"), ("training_eligible", True),
                           ("checkpoint_selection_eligible", True), ("human_acceptance", "accepted")):
            with self.subTest(field=key), self.assertRaises(ValueError):
                sac.guard_episode({**self.config, key: value}, self.roles)
        changed = copy.deepcopy(self.config)
        changed["review"]["timing_mode"] = "cfr"
        with self.assertRaises(ValueError):
            sac.guard_episode(changed, self.roles)

    def test_native_pts_raw_duration_and_presentation_duration_are_independently_joined(self):
        for key in ("native_pts_ticks", "native_duration_ticks", "presentation_duration_ticks", "raw_packet_duration_ticks"):
            changed = copy.deepcopy(self.pngs)
            changed[0][key] += 1
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.join(source_frames=changed)
        changed = copy.deepcopy(self.fixed)
        changed[0]["pts"] += 1
        with self.assertRaises(ValueError):
            self.join(fixed_frames=changed)

    def test_selected_and_full_global_census_cannot_be_reordered_or_shortened(self):
        for changed in (self.pngs[:-1], list(reversed(self.pngs)), self.pngs[:-1] + self.pngs[:1]):
            with self.assertRaises(ValueError):
                self.join(source_frames=changed)
        packets = copy.deepcopy(self.packets)
        packets["packets"].pop()
        with self.assertRaises(ValueError):
            self.join(packet_timing=packets)

    def test_actual_png_bytes_dimensions_and_rgb_hash(self):
        for record in (self.pngs[0], self.pngs[-1]):
            sac._check_binding(self.root, record, "Source PNG")
            image = cv2.imread(str(self.root / record["path"]))
            source = self.episode["source"]
            self.assertEqual(image.shape, (source["height"], source["width"], 3))
            self.assertEqual(hashlib.sha256(cv2.cvtColor(image, cv2.COLOR_BGR2RGB).tobytes()).hexdigest(), record["rgb_sha256"])

    def test_completed_preparation_and_seek_context_are_required(self):
        evidence = sac.validate_preparation(self.root, self.folder, self.episode, self.join())
        self.assertEqual(evidence["source_pixel_audit"], binding(self.root, self.folder / "source_pixel_audit.json"))
        original = read_json
        def failed(path):
            record = original(path)
            if Path(path) == self.folder / "preparation.json":
                record["status"] = "failed"
            return record
        # Patch the record reader, not the consuming record's schema; retain all
        # other actual producer fields and hashes unchanged.
        with mock.patch("src.ball_tracking.completion_nba_references.read_json", side_effect=failed):
            with self.assertRaises(ValueError):
                sac.validate_preparation(self.root, self.folder, self.episode, self.join())

    def test_seek_context_must_preserve_global_indices_not_local_output_numbers(self):
        frames = self.join()
        decode, audit, preparation = (read_json(self.folder / name) for name in
            ("decode_audit.json", "source_pixel_audit.json", "preparation.json"))
        sac.validate_seek_context(self.episode, frames, self.packets, decode, audit, preparation)
        changed = copy.deepcopy(audit)
        changed["ffmpeg_filter_frames"][0]["source_frame_index"] = 0
        with self.assertRaises(ValueError):
            sac.validate_seek_context(self.episode, frames, self.packets, decode, changed, preparation)
        changed = copy.deepcopy(decode)
        changed["returned_frames"] = changed["returned_frames"][:-1]
        with self.assertRaises(ValueError):
            sac.validate_seek_context(self.episode, frames, self.packets, changed, audit, preparation)

    def test_actual_native_png_encode_preserves_every_pts_and_final_interval(self):
        frames = self.join()[:6]
        unit, schedule = sac.timing_schedule(frames)
        folder = Path(tempfile.mkdtemp(prefix="sac_actual_transport_test_", dir=self.root / "data/outputs/t"))
        write_new(folder / "inputs.json", {"source_frames": [f["source_png"] for f in frames],
            "timing": [list(pair) for pair in schedule], "time_base": str(unit),
            "source_video_decoded": False, "labels_created": 0})
        try:
            canvases = [cv2.resize(cv2.imread(str(self.root / f["source_png"]["path"])), (1280, 720)) for f in frames]
            video = folder / "native.mp4"
            sac.encode_review_video(video, iter(canvases), schedule, unit, "bt709", "bt709")
            probe = sac.probe_encoded_video(video)
            write_new(folder / "probe.json", probe)
            checked = sac.validate_encoded_timing(probe, schedule, unit, "bt709", "bt709")
            self.assertEqual(len(checked), len(frames))
            self.assertEqual(checked[-1]["encoded_duration_ticks"], frames[-1]["presentation_duration_ticks"])
            capture = cv2.VideoCapture(str(video))
            errors = []
            try:
                for expected in canvases:
                    ok, actual = capture.read()
                    self.assertTrue(ok)
                    errors.append(float(np.abs(actual.astype(np.int16) - expected.astype(np.int16)).mean()))
                self.assertFalse(capture.read()[0])
            finally:
                capture.release()
            self.assertLess(max(errors), 8)
            write_new(folder / "passed.json", {"status": "passed", "checked": checked, "pixel_errors": errors})
        except BaseException:
            write_new(folder / "failure.json", {"status": "failed", "traceback": traceback.format_exc()})
            raise

    def test_emitted_timing_rejects_wrong_final_duration_or_silent_cfr(self):
        # This fixture is the actual independently emitted diagnostic, never a
        # hand-authored object mirroring the validation function.
        candidates = sorted((self.root / "data/outputs/t").glob("sac_actual_transport_test_*/passed.json"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            self.skipTest("No actual emitted SAC regression transport exists")
        folder = candidates[-1].parent
        inputs, original = read_json(folder / "inputs.json"), read_json(folder / "probe.json")
        schedule = [tuple(row) for row in inputs["timing"]]
        for mutation in ("final_duration", "cfr_pts"):
            probe = copy.deepcopy(original)
            packets = [r for r in probe["packets_and_frames"] if r["type"] == "packet"]
            if mutation == "final_duration":
                packets[-1]["duration"] = 1500
            else:
                packets[1]["pts"] = 1500
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                sac.validate_encoded_timing(probe, schedule, Fraction(inputs["time_base"]), "bt709", "bt709")


class SACCurrentReviewTests(_ActualSACRecords, unittest.TestCase):
    def test_actual_current_proposal_and_complete_native_slow_media(self):
        proposal = Path(os.environ.get("SAC_REFERENCE_PROPOSAL", str(self.folder / "proposal.json")))
        review = Path(os.environ.get("SAC_REFERENCE_REVIEW_DIR", str(self.folder / "review_v1")))
        if not proposal.is_file() or not (review / "manifest.json").is_file():
            self.skipTest("Current actual proposal and complete review media unavailable")
        config, validated = sac.validate_batch(self.root, self.config_path, proposal)
        manifest = read_json(review / "manifest.json")
        self.assertEqual(manifest["frames"], validated["frames"])
        self.assertEqual(manifest["proposal"], binding(self.root, proposal))
        self.assertEqual(len(manifest["videos"]), 2)
        for index, video in enumerate(manifest["videos"]):
            checked = sac.validate_video_timing(self.root, video, validated["frames"], config["review"]["slow_playback_fps"], index == 0)
            self.assertEqual(len(checked), len(self.fixed))
        self.assertEqual(manifest["videos"][0]["fps"], None)
        self.assertEqual(manifest["videos"][1]["fps"], 10)


if __name__ == "__main__":
    unittest.main()

"""NBA transport checks derived from actual fixed selection and PNG producer output.

Ignored source records are required for integration tests. No source video is
decoded, no labels are accepted, and no consumer-shaped records replace the
producer's field names, frame census, native timestamps or image hashes.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import cv2
import numpy as np

from src.ball_tracking.completion_references import read_json
from src.ball_tracking.completion_nba_references import (
    _check_binding, _check_proposal, guard_episode, join_native_frames,
    render_frame, review_encoding_command, validate_batch, validate_preparation,
)


class _ActualNBARecords:
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = cls.root / "configs/ball_tracking/completion_campaign/nba_reference_batch_01_v0_1.json"
        if not cls.config_path.is_file():
            raise unittest.SkipTest("Actual NBA batch01 config is not available")
        cls.config = read_json(cls.config_path)
        cls.roles = read_json(cls.root / cls.config["source_roles"]["path"])
        _check_binding(cls.root, cls.config["source_roles"], "Fixed source-role manifest")
        cls.episode = guard_episode(cls.config, cls.roles)
        cls.folder = cls.root / cls.config["output_root"]
        paths = [cls.root / cls.episode["frame_list"]["path"], cls.folder / "source_frames.json",
                 cls.folder / "source_timing.json", cls.folder / "source_packet_timing.json"]
        if not all(p.is_file() for p in paths):
            raise unittest.SkipTest("Actual NBA source producer records are not available")
        _check_binding(cls.root, cls.episode["frame_list"], "Fixed episode frame list")
        cls.fixed, cls.pngs, cls.timing, cls.packets = [read_json(p) for p in paths]

    def join(self, **overrides):
        fields = {"episode": self.episode, "fixed_frames": self.fixed, "source_frames": self.pngs,
                  "source_timing": self.timing, "packet_timing": self.packets}
        fields.update(overrides)
        return join_native_frames(**fields)


class FixedNBAEpisodeTests(_ActualNBARecords, unittest.TestCase):
    def test_actual_producer_join_preserves_native_pts_and_batch_source_finals(self):
        frames = self.join()
        self.assertEqual(len(frames), 120)
        self.assertEqual([f["source_frame_index"] for f in frames], list(range(120)))
        self.assertEqual([f["native_pts_ticks"] for f in frames], list(range(0, 120000, 1000)))
        self.assertEqual({f["native_time_base"] for f in frames}, {"1/60000"})
        self.assertEqual({f["native_duration_ticks"] for f in frames}, {1000})
        self.assertEqual(frames[-1]["native_pts_seconds"], 119 / 60)
        self.assertEqual(frames[0]["clip_relative_seconds"], 0)
        self.assertEqual(frames[0]["batch_relative_seconds"], 0)
        self.assertEqual(self.episode["source"]["decoded_frames"] - 1, 662)
        self.assertNotEqual(frames[-1]["source_frame_index"], 662)

    def test_fixed_game_role_and_pending_flags_cannot_change(self):
        self.assertEqual(guard_episode(self.config, self.roles)["role"], "training")
        changes = {"role": "checkpoint_validation", "training_eligible": True,
                   "checkpoint_selection_eligible": True, "human_acceptance": "accepted",
                   "annotation_origin": "human"}
        for key, value in changes.items():
            with self.subTest(field=key), self.assertRaises(ValueError):
                guard_episode({**self.config, key: value}, self.roles)
        roles = copy.deepcopy(self.roles)
        next(g for g in roles["game_roles"] if g["game_id"] == self.episode["game_id"])["role"] = "checkpoint_validation"
        with self.assertRaisesRegex(ValueError, "role"):
            guard_episode(self.config, roles)

    def test_authority_hash_is_required_not_just_path(self):
        changed = {**self.config["source_roles"], "sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "binding changed"):
            _check_binding(self.root, changed, "Fixed source-role manifest")

    def test_native_review_rate_and_whole_batch_review_cannot_change(self):
        changed = copy.deepcopy(self.config)
        changed["review"]["native_playback_fps"] = 25
        with self.assertRaisesRegex(ValueError, "native playback rate differs"):
            guard_episode(changed, self.roles)
        changed = copy.deepcopy(self.config)
        changed["review"]["whole_batch_required"] = False
        with self.assertRaisesRegex(ValueError, "visual review"):
            guard_episode(changed, self.roles)

    def test_actual_source_census_rejects_missing_reordered_or_duplicated_rows(self):
        variants = [self.pngs[:-1], self.pngs[1:] + self.pngs[:1], self.pngs[:-1] + self.pngs[:1]]
        for rows in variants:
            with self.subTest(indices=[r["frame_index"] for r in rows[:2]]), self.assertRaisesRegex(ValueError, "census"):
                self.join(source_frames=rows)
        with self.assertRaisesRegex(ValueError, "census"):
            self.join(source_timing=list(reversed(self.timing)))

    def test_source_native_offset_duration_and_fixed_frame_pts_must_agree(self):
        for key, value in (("native_pts_ticks", 512), ("native_duration_ticks", 512),
                           ("native_time_base", "1/12800")):
            pngs = copy.deepcopy(self.pngs)
            pngs[0][key] = value
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, "native PTS or duration"):
                self.join(source_frames=pngs)
        fixed = copy.deepcopy(self.fixed)
        fixed[0]["pts"] = 512
        with self.assertRaisesRegex(ValueError, "frame-list PTS"):
            self.join(fixed_frames=fixed)
        timing = copy.deepcopy(self.timing)
        timing[0]["decoded_frame_duration_ticks"] = 512
        with self.assertRaisesRegex(ValueError, "Decoded source timing"):
            self.join(source_timing=timing)

    def test_actual_png_bytes_and_rgb_transport_match_independent_reader(self):
        # OpenCV reads lossless saved PNGs, never the copyrighted source video.
        # RGB24 hashing is the producer's documented contiguous row-major format.
        for png in (self.pngs[0], self.pngs[-1]):
            with self.subTest(frame=png["frame_index"]):
                _check_binding(self.root, png, "Source PNG")
                image = cv2.imread(str(self.root / png["path"]))
                self.assertEqual(image.shape, (720, 1280, 3))
                self.assertEqual(hashlib.sha256(cv2.cvtColor(image, cv2.COLOR_BGR2RGB).tobytes()).hexdigest(),
                                 png["rgb_sha256"])

    def test_completed_preparation_binds_actual_passed_pixel_audit_and_failure_history(self):
        evidence = validate_preparation(self.root, self.folder, self.episode, self.join())
        preparation = read_json(self.folder / "preparation.json")
        self.assertEqual(evidence["source_pixel_audit"], preparation["source_pixel_audit"])
        self.assertIn(preparation["original_failed_attempt"], evidence["source_preparation_evidence"])
        self.assertEqual(read_json(self.root / evidence["source_pixel_audit"]["path"])["exact_matches"], 120)

    def test_actual_one_frame_encode_preserves_declared_primaries_and_transfer(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg and ffprobe are required for the emitted-metadata regression")
        source_color = read_json(self.folder / "source_pixel_audit.json")["source_color_metadata"]
        image = cv2.imread(str(self.root / self.pngs[0]["path"]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actual_source_frame_review.mp4"
            command = review_encoding_command(path, 60, source_color["color_primaries"], source_color["color_transfer"])
            subprocess.run(command, input=image.tobytes(), check=True, capture_output=True)
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=nb_frames,color_space,color_range,color_primaries,color_transfer",
                                    "-of", "json", str(path)], check=True, capture_output=True, text=True)
            stream = json.loads(probe.stdout)["streams"][0]
            self.assertEqual(stream["nb_frames"], "1")
            self.assertEqual(stream["color_space"], "smpte170m")
            self.assertEqual(stream["color_range"], "tv")
            self.assertEqual(stream.get("color_primaries"), source_color["color_primaries"])
            self.assertEqual(stream.get("color_transfer"), source_color["color_transfer"])

    def test_missing_or_failed_preparation_and_failed_partial_pixel_audit_are_rejected(self):
        # Clone only actual producer JSON for these pre-binding failures. No
        # authoritative files or source pixels are changed by a negative test.
        original_preparation = read_json(self.folder / "preparation.json")
        original_audit = read_json(self.folder / "source_pixel_audit.json")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaisesRegex(ValueError, "preparation.*required"):
                validate_preparation(folder, folder, self.episode, self.join())
            variants = [("preparation", "status", "failed"), ("audit", "status", "failed"),
                        ("audit", "exact_matches", 119), ("audit", "native_pts_matches", 119),
                        ("audit", "failures", 1)]
            for owner, field, value in variants:
                preparation, audit = copy.deepcopy(original_preparation), copy.deepcopy(original_audit)
                (preparation if owner == "preparation" else audit)[field] = value
                (folder / "preparation.json").write_text(json.dumps(preparation), encoding="utf-8")
                (folder / "source_pixel_audit.json").write_text(json.dumps(audit), encoding="utf-8")
                with self.subTest(record=owner, field=field), self.assertRaisesRegex(ValueError, "preparation|audit"):
                    validate_preparation(folder, folder, self.episode, self.join())


class ActualNBAProposalTests(_ActualNBARecords, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.proposal_path = cls.folder / "proposal.json"
        if not cls.proposal_path.is_file():
            raise unittest.SkipTest("Actual pending NBA proposal is not yet available")
        cls.proposal = read_json(cls.proposal_path)

    def test_actual_pending_proposal_and_all_source_pixels_validate(self):
        _, manifest = validate_batch(self.root, self.config_path, self.proposal_path)
        self.assertEqual([f["annotation"] for f in manifest["frames"]], self.proposal["annotations"])
        self.assertEqual(manifest["role"], "training")
        self.assertFalse(manifest["training_eligible"])
        self.assertFalse(manifest["checkpoint_selection_eligible"])
        self.assertIsNone(manifest["human_acceptance"])
        self.assertEqual(manifest["validation"]["native_source_frame_and_pts_joins_checked"], 120)

    def test_actual_proposal_cannot_flip_eligibility_role_or_acceptance(self):
        for key, value in (("training_eligible", True), ("checkpoint_selection_eligible", True),
                           ("human_acceptance", "accepted"), ("role", "checkpoint_validation"),
                           ("game_id", "0022500828"), ("episode_id", "wrong_episode")):
            changed = {**self.proposal, key: value}
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, "Proposal identity"):
                _check_proposal(self.config, self.episode, changed)

    def test_actual_point_scales_from_1280_pixels_and_null_retains_no_marker(self):
        frames = self.join()
        point = next(row for row in self.proposal["annotations"] if row["geometry"] is not None)
        item = {**frames[point["frame_index"]], "annotation": point}
        blank = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = render_frame(blank, item, 120, self.episode["episode_id"], "training", 119, 662)
        x, y = point["geometry"]["center_xy_px"]
        self.assertEqual(result[round(y * 540 / 720), round(x * 960 / 1280)].tolist(), [0, 255, 255])
        null = next((row for row in self.proposal["annotations"] if row["geometry"] is None), None)
        if null is not None:
            item = {**frames[null["frame_index"]], "annotation": null}
            result = render_frame(blank, item, 120, self.episode["episode_id"], "training", 119, 662)
            self.assertFalse(result[40:340, 970:1270].any())
            self.assertFalse(result[:540, :960].any())


if __name__ == "__main__":
    unittest.main()

"""Native input transport using a real tiny FFmpeg producer, never NBA media."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from src.ball_tracking import nba_action_inputs as inputs
from src.ball_tracking import nba_wasb_diagnostic as evidence
from src.ball_tracking.prepare_nba_annotation_pilot import extraction_command, parse_framehash, source_stat

FFBIN = Path("C:/Users/Ryan/AppData/Local/Microsoft/WinGet/Packages/"
             "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0-full_build/bin")
FFMPEG = shutil.which("ffmpeg") or (str(FFBIN / "ffmpeg.exe") if (FFBIN / "ffmpeg.exe").is_file() else None)
FFPROBE = shutil.which("ffprobe") or (str(FFBIN / "ffprobe.exe") if (FFBIN / "ffprobe.exe").is_file() else None)


@unittest.skipUnless(FFMPEG and FFPROBE, "FFmpeg/ffprobe required for native producer test")
class NBAActionInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="nba_action_producer_")
        cls.addClassCleanup(temporary.cleanup)
        cls.producer = Path(temporary.name)
        cls.source = cls.producer / "source.mp4"
        cls.process([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-n",
                     "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=60", "-frames:v", "10",
                     "-vf", r"settb=1/90000,setpts=3000+floor(N/2)*2970+mod(N\,2)*1440",
                     "-an", "-c:v", "libx264", "-threads", "1", "-bf", "2", "-pix_fmt", "yuv420p",
                     "-fps_mode", "passthrough", "-enc_time_base", "1:90000",
                     "-video_track_timescale", "90000", str(cls.source)])
        result = cls.process([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_frames",
                              "-show_entries", "frame=pts", "-of", "json", str(cls.source)])
        cls.pts = [row["pts"] for row in json.loads(result.stdout)["frames"]]
        oracle = cls.producer / "oracle.framehash"
        cls.process([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-n",
                     "-copyts", "-i", str(cls.source), "-map", "0:v:0", "-an", "-vf", "format=rgb24",
                     "-c:v", "rawvideo", "-threads", "1", "-pix_fmt", "rgb24", "-fps_mode", "passthrough",
                     "-enc_time_base", "1:90000", "-f", "framehash", "-hash", "sha256", str(oracle)])
        cls.oracle = parse_framehash(oracle)
        cls.old_dir = cls.producer / "old"
        (cls.old_dir / "frames").mkdir(parents=True)
        cls.process(extraction_command(FFMPEG, cls.source, cls.old_dir, 3, cls.pts[3], cls.pts[5]))

    @staticmethod
    def process(command):
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(f"Synthetic producer failed: {result.stderr}")
        return result

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nba_action_inputs_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.original = self.root / "source.mp4"
        shutil.copyfile(self.source, self.original)
        source = {"path": "source.mp4", "sha256": evidence.digest(self.original),
                  "width_px": 64, "height_px": 48, "frame_count": 10}
        self.save("audit.json", {"sha256": source["sha256"], "source_stat_after": source_stat(self.original)})
        self.rows = [{"clip_frame_index": index, "source_frame_index": index, "source_pts_ticks": pts,
                      "clip_pts_ticks": pts - self.pts[0], "time_base": "1/90000"}
                     for index, pts in enumerate(self.pts)]
        (self.root / "frame_map.jsonl").write_text("".join(json.dumps(row) + "\n" for row in self.rows), encoding="utf-8")
        frames = []
        for index in (3, 4):
            path = self.root / f"old_{index}.png"
            shutil.copyfile(self.old_dir / "frames" / f"source_{index:06d}.png", path)
            with Image.open(path) as image:
                rgb = hashlib.sha256(image.tobytes()).hexdigest()
            frames.append({"source_frame_index": index, "source_pts_ticks": self.pts[index],
                           "png": {"path": path.name, "sha256": evidence.digest(path), "rgb_sha256": rgb}})
        self.reference = {"candidate_id": "synthetic_action", "game_id": "synthetic_game",
                          "approved_role": "target_case_development", "source_video": source,
                          "time_base": "1/90000", "frames": frames}
        self.window = {key: copy.deepcopy(value) for key, value in self.reference.items() if key != "frames"}
        self.window.update(source_verification={"audit": self.bind("audit.json"), "hash_field": "sha256",
                            "stat_field": "source_stat_after", "source_stat": source_stat(self.original)},
                           source_frame_range_inclusive=[1, 8], source_pts_ticks_inclusive=[self.pts[1], self.pts[8]],
                           source_end_exclusive_pts_ticks=self.pts[9], frames=8, reused_native_png_frames=2,
                           new_native_png_frames=6, frame_map=self.bind("frame_map.jsonl"))
        self.proposal = {"schema_version": "nba_wasb_action_observation_proposal/v0.1",
                         "proposal_id": "synthetic_action", "windows": [self.window]}
        self.refresh_approval()
        self.output = self.root / "data/outputs/inputs"

    def save(self, name, data):
        (self.root / name).write_text(json.dumps(data), encoding="utf-8")

    def bind(self, name):
        return evidence.binding(self.root, self.root / name)

    def refresh_approval(self):
        self.save("proposal.json", self.proposal)
        self.approval = {"schema_version": "nba_wasb_action_observation_approval/v0.1", "status": "approved",
                         "approved_by": "Ryan", "proposal": self.bind("proposal.json")}
        self.save("approval.json", self.approval)
        self.approval_binding = self.bind("approval.json")

    def prepare(self):
        return inputs.prepare_inputs(self.root, self.proposal, self.approval_binding,
                                     [self.reference], self.output, FFMPEG)

    def test_actual_native_transport_reuses_original_records_and_has_no_annotations(self):
        reference = copy.deepcopy(self.reference)
        original_bytes = {f["png"]["path"]: (self.root / f["png"]["path"]).read_bytes() for f in reference["frames"]}
        manifest = self.prepare()[0]
        self.assertEqual(self.pts, [row["pts"] for row in self.oracle])
        self.assertEqual(manifest["source_end_exclusive_pts_ticks"], self.pts[9])
        self.assertNotIn("annotations", manifest)
        self.assertEqual(manifest["preparation"]["annotations_created"], 0)
        self.assertEqual([f["source_frame_index"] for f in manifest["frames"]], list(range(1, 9)))
        for frame in manifest["frames"]:
            index = frame["source_frame_index"]
            self.assertEqual(frame["source_pts_ticks"], self.oracle[index]["pts"])
            self.assertEqual(frame["png"]["rgb_sha256"], self.oracle[index]["rgb_sha256"])
        self.assertEqual(manifest["frames"][2:4], reference["frames"])
        self.assertEqual(self.reference, reference)
        for name, expected in original_bytes.items():
            self.assertEqual((self.root / name).read_bytes(), expected)
        self.assertEqual(len(list(self.output.glob("*/range_*/attempts/*/started.json"))), 2)

    def test_completed_resume_no_decode_no_original_hash_and_exact_manifest(self):
        first = self.prepare()
        real_digest = evidence.digest
        def no_original_hash(path):
            self.assertNotEqual(Path(path).resolve(), self.original.resolve(), "Original recording was rehashed")
            return real_digest(path)
        with patch.object(inputs.subprocess, "run", side_effect=AssertionError("Completed inputs decoded again")), \
             patch.object(evidence, "digest", side_effect=no_original_hash):
            second = self.prepare()
        self.assertEqual(second, first)

    def test_approval_scope_and_original_stat_refuse_before_output(self):
        self.approval["status"] = "pending"
        self.save("approval.json", self.approval)
        self.approval_binding = self.bind("approval.json")
        with self.assertRaisesRegex(ValueError, "approved scope"):
            self.prepare()
        self.assertFalse(self.output.exists())
        self.refresh_approval()
        self.proposal["windows"][0]["new_native_png_frames"] = 7
        with self.assertRaisesRegex(ValueError, "different proposal"):
            self.prepare()
        self.assertFalse(self.output.exists())
        self.proposal["windows"][0]["new_native_png_frames"] = 6
        with self.original.open("ab") as handle:
            handle.write(b"changed-source")
        with self.assertRaisesRegex(ValueError, "size/mtime changed"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_actual_producer_map_wrong_cadence_refuses_before_extract(self):
        self.rows[6]["source_pts_ticks"] += 1
        (self.root / "frame_map.jsonl").write_text("".join(json.dumps(row) + "\n" for row in self.rows), encoding="utf-8")
        self.window["frame_map"] = self.bind("frame_map.jsonl")
        self.refresh_approval()
        with patch.object(inputs.subprocess, "run", side_effect=AssertionError("Bad cadence decoded")), \
             self.assertRaisesRegex(ValueError, "native cadence"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_failed_second_range_preserved_completed_first_not_redecoded(self):
        real_run = subprocess.run
        calls = []
        def fail_second(*args, **kwargs):
            calls.append(args[0])
            if len(calls) == 2:
                raise RuntimeError("synthetic extraction interruption")
            return real_run(*args, **kwargs)
        with patch.object(inputs.subprocess, "run", side_effect=fail_second), \
             self.assertRaisesRegex(RuntimeError, "synthetic extraction interruption"):
            self.prepare()
        self.assertEqual(len(list(self.output.glob("*/range_*/completion.json"))), 1)
        self.assertEqual(len(list(self.output.glob("*/range_*/attempts/*/failed.json"))), 1)
        with patch.object(inputs.subprocess, "run", wraps=real_run) as resumed:
            manifest = self.prepare()[0]
        self.assertEqual(resumed.call_count, 1)
        self.assertEqual(len(manifest["frames"]), 8)
        self.assertEqual(len(list(self.output.glob("*/range_*/attempts/*/started.json"))), 3)
        self.assertEqual(len(list(self.output.glob("*/range_*/attempts/*/failed.json"))), 1)

    def test_completed_png_corruption_refuses_without_redecode(self):
        manifest = self.prepare()[0]
        path = self.root / manifest["frames"][0]["png"]["path"]
        with path.open("ab") as handle:
            handle.write(b"corruption")
        with patch.object(inputs.subprocess, "run", side_effect=AssertionError("Corrupt completed PNG replaced")), \
             self.assertRaisesRegex(ValueError, "PNG hash mismatch"):
            self.prepare()

    def test_completed_attempt_recovers_after_pointer_write_failure_without_redecode(self):
        real_write = evidence.write_once
        failed = False
        def fail_pointer(path, value):
            nonlocal failed
            path = Path(path)
            if path.name == "completion.json" and not failed:
                failed = True
                raise OSError("synthetic completion pointer delivery failure")
            return real_write(path, value)
        with patch.object(evidence, "write_once", side_effect=fail_pointer), \
             self.assertRaisesRegex(OSError, "pointer delivery failure"):
            self.prepare()
        self.assertEqual(len(list(self.output.glob("*/range_*/attempts/*/completed.json"))), 1)
        self.assertEqual(len(list(self.output.glob("*/range_*/completion.json"))), 0)
        real_run = subprocess.run
        with patch.object(inputs.subprocess, "run", wraps=real_run) as resumed:
            result = self.prepare()
        self.assertEqual(resumed.call_count, 1)  # Only the previously unstarted second range.
        self.assertEqual(len(result[0]["frames"]), 8)
        self.assertEqual(len(list(self.output.glob("*/range_*/attempts/*/started.json"))), 2)
        self.assertEqual(len(list(self.output.glob("*/range_*/attempts/*/failed.json"))), 1)


if __name__ == "__main__":
    unittest.main()

"""Exercise native-PTS extraction against real, tiny FFmpeg producer records."""

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from src.ball_tracking.prepare_nba_annotation_pilot import (
    extraction_command,
    parse_framehash,
)


FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


@unittest.skipUnless(FFMPEG and FFPROBE, "Installed FFmpeg and ffprobe required")
class NativePreparationProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="nba_preparation_test_")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.source = cls.root / "synthetic_vfr.mp4"
        # A late selection exercises a positive input seek. Alternating 16/17ms
        # timestamps and B-frames expose nominal-fps and packet-order mistakes.
        cls.expected_pts = [3000 + (n // 2) * 2970 + (n % 2) * 1440
                            for n in range(300)]
        cls.run_process([
            FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-n",
            "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=60:duration=5",
            "-vf", r"settb=1/90000,setpts=3000+floor(N/2)*2970+mod(N\,2)*1440",
            "-an", "-c:v", "libx264", "-threads", "1", "-g", "24",
            "-bf", "2", "-pix_fmt", "yuv420p", "-fps_mode", "passthrough",
            "-enc_time_base", "1:90000", "-video_track_timescale", "90000",
            str(cls.source),
        ])
        probe = cls.run_process([
            FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_packets",
            "-show_entries", "packet=pts", "-of", "csv=p=0", str(cls.source),
        ])
        cls.packet_pts = sorted(int(line) for line in probe.stdout.splitlines()
                                if line.strip())
        # The independent oracle decodes the complete SMALL synthetic source
        # without seeking or trimming. No NBA source or existing holdout is read.
        cls.oracle_path = cls.root / "direct_all_rgb.framehash"
        cls.run_process([
            FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-n",
            "-copyts", "-noautorotate", "-hwaccel", "none", "-threads", "1",
            "-i", str(cls.source), "-map", "0:v:0", "-an", "-vf", "format=rgb24",
            "-c:v", "rawvideo", "-threads", "1", "-pix_fmt", "rgb24",
            "-fps_mode", "passthrough", "-enc_time_base", "1:90000",
            "-f", "framehash", "-hash", "sha256", str(cls.oracle_path),
        ])
        cls.oracle = parse_framehash(cls.oracle_path)
        cls.directory = cls.root / "selected"
        (cls.directory / "frames").mkdir(parents=True)
        cls.command = extraction_command(
            FFMPEG, cls.source, cls.directory, 260,
            cls.expected_pts[260], cls.expected_pts[270],
        )
        cls.extraction = cls.run_process(cls.command)
        cls.produced_path = cls.directory / "source_rgb_framehash.txt"
        cls.produced = parse_framehash(cls.produced_path)

    @staticmethod
    def run_process(command):
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(
                f"FFmpeg producer failed ({result.returncode}): {command!r}\n"
                f"stdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def test_actual_vfr_pts_pngs_and_rgb_equal_independent_original_decode(self):
        self.assertEqual(self.packet_pts, self.expected_pts)
        self.assertEqual([row["pts"] for row in self.oracle], self.expected_pts)
        self.assertEqual(self.produced, self.oracle[260:270])
        self.assertEqual({b - a for a, b in zip(self.expected_pts[260:269],
                                               self.expected_pts[261:270])},
                         {1440, 1530})
        files = sorted((self.directory / "frames").glob("*.png"))
        self.assertEqual([path.name for path in files],
                         [f"source_{index:06d}.png" for index in range(260, 270)])
        for path, record in zip(files, self.oracle[260:270]):
            with self.subTest(path=path.name), Image.open(path) as image:
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, (64, 48))
                self.assertEqual(len(image.tobytes()), record["bytes"])
                self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(),
                                 record["rgb_sha256"])

    def test_fastseek_is_bounded_before_input_without_nominal_fps_conversion(self):
        input_index = self.command.index("-i")
        self.assertLess(self.command.index("-t"), input_index)
        self.assertGreater(float(self.command[self.command.index("-ss") + 1]), 0)
        self.assertLess(float(self.command[self.command.index("-t") + 1]), 5)
        self.assertNotIn("-r", self.command)
        self.assertNotIn("-start_at_zero", self.command)
        self.assertNotIn("-frames:v", self.command)

    def test_actual_producer_record_rejects_changed_timebase_and_stream(self):
        original = self.produced_path.read_text(encoding="utf-8")
        changed_timebase = self.root / "wrong_timebase.framehash"
        changed_timebase.write_text(original.replace("#tb 0: 1/90000", "#tb 0: 1/60"),
                                    encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "90 kHz"):
            parse_framehash(changed_timebase)
        changed_stream = self.root / "wrong_stream.framehash"
        lines = original.splitlines()
        row_index = next(i for i, line in enumerate(lines)
                         if line.strip() and not line.startswith("#"))
        fields = lines[row_index].split(",")
        fields[0] = "1"
        lines[row_index] = ",".join(fields)
        changed_stream.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unexpected framehash row"):
            parse_framehash(changed_stream)


if __name__ == "__main__":
    unittest.main()

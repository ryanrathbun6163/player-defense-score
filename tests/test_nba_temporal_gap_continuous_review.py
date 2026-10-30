"""Synthetic streaming/transport tests; no project footage, labels or model calls."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_temporal_gap_continuous_review as render
from src.ball_tracking import nba_action_review as review
from tests.test_nba_annotations import build_fixture
from tests.test_nba_wasb_diagnostic import FFBIN


def attach_components(rows):
    for row in rows:
        if row["decision"] == "withheld":
            continue
        point = row["selected_center_xy_px"]
        component = None if point is None else {"candidate_index": 0, "center_x": point[0], "center_y": point[1], "native_score": 1.}
        provenance = None if point is None else [row["candidate_id"], row["source_frame_index"], "synthetic_saved_component"]
        row.update(original_observation={"center_xy_px": row["baseline_center_xy_px"]},
                   selected_component=component, selected_pool_record_index=None if point is None else 0,
                   selected_native_score=None if point is None else 1., selected_provenance_id=provenance,
                   candidate_pool={"records": [] if point is None else [{"component": component, "provenance_id": provenance}]})
    return rows


def nba_fixture(root):
    _, manifest = build_fixture(root)
    manifest["source_end_exclusive_pts_ticks"] = manifest["frames"][-1]["source_pts_ticks"]+1530
    path = root/"native_source_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    rows = [{"candidate_id": manifest["candidate_id"], "source_frame_index": frame["source_frame_index"],
             "source_pts_ticks": frame["source_pts_ticks"], "source_frame": frame,
             "baseline_center_xy_px": None if i == 1 else [3., 2.], "selected_center_xy_px": [3., 2.],
             "decision": "filled_saved_candidate" if i == 1 else "preserved_original", "segment_id": "nba_segment"}
            for i, frame in enumerate(manifest["frames"])]
    attach_components(rows)
    return {"candidate_id": manifest["candidate_id"], "kind": "nba", "source_video": manifest["source_video"],
            "source_manifest": review.binding(root, path), "source_end_exclusive_pts_ticks": manifest["source_end_exclusive_pts_ticks"],
            "protected_ranges": [], "frames": rows,
            "segments": [{"segment_id": "nba_segment", "range_inclusive": [660, 662], "frames": rows, "gaps": []}]}


def nfhs_fixture(root):
    """Create nine color-coded source frames with a protected three-slot band."""
    import av
    path = root/"data/clips/possession_fixture.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), "w") as container:
        stream = container.add_stream("libx264", rate=25, options={"crf": "18", "bf": "0"})
        stream.width, stream.height, stream.pix_fmt = 64, 36, "yuv420p"
        for i in range(9):
            frame = av.VideoFrame.from_image(Image.new("RGB", (64, 36), (i*20, 30, 60)))
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    player_path = root/"players.csv"
    player_path.write_text("frame_index,player_id,floor_x,floor_y\n0,reviewed_A,12,12\n3,must_not_display,5,5\n6,reviewed_B,22,22\n", encoding="utf-8")
    metadata = {"path": path.relative_to(root).as_posix(), "sha256": review.binding(root, path)["sha256"],
                "width_px": 64, "height_px": 36, "fps": 25., "frame_count": 9}
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        packets = [{"pts": str(packet.pts), "duration": str(packet.duration)}
                   for packet in container.demux(stream) if packet.pts is not None]
        probe = {"streams": [{"time_base": str(stream.time_base), "nb_frames": str(stream.frames),
                              "width": stream.width, "height": stream.height}], "packets": packets}
    probe_path = root/"packets.json"
    probe_path.write_text(json.dumps(probe), encoding="utf-8")
    origin = int(min(int(p["pts"]) for p in packets)*Fraction(probe["streams"][0]["time_base"])*90000)
    timed = [{"source_frame_index": i, "source_pts_ticks": i*3600,
              "container_pts_ticks": origin+i*3600, "duration_ticks": 3600} for i in range(9)]
    timing = {"schema_version": "nfhs_container_native_timestamps/v0.1", "status": "verified",
              "candidate_id": "possession_fixture", "source_video": metadata, "time_base": "1/90000",
              "time_origin": "clip_first_frame", "container_time_origin_ticks": origin,
              "original_time_base": probe["streams"][0]["time_base"], "actual_source_binding": review.binding(root, path),
              "packet_probe": review.binding(root, probe_path), "source_end_exclusive_pts_ticks": 9*3600,
              "container_end_exclusive_pts_ticks": origin+9*3600, "frames": timed}
    timing_path = root/"timestamps.json"
    timing_path.write_text(json.dumps(timing), encoding="utf-8")
    possession = {"possession_id": "possession_fixture", "source_video": metadata,
                  "protected_ranges": [[3, 5]], "visible_segments": [[0, 2], [6, 8]],
                  "player_context": review.binding(root, player_path)}
    rows = []
    for i in range(9):
        protected = 3 <= i <= 5
        rows.append({"candidate_id": "possession_fixture", "source_frame_index": i, "source_pts_ticks": i*3600,
                     "container_pts_ticks": timed[i]["container_pts_ticks"], "source_frame": timed[i],
                     "baseline_center_xy_px": None if protected or i == 1 else [30., 20.],
                     "selected_center_xy_px": None if protected else [30., 20.],
                     "decision": "withheld" if protected else "filled_saved_candidate" if i == 1 else "preserved_original",
                     "segment_id": None if protected else "before" if i < 3 else "after"})
    attach_components(rows)
    return {"candidate_id": "possession_fixture", "kind": "nfhs", "source_video": metadata,
            "time_origin": "clip_first_frame", "native_timestamps": review.binding(root, timing_path),
            "possession": possession, "protected_ranges": [[3, 5]], "frames": rows,
            "segments": [{"segment_id": "before", "range_inclusive": [0, 2], "frames": rows[:3], "gaps": []},
                         {"segment_id": "after", "range_inclusive": [6, 8], "frames": rows[6:], "gaps": []}]}


class ContinuousGapReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gap_continuous_review_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = nba_fixture(self.root)

    def test_native_nba_timeline_manifest_join_and_final_hold(self):
        records = render.validate_source(self.root, self.source)
        self.assertEqual([r["review_pts_ticks"] for r in records], [0, 1440, 2970])
        self.assertEqual([r["duration_ticks"] for r in records], [1440, 1530, 91530])
        self.assertEqual([r["source_png"] for r in records], [r["source_frame"]["png"] for r in self.source["frames"]])
        bad = copy.deepcopy(self.source)
        bad["frames"][1]["source_pts_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "cadence|mapping"):
            render.validate_source(self.root, bad)
        bad = copy.deepcopy(self.source)
        bad["frames"][1]["source_frame"]["png"] = bad["frames"][0]["source_frame"]["png"]
        with self.assertRaisesRegex(ValueError, "manifest join"):
            render.validate_source(self.root, bad)

    def test_reject_changed_original_and_segment_join(self):
        bad = copy.deepcopy(self.source)
        bad["frames"][0]["selected_center_xy_px"] = [4., 2.]
        with self.assertRaisesRegex(ValueError, "Original selection changed"):
            render.validate_source(self.root, bad)
        bad = copy.deepcopy(self.source)
        bad["segments"][0]["frames"] = copy.deepcopy(bad["segments"][0]["frames"])
        bad["segments"][0]["frames"][1]["decision"] = "abstained"
        with self.assertRaisesRegex(ValueError, "decision rows differ"):
            render.validate_source(self.root, bad)

    def test_rejects_selected_saved_component_and_original_producer_mismatch(self):
        bad = copy.deepcopy(self.source)
        bad["frames"][1]["selected_center_xy_px"] = [4., 2.]
        with self.assertRaisesRegex(ValueError, "component/provenance"):
            render.validate_source(self.root, bad)
        bad = copy.deepcopy(self.source)
        bad["frames"][0]["original_observation"]["center_xy_px"] = [4., 2.]
        with self.assertRaisesRegex(ValueError, "Baseline producer"):
            render.validate_source(self.root, bad)

    def test_png_rgb_integrity_and_binary_panel_mapping(self):
        images = list(render.iter_images(self.root, self.source))
        for i, (row, image) in enumerate(zip(self.source["frames"], images)):
            self.assertEqual(image.size, (1280, 816))
            self.assertEqual(render.verify_pixels(np.asarray(image), image, row, i), [0., 0.])
        tampered = np.asarray(images[1]).copy()
        tampered[808:816, 112*8:113*8] = 255-tampered[808:816, 112*8:113*8]
        with self.assertRaisesRegex(ValueError, "panel key"):
            render.verify_pixels(tampered, images[1], self.source["frames"][1], 1)
        bad = copy.deepcopy(self.source)
        bad["frames"][1]["source_frame"]["png"]["rgb_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "RGB hash"):
            list(render.iter_images(self.root, bad))

    def test_probe_rejects_native_duration_or_transport_mismatch(self):
        records = render.validate_source(self.root, self.source)
        probe = {"streams": [{"time_base": "1/90000", "duration_ts": "94500", "nb_frames": "3",
                              "width": 1280, "height": 816}],
                 "frames": [{"best_effort_timestamp": str(r["review_pts_ticks"]), "duration": str(r["duration_ticks"])}
                            for r in records]}
        self.assertEqual(render.verify_probe(probe, records), 94500)
        probe["frames"][1]["duration"] = "1500"
        with self.assertRaisesRegex(ValueError, "timestamps"):
            render.verify_probe(probe, records)

    def test_nfhs_every_slot_and_protected_decoder_boundary(self):
        source = nfhs_fixture(self.root)
        records = render.validate_source(self.root, source)
        self.assertEqual([r["review_pts_ticks"] for r in records], [i*3600 for i in range(9)])
        self.assertEqual(records[-1]["duration_ticks"], 93600)
        decoded, player_lists = [], []
        actual_decoder = render.observation.decode_segment
        actual_render = render.render_frame
        def decoder(root, possession, segment):
            self.assertIn(segment, [[0, 2], [6, 8]])
            for index, pixels in actual_decoder(root, possession, segment):
                self.assertNotIn(index, [3, 4, 5]); decoded.append(index)
                yield index, pixels
        def frame(image, package, row, index, players=()):
            player_lists.append([p["player_id"] for p in players])
            return actual_render(image, package, row, index, players)
        with patch.object(render.observation, "decode_segment", decoder), patch.object(render, "render_frame", frame):
            images = list(render.iter_images(self.root, source))
        self.assertEqual(decoded, [0, 1, 2, 6, 7, 8])
        self.assertEqual(player_lists[0], ["reviewed_A"])
        self.assertEqual(player_lists[3:6], [[], [], []])
        for i in (3, 4, 5):
            self.assertEqual(int(np.asarray(images[i])[96:776].max()), 0)
        bad = copy.deepcopy(source)
        bad["frames"][3]["selected_center_xy_px"] = [1., 1.]
        with self.assertRaisesRegex(ValueError, "Protected frame"):
            render.validate_source(self.root, bad)
        with self.assertRaisesRegex(ValueError, "no source pixels"):
            render.render_frame(Image.new("RGB", (64, 36)), source, source["frames"][3], 3)

    def test_nfhs_consumer_checks_actual_packet_producer_and_container_offset(self):
        source = nfhs_fixture(self.root)
        render.validate_nfhs_timing(self.root, source)
        bad = copy.deepcopy(source)
        bad["frames"][4]["container_pts_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "native frame mapping"):
            render.validate_source(self.root, bad)
        timing_path = self.root/source["native_timestamps"]["path"]
        timing = json.loads(timing_path.read_text())
        probe_path = self.root/timing["packet_probe"]["path"]
        probe = json.loads(probe_path.read_text())
        probe["packets"][4]["duration"] = str(int(probe["packets"][4]["duration"])+1)
        probe_path.write_text(json.dumps(probe), encoding="utf-8")
        timing["packet_probe"] = review.binding(self.root, probe_path)
        timing_path.write_text(json.dumps(timing), encoding="utf-8")
        source["native_timestamps"] = review.binding(self.root, timing_path)
        with self.assertRaisesRegex(ValueError, "native packet timing"):
            render.validate_source(self.root, source)

    @unittest.skipUnless((FFBIN/"ffmpeg.exe").is_file(), "FFmpeg required")
    def test_actual_encoded_nba_and_nfhs_final_transport_protected_and_resume(self):
        for source in (self.source, nfhs_fixture(self.root)):
            output = self.root/"data/outputs"/source["kind"]
            args = (self.root, source, str(FFBIN/"ffmpeg.exe"), output, {"fixture": True})
            package = render.render_source(*args)
            verified = json.loads((self.root/package["verification"]["path"]).read_text())
            self.assertEqual(verified["decoded_frames"], len(source["frames"]))
            self.assertEqual(verified["actual_final_source_frame_index"], source["frames"][-1]["source_frame_index"])
            self.assertEqual(verified["protected_frame_pairs_verified_black"], 3 if source["kind"] == "nfhs" else 0)
            self.assertEqual([r["source_frame_index"] for r in package["segment_final_frames"]],
                             [s["range_inclusive"][1] for s in source["segments"]])
            self.assertEqual([r["source_frame_index"] for r in package["changed_frames"]],
                             [r["source_frame_index"] for r in source["frames"] if r["decision"] == "filled_saved_candidate"])
            self.assertLess(max(verified["panel_overlay_mae_max"]), 8)
            self.assertFalse(list(output.rglob("source_*.png")))
            with patch("av.open", side_effect=AssertionError("completed render repeated")):
                self.assertEqual(render.render_source(*args), package)

    def test_failure_preserved_and_never_published_as_completion(self):
        output = self.root/"data/outputs/failed"
        with patch("av.open", side_effect=RuntimeError("synthetic encoder failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic encoder failure"):
                render.render_source(self.root, self.source, "ffmpeg", output, {"fixture": True})
        self.assertEqual(len(list(output.rglob("failed.json"))), 1)
        self.assertFalse(list(output.rglob("completion.json")))


if __name__ == "__main__":
    unittest.main()

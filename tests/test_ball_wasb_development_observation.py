"""Protected-frame exclusion and actual cache/observation/render boundaries."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import cv2
import numpy as np

from src.ball_tracking import wasb_development_observation as observation
from src.ball_tracking import wasb_experiment as producer
from src.ball_tracking.wasb_adapter import transform_metadata


def source(count=9):
    return {"path": "data/clips/artificial.mp4", "sha256": "a" * 64,
            "width_px": 512, "height_px": 288, "fps": 25.0, "frame_count": count}


def possession():
    return {"possession_id": "artificial", "source_video": source(),
            "visible_segments": [[0, 2], [6, 8]], "protected_ranges": [[3, 5]]}


def prediction(rgb):
    values = np.zeros((3, 288, 512), dtype=np.float32)
    for channel, image in enumerate(rgb):
        values[channel, 100:102, 200:202] = .6 + float(image[0, 0, 0]) / 100
    transform = transform_metadata(rgb[0].shape[1], rgb[0].shape[0])
    return {"heatmaps": values, "frames": [{"transform": transform} for _ in range(3)]}


def local_comparison_available():
    """The captured-record check is optional on a checkout without ignored data."""
    root = observation.ROOT
    config_path = root / observation.DEFAULT_CONFIG
    if not config_path.is_file():
        return False
    config = producer.read_json(config_path)
    required = [root / config[key]["path"] for key in ("training_completion", "cached_experiment")]
    required += [root / p["player_context"]["path"] for p in config["possessions"]]
    if not all(path.is_file() for path in required):
        return False
    old = producer.read_json(root / config["cached_experiment"]["path"])
    for window in old["windows"]:
        folder = root / old["output_root"] / window["window_id"]
        required.append(folder / "inference_identity.json")
        for first in producer.triplet_starts(window["start_frame_index"], window["end_frame_index"]):
            required += [folder / f"triplet_{first:06d}.{suffix}" for suffix in ("npz", "json")]
    return all(path.is_file() for path in required)


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "data/outputs/observation"
        self.output.mkdir(parents=True)

    @unittest.skipUnless(local_comparison_available(), "Requires the ignored completed comparison/player assets")
    def test_real_metadata_keeps_225_protected_frames_and_138_original_triplets(self):
        root = observation.ROOT
        config, old, completion, training = observation.load_config(root, root / observation.DEFAULT_CONFIG)
        totals = observation.execute(root, root / observation.DEFAULT_CONFIG, check_only=True)
        self.assertEqual({k: totals[k] for k in ("visible_frames", "withheld_frames", "triplets", "prior_cached_triplets", "new_triplets")},
                         {"visible_frames": 1273, "withheld_frames": 225, "triplets": 1261,
                          "prior_cached_triplets": 138, "new_triplets": 1123})
        self.assertEqual(completion["checkpoint"]["sha256"], "09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98")
        self.assertEqual(len(training["training_blocks"]), 5)
        self.assertEqual([p["protected_ranges"] for p in config["possessions"]],
                         [[[275, 349]], [[175, 249]], [[225, 299]]])
        # One real, already-produced cache is consumed without opening video or a model.
        index = observation.cache_index(root, config, old, observation.model_identity(old, producer.runtime_versions()))
        item = index[("possession_001", 50)]
        original = (item["cache"].read_bytes(), item["receipt"].read_bytes())
        with mock.patch.object(cv2, "VideoCapture", side_effect=AssertionError("No source access")):
            values, record = observation.read_bound_triplet(root, item["cache"], item["receipt"], 50,
                item["identity"], config["possessions"][0]["source_video"])
        self.assertEqual(values.shape, (3, 288, 512))
        self.assertEqual(values.dtype, np.float32)
        self.assertGreater(record["original_inference_seconds"], 0)
        self.assertEqual(original, (item["cache"].read_bytes(), item["receipt"].read_bytes()))

    def test_bad_scope_rejected_before_any_source_decoder_can_open(self):
        root = observation.ROOT
        config = producer.read_json(root / observation.DEFAULT_CONFIG)
        split = producer.read_json(root / config["split_metadata"]["path"])
        for mutate in (lambda c: c["possessions"][0]["visible_segments"][0].__setitem__(1, 275),
                       lambda c: c["possessions"][0]["protected_ranges"][0].__setitem__(0, 300),
                       lambda c: c.__setitem__("holdout_buffer_frames", 0)):
            bad = copy.deepcopy(config)
            mutate(bad)
            with mock.patch.object(cv2, "VideoCapture") as decoder, self.assertRaises(ValueError):
                observation.validate_scope(bad, split)
            decoder.assert_not_called()
        with mock.patch.object(cv2, "VideoCapture") as decoder, self.assertRaisesRegex(ValueError, "protected band"):
            list(observation.decode_segment(self.root, possession(), [0, 8]))
        decoder.assert_not_called()

    def test_streaming_decoder_requests_only_allowed_indices_and_resets_after_band(self):
        opened, read_indices = [], []

        class Capture:
            def __init__(self, path):
                self.index = None
                self.closed = False
                opened.append(self)
            def isOpened(self):
                return True
            def set(self, prop, index):
                self.index = index
                return True
            def read(self):
                read_indices.append(self.index)
                pixels = np.full((288, 512, 3), self.index, dtype=np.uint8)
                self.index += 1
                return True, pixels
            def get(self, prop):
                return self.index
            def release(self):
                self.closed = True

        with mock.patch.object(cv2, "VideoCapture", Capture):
            for segment in possession()["visible_segments"]:
                rows = list(observation.decode_segment(self.root, possession(), segment))
                self.assertEqual([r[0] for r in rows], list(range(segment[0], segment[1] + 1)))
        self.assertEqual(read_indices, [0, 1, 2, 6, 7, 8])
        self.assertEqual(len(opened), 2)
        self.assertTrue(all(cap.closed for cap in opened))

    def make_old_producer_cache(self):
        window = {"window_id": "artificial_old", "annotation_set_id": "artificial_producer_fixture",
                  "possession_id": "artificial", "source_video": source(), "start_frame_index": 0, "end_frame_index": 2}
        old = {"output_root": "data/outputs/prior", "windows": [window], "inference": observation.OLD_POLICY}
        model = {"weights": {"path": "artificial", "sha256": "b" * 64}, "input_modality": "three_RGB_images"}
        identity = {**model, "experiment_config_sha256": producer.canonical(old), "inference": observation.OLD_POLICY}
        pixels = {i: np.full((288, 512, 3), i, dtype=np.uint8) for i in range(3)}
        adapter = mock.Mock()
        adapter.predict_triplet.side_effect = prediction
        # Run the actual old writer, including its embedded metadata and JSON receipt.
        # CUDA synchronization is inert because this artificial adapter has no GPU.
        with mock.patch.object(producer, "decode_window", return_value=pixels), \
                mock.patch("torch.cuda.reset_peak_memory_stats"), mock.patch("torch.cuda.synchronize"), \
                mock.patch("torch.cuda.max_memory_allocated", return_value=0):
            producer.infer_window(self.root, old, window, adapter, self.root / old["output_root"], identity)
        index = observation.cache_index(self.root, {"possessions": [possession()]}, old, model)
        return old, model, identity, index

    def test_actual_old_producer_record_reused_under_original_identity_without_decode_or_inference(self):
        old, model, identity, index = self.make_old_producer_cache()
        item = index[("artificial", 0)]
        prior_bytes = item["cache"].read_bytes(), item["receipt"].read_bytes()
        with mock.patch.object(observation, "decode_segment", side_effect=AssertionError("Cached segment needs no pixels")):
            result = observation.infer_segment(self.root, {"inference": observation.POLICY}, possession(), [0, 2],
                self.output, {"new_observation": True}, index, mock.Mock(side_effect=AssertionError("No repeat inference")))
        self.assertEqual([r["state"] for r in result["frames"]], ["observed"] * 3)
        self.assertEqual(result["triplets"][0]["origin"], "prior_development_cache")
        self.assertEqual(result["triplets"][0]["original_identity"], item["identity_binding"])
        self.assertEqual(prior_bytes, (item["cache"].read_bytes(), item["receipt"].read_bytes()))
        self.assertNotIn("annotation_set_id", result)
        self.assertEqual(result["frames"][0]["native_score"], float(np.float32(.6) * 4))

    def test_cache_input_mismatch_rejected_even_when_checkpoint_or_frame_ids_match(self):
        old, model, identity, index = self.make_old_producer_cache()
        for key, changed in (("weights", {"sha256": "wrong"}), ("input_modality", "BGR"),
                             ("experiment_config_sha256", "wrong"), ("inference", {**observation.OLD_POLICY, "padding": "repeat"})):
            bad = {**identity, key: changed}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "incompatible"):
                observation.validate_cache_identity(bad, old, model)
        bad_possession = possession()
        bad_possession["source_video"]["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "allowed source"):
            observation.cache_index(self.root, {"possessions": [bad_possession]}, old, model)
        item = index[("artificial", 0)]
        changed_dimensions = {**source(), "width_px": 1024}
        with self.assertRaisesRegex(ValueError, "affine"):
            observation.read_bound_triplet(self.root, item["cache"], item["receipt"], 0, identity, changed_dimensions)

    def test_new_triplets_cache_actual_outputs_once_and_keep_segment_boundaries(self):
        calls = []
        pos = possession()

        def decode(root, declared, segment):
            for index in range(segment[0], segment[1] + 1):
                yield index, np.full((288, 512, 3), index, dtype=np.uint8)

        def predict(rgb):
            calls.append([int(image[0, 0, 0]) for image in rgb])
            return prediction(rgb), .01, 0

        config = {"inference": observation.POLICY}
        with mock.patch.object(observation, "decode_segment", side_effect=decode):
            results = [observation.infer_segment(self.root, config, pos, segment, self.output,
                {"test_model": True}, {}, predict) for segment in pos["visible_segments"]]
        self.assertEqual(calls, [[0, 1, 2], [6, 7, 8]])
        with mock.patch.object(observation, "decode_segment", side_effect=AssertionError("No repeat decode")):
            repeated = observation.infer_segment(self.root, config, pos, [6, 8], self.output,
                {"test_model": True}, {}, mock.Mock(side_effect=AssertionError("No repeat model")))
        self.assertEqual(repeated, results[-1])
        timeline = observation.make_timeline(pos, results, [{"possession_id": "artificial", "start_frame_index": 0, "end_frame_index": 2}])
        self.assertEqual([r["state"] for r in timeline], ["observed"] * 3 + ["withheld"] * 3 + ["observed"] * 3)
        self.assertEqual([r["contribution_count"] for r in timeline], [1] * 3 + [0] * 3 + [1] * 3)
        self.assertEqual([r["training_frame"] for r in timeline], [True] * 3 + [False] * 6)
        for row in timeline[3:6]:
            self.assertEqual((row["center_xy_px"], row["candidates"], row["native_score"], row["segment"]), (None, [], None, None))

    def test_strict_threshold_component_mass_and_new_context_mean_are_preserved(self):
        triplets = {i: np.zeros((3, 288, 512), dtype=np.float32) for i in range(3)}
        # Aligned center output has three unequal contributing channels.
        triplets[0][2, 90, 90] = .9
        triplets[1][1, 90, 90] = .3
        triplets[2][0, 90, 90] = .6
        means, counts = producer.merge_heatmaps(triplets, 0, 4)
        self.assertEqual(counts, [1, 2, 3, 2, 1])
        self.assertAlmostEqual(float(means[2, 90, 90]), .6, places=6)
        # Equality to the threshold remains missing, distinct from withheld.
        means[0, 100, 100] = np.float32(.3)
        means[1, 80, 80] = .9
        means[1, 90:92, 90:92] = .4
        frames = observation.observed_frames(means, counts, 0, source(), .3)
        self.assertEqual(frames[0]["state"], "missing")
        self.assertEqual(frames[1]["center_xy_px"], [90.5, 90.5])
        self.assertAlmostEqual(frames[1]["native_score"], 1.6, places=6)
        self.assertEqual(frames[-1]["frame_index"], 4)

    def test_invalid_model_arrays_and_withheld_pixels_are_never_silently_accepted(self):
        valid = np.zeros((3, 288, 512), dtype=np.float32)
        for bad in (valid.astype(np.float64), valid[:2], np.full_like(valid, np.nan), np.full_like(valid, 1.01)):
            with self.assertRaises(ValueError):
                observation.validate_heatmaps(bad)
        row = {"state": "withheld", "frame_index": 3, "center_xy_px": None, "contribution_count": 0}
        with self.assertRaisesRegex(ValueError, "no source pixels"):
            observation.render_frame(np.zeros((288, 512, 3), dtype=np.uint8), row, source(), [])
        canvas = observation.render_frame(None, row, source(), [])
        self.assertFalse(canvas[observation.HEADER_HEIGHT:].any())

    def test_actual_h264_timeline_contains_black_placeholders_and_decoded_final_frame(self):
        pos = possession()
        player_path = self.root / "data/outputs/identity/artificial.csv"
        player_path.parent.mkdir(parents=True)
        player_path.write_text("frame_index,player_id,floor_x,floor_y\n0,P1,20,20\n", encoding="utf-8")
        pos["player_context"] = observation.binding(self.root, player_path)
        emitted = prediction([np.zeros((288, 512, 3), dtype=np.uint8) for _ in range(3)])
        segments = [{"segment": segment, "frames": observation.observed_frames(
            emitted["heatmaps"] if segment[0] == 0 else np.zeros((3, 288, 512), dtype=np.float32),
            [1, 1, 1], segment[0], source(), .3)} for segment in pos["visible_segments"]]
        frames = observation.make_timeline(pos, segments, [])
        folder = self.output / "artificial"
        folder.mkdir()
        producer.write_once(folder / "observations.json", {"frames": frames})
        requested = []

        def decode(root, declared, segment):
            for index in range(segment[0], segment[1] + 1):
                requested.append(index)
                yield index, np.full((288, 512, 3), 30 + index, dtype=np.uint8)

        with mock.patch.object(observation, "decode_segment", side_effect=decode):
            result = observation.render_possession(self.root, {"rendering": {"playback_fps": 25, "crf": 18}},
                pos, {"frames": frames}, folder)
        self.assertEqual(requested, [0, 1, 2, 6, 7, 8])
        self.assertEqual(result["verification"], {"decoded_frames": 9, "final_frame_decoded": True,
                                                "protected_source_areas_verified_black": 3})
        final = cv2.imread(str(self.root / result["decoded_final_frame"]["path"]))
        self.assertEqual(final.shape, (448, 512, 3))
        self.assertGreater(float(final[observation.HEADER_HEIGHT:].mean()), 20)
        self.assertIsNone(result["selected_operating_point"])
        self.assertEqual(result["human_visual_review"], "pending")


if __name__ == "__main__":
    unittest.main()

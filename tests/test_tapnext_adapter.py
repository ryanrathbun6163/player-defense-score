"""CPU-only transport checks; no released checkpoint, real frames, or GPU."""
import ast
import copy
import hashlib
import importlib
from importlib.machinery import ModuleSpec
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import ModuleType

import numpy as np

from src.ball_tracking import tapnext_adapter as a
from src.ball_tracking.nba_action_observation import select_observation


ROOT = Path(__file__).resolve().parents[1]


def produced_input(rgb, index=10, pts=90000, duration=1440, point=True):
    """Use the actual retained observation producer, rather than mirror its JSON."""
    png = {"path": "synthetic.png", "sha256": "a" * 64,
           "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(), "bytes": 123}
    frame = {"source_frame_index": index, "source_pts_ticks": pts, "png": png}
    mean = np.zeros((288, 512), dtype=np.float32)
    if point:
        mean[96, 160] = .75
    manifest = {"source_video": {"width_px": rgb.shape[1], "height_px": rgb.shape[0]},
                "time_base": "1/90000"}
    emitted = select_observation(frame, mean, 1, manifest, {"kind": "live_action"})
    return {"source_frame_index": index, "source_pts_ticks": pts,
            "duration_ticks": duration, "time_base": "1/90000", "source_png": png,
            "wasb_observation": a.project_wasb_observation(emitted)}, emitted


class Backend:
    def __init__(self, predictions):
        self.predictions = iter(predictions)
        self.calls = []

    def infer(self, rgb, query, state):
        self.calls.append((None if query is None else query.copy(), state))
        x, y, visible = next(self.predictions)
        return a.TrackerFrame(np.tile([x, y], (65, 1)).astype(np.float32),
                              np.zeros((65, 2), np.float32),
                              np.zeros((65, 512), np.float32),
                              np.full(65, visible, np.float32), {"step": len(self.calls)})


class AdapterPolicyTests(unittest.TestCase):
    def setUp(self):
        self.rgb = np.zeros((36, 64, 3), np.uint8)

    def test_real_wasb_producer_seed_and_emitted_record_roundtrip(self):
        record, producer = produced_input(self.rgb)
        self.assertEqual(record["wasb_observation"]["center_xy_px"], [20., 12.])
        self.assertEqual(record["wasb_observation"]["original_record_sha256"], a.canonical(producer))
        backend = Backend([(20, 12, .2)])
        adapter = a.SingleSeedAdapter(backend)
        adapter.begin_block("nba", 64, 36, "1/90000")
        result = adapter.observe(self.rgb, record)
        restored = json.loads(json.dumps(result, allow_nan=False))
        self.assertEqual(restored["center_xy_px"], [20., 12.])
        self.assertEqual(restored["point_origin"], "automatic")
        self.assertIsNone(restored["native_score"])
        self.assertEqual(restored["source_pts_ticks"], producer["source_pts_ticks"])
        self.assertEqual(restored["seed"]["wasb_record_sha256"], a.canonical(producer))
        self.assertEqual(backend.calls[0][0].shape, (65, 2))
        self.assertEqual(len(restored["tracker_raw"]["coordinate_logits_model_yx"]), 512)
        result["seed"]["center_xy_px"][0] = 1000
        result["wasb_observation"]["center_xy_px"][0] = 1000
        self.assertEqual(adapter.seed["center_xy_px"], [20., 12.])
        self.assertEqual(record["wasb_observation"]["center_xy_px"], [20., 12.])

    def test_hidden_zero_outside_recovery_never_reseed_or_fallback(self):
        backend = Backend([(20, 12, 0), (21, 13, -1), (64, 0, 1), (22, 13, 1)])
        adapter = a.SingleSeedAdapter(backend)
        adapter.begin_block("nba", 64, 36, "1/90000")
        results = []
        for i in range(4):
            record, _ = produced_input(self.rgb, 10+i, 90000+1440*i)
            results.append(adapter.observe(self.rgb, record))
        self.assertEqual([r["center_xy_px"] for r in results], [None, None, None, [22., 13.]])
        self.assertEqual([r["missing_reason"] for r in results],
                         ["tracker_predicted_hidden", "tracker_predicted_hidden", "tracker_out_of_image", None])
        self.assertTrue(results[0]["seeded_this_frame"])
        self.assertTrue(all(not r["seeded_this_frame"] for r in results[1:]))
        self.assertTrue(all(q is None for q, _ in backend.calls[1:]))
        self.assertEqual([s for _, s in backend.calls], [None, {"step": 1}, {"step": 2}, {"step": 3}])
        self.assertEqual(results[0]["tracker_raw"]["center_xy_px"], [20., 12.])

    def test_missing_before_seed_vfr_final_interval_and_explicit_reset(self):
        backend = Backend([(20, 12, 1), (21, 13, 1), (20, 12, 1)])
        adapter = a.SingleSeedAdapter(backend)
        adapter.begin_block("segment1", 64, 36, "1/90000")
        first, _ = produced_input(self.rgb, point=False)
        missing = adapter.observe(self.rgb, first)
        self.assertEqual(missing["missing_reason"], "before_first_valid_automatic_seed")
        self.assertEqual(backend.calls, [])
        second, _ = produced_input(self.rgb, 11, 91440, 1530)
        result = adapter.observe(self.rgb, second)
        self.assertEqual(result["duration_ticks"], 1530)
        final, _ = produced_input(self.rgb, 12, 92970, 1440)
        result = adapter.observe(self.rgb, final)
        self.assertEqual(result["source_pts_ticks"] + result["duration_ticks"], 94410)
        adapter.begin_block("segment2", 64, 36, "1/90000")
        result = adapter.observe(self.rgb, first | {"wasb_observation": second["wasb_observation"] |
                                                  {"source_frame_index": 10, "source_pts_ticks": 90000}})
        self.assertTrue(result["seeded_this_frame"])
        self.assertIsNone(backend.calls[-1][1])
        self.assertEqual(result["tracker_calls_in_block"], 1)

    def test_strict_prediction_boundary_and_native_join(self):
        base, emitted = produced_input(self.rgb)
        for mutate in (lambda r: r.update(annotation={}),
                       lambda r: r["wasb_observation"].update(point_origin="manual"),
                       lambda r: r["wasb_observation"].update(source_pts_ticks=1),
                       lambda r: r["source_png"].update(rgb_sha256="0"*64),
                       lambda r: r["source_png"].update(reference={})):
            with self.subTest(mutate=mutate):
                adapter = a.SingleSeedAdapter(Backend([]))
                adapter.begin_block("block", 64, 36, "1/90000")
                record = copy.deepcopy(base)
                mutate(record)
                with self.assertRaises(ValueError):
                    adapter.observe(self.rgb, record)
        with self.assertRaises(ValueError):
            a.project_wasb_observation(emitted | {"annotation": {}})

    def test_nonconsecutive_timing_rejected(self):
        adapter = a.SingleSeedAdapter(Backend([(20, 12, 1)]))
        adapter.begin_block("block", 64, 36, "1/90000")
        adapter.observe(self.rgb, produced_input(self.rgb)[0])
        with self.assertRaisesRegex(ValueError, "explicit boundary reset"):
            adapter.observe(self.rgb, produced_input(self.rgb, 11, 91500)[0])

    def test_nonfinite_model_output_poisoned_until_explicit_reset(self):
        adapter = a.SingleSeedAdapter(Backend([(float("nan"), 12, 1), (20, 12, 1)]))
        adapter.begin_block("block", 64, 36, "1/90000")
        record = produced_input(self.rgb)[0]
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            adapter.observe(self.rgb, record)
        with self.assertRaisesRegex(ValueError, "fresh block"):
            adapter.observe(self.rgb, record)
        adapter.begin_block("new", 64, 36, "1/90000")
        self.assertEqual(adapter.observe(self.rgb, record)["center_xy_px"], [20., 12.])

    def test_wrong_pinned_release_rejected_before_loading(self):
        with self.assertRaisesRegex(ValueError, "source commit"):
            a.create_adapter(ROOT, {"source_commit": "wrong"}, device="cpu")

    def test_import_roots_and_preloaded_transitive_modules_must_be_verified(self):
        extracted = [(ROOT / "source_test").resolve(), (ROOT / "vendor_test").resolve()]
        source = extracted[0] / ("tapnet-" + a.PIN)
        manifest = {"source_import_root": str(source), "dependency_import_root": str(extracted[1])}
        files = {source / "tapnet/__init__.py", extracted[1] / "einops/__init__.py"}
        with patch.dict(sys.modules, {}, clear=True):
            self.assertEqual(a._checked_import_roots(manifest, extracted, files), [source, extracted[1]])
            with self.assertRaisesRegex(ValueError, "Import roots"):
                a._checked_import_roots(manifest | {"source_import_root": str(ROOT)}, extracted, files)
            stale = ModuleType("tapnet.tapnext.tapnext_torch")
            stale.__file__ = str(ROOT / "unverified/tapnext_torch.py")
            with patch.dict(sys.modules, {stale.__name__: stale}):
                with self.assertRaisesRegex(ValueError, "preloaded dependency"):
                    a._checked_import_roots(manifest, extracted, files)
            namespace = ModuleType("tapnet.tapnextpp")
            namespace.__spec__ = ModuleSpec(namespace.__name__, loader=None, is_package=True)
            namespace.__path__ = [str(source / "tapnet/tapnextpp")]
            namespace.__spec__.submodule_search_locations = namespace.__path__
            files.add(source / "tapnet/tapnextpp/votsp2026/model.py")
            with patch.dict(sys.modules, {namespace.__name__: namespace}):
                a._checked_import_roots(manifest, extracted, files)
                namespace.__path__ = [str(ROOT / "unverified/tapnextpp")]
                namespace.__spec__.submodule_search_locations = namespace.__path__
                with self.assertRaisesRegex(ValueError, "namespace dependency"):
                    a._checked_import_roots(manifest, extracted, files)


class PinnedProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ready = sorted((ROOT / "data/outputs/tapnext_assets" / a.PIN / "attempts").glob("*/bootstrap_ready.json"))
        if not ready:
            raise unittest.SkipTest("Pinned source/vendor assets are not available; no download is performed")
        manifest = json.loads(ready[0].read_text(encoding="utf-8"))
        if manifest["source_commit"] != a.PIN:
            raise AssertionError("Source pin differs")
        cls.source = Path(manifest["python_paths"][0])
        for path in reversed(manifest["python_paths"]):
            if path not in sys.path:
                sys.path.insert(0, path)
        cls.torch = importlib.import_module("torch")
        cls.model = importlib.import_module("tapnet.tapnextpp.votsp2026.model")
        cls.utils = importlib.import_module("tapnet.tapnextpp.votsp2026.utils")
        cls.inner = importlib.import_module("tapnet.tapnext.tapnext_torch")
        cls.old_threads = cls.torch.get_num_threads()
        cls.torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        cls.torch.set_num_threads(cls.old_threads)

    def test_support_grid_matches_actual_upstream_functions(self):
        path = self.source / "tapnet/tapnextpp/votsp2026/tracker.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name in {"grid_support_points", "local_support_points"}]
        self.assertEqual(len(selected), 2)
        namespace = {"np": np}
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
        for w, h, center in ((1920, 1080, [960., 540.]), (1280, 720, [0., 719.]), (64, 36, [63., 0.])):
            query = np.asarray([center], np.float32)
            actual = namespace["local_support_points"](query, 64, 32*w/512, 32*h/512, w, h)
            np.testing.assert_array_equal(a.support_queries(center, w, h), np.concatenate([query, actual]))

    def test_actual_factory_metadata_and_namespace_import_without_weight_load(self):
        manifests = sorted((ROOT / "data/outputs/tapnext_assets" / a.PIN / "attempts").glob("*/ready_asset_bindings.json"))
        if not manifests:
            self.skipTest("Pinned checkpoint asset manifest is unavailable; no download performed")
        # Exercise the actual factory, full asset verification, and all actual
        # transitive imports. Only weight construction/loading is substituted.
        wrapper = self.model.TAPNextPP(None, self.torch.device("cpu"), input_resolution=512)
        with patch.object(self.model.TAPNextPP, "from_checkpoint", return_value=wrapper) as load:
            adapter = a.create_adapter(ROOT, manifests[-1], device="cpu")
        self.assertIsInstance(adapter, a.SingleSeedAdapter)
        self.assertEqual(load.call_args.kwargs, {"device": "cpu", "input_resolution": 512,
                                                "half_precision": False, "compile_model": False})
        namespace = sys.modules["tapnet.tapnextpp"]
        self.assertIsNone(namespace.__file__)
        self.assertEqual([Path(p).resolve() for p in namespace.__path__], [self.source / "tapnet/tapnextpp"])

    def test_real_cpu_producer_matches_official_wrapper_and_keeps_logits(self):
        # Random tiny model validates the real tensor producer, not released accuracy.
        # Zero attention blocks avoid a full model or any CUDA use.
        torch = self.torch
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(24)
            inner = self.inner.TAPNext(image_size=(256, 256), width=16,
                                      lru_width=16, num_heads=1, depth=0).eval()
        wrapper = self.model.TAPNextPP(inner, torch.device("cpu"), input_resolution=512)
        backend = a.TorchTAPBackend(wrapper, self.utils)
        rgb = np.zeros((36, 64, 3), np.uint8)
        rgb[..., 0], rgb[..., 1], rgb[..., 2] = 12, 40, 200
        queries = a.support_queries([20., 12.], 64, 36)
        official_xy, official_visible, official_state = wrapper.track_frame(rgb[..., ::-1], queries)
        output = backend.infer(rgb, queries, None)
        np.testing.assert_array_equal(output.positions_xy, official_xy)
        np.testing.assert_array_equal(output.visibility_logits > 0, official_visible)
        self.assertEqual(output.coordinate_logits.shape, (65, 512))
        self.assertEqual(output.state.step, official_state.step)
        self.assertEqual(output.state.query_points.shape, (1, 65, 3))
        np.testing.assert_allclose(output.state.query_points[0, 0].numpy(), [0., 12*256/36, 20*256/64], atol=4e-6)
        transformed = self.utils.preprocess_frame(rgb[..., ::-1], torch.device("cpu"), 512)
        self.assertEqual(tuple(transformed.shape), (1, 1, 512, 512, 3))
        np.testing.assert_allclose(transformed[0, 0, 0, 0].numpy(), np.array([12, 40, 200])/127.5-1, atol=1e-7)
        expected_xy, expected_visible, _ = wrapper.track_frame(rgb[..., ::-1], state=official_state)
        follow = backend.infer(rgb, None, output.state)
        np.testing.assert_array_equal(follow.positions_xy, expected_xy)
        np.testing.assert_array_equal(follow.visibility_logits > 0, expected_visible)


if __name__ == "__main__":
    unittest.main()

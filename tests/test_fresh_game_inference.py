"""Synthetic/metadata checks only; no model construction or GPU queries."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from src.ball_tracking import fresh_game_inference as worker


def block(clip="122", size=120):
    bid = f"bkn_det_{worker.GAME}_c{clip}"
    return {"block_id": bid, "clip_id": clip, "game_id": worker.GAME, "domain": "nba", "role": worker.ROLE,
        "source_video": {"path": "synthetic/" + clip + ".mp4", "bytes": 5,
                         "sha256": hashlib.sha256(clip.encode()).hexdigest(), "width_px": 1280, "height_px": 720},
        "time_base": "1/60000", "range_inclusive": [0, size - 1], "frames": [
            {"frame_key": bid + ":" + str(i), "source_frame_index": i, "source_pts_ticks": 1000 * i,
             "duration_ticks": 1000, "png": {"path": f"synthetic/{clip}/{i}.png", "bytes": 3,
                                             "sha256": "a" * 64, "rgb_sha256": "b" * 64}} for i in range(size)]}


def candidate(identity, frame="f", inside=True, qnative=False):
    return {"candidate_id": identity, "frame_key": frame, "in_source_bounds": inside, "selected_native": qnative}


class FreshGameInferenceTest(unittest.TestCase):
    def test_import_is_metadata_only_and_entrypoint_requires_exact_owned_arguments(self):
        code = "import sys;from src.ball_tracking import fresh_game_inference as m;assert 'torch' not in sys.modules;assert 'src.ball_tracking.wasb_resolution' not in sys.modules;print('metadata only')"
        result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, check=True)
        self.assertIn("metadata only", result.stdout)
        with self.assertRaisesRegex(ValueError, "owned invocation"):
            worker.run(Path.cwd(), "wrong", ["--run", "--monitor", "wrong"])

    def test_full_native_manifest_rejects_labels_role_context_gaps_and_wrong_game(self):
        good = {"schema_version": "fresh_game_label_free_inputs/v0.1", "blocks": [block(c) for c in worker.CLIPS]}
        worker.validate_inputs(good)
        for kind in ("label", "role", "game", "gap", "pts", "extra_context", "order"):
            bad = deepcopy(good)
            if kind == "label": bad["blocks"][0]["frames"][0]["annotation"] = {"geometry": [1, 2]}
            if kind == "role": bad["blocks"][0]["role"] = "training"
            if kind == "game": bad["blocks"][0]["game_id"] = "0022400868"
            if kind == "gap": bad["blocks"][0]["frames"][20]["source_frame_index"] = 21
            if kind == "pts": bad["blocks"][0]["frames"][20]["source_pts_ticks"] += 1
            if kind == "extra_context": bad["blocks"][0] = block("122", 121)
            if kind == "order": bad["blocks"].reverse()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                worker.validate_inputs(bad)

    def test_affine_matches_original_canonical_function_exactly(self):
        from src.ball_tracking import wasb_resolution
        for width, height in ((1280, 720), (1920, 1080), (1440, 1080)):
            expected, _ = wasb_resolution.affine_matrices(width, height)
            np.testing.assert_array_equal(worker.canonical_affine(width, height), expected)

    def test_streaming_capture_native_cadence_channels_float32_means_and_boundaries(self):
        values = [[1e-8, .4, .75], [.2, .25, .9], [.01, .6, .7]]
        calls, returned = [], []
        def provider(frames):
            start = frames[0]["source_frame_index"]
            calls.append([f["source_frame_index"] for f in frames])
            output = np.zeros((3, worker.HEIGHT, worker.WIDTH), np.float32)
            for channel in range(3): output[channel, 30:32, 40:42] = np.float32(values[start][channel])
            returned.append(output.copy())
            return output
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = worker.capture_block(root, block(size=5), root / "capture", provider)
            self.assertEqual(calls, [[0, 1, 2], [1, 2, 3], [2, 3, 4]])
            self.assertEqual(record["calls"], 3)
            means = np.load(root / record["extraction"]["mean_heatmaps"]["path"], allow_pickle=False)
            ledger = worker.io.rows(root / record["contributor_ledger"]["path"])
            self.assertEqual([r["count"] for r in ledger], [1, 2, 3, 2, 1])
            for i in range(5):
                starts = list(range(max(0, i - 2), min(i, 2) + 1))
                expected = np.zeros((worker.HEIGHT, worker.WIDTH), np.float32)
                for start in starts: expected += returned[start][i - start]
                expected /= np.float32(len(starts))
                np.testing.assert_array_equal(means[i], expected)
                self.assertEqual(ledger[i]["mean_heatmap_sha256"], hashlib.sha256(expected.tobytes()).hexdigest())
                self.assertEqual([(c["triplet_start_offset"], c["channel"]) for c in ledger[i]["contributors"]], [(s, i - s) for s in starts])
            self.assertFalse(record["labels_used"])
            self.assertFalse(record["raw_forward_channels_retained"])
            frames, candidates = worker.pool_rows(block(size=5), record, worker.io.rows(root / record["extraction"]["pools"]["path"]))
            self.assertEqual(len(frames), 5)
            self.assertEqual(sum(len(f["candidate_ids"]) for f in frames), len(candidates))

    def test_strict_native_and_weak_thresholds_keep_original_dedup(self):
        from src.ball_tracking import wasb_resolution
        from src.ball_tracking.weak_response_followup import narrow_pool
        heatmap = np.zeros((432, 768), np.float32)
        heatmap[30, 40] = .31
        heatmap[60, 80] = .3
        heatmap[90, 120] = .01
        heatmap[120, 160] = .0101
        native = [{"candidate_index": i, **r} for i, r in enumerate(wasb_resolution.components_from_heatmap(heatmap, 1280, 720))]
        pool, stats = narrow_pool(heatmap, native, 1280, 720)
        self.assertEqual(len(native), 1)
        self.assertEqual(stats["raw_threshold_0.01_count"], 3)
        self.assertEqual(stats["retained_weak_count"], 2)
        self.assertEqual(len(pool), 3)
        self.assertEqual(pool[0]["extraction"], "native_component")
        self.assertEqual(len(pool[0]["equivalent_extractions"]), 1)

    def test_complete_global_Q_budget_preserves_tail_and_out_of_bounds(self):
        rows = [candidate(str(i), frame=str(i // 12)) for i in range(65)] + [candidate("outside", inside=False)]
        result = worker.q_budget(rows)
        self.assertEqual((result["K"], result["Q_forwards"], result["J_predictions"], result["out_of_source_bounds"]), (65, 3, 65, 1))
        self.assertEqual(result["ordered_candidate_ids"], [str(i) for i in range(65)])
        self.assertEqual(result["ordered_ids_sha256"], worker.canonical(result["ordered_candidate_ids"]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            worker.q_budget(rows + [rows[0]])
        self.assertEqual(worker.q_budget([])["Q_forwards"], 0)

    def test_out_of_bounds_native_choice_and_empty_frames_survive_identity_transport(self):
        source = block(size=3)
        native = {"candidate_index": 0, "center_x": -.5, "center_y": 10., "heatmap_x": -.3,
                  "heatmap_y": 6., "native_score": .8, "component_pixels": 1, "in_source_bounds": False}
        observation_rows, pools = [], []
        for i, frame in enumerate(source["frames"]):
            values = [native] if i == 0 else []
            observation_rows.append({"source_frame_index": i, "source_pts_ticks": i * 1000,
                "time_base": source["time_base"], "source_png": frame["png"], "mean_heatmap_sha256": str(i) * 64,
                "candidates": values, "selected_candidate_index": 0 if i == 0 else None,
                "state": "observed" if values else "missing", "temporal_contributions": 1})
            pools.append({"block_id": source["block_id"], "source_frame_index": i, "source_pts_ticks": i * 1000,
                "time_base": source["time_base"], "mean_heatmap_sha256": str(i) * 64,
                "candidates": [{**native, "extraction": "native_component", "threshold": .3}] if values else [],
                "diagnostic": {"native_parity": True, "labels_used": False, "native_count": len(values), "pool_count": len(values)}})
        record = {"native_observations": observation_rows, "extraction": {"pools": {"path": "pool.jsonl", "bytes": 1, "sha256": "d" * 64}}}
        frames, candidates = worker.pool_rows(source, record, pools)
        self.assertEqual(len(frames), 3)
        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0]["in_source_bounds"])
        self.assertTrue(candidates[0]["selected_native"])
        self.assertEqual(worker.q_budget(candidates)["K"], 0)
        fixed = worker.fixed_choices(frames, candidates, {})
        self.assertEqual(fixed[0]["native_selected_candidate_id"], candidates[0]["candidate_id"])
        self.assertIsNone(fixed[0]["quality_top_candidate_id"])
        self.assertEqual(fixed[1]["candidate_ids"], [])

    def test_fixed_native_choice_is_not_reranked_or_replaced_and_Qtop_ties_are_lexical(self):
        candidates = [candidate("z", qnative=True), candidate("b"), candidate("a"), candidate("outside", inside=False)]
        frames = [{"frame_key": "f", "candidate_ids": [r["candidate_id"] for r in candidates], "native_selected_candidate_id": "z"},
                  {"frame_key": "empty", "candidate_ids": [], "native_selected_candidate_id": None}]
        result = worker.fixed_choices(frames, candidates, {"z": -4., "b": 1., "a": 1.})
        self.assertEqual(result[0]["native_selected_candidate_id"], "z")
        self.assertEqual(result[0]["quality_top_candidate_id"], "a")
        self.assertEqual(result[0]["quality_top_tied_candidate_ids"], ["a", "b"])
        self.assertFalse(result[0]["fallback_allowed"])
        self.assertIsNone(result[1]["quality_top_candidate_id"])
        for bad in ({"z": -4., "b": 1.}, {"z": -4., "b": True, "a": 1.}, {"z": float("nan"), "b": 1., "a": 1.}):
            with self.assertRaises(ValueError): worker.fixed_choices(frames, candidates, bad)

    def test_attempted_call_durability_and_exact_counter_refuse_extra_or_unreturned_call(self):
        counters = {"detector_attempted": 0, "detector_returned": 0, "means": 0,
                    "Q_attempted": 0, "Q_returned": 0, "Q_presentations": 0, "J_predictions": 0, "optimizer_updates": 0}
        with tempfile.TemporaryDirectory() as folder:
            journal = Path(folder) / "journal.jsonl"
            worker.start_call(counters, "detector", 1, journal, {"ids": [0, 1, 2]})
            self.assertEqual(worker.io.rows(journal)[0]["counters"]["detector_attempted"], 1)
            self.assertEqual(counters["detector_returned"], 0)
            with self.assertRaisesRegex(ValueError, "budget"):
                worker.start_call(counters, "detector", 1, journal, {})
        final = dict(detector_attempted=354, detector_returned=354, means=360, Q_attempted=3,
                     Q_returned=3, Q_presentations=65, J_predictions=65, optimizer_updates=0)
        worker.validate_counters(final, {"Q_forwards": 3, "K": 65})
        for key in ("detector_returned", "Q_presentations", "J_predictions", "optimizer_updates"):
            bad = dict(final); bad[key] += 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                worker.validate_counters(bad, {"Q_forwards": 3, "K": 65})

    def test_J_features_use_complete_same_frame_original_Q_pool_without_labels(self):
        from src.ball_tracking import candidate_acceptance_features as features
        probe = {"row_key": "all_nba|a", "frame_key": "f", "fit": "all_nba", "cohort": "fresh_game",
                 "logit": 2., "center_xy_px": [100., 100.], "native_score": 3., "component_pixels": 4,
                 "padding_pixels": 0, "native_or_weak": "weak"}
        far = dict(probe, row_key="all_nba|b", center_xy_px=[130., 100.], logit=5.)
        near = dict(probe, row_key="all_nba|c", center_xy_px=[110., 100.], logit=4.)
        result = features.build_feature_row(probe, [probe, far, near])
        self.assertEqual(result["raw_features"]["quality_minus_far_max"], -3.)
        self.assertEqual(result["raw_features"]["quality_minus_near_max"], -2.)
        self.assertEqual(result["pool_provenance"]["original_candidate_count"], 3)
        with self.assertRaises(ValueError):
            features.build_feature_row(probe, [probe, dict(far, fit="Qplus")])

    def test_authorization_and_owned_hard_soft_limits(self):
        freeze, protocol = {"sha256": "a"}, {"sha256": "b"}
        auth = {"execution_approved": True, "execution_freeze": freeze, "protocol": protocol, "scope": worker.COUNTS,
                "max_total_seconds": 1800, "user_statement": "Proceed", **{k: False for k in
                ("automatic_retry", "automatic_extension", "protected_access_approved", "new_labels_approved", "training_approved", "selector_approved")}}
        worker.validate_authorization(auth, freeze, protocol)
        with self.assertRaises(ValueError): worker.validate_authorization(dict(auth, training_approved=True), freeze, protocol)
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        self.assertEqual(worker.remaining_seconds({"created_at_utc": now.isoformat()}, now), 1800)
        with self.assertRaises(ValueError):
            worker.remaining_seconds({"created_at_utc": (now - timedelta(seconds=1770)).isoformat()}, now)

    def test_readiness_permits_only_bound_standing_Debug_restoration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); now = datetime(2026, 10, 30, 16, tzinfo=timezone.utc)
            restored = {"at_utc": (now - timedelta(seconds=80)).isoformat(), "setting": "NVIDIA Debug Mode",
                "before": "Off, gray toggle left observed via NVIDIA App System Advanced screenshot",
                "after": "On, green toggle right and accessibility Debug Mode Toggle switch On",
                "action": "Restored Off to On with one toggle action", "settings_changed": True, "no_other_settings_changed": True,
                "authority": "Standing project instruction to keep Debug Mode ON; ordinary restoration of successful prior setup"}
            path = root / worker.RESTORATION; worker.write_once(path, restored); link = worker.binding(root, path)
            ui_path = root / "ui.json"
            worker.write_once(ui_path, {"at_utc": (now - timedelta(seconds=20)).isoformat(), "debug_mode_enabled": True,
                                       "settings_changed": True, "restoration_receipt": link})
            ui = worker.binding(root, ui_path); freeze, auth = {"path": "freeze"}, {"path": "auth"}
            ready = {"at_utc": (now - timedelta(seconds=10)).isoformat(), "execution_freeze": freeze, "execution_authorization": auth,
                "driver_version": "617.42", "gpu_uuid": worker.GPU, "power_limit_W": 250, "ram_configured_mt_s": [5200, 5200],
                "isolation_conflicts": [], "existing_gpu_workers": [], "debug_mode_enabled": True, "debug_mode_state_basis": "ui_observed",
                "configuration_changes": ["NVIDIA Debug Mode"], "unexpected_setting_changes": [], "settings_changed": True,
                "settings_changed_by_agent": True, "fresh_launch_checks_passed": True, "temperature_C": 40,
                "debug_mode_restoration": link, "debug_mode_ui_observation": ui, "sources": [link, ui, {"path": "other"}]}
            worker.validate_readiness(root, ready, freeze, auth, now)
            self.assertTrue(ready["settings_changed"])
            self.assertEqual(ready["configuration_changes"], ["NVIDIA Debug Mode"])
            for field, value in (("configuration_changes", ["NVIDIA Debug Mode", "power"]), ("power_limit_W", 260),
                                 ("debug_mode_enabled", False), ("at_utc", (now - timedelta(seconds=121)).isoformat()),
                                 ("existing_gpu_workers", [{"pid": 10}])):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    worker.validate_readiness(root, dict(ready, **{field: value}), freeze, auth, now)
            changed = deepcopy(restored); changed["no_other_settings_changed"] = False
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(ValueError): worker.validate_readiness(root, ready, freeze, auth, now)


if __name__ == "__main__":
    unittest.main()

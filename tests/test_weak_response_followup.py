"""Actual producer parity, fixed factor isolation and emitted scoring transport."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from src.ball_tracking import weak_response_followup as followup
from src.ball_tracking.weak_response_capture import read
from src.ball_tracking.weak_response_experiment import materialize_choices
from src.ball_tracking.weak_response_review import score_block

ROOT = Path(__file__).resolve().parents[1]


def original_components():
    """Isolate the original frozen CPU extractor without importing Torch."""
    adapter = ROOT / "src/ball_tracking/wasb_adapter.py"
    node = next(n for n in ast.parse(adapter.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "_dimension")
    adscope = {"np": np}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(adapter), "exec"), adscope)
    source = ROOT / "src/ball_tracking/wasb_resolution.py"
    names = {"dimensions", "affine_matrices", "components_from_heatmap"}
    nodes = [n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
    def check(value, message):
        if not value:
            raise ValueError(message)
    scope = {"np": np, "cv2": cv2, "WIDTH": 768, "HEIGHT": 432, "check": check,
             "adapter": types.SimpleNamespace(_dimension=adscope["_dimension"])}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), scope)
    return scope["components_from_heatmap"]


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(ROOT / followup.CONFIG)
        cls.original = read(ROOT / cls.config["original_config"]["path"])
        cls.extractor = staticmethod(original_components())

    def require_local_records(self, *relative_paths):
        missing = [str(path) for path in relative_paths if not (ROOT / path).is_file()]
        if missing:
            self.skipTest("Optional ignored research records are unavailable: " + ", ".join(missing))

    def test_fixed_factorial_changes_only_declared_cost_and_speed(self):
        followup.validate_parameters(self.config, self.original)
        for arm, changes in self.config["arms"].items():
            parameters = followup.parameters_for(self.config, arm)
            self.assertEqual(parameters, {**self.original["sequence"], **changes["changes"]})
        bad = deepcopy(self.config)
        bad["arms"]["speed_only"]["changes"]["switch_missing_cost"] = .2
        with self.assertRaises(ValueError):
            followup.validate_parameters(bad, self.original)

    def test_hou_threshold_rule_rejects_det_and_changed_result(self):
        self.require_local_records(
            self.config["diagnostic_evidence"]["hou_threshold_unions"]["path"],
            self.config["diagnostic_evidence"]["hou_v1_weak_selected_sources"]["path"])
        report = read(ROOT / self.config["diagnostic_evidence"]["hou_threshold_unions"]["path"])
        selected = read(ROOT / self.config["diagnostic_evidence"]["hou_v1_weak_selected_sources"]["path"])
        result = followup.validate_threshold_basis(report, selected)
        self.assertEqual(result["chosen_threshold"], .01)
        bad = deepcopy(report)
        bad["blocks"][0]["block_id"] = "sas_det_q1_c02:10668-11898"
        with self.assertRaises(ValueError):
            followup.validate_threshold_basis(bad, selected)
        bad = deepcopy(report)
        bad["blocks"][0]["methods"]["threshold_0.01"]["union_available"] = 118
        with self.assertRaises(ValueError):
            followup.validate_threshold_basis(bad, selected)

        bad_selected = deepcopy(selected)
        next(row for row in bad_selected["rows"] if row["change"] == "certain_hidden_added")["selection"]["peak"] = .02
        with self.assertRaises(ValueError):
            followup.validate_threshold_basis(report, bad_selected)

    def test_narrow_components_match_independent_original_producer(self):
        mean = np.zeros((432, 768), np.float32)
        mean[100:103, 200:204] = np.array([[.01, .05, .1, .02], [.05, .8, .6, .08], [.01, .1, .05, .01]], np.float32)
        mean[200:202, 350:352] = .1
        mean[250, 400] = .005  # below .01: must not become a local-maximum candidate.
        native = [{"candidate_index": i, **c} for i, c in enumerate(self.extractor(mean, 1920, 1080, .3))]
        weak = self.extractor(mean, 1920, 1080, .01)
        pool, diagnostic = followup.narrow_pool(mean, native, 1920, 1080)
        self.assertEqual(diagnostic["raw_threshold_0.01_count"], len(weak))
        self.assertEqual(diagnostic["native_count"], len(native))
        for old, new in zip(native, pool):
            self.assertTrue(all(new[k] == v for k, v in old.items()))
        retained_or_equivalent = [c for c in pool if c["original_index"] is None]
        retained_or_equivalent += [c for row in pool for c in row["equivalent_extractions"]]
        retained_or_equivalent.sort(key=lambda c: c["extraction_index"])
        self.assertEqual([{k: c[k] for k in followup.NATIVE_FIELDS} for c in retained_or_equivalent], weak)
        self.assertTrue(all(c["extraction"] == "threshold_component" for c in retained_or_equivalent))
        altered = deepcopy(native)
        altered[0]["native_score"] += .01
        with self.assertRaises(ValueError):
            followup.narrow_pool(mean, altered, 1920, 1080)

    def test_actual_saved_map_native_parity_and_score_transport(self):
        self.require_local_records(self.original["input_package"], followup.BASE + "/capture_v0_1/completed.json")
        package = read(ROOT / self.original["input_package"])
        entry = next(e for e in package["blocks"] if e["block"]["block_id"] == followup.HOU[0])
        captured = read(ROOT / followup.BASE / "capture_v0_1/completed.json")
        map_link = next(b["mean_heatmaps"] for b in captured["blocks"] if b["block_id"] == followup.HOU[0])
        self.require_local_records(map_link["path"], entry["provenance"]["candidate_records"]["path"])
        array = np.load(ROOT / map_link["path"], mmap_mode="r")
        try:
            for i in (0, 75, 83, len(array) - 1):
                native = entry["candidate_observations"][i]
                self.assertEqual(hashlib.sha256(array[i].tobytes()).hexdigest(), native["mean_heatmap_sha256"])
                pool, _ = followup.narrow_pool(array[i], native["candidates"], 1280, 720)
                source = self.extractor(array[i], 1280, 720, .3)
                self.assertEqual([{k: c[k] for k in followup.NATIVE_FIELDS} for c in pool if c["original_index"] is not None], source)
        finally:
            array._mmap.close()
        block, native = entry["block"], entry["candidate_observations"]
        native_score = score_block(block, native, baseline=native, expected_pools=[r["candidates"] for r in native])
        original_score = read(ROOT / entry["provenance"]["candidate_records"]["path"])["score"]
        self.assertEqual(native_score, original_score)
        projected = [[{**{k: c[k] for k in ("candidate_index", "center_x", "center_y", "native_score", "in_source_bounds")},
                       "original_index": c["candidate_index"]} for c in r["candidates"]] for r in native]
        compact, _ = followup.select_arm(native, projected, 1280, self.config, "motion_and_speed")
        restored = materialize_choices({"observations": compact}, projected)
        score = score_block(block, restored, baseline=native, expected_pools=projected)
        self.assertEqual(score["summary"]["frames"], 120)
        self.assertEqual(score["summary"]["eligible_frames"], 120)
        self.assertIsNone(score["human_visual_acceptance"])
        bad = deepcopy(compact)
        selected = next(row for row in bad if row["center_xy_px"] is not None)
        selected["native_score"] += .01
        with self.assertRaises(ValueError):
            score_block(block, materialize_choices({"observations": bad}, projected), baseline=native, expected_pools=projected)

    def test_actual_emitted_pool_record_consumed_and_tamper_rejected(self):
        self.require_local_records(self.original["input_package"], followup.BASE + "/capture_v0_1/completed.json")
        package = read(ROOT / self.original["input_package"])
        entry = next(e for e in package["blocks"] if e["block"]["block_id"] == followup.HOU[0])
        captured = read(ROOT / followup.BASE / "capture_v0_1/completed.json")
        link = next(b["mean_heatmaps"] for b in captured["blocks"] if b["block_id"] == followup.HOU[0])
        self.require_local_records(link["path"])
        array = np.load(ROOT / link["path"], mmap_mode="r")
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                native = entry["candidate_observations"][:2]
                path = root / "actual_mean_slice.npy"
                np.save(path, np.asarray(array[:2]), allow_pickle=False)
                destination = root / "pools.jsonl"
                result = followup.extract_block(root, entry["block"], native, followup.bind(root, path), destination)
                pools = followup.pool_rows(root, destination, entry["block"], native)
                self.assertEqual(result["frames"], 2)
                emitted = [json.loads(line) for line in destination.read_text().splitlines()]
                self.assertEqual(pools, [[{k: candidate[k] for k in followup.SELECTOR_FIELDS}
                                         for candidate in row["candidates"]] for row in emitted])
                self.assertTrue(all(row["mean_heatmap_sha256"] == old["mean_heatmap_sha256"]
                                    for row, old in zip(emitted, native)))
                emitted[0]["candidates"][0]["native_score"] += .01
                destination.write_text("\n".join(json.dumps(row) for row in emitted) + "\n")
                with self.assertRaises(ValueError):
                    followup.pool_rows(root, destination, entry["block"], native)
        finally:
            array._mmap.close()

    def test_selector_boundary_ignores_reference_like_extra_fields(self):
        native = [{"source_frame_index": i, "source_pts_ticks": i * 1000, "time_base": "1/60000", "candidates": [],
                   "selected_candidate_index": None, "center_xy_px": None} for i in range(3)]
        pools = [[{"candidate_index": 0, "center_x": 10., "center_y": 10., "native_score": .4,
                   "in_source_bounds": True, "original_index": 0}] for _ in native]
        selected_args = []
        def chooser(used, seconds, width, parameters):
            selected_args.append(deepcopy((used, seconds, width, parameters)))
            return [0, 0, 0], {"objective": 3., "frames": [{"selected_pool_position": 0}] * 3}
        with patch.object(followup, "choose_sequence", side_effect=chooser):
            followup.select_arm(native, pools, 1280, self.config, "motion_only")
            changed = [{**row, "annotation": {"visibility": "hidden", "geometry": [999, 999]}, "outcome": "wrong"} for row in native]
            followup.select_arm(changed, pools, 1280, self.config, "motion_only")
        self.assertEqual(selected_args[0], selected_args[1])
        self.assertEqual(set(selected_args[0][0][0][0]), set(followup.SELECTOR_FIELDS))

    def test_import_is_cpu_only(self):
        result = subprocess.run([sys.executable, "-B", "-c", "import sys; from src.ball_tracking import weak_response_followup; assert 'torch' not in sys.modules"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

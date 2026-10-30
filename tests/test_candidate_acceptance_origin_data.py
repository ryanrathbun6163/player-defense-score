"""Synthetic transport failures and a few saved rows; no fitting or inference."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest

from src.ball_tracking import candidate_acceptance_origin_data as data


def feature(key, frame_key, fit, q=1.0):
    raw = {name: 0.0 for name in data.FEATURE_NAMES}
    raw.update(quality_logit=q, native_indicator=1, near_max_missing=1, quality_minus_near_max=None)
    return {"row_key": key, "frame_key": frame_key, "fit": fit, "status": "observed", "Q": q, "M": q,
            "feature_names": list(data.FEATURE_NAMES), "raw_features": raw,
            "values": [raw[name] for name in data.FEATURE_NAMES],
            "pool_provenance": {"excluded_self_row_keys": [key]}, "out_of_fitting_schema": False}


def fixture():
    loaded = {key: [] for key in data.FILES}
    loaded["original_J_models"] = {}
    targets = (("positive", 1), ("eligible_distant_miss", 0), ("certain_hidden", 0), ("masked_unknown", None))
    for name, game_id in data.GAMES.items():
        for i, (group, target) in enumerate(targets):
            cid, fid = name + "-candidate-" + str(i), name + "-frame-" + str(i)
            key, frame_key = "nba_out_of_fold|" + cid, "nba_out_of_fold|" + fid
            scores = {"Q": 1.0 + i, "M": 1.0 + i, "S": 1.0, "J": 2.0}
            candidate = {"row_key": key, "candidate_id": cid, "query_id": None, "frame_key": frame_key,
                         "frame_id": fid, "game_id": game_id, "block_id": name + "-block", "domain": "nba",
                         "context": "nba_out_of_fold", "fit": data.OLD_BASES[name], "gate_fit": "outer_" + name,
                         "cohort": "package", "target_group": group, "target": target, "logit": scores["Q"],
                         "scores": scores, "native_or_weak": "native", "selected_native": True,
                         "evaluation_category": "eligible_match" if target == 1 else "certain_hidden" if group == "certain_hidden" else "eligible_miss"}
            frame = {"frame_key": frame_key, "frame_id": fid, "game_id": game_id, "block_id": name + "-block",
                     "fit": data.OLD_BASES[name], "context": "nba_out_of_fold", "source_frame_index": i,
                     "eligible": group != "certain_hidden", "reference_category": group}
            loaded["candidates"].append(candidate)
            loaded["frames"].append(frame)
            current = feature(key, frame_key, data.OLD_BASES[name], scores["Q"])
            loaded["evaluation_features"].append(current)
            loaded["final_features"].append(deepcopy(current))
            for source in data.GAMES:
                if source == name:
                    continue
                base = source + "_only"
                loaded["cross_features"].append(feature(base + "|" + cid, base + "|" + fid, base, scores["Q"]))
            for policy in ("native", "quality_top"):
                loaded["fixed_policies"].append({**frame, "row_key": policy + "|" + frame_key, "policy": policy,
                    "chosen_row_key": key, "point_chosen_before_acceptance": True, "fallback_allowed": False,
                    "quality_top_tied_row_keys": [key], "original_pool_count": 1, "scores": deepcopy(scores),
                    "target_group": group, "native_or_weak": "native", "evaluation_category": candidate["evaluation_category"]})
    for gate in data.GATES:
        games = 3 if gate == "final_all_NBA" else 2
        selected = [r for r in loaded["candidates"] if gate == "final_all_NBA" or r["gate_fit"] != gate]
        members = []
        for row in selected:
            base = data.expected_source(gate, row)
            key = row["row_key"] if gate == "final_all_NBA" else base + "|" + row["candidate_id"]
            known = row["target"] is not None
            member = {"gate_fit": gate, "row_key": key, "candidate_id": row["candidate_id"], "game_id": row["game_id"],
                      "base_fit": base, "target": row["target"], "included_in_fitting": known,
                      "objective_weight": data.STRATUM_MASSES[row["target_group"]] / games if known else None}
            members.append(member)
        loaded["fit_membership"].extend(members)
        index = {r["row_key"]: r for r in loaded["final_features" if gate == "final_all_NBA" else "cross_features"]}
        # Deliberately differ from registry order: transport must honor saved J order.
        fitting = list(reversed([r for r in members if r["included_in_fitting"]]))
        scaler = {"feature_names": list(data.FEATURE_NAMES), "means": [0.0] * 16,
                  "scales": [1.0] * 16, "binary_features": sorted(data.BINARY)}
        def array(values, shape):
            return {"dtype": "little_endian_float64", "shape": shape,
                    "sha256": hashlib.sha256(b"".join(struct.pack("<d", value) for value in values)).hexdigest()}
        matrix = [0.0 if value is None else float(value) for r in fitting for value in index[r["row_key"]]["values"]]
        loaded["original_J_models"][gate] = {"status": "fitted", "arm": "J", "fit_id": gate,
            "feature_names": list(data.FEATURE_NAMES), "scaler": scaler, "training_row_count": len(fitting),
            "training_row_keys": [r["row_key"] for r in fitting], "training_arrays": {
                "features": array(matrix, [len(fitting), 16]),
                "targets": array([float(r["target"]) for r in fitting], [len(fitting)]),
                "weights": array([r["objective_weight"] for r in fitting], [len(fitting)])}}
    return loaded


class OriginDataTests(unittest.TestCase):
    def test_exact_saved_order_labels_weights_and_unknown_registry_preserved(self):
        loaded = fixture()
        before = deepcopy(loaded)
        data.validate_loaded(loaded, exact_counts=False)
        for gate in data.GATES:
            features, targets, weights = data.fit_inputs(gate, loaded)
            self.assertEqual([r["row_key"] for r in features], loaded["original_J_models"][gate]["training_row_keys"])
            self.assertEqual(set(targets), {0, 1})
            self.assertAlmostEqual(sum(weights), 1.0)
            self.assertEqual(len(features), 9 if gate == "final_all_NBA" else 6)
            index = loaded["feature_indices"]["final" if gate == "final_all_NBA" else "cross"]
            self.assertTrue(all(row is index[row["row_key"]] for row in features))
        for key in data.FILES:
            self.assertEqual(loaded[key], before[key])
        self.assertEqual(sum(r["target"] is None for r in loaded["candidates"]), 3)
        self.assertEqual(sum(not r["included_in_fitting"] for r in loaded["fit_membership"]), 9)

    def test_outer_game_leak_and_wrong_base_scorer_rejected(self):
        for field, value in (("game_id", data.GAMES["CHI"]), ("base_fit", "CHI_only")):
            loaded = fixture()
            row = next(r for r in loaded["fit_membership"] if r["gate_fit"] == "outer_CHI")
            row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                data.validate_loaded(loaded, exact_counts=False)

    def test_duplicate_candidate_across_gate_or_lost_unknown_rejected(self):
        loaded = fixture()
        duplicate = deepcopy(loaded["fit_membership"][0])
        duplicate["row_key"] += "-duplicate"
        loaded["fit_membership"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "duplicated"):
            data.validate_loaded(loaded, exact_counts=False)
        loaded = fixture()
        loaded["fit_membership"].pop(next(i for i, r in enumerate(loaded["fit_membership"]) if not r["included_in_fitting"]))
        with self.assertRaisesRegex(ValueError, "dropped"):
            data.validate_loaded(loaded, exact_counts=False)

    def test_unknown_mask_or_weight_change_rejected(self):
        for field, value in (("included_in_fitting", True), ("objective_weight", .01)):
            loaded = fixture()
            row = next(r for r in loaded["fit_membership"] if not r["included_in_fitting"])
            row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                data.validate_loaded(loaded, exact_counts=False)

    def test_feature_schema_same_frame_and_same_scorer_pool_required(self):
        loaded = fixture()
        loaded["cross_features"][0]["pool_provenance"]["excluded_self_row_keys"] = [loaded["cross_features"][1]["row_key"]]
        with self.assertRaisesRegex(ValueError, "pool provenance"):
            data.validate_loaded(loaded, exact_counts=False)
        item = feature("x", "f", "base")
        item["values"][0] += 1
        with self.assertRaisesRegex(ValueError, "array/dictionary"):
            data.validate_feature(item)

    def test_saved_J_array_hash_detects_changed_values_or_training_order(self):
        loaded = fixture()
        loaded["original_J_models"]["outer_CHI"]["training_row_keys"].reverse()
        with self.assertRaisesRegex(ValueError, "array binding"):
            data.validate_loaded(loaded, exact_counts=False)
        loaded = fixture()
        row = loaded["cross_features"][0]
        row["raw_features"]["padding_fraction"] = .1
        row["values"][3] = .1
        with self.assertRaisesRegex(ValueError, "feature array binding"):
            data.validate_loaded(loaded, exact_counts=False)

    def test_stratum_mass_change_rejected_before_array_binding(self):
        loaded = fixture()
        next(r for r in loaded["fit_membership"] if r["included_in_fitting"])["objective_weight"] *= 2
        with self.assertRaisesRegex(ValueError, "objective masses"):
            data.validate_loaded(loaded, exact_counts=False)

    def test_fixed_policy_choice_fallback_ties_and_score_transport_immutable(self):
        for field, value in (("chosen_row_key", None), ("fallback_allowed", True),
                             ("quality_top_tied_row_keys", []), ("scores", {"Q": -99})):
            loaded = fixture()
            loaded["fixed_policies"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                data.validate_fixed_policies(loaded["frames"], loaded["candidates"], loaded["fixed_policies"])

    def test_missing_features_stay_null(self):
        item = {"row_key": "missing", "feature_names": list(data.FEATURE_NAMES), "status": "missing_image",
                "Q": None, "M": None, "raw_features": None, "values": None}
        data.validate_feature(item)
        item["values"] = [0.0] * 16
        with self.assertRaisesRegex(ValueError, "fabricated"):
            data.validate_feature(item)

    def test_small_saved_feature_samples_preserve_original_schema_and_missing_slots(self):
        root = Path(__file__).resolve().parents[1]
        with (root / data.SOURCE / "evaluation_features.jsonl").open(encoding="utf-8") as stream:
            first = json.loads(next(stream))
            data.validate_feature(first)
            # Read until the first missing image; inspect schema, not an outcome statistic.
            missing = next(json.loads(line) for line in stream if '"status":"missing_image"' in line)
        data.validate_feature(missing)
        self.assertEqual(first["values"][0], first["Q"])
        self.assertIsNone(missing["values"])

    def test_import_and_synthetic_transport_do_not_load_numerical_or_ML_libraries(self):
        code = ("import sys; from tests.test_candidate_acceptance_origin_data import fixture; "
                "from src.ball_tracking import candidate_acceptance_origin_data as d; "
                "d.validate_loaded(fixture(),exact_counts=False); "
                "assert not any(k in sys.modules for k in ('torch','numpy','scipy','PIL','transformers')); print('metadata-only')")
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "metadata-only")


if __name__ == "__main__":
    unittest.main()

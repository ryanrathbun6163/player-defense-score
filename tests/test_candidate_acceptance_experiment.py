"""Bounded runner integration; fake predictors and temporary output roots only."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import candidate_acceptance_data as data
from src.ball_tracking import candidate_acceptance_experiment as experiment


def point(key, *, game="CHI", context="nba_out_of_fold", cohort="package", frame=None, q=1, **extra):
    return {"row_key": key, "candidate_id": key, "frame_key": frame or key + "_frame",
            "fit": "base", "game_id": data.GAMES.get(game, game), "context": context,
            "cohort": cohort, "logit": q, "center_xy_px": [0, 0] if q is not None else None,
            "native_score": 7, "component_pixels": 3, "padding_pixels": 0,
            "native_or_weak": "native", "target": 1, "visibility": "visible", **extra}


def fake_feature(row, pool):
    reason = "missing_image" if row["logit"] is None else "pool_unavailable" if pool is None else None
    return {"row_key": row["row_key"], "frame_key": row["frame_key"], "fit": row["fit"],
            "Q": row["logit"], "M": row["logit"], "M_fallback_reason": reason}


def fake_binding(root, path):
    return {"path": Path(path).relative_to(root).as_posix(), "sha256": "test-only", "bytes": 0}


class CandidateAcceptanceExperimentTests(unittest.TestCase):
    def test_feature_adapter_is_label_blind_and_stress_never_enters_original_pool(self):
        candidates = [point("native", frame="shared"), point("unknown", frame="shared", target=None),
                      point("stress", frame="shared", cohort="HOU_stress", target=0, out_of_fitting_schema=True),
                      point("empty", frame="empty", cohort="HOU_stress"),
                      point("history", cohort="historical", context="historical", out_of_fitting_schema=True),
                      point("missing", cohort="HOU_stress", q=None)]
        pools = data.pool_index(candidates)
        calls = []

        def builder(row, pool):
            calls.append((copy.deepcopy(row), copy.deepcopy(pool)))
            return fake_feature(row, pool)

        before = experiment.features_for(candidates, pools, builder)
        self.assertEqual(len(calls), 6)
        expected_names = {"row_key", "frame_key", "fit", "cohort", "logit", "center_xy_px", "native_score",
                          "component_pixels", "padding_pixels", "native_or_weak"}
        for supplied, pool in calls:
            self.assertEqual(set(supplied), expected_names)
            for neighbor in pool or []:
                self.assertEqual(set(neighbor), expected_names)
        self.assertEqual([r["row_key"] for r in calls[2][1]], ["native", "unknown"])
        self.assertEqual(calls[3][1], [])
        self.assertIsNone(calls[4][1])
        self.assertEqual(calls[5][1], [])
        self.assertTrue(before[2]["out_of_fitting_schema"])
        self.assertTrue(before[4]["out_of_fitting_schema"])
        self.assertIsNone(before[5]["Q"])
        original_calls = copy.deepcopy(calls)
        altered = copy.deepcopy(candidates)
        for row in altered:
            row.update(target=0, visibility="hidden", game_id="annotation-change", distance_px=9999,
                       recorded_uncertainty_radius_px=999, difficulty_tags=["irrelevant"],
                       annotation={"geometry": {"center_xy_px": [900, 900]}})
        calls.clear()
        after = experiment.features_for(altered, data.pool_index(altered), builder)
        self.assertEqual(calls, original_calls)
        self.assertEqual(after, before)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            experiment.features_for([candidates[0], candidates[0]], pools, builder)

    def test_prediction_routing_preserves_order_old_quality_missing_slots_and_fallback_flags(self):
        candidates = [point("den", game="DEN", q=2),
                      point("hou", game="HOU", context="HOU_development", cohort="HOU_main", q=3),
                      point("chi", game="CHI", q=4), point("sac", game="SAC", q=5),
                      point("old", game="history", context="historical", cohort="historical", q=-1),
                      point("missing", game="HOU", context="HOU_development", cohort="HOU_stress", q=None)]
        features = {r["row_key"]: fake_feature(r, None if r["cohort"] == "historical" else []) for r in candidates}
        features["hou"]["M_fallback_reason"] = "no_far_rival"
        models = {(gate, arm): (gate, arm) for gate in experiment.GATES for arm in ("S", "J")}
        calls = []

        def predict(model, vectors):
            calls.append((model, [r["row_key"] for r in vectors]))
            offset = 10 if model[1] == "S" else 100
            return [None if r["Q"] is None else r["Q"] + offset for r in vectors]

        experiment.attach_gate_predictions(candidates, features, models, predict)
        self.assertEqual([r["row_key"] for r in candidates], ["den", "hou", "chi", "sac", "old", "missing"])
        self.assertEqual([r["gate_fit"] for r in candidates],
                         ["outer_DEN", "final_all_NBA", "outer_CHI", "outer_SAC", "final_all_NBA", "final_all_NBA"])
        self.assertEqual(len(calls), 8)
        for (gate, arm), keys in calls:
            self.assertEqual(keys, {"outer_CHI": ["chi"], "outer_DEN": ["den"], "outer_SAC": ["sac"],
                                    "final_all_NBA": ["hou", "old", "missing"]}[gate])
        for row in candidates[:-1]:
            self.assertEqual(row["scores"]["Q"], row["logit"])
            self.assertEqual(row["scores"]["S"], row["logit"] + 10)
            self.assertEqual(row["scores"]["J"], row["logit"] + 100)
        self.assertEqual(candidates[-1]["scores"], {"Q": None, "M": None, "S": None, "J": None})
        self.assertIsNone(candidates[-1]["M_no_rival_fallback"])
        self.assertTrue(candidates[1]["M_no_rival_fallback"])
        self.assertTrue(candidates[4]["M_no_rival_fallback"])
        self.assertFalse(candidates[0]["M_no_rival_fallback"])

    def test_prediction_missingness_row_count_and_numeric_integrity_fail_closed(self):
        models = {(gate, arm): object() for gate in experiment.GATES for arm in ("S", "J")}
        for quality, predicted, reason in ((1, None, "missingness changed"),
                                          (None, 0, "missingness changed"),
                                          (1, True, "Nonfinite/malformed"),
                                          (1, "1", "Nonfinite/malformed"),
                                          (1, float("nan"), "Nonfinite/malformed"),
                                          (1, float("inf"), "Nonfinite/malformed")):
            with self.subTest(quality=quality, predicted=predicted):
                row = point("test", q=quality)
                features = {"test": fake_feature(row, [])}
                predictor = lambda model, vectors: [predicted for _ in vectors]
                with self.assertRaisesRegex(ValueError, reason):
                    experiment.attach_gate_predictions([row], features, models, predictor)
        row = point("test")
        features = {"test": fake_feature(row, [])}
        with self.assertRaisesRegex(ValueError, "Predictions dropped rows"):
            experiment.attach_gate_predictions([row], features, models, lambda model, vectors: [])
        with self.assertRaises(KeyError):
            experiment.attach_gate_predictions([row], {}, models, lambda model, vectors: [])
        features["test"]["Q"] = 99
        with self.assertRaisesRegex(ValueError, "Original quality score changed"):
            experiment.attach_gate_predictions([row], features, models, lambda model, vectors: [1 for _ in vectors])

    def test_existing_analysis_is_refused_before_preflight_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / experiment.OUTPUT
            output.mkdir(parents=True)
            sentinel = output / "completed.json"
            sentinel.write_bytes(b"preserved completed results")
            with patch.object(experiment, "check_frozen") as frozen, patch.object(experiment, "checked_new_scores") as scores:
                with self.assertRaisesRegex(ValueError, "no automatic retry"):
                    experiment.analyze(root)
                frozen.assert_not_called()
                scores.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b"preserved completed results")
            self.assertEqual(list(output.iterdir()), [sentinel])

    def test_preflight_and_score_audit_failures_create_no_analysis_output(self):
        for stage in ("freeze", "scores"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with patch.object(experiment, "check_frozen", side_effect=ValueError("freeze failure") if stage == "freeze" else None,
                                  return_value=({}, {})), \
                     patch.object(experiment, "checked_new_scores", side_effect=ValueError("score audit failure")) as scores, \
                     patch.object(experiment.data, "load_saved") as loader:
                    with self.assertRaisesRegex(ValueError, "failure"):
                        experiment.analyze(root)
                    loader.assert_not_called()
                    if stage == "freeze":
                        scores.assert_not_called()
                self.assertFalse((root / experiment.OUTPUT).exists())

    def test_analysis_failure_persists_receipt_and_refuses_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(experiment, "check_frozen", return_value=({}, {})), \
                 patch.object(experiment, "checked_new_scores", return_value=[]), \
                 patch.object(experiment.neural, "binding", side_effect=fake_binding), \
                 patch.object(experiment.data, "load_saved", side_effect=ValueError("synthetic metadata failure")) as loader:
                with self.assertRaisesRegex(ValueError, "synthetic metadata failure"):
                    experiment.analyze(root)
                output = root / experiment.OUTPUT
                self.assertEqual({p.name for p in output.iterdir()}, {"started.json", "failed.json"})
                failed_bytes = (output / "failed.json").read_bytes()
                failure = json.loads(failed_bytes)
                self.assertEqual(failure["error"], "ValueError")
                self.assertFalse(failure["automatic_retry"])
                self.assertIn("synthetic metadata failure", failure["traceback"])
                self.assertEqual(json.loads((output / "started.json").read_text())["new_model_calls"], 0)
                with self.assertRaisesRegex(ValueError, "no automatic retry"):
                    experiment.analyze(root)
                self.assertEqual(loader.call_count, 1)
                self.assertEqual((output / "failed.json").read_bytes(), failed_bytes)

    def test_jsonl_outputs_are_exclusive_and_missing_remains_null(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.jsonl"
            count = experiment.write_lines(path, ({"id": key, "score": value} for key, value in (("missing", None), ("zero", 0))))
            self.assertEqual(count, 2)
            before = path.read_bytes()
            self.assertEqual(list(data.rows(path)), [{"id": "missing", "score": None}, {"id": "zero", "score": 0}])
            with self.assertRaises(FileExistsError):
                experiment.write_lines(path, [{"replacement": True}])
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(ValueError):
                experiment.write_lines(Path(directory) / "bad.jsonl", [{"score": float("nan")}])

    def test_freeze_requires_all_cpu_sources_and_exact_pinned_dependencies(self):
        root = Path("synthetic-test-root").resolve()
        specification = {"path": experiment.neural.CONFIG, "sha256": experiment.neural.SPEC_SHA256, "bytes": 1}
        freeze_path = root / experiment.neural.LAUNCH_BASE / "execution_freeze.json"
        freeze_binding = {"path": "freeze", "sha256": "freeze", "bytes": 1}
        spec = {"protocol": {"path": "protocol"}, "input_bindings": [{"path": "old-input", "sha256": "old"}]}
        freeze = {"status": "frozen_for_authorized_execution", "specification": specification,
                  "implementation": [{"path": path} for path in sorted(experiment.REQUIRED)],
                  "inputs": spec["input_bindings"], "review": [{"path": "independent-review"}],
                  "focused_tests": {"path": "tests-receipt"}}
        documents = {experiment.neural.CONFIG: spec,
                     experiment.neural.LAUNCH_BASE + "/execution_freeze.json": freeze,
                     experiment.neural.LAUNCH_BASE + "/execution_authorization.json": {"authorized": "test"}}
        read = lambda path: documents[Path(path).relative_to(root).as_posix()]
        binding = lambda base, path: freeze_binding if Path(path) == freeze_path else specification
        with patch.object(experiment.neural, "read", side_effect=read), \
             patch.object(experiment.neural, "binding", side_effect=binding), \
             patch.object(experiment.neural, "bound") as bound, \
             patch.object(experiment.neural, "validate_authorization") as authorize, \
             patch.object(experiment.metadata, "version", side_effect=lambda name: {"numpy": "2.4.6", "scipy": "1.17.1"}[name]):
            self.assertEqual(experiment.check_frozen(root), (spec, freeze))
            authorize.assert_called_once_with({"authorized": "test"}, freeze_binding, specification)
            self.assertEqual(bound.call_count, len(experiment.REQUIRED) + 4)
            freeze["implementation"].pop()
            with self.assertRaisesRegex(ValueError, "implementation bindings missing"):
                experiment.check_frozen(root)
            freeze["implementation"] = [{"path": path} for path in experiment.REQUIRED]
            with patch.object(experiment.metadata, "version", return_value="different"):
                with self.assertRaisesRegex(ValueError, "package versions changed"):
                    experiment.check_frozen(root)


if __name__ == "__main__":
    unittest.main()

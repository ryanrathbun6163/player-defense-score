"""Metadata/synthetic checks only; never construct a model or query a GPU."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import candidate_acceptance_neural as neural


def synthetic_candidates():
    result = []
    for name, game in neural.GAMES.items():
        for group, target in (("positive", 1), ("eligible_distant_miss", 0), ("certain_hidden", 0), ("masked_unknown", None)):
            origins = ("weak",) if group == "certain_hidden" else ("native", "weak")
            for origin in origins:
                result.append({"candidate_id": f"{name}-{group}-{origin}", "domain": "nba", "game_id": game,
                               "block_id": name + "-block", "frame_id": name + "-" + group,
                               "native_or_weak": origin, "target": target, "target_group": group})
    result.append({"candidate_id": "nfhs", "domain": "nfhs", "game_id": "secondary",
                   "block_id": "secondary", "frame_id": "secondary", "native_or_weak": "native",
                   "target": 1, "target_group": "positive"})
    return result


def authorization():
    return {"execution_approved": True, "execution_freeze": {"sha256": "freeze"},
            "specification": {"sha256": "spec"}, "scope": dict(neural.COUNTS),
            "max_total_seconds": 5400, "user_statement": "ok chat move forward. thank you for this",
            "automatic_retry": False, "automatic_extension": False, "protected_access_approved": False,
            "new_labels_approved": False, "selector_approved": False}


def readiness(now):
    return {"at_utc": now.isoformat(), "execution_freeze": {"sha256": "freeze"},
            "execution_authorization": {"sha256": "authorization"}, "driver_version": "617.42",
            "gpu_uuid": neural.GPU, "power_limit_W": 250, "temperature_C": 40,
            "ram_configured_mt_s": [5200, 5200], "isolation_conflicts": [], "existing_gpu_workers": [],
            "debug_mode_enabled": True, "debug_mode_state_basis": "ui_observed", "configuration_changes": [],
            "unexpected_setting_changes": [], "settings_changed": False, "settings_changed_by_agent": False,
            "fresh_launch_checks_passed": True, "sources": [{"path": str(i)} for i in range(3)]}


class NeuralPreparationTests(unittest.TestCase):
    def test_fresh_import_and_real_metadata_preparation_do_not_import_ml(self):
        code = ("import sys; from src.ball_tracking import candidate_acceptance_neural as n; "
                "p=n.prepare_neural(); assert p['counts']==n.COUNTS; "
                "assert not any(x in sys.modules for x in ('torch','numpy','PIL','transformers')); "
                "print('metadata-only')")
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=neural.ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "metadata-only")

    def test_all_known_rows_and_only_one_game_enter_each_fit(self):
        candidates = synthetic_candidates()
        for name in neural.FIT_NAMES:
            plan = neural.make_fit_plan(candidates, name)
            rows = {r["candidate_id"]: r for r in candidates}
            actual = [rows[w["candidate_id"]] for w in plan["weights"]]
            self.assertEqual({r["game_id"] for r in actual}, {plan["fit_game_id"]})
            self.assertEqual(len(actual), 5)
            self.assertTrue(all(r["target"] is not None for r in actual))
            self.assertEqual({r["target_group"] for r in actual}, {"positive", "eligible_distant_miss", "certain_hidden"})

    def test_single_game_weights_recomputed_with_absent_native_hidden_child(self):
        candidates = synthetic_candidates()
        plan = neural.make_fit_plan(candidates, "DEN_only")
        weights = {w["candidate_id"]: w for w in plan["weights"]}
        self.assertEqual(weights["DEN-certain_hidden-weak"]["objective_weight"], 0.25)
        self.assertEqual(weights["DEN-positive-native"]["objective_weight"], 0.25)
        self.assertEqual(weights["DEN-eligible_distant_miss-native"]["objective_weight"], 0.125)
        self.assertAlmostEqual(sum(w["objective_weight"] for w in weights.values()), 1)
        self.assertTrue(all(w["training_multiplier"] == 5 * w["objective_weight"] for w in weights.values()))

    def test_whole_game_exclusion_and_unknown_score_preservation(self):
        plan = neural.make_fit_plan(synthetic_candidates(), "CHI_only")
        self.assertEqual([g["name"] for g in plan["score_groups"]], ["DEN", "SAC"])
        for group in plan["score_groups"]:
            self.assertEqual(group["candidates"], 7)
            self.assertEqual(group["forwards"], 1)
            self.assertTrue(all(key.startswith(group["name"] + "-") for key in group["candidate_ids"]))
            self.assertEqual(sum("masked_unknown" in key for key in group["candidate_ids"]), 2)
        self.assertFalse(any("nfhs" in g["candidate_ids"] for g in plan["score_groups"]))

    def test_unknown_and_held_labels_cannot_change_single_game_weights(self):
        first = synthetic_candidates()
        second = deepcopy(first)
        for row in second:
            if row["game_id"] != neural.GAMES["CHI"]:
                row["target"], row["target_group"] = None, "masked_unknown"
        self.assertEqual(neural.make_fit_plan(first, "CHI_only"), neural.make_fit_plan(second, "CHI_only"))

    def test_duplicate_id_or_missing_required_stratum_rejected(self):
        candidates = synthetic_candidates()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            neural.make_fit_plan(candidates + [candidates[0]], "CHI_only")
        missing = [r for r in candidates if not (r["game_id"] == neural.GAMES["DEN"] and r["target_group"] == "certain_hidden")]
        with self.assertRaisesRegex(ValueError, "stratum"):
            neural.make_fit_plan(missing, "DEN_only")

    def test_target_game_batches_are_separate_not_concatenated(self):
        plan = neural.make_fit_plan(synthetic_candidates(), "CHI_only")
        self.assertEqual(neural.plan_counts([plan])["cross_game_score_forwards_game_batched"], 2)
        self.assertEqual(neural.plan_counts([plan])["cross_game_score_presentations"], 14)

    def test_real_den_hidden_support_and_source_order(self):
        prepared = neural.prepare_neural()
        den = prepared["fits"][1]
        support = den["summary"]["stratum_support"]["certain_hidden"][neural.GAMES["DEN"]]
        self.assertEqual(support, {"blocks": 1, "frames": 8, "candidates": 12})
        self.assertEqual([p["fit"] for p in prepared["fits"]], list(neural.FIT_NAMES))
        original = neural.rows(neural.ROOT / neural.CANDIDATES)
        for plan in prepared["fits"]:
            for group in plan["score_groups"]:
                self.assertEqual(group["candidate_ids"], [r["candidate_id"] for r in original
                    if r["domain"] == "nba" and r["game_id"] == group["game_id"]])


class LaunchGuardTests(unittest.TestCase):
    def test_authorization_binds_exact_scope_and_rejects_old_approval(self):
        item = authorization()
        neural.validate_authorization(item, {"sha256": "freeze"}, {"sha256": "spec"})
        for field, value in (("execution_approved", False), ("execution_freeze", {}), ("specification", {}),
                             ("user_statement", ""), ("automatic_retry", True), ("automatic_extension", True),
                             ("protected_access_approved", True), ("selector_approved", True), ("max_total_seconds", 5401)):
            changed = deepcopy(item)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                neural.validate_authorization(changed, {"sha256": "freeze"}, {"sha256": "spec"})
        changed = deepcopy(item)
        changed["scope"]["quality_fits"] = 4
        with self.assertRaises(ValueError):
            neural.validate_authorization(changed, {"sha256": "freeze"}, {"sha256": "spec"})

    def test_readiness_lease_and_observed_debug_state(self):
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        item = readiness(now)
        neural.validate_readiness(item, {"sha256": "freeze"}, {"sha256": "authorization"}, now)
        for field, value in (("debug_mode_state_basis", "user_reported"), ("debug_mode_enabled", False),
                             ("temperature_C", 80), ("driver_version", "old"), ("existing_gpu_workers", [123]),
                             ("settings_changed_by_agent", True), ("execution_authorization", {}), ("sources", []),
                             ("at_utc", (now - timedelta(seconds=121)).isoformat()),
                             ("at_utc", (now + timedelta(seconds=3)).isoformat())):
            changed = deepcopy(item)
            changed[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                neural.validate_readiness(changed, {"sha256": "freeze"}, {"sha256": "authorization"}, now)

    def test_policy_scope_and_cleanup_reserve(self):
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        policy = {"module": neural.MODULE, "arguments": ["--run", "--monitor", neural.MONITOR],
                  "sample_seconds": 2, "temperature_stop_C": 80, "telemetry_timeout_seconds": 5,
                  "grace_seconds": 10, "automatic_retry": False, "max_total_seconds": 5400,
                  "soft_stop_seconds": 5370, "gpu_uuid": neural.GPU, "created_at_utc": now.isoformat()}
        neural.validate_policy(policy)
        self.assertEqual(neural.remaining_wall_seconds(policy, now + timedelta(seconds=5369)), 31)
        with self.assertRaisesRegex(ValueError, "deadline"):
            neural.remaining_wall_seconds(policy, now + timedelta(seconds=5370))
        for field, value in (("module", "old_worker"), ("arguments", ["--run"]), ("automatic_retry", True),
                             ("max_total_seconds", 5500), ("soft_stop_seconds", 5400)):
            changed = {**policy, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                neural.validate_policy(changed)

    def test_accounting_rejects_a_partial_or_extra_forward(self):
        neural.validate_counters(neural.COUNTER_EXPECTED)
        for key in neural.COUNTER_EXPECTED:
            changed = dict(neural.COUNTER_EXPECTED)
            changed[key] += 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                neural.validate_counters(changed)

    def test_fixed_monitor_is_checked_before_preflight_or_runtime(self):
        with patch.object(neural, "preflight") as preflight:
            with self.assertRaisesRegex(ValueError, "declared owned"):
                neural.run(neural.ROOT, "old-monitor", ["--run", "--monitor", "old-monitor"])
            preflight.assert_not_called()

    def test_bindings_reject_escape_change_and_writes_preserve_old_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "artifact.json"
            neural.write_once(path, {"preserve": True})
            old = path.read_bytes()
            link = neural.binding(root, path)
            self.assertEqual(neural.bound(root, link), path.resolve())
            with self.assertRaises(FileExistsError):
                neural.write_once(path, {"preserve": False})
            self.assertEqual(path.read_bytes(), old)
            with self.assertRaisesRegex(ValueError, "escapes"):
                neural.owned_path(root, "../outside")
            path.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Binding differs"):
                neural.bound(root, link)


if __name__ == "__main__":
    unittest.main()

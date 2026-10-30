"""Render transport checked against the actual completed follow-up producer."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import unittest

from src.ball_tracking import weak_response_followup_render as render
from src.ball_tracking.weak_response_capture import read, bound

ROOT = Path(__file__).resolve().parents[1]


class FollowupRenderTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / render.COMPARISON
        if not path.exists():
            raise unittest.SkipTest("Completed actual follow-up producer is required; no synthetic replacement")
        cls.comparison = read(path)
        cls.config = read(bound(ROOT, cls.comparison["config"]))
        cls.package = read(bound(ROOT, cls.comparison["paired_inputs"]))
        cls.entry = cls.package["blocks"][1]
        cls.record = cls.comparison["records"][1]
        cls.arm = "motion_and_speed_narrow_weak"

    def test_actual_records_keep_original_arm_and_native_bindings(self):
        frozen = read(bound(ROOT, self.comparison["freeze"]))
        try:
            bound(ROOT, frozen["tests"])
        except (FileNotFoundError, ValueError):
            self.skipTest("Historical render preflight requires the frozen preparation-test version; "
                          "post-study test edits do not invalidate completed scientific records")
        for arm in render.ARMS:
            entries, records, identity = render.preflight(ROOT, render.COMPARISON, arm)
            self.assertEqual(identity["actual_arm_name"], arm)
            self.assertFalse(identity["display_aliases_used"])
            clarification = read(bound(ROOT, identity["prospective_history_clarification"]))
            self.assertEqual(clarification["original_freeze"], self.comparison["freeze"])
            self.assertEqual(len(entries), 8)
            self.assertEqual(sum(len(e["block"]["frames"]) for e in entries), 3662)
            for source, adapted in zip(self.comparison["records"], records, strict=True):
                self.assertEqual(adapted["variants"][arm], source["variants"][arm])
                self.assertEqual(adapted["variants"]["native"], source["controls"]["native"])

    def test_actual_choice_envelope_rejects_alias_and_provenance_tampering(self):
        body = read(bound(ROOT, self.record["variants"][self.arm]))
        render.validate_choice(body, self.record, self.entry, self.arm, self.config)
        def changed(key, value):
            candidate = deepcopy(body)
            candidate[key] = value
            return candidate
        cases = [changed("variant", "sequence_weak"), changed("references_used_in_selection", True),
                 changed("pool_source", self.record["controls"]["native"]),
                 changed("pool_policy", "native_plus_0.03"), changed("observations", body["observations"][:-1])]
        wrong_time = deepcopy(body)
        wrong_time["observations"][0]["source_pts_ticks"] += 1
        cases.append(wrong_time)
        wrong_parameter = deepcopy(body)
        wrong_parameter["sequence_parameters"]["motion_cost_weight"] += .01
        cases.append(wrong_parameter)
        for candidate in cases:
            with self.subTest(candidate=candidate.get("variant")), self.assertRaises(ValueError):
                render.validate_choice(candidate, self.record, self.entry, self.arm, self.config)

    def test_actual_compact_choices_materialize_from_exact_bound_pool(self):
        block, native = self.entry["block"], self.entry["candidate_observations"]
        pools = render.experiment.pool_rows(ROOT, bound(ROOT, self.record["pool_source"]), block, native)
        for arm in render.ARMS:
            used = pools if arm.endswith("narrow_weak") else [[c for c in p if c["original_index"] is not None] for p in pools]
            body = read(bound(ROOT, self.record["variants"][arm]))
            rows = render.experiment.materialize_choices(body, used)
            render.review.validate_observations(block, rows, baseline=native, expected_pools=used)
            entry = {"block": block, "baseline_observations": native, "candidate_observations": rows,
                "candidate_pool_source": self.record["pool_source"],
                "candidate_pool_policy": "all" if arm.endswith("narrow_weak") else "native_only",
                "candidate_pool_projection": list(render.experiment.SELECTOR_FIELDS)}
            render.review.verify_pool_source(ROOT, entry)
            self.assertEqual(len(rows), 120)
            self.assertTrue(all(row["selected_candidate_index"] == compact["selected_candidate_index"]
                                for row, compact in zip(rows, body["observations"], strict=True)))


class FollowupRenderImportTests(unittest.TestCase):
    def test_import_is_cpu_only(self):
        result = subprocess.run([sys.executable, "-B", "-c",
            "import sys; from src.ball_tracking import weak_response_followup_render; assert 'torch' not in sys.modules"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

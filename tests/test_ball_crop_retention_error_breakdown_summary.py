"""Fabricated-only contracts for the bounded saved-membership formatter."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from src.ball_tracking import crop_retention_error_breakdown_summary as summary


def seal(value, field="content_sha256"):
    value[field] = hashlib.sha256(json.dumps({k: v for k, v in value.items() if k != field},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    return value


def fabricated_audit():
    return seal({"schema_version": summary.AUDIT_SCHEMA, "status": "passed",
                 "execution_code_commit": summary.AUDIT_COMMIT,
                 "original_evaluation_commit": summary.SCORING_COMMIT,
                 "original_evaluation_spec_sha256": summary.SCORING_SPEC,
                 "original_selection_commit": summary.SELECTION_COMMIT,
                 "original_selection_spec_sha256": summary.SELECTION_SPEC,
                 "pool_audits": [{"purpose": p} for p in summary.PURPOSES],
                 "review_audits": [{"window_id": w["window_id"]} for w in summary.WINDOWS],
                 "selected_method": None, "selected_operating_point": None, "quality_gate": None})


def fabricated_pool(purpose=summary.PURPOSES[0], order=(2, 0, 1)):
    windows = [w for w in summary.WINDOWS if w["purpose"] == purpose]
    windows = [windows[i] for i in order]
    rows = []
    for window in windows:
        first, last = window["start_frame_index"], window["end_frame_index"]
        for arm in summary.ARMS:
            for radius in (5.0, 10.0, 15.0, 20.0, 30.0):
                for confidence in (.01, .20, .35):
                    for policy in ("cap20", "all"):
                        parts = {summary.PARTS[0]: [first], summary.PARTS[1]: [] if confidence == .01 else [first + 1],
                                 summary.PARTS[2]: [first + 2] if policy == "cap20" else [], summary.PARTS[3]: [first + 3]}
                        role = "saved" if policy == "cap20" else "new_distinct" if confidence == .01 else "structural_equivalence_not_executed"
                        rows.append({"arm": arm, "radius_px": radius, "confidence_threshold": confidence,
                                     "retention_policy": policy, "selection_execution_role": role, "parts": parts,
                                     "total_missed_eligible_frames": sum(len(v) for v in parts.values()),
                                     "false_observations_on_eligible_frames": [first + 3], "hidden_alarm_frames": [last],
                                     "candidate_burden_is_tracker_accuracy": False, "semantic_training_labels_created": False})
    return seal({"schema_version": summary.POOL_SCHEMA, "purpose": purpose,
                 "code_commit": summary.SCORING_COMMIT, "experiment_spec_sha256": summary.SCORING_SPEC,
                 "retention_measurements": [{"window_id": w["window_id"], "measurements": "RAW_MEASUREMENT_SENTINEL"} for w in windows],
                 "loss_decomposition": rows, "evaluation_reports": [{"raw_payload": "RAW_REPORT_SENTINEL"}],
                 "path_reference": {"path": "forbidden/raw.json", "json_pointer": "/never/read"},
                 "selected_method": None, "selected_operating_point": None, "quality_gate": None,
                 "semantic_training_labels_created": False, "independent_trials_claimed": False})


def resolve(value, pointer):
    for part in pointer.lstrip("/").split("/"):
        value = value[int(part)] if type(value) is list else value[part]
    return value


class ErrorBreakdownSummaryTests(unittest.TestCase):
    def setUp(self):
        self.audit = fabricated_audit()
        self.pools = [fabricated_pool(p) for p in summary.PURPOSES]

    def extract(self, pool=None):
        return summary.extract_pool(self.pools[0] if pool is None else pool, self.audit)

    def assembled(self):
        return summary.build_summary([self.extract(p) for p in self.pools])

    def test_shuffled_saved_window_blocks_define_identity_and_complete_inventory(self):
        result, markdown = self.assembled()
        self.assertEqual(result["schema_version"], summary.SUMMARY_SCHEMA)
        self.assertEqual([p["purpose"] for p in result["pools"]], list(summary.PURPOSES))
        for pool, source in zip(result["pools"], self.pools):
            self.assertEqual(len(pool["rows"]), 24)
            self.assertEqual([pool["rows"][i]["window_id"] for i in (0, 8, 16)],
                             [m["window_id"] for m in source["retention_measurements"]])
            self.assertEqual({(r["arm"], r["retention_policy"]) for r in pool["rows"]},
                             {(a, p) for a in summary.ARMS for p in summary.POLICIES})
            for row in pool["rows"]:
                saved = resolve(source, row["source_row_pointer"])
                self.assertEqual(row["window_id"], resolve(source, row["window_identity_pointer"]))
                for field in ("parts", "total_missed_eligible_frames", *summary.OTHER_LISTS, "selection_execution_role"):
                    self.assertEqual(row[field], saved[field])
        self.assertEqual(markdown.count("[saved row]"), 48)
        self.assertLessEqual(len(markdown.encode("utf-8")), 65536)
        self.assertTrue(all(result[k] is None for k in summary.DECISIONS))
        self.assertIn("can include missing output", markdown)
        self.assertIn("must not be added", markdown)

    def test_every_value_and_membership_count_has_exact_inert_sources(self):
        result, _ = self.assembled()
        inputs = {"representative_pool": self.pools[0], "challenge_pool": self.pools[1], "audit": self.audit,
                  "window_authority": {"windows": list(summary.WINDOWS)}}
        for entry in result["source_map"]:
            value = resolve(inputs[entry["input"]], entry["json_pointer"])
            expected = len(value) if entry["operation"] == "list_length" else value
            self.assertEqual(resolve(result, entry["output_pointer"]), expected)
            if entry["window_identity_pointer"] is not None:
                pool_index = int(entry["output_pointer"].split("/")[2])
                pool = inputs[result["pools"][pool_index]["source_input"]]
                self.assertIn(resolve(pool, entry["window_identity_pointer"]), [w["window_id"] for w in summary.WINDOWS])
        operations = {e["operation"] for e in result["source_map"]}
        self.assertEqual(operations, {"copied", "list_length"})

    def test_empty_memberships_remain_empty_zero_and_inputs_are_not_modified(self):
        pool = copy.deepcopy(self.pools[0])
        row = pool["loss_decomposition"][6]
        row["parts"] = {k: [] for k in summary.PARTS}
        row.update(total_missed_eligible_frames=0, false_observations_on_eligible_frames=[], hidden_alarm_frames=[])
        seal(pool)
        original = copy.deepcopy(pool)
        extracted = self.extract(pool)
        self.assertEqual(pool, original)
        self.assertTrue(all(v == 0 for v in extracted["rows"][0]["membership_counts"].values()))
        extracted["rows"][0]["parts"][summary.PARTS[0]].append(999)
        self.assertEqual(pool, original)

    def test_missing_duplicate_or_mixed_window_mapping_stops(self):
        for mutation in (lambda p: p["retention_measurements"].pop(),
                         lambda p: p["retention_measurements"].__setitem__(1, copy.deepcopy(p["retention_measurements"][0])),
                         lambda p: p["retention_measurements"][0].__setitem__("window_id", summary.WINDOWS[1]["window_id"]),
                         lambda p: p["retention_measurements"].reverse()):
            with self.subTest(mutation=mutation):
                pool = copy.deepcopy(self.pools[0]); mutation(pool); seal(pool)
                with self.assertRaises(ValueError):
                    self.extract(pool)

    def test_full_block_key_role_sequence_and_cardinality_are_required(self):
        for mutation in (lambda rows: rows.pop(), lambda rows: rows.append(copy.deepcopy(rows[-1])),
                         lambda rows: rows.__setitem__(1, copy.deepcopy(rows[0])),
                         lambda rows: rows[0].__setitem__("radius_px", 10.0),
                         lambda rows: rows[3].__setitem__("selection_execution_role", "new_distinct"),
                         lambda rows: rows[6].__setitem__("confidence_threshold", True),
                         lambda rows: rows[6].__setitem__("arm", summary.ARMS[1])):
            with self.subTest(mutation=mutation):
                pool = copy.deepcopy(self.pools[0]); mutation(pool["loss_decomposition"]); seal(pool)
                with self.assertRaises(ValueError):
                    self.extract(pool)

    def test_non_target_memberships_are_not_interpreted(self):
        pool = copy.deepcopy(self.pools[0])
        pool["loss_decomposition"][0]["parts"] = "NOT_TARGET_MEMBERSHIPS"
        pool["loss_decomposition"][0].pop("hidden_alarm_frames")
        seal(pool)
        extracted = self.extract(pool)
        self.assertEqual(len(extracted["rows"]), 24)
        self.assertNotIn("NOT_TARGET", json.dumps(extracted))

    def test_strict_integer_sorted_unique_in_range_memberships_and_saved_total(self):
        for mutation in (lambda r, f: r["parts"][summary.PARTS[0]].append(f),
                         lambda r, f: r["parts"].__setitem__(summary.PARTS[0], [f + 1, f]),
                         lambda r, f: r["parts"].__setitem__(summary.PARTS[0], [f - 1]),
                         lambda r, f: r["parts"].__setitem__(summary.PARTS[0], [True]),
                         lambda r, f: r["parts"].__setitem__(summary.PARTS[0], [float(f)]),
                         lambda r, f: r.__setitem__("total_missed_eligible_frames", 100),
                         lambda r, f: r.__setitem__("total_missed_eligible_frames", True),
                         lambda r, f: r["parts"].pop(summary.PARTS[1]),
                         lambda r, f: r.pop("hidden_alarm_frames")):
            with self.subTest(mutation=mutation):
                pool = copy.deepcopy(self.pools[0]); row = pool["loss_decomposition"][6]
                mutation(row, row["parts"][summary.PARTS[0]][0]); seal(pool)
                with self.assertRaises(ValueError):
                    self.extract(pool)

    def test_disjoint_losses_hidden_separation_and_single_output_false_observations(self):
        for mutation in (lambda r, f: r["parts"].__setitem__(summary.PARTS[1], [f]),
                         lambda r, f: r.__setitem__("hidden_alarm_frames", [f]),
                         lambda r, f: r.__setitem__("false_observations_on_eligible_frames", [f + 4]),
                         lambda r, f: r.__setitem__("hidden_alarm_frames", list(r["false_observations_on_eligible_frames"]))):
            with self.subTest(mutation=mutation):
                pool = copy.deepcopy(self.pools[0]); row = pool["loss_decomposition"][6]
                mutation(row, row["parts"][summary.PARTS[0]][0]); seal(pool)
                with self.assertRaises(ValueError):
                    self.extract(pool)
        # Eligible false observations overlapping misses are preserved, not added.
        extracted = self.extract()
        self.assertEqual(extracted["rows"][0]["false_observations_on_eligible_frames"],
                         extracted["rows"][0]["parts"][summary.PARTS[3]])

    def test_published_digests_provenance_passed_audit_and_explicit_nulls(self):
        changed = copy.deepcopy(self.pools[0]); changed["purpose"] = summary.PURPOSES[1]
        with self.assertRaises(ValueError):
            self.extract(changed)
        for key, value in (("schema_version", "wrong"), ("code_commit", "0" * 40),
                           ("experiment_spec_sha256", "0" * 64), ("selected_method", "TT"),
                           ("semantic_training_labels_created", True), ("independent_trials_claimed", True)):
            pool = copy.deepcopy(self.pools[0]); pool[key] = value; seal(pool)
            with self.subTest(pool_field=key), self.assertRaises(ValueError):
                self.extract(pool)
        for key in summary.DECISIONS:
            pool = copy.deepcopy(self.pools[0]); pool.pop(key); seal(pool)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.extract(pool)
        for key, value in (("status", "failed"), ("execution_code_commit", "0" * 40),
                           ("original_evaluation_commit", "0" * 40), ("original_evaluation_spec_sha256", "0" * 64),
                           ("original_selection_commit", "0" * 40), ("original_selection_spec_sha256", "0" * 64)):
            audit = copy.deepcopy(self.audit); audit[key] = value; seal(audit)
            with self.subTest(audit_field=key), self.assertRaises(ValueError):
                summary.extract_pool(self.pools[0], audit)

    def test_combiner_refuses_missing_duplicate_changed_or_unapproved_payloads(self):
        pools = [self.extract(p) for p in self.pools]
        for values in (pools[:1], [pools[0], pools[0]]):
            with self.assertRaises(ValueError):
                summary.build_summary(values)
        for mutation in (lambda p: p.__setitem__("raw_payload", "FORBIDDEN"),
                         lambda p: p["rows"][0].__setitem__("raw_payload", "FORBIDDEN"),
                         lambda p: p["rows"][0]["membership_counts"].__setitem__(summary.PARTS[0], True),
                         lambda p: p["source_map"][0].__setitem__("json_pointer", "/unrelated"),
                         lambda p: p["rows"][0].__setitem__("window_identity_pointer", "/retention_measurements/1/window_id")):
            changed = copy.deepcopy(pools); mutation(changed[0]); seal(changed[0], "extraction_content_sha256")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                summary.build_summary(changed)
        changed = copy.deepcopy(pools); changed[0]["rows"][0]["total_missed_eligible_frames"] += 1
        with self.assertRaises(ValueError):
            summary.build_summary(changed)

    def test_pure_access_complete_display_and_bound_refuse_truncation(self):
        with mock.patch("builtins.open", side_effect=AssertionError("Filesystem access forbidden")), \
             mock.patch.object(Path, "open", side_effect=AssertionError("Filesystem access forbidden")):
            result, text = self.assembled()
        for token in ("RAW_MEASUREMENT_SENTINEL", "RAW_REPORT_SENTINEL", "forbidden/raw.json"):
            self.assertNotIn(token, json.dumps(result) + text)
        self.assertEqual(text.count("[saved row]"), 48)
        self.assertEqual(sum(len(p["rows"]) for p in result["pools"]), 48)
        pools = [self.extract(p) for p in self.pools]
        with mock.patch.object(summary, "MAX_TEXT_BYTES", len(text.encode("utf-8")) - 1):
            with self.assertRaisesRegex(ValueError, "no rows were truncated"):
                summary.build_summary(pools)


if __name__ == "__main__":
    unittest.main()

"""Fabricated-only coverage for the new within-row presence derivation."""
import copy
import json
from pathlib import Path
import unittest
from unittest import mock

from src.ball_tracking import crop_retention_error_breakdown_summary as prior
from src.ball_tracking import crop_retention_output_presence_summary as summary
from test_ball_crop_retention_error_breakdown_summary import fabricated_audit, fabricated_pool, seal


def fabricated_breakdown():
    """Create all 48 rows from artificial memberships, never repository data."""
    audit = fabricated_audit()
    extracted = []
    for purpose in prior.PURPOSES:
        pool = fabricated_pool(purpose)
        target_index = 0
        for row in pool["loss_decomposition"]:
            if row["radius_px"] != 10 or row["confidence_threshold"] != .01:
                continue
            first = row["parts"][prior.PARTS[0]][0]
            source = [first + 3, first + 4, first + 5]
            case = target_index % 4
            row["parts"][summary.S_PART] = [] if case == 0 else source
            row[summary.E_FIELD] = ([first] if case in (0, 1) else
                                   [first, *source] if case == 2 else [first, first + 4])
            row["total_missed_eligible_frames"] = sum(len(values) for values in row["parts"].values())
            target_index += 1
        seal(pool)
        extracted.append(prior.extract_pool(pool, audit))
    return prior.build_summary(extracted)[0]


def resolve(value, pointer):
    if not pointer:
        return value
    for token in pointer.lstrip("/").split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if type(value) is list else value[key]
    return value


def reseal_pool(value, pool_index=0):
    seal(value["pools"][pool_index], "extraction_content_sha256")


class OutputPresenceSummaryTests(unittest.TestCase):
    def setUp(self):
        self.breakdown = fabricated_breakdown()

    def test_empty_all_missing_all_present_and_mixed_are_row_local(self):
        result, _ = summary.build_summary(self.breakdown)
        for pool_index, pool in enumerate(self.breakdown["pools"]):
            for row_index, row in enumerate(pool["rows"]):
                pointer = f"/pools/{pool_index}/rows/{row_index}"
                derived = result["derived_by_row"][pointer]
                source, false = row["parts"][summary.S_PART], row[summary.E_FIELD]
                self.assertEqual(derived[summary.MISSING], [frame for frame in source if frame not in false])
                self.assertEqual(derived[summary.PRESENT], [frame for frame in source if frame in false])
                self.assertEqual(sum(derived["membership_counts"].values()), len(source))
                for name in (summary.MISSING, summary.PRESENT):
                    self.assertEqual(derived["membership_counts"][name], len(derived[name]))
                    self.assertNotIn(row["parts"][prior.PARTS[0]][0], derived[name])
                    self.assertTrue(set(derived[name]).isdisjoint(row["hidden_alarm_frames"]))
        values = list(result["derived_by_row"].values())
        self.assertEqual([tuple(v["membership_counts"].values()) for v in values[:4]],
                         [(0, 0), (3, 0), (0, 3), (2, 1)])

    def test_complete_inventory_identity_roles_and_overlapping_rows_preserved(self):
        result, text = summary.build_summary(self.breakdown)
        expected = [f"/pools/{p}/rows/{r}" for p in range(2) for r in range(24)]
        self.assertEqual(list(result["derived_by_row"]), expected)
        self.assertEqual(text.count("[saved row]"), 48)
        self.assertEqual(text.count("## Representative pool"), 1)
        self.assertEqual(text.count("## Challenge pool"), 1)
        self.assertIn("cap20 / saved", text)
        self.assertIn("all / new_distinct", text)
        self.assertIn("0: none", text)
        for p, pool in enumerate(self.breakdown["pools"]):
            for r, row in enumerate(pool["rows"]):
                self.assertIn(row["window_id"], text)
                self.assertIn(f"#/pools/{p}/rows/{r}", text)
        # Distinct arms/policies can contain the same frame without being joined.
        self.assertEqual(result["derived_by_row"]["/pools/0/rows/1"][summary.MISSING],
                         result["derived_by_row"]["/pools/0/rows/5"][summary.MISSING])
        self.assertEqual(len(result["derived_by_row"]), 48)

    def test_original_is_exact_and_copies_do_not_alias_input(self):
        before = copy.deepcopy(self.breakdown)
        result, _ = summary.build_summary(self.breakdown)
        self.assertEqual(self.breakdown, before)
        self.assertEqual(result["original_breakdown"], before)
        result["original_breakdown"]["pools"][0]["rows"][1]["parts"][summary.S_PART].append(9999)
        result["derived_by_row"]["/pools/0/rows/1"][summary.MISSING].append(8888)
        self.assertEqual(self.breakdown, before)
        self.assertNotIn(9999, result["derived_by_row"]["/pools/0/rows/1"][summary.MISSING])

    def test_every_new_list_and_count_has_both_inert_operands(self):
        result, _ = summary.build_summary(self.breakdown)
        self.assertEqual(len(result["source_map"]), 1 + 48 * 4)
        operations = set()
        for entry in result["source_map"]:
            operations.add(entry["operation"])
            if entry["operation"] == "copied":
                expected = resolve(self.breakdown, entry["json_pointer"])
            else:
                self.assertEqual(entry["operands"], [entry["row_pointer"] + "/parts/" + summary.S_PART,
                                                       entry["row_pointer"] + "/" + summary.E_FIELD])
                source, false = [resolve(self.breakdown, pointer) for pointer in entry["operands"]]
                operation = entry.get("membership_operation", entry["operation"])
                expected = [frame for frame in source if (frame in false) == (operation == "ordered_intersection")]
                if entry["operation"] == "list_length":
                    self.assertEqual(resolve(result, entry["derived_from"]), expected)
                    expected = len(expected)
            self.assertEqual(resolve(result, entry["output_pointer"]), expected)
        self.assertEqual(operations, {"copied", "ordered_difference", "ordered_intersection", "list_length"})

    def test_semantic_unknowns_decisions_and_limits_remain_explicit(self):
        result, text = summary.build_summary(self.breakdown)
        self.assertEqual(result["schema_version"], summary.SUMMARY_SCHEMA)
        self.assertTrue(result["new_membership_derivation"])
        for field in prior.DECISIONS:
            self.assertIsNone(result[field])
        for value in result["derived_by_row"].values():
            self.assertEqual(value["unresolved_evidence"], {field: None for field in summary.UNKNOWN_FIELDS})
        self.assertFalse(result["semantic_training_labels_created"])
        self.assertFalse(result["independent_trials_claimed"])
        self.assertFalse(result["new_scoring_selection_or_media"])
        self.assertIn("does not mean that the ball was absent", text)
        self.assertIn("not a wrong-object label", text)
        self.assertIn("separately authorized scope", text)
        self.assertNotIn("pool_totals", result)

    def test_missing_extra_or_modified_top_level_fields_are_rejected(self):
        mutations = (
            lambda value: value.pop("pools"),
            lambda value: value.__setitem__("schema_version", "wrong"),
            lambda value: value.__setitem__("unapproved", {}),
            lambda value: value.__setitem__("selected_method", "TT"),
            lambda value: value.pop("quality_gate"),
            lambda value: value.__setitem__("new_scientific_aggregation", 0),
            lambda value: value["checks"].__setitem__("complete_target_rows_preserved", 1),
            lambda value: value["limitations"].pop(),
            lambda value: value["unresolved_questions"].append("invented"),
            lambda value: value["source_map"][0].__setitem__("json_pointer", "/other"),
            lambda value: value.__setitem__("pools", tuple(value["pools"])),
        )
        for mutate in mutations:
            changed = copy.deepcopy(self.breakdown)
            mutate(changed)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                summary.build_summary(changed)

    def test_missing_duplicate_reordered_or_wrong_pools_and_rows_are_rejected(self):
        mutations = (
            lambda value: value["pools"].pop(),
            lambda value: value["pools"].reverse(),
            lambda value: value["pools"].__setitem__(1, copy.deepcopy(value["pools"][0])),
            lambda value: value["pools"][0]["rows"].pop(),
            lambda value: value["pools"][0]["rows"].__setitem__(1, copy.deepcopy(value["pools"][0]["rows"][0])),
            lambda value: value["pools"][0]["rows"].reverse(),
        )
        for mutate in mutations:
            changed = copy.deepcopy(self.breakdown)
            mutate(changed)
            if changed["pools"]:
                reseal_pool(changed)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                summary.build_summary(changed)

    def test_provenance_digest_role_and_source_map_tampering_are_rejected(self):
        mutations = (
            lambda pool: pool.__setitem__("scoring_commit", "0" * 40),
            lambda pool: pool.__setitem__("scoring_spec_sha256", "0" * 64),
            lambda pool: pool.__setitem__("audit_execution_commit", "0" * 40),
            lambda pool: pool.__setitem__("audit_content_sha256", "0" * 64),
            lambda pool: pool.__setitem__("source_content_sha256", "not-a-digest"),
            lambda pool: pool["rows"][0].__setitem__("selection_execution_role", "new_distinct"),
            lambda pool: pool["rows"][0].__setitem__("arm", "crop_raw"),
            lambda pool: pool["rows"][0].__setitem__("confidence_threshold", .20),
            lambda pool: pool["rows"][0].__setitem__("radius_px", 15),
            lambda pool: pool["rows"][0].__setitem__("source_row_pointer", "/loss_decomposition/0"),
            lambda pool: pool["source_map"][0].__setitem__("operation", "computed"),
        )
        for mutate in mutations:
            changed = copy.deepcopy(self.breakdown)
            mutate(changed["pools"][0])
            reseal_pool(changed)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                summary.build_summary(changed)
        changed = copy.deepcopy(self.breakdown)
        changed["pools"][0]["extraction_content_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            summary.build_summary(changed)

    def test_malformed_memberships_are_not_treated_as_empty(self):
        mutations = (
            lambda row: row["parts"].pop(summary.S_PART),
            lambda row: row.pop(summary.E_FIELD),
            lambda row: row.__setitem__(summary.E_FIELD, None),
            lambda row: row["parts"].__setitem__(summary.S_PART, [True]),
            lambda row: row["parts"][summary.S_PART].reverse(),
            lambda row: row["parts"][summary.S_PART].append(row["parts"][summary.S_PART][0]),
            lambda row: row["parts"][summary.S_PART].append(row["end_frame_index"] + 1),
            lambda row: row["membership_counts"].__setitem__(summary.S_PART, True),
            lambda row: row.__setitem__(summary.E_FIELD, [row["start_frame_index"] + 10]),
            lambda row: row.__setitem__("hidden_alarm_frames", list(row["parts"][summary.S_PART])),
            lambda row: row.__setitem__("start_frame_index", float(row["start_frame_index"])),
        )
        for mutate in mutations:
            changed = copy.deepcopy(self.breakdown)
            mutate(changed["pools"][0]["rows"][1])
            reseal_pool(changed)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                summary.build_summary(changed)

    def test_filesystem_access_is_forbidden_and_complete_text_is_bounded(self):
        with mock.patch("builtins.open", side_effect=AssertionError("Forbidden filesystem access")), \
             mock.patch.object(Path, "open", side_effect=AssertionError("Forbidden filesystem access")), \
             mock.patch.object(Path, "read_bytes", side_effect=AssertionError("Forbidden filesystem access")), \
             mock.patch.object(Path, "read_text", side_effect=AssertionError("Forbidden filesystem access")):
            result, text = summary.build_summary(self.breakdown)
        self.assertEqual(len(result["derived_by_row"]), 48)
        self.assertLessEqual(len(text.encode("utf-8")), summary.MAX_TEXT_BYTES)
        for token in ("RAW_MEASUREMENT_SENTINEL", "RAW_REPORT_SENTINEL", "forbidden/raw.json"):
            self.assertNotIn(token, json.dumps(result) + text)
        with mock.patch.object(summary, "MAX_TEXT_BYTES", len(text.encode("utf-8")) - 1):
            with self.assertRaisesRegex(ValueError, "no rows were truncated"):
                summary.build_summary(self.breakdown)


if __name__ == "__main__":
    unittest.main()

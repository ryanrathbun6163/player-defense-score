"""Invented guide/audit pairs exercise interpretation without scientific I/O."""
import builtins
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_retention_interpretation_summary as summary


def seal(audit):
    audit["content_sha256"] = hashlib.sha256(json.dumps(
        {k: v for k, v in audit.items() if k != "content_sha256"},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def fabricated_audit():
    """Independent invented counts include recoveries and regressions in both pools."""
    audit = {"schema_version": "ball_crop_retention_independent_publication_recovery_audit/v0.1",
             "status": "passed", "execution_code_commit": "synthetic_commit", "experiment_spec_sha256": "synthetic_spec",
             "human_visual_review": "pending_six_new_floor_clips_only", "prior_reviews": "complete_no_repeat",
             "selected_method": None, "selected_operating_point": None, "quality_gate": None,
             "pool_audits": [], "review_audits": [],
             "resource_audit": {"prior_active_seconds": 101.25, "remaining_seconds_before_current_audit": 14298.75},
             "untrusted_deeper_pointer": {"path": "/must/never/open/raw-science.json", "candidate_payload": [999]}}
    for pi, purpose in enumerate(summary.PURPOSES):
        windows = [w for w in summary.WINDOWS if w["purpose"] == purpose]
        denominators = {"eligible_frame_count": 75 - 5*pi, "not_visible_frame_count": 5*pi, "unscored_frame_count": 0}
        cells = []
        for ai, arm in enumerate(summary.ARMS):
            change = (2, -1, 0, 1)[ai]
            old_tp = 40 + ai + pi
            new_tp = old_tp + change
            before = {**denominators, "true_positive_count": old_tp, "false_positive_count": 60-old_tp,
                      "false_negative_count": denominators["eligible_frame_count"]-old_tp,
                      "non_visible_false_alarm_count": 2*pi, "duplicate_false_positive_count": 0,
                      "non_visible_false_alarm_frame_count": 2*pi}
            after = {**denominators, "true_positive_count": new_tp, "false_positive_count": 63-new_tp,
                     "false_negative_count": denominators["eligible_frame_count"]-new_tp,
                     "non_visible_false_alarm_count": 3*pi, "duplicate_false_positive_count": 0,
                     "non_visible_false_alarm_frame_count": 3*pi}
            def frames(offsets):
                window = windows[0]
                return [{"window_id": window["window_id"], "possession_id": window["possession_id"],
                         "frame_index": window["start_frame_index"]+offset} for offset in offsets]
            gains = frames(range(max(change, 0)+1))
            losses = frames(range(10, 10+max(-change, 0)+1))
            for radius in summary.RADII:
                cells.append({"arm": arm, "confidence_threshold": .01, "radius_px": radius,
                              "semantic_identity_judgments": False,
                              "saved_cap20": copy.deepcopy(before), "new_all": copy.deepcopy(after),
                              "metric_deltas": {key: after[key]-before[key] for key in before},
                              "gained_match_frames": copy.deepcopy(gains), "lost_match_frames": copy.deepcopy(losses)})
        missing = [{"window_id": w["window_id"], "possession_id": w["possession_id"], "purpose": purpose,
                    "arm": arm, "confidence_threshold": .01, "radius_px": 10.,
                    "saved_cap20": {"frame_count": 25, "emitted_frame_count": 20, "missing_frame_count": 5, "emitted_frame_coverage": .8},
                    "new_all": {"frame_count": 25, "emitted_frame_count": 21, "missing_frame_count": 4, "emitted_frame_coverage": .84}}
                   for w in windows for arm in summary.ARMS]
        audit["pool_audits"].append({"purpose": purpose, "fixed_floor_radius10_descriptive_cells": copy.deepcopy([c for c in cells if c["radius_px"] == 10]),
                                     "all_radius_cap_deltas": cells, "fixed_floor_radius10_missingness_by_window": missing})
    audit["review_audits"] = [{"window_id": w["window_id"], "final_source_frame": w["end_frame_index"],
                               "human_visual_review": "pending", "independent_new_clip_decode": {"decoded_frames": 25}}
                              for w in summary.WINDOWS]
    seal(audit)
    return audit


def fabricated_guide(audit):
    """Published table format, independently populated from invented records."""
    lines = ["# Synthetic guide",
             "The unchanged motion scorer can retain every saved candidate at confidence .01 instead of the first twenty.",
             "Each clip contains 25 frames shown at 5 fps.",
             "left is the saved twenty-candidate cap and middle is all candidates",
             "same .01 confidence and 10-pixel localization radius",
             "Matches are true positives; false observations are false positives; missed eligible frames are false negatives.",
             "TT/TW/WT/WW refer to the frozen tight/wide edge and cost settings; none is selected as a winner.",
             "Missing observations (NULL) differ from missed eligible frames (false negatives)",
             "Higher-confidence .20/.35 equivalence references reuse existing results and are not extra trials.",
             "## Review the six clips", "| Window | Source frames | Clip | Final comparison | Final closeup |"]
    for w in summary.WINDOWS:
        lines.append(f"| {w['possession_id']} {w['purpose'].replace('_evaluation', '')} | {w['start_frame_index']}–{w['end_frame_index']} | "
                     f"[Clip](</inert/comparison_slow.mp4>) | [Final](</inert/comparison/frame_{w['end_frame_index']:06d}.png>) | "
                     f"[Closeup](</inert/closeups/frame_{w['end_frame_index']:06d}.png>) |")
    lines.append("## Audited descriptive results")
    for pool in audit["pool_audits"]:
        lines.append("### " + ("Representative pool" if pool["purpose"] == summary.PURPOSES[0] else "Challenge pool"))
        d = pool["fixed_floor_radius10_descriptive_cells"][0]["saved_cap20"]
        lines.append(f"Audited common denominators: {d['eligible_frame_count']} localization-eligible frames, {d['not_visible_frame_count']} reviewed hidden frames, and {d['unscored_frame_count']} unscored frames.")
        lines.append("| Setting | Matches cap20 → all | False observations cap20 → all | Missed eligible cap20 → all | Hidden alarms cap20 → all |")
        for cell in pool["fixed_floor_radius10_descriptive_cells"]:
            name = summary.ARM_NAMES[cell["arm"]]
            lines.append("| " + " | ".join([name, *(f"{cell['saved_cap20'][k]} → {cell['new_all'][k]}" for k in summary.GUIDE_METRICS)]) + " |")
        for cell in pool["fixed_floor_radius10_descriptive_cells"]:
            def frame_text(rows):
                return "; ".join(f"{r['possession_id']} frame {r['frame_index']}" for r in rows) or "None"
            lines.append(f"**{summary.ARM_NAMES[cell['arm']]} gained localization matches:** {frame_text(cell['gained_match_frames'])}. **Lost localization matches:** {frame_text(cell['lost_match_frames'])}.")
        lines.append("| Window | Setting | Missing observations cap20 → all | Emitted observations cap20 → all | Frames |")
        for row in pool["fixed_floor_radius10_missingness_by_window"]:
            window = next(w for w in summary.WINDOWS if w["window_id"] == row["window_id"])
            old, new = row["saved_cap20"], row["new_all"]
            lines.append(f"| {window['possession_id']} {window['start_frame_index']}–{window['end_frame_index']} | {summary.ARM_NAMES[row['arm']]} | {old['missing_frame_count']} → {new['missing_frame_count']} | {old['emitted_frame_count']} → {new['emitted_frame_count']} | {old['frame_count']} |")
    lines.extend(["## All audited radius comparisons", "These copied deltas are all-candidate minus cap20 at .01.",
                  "| Pool | Setting | Radius px | Match delta | False-observation delta | Missed-eligible delta | Hidden-alarm delta |"])
    for pool in audit["pool_audits"]:
        for cell in pool["all_radius_cap_deltas"]:
            lines.append("| " + " | ".join([pool["purpose"].replace("_evaluation", ""), summary.ARM_NAMES[cell["arm"]], str(cell["radius_px"]),
                *(str(cell["metric_deltas"][k]) for k in summary.GUIDE_METRICS)]) + " |")
    lines.extend(["## Provenance", "```json", json.dumps({"execution_commit": audit["execution_code_commit"],
                  "spec_sha256": audit["experiment_spec_sha256"], "scientific_scores_recomputed": False}), "```", ""])
    return "\n".join(lines)


def pointer(value, path):
    for segment in path.lstrip("/").split("/"):
        value = value[int(segment)] if isinstance(value, list) else value[segment]
    return value


class InterpretationSummaryTests(unittest.TestCase):
    def test_all_pools_families_radii_and_window_rows_are_preserved(self):
        audit = fabricated_audit()
        saved = copy.deepcopy(audit)
        result, memo = summary.build_summary(fabricated_guide(audit), audit)
        self.assertEqual(audit, saved)
        self.assertEqual([p["purpose"] for p in result["pools"]], list(summary.PURPOSES))
        for pool in result["pools"]:
            self.assertEqual(len(pool["fixed_floor_radius10_descriptive_cells"]), 4)
            self.assertEqual(len(pool["all_radius_cap_deltas"]), 20)
            self.assertEqual(len(pool["fixed_floor_radius10_missingness_by_window"]), 12)
        self.assertLessEqual(len(memo.encode()), 65536)
        for name in ("selected_method", "selected_operating_point", "quality_gate"):
            self.assertIsNone(result[name])
        self.assertFalse(result["new_scientific_aggregation"])
        self.assertFalse(result["new_experiment_authorized"])
        self.assertIn("frame-level regressions present", memo)
        self.assertIn("Frame-level recoveries present", memo)
        self.assertIn("localized matches decreased", memo)
        self.assertIn("false observations increased", memo)
        self.assertIn("not newly executed uncapped trials", memo)
        self.assertIn("No clip review is requested again", memo)

    def test_every_copied_value_has_an_exact_inert_source_pointer(self):
        audit = fabricated_audit()
        result, _ = summary.build_summary(fabricated_guide(audit), audit)
        self.assertEqual(len({row["output_pointer"] for row in result["source_map"]}), len(result["source_map"]))
        for row in result["source_map"]:
            with self.subTest(pointer=row["output_pointer"]):
                self.assertEqual(row["input"], "audit")
                expected = pointer(audit, row["json_pointer"])
                self.assertEqual(pointer(result, row["output_pointer"]), bool(expected) if row["status"] == "qualitative_presence" else expected)

    def test_pure_builder_never_opens_files_or_copies_raw_payloads(self):
        audit = fabricated_audit()
        guide = fabricated_guide(audit)
        with patch.object(builtins, "open", side_effect=AssertionError("forbidden I/O")), \
             patch.object(Path, "read_text", side_effect=AssertionError("forbidden text")), \
             patch.object(Path, "read_bytes", side_effect=AssertionError("forbidden bytes")):
            result, memo = summary.build_summary(guide, audit)
        serialized = json.dumps(result)
        self.assertNotIn("must/never/open", serialized + memo)
        self.assertNotIn("candidate_payload", serialized)
        self.assertNotIn('"frame_index"', serialized)
        self.assertNotIn('"gained_match_frames":', serialized)
        self.assertNotIn('"lost_match_frames":', serialized)

    def test_optional_absence_is_unavailable_not_zero(self):
        audit = fabricated_audit()
        audit.pop("resource_audit")
        for pool in audit["pool_audits"]:
            for field in ("fixed_floor_radius10_descriptive_cells", "all_radius_cap_deltas"):
                for cell in pool[field]:
                    for policy in ("saved_cap20", "new_all", "metric_deltas"):
                        cell[policy].pop("duplicate_false_positive_count")
        seal(audit)
        result, memo = summary.build_summary(fabricated_guide(audit), audit)
        unavailable = {"status": "unavailable"}
        self.assertEqual(result["resource_context"]["prior_active_seconds"], unavailable)
        self.assertEqual(result["pools"][0]["fixed_floor_radius10_descriptive_cells"][0]["new_all"]["duplicate_false_positive_count"], unavailable)
        self.assertIn("unavailable", memo)

    def test_guide_cannot_claim_a_missing_required_count(self):
        audit = fabricated_audit()
        guide = fabricated_guide(audit)
        del audit["pool_audits"][0]["fixed_floor_radius10_descriptive_cells"][0]["new_all"]["true_positive_count"]
        seal(audit)
        with self.assertRaises(ValueError):
            summary.build_summary(guide, audit)

    def test_favorable_unfavorable_denominator_missingness_and_radius_mismatches_fail(self):
        audit = fabricated_audit()
        guide = fabricated_guide(audit)
        variants = (guide.replace("40 → 42", "40 → 99", 1),
                    guide.replace("**Lost localization matches:** possession_001 frame 60", "**Lost localization matches:** None", 1),
                    guide.replace("75 localization-eligible", "74 localization-eligible", 1),
                    guide.replace("| 5 → 4 | 20 → 21 | 25 |", "| 5 → 0 | 20 → 25 | 25 |", 1),
                    guide.replace("| representative | TT | 5.0 | 2 |", "| representative | TT | 5.0 | 9 |", 1),
                    guide.replace("frame_000174.png", "frame_000173.png"))
        for guide_variant in variants:
            self.assertNotEqual(guide_variant, guide)
            with self.subTest(variant=guide_variant[-80:]), self.assertRaises(ValueError):
                summary.build_summary(guide_variant, audit)

    def test_missing_family_window_pool_final_frame_or_method_selection_fails(self):
        baseline = fabricated_audit()
        guide = fabricated_guide(baseline)
        variants = []
        for field in ("fixed_floor_radius10_descriptive_cells", "all_radius_cap_deltas", "fixed_floor_radius10_missingness_by_window"):
            value = copy.deepcopy(baseline)
            value["pool_audits"][0][field].pop()
            variants.append(value)
        value = copy.deepcopy(baseline)
        value["pool_audits"][1]["purpose"] = summary.PURPOSES[0]
        variants.append(value)
        value = copy.deepcopy(baseline)
        value["review_audits"][-1]["final_source_frame"] -= 1
        variants.append(value)
        value = copy.deepcopy(baseline)
        value["selected_method"] = "synthetic winner"
        variants.append(value)
        value = copy.deepcopy(baseline)
        value["pool_audits"][0]["fixed_floor_radius10_descriptive_cells"][0]["new_all"]["true_positive_count"] += 1
        variants.append(value)
        for index, value in enumerate(variants):
            seal(value)
            with self.subTest(index=index), self.assertRaises(ValueError):
                summary.build_summary(guide, value)

    def test_invalid_hash_boolean_count_or_nonfinite_count_fails(self):
        for value in (True, float("inf"), -1):
            audit = fabricated_audit()
            guide = fabricated_guide(audit)
            audit["pool_audits"][0]["fixed_floor_radius10_descriptive_cells"][0]["new_all"]["true_positive_count"] = value
            if value != float("inf"):
                seal(audit)
            with self.subTest(value=value), self.assertRaises(ValueError):
                summary.build_summary(guide, audit)
        audit = fabricated_audit()
        audit["status"] = "failed"
        with self.assertRaises(ValueError):
            summary.build_summary(fabricated_guide(audit), audit)

    def test_utf8_limits_reject_oversize_and_never_truncate_rows(self):
        audit = fabricated_audit()
        guide = fabricated_guide(audit)
        with self.assertRaisesRegex(ValueError, "64 KiB"):
            summary.build_summary(guide + "é" * 32768, audit)
        _, memo = summary.build_summary(guide, audit)
        self.assertGreater(len(memo.encode()), len(guide.encode()))
        with patch.object(summary, "MAX_TEXT_BYTES", len(memo.encode())-1), self.assertRaisesRegex(ValueError, "no rows were truncated"):
            summary.build_summary(guide, audit)


if __name__ == "__main__":
    unittest.main()

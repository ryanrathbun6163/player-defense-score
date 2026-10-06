"""Pure within-row output-presence derivation from one supplied breakdown.

No paths are opened or followed. The original breakdown stays intact; the only
new memberships are its S list filtered by its eligible false-observation list.
"""
from __future__ import annotations

import copy
import json

from . import crop_retention_error_breakdown_summary as breakdown_summary


SUMMARY_SCHEMA = "ball_crop_retention_output_presence/v0.1"
MAX_TEXT_BYTES = 65_536
INPUT_SCHEMA = breakdown_summary.SUMMARY_SCHEMA
S_PART = "S_path_choice_loss"
E_FIELD = "false_observations_on_eligible_frames"
MISSING = "missing_current_output"
PRESENT = "present_nonmatching_current_output"
INPUT_REFERENCE = "../post_review_error_breakdown_recovery_v0_1/breakdown.json"
UNKNOWN_FIELDS = (
    "emitted_candidate_index", "emitted_center_xy_px", "raw_center_error_px",
    "missing_output_reason", "wrong_object_verdict", "ball_center_placement_verdict",
    "causal_explanation",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json_value(value):
    """Reject non-JSON objects before comparing the complete supplied schema."""
    if type(value) is dict:
        _require(all(type(key) is str for key in value), "JSON object keys must be strings")
        for child in value.values():
            _json_value(child)
    elif type(value) is list:
        for child in value:
            _json_value(child)
    else:
        _require(value is None or type(value) in (str, int, float, bool),
                 "The supplied breakdown must contain only JSON values")


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _validate_input(value):
    _require(type(value) is dict and value.get("schema_version") == INPUT_SCHEMA,
             "The exact completed breakdown schema is required")
    _json_value(value)
    # This pure formatter revalidates extraction digests, source maps, all 48
    # rows and provenance using supplied objects only. It does not load pools.
    expected, _ = breakdown_summary.build_summary(value["pools"])
    _require(_canonical(value) == _canonical(expected),
             "The complete breakdown structure, source map, limits or decisions changed")
    for pool in value["pools"]:
        for row in pool["rows"]:
            _require(all(type(row[key]) is int for key in ("start_frame_index", "end_frame_index")),
                     "Saved source-frame bounds must be integers")
    return value


def _token(value):
    return value.replace("~", "~0").replace("/", "~1")


def _entry(output_pointer, row_pointer, operation, *, derived_from=None, membership_operation=None):
    value = {
        "output_pointer": output_pointer, "input": "breakdown", "row_pointer": row_pointer,
        "operands": [row_pointer + "/parts/" + S_PART, row_pointer + "/" + E_FIELD],
        "operation": operation,
    }
    if derived_from is not None:
        value.update(derived_from=derived_from, membership_operation=membership_operation)
    return value


def _derive(row, pointer):
    source = row["parts"][S_PART]
    eligible_false = row[E_FIELD]
    missing = [frame for frame in source if frame not in eligible_false]
    present = [frame for frame in source if frame in eligible_false]
    # Preserve order and each membership's row identity; never combine rows.
    _require(len(missing) + len(present) == row["membership_counts"][S_PART]
             and all((frame in missing) != (frame in present) for frame in source),
             "Output-presence memberships do not reconcile with the saved S row")
    derived = {MISSING: missing, PRESENT: present,
               "membership_counts": {MISSING: len(missing), PRESENT: len(present)},
               "unresolved_evidence": {field: None for field in UNKNOWN_FIELDS}}
    sources = []
    base = "/derived_by_row/" + _token(pointer)
    for name, operation in ((MISSING, "ordered_difference"), (PRESENT, "ordered_intersection")):
        membership_pointer = base + "/" + name
        sources.append(_entry(membership_pointer, pointer, operation))
        sources.append(_entry(base + "/membership_counts/" + name, pointer, "list_length",
                              derived_from=membership_pointer, membership_operation=operation))
    return derived, sources


def _members(derived, name):
    values = derived[name]
    return str(derived["membership_counts"][name]) + ": " + (", ".join(map(str, values)) if values else "none")


def build_summary(breakdown: dict) -> tuple[dict, str]:
    """Validate and split the complete saved S inventory without external IO."""
    try:
        _validate_input(breakdown)
        original = copy.deepcopy(breakdown)
        derived_by_row, source_map = {}, [{"output_pointer": "/original_breakdown", "input": "breakdown",
                                           "json_pointer": "", "operation": "copied"}]
        text = ["# Saved path-choice losses: current output presence", "",
                "Each row splits its existing S_path_choice_loss memberships at confidence .01 and a raw radius of 10 source-image pixels. Counts are lengths of those row-specific lists, not new detector performance or independent trials.", "",
                "- **Missing current output:** no current observation was emitted. This does not mean that the ball was absent from the pixels.",
                "- **Present nonmatching current output:** one original candidate was emitted and failed the existing localization rule. This is not a wrong-object label.", "",
                "Each list cell gives **membership count: saved source-frame indices**. Empty lists remain visible. Both pools and the original execution roles stay separate.", ""]
        for pool_index, pool in enumerate(original["pools"]):
            text += ["## " + pool["purpose"].replace("_evaluation", "").capitalize() + " pool", ""]
            last_window = None
            for row_index, row in enumerate(pool["rows"]):
                pointer = f"/pools/{pool_index}/rows/{row_index}"
                derived, sources = _derive(row, pointer)
                _require(pointer not in derived_by_row, "Duplicate output-presence row")
                derived_by_row[pointer] = derived
                source_map.extend(sources)
                if row["window_id"] != last_window:
                    last_window = row["window_id"]
                    text += ["### " + last_window, "",
                             f"{row['possession_id']}; source frames {row['start_frame_index']}–{row['end_frame_index']}; confidence .01; raw radius 10 pixels.", "",
                             "| Setting | Policy / original execution role | Original S count | Missing current output | Present nonmatching current output | Source row |",
                             "| --- | --- | --- | --- | --- | --- |"]
                text.append("| " + " | ".join([
                    breakdown_summary.ARM_NAMES[row["arm"]],
                    row["retention_policy"] + " / " + row["selection_execution_role"],
                    str(row["membership_counts"][S_PART]), _members(derived, MISSING), _members(derived, PRESENT),
                    "[saved row](" + INPUT_REFERENCE + "#" + pointer + ")"]) + " |")
                if (row_index + 1) % 8 == 0:
                    text.append("")
        _require(len(derived_by_row) == 48, "All 48 original rows must be preserved")
        limitations = [
            "Only within-row ordered difference/intersection and resulting list lengths are new. No pool totals, rates, rankings, cross-row unions or significance tests are created.",
            "Eligible false observations outside S and hidden alarms remain unchanged in the original breakdown and are not folded into either new category.",
            "No emitted candidate identity, coordinates, out-of-radius error magnitude, missing-output reason or causal explanation is available from this input. These remain unknown.",
            "Wrong-object output versus inaccurate ball-center placement remains unresolved. Localization outcomes do not create semantic identity or training labels.",
            "All completed clip reviews, embargoes and sealed holdouts remain unchanged. Any new frame-specific semantic adjudication needs a separately authorized scope.",
            "No inference, scoring, selection, media rendering, threshold choice, method choice, operating point or quality gate is created.",
        ]
        text += ["## Limits", "", *("- " + line for line in limitations), ""]
        markdown = "\n".join(text)
        _require(0 < len(markdown.encode("utf-8")) <= MAX_TEXT_BYTES,
                 "Complete readable output-presence summary exceeds 64 KiB; no rows were truncated")
        result = {
            "schema_version": SUMMARY_SCHEMA, "original_breakdown": original,
            "derived_by_row": derived_by_row, "source_map": source_map,
            "source_contract": {"input_schema_version": INPUT_SCHEMA,
                                "original_scoring_commit": breakdown_summary.SCORING_COMMIT,
                                "original_scoring_spec_sha256": breakdown_summary.SCORING_SPEC,
                                "confidence_threshold": .01, "localization_radius_px": 10.0,
                                "emission_rule": "zero or one current original threshold-qualified candidate",
                                "matching_rule": "raw center distance; uncertainty diagnostic only"},
            "new_membership_derivation": True,
            "membership_count_basis": "Length of each derived list within its original saved row only",
            "selected_method": None, "selected_operating_point": None, "quality_gate": None,
            "semantic_training_labels_created": False, "independent_trials_claimed": False,
            "new_scoring_selection_or_media": False, "limitations": limitations,
            "checks": {"complete_input_structure_validated": True, "original_breakdown_preserved": True,
                       "all_48_rows_preserved": True, "within_row_memberships_reconciled": True,
                       "source_pointers_followed": False},
        }
        return result, markdown
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError("Missing or unsupported saved output-presence relationship") from error

"""Pure postselection scoring and immutable saved-control comparisons.

The guarded worker supplies values only after sealing every new selection.
This module has no file access and never reselects or rescores saved controls.
Box support and raw-center proximity are not semantic identity judgments.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import math

from . import crop_cross_detector_corroboration as selector
from .crop_path_confidence_mean_evaluation import (
    HIDDEN_STATES, POOLS, STATES, frame_state, state_summary,
    temporal_metrics, transitions,
)
from .development_experiments import canonical_sha256, require_digest
from .evaluation import evaluate_detections
from .tiled_evaluation import METRICS

ARM = "rfdetr_yolo_box_corroborated_top_one"
TOP = "crop_top_one"
TT = "history_edge_tight_cost_tight"
MEAN = "history_mean_edge_tight_cost_tight"
CONTROLS = (TOP, TT, MEAN)
ARMS = (*CONTROLS, ARM)
CONFIG = dict(arm=ARM, confidence_threshold=.01, iou_threshold=.5)
RADIUS = 10.0
SCHEMA = "ball_crop_cross_detector_corroboration_evaluation/v0.1"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _control_config(arm):
    _require(arm in CONTROLS, "Unknown saved control")
    return dict(arm=arm, confidence_threshold=.01,
                candidate_cap=None if arm == TOP else 20,
                edge_step=None if arm == TOP else .01,
                cost_step=None if arm == TOP else .01)


def _selected_frames(run, observations):
    """Check original references only, without rederiving any selection."""
    _require(observations["input_candidate_content_sha256"] == canonical_sha256(run.to_dict()),
             "Observation RF candidate namespace differs")
    _require(observations["source_video"] == run.source_video.to_dict()
             and observations["window"] == run.window.to_dict()
             and observations["possession_id"] == run.possession_id,
             "Observation source/window differs")
    _require([row["frame_index"] for row in observations["frames"]]
             == [frame.frame_index for frame in run.frames], "Observation frame alignment differs")
    selected = []
    for frame, row in zip(run.frames, observations["frames"]):
        emitted = row["emitted_candidate_indices"]
        candidates = {candidate.candidate_index: candidate for candidate in frame.detections}
        _require(isinstance(emitted, list) and len(emitted) <= 1
                 and all(type(index) is int and index in candidates
                         and candidates[index].confidence >= .01 for index in emitted),
                 "Expected zero or one original floor-qualified emission")
        selected.append(replace(frame, detections=tuple(candidates[index] for index in emitted)))
    return tuple(selected)


def candidate_availability(labels, rf_run, observations):
    """Label-assisted diagnostic: call only after the new selections are sealed."""
    annotation_by_frame = labels.annotation_by_frame()
    rows = []
    for frame, observation in zip(rf_run.frames, observations["frames"]):
        label = annotation_by_frame[frame.frame_index]
        eligible = label.localization_eligible
        original = []
        if eligible:
            original = [candidate.candidate_index for candidate in frame.detections
                        if candidate.confidence >= .01
                        and math.dist(candidate.center_xy_px, label.geometry.center_xy_px) <= RADIUS]
        supported = set(observation["supported_candidate_indices"])
        corroborated = [index for index in original if index in supported]
        rows.append({"frame_index": frame.frame_index, "localization_eligible": eligible,
                     "original_rf_raw10_candidate_indices": original if eligible else None,
                     "corroborated_raw10_candidate_indices": corroborated if eligible else None,
                     "original_rf_raw10_available": bool(original) if eligible else None,
                     "corroborated_raw10_available": bool(corroborated) if eligible else None})
    result = {"eligible_denominator": sum(row["localization_eligible"] for row in rows),
              "frame_results": rows, "postselection_only": True,
              "label_assisted_localization_diagnostic": True,
              "semantic_identity_established": False}
    for name, key in (("original_rf", "original_rf_raw10_available"),
                      ("corroborated", "corroborated_raw10_available")):
        frames = [row["frame_index"] for row in rows if row[key] is True]
        result[name] = {"count": len(frames), "frame_indices": frames}
    return result


def evaluate_selection(labels, rf_run, observations, commit, *, yolo_run):
    """Score only the fixed new arm with the unchanged .01/raw10 evaluator."""
    require_digest(commit, "corroboration evaluator commit", 40)
    _require(observations["config"] == CONFIG, "Only the fixed new corroboration arm may be evaluated")
    selector.validate_observations(observations, rf_run, yolo_run)
    selected = _selected_frames(rf_run, observations)
    score = evaluate_detections(labels, replace(rf_run, frames=selected),
                                confidence_threshold=.01, localization_radius_px=RADIUS)
    report = {
        "schema_version": SCHEMA, "variant_id": observations["variant_id"],
        "config": deepcopy(CONFIG), "localization_radius_px": RADIUS,
        "selection_purpose": labels.window.selection_purpose,
        "possession_id": rf_run.possession_id, "source_video": rf_run.source_video.to_dict(),
        "window": rf_run.window.to_dict(), "input_model_provenance": rf_run.model_provenance.to_dict(),
        "input_bindings": deepcopy(observations["input_bindings"]),
        "ranking_code_commit": observations["ranking_code_commit"], "evaluator_code_commit": commit,
        "observations_content_sha256": canonical_sha256(observations),
        "input_candidate_content_sha256": observations["input_candidate_content_sha256"],
        "annotation_content_sha256": score["annotation_content_sha256"],
        "matching_rule": "raw center distance; uncertainty diagnostic only",
        "metrics": {key: score[key] for key in METRICS}, "frame_results": score["frame_results"],
        "execution_role": "new_distinct_evaluation", "selected_operating_point": None,
        "quality_gate": None, "semantic_identity_labels_created": False,
        "absence_is_hidden_label": False,
    }
    report["state_summary"] = state_summary(report)
    report["temporal_metrics"] = temporal_metrics(report)
    report["candidate_availability"] = candidate_availability(labels, rf_run, observations)
    return report


def verify_saved_observations(wrapper, reference, rf_run):
    """Copy bound controls, ignoring legacy winner/path assumptions entirely."""
    _require(isinstance(wrapper, dict) and isinstance(wrapper.get("observations"), dict),
             "Expected saved observations wrapper")
    value = wrapper["observations"]
    _require(value["config"] == reference["config"] == _control_config(value["config"]["arm"])
             and value["variant_id"] == reference["variant_id"], "Saved control configuration differs")
    _require(canonical_sha256(value) == reference["observations_content_sha256"]
             and value["input_candidate_content_sha256"] == reference["input_candidate_content_sha256"]
             and value["ranking_code_commit"] == reference["original_selection_commit"]
             and value["detector_code_commit"] == reference["original_detector_commit"]
             and len(value["frames"]) == reference["frame_count"],
             "Saved observation content/provenance differs")
    _selected_frames(rf_run, value)
    return deepcopy(value)


def _bind_report_observations(report, observations):
    _require(report["config"] == observations["config"]
             and report["variant_id"] == observations["variant_id"]
             and report["observations_content_sha256"] == canonical_sha256(observations)
             and report["input_candidate_content_sha256"] == observations["input_candidate_content_sha256"]
             and report["ranking_code_commit"] == observations["ranking_code_commit"]
             and all(report[key] == observations[key] for key in ("source_video", "window", "possession_id")),
             "Report observation content/provenance differs")
    _require([row["frame_index"] for row in report["frame_results"]]
             == [row["frame_index"] for row in observations["frames"]], "Report observation alignment differs")
    for result, observation in zip(report["frame_results"], observations["frames"]):
        emitted = observation["emitted_candidate_indices"]
        matched = result["matched_candidate_index"]
        _require(isinstance(emitted, list) and len(emitted) <= 1
                 and all(type(index) is int and index >= 0 for index in emitted)
                 and result["accepted_detection_count"] == len(emitted)
                 and (matched is None or (type(matched) is int and matched >= 0 and matched in emitted)),
                 "Saved result and emitted candidate differ")
        if frame_state(result) == "matched":
            error = result["matched_center_error_px"]
            _require(type(error) in (int, float) and math.isfinite(error) and 0 <= error <= RADIUS,
                     "Invalid matched original center error")
    state_summary(report)


def verify_saved_report(report, reference, observations, rf_run, labels):
    """Verify a saved .01/raw10 report without invoking an evaluator or selector."""
    _require(report["config"] == reference["config"] == _control_config(report["config"]["arm"])
             and report["localization_radius_px"] == reference["localization_radius_px"] == RADIUS,
             "Saved report settings differ")
    _require(canonical_sha256(report) == reference["report_content_sha256"], "Saved report content differs")
    _require(report["observations_content_sha256"] == reference["observations_content_sha256"]
             and report["input_candidate_content_sha256"] == canonical_sha256(rf_run.to_dict())
             and report["annotation_content_sha256"] == canonical_sha256(labels.to_dict())
             and report["ranking_code_commit"] == reference["original_selection_commit"]
             and report["evaluator_code_commit"] == reference["original_evaluation_commit"],
             "Saved report provenance differs")
    _require(report["source_video"] == rf_run.source_video.to_dict()
             and report["window"] == rf_run.window.to_dict() and report["possession_id"] == rf_run.possession_id
             and report["input_model_provenance"] == rf_run.model_provenance.to_dict()
             and report["selection_purpose"] == reference["purpose"] == labels.window.selection_purpose,
             "Saved report identity differs")
    _selected_frames(rf_run, observations)
    _bind_report_observations(report, observations)
    return deepcopy(report)


def _paired_errors(before, after):
    result = []
    for old, new in zip(before["frame_results"], after["frame_results"]):
        if frame_state(old) == frame_state(new) == "matched":
            result.append({"frame_index": old["frame_index"],
                           "old_error_px": old["matched_center_error_px"],
                           "new_error_px": new["matched_center_error_px"],
                           "difference_px": new["matched_center_error_px"] - old["matched_center_error_px"],
                           "old_candidate_index": old["matched_candidate_index"],
                           "new_candidate_index": new["matched_candidate_index"],
                           "candidate_choice": "same" if old["matched_candidate_index"] == new["matched_candidate_index"] else "replaced"})
    return result


def _choice_changes(old_observations, new_observations, old_report, new_report):
    groups = {key: [] for key in ("retained", "suppressed", "replaced", "both_missing")}
    rows = []
    for old, new, old_result, new_result in zip(old_observations["frames"], new_observations["frames"],
                                               old_report["frame_results"], new_report["frame_results"]):
        before, after = old["emitted_candidate_indices"], new["emitted_candidate_indices"]
        _require(before or not after, "Corroboration cannot add output where the same-floor top-one has no candidate")
        choice = "both_missing" if not before else "suppressed" if not after else "retained" if before == after else "replaced"
        groups[choice].append(old["frame_index"])
        rows.append({"frame_index": old["frame_index"], "choice": choice,
                     "old_candidate_index": before[0] if before else None,
                     "new_candidate_index": after[0] if after else None,
                     "old_state": frame_state(old_result), "new_state": frame_state(new_result)})
    return {"counts": {key: len(frames) for key, frames in groups.items()}, "frame_indices": groups,
            "frame_results": rows,
            "wrong_replacement_frames": [row["frame_index"] for row in rows
                                          if row["choice"] == "replaced" and row["new_state"] == "wrong_present"]}


def _recovery(window, reports, observations, availability):
    """Describe the declared P003 episode; other windows have no such episode."""
    if window["possession_id"] != "possession_003" or not (window["start_frame_index"] <= 163 and window["end_frame_index"] >= 174):
        return None
    indexed = {arm: {row["frame_index"]: row for row in reports[arm]["frame_results"]} for arm in ARMS}
    observed = {arm: {row["frame_index"]: row for row in observations[arm]["frames"]} for arm in ARMS}
    available = {row["frame_index"]: row for row in availability["frame_results"]}
    _require(all(frame_state(indexed[arm][index]) in HIDDEN_STATES
                 for arm in ARMS for index in range(165, 170)), "Declared recovery hidden episode differs")
    fps = reports[ARM]["source_video"]["fps"]
    _require(type(fps) in (int, float) and math.isfinite(fps) and fps > 0, "Invalid recovery source fps")
    arms = {}
    for arm in ARMS:
        first = next((index for index in range(170, 175) if frame_state(indexed[arm][index]) == "matched"), None)
        delay = None if first is None else first - 170
        arms[arm] = {"first_subsequent_raw10_match": first, "delay_frames_from_170": delay,
                     "delay_seconds_from_170": None if delay is None else delay / fps}
    return {"boundary_frame_results": [{"frame_index": index,
              "arms": {arm: {"state": frame_state(indexed[arm][index]),
                              "emitted_candidate_indices": deepcopy(observed[arm][index]["emitted_candidate_indices"])} for arm in ARMS}}
             for index in range(163, 175)],
            "hidden_frame_indices": [165, 166, 167, 168, 169], "arms": arms,
            "frame_170_candidate_availability": deepcopy(available[170]),
            "single_selected_episode_only": True, "general_reacquisition_guarantee": False}


def _validate_availability(availability, report, observations):
    """Reconcile the sealed diagnostic's lists and totals without rescoring."""
    results = report["frame_results"]
    _require(availability["postselection_only"] is True
             and type(availability["eligible_denominator"]) is int
             and availability["eligible_denominator"] == state_summary(report)["eligible_denominator"]
             and [row["frame_index"] for row in availability["frame_results"]]
             == [row["frame_index"] for row in results], "Postselection availability alignment differs")
    available = {"original_rf": [], "corroborated": []}
    for row, result, observation in zip(availability["frame_results"], results, observations["frames"]):
        eligible = result["scoring_status"] == "localization_eligible"
        _require(type(row["localization_eligible"]) is bool and row["localization_eligible"] == eligible,
                 "Availability eligibility differs from scored frame")
        original = row["original_rf_raw10_candidate_indices"]
        supported = row["corroborated_raw10_candidate_indices"]
        original_flag = row["original_rf_raw10_available"]
        supported_flag = row["corroborated_raw10_available"]
        if not eligible:
            _require(all(value is None for value in (original, supported, original_flag, supported_flag)),
                     "Ineligible availability must retain null diagnostics")
            continue
        for value in (original, supported):
            _require(isinstance(value, list) and all(type(index) is int and index >= 0 for index in value)
                     and value == sorted(set(value)), "Invalid availability candidate indices")
        supporting_indices = observation["supported_candidate_indices"]
        _require(isinstance(supporting_indices, list)
                 and all(type(index) is int and index >= 0 for index in supporting_indices)
                 and supporting_indices == sorted(set(supporting_indices)),
                 "Invalid supported candidate indices in observations")
        _require(supported == [index for index in original if index in set(supporting_indices)],
                 "Corroborated availability differs from supported original candidates")
        _require(type(original_flag) is bool and original_flag == bool(original)
                 and type(supported_flag) is bool and supported_flag == bool(supported),
                 "Availability flags differ from candidate lists")
        if original_flag:
            available["original_rf"].append(row["frame_index"])
        if supported_flag:
            available["corroborated"].append(row["frame_index"])
    for key, frames in available.items():
        total = availability[key]
        _require(type(total["count"]) is int and total["count"] == len(frames)
                 and isinstance(total["frame_indices"], list)
                 and all(type(index) is int for index in total["frame_indices"])
                 and total["frame_indices"] == frames, "Availability total/list differs from per-frame diagnostics")


def compare_window(window, new_report, saved_reports_by_arm, observations_by_arm):
    _require(set(saved_reports_by_arm) == set(CONTROLS), "Exactly the three saved controls are required")
    reports = {**saved_reports_by_arm, ARM: new_report}
    _require(set(observations_by_arm) == set(ARMS), "Exactly the four fixed observation arms are required")
    expected = list(range(window["start_frame_index"], window["end_frame_index"] + 1))
    _require(expected and window["purpose"] in POOLS, "Invalid comparison window/pool")
    for arm in ARMS:
        report = reports[arm]
        _require(report["config"] == (CONFIG if arm == ARM else _control_config(arm))
                 and report["localization_radius_px"] == RADIUS
                 and report["selection_purpose"] == window["purpose"]
                 and report["possession_id"] == window["possession_id"]
                 and report["source_video"] == window["source_video"]
                 and [row["frame_index"] for row in report["frame_results"]] == expected,
                 "Window report alignment/configuration differs")
        _bind_report_observations(report, observations_by_arm[arm])
    tables = {arm: transitions(reports[arm], new_report) for arm in CONTROLS}
    summaries = {arm: state_summary(reports[arm]) for arm in ARMS}
    choices = _choice_changes(observations_by_arm[TOP], observations_by_arm[ARM], reports[TOP], new_report)
    primary = tables[TOP]
    effects = {
        "correct_choices_lost": primary["eligible"]["matched"]["wrong_present"]["frame_indices"] + primary["eligible"]["matched"]["missing"]["frame_indices"],
        "wrong_outputs_suppressed": primary["eligible"]["wrong_present"]["missing"]["frame_indices"],
        "matches_recovered": primary["eligible"]["wrong_present"]["matched"]["frame_indices"] + primary["eligible"]["missing"]["matched"]["frame_indices"],
        "hidden_alarms_suppressed": primary["hidden"]["alarm"]["no_current_output"]["frame_indices"],
        "new_hidden_alarms": primary["hidden"]["no_current_output"]["alarm"]["frame_indices"],
        "wrong_replacements": choices["wrong_replacement_frames"],
    }
    availability = new_report["candidate_availability"]
    _validate_availability(availability, new_report, observations_by_arm[ARM])
    deltas = {control: {state: summaries[ARM]["counts"][state] - summaries[control]["counts"][state]
                        for state in (*STATES, "alarm")} for control in CONTROLS}
    return {"window_id": window["window_id"], "purpose": window["purpose"],
            "possession_id": window["possession_id"], "first_frame": expected[0], "last_frame": expected[-1],
            "summaries": summaries, "paired_transitions": tables,
            "temporal_metrics": {arm: temporal_metrics(reports[arm]) for arm in ARMS},
            "startup": {arm: {"frame_index": expected[0], "state": frame_state(reports[arm]["frame_results"][0]),
                              "emitted_candidate_indices": deepcopy(observations_by_arm[arm]["frames"][0]["emitted_candidate_indices"])} for arm in ARMS},
            "startup_parity_required": False, "candidate_choices_against_top_one": choices,
            "primary_effects": {key: {"count": len(frames), "frame_indices": sorted(frames)} for key, frames in effects.items()},
            "paired_original_center_errors": {arm: _paired_errors(reports[arm], new_report) for arm in CONTROLS},
            "candidate_availability": deepcopy(availability),
            "recovery": _recovery(window, reports, observations_by_arm, availability),
            "count_deltas": deltas,
            "window_regressions": {arm: {state: delta for state, delta in deltas[arm].items()
                                         if (delta < 0 if state == "matched" else delta > 0)} for arm in CONTROLS},
            "changed_emission_frames": {arm: [old["frame_index"] for old, new in zip(observations_by_arm[arm]["frames"], observations_by_arm[ARM]["frames"])
                                              if old["emitted_candidate_indices"] != new["emitted_candidate_indices"]] for arm in CONTROLS}}


def aggregate_pool(windows, purpose):
    _require(purpose in POOLS and windows and all(window["purpose"] == purpose for window in windows), "Pools must stay separate")
    _require(len({window["window_id"] for window in windows}) == len(windows), "Duplicate pool window")
    for index, window in enumerate(windows):
        _require(not any(other["possession_id"] == window["possession_id"]
                         and other["first_frame"] <= window["last_frame"] and window["first_frame"] <= other["last_frame"]
                         for other in windows[:index]), "Overlapping pool windows")
    totals = {}
    for arm in ARMS:
        keyed = {state: [{"window_id": window["window_id"], "frame_index": frame}
                          for window in windows for frame in window["summaries"][arm]["frame_indices"][state]]
                 for state in (*STATES, *HIDDEN_STATES, "ineligible")}
        totals[arm] = {"counts": {state: len(frames) for state, frames in keyed.items()}, "frames": keyed,
                       **{key: sum(window["summaries"][arm][key] for window in windows)
                          for key in ("eligible_denominator", "hidden_denominator", "frame_denominator", "missed_eligible_count")}}
    tables = {}
    for arm in CONTROLS:
        tables[arm] = {}
        for kind, states in (("eligible", STATES), ("hidden", HIDDEN_STATES)):
            tables[arm][kind] = {}
            for before in states:
                tables[arm][kind][before] = {}
                for after in states:
                    frames = [{"window_id": window["window_id"], "frame_index": frame} for window in windows
                              for frame in window["paired_transitions"][arm][kind][before][after]["frame_indices"]]
                    tables[arm][kind][before][after] = {"count": len(frames), "frames": frames}
    availability = {"eligible_denominator": sum(window["candidate_availability"]["eligible_denominator"] for window in windows)}
    for key in ("original_rf", "corroborated"):
        frames = [{"window_id": window["window_id"], "frame_index": frame} for window in windows
                  for frame in window["candidate_availability"][key]["frame_indices"]]
        availability[key] = {"count": len(frames), "frames": frames}
    choices = {}
    for key in ("retained", "suppressed", "replaced", "both_missing"):
        frames = [{"window_id": window["window_id"], "frame_index": frame} for window in windows
                  for frame in window["candidate_choices_against_top_one"]["frame_indices"][key]]
        choices[key] = {"count": len(frames), "frames": frames}
    effects = {}
    for key in windows[0]["primary_effects"]:
        frames = [{"window_id": window["window_id"], "frame_index": frame} for window in windows
                  for frame in window["primary_effects"][key]["frame_indices"]]
        effects[key] = {"count": len(frames), "frames": frames}
    return {"purpose": purpose, "window_count": len(windows), "totals": totals,
            "paired_transitions": tables, "candidate_availability": availability,
            "candidate_choices_against_top_one": choices, "primary_effects": effects,
            "paired_original_center_errors": {arm: [{"window_id": window["window_id"], **deepcopy(row)}
                                                       for window in windows for row in window["paired_original_center_errors"][arm]]
                                               for arm in CONTROLS},
            "window_regressions": [{"window_id": window["window_id"], "against": arm, "deltas": deepcopy(window["window_regressions"][arm])}
                                   for window in windows for arm in CONTROLS if window["window_regressions"][arm]],
            "windows": deepcopy(windows), "runs_not_concatenated": True,
            "selected_operating_point": None, "quality_gate": None}


def development_interpretation(pools):
    """Apply the frozen ordered, per-window primary-control rule exactly."""
    _require(len(pools) == 2 and {pool["purpose"] for pool in pools} == set(POOLS), "Both separate pools required")
    windows = [window for pool in pools for window in pool["windows"]]
    _require(windows and len({window["window_id"] for window in windows}) == len(windows), "Duplicate/empty interpretation windows")
    favorable, strict, unchanged = True, False, True
    match_gain, wrong_suppression, hidden_suppression, any_gain, any_loss = False, False, False, False, False
    for window in windows:
        old, new = (window["summaries"][arm]["counts"] for arm in (TOP, ARM))
        table = window["paired_transitions"][TOP]
        lost = sum(table["eligible"]["matched"][state]["count"] for state in ("wrong_present", "missing"))
        new_hidden = table["hidden"]["no_current_output"]["alarm"]["count"]
        favorable &= lost == 0 and new["wrong_present"] <= old["wrong_present"] and new["alarm"] <= old["alarm"] and new_hidden == 0
        match_gain |= new["matched"] > old["matched"]
        wrong_suppression |= new["wrong_present"] < old["wrong_present"]
        hidden_suppression |= new["alarm"] < old["alarm"]
        strict |= new["matched"] > old["matched"] or new["wrong_present"] < old["wrong_present"] or new["alarm"] < old["alarm"]
        unchanged &= all(cell["count"] == 0 for kind in table.values() for before, row in kind.items() for after, cell in row.items() if before != after)
        any_gain |= any(table["eligible"][before][after]["count"] for before, after in (("wrong_present", "matched"), ("missing", "matched"), ("wrong_present", "missing"))) or table["hidden"]["alarm"]["no_current_output"]["count"] > 0
        any_loss |= lost > 0 or table["eligible"]["missing"]["wrong_present"]["count"] > 0 or new_hidden > 0
    label = "favorable_development" if favorable and strict else "unchanged_measured_outcomes" if unchanged else "not_favorable"
    return {"against": TOP, "label": label, "favorable_development": label == "favorable_development",
            "raw10_matched_coverage_improved_somewhere": bool(match_gain),
            "wrong_present_reduced_somewhere": bool(wrong_suppression),
            "hidden_alarms_reduced_somewhere": bool(hidden_suppression),
            "tradeoff": bool(any_gain and any_loss), "pure_regression": bool(any_loss and not any_gain),
            "suppression_alone_is_recovered_localization": False,
            "semantic_identity_established": False, "better_centering_established": False,
            "requires_six_new_human_final_frame_reviews": True,
            "production_quality_gate": False, "selected_operating_point": None, "quality_gate": None}

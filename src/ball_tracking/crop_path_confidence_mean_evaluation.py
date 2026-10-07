"""Pure fixed-scope mean-path scoring and copied-control comparisons.

All values are supplied by the phase-guarded worker. This module never opens a
file, follows a provenance pointer, or re-executes a saved selector/evaluator.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from .development_experiments import canonical_sha256, require_digest
from .evaluation import evaluate_detections
from .tiled_evaluation import METRICS

ARM = "history_mean_edge_tight_cost_tight"
TT = "history_edge_tight_cost_tight"
TOP = "crop_top_one"
ARMS = (TT, ARM, TOP)
STATES = ("matched", "wrong_present", "missing")
HIDDEN_STATES = ("alarm", "no_current_output")
POOLS = ("representative_evaluation", "challenge_evaluation")
CONFIG = dict(arm=ARM, confidence_threshold=.01, candidate_cap=20, edge_step=.01, cost_step=.01)
DIAGNOSTIC_FRAMES = (300, 301, 302, 304, 308, 319, 320, 324)
DIAGNOSTIC_WINDOW = "possession_003_frames_0300_0324_representative_evaluation_development_v0_2"
IDENTITY = ("possession_id", "source_video", "window", "selection_purpose",
            "input_model_provenance", "input_candidate_content_sha256",
            "annotation_content_sha256", "matching_rule", "localization_radius_px")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _frames(run, observations):
    """Validate original candidate references without deriving any selection."""
    _require(observations["input_candidate_content_sha256"] == canonical_sha256(run.to_dict()),
             "Observation candidate namespace differs")
    _require(observations["source_video"] == run.source_video.to_dict()
             and observations["window"] == run.window.to_dict()
             and observations["possession_id"] == run.possession_id,
             "Observation source/window differs")
    _require([f["frame_index"] for f in observations["frames"]] == [f.frame_index for f in run.frames],
             "Observation frame order differs")
    selected = []
    for frame, observation in zip(run.frames, observations["frames"]):
        emitted = observation["emitted_candidate_indices"]
        candidates = {c.candidate_index: c for c in frame.detections}
        _require(isinstance(emitted, list) and len(emitted) <= 1
                 and all(type(i) is int and i in candidates and candidates[i].confidence >= .01 for i in emitted),
                 "Expected zero or one original floor-qualified emission")
        ranking = observation["ranking"]
        if ranking is not None:
            winner = ranking["winner"]
            endpoint = winner["endpoint"]
            expected = [endpoint[1]] if endpoint is not None and endpoint[0] == frame.frame_index else []
            _require(expected == emitted, "Emission differs from current endpoint")
        selected.append(replace(frame, detections=tuple(c for c in frame.detections if c.candidate_index in emitted)))
    return tuple(selected)


def evaluate_unit(labels, run, observations, commit):
    """Call the established raw evaluator only for the frozen new arm."""
    require_digest(commit, "mean evaluator commit", 40)
    _require(observations["config"] == CONFIG, "Only the fixed new mean arm may be evaluated")
    selected = _frames(run, observations)
    score = evaluate_detections(labels, replace(run, frames=selected),
                                confidence_threshold=.01, localization_radius_px=10.0)
    report = {
        "schema_version": "ball_crop_path_confidence_mean_evaluation/v0.1",
        "variant_id": observations["variant_id"], "config": deepcopy(CONFIG),
        "localization_radius_px": 10.0, "selection_purpose": labels.window.selection_purpose,
        "possession_id": run.possession_id, "source_video": run.source_video.to_dict(),
        "window": run.window.to_dict(), "input_model_provenance": run.model_provenance.to_dict(),
        "ranking_code_commit": observations["ranking_code_commit"], "evaluator_code_commit": commit,
        "observations_content_sha256": canonical_sha256(observations),
        "input_candidate_content_sha256": observations["input_candidate_content_sha256"],
        "annotation_content_sha256": score["annotation_content_sha256"],
        "matching_rule": "raw center distance; uncertainty diagnostic only",
        "metrics": {k: score[k] for k in METRICS}, "frame_results": score["frame_results"],
        "execution_role": "new_distinct_evaluation", "selected_operating_point": None,
        "quality_gate": None, "semantic_identity_labels_created": False,
    }
    report["state_summary"] = state_summary(report)
    report["temporal_metrics"] = temporal_metrics(report)
    report["path_metrics"] = path_metrics(observations)
    return report


def verify_saved_observations(wrapper, reference, run):
    """Copy a bound legacy wrapper; never invoke its rederiving validator."""
    _require(isinstance(wrapper, dict) and isinstance(wrapper.get("observations"), dict),
             "Expected saved observations wrapper")
    value = wrapper["observations"]
    expected_config = dict(CONFIG, arm=TT) if reference["config"]["arm"] == TT else dict(
        arm=TOP, confidence_threshold=.01, candidate_cap=None, edge_step=None, cost_step=None)
    _require(reference["config"]["arm"] in (TT, TOP) and reference["config"] == expected_config
             and value["config"] == reference["config"]
             and value["variant_id"] == reference["variant_id"], "Saved control configuration differs")
    _require(canonical_sha256(value) == reference["observations_content_sha256"]
             and value["input_candidate_content_sha256"] == reference["input_candidate_content_sha256"]
             and value["ranking_code_commit"] == reference["original_selection_commit"]
             and value["detector_code_commit"] == reference["original_detector_commit"]
             and len(value["frames"]) == reference["frame_count"], "Saved control content/provenance differs")
    _frames(run, value)
    return deepcopy(value)


def verify_saved_report(report, reference, observations, run, labels):
    """Validate a single already-extracted .01/raw10 report and preserve it."""
    _require(report["config"]["arm"] in (TT, TOP)
             and report["config"] == observations["config"] == reference["config"]
             and report["config"]["confidence_threshold"] == .01
             and report["localization_radius_px"] == reference["localization_radius_px"] == 10.0,
             "Saved report settings differ")
    _require(canonical_sha256(report) == reference["report_content_sha256"], "Saved report content differs")
    _require(report["observations_content_sha256"] == reference["observations_content_sha256"] == canonical_sha256(observations)
             and report["input_candidate_content_sha256"] == canonical_sha256(run.to_dict())
             and report["annotation_content_sha256"] == canonical_sha256(labels.to_dict())
             and report["ranking_code_commit"] == reference["original_selection_commit"]
             and report["evaluator_code_commit"] == reference["original_evaluation_commit"],
             "Saved report provenance differs")
    _require(report["source_video"] == run.source_video.to_dict()
             and report["window"] == run.window.to_dict() and report["possession_id"] == run.possession_id
             and report["input_model_provenance"] == run.model_provenance.to_dict()
             and report["selection_purpose"] == reference["purpose"] == labels.window.selection_purpose,
             "Saved report identity differs")
    _require([f["frame_index"] for f in report["frame_results"]] == [f.frame_index for f in run.frames],
             "Saved report frame order differs")
    for result, observation in zip(report["frame_results"], observations["frames"]):
        emitted = observation["emitted_candidate_indices"]
        _require(result["accepted_detection_count"] == len(emitted)
                 and (result["matched_candidate_index"] is None or result["matched_candidate_index"] in emitted),
                 "Saved result and emitted candidate differ")
    state_summary(report)
    return deepcopy(report)


def frame_state(result):
    count = result["accepted_detection_count"]
    _require(type(count) is int and count in (0, 1), "Single-output state requires zero/one accepted candidate")
    if result["scoring_status"] == "localization_eligible":
        matched = result["matched_candidate_index"] is not None
        _require(not matched or count == 1, "Matched frame has no emission")
        return "matched" if matched else "wrong_present" if count else "missing"
    if result["scoring_status"] == "not_visible_negative":
        _require(result["matched_candidate_index"] is None, "Hidden frame cannot match a fabricated center")
        return "alarm" if count else "no_current_output"
    return "ineligible"


def state_summary(report):
    rows = report["frame_results"]
    indices = [r["frame_index"] for r in rows]
    _require(len(set(indices)) == len(indices) and indices == sorted(indices), "Duplicate/reordered result frames")
    frames = {state: [] for state in (*STATES, *HIDDEN_STATES, "ineligible")}
    for row in rows:
        frames[frame_state(row)].append(row["frame_index"])
    eligible = sum(len(frames[s]) for s in STATES)
    hidden = sum(len(frames[s]) for s in HIDDEN_STATES)
    return {"eligible_denominator": eligible, "hidden_denominator": hidden, "frame_denominator": len(rows),
            "counts": {s: len(f) for s, f in frames.items()}, "frame_indices": frames,
            "missed_eligible_count": len(frames["wrong_present"]) + len(frames["missing"])}


def temporal_metrics(report):
    """Hidden/ineligible frames and source discontinuities break both runs."""
    correct, missed, current, last, mode = [], [], 0, None, None
    for row in [*report["frame_results"], None]:
        state = frame_state(row) if row is not None else None
        next_mode = "correct" if state == "matched" else "missed" if state in ("wrong_present", "missing") else None
        consecutive = row is not None and (last is None or row["frame_index"] == last + 1)
        if current and (not consecutive or next_mode != mode):
            (correct if mode == "correct" else missed).append(current)
            current = 0
        if next_mode:
            current += 1
        mode = next_mode
        last = row["frame_index"] if row is not None else None
    return {"correct_run_lengths": correct, "longest_correct_run": max(correct, default=0),
            "missed_eligible_run_lengths": missed, "longest_missed_eligible_run": max(missed, default=0)}


def path_metrics(observations):
    histogram, choices = {}, {"current": [], "older": [], "empty": []}
    singleton = []
    for row in observations["frames"]:
        ranking, emitted = row["ranking"], row["emitted_candidate_indices"]
        if ranking is None:
            count, choice = (1, "current") if emitted else (0, "empty")
        else:
            winner = ranking["winner"]
            endpoint = winner["endpoint"]
            count = len(winner["path"])
            _require(winner.get("node_count", count) == count, "Winner node count differs from path")
            choice = "empty" if endpoint is None else "current" if endpoint[0] == row["frame_index"] else "older"
            _require(bool(emitted) == (choice == "current"), "Path endpoint emission disagrees")
        histogram[str(count)] = histogram.get(str(count), 0) + 1
        choices[choice].append(row["frame_index"])
        if count == 1 and emitted:
            singleton.append(row["frame_index"])
    return {"path_node_counts": histogram, "endpoint_choice_counts": {k: len(v) for k, v in choices.items()},
            "endpoint_choice_frame_indices": choices, "singleton_emission_count": len(singleton),
            "singleton_emission_frame_indices": singleton,
            "top_one_path_is_descriptive_singleton": observations["config"]["arm"] == TOP}


def transitions(before, after):
    _require(all(before[k] == after[k] for k in IDENTITY), "Comparison mixes source, labels, window, pool or radius")
    old, new = before["frame_results"], after["frame_results"]
    _require([r["frame_index"] for r in old] == [r["frame_index"] for r in new], "Comparison alignment differs")
    tables = {"eligible": {a: {b: {"count": 0, "frame_indices": []} for b in STATES} for a in STATES},
              "hidden": {a: {b: {"count": 0, "frame_indices": []} for b in HIDDEN_STATES} for a in HIDDEN_STATES}}
    for left, right in zip(old, new):
        a, b = frame_state(left), frame_state(right)
        if a == "ineligible":
            _require(b == a, "Eligibility changed across arms")
            continue
        kind = "eligible" if a in STATES else "hidden"
        _require(b in tables[kind][a], "Eligibility changed across arms")
        cell = tables[kind][a][b]
        cell["count"] += 1
        cell["frame_indices"].append(left["frame_index"])
    return tables


def compare_window(window, new_report, saved_reports_by_arm, observations_by_arm):
    reports = {ARM: new_report, **saved_reports_by_arm}
    _require(set(reports) == set(ARMS) and set(observations_by_arm) == set(ARMS), "Exactly the three fixed arms are required")
    expected = list(range(window["start_frame_index"], window["end_frame_index"] + 1))
    for arm in ARMS:
        _require(reports[arm]["config"]["arm"] == observations_by_arm[arm]["config"]["arm"] == arm
                 and reports[arm]["selection_purpose"] == window["purpose"]
                 and [r["frame_index"] for r in reports[arm]["frame_results"]] == expected
                 and [r["frame_index"] for r in observations_by_arm[arm]["frames"]] == expected,
                 "Window observations/report alignment differs")
    startup = [observations_by_arm[a]["frames"][0]["emitted_candidate_indices"] for a in ARMS]
    _require(all(s == startup[0] for s in startup), "All-window startup singleton parity failed")
    tables = {a: transitions(reports[a], new_report) for a in (TT, TOP)}
    summaries = {a: state_summary(reports[a]) for a in ARMS}
    regressions = {}
    for control in (TT, TOP):
        old, new = summaries[control]["counts"], summaries[ARM]["counts"]
        regressions[control] = {k: new[k] - old[k] for k in (*STATES, "alarm")
                                if (new[k] < old[k] if k == "matched" else new[k] > old[k])}
    return {"window_id": window["window_id"], "purpose": window["purpose"],
            "possession_id": window["possession_id"], "first_frame": expected[0], "last_frame": expected[-1],
            "startup_parity": True, "summaries": summaries, "paired_transitions": tables,
            "temporal_metrics": {a: temporal_metrics(reports[a]) for a in ARMS},
            "path_metrics": {a: path_metrics(observations_by_arm[a]) for a in ARMS},
            "window_regressions": regressions,
            "changed_emission_frames": {a: [n["frame_index"] for o, n in zip(observations_by_arm[a]["frames"], observations_by_arm[ARM]["frames"])
                                             if o["emitted_candidate_indices"] != n["emitted_candidate_indices"]]
                                        for a in (TT, TOP)}}


def aggregate_pool(windows, purpose):
    _require(purpose in POOLS and windows and all(w["purpose"] == purpose for w in windows), "Pools must stay separate")
    _require(len({w["window_id"] for w in windows}) == len(windows), "Duplicate pool window")
    totals = {}
    for arm in ARMS:
        totals[arm] = {"counts": {s: sum(w["summaries"][arm]["counts"][s] for w in windows)
                                  for s in (*STATES, *HIDDEN_STATES, "ineligible")},
                       **{d: sum(w["summaries"][arm][d] for w in windows)
                          for d in ("eligible_denominator", "hidden_denominator", "frame_denominator", "missed_eligible_count")}}
    tables = {}
    for control in (TT, TOP):
        tables[control] = {}
        for kind, states in (("eligible", STATES), ("hidden", HIDDEN_STATES)):
            tables[control][kind] = {}
            for a in states:
                tables[control][kind][a] = {}
                for b in states:
                    frames = [{"window_id": w["window_id"], "frame_index": f} for w in windows
                              for f in w["paired_transitions"][control][kind][a][b]["frame_indices"]]
                    tables[control][kind][a][b] = {"count": len(frames), "frames": frames}
    return {"purpose": purpose, "window_count": len(windows), "totals": totals,
            "paired_transitions": tables, "windows": deepcopy(windows),
            "window_regressions": [{"window_id": w["window_id"], "against": c, "deltas": w["window_regressions"][c]}
                                   for w in windows for c in (TT, TOP) if w["window_regressions"][c]],
            "runs_not_concatenated": True, "selected_operating_point": None, "quality_gate": None}


def development_interpretation(pools):
    _require(len(pools) == 2 and {p["purpose"] for p in pools} == set(POOLS), "Both separate pools required")
    weak, strict, unchanged, any_better = True, False, True, False
    for pool in pools:
        old, new = (pool["totals"][arm]["counts"] for arm in (TT, ARM))
        for state in (*STATES, "alarm"):
            delta = new[state] - old[state]
            favorable = delta > 0 if state == "matched" else delta < 0
            weak &= delta >= 0 if state == "matched" else delta <= 0
            unchanged &= delta == 0
            any_better |= favorable
            strict |= favorable and state in ("matched", "alarm")
    regressions = any(r["against"] == TT for p in pools for r in p["window_regressions"])
    label = ("favorable pool totals with window regressions" if regressions else "favorable development signal") if weak and strict else (
        "unchanged" if unchanged else "mixed" if any_better else "unfavorable")
    return {"against": TT, "label": label, "favorable_development_signal": bool(weak and strict),
            "requires_six_new_human_final_frame_reviews": True, "production_quality_gate": False,
            "top_one_comparison_is_independent": True, "history_adds_value_established": False,
            "semantic_identity_established": False}


def diagnostic_rows(window_id, observations_by_arm, human_rows):
    _require(window_id == DIAGNOSTIC_WINDOW, "Diagnostic is fixed to the reviewed P003 window")
    _require([r["frame_index"] for r in human_rows] == list(DIAGNOSTIC_FRAMES), "Exactly the eight existing human rows required")
    indexed = {a: {r["frame_index"]: r for r in observations_by_arm[a]["frames"]} for a in ARMS}

    def compact(observation):
        ranking = observation["ranking"]
        return {"frame_index": observation["frame_index"],
                "emitted_candidate_indices": deepcopy(observation["emitted_candidate_indices"]),
                "decision_reason": observation["decision_reason"],
                "winner": deepcopy(ranking["winner"]) if ranking is not None else None,
                "score_margin": ranking["score_margin"] if ranking is not None else None}

    result = []
    for human in human_rows:
        frame = human["frame_index"]
        _require(human["status"] == "reviewed" and human["reviewer"] == "Ryan", "Human judgment not completed")
        old = indexed[TT][frame]["emitted_candidate_indices"]
        _require(len(old) == 1 and (human["emitted_candidate_index"] is None or human["emitted_candidate_index"] == old[0]),
                 "Human review names a different old emission")
        row = {"frame_index": frame, "saved_tt": {"observation": compact(indexed[TT][frame]),
                                                  "original_human_record": deepcopy(human)},
               "new_mean": {"observation": compact(indexed[ARM][frame]), "semantic_identity": None},
               "saved_top_one": {"observation": compact(indexed[TOP][frame]), "semantic_identity": None},
               "judgment_scope": "originally reviewed saved TT emission only",
               "prior_contrast_context": "confidence_only_startup" if frame == 300 else "motion_related_comparison" if frame == 304 else "one_of_six_history_dominated_saved_comparisons",
               "new_causal_verdict": None}
        if frame == 300:
            _require(indexed[ARM][frame]["emitted_candidate_indices"] == old, "Frame 300 must be unchanged")
        result.append(row)
    return result

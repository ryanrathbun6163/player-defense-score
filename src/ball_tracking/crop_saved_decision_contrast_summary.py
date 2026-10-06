"""Pure, bounded extraction of two saved endpoints; never reruns selection.

Inputs are already byte-verified JSON values supplied by the owned worker.
This module performs no file access and never follows embedded file pointers.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

CONTRAST_SCHEMA = "ball_crop_saved_decision_contrast/v0.1"
MAX_JSON_BYTES = 131072
MAX_TEXT_BYTES = 65536
FRAMES = (300, 301, 302, 304, 308, 319, 320, 324)
ARM = "history_edge_tight_cost_tight"
WINDOW = "possession_003_frames_0300_0324_representative_evaluation_development_v0_2"
TERMS = ("current_confidence", "past_confidence", "internal_gap", "motion")
TT_CONFIG = dict(arm=ARM, confidence_threshold=.01, candidate_cap=20, edge_step=.01, cost_step=.01)
TOP_CONFIG = dict(arm="crop_top_twenty", confidence_threshold=.01, candidate_cap=20, edge_step=None, cost_step=None)
SETTING = dict(TT_CONFIG, policy="cap20", localization_radius_source_px=10.0)
REPORT_FIELDS = ("frame_index", "annotation_status", "visibility", "scoring_status",
                 "accepted_detection_count", "matched_candidate_index", "false_positive_count",
                 "false_negative_count", "matched_center_error_px")
LIMITATIONS = [
    "Eight correlated failures in one window; no performance or generalization estimate.",
    "Comparison is the saved highest-confidence raw-radius-qualified retained candidate, with original-index confidence tie break.",
    "Comparison identity, nearest-candidate status and highest-objective-compatible-endpoint status are unknown.",
    "Human judgments apply only to the emitted endpoint; recorded null human indices remain null.",
    "Different saved histories are not a controlled intervention or a causal explanation.",
    "Saved global margin is against the global runner-up, not necessarily this comparison.",
    "Frame 300 is confidence-only; no prior-history contribution exists.",
]
SOURCE_RULE = "Each copies entry maps the present descendant leaves of a value or field projection. Every descendant leaf uses the source pointer plus the identical RFC6901-escaped relative suffix; omitted source fields are not copied. No file pointer is followed."


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value, label, minimum=None, maximum=None):
    _require(type(value) in (int, float) and math.isfinite(value), f"Invalid numeric {label}")
    _require(minimum is None or value >= minimum, f"Below range: {label}")
    _require(maximum is None or value <= maximum, f"Above range: {label}")
    return value


def _integer(value, label, minimum=0):
    _require(type(value) is int and value >= minimum, f"Invalid integer {label}")
    return value


def _digest(value, label, length=64):
    _require(isinstance(value, str) and re.fullmatch("[0-9a-f]{" + str(length) + "}", value),
             f"Invalid digest {label}")


def _canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _same(value, expected, label):
    # JSON canonical equality also distinguishes booleans from numeric constants.
    _require(_canonical(value) == _canonical(expected), f"Inconsistent {label}")


def _null_choices(value):
    for key in ("selected_operating_point", "quality_gate"):
        _require(key in value and value[key] is None, f"Unexpected decision: {key}")


def _binding(value):
    _require(isinstance(value, dict) and isinstance(value.get("path"), str) and value["path"], "Invalid binding")
    _digest(value.get("sha256"), "binding")
    if "size_bytes" in value:
        _integer(value["size_bytes"], "binding size", 1)
    return {key: value[key] for key in ("path", "sha256")}


def _scope(scope):
    _require(scope.get("schema_version") == "ball_crop_saved_decision_contrast_scope/v0.1", "Wrong scope schema")
    _same(scope.get("frame_indices"), list(FRAMES), "scope frames")
    _same(scope.get("setting"), SETTING, "scope setting")
    _require(scope.get("window_id") == WINDOW and scope.get("possession_id") == "possession_003"
             and scope.get("purpose") == "representative_evaluation", "Wrong scope window")
    _null_choices(scope)
    _require(scope.get("selected_method") is None, "Unexpected selected method")
    arithmetic = scope["arithmetic"]
    for key, expected in {"gap_penalty": .25, "motion_penalty": .25, "relative_tolerance": 1e-9,
                          "absolute_tolerance": 1e-9, "current_endpoint_trailing_skips": 0,
                          "tie_definition": "exact_stored_score_equality", "frame300_has_no_prior_history": True,
                          "saved_global_margin_is_not_pair_gap": True}.items():
        _same(arithmetic.get(key), expected, "arithmetic " + key)
    _same(scope["outputs"]["files"], {"contrast.json": MAX_JSON_BYTES, "summary.md": MAX_TEXT_BYTES,
                                      "provenance.json": MAX_JSON_BYTES}, "output limits")
    _same(scope["comparison_rule"]["historical_path_bounds"],
          {str(f): {"start": max(300, f-4), "end": f} for f in FRAMES}, "path scope")
    inputs = scope["scientific_inputs"]
    _require(set(inputs) == {"representative_pool", "tt_observations_wrapper"}, "Wrong input scope")
    for value in inputs.values():
        _binding(value)
    refs = scope["frozen_report_references"]
    _require(set(refs) == {"crop_top_twenty", ARM}, "Wrong report scope")
    for arm, index, config in (("crop_top_twenty", 641, TOP_CONFIG), (ARM, 646, TT_CONFIG)):
        ref = refs[arm]
        _same(ref["source"], dict(_binding(inputs["representative_pool"]), json_pointer=f"/evaluation_reports/{index}"), "report source")
        _same(ref["config"], config, "report config")
        _require(ref["window_id"] == WINDOW and ref["purpose"] == scope["purpose"], "Report reference window")
        _number(ref["localization_radius_px"], "report radius")
        _require(ref["localization_radius_px"] == 10, "Wrong report radius")
        for field in ("report_content_sha256", "observations_content_sha256"):
            _digest(ref[field], field)
        for field in ("original_selection_commit", "original_evaluation_commit"):
            _digest(ref[field], field, 40)
        _binding(ref["observations_file"])
    control = scope["frozen_control_reference"]
    _same(control["config"], TT_CONFIG, "control config")
    _same(control["file"], _binding(inputs["tt_observations_wrapper"]), "control file")
    _same(refs[ARM]["observations_file"], control["file"], "TT observation file")
    _require(control["window_id"] == WINDOW and control["purpose"] == scope["purpose"]
             and control["possession_id"] == "possession_003" and type(control["frame_count"]) is int
             and control["frame_count"] == 25, "Control window differs")
    _require(control["observations_content_sha256"] == refs[ARM]["observations_content_sha256"], "Control digest differs")
    for field in ("observations_content_sha256", "input_candidate_content_sha256"):
        _digest(control[field], field)
    for field in ("original_selection_commit", "original_detector_commit"):
        _digest(control[field], field, 40)
    return refs, control


def _human(ledger, scope):
    _require(ledger.get("schema_version") == "ball_crop_candidate_identity_review_ledger/v0.1", "Wrong human ledger")
    _same(ledger["scope"], _binding(scope["administrative_authorities"]["selection_scope"]), "human scope")
    _require(ledger["window_id"] == WINDOW and ledger["required_reviewer"] == "Ryan", "Wrong human review window")
    _same(ledger["setting"], {"arm": ARM, "policy": "cap20", "confidence_threshold": .01,
                              "localization_radius_source_px": 10.0, "native_view": "view_0"}, "human setting")
    _same(ledger["selection_source"]["frame_indices"], list(FRAMES), "human selection")
    _null_choices(ledger)
    _require(ledger.get("selected_method") is None, "Human selected method")
    rows = ledger["rows"]
    _same([r["frame_index"] for r in rows], list(FRAMES), "human frames")
    _same(ledger["review_record"]["answered_frame_indices"], list(FRAMES), "answered frames")
    _same(ledger["review_record"]["pending_frame_indices"], [], "pending frames")
    for row in rows:
        _require(row["status"] == "reviewed" and row["reviewer"] == "Ryan"
                 and row["prior_localization_outcome"] == "present_nonmatching_current_output", "Stale human outcome")
        _require(isinstance(row["actual_response"], str) and row["actual_response"].strip(), "Missing human response")
        index = row["emitted_candidate_index"]
        _require(index is None or type(index) is int and index >= 0, "Invalid recorded human index")
        _require(index == 0 if row["frame_index"] == 300 else index is None, "Changed original human index uncertainty")
        expected = ("ball", "clearly_displaced") if row["frame_index"] == 319 else ("another_object", "not_applicable")
        _same([row["candidate_identity"], row["ball_center"]], list(expected), "human judgment")
    return rows


def _frame_index(rows, label):
    _require(isinstance(rows, list) and len(rows) == 25, "Wrong frame count: " + label)
    _same([row["frame_index"] for row in rows], list(range(300, 325)), label + " frame order")


def _input_headers(pool, wrapper, scope):
    refs, control = _scope(scope)
    _require(pool.get("schema_version") == "ball_crop_motion_pool/v0.1"
             and pool.get("purpose") == scope["purpose"], "Wrong pool header")
    _null_choices(pool)
    _digest(pool["experiment_spec_sha256"], "pool specification")
    _digest(pool["code_commit"], "pool commit", 40)
    _require(set(wrapper) == {"experiment_spec_sha256", "input_crop_file", "crop_content_sha256", "observations"}, "Wrong wrapper fields")
    _require(wrapper["experiment_spec_sha256"] == pool["experiment_spec_sha256"], "Different experiment namespace")
    _binding(wrapper["input_crop_file"])  # Inert provenance only, never opened.
    _digest(wrapper["crop_content_sha256"], "wrapper crop content")
    obs = wrapper["observations"]
    _require(_canonical(obs) == control["observations_content_sha256"], "Observation content digest differs")
    _require(obs["schema_version"] == "ball_crop_motion_observations/v0.1", "Wrong observation schema")
    _same(obs["config"], TT_CONFIG, "observation config")
    _require(obs["variant_id"] == control["variant_id"]
             and obs["ranking_code_commit"] == control["original_selection_commit"]
             and obs["detector_code_commit"] == control["original_detector_commit"]
             and obs["input_candidate_content_sha256"] == control["input_candidate_content_sha256"], "Observation provenance differs")
    _require(obs["possession_id"] == scope["possession_id"], "Observation possession differs")
    _same(obs["window"], {"start_frame_index": 300, "end_frame_index": 324}, "observation window")
    _null_choices(obs)
    _frame_index(obs["frames"], "observations")
    reports = []
    for arm, index in (("crop_top_twenty", 641), (ARM, 646)):
        report = pool["evaluation_reports"][index]
        ref = refs[arm]
        _require(_canonical(report) == ref["report_content_sha256"], "Report content digest differs")
        _require(report["schema_version"] == "ball_crop_motion_evaluation/v0.1", "Wrong report schema")
        _same(report["config"], ref["config"], "saved report configuration")
        _require(report["selection_purpose"] == scope["purpose"] and report["possession_id"] == scope["possession_id"], "Report window role differs")
        _same(report["window"], obs["window"], "report window")
        _same(report["source_video"], obs["source_video"], "source video namespace")
        _require(report["localization_radius_px"] == 10 and type(report["localization_radius_px"]) in (int, float), "Report radius differs")
        _require(report["input_candidate_content_sha256"] == control["input_candidate_content_sha256"]
                 and report["observations_content_sha256"] == ref["observations_content_sha256"]
                 and report["ranking_code_commit"] == ref["original_selection_commit"]
                 and report["evaluator_code_commit"] == ref["original_evaluation_commit"]
                 and pool["code_commit"] == ref["original_evaluation_commit"], "Report provenance differs")
        _require(report["matching_rule"] == "raw center distance; uncertainty diagnostic only", "Matching rule differs")
        _digest(report["annotation_content_sha256"], "annotation provenance")
        _null_choices(report)
        _frame_index(report["frame_results"], "report")
        reports.append(report)
    _require(reports[1]["variant_id"] == obs["variant_id"], "TT variant differs")
    expected_top_variant = "crop_top_twenty_" + _canonical(TOP_CONFIG)[:16]
    _require(reports[0]["variant_id"] == expected_top_variant, "Top-twenty variant differs")
    _same(reports[0]["input_model_provenance"], reports[1]["input_model_provenance"], "model provenance")
    _require(reports[0]["annotation_content_sha256"] == reports[1]["annotation_content_sha256"], "Annotation namespace differs")
    return obs, reports


def _outcome(value, frame, matched):
    _same(value["frame_index"], frame, "outcome frame")
    _require(value["annotation_status"] == "labeled" and value["visibility"] in ("fully_visible", "partially_visible")
             and value["scoring_status"] == "localization_eligible", "Unsupported localization outcome")
    count = _integer(value["accepted_detection_count"], "accepted count", 1)
    _integer(value["false_positive_count"], "false positive count")
    _integer(value["false_negative_count"], "false negative count")
    if matched:
        _integer(value["matched_candidate_index"], "comparison index")
        _number(value["matched_center_error_px"], "saved comparison error", 0, 10)
        _require(count <= 20 and value["false_positive_count"] == count-1 and value["false_negative_count"] == 0, "Contradictory retained match")
    else:
        _require(count == 1 and value["matched_candidate_index"] is None and value["matched_center_error_px"] is None
                 and value["false_positive_count"] == 1 and value["false_negative_count"] == 1, "Contradictory TT nonmatch")


def _unique_match(records, endpoint, label):
    _require(isinstance(records, list), "Missing " + label)
    keys = []
    for record in records:
        key = record["endpoint"]
        if key is not None:
            _require(isinstance(key, list) and len(key) == 2, "Invalid endpoint reference")
            for value in key:
                _integer(value, "endpoint reference")
            key = tuple(key)
        keys.append(key)
    _require(len(keys) == len(set(keys)), "Duplicate " + label)
    wanted = tuple(endpoint)
    _require(wanted in keys, "Missing " + label + " endpoint")
    index = keys.index(wanted)
    return index, records[index]


def _endpoint(value, frame, candidate):
    best, competing = value["best_path"], value["competing_endpoint"]
    _require(set(value) == {"best_path", "competing_endpoint", "disposition"}, "Unexpected endpoint fields")
    _require(set(best) == {"endpoint", "score", "path", "confidence_sum", "internal_skipped_frames", "normalized_step_squared_sum"}, "Unexpected best-path fields")
    _require(set(competing) == {"endpoint", "score", "path", "endpoint_confidence", "trailing_skipped_frames"}, "Unexpected competing fields")
    _same(best["endpoint"], [frame, candidate], "best endpoint")
    _same(competing["endpoint"], best["endpoint"], "competing endpoint")
    _same(competing["path"], best["path"], "saved endpoint paths")
    _same(competing["score"], best["score"], "saved endpoint scores")
    _same(competing["trailing_skipped_frames"], 0, "current endpoint trailing skips")
    path = best["path"]
    _require(isinstance(path, list) and 1 <= len(path) <= 5 and path[-1] == [frame, candidate], "Invalid saved path")
    for node in path:
        _require(isinstance(node, list) and len(node) == 2, "Invalid path node")
        _integer(node[0], "path frame")
        _integer(node[1], "path candidate")
        _require(max(300, frame-4) <= node[0] <= frame, "Path outside approved horizon")
    _require(all(1 <= b[0]-a[0] <= 3 for a, b in zip(path, path[1:])), "Invalid historical gap")
    c = _number(competing["endpoint_confidence"], "endpoint confidence", .01, 1)
    total = _number(best["confidence_sum"], "confidence sum", c, len(path))
    gap = _integer(best["internal_skipped_frames"], "internal skips")
    _require(gap == sum(b[0]-a[0]-1 for a, b in zip(path, path[1:])), "Saved gap count inconsistent with path")
    motion = _number(best["normalized_step_squared_sum"], "motion sum", 0)
    score = _number(best["score"], "saved score")
    terms = dict(zip(TERMS, (c, total-c, -.25*gap, -.25*motion)))
    _require(math.isclose(sum(terms.values()), score, rel_tol=1e-9, abs_tol=1e-9), "Saved score does not reconcile")
    if len(path) == 1:
        _require(total == c and gap == 0 and motion == 0, "Singleton has historical contribution")
    return terms


def _derived(row):
    frame = row["frame_index"]
    winner = row["winner"]["best_path"]["endpoint"][1]
    comparison = row["comparison_report"]["matched_candidate_index"]
    _integer(winner, "winner index")
    _integer(comparison, "comparison index")
    _require(winner != comparison, "Winner equals comparison")
    _require(row["winner"]["disposition"] == "emitted" and row["comparison"]["disposition"] == "eligible_not_emitted", "Candidate retention differs")
    contributions = {name: _endpoint(row[name], frame, candidate)
                     for name, candidate in (("winner", winner), ("comparison", comparison))}
    ws = row["winner"]["best_path"]["score"]
    cs = row["comparison"]["best_path"]["score"]
    gap = ws-cs
    _require(ws >= cs, "Comparison scores above saved winner")
    exact_tie = ws == cs
    if exact_tie:
        def key(name):
            item = row[name]["competing_endpoint"]
            return (-item["endpoint_confidence"], item["endpoint"][1], tuple(map(tuple, item["path"])))
        _require(key("winner") < key("comparison"), "Saved current-endpoint tie order contradicted")
    contrast = {key: contributions["winner"][key]-contributions["comparison"][key] for key in TERMS}
    _require(math.isclose(sum(contrast.values()), gap, rel_tol=1e-9, abs_tol=1e-9), "Pair contrast does not reconcile")
    _number(row["saved_global_score_margin"], "saved global margin", 0)
    _require(row["saved_global_score_margin"] <= gap or math.isclose(row["saved_global_score_margin"], gap, rel_tol=1e-9, abs_tol=1e-9), "Global margin exceeds named pair gap")
    return {"contributions": contributions, "pair_score_gap": gap,
            "term_contrasts": contrast, "exact_score_tie": exact_tie}


def _provenance(rows):
    copies = {"/window_id": ["scope", "/window_id"], "/setting": ["scope", "/setting"],
              "/source_bindings": ["scope", "/scientific_inputs"],
              "/candidate_namespace_sha256": ["scope", "/frozen_control_reference/input_candidate_content_sha256"]}
    derived = {}
    for i, row in enumerate(rows):
        target, offset = f"/rows/{i}", row["frame_index"]-300
        ob = f"/observations/frames/{offset}"
        for field in ("frame_index", "horizon_start", "horizon_end"):
            copies[f"{target}/{field}"] = ["tt_observations_wrapper", f"{ob}/{field}"]
        copies[target + "/human_review"] = ["human_ledger", f"/rows/{i}"]
        for name, index in (("comparison_report", 641), ("tt_report", 646)):
            copies[f"{target}/{name}"] = ["representative_pool", f"/evaluation_reports/{index}/frame_results/{offset}"]
        copies[target + "/saved_global_score_margin"] = ["tt_observations_wrapper", ob + "/ranking/score_margin"]
        for name in ("winner", "comparison"):
            locations = row["source_locations"][name]
            best = ob + f"/ranking/best_path_per_endpoint/{locations['best_path']}"
            endpoint = ob + f"/ranking/competing_endpoints/{locations['competing_endpoint']}"
            copies[f"{target}/{name}/best_path"] = ["tt_observations_wrapper", best]
            copies[f"{target}/{name}/competing_endpoint"] = ["tt_observations_wrapper", endpoint]
            copies[f"{target}/{name}/disposition"] = ["tt_observations_wrapper", ob + f"/candidate_decisions/{locations['disposition']}/disposition"]
            c = ["tt_observations_wrapper", endpoint + "/endpoint_confidence"]
            operands = {
                "current_confidence": ("identity", [c]),
                "past_confidence": ("subtract", [["tt_observations_wrapper", best + "/confidence_sum"], c]),
                "internal_gap": ("negative_product", [["scope", "/arithmetic/gap_penalty"], ["tt_observations_wrapper", best + "/internal_skipped_frames"]]),
                "motion": ("negative_product", [["scope", "/arithmetic/motion_penalty"], ["tt_observations_wrapper", best + "/normalized_step_squared_sum"]]),
            }
            for term, (operation, values) in operands.items():
                derived[f"{target}/contributions/{name}/{term}"] = {"operation": operation, "operands": values}
        score_operands = [["contrast", f"{target}/{name}/best_path/score"] for name in ("winner", "comparison")]
        derived[target + "/pair_score_gap"] = {"operation": "subtract", "operands": score_operands}
        derived[target + "/exact_score_tie"] = {"operation": "exact_equality", "operands": score_operands}
        for term in TERMS:
            derived[f"{target}/term_contrasts/{term}"] = {"operation": "subtract", "operands": [
                ["contrast", f"{target}/contributions/{name}/{term}"] for name in ("winner", "comparison")]}
    return {"copy_rule": SOURCE_RULE, "copies": copies, "derived": derived,
            "source_locations_rule": "Nonnegative array indices of the uniquely joined saved records; no alternative-comparator search or re-ranking is performed."}


def build_contrast(pool, wrapper, human_ledger, scope):
    """Extract the exact approved rows from supplied values, without any I/O."""
    obs, reports = _input_headers(pool, wrapper, scope)
    humans = _human(human_ledger, scope)
    rows = []
    for i, frame in enumerate(FRAMES):
        offset = frame-300
        observation = obs["frames"][offset]
        top, tt = (report["frame_results"][offset] for report in reports)
        _outcome(top, frame, True)
        _outcome(tt, frame, False)
        _same(observation["horizon_start"], max(300, frame-4), "horizon start")
        _same(observation["horizon_end"], frame, "horizon end")
        emitted = observation["emitted_candidate_indices"]
        _require(isinstance(emitted, list) and len(emitted) == 1, "Requires one emitted candidate")
        winner = _integer(emitted[0], "emitted candidate")
        _require(observation["decision_reason"] == "current_endpoint"
                 and observation["output_state"] == "tentative_observation", "Non-current saved output")
        rank = observation["ranking"]
        _same(rank["winner"]["endpoint"], [frame, winner], "saved winner")
        _same(rank["winner"], rank["competing_endpoints"][0], "first saved endpoint")
        decisions = observation["candidate_decisions"]
        ids = [_integer(d["candidate_index"], "disposition index") for d in decisions]
        _require(len(ids) == len(set(ids)), "Duplicate candidate dispositions")
        row = {"frame_index": frame, "horizon_start": observation["horizon_start"], "horizon_end": observation["horizon_end"],
               "comparison_report": {k: deepcopy(top[k]) for k in REPORT_FIELDS},
               "tt_report": {k: deepcopy(tt[k]) for k in REPORT_FIELDS},
               "saved_global_score_margin": rank["score_margin"], "human_review": deepcopy(humans[i]), "source_locations": {}}
        for name, candidate in (("winner", winner), ("comparison", top["matched_candidate_index"])):
            bi, best = _unique_match(rank["best_path_per_endpoint"], [frame, candidate], "best paths")
            ci, competing = _unique_match(rank["competing_endpoints"], [frame, candidate], "competing endpoints")
            _require(candidate in ids, "Missing candidate disposition")
            di = ids.index(candidate)
            row[name] = {"best_path": deepcopy(best), "competing_endpoint": deepcopy(competing), "disposition": decisions[di]["disposition"]}
            row["source_locations"][name] = {"best_path": bi, "competing_endpoint": ci, "disposition": di}
        row.update(_derived(row))
        rows.append(row)
    result = {"schema_version": CONTRAST_SCHEMA, "window_id": scope["window_id"], "setting": deepcopy(scope["setting"]),
              "source_bindings": deepcopy(scope["scientific_inputs"]),
              "candidate_namespace_sha256": scope["frozen_control_reference"]["input_candidate_content_sha256"],
              "rows": rows, "source_map": _provenance(rows), "limitations": deepcopy(LIMITATIONS),
              "selected_method": None, "selected_operating_point": None, "quality_gate": None}
    return validate_returned_contrast(result, scope, human_ledger)


def validate_returned_contrast(contrast, scope, human_ledger):
    """Check bounded worker transport without reopening either scientific input.

    Byte-bound worker evidence establishes original copies; this check validates
    their internal joins, arithmetic, declared provenance and unchanged human rows.
    """
    _scope(scope)
    humans = _human(human_ledger, scope)
    _require(set(contrast) == {"schema_version", "window_id", "setting", "source_bindings", "candidate_namespace_sha256",
                              "rows", "source_map", "limitations", "selected_method", "selected_operating_point", "quality_gate"}, "Unexpected contrast fields")
    _require(contrast["schema_version"] == CONTRAST_SCHEMA, "Wrong contrast schema")
    for field, expected in (("window_id", scope["window_id"]), ("setting", scope["setting"]),
                            ("source_bindings", scope["scientific_inputs"]), ("candidate_namespace_sha256", scope["frozen_control_reference"]["input_candidate_content_sha256"]),
                            ("limitations", LIMITATIONS)):
        _same(contrast[field], expected, "returned " + field)
    _null_choices(contrast)
    _require(contrast["selected_method"] is None, "Unexpected method decision")
    rows = contrast["rows"]
    _same([r["frame_index"] for r in rows], list(FRAMES), "returned frame order")
    for i, row in enumerate(rows):
        _require(set(row) == {"frame_index", "horizon_start", "horizon_end", "winner", "comparison", "comparison_report", "tt_report",
                              "saved_global_score_margin", "human_review", "source_locations", "contributions", "pair_score_gap", "term_contrasts", "exact_score_tie"}, "Unexpected row fields")
        frame = row["frame_index"]
        _same(row["horizon_start"], max(300, frame-4), "returned horizon start")
        _same(row["horizon_end"], frame, "returned horizon end")
        _same(row["human_review"], humans[i], "returned human record")
        for key, matched in (("comparison_report", True), ("tt_report", False)):
            _require(set(row[key]) == set(REPORT_FIELDS), "Unexpected report fields")
            _outcome(row[key], frame, matched)
        _same([row["comparison_report"][k] for k in ("annotation_status", "visibility", "scoring_status")],
              [row["tt_report"][k] for k in ("annotation_status", "visibility", "scoring_status")], "report label context")
        human_index = row["human_review"]["emitted_candidate_index"]
        _require(human_index is None or human_index == row["winner"]["best_path"]["endpoint"][1], "Human known index differs")
        locations = row["source_locations"]
        _require(set(locations) == {"winner", "comparison"}, "Wrong source locations")
        for item in locations.values():
            _require(set(item) == {"best_path", "competing_endpoint", "disposition"}, "Wrong source index fields")
            for value in item.values():
                _integer(value, "source array index")
        for field in ("best_path", "competing_endpoint", "disposition"):
            _require(locations["winner"][field] != locations["comparison"][field], "Reused source record")
        _require(locations["winner"]["competing_endpoint"] == 0, "Saved winner pointer is not first")
        for key, expected in _derived(row).items():
            _same(row[key], expected, "derived " + key)
    _same(contrast["source_map"], _provenance(rows), "source map")
    _require(len(_bytes(contrast)) <= MAX_JSON_BYTES, "Contrast exceeds byte limit")
    return contrast


def format_summary(contrast):
    """Format every row; reject excess bytes rather than truncate."""
    _require(contrast.get("schema_version") == CONTRAST_SCHEMA, "Wrong contrast schema")
    _same([r["frame_index"] for r in contrast["rows"]], list(FRAMES), "summary frames")
    lines = ["# Saved endpoint decision contrasts", "", "P003 representative window; TT/cap20, confidence .01, raw localization radius 10 source pixels.",
             "", "All arithmetic below is derived from saved values. Signed contrasts are winner minus comparison. Exact score equality alone marks a tie.", ""]
    for row in contrast["rows"]:
        for field, expected in _derived(row).items():
            _same(row[field], expected, "summary " + field)
        winner, comparison = row["winner"], row["comparison"]
        human = row["human_review"]
        frame = row["frame_index"]
        lines += [f"## Frame {frame}", "", f"Saved emitted candidate {winner['best_path']['endpoint'][1]}; retained localization witness {comparison['best_path']['endpoint'][1]}. Horizon {row['horizon_start']}–{row['horizon_end']}.",
                  f"Existing human judgment: {human['candidate_identity']}; center {human['ball_center']}; recorded human candidate index {human['emitted_candidate_index']!r}.",
                  f"Saved comparison raw center error: {row['comparison_report']['matched_center_error_px']!r} px. Its visual identity remains unknown.", "",
                  "| Signed contribution | Winner | Comparison | Winner minus comparison |", "| --- | ---: | ---: | ---: |"]
        for term in TERMS:
            lines.append(f"| {term.replace('_', ' ')} | {row['contributions']['winner'][term]!r} | {row['contributions']['comparison'][term]!r} | {row['term_contrasts'][term]!r} |")
        lines += ["", f"Saved scores: winner {winner['best_path']['score']!r}; comparison {comparison['best_path']['score']!r}. Pair gap {row['pair_score_gap']!r}; exact tie {row['exact_score_tie']}. Separate saved global margin {row['saved_global_score_margin']!r}.",
                  f"Saved paths: winner {winner['best_path']['path']!r}; comparison {comparison['best_path']['path']!r}.",
                  "Current-endpoint exact tie order: descending endpoint confidence, lower original candidate index, then saved path."]
        if frame == 300:
            lines.append("Frame 300 has only current confidence; history cannot explain this choice.")
        lines.append("")
    lines.extend("- " + value for value in LIMITATIONS)
    result = "\n".join(lines) + "\n"
    _require(len(result.encode("utf-8")) <= MAX_TEXT_BYTES, "Summary exceeds byte limit")
    return result

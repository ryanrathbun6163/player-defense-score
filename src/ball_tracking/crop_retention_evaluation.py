"""Score only the 24 new retention units; reuse bound reports without rescoring.

Localization outcomes remain separate from semantic identity. Structural
equivalence references never become executed or independent results.
"""
from __future__ import annotations

from collections import defaultdict
import copy
from dataclasses import replace
import json
from pathlib import Path
import uuid

from .annotations import load_annotations
from .candidate_retention_diagnostic import resolve_pointer, verify_binding
from .development_experiments import canonical_sha256, require_digest
from .evaluation import evaluate_detections
from .tiled_evaluation import COUNTS, METRICS


RADII = (5.0, 10.0, 15.0, 20.0, 30.0)
THRESHOLDS = (.01, .20, .35)
MOTION_ARMS = tuple("history_edge_{}_cost_{}".format(edge, cost)
                    for edge in ("tight", "wide") for cost in ("tight", "wide"))
CONTROL_ARMS = ("crop_raw", "crop_top_one", "crop_top_twenty", *MOTION_ARMS)
RETENTION_POLICY = "all_threshold_qualified_saved_candidates"
REPORT_SCHEMA = "ball_crop_candidate_retention_evaluation/v0.1"
WINDOW_SCHEMA = "ball_crop_candidate_retention_window_scoring/v0.1"
POOL_SCHEMA = "ball_crop_candidate_retention_pool/v0.1"
IDENTITY_FIELDS = ("possession_id", "source_video", "window", "selection_purpose",
                   "input_model_provenance", "input_candidate_content_sha256",
                   "annotation_content_sha256", "matching_rule")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _context(context, name):
    return context[name] if isinstance(context, dict) else getattr(context, name)


def _runs(values):
    result, current = [], 0
    for value in (*values, False):
        if value:
            current += 1
        elif current:
            result.append(current)
            current = 0
    return result


def _validate_selected(run, observations):
    config = observations["config"]
    _require(config["arm"] in MOTION_ARMS and config["confidence_threshold"] == .01
             and config["candidate_cap"] is None and config.get("retention_policy") == RETENTION_POLICY,
             "Only new all-candidate floor observations may be scored")
    _require(observations["input_candidate_content_sha256"] == canonical_sha256(run.to_dict()),
             "New observations use different original candidates")
    _require([f["frame_index"] for f in observations["frames"]] == [f.frame_index for f in run.frames],
             "New observation frames are incomplete or reordered")
    selected = []
    for frame, observed in zip(run.frames, observations["frames"]):
        emitted = observed["emitted_candidate_indices"]
        candidates = {d.candidate_index: d for d in frame.detections}
        _require(len(emitted) <= 1 and len(set(emitted)) == len(emitted)
                 and all(i in candidates and candidates[i].confidence >= .01 for i in emitted),
                 "Emission must be one original threshold-qualified candidate or explicit absence")
        winner = observed["ranking"]["winner"]
        endpoint = winner["endpoint"]
        expected = [endpoint[1]] if endpoint is not None and endpoint[0] == frame.frame_index else []
        _require(emitted == expected, "Emission differs from saved current endpoint")
        selected.append(replace(frame, detections=tuple(d for d in frame.detections if d.candidate_index in emitted)))
    return replace(run, frames=tuple(selected))


def evaluate_unit(labels, run, observations, radius, commit):
    """Evaluate immutable emitted originals; never run or validate a selector."""
    require_digest(commit, "retention evaluator commit", 40)
    _require(radius in RADII and not isinstance(radius, bool), "Undeclared retention radius")
    view = _validate_selected(run, observations)
    score = evaluate_detections(labels, view, confidence_threshold=.01, localization_radius_px=radius)
    emitted = sum(bool(f["emitted_candidate_indices"]) for f in observations["frames"])
    frames = score["frame_results"]
    return {
        "schema_version": REPORT_SCHEMA, "variant_id": observations["variant_id"],
        "config": copy.deepcopy(observations["config"]), "localization_radius_px": radius,
        "selection_purpose": labels.window.selection_purpose, "possession_id": run.possession_id,
        "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
        "input_model_provenance": run.model_provenance.to_dict(),
        "ranking_code_commit": observations["ranking_code_commit"], "evaluator_code_commit": commit,
        "observations_content_sha256": canonical_sha256(observations),
        "input_candidate_content_sha256": observations["input_candidate_content_sha256"],
        "annotation_content_sha256": score["annotation_content_sha256"],
        "matching_rule": "raw center distance; uncertainty diagnostic only",
        "metrics": {k: score[k] for k in METRICS}, "frame_results": frames,
        "temporal_metrics": {"emitted_frame_count": emitted, "missing_frame_count": len(frames) - emitted,
                             "frame_count": len(frames), "emitted_frame_coverage": emitted / len(frames),
                             "longest_consecutive_missed_eligible_run": max(_runs([f["false_negative_count"] == 1 for f in frames]), default=0),
                             "correct_match_run_lengths": _runs([f["matched_candidate_index"] is not None for f in frames])},
        "execution_role": "new_distinct_evaluation", "selected_operating_point": None,
        "quality_gate": None, "semantic_identity_labels_created": False,
    }


def report_key(report):
    config = report["config"]
    return (report["selection_purpose"], report["possession_id"], config["arm"],
            config["confidence_threshold"], config["candidate_cap"], report["localization_radius_px"])


def _index(reports):
    result = {}
    for report in reports:
        key = report_key(report)
        _require(key not in result, "Duplicate retention scoring cell")
        result[key] = report
    return result


def _aligned(before, after, *, same_radius=True):
    _require(all(before[k] == after[k] for k in IDENTITY_FIELDS), "Comparison mixes sources, labels, windows or pools")
    if same_radius:
        _require(before["localization_radius_px"] == after["localization_radius_px"], "Comparison changes radius")
    _require([f["frame_index"] for f in before["frame_results"]] == [f["frame_index"] for f in after["frame_results"]],
             "Comparison frame alignment differs")


def match_changes(before, after):
    _aligned(before, after)
    old = {f["frame_index"]: f for f in before["frame_results"]}
    new = {f["frame_index"]: f for f in after["frame_results"]}
    good_old = {i for i, f in old.items() if f["matched_candidate_index"] is not None}
    good_new = {i for i, f in new.items() if f["matched_candidate_index"] is not None}
    shared = [{"frame_index": i, "before_error_px": old[i]["matched_center_error_px"],
               "after_error_px": new[i]["matched_center_error_px"],
               "raw_error_delta_px": new[i]["matched_center_error_px"] - old[i]["matched_center_error_px"]}
              for i in sorted(good_old & good_new)]
    return {"newly_recovered_frames": sorted(good_new - good_old), "newly_lost_frames": sorted(good_old - good_new),
            "correct_to_wrong_frames": sorted(i for i in good_old - good_new if new[i]["accepted_detection_count"]),
            "wrong_to_correct_frames": sorted(i for i in good_new - good_old if old[i]["accepted_detection_count"]),
            "shared_match_errors": shared,
            **{name + "_delta": after["metrics"][name] - before["metrics"][name]
               for name in ("true_positive_count", "false_positive_count", "false_negative_count",
                            "duplicate_false_positive_count", "non_visible_false_alarm_count")},
            "emitted_frame_delta": after["temporal_metrics"]["emitted_frame_count"] - before["temporal_metrics"]["emitted_frame_count"]}


def loss_partition(floor, qualified, retained, selected):
    """Ordered U/F/C/S partition of misses; hidden alarms are separate."""
    for other in (qualified, retained, selected):
        _aligned(floor, other)
    matched = lambda report: {f["frame_index"] for f in report["frame_results"] if f["matched_candidate_index"] is not None}
    available, filtered, capped, chosen = map(matched, (floor, qualified, retained, selected))
    _require(chosen <= capped <= filtered <= available, "Selected matches exceed bound candidate availability")
    unavailable = {f["frame_index"] for f in floor["frame_results"] if f["false_negative_count"]}
    parts = {"U_no_candidate_at_export_floor": unavailable, "F_confidence_filter_loss": available - filtered,
             "C_candidate_cap_loss": filtered - capped, "S_path_choice_loss": capped - chosen}
    misses = {f["frame_index"] for f in selected["frame_results"] if f["false_negative_count"]}
    _require(set.union(*parts.values()) == misses and sum(map(len, parts.values())) == len(misses)
             and len(misses) == selected["metrics"]["false_negative_count"], "U/F/C/S misses do not reconcile")
    return {"parts": {k: sorted(v) for k, v in parts.items()}, "total_missed_eligible_frames": len(misses),
            "false_observations_on_eligible_frames": [f["frame_index"] for f in selected["frame_results"]
                                                     if f["scoring_status"] == "localization_eligible" and f["false_positive_count"]],
            "hidden_alarm_frames": [f["frame_index"] for f in selected["frame_results"] if f["non_visible_false_alarm_count"]],
            "candidate_burden_is_tracker_accuracy": False, "semantic_training_labels_created": False}


def observation_changes(before, after):
    """Attribute changed winners using saved original paths, never reranking."""
    _require([f["frame_index"] for f in before["frames"]] == [f["frame_index"] for f in after["frames"]],
             "Paired observation frames differ")
    retained = {f["frame_index"]: {d["candidate_index"] for d in f["candidate_decisions"]
                                  if d["disposition"] in ("emitted", "eligible_not_emitted")}
                for f in before["frames"]}
    rows = []
    for old, new in zip(before["frames"], after["frames"]):
        old_rank, new_rank = old["ranking"], new["ranking"]
        a, b = old_rank["winner"], new_rank["winner"]
        added = [node for node in b["path"] if node[1] not in retained[node[0]]]
        current_added = [node for node in added if node[0] == new["frame_index"]]
        historical_added = [node for node in added if node[0] < new["frame_index"]]
        changed = old["emitted_candidate_indices"] != new["emitted_candidate_indices"]
        rows.append({"frame_index": new["frame_index"], "changed_emission": changed,
                     "changed_endpoint": a["endpoint"] != b["endpoint"], "changed_path": a["path"] != b["path"],
                     "before_original_indices": old["emitted_candidate_indices"], "after_original_indices": new["emitted_candidate_indices"],
                     "newly_abstained": bool(old["emitted_candidate_indices"]) and not new["emitted_candidate_indices"],
                     "newly_emitted": bool(new["emitted_candidate_indices"]) and not old["emitted_candidate_indices"],
                     "before_winner": copy.deepcopy(a), "after_winner": copy.deepcopy(b),
                     "before_score_margin": old_rank["score_margin"], "after_score_margin": new_rank["score_margin"],
                     "newly_admitted_current_nodes": current_added, "newly_admitted_historical_nodes": historical_added,
                     "changed_to_new_current_candidate": changed and bool(current_added),
                     "changed_to_previously_retained_candidate_via_new_history": changed and bool(new["emitted_candidate_indices"])
                         and not current_added and bool(historical_added),
                     "before_path_evidence": copy.deepcopy(old_rank.get("best_path_for_winner", old_rank.get("best_path_per_endpoint"))),
                     "after_path_evidence": copy.deepcopy(new_rank.get("best_path_for_winner", new_rank.get("best_path_per_endpoint"))),
                     "before_competing_evidence": copy.deepcopy(old_rank.get("current_alternatives", old_rank.get("competing_endpoints"))),
                     "after_competing_evidence": copy.deepcopy(new_rank.get("current_alternatives", new_rank.get("competing_endpoints"))),
                     "full_trace_binding": copy.deepcopy(new.get("full_trace_binding", new.get("trace_binding"))),
                     "score_improvement_is_accuracy_improvement": False})
    return rows


def _load_reference(root, record, documents, aggregate=False):
    source = record["source"]
    key = (source["path"], source["sha256"])
    if key not in documents:
        documents[key] = json.loads(verify_binding(Path(root), source).read_text(encoding="utf-8"))
    value = resolve_pointer(documents[key], source["json_pointer"])
    digest_field = "aggregate_content_sha256" if aggregate else "report_content_sha256"
    _require(canonical_sha256(value) == record[digest_field], "Saved report content binding differs")
    _require(value["config"] == record["config"] and value["selection_purpose"] == record["purpose"]
             and value["localization_radius_px"] == record["localization_radius_px"], "Saved report identity differs")
    _require(value["ranking_code_commit"] == record["original_selection_commit"]
             and value["evaluator_code_commit"] == record["original_evaluation_commit"], "Saved provenance was relabeled")
    if not aggregate:
        _require(value["observations_content_sha256"] == record["observations_content_sha256"], "Saved report/observation contract differs")
    return copy.deepcopy(value)


def load_saved_pool(root, proposal, purpose):
    """Read exact approved JSON pointers; no selector/evaluator calls."""
    documents = {}
    refs = [r for r in proposal["saved_report_references"] if r["purpose"] == purpose]
    aggregate_refs = [r for r in proposal["saved_aggregate_references"] if r["purpose"] == purpose]
    _require(len(refs) == 315 and len(aggregate_refs) == 105, "Incomplete frozen saved pool")
    reports = [_load_reference(root, r, documents) for r in refs]
    aggregates = [_load_reference(root, r, documents, True) for r in aggregate_refs]
    _require(len(_index(reports)) == 315, "Duplicate saved window reports")
    keys = {(a["selection_purpose"], a["config"]["arm"], a["config"]["confidence_threshold"], a["localization_radius_px"]) for a in aggregates}
    _require(len(keys) == 105, "Duplicate saved aggregates")
    return {"evaluation_reports": reports, "aggregate_results": aggregates,
            "saved_report_references": refs, "saved_aggregate_references": aggregate_refs}


def _publish(path, payload):
    path = Path(path)
    complete = {**payload, "content_sha256": canonical_sha256(payload)}
    if path.exists():
        _require(json.loads(path.read_text(encoding="utf-8")) == complete, "Refusing changed scoring checkpoint")
        return complete
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".incomplete-" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(complete, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    _require(not path.exists(), "Refusing concurrent scoring checkpoint replacement")
    temporary.rename(path)
    return complete


def _read_published(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = document.pop("content_sha256")
    _require(canonical_sha256(document) == digest, "Scoring checkpoint content hash mismatch")
    return {**document, "content_sha256": digest}


def _window_path(root, context, window_id, target_dir=None):
    if target_dir is None:
        output_root = _context(context, "manifest").get("output_root", _context(context, "proposal")["proposed_output_root"])
        target_dir = Path(root) / output_root / "evaluation" / "windows"
    _require(Path(window_id).name == window_id, "Invalid scoring window identifier")
    return Path(target_dir) / (window_id + ".json")


def load_window_score(root, context, window_id, target_dir=None):
    payload = _read_published(_window_path(root, context, window_id, target_dir))
    _require(payload["schema_version"] == WINDOW_SCHEMA and payload["window_id"] == window_id
             and payload["experiment_spec_sha256"] == _context(context, "spec_sha256")
             and payload["code_commit"] == _context(context, "commit"), "Scoring checkpoint belongs to a different experiment")
    _require(len(payload["evaluation_reports"]) == 125 and len(payload["saved_report_references"]) == 105
             and len(payload["equivalence_report_references"]) == 40, "Incomplete scoring window")
    _index(payload["evaluation_reports"])
    proposal = _context(context, "proposal")
    expected = [r for r in proposal["saved_report_references"] if r["window_id"] == window_id]
    _require(payload["saved_report_references"] == expected, "Scoring checkpoint changed saved references")
    documents = {}
    original = {_key_without_cap(r): r for r in payload["evaluation_reports"] if r["schema_version"] != REPORT_SCHEMA}
    for reference in expected:
        saved = _load_reference(root, reference, documents)
        _require(original.get(_key_without_cap(saved)) == saved, "Copied saved report was changed")
    for binding in {r["observations_file"]["path"]: r["observations_file"] for r in expected}.values():
        verify_binding(Path(root), binding)
    window = next(w for w in proposal["windows"] if w["window_id"] == window_id)
    label = next(r for r in proposal["scoring_labels"] if r["window_id"] == window_id)
    _require(payload["annotation_binding"] == label["annotation"] and payload["crop_input_binding"] == window["crop_candidates"],
             "Scoring checkpoint changed its input bindings")
    verify_binding(Path(root), label["annotation"])
    verify_binding(Path(root), window["crop_candidates"])
    return payload


def _key_without_cap(report):
    return (report["config"]["arm"], report["config"]["confidence_threshold"], report["localization_radius_px"])


def _case_tags(root, proposal, window_id, run):
    result = {str(f.frame_index): [] for f in run.frames}
    contract = proposal.get("case_tags")
    if contract is None:
        return result
    ledger = json.loads(verify_binding(Path(root), contract["source"]).read_text(encoding="utf-8"))
    focused = set(contract["focused_identity_localization_cases"])
    for frame in ledger["frames"]:
        saved = frame["saved_frame"]
        if saved["window_id"] != window_id:
            continue
        tags = [saved["cohort_role"]]
        if saved["id"] in focused:
            tags.append("focused_identity_localization_question")
        cap = frame.get("cap_record")
        if cap and cap["saved_record"]["saved_top_twenty_frame_result"]["matched_candidate_index"] is None:
            tags.append("saved_floor_cap_loss_case")
        result[str(saved["frame_index"])] = tags
    return result


def retention_measurements(run, before, after):
    rows = []
    for source, old, new in zip(run.frames, before["frames"], after["frames"]):
        retained = lambda frame: sum(d["disposition"] in ("emitted", "eligible_not_emitted") for d in frame["candidate_decisions"])
        old_count, new_count = retained(old), retained(new)
        _require(new_count >= old_count, "All-candidate retained count decreased")
        rows.append({"frame_index": source.frame_index, "stored_candidate_count": len(source.detections),
                     "confidence_qualified_count": sum(d.confidence >= .01 for d in source.detections),
                     "saved_cap20_retained_count": old_count, "all_retained_count": new_count,
                     "newly_admitted_candidate_count": new_count - old_count,
                     "new_graph_audit_counts": copy.deepcopy(new.get("audit_counts")),
                     "new_full_trace_binding": copy.deepcopy(new.get("trace_binding", new.get("full_trace_binding")))})
    return rows


def _comparisons(reports, observations):
    index = _index(reports)
    exemplar = reports[0]
    purpose, possession = exemplar["selection_purpose"], exemplar["possession_id"]
    get = lambda arm, confidence, cap, radius: index[(purpose, possession, arm, confidence, cap, radius)]
    cap_pairs, confidence_pairs, parts = [], [], []
    for arm in MOTION_ARMS:
        for radius in RADII:
            before, after = get(arm, .01, 20, radius), get(arm, .01, None, radius)
            cap_pairs.append({"arm": arm, "confidence_threshold": .01, "radius_px": radius,
                              "status": "new_distinct_comparison", "comparison": "cap20_to_all_same_confidence",
                              "before_ranking_commit": before["ranking_code_commit"], "after_ranking_commit": after["ranking_code_commit"],
                              **match_changes(before, after), "frame_observation_changes": observation_changes(observations[(arm, .01, 20)], observations[(arm, .01, None)])})
            for confidence in (.20, .35):
                high = get(arm, confidence, 20, radius)
                cap_pairs.append({"arm": arm, "confidence_threshold": confidence, "radius_px": radius,
                                  "status": "structural_equivalence_not_executed", "comparison": "cap20_to_all_same_confidence",
                                  "original_config": high["config"], **match_changes(high, high)})
                for policy, floor in (("cap20", before), ("all", after)):
                    confidence_pairs.append({"arm": arm, "retention_policy": policy, "from_confidence": .01,
                                             "to_confidence": confidence, "radius_px": radius,
                                             "higher_all_role": "structural_equivalence_not_executed" if policy == "all" else "saved_executed",
                                             "before_config": floor["config"], "after_original_config": high["config"], **match_changes(floor, high)})
            for confidence in THRESHOLDS:
                floor = get("crop_raw", .01, None, radius)
                qualified = get("crop_raw", confidence, None, radius)
                for policy in ("cap20", "all"):
                    retained = get("crop_top_twenty", confidence, 20, radius) if policy == "cap20" else qualified
                    selected = get(arm, confidence, None if policy == "all" and confidence == .01 else 20, radius)
                    parts.append({"arm": arm, "confidence_threshold": confidence, "retention_policy": policy,
                                  "radius_px": radius, "selection_execution_role": "structural_equivalence_not_executed"
                                  if policy == "all" and confidence != .01 else "new_distinct" if policy == "all" else "saved",
                                  **loss_partition(floor, qualified, retained, selected)})
    return cap_pairs, confidence_pairs, parts


def score_window(root, context, window_id, target_dir):
    from . import crop_retention_experiment as experiment
    root = Path(root)
    proposal = _context(context, "proposal")
    target = _window_path(root, context, window_id, target_dir)
    if target.exists():
        payload = load_window_score(root, context, window_id, target_dir)
        # Resume binds the completed new observations without executing selection
        # or scoring again. A missing/different source is never silently reused.
        for unit in proposal["new_selection_units"]:
            if unit["window_id"] != window_id:
                continue
            obs = experiment.load_new_observations(root, context, unit)
            rows = [r for r in payload["evaluation_reports"] if r["schema_version"] == REPORT_SCHEMA and r["config"]["arm"] == unit["config"]["arm"]]
            _require(len(rows) == 5 and all(r["observations_content_sha256"] == canonical_sha256(obs) for r in rows),
                     "Completed scoring checkpoint has different new observations")
        return payload
    window = next(w for w in proposal["windows"] if w["window_id"] == window_id)
    run, _ = _context(context, "inputs")[window_id]
    label_record = next(r for r in proposal["scoring_labels"] if r["window_id"] == window_id)
    labels = load_annotations(verify_binding(root, label_record["annotation"]))
    _require(labels.window.selection_purpose == window["purpose"] and labels.annotation_set_id == window["annotation_set_id"],
             "Scoring annotation identity differs")
    documents = {}
    saved_refs = [r for r in proposal["saved_report_references"] if r["window_id"] == window_id]
    _require(len(saved_refs) == 105, "Expected105 saved reports per window")
    reports = [_load_reference(root, r, documents) for r in saved_refs]
    observations = {}
    controls = [r for r in proposal["saved_control_outputs"] if r["window_id"] == window_id]
    _require(len(controls) == 21, "Expected21 saved observation controls per window")
    for record in controls:
        obs = experiment.load_saved_control(root, record, run=run)
        c = obs["config"]
        observations[(c["arm"], c["confidence_threshold"], c["candidate_cap"])] = obs
    for report in reports:
        c = report["config"]
        obs = observations[(c["arm"], c["confidence_threshold"], c["candidate_cap"])]
        _require(canonical_sha256(obs) == report["observations_content_sha256"], "Saved report/observation content mismatch")
    units = [u for u in proposal["new_selection_units"] if u["window_id"] == window_id]
    _require(len(units) == 4, "Expected four new selection units per window")
    for unit in units:
        obs = experiment.load_new_observations(root, context, unit)
        c = obs["config"]
        observations[(c["arm"], c["confidence_threshold"], None)] = obs
        reports.extend(evaluate_unit(labels, run, obs, radius, _context(context, "commit")) for radius in RADII)
    aliases = []
    for equivalence in proposal["higher_confidence_structural_equivalence"]:
        if equivalence["window_id"] != window_id:
            continue
        proof = [{"frame_index": f.frame_index, "qualified_candidate_count": sum(d.confidence >= equivalence["confidence_threshold"] for d in f.detections)} for f in run.frames]
        _require(proof == equivalence["per_frame_count_proof"] and max(p["qualified_candidate_count"] for p in proof) <= 20,
                 "Higher-confidence structural equivalence is not proven")
        for reference in equivalence["original_reports"]:
            _load_reference(root, reference, documents)
            aliases.append({"window_id": window_id, "purpose": window["purpose"], "arm": equivalence["arm"],
                            "confidence_threshold": equivalence["confidence_threshold"],
                            "localization_radius_px": reference["localization_radius_px"],
                            "status": "structural_equivalence_not_executed", "new_selection_or_scoring_executed": False,
                            "original_report_reference": copy.deepcopy(reference)})
    _require(len(reports) == 125 and len(aliases) == 40, "Incomplete window scoring and equivalence counts")
    cap_pairs, confidence_pairs, parts = _comparisons(reports, observations)
    measurements = [{"arm": arm, "confidence_threshold": .01,
                     "frames": retention_measurements(run, observations[(arm, .01, 20)], observations[(arm, .01, None)])}
                    for arm in MOTION_ARMS]
    payload = {"schema_version": WINDOW_SCHEMA, "window_id": window_id, "purpose": window["purpose"],
               "experiment_spec_sha256": _context(context, "spec_sha256"), "code_commit": _context(context, "commit"),
               "annotation_binding": label_record["annotation"], "crop_input_binding": window["crop_candidates"],
               "evaluation_reports": reports, "saved_report_references": saved_refs,
               "equivalence_report_references": aliases, "paired_cap_differences": cap_pairs,
               "confidence_differences": confidence_pairs, "loss_decomposition": parts,
               "retention_measurements": measurements, "case_tags_by_frame": _case_tags(root, proposal, window_id, run),
               "counts": {"new_reports": 20, "saved_reports": 105, "equivalence_references": 40},
               "selected_method": None, "selected_operating_point": None, "quality_gate": None,
               "semantic_training_labels_created": False, "independent_trials_claimed": False}
    for source in {r["source"]["path"]: r["source"] for r in saved_refs}.values():
        verify_binding(root, source)
    verify_binding(root, label_record["annotation"])
    return _publish(target, payload)


def aggregate_new_reports(reports):
    _require(len(reports) == 3 and len({r["possession_id"] for r in reports}) == 3, "Expected three distinct windows in one pool")
    first = reports[0]
    fields = ("config", "variant_id", "localization_radius_px", "selection_purpose", "input_model_provenance", "ranking_code_commit", "evaluator_code_commit")
    _require(all(r["schema_version"] == REPORT_SCHEMA and all(r[k] == first[k] for k in fields) for r in reports),
             "New aggregate mixes settings, pools or provenance")
    metrics = {key: sum(r["metrics"][key] for r in reports) for key in COUNTS}
    tp, fp, fn = (metrics[k] for k in ("true_positive_count", "false_positive_count", "false_negative_count"))
    metrics.update(precision=tp / (tp + fp) if tp + fp else None, recall=tp / (tp + fn) if tp + fn else None)
    return {**{key: copy.deepcopy(first[key]) for key in fields}, "metrics": metrics, "window_count": 3,
            "per_window": [{"possession_id": r["possession_id"], "window": r["window"], "metrics": r["metrics"], "temporal_metrics": r["temporal_metrics"]} for r in reports],
            "execution_role": "new_distinct_aggregate", "selected_operating_point": None, "quality_gate": None}


def deduplicate_aggregate_aliases(equivalences, purpose):
    by_key = {}
    for equivalence in equivalences:
        if equivalence["purpose"] != purpose:
            continue
        for reference in equivalence["original_aggregates"]:
            c = reference["config"]
            key = (purpose, c["arm"], c["confidence_threshold"], reference["localization_radius_px"])
            if key not in by_key:
                by_key[key] = {"purpose": purpose, "config": copy.deepcopy(c), "localization_radius_px": reference["localization_radius_px"],
                               "status": "structural_equivalence_not_executed", "new_selection_or_scoring_executed": False,
                               "original_aggregate_reference": copy.deepcopy(reference), "referencing_windows": []}
            _require(by_key[key]["original_aggregate_reference"] == reference, "Conflicting aggregate alias reference")
            _require(equivalence["window_id"] not in by_key[key]["referencing_windows"], "Duplicate aggregate alias for one window")
            by_key[key]["referencing_windows"].append(equivalence["window_id"])
    _require(len(by_key) == 40 and all(len(r["referencing_windows"]) == 3 for r in by_key.values()),
             "Expected40 unique aggregate aliases, each referenced by three windows")
    return list(by_key.values())


def finalize(root, context, window_artifacts, target_dir):
    """Combine six verified window artifacts; never evaluate an old result."""
    proposal = _context(context, "proposal")
    payloads = []
    for item in window_artifacts:
        payload = _read_published(item) if isinstance(item, (str, Path)) else item
        check = {k: v for k, v in payload.items() if k != "content_sha256"}
        _require(canonical_sha256(check) == payload["content_sha256"], "Changed window artifact")
        _require(payload["experiment_spec_sha256"] == _context(context, "spec_sha256")
                 and payload["code_commit"] == _context(context, "commit"), "Mixed scoring checkpoint provenance")
        payloads.append(payload)
    _require(len(payloads) == 6 and {p["window_id"] for p in payloads} == {w["window_id"] for w in proposal["windows"]},
             "Final scoring requires all six distinct windows")
    outputs = []
    for purpose in proposal["pool_separation"]:
        windows = [p for p in payloads if p["purpose"] == purpose]
        _require(len(windows) == 3, "Representative and challenge pools must stay separate")
        saved = load_saved_pool(root, proposal, purpose)
        new_reports = [r for p in windows for r in p["evaluation_reports"] if r["schema_version"] == REPORT_SCHEMA]
        _require(len(new_reports) == 60, "Expected60 new reports per pool")
        groups = defaultdict(list)
        for report in new_reports:
            groups[(report["config"]["arm"], report["localization_radius_px"])].append(report)
        _require(len(groups) == 20, "Expected20 distinct new aggregate cells")
        new_aggregates = [aggregate_new_reports(group) for group in groups.values()]
        aliases = deduplicate_aggregate_aliases(proposal["higher_confidence_structural_equivalence"], purpose)
        documents = {}
        for alias in aliases:
            _load_reference(root, alias["original_aggregate_reference"], documents, True)
        saved_by_key = {(r["config"]["arm"], r["config"]["confidence_threshold"], r["localization_radius_px"]): r for r in saved["aggregate_results"]}
        cap_differences = []
        for after in new_aggregates:
            before = saved_by_key[(after["config"]["arm"], .01, after["localization_radius_px"])]
            cap_differences.append({"config": after["config"], "original_control_config": before["config"],
                                    "localization_radius_px": after["localization_radius_px"],
                                    **{key + "_delta": after["metrics"][key] - before["metrics"][key] for key in COUNTS}})
        payload = {"schema_version": POOL_SCHEMA, "purpose": purpose, "code_commit": _context(context, "commit"),
                   "experiment_spec_sha256": _context(context, "spec_sha256"),
                   "evaluation_reports": [*saved["evaluation_reports"], *new_reports],
                   "aggregate_results": [*saved["aggregate_results"], *new_aggregates],
                   "saved_report_references": saved["saved_report_references"], "saved_aggregate_references": saved["saved_aggregate_references"],
                   "equivalence_report_references": [r for p in windows for r in p["equivalence_report_references"]],
                   "equivalence_aggregate_references": aliases, "aggregate_cap_differences": cap_differences,
                   "paired_cap_differences": [r for p in windows for r in p["paired_cap_differences"]],
                   "confidence_differences": [r for p in windows for r in p["confidence_differences"]],
                   "loss_decomposition": [r for p in windows for r in p["loss_decomposition"]],
                   "retention_measurements": [{"window_id": p["window_id"], "measurements": p["retention_measurements"]} for p in windows],
                   "case_tags_by_window": {p["window_id"]: p["case_tags_by_frame"] for p in windows},
                   "counts": {"saved_reports": 315, "new_reports": 60, "distinct_reports": 375,
                              "equivalence_report_references": 120, "saved_aggregates": 105, "new_aggregates": 20,
                              "distinct_aggregates": 125, "equivalence_aggregate_references": 40},
                   "selected_method": None, "selected_operating_point": None, "quality_gate": None,
                   "semantic_training_labels_created": False, "independent_trials_claimed": False}
        target = Path(target_dir) / (purpose + ".json")
        _publish(target, payload)
        outputs.append(str(target))
    return {"pool_paths": outputs, "new_reports": 120, "reused_saved_reports": 630,
            "distinct_reports": 750, "equivalence_report_references": 240,
            "new_aggregate_cells_per_pool": 20, "distinct_aggregate_cells_per_pool": 125,
            "equivalence_aggregate_references_per_pool": 40}

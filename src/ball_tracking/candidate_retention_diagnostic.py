"""Create a bounded ledger from saved evidence; never execute a selector or model.

Only standard-library JSON/file operations and three descriptive residual
calculations are used. Saved localization outcomes are not identity labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess


class DiagnosticError(ValueError):
    """A saved binding or the bounded authorization could not be verified."""


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(condition, message):
    if not condition:
        raise DiagnosticError(message)


def _path(root, relative):
    name = PurePosixPath(str(relative).replace("\\", "/"))
    _require(not name.is_absolute() and ".." not in name.parts and ":" not in str(name),
             f"Expected repository-relative path: {relative}")
    result = (root / Path(*name.parts)).resolve()
    _require(result.is_relative_to(root.resolve()), f"Path escapes repository: {relative}")
    return result


def _reject_holdout_path(relative):
    # These exact window tokens are metadata only; no bound file inside them is read.
    for possession, start, end in ((1, 300, 324), (2, 200, 224), (3, 250, 274)):
        token = f"possession_{possession:03d}_frames_{start:04d}_{end:04d}"
        _require(token not in str(relative), f"Sealed holdout content prohibited: {relative}")


def verify_binding(root, binding):
    _reject_holdout_path(binding["path"])
    path = _path(root, binding["path"])
    _require(path.is_file(), f"Missing bound file: {binding['path']}")
    _require(_sha256(path) == binding["sha256"], f"SHA-256 mismatch: {binding['path']}")
    return path


def resolve_pointer(document, pointer):
    if pointer == "":
        return document
    _require(isinstance(pointer, str) and pointer.startswith("/"), "Invalid JSON pointer")
    value = document
    try:
        for token in pointer[1:].split("/"):
            _require(not re.search(r"~(?![01])", token), "Invalid JSON pointer escape")
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                _require(token == "0" or (token.isdigit() and not token.startswith("0")),
                         "Invalid JSON array index")
                value = value[int(token)]
            else:
                value = value[token]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise DiagnosticError(f"Unresolved JSON pointer: {pointer}") from exc
    return value


def reference_residual(detection, annotation):
    """Do not subtract uncertainty, rematch, revise geometry, or infer identity."""
    geometry = annotation.get("geometry")
    result = {"dx": None, "dy": None, "reference_distance_px": None,
              "reference_geometry": copy.deepcopy(geometry), "reason": None}
    if (annotation.get("visibility") == "not_visible" or not annotation.get("localization_eligible")
            or geometry is None):
        result["reason"] = "hidden_or_no_eligible_reference_geometry"
        return result
    center, reference = detection.get("center_xy_px"), geometry.get("center_xy_px")
    _require(all(isinstance(p, (list, tuple)) and len(p) == 2 for p in (center, reference)),
             "Eligible geometry requires two saved center coordinates")
    _require(all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                 for p in (center, reference) for v in p), "Nonfinite center coordinate")
    dx, dy = center[0] - reference[0], center[1] - reference[1]
    result.update(dx=dx, dy=dy, reference_distance_px=math.hypot(dx, dy))
    return result


def candidate_key(frame, candidate):
    return (candidate["input_candidates"]["sha256"], candidate["detector"],
            frame["window_id"], frame["frame_index"], candidate["detection"]["candidate_index"])


def verify_candidate_mapping(frame, candidate, raw_document):
    pointer = candidate["source_candidate_pointer"]
    raw = resolve_pointer(raw_document, pointer)
    _require(raw["detection"] == candidate["detection"], "Original candidate mapping mismatch")
    source_frame = resolve_pointer(raw_document, pointer.rsplit("/candidates/", 1)[0])
    _require(source_frame["frame_index"] == frame["frame_index"], "Candidate frame mismatch")
    matches = [c for c in source_frame["candidates"]
               if c["detection"]["candidate_index"] == candidate["detection"]["candidate_index"]]
    _require(len(matches) == 1 and matches[0] == raw, "Ambiguous original candidate index")
    return raw


def retention_state(disposition, *, content_verified=True, arm=None):
    if not content_verified:
        return "unknown"
    if disposition == "outside_selector_cap" and arm in ("yolo_top_one", "crop_top_one"):
        return "retained_but_not_emitted"
    states = {"below_threshold": "confidence_rejected",
              "outside_selector_cap": "saved_cap_rejected",
              "outside_top_twenty": "saved_cap_rejected",
              "capped": "saved_cap_rejected", "emitted": "emitted",
              "eligible_not_emitted": "retained_but_not_emitted"}
    _require(disposition in states, f"Unknown saved disposition: {disposition}")
    return states[disposition]


def validate_scope(proposal, inspection, cap_diagnosis):
    scope = proposal["scope"]
    frames = inspection["frames"]
    candidates = [c for f in frames for c in f["candidates"]]
    outcomes = [o for f in frames for o in f["display_outcomes"]]
    counts = {"frame_count": len(frames), "candidate_count": len(candidates),
              "display_outcome_count": len(outcomes),
              "saved_cap_record_count": len(cap_diagnosis["records"])}
    _require(counts == {"frame_count": 32, "candidate_count": 82,
                       "display_outcome_count": 640, "saved_cap_record_count": 15},
             "Expected exact 32/82/640/15 saved scope")
    _require(all(scope[k] == v for k, v in counts.items()), "Proposal count mismatch")
    _require(len({f["id"] for f in frames}) == len(frames), "Duplicate frame")
    keys = ("id", "cohort_role", "possession_id", "purpose", "frame_index", "window_id")
    actual = [{k: f[k] for k in keys} for f in frames]
    _require(actual == scope["frames"], "Frame cohort or order changed")
    ids = [c["id"] for c in candidates]
    _require(ids == scope["candidate_ids"] and len(set(ids)) == len(ids),
             "Candidate catalog or order changed")
    identities = [candidate_key(f, c) for f in frames for c in f["candidates"]]
    _require(len(set(identities)) == len(identities), "Duplicate candidate identity")
    cap_ids = [c["frame_id"] for c in cap_diagnosis["records"]]
    _require(len(set(cap_ids)) == 15 and set(cap_ids) <= {f["id"] for f in frames},
             "Invalid cap-record cohort")
    for f in frames:
        setting_ids = {(o["detector"], o["arm"], o["confidence_threshold"])
                       for o in f["display_outcomes"]}
        _require(len(setting_ids) == 20 and len(f["display_outcomes"]) == 20,
                 "Duplicate or missing saved display setting")
    return counts


def verify_approval(root, proposal_path, proposal, approval):
    _require(approval.get("schema_version") == "ball_candidate_retention_localization_approval/v0.1",
             "Missing diagnostic approval schema")
    _require(bool(approval.get("approved_by")) and bool(approval.get("statement")),
             "An attributed approval statement is required")
    for key in ("diagnostic_implementation_authorized", "diagnostic_execution_authorized"):
        _require(approval.get(key) is True, f"Approval required: {key}")
    for key in ("new_tracking_experiment_authorized", "training_authorized", "git_mutations_authorized"):
        _require(approval.get(key) is False, f"Approval exceeds bounded diagnostic: {key}")
    bound = verify_binding(root, approval["proposal"])
    _require(bound == proposal_path.resolve(), "Approval binds a different proposal")
    _require(approval["design_document"] == proposal["design_document"], "Design approval mismatch")
    verify_binding(root, approval["design_document"])


def create_output_directory(root, output_dir, output_root):
    base = _path(root, output_root)
    target = output_dir.resolve() if output_dir.is_absolute() else (root / output_dir).resolve()
    _require(target != base and target.is_relative_to(base), "Output must be a fresh versioned child")
    _require(not target.exists(), "Refusing existing output destination")
    target.mkdir(parents=True, exist_ok=False)
    return target


class _Evidence:
    def __init__(self, root):
        self.root = root
        self.bindings = {}
        self.documents = {}
        self.pointers = []

    def bind(self, binding):
        name, digest = binding["path"], binding["sha256"]
        if name in self.bindings:
            _require(self.bindings[name] == digest, f"Conflicting binding: {name}")
            return _path(self.root, name)
        path = verify_binding(self.root, binding)
        self.bindings[name] = digest
        return path

    def document(self, binding):
        path = self.bind(binding)
        if binding["path"] not in self.documents:
            self.documents[binding["path"]] = json.loads(path.read_text(encoding="utf-8"))
        return self.documents[binding["path"]]

    def pointer(self, binding, expected=None):
        value = resolve_pointer(self.document(binding), binding["json_pointer"])
        if expected is not None:
            _require(value == expected, f"Saved payload differs at {binding}")
        self.pointers.append(dict(binding))
        return value

    def preserve(self):
        for name, digest in self.bindings.items():
            verify_binding(self.root, {"path": name, "sha256": digest})


def _report(evidence, source, frame):
    result = evidence.pointer(source)
    _require(result["frame_index"] == frame["frame_index"], "Saved report frame mismatch")
    parent = source["json_pointer"].rsplit("/frame_results/", 1)[0]
    report = resolve_pointer(evidence.document(source), parent)
    _require(report["possession_id"] == frame["possession_id"], "Saved report possession mismatch")
    _require(report["selection_purpose"] == frame["purpose"], "Saved report pool mismatch")
    _require(report["localization_radius_px"] == 10, "Report outside frozen radius")
    return result, report


def _trace(evidence, source, frame, report, candidates_binding):
    wrapper = evidence.document(source)
    observations = wrapper["observations"]
    _require(canonical_sha256(observations) == report["observations_content_sha256"],
             "Saved observations content contract mismatch")
    _require(observations["config"] == report["config"]
             and observations["variant_id"] == report["variant_id"], "Selector/report setting mismatch")
    _require(observations["possession_id"] == frame["possession_id"], "Selector possession mismatch")
    input_binding = wrapper.get("input_crop_file", wrapper.get("input_candidates"))
    _require(input_binding == candidates_binding, "Selector original candidate namespace mismatch")
    _require(observations["input_candidate_content_sha256"] == report["input_candidate_content_sha256"],
             "Selector/report candidate content mismatch")
    trace = evidence.pointer(source)
    _require(trace["frame_index"] == frame["frame_index"], "Selector frame mismatch")
    raw = evidence.document(candidates_binding)
    wrapper_digest = wrapper.get("crop_content_sha256", wrapper.get("candidate_content_sha256"))
    _require(wrapper_digest == raw["content_sha256"], "Selector/raw candidate content binding mismatch")
    raw_frame = next(f for f in raw["frames"] if f["frame_index"] == frame["frame_index"])
    original_indices = [c["detection"]["candidate_index"] for c in raw_frame["candidates"]]
    decision_indices = [c["candidate_index"] for c in trace["candidate_decisions"]]
    _require(decision_indices == original_indices, "Selector decisions lost original candidate mapping")
    emitted = [c["candidate_index"] for c in trace["candidate_decisions"] if c["disposition"] == "emitted"]
    _require(emitted == trace["emitted_candidate_indices"], "Selector emission mapping mismatch")
    return trace


def _cap_membership(evidence, record, frame):
    result, report = _report(evidence, record["source"], frame)
    _require(result == record["saved_top_twenty_frame_result"], "Saved cap result mismatch")
    _require(report["config"]["confidence_threshold"] == .01
             and report["config"]["candidate_cap"] == 20, "Cap report setting mismatch")
    aggregate = evidence.document(record["source"])
    matches = [b for b in aggregate.get("saved_control_outputs", [])
               if Path(b["path"]).name == report["variant_id"] + ".json"
               and frame["window_id"] in PurePosixPath(b["path"]).parts]
    detail = {"membership": "unknown", "reason": None, "observations_source": None,
              "original_candidate_index": record["raw_floor_match_candidate_index"],
              "saved_disposition": None, "content_contract_verified": False}
    if len(matches) != 1:
        detail["reason"] = "No unique saved selector binding for this report/window"
        return detail
    bound = matches[0]
    if not _path(evidence.root, bound["path"]).is_file():
        detail["reason"] = "Saved selector file unavailable; membership unknown"
        return detail
    # Missing evidence can remain unknown; contradictory evidence must fail.
    try:
        wrapper = evidence.document(bound)
        offsets = [i for i, f in enumerate(wrapper["observations"]["frames"])
                   if f["frame_index"] == frame["frame_index"]]
        _require(len(offsets) == 1, "No unique saved selector frame")
        source = {**bound, "json_pointer": f"/observations/frames/{offsets[0]}"}
        candidates_binding = next(c["input_candidates"] for c in frame["candidates"] if c["detector"] == "RF")
        trace = _trace(evidence, source, frame, report, candidates_binding)
        decisions = [d for d in trace["candidate_decisions"]
                     if d["candidate_index"] == record["raw_floor_match_candidate_index"]]
        _require(len(decisions) == 1, "Missing original cap candidate decision")
        state = retention_state(decisions[0]["disposition"])
        _require(state in ("saved_cap_rejected", "emitted"), "Unexpected floor/top-twenty disposition")
        detail.update(membership="saved_cap_retained" if state == "emitted" else state,
                      observations_source=source, saved_disposition=decisions[0]["disposition"],
                      content_contract_verified=True)
    except (KeyError, StopIteration) as exc:
        detail["reason"] = str(exc)
    return detail


def _finding_passages(evidence, binding):
    lines = evidence.bind(binding).read_text(encoding="utf-8").splitlines()
    passages = []
    start = None
    for offset, line in enumerate(lines + ["## End"]):
        if re.match(r"[1-5]\. \*\*", line) or (start is not None and line.startswith("## ")):
            if start is not None:
                end = offset
                while end > start and not lines[end-1].strip():
                    end -= 1
                passages.append({"evidence_type": "agent_observation", "source": dict(binding),
                                 "start_line": start+1, "end_line": end,
                                 "passage": "\n".join(lines[start:end])})
            start = offset if re.match(r"[1-5]\. \*\*", line) else None
    _require(len(passages) == 5, "Completed findings passages changed")
    return passages


def _identity(candidate, findings_binding, focused_binding):
    # Shared prose remains shared; do not distribute broad findings as new individual verdicts.
    return {"certified_candidate_identity": None, "training_eligible": False,
            "agent_observation": None,
            "existing_observation_reference": dict(findings_binding),
            "focused_plate": focused_binding,
            "unresolved_question": "Candidate identity remains uncertified; localization status is not a semantic label.",
            "attribution_limit": "Read the preserved findings passages in their original scope; no new per-candidate judgment."}


def _git(root, *arguments):
    result = subprocess.run(["git", "-C", str(root), *arguments], check=True,
                            capture_output=True, text=True)
    return result.stdout.rstrip("\r\n")


def _checkpoint(root):
    return {"branch": _git(root, "branch", "--show-current"),
            "head": _git(root, "rev-parse", "HEAD"),
            "worktree_status": _git(root, "status", "--short"),
            "index_empty": not bool(_git(root, "diff", "--cached", "--name-only"))}


def _embargoes(root, proposal):
    paths = proposal["boundaries"]["original_nine_embargo_paths"]
    _require(len(paths) == 9 and len(set(paths)) == 9, "Expected nine original embargo paths")
    for path in paths:
        _require(not _path(root, path).exists(), f"Embargoed prediction exists: {path}")
    return [{"path": path, "absent": True} for path in paths]


def _summary(ledger):
    frames = ledger["frames"]
    rows = ["# Saved candidate-retention and localization diagnostic", "",
            "This ledger describes immutable saved evidence. It creates no predictions, scores, identity labels or selected method.", "",
            "The fixed cohort has 32 source frames, 82 catalog candidates, 640 saved display outcomes and 15 saved cap records. Repeated settings are not independent samples.", "",
            "| Pool / cohort | Unique frames | Eligible reference centers | Candidates | Saved emissions / outcomes |",
            "| --- | ---: | ---: | ---: | ---: |"]
    groups = defaultdict(list)
    for frame in frames:
        groups[(frame["saved_frame"]["purpose"], frame["saved_frame"]["cohort_role"])].append(frame)
    for (pool, role), items in sorted(groups.items()):
        outcomes = [o for f in items for o in f["display_outcomes"]]
        rows.append(f"| {pool} / {role} | {len(items)} | "
                    f"{sum(f['saved_frame']['annotation']['localization_eligible'] for f in items)} | "
                    f"{sum(len(f['candidates']) for f in items)} | "
                    f"{sum(bool(o['saved_display_outcome']['emitted_candidate_indices']) for o in outcomes)} / {len(outcomes)} |")
    rows += ["", "| Mechanism | Saved evidence | Interpretation / limit |", "| --- | --- | --- |",
             "| Confidence retention | 15 of 20 persistent display misses have an RF floor match; all 15 are below .20 and .35. | The other five lack a saved qualifying center; this does not prove their boxes contain no ball pixels. |",
             "| Candidate cap | At the separate .01/top-twenty setting, eight of those 15 still miss; seven retain a match. | These eight are not additive losses at .20/.35. Membership is resolved only when the saved content contract verifies. |",
             "| Object identity | Existing agent observations describe seating, glare, limb/footwear and ball-region alternatives. | All 82 certified identities remain null and training eligibility false. No new visual judgment is claimed. |",
             "| Center placement | Raw dx/dy/distance appear only with an eligible reference center; uncertainty remains separate. | Unmatched saved errors remain null. Amodal references and accidental geometric matches leave semantic ambiguity. |", "",
             "Candidate-load, false-positive, duplicate and hidden-alarm counts are copied with every floor/cap/display frame result in the ledger. The summary does not turn these availability references into tracker accuracy.", "",
             "Contrary cases remain explicit: P002 representative 262#0 versus #2 (surviving ball-region/seating alternatives), P001 challenge 200-201 and P002 representative 262-264 (flight), P003 challenge 165-169 (hidden), and 170/171/173/174 (reacquisition). No hidden coordinate is created.", "",
             "The focused center questions remain P001 representative 51#0 and 59#0, P002 representative 257#4 and P003 challenge 164#0. Existing fragment/ball-hand observations do not decide whether the center discrepancy comes from box extent, occlusion or reference uncertainty.", "",
             "Before a later retention comparison, establish useful pixel support and state candidate-load/false-alarm/missingness tradeoffs. Before a ranking comparison, show the useful alternative survives preprocessing and inspect the saved path/cost trace. Before a localization study, distinguish ball-region identity from center discrepancy. Any later proposal must expose gains and regressions across all six development windows with pools separate. Training requires a separate reviewed identity-semantics and leakage-aware design.", "",
             "Reuse the completed [native gallery](../../weak_candidate_inspection/9fe6a1ef86d2/review_native.html). No repeat twelve-clip approval or new blanket identity review is requested.", "",
             "All nine prediction embargoes remain absent; three holdouts remain sealed. No method, operating point or quality gate is selected. No model, selector, evaluator, renderer, media decoder or training call occurred.", ""]
    return "\n".join(rows)


def write_ledger_files(target, ledger):
    """Write only new ledger/summary files; integrity is finalized by the caller."""
    for name, contents in (("case_ledger.json", json.dumps(ledger, indent=2, ensure_ascii=False, allow_nan=False) + "\n"),
                           ("summary.md", _summary(ledger))):
        with (target / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(contents)


def build_ledger_frames(inspection, cap, evidence, by_name, completion):
    """Join verified saved pointers; caller separately enforces the fixed cohort."""
    asset_by_path = {a["path"]: a for a in completion["assets"]}
    cap_by_frame = {c["frame_id"]: c for c in cap["records"]}
    ledger_frames = []
    for frame_offset, frame in enumerate(inspection["frames"]):
        inspection_source = {**by_name["inspection.json"], "json_pointer": f"/frames/{frame_offset}"}
        evidence.pointer(inspection_source, frame)
        annotation = evidence.document(frame["annotation_binding"])
        offsets = [i for i, a in enumerate(annotation["annotations"]) if a["frame_index"] == frame["frame_index"]]
        _require(len(offsets) == 1, "Missing reviewed annotation frame")
        annotation_source = {**frame["annotation_binding"], "json_pointer": f"/annotations/{offsets[0]}"}
        evidence.pointer(annotation_source, frame["annotation"])
        floor = {}
        for detector, outcome in frame["saved_floor_outcomes"].items():
            result, report = _report(evidence, outcome["source"], frame)
            _require(result == outcome["saved_frame_result"] and report["config"]["confidence_threshold"] == .01,
                     "Floor report differs from saved inspection")
            floor[detector] = copy.deepcopy(outcome)
        display = []
        traces = {}
        for outcome in frame["display_outcomes"]:
            result, report = _report(evidence, outcome["report_source"], frame)
            detector = outcome["detector"]
            candidates_binding = next((c["input_candidates"] for c in frame["candidates"] if c["detector"] == detector), None)
            # Even an all-abstaining detector has a bound input in its saved selector envelope.
            if candidates_binding is None:
                wrapper = evidence.document(outcome["observations_source"])
                candidates_binding = wrapper.get("input_crop_file", wrapper.get("input_candidates"))
            trace = _trace(evidence, outcome["observations_source"], frame, report, candidates_binding)
            _require(trace["emitted_candidate_indices"] == outcome["emitted_candidate_indices"], "Saved emission changed")
            _require(report["config"]["confidence_threshold"] == outcome["confidence_threshold"], "Display confidence mismatch")
            _require(report["config"]["arm"] == outcome["arm"], "Display arm mismatch")
            matched = result["matched_candidate_index"]
            emitted = trace["emitted_candidate_indices"]
            _require(matched is None or matched in emitted, "Matched index is not an emitted original index")
            _require(result["accepted_detection_count"] == len(emitted), "Report/emission count mismatch")
            saved_outcome = ("matched" if matched is not None else "hidden_alarm"
                             if result["non_visible_false_alarm_count"] else "unmatched" if emitted else "missing")
            _require(outcome["saved_outcome"] == saved_outcome, "Saved outcome/report mismatch")
            setting = (detector, outcome["arm"], outcome["confidence_threshold"])
            traces[setting] = trace
            display.append({"saved_display_outcome": copy.deepcopy(outcome), "saved_frame_result": result,
                            "saved_setting": report["config"],
                            "saved_trace_context": {k: copy.deepcopy(v) for k, v in trace.items() if k != "candidate_decisions"},
                            "saved_decision_counts": dict(Counter(d["disposition"] for d in trace["candidate_decisions"])),
                            "candidate_namespace": candidates_binding})
        cap_record = cap_by_frame.get(frame["id"])
        cap_detail = _cap_membership(evidence, cap_record, frame) if cap_record else None
        candidate_records = []
        for candidate in frame["candidates"]:
            raw_document = evidence.document(candidate["input_candidates"])
            raw = verify_candidate_mapping(frame, candidate, raw_document)
            evidence.pointer({**candidate["input_candidates"], "json_pointer": candidate["source_candidate_pointer"]}, raw)
            source_frame = resolve_pointer(raw_document, candidate["source_candidate_pointer"].rsplit("/candidates/", 1)[0])
            view = next(v for v in source_frame["views"] if v["view"]["ordinal"] == raw["view_ordinal"])
            local_candidates = view["candidates"] if candidate["detector"] == "RF" else view["prediction"]["candidates"]
            local = next(c for c in local_candidates if c["candidate_index"] == raw["local_candidate_index"])
            provenance = candidate["crop_provenance"]
            _require(view["view"] == provenance["view"] and local == provenance["local_candidate"], "Crop mapping changed")
            rectangle = view["view"]["xyxy_half_open_px"]
            _require(all(math.isclose(local["center_xy_px"][axis] + rectangle[axis],
                                      candidate["detection"]["center_xy_px"][axis], rel_tol=0, abs_tol=1e-9)
                         for axis in (0, 1)), "Local-to-source center mapping changed")
            if candidate["detector"] == "RF":
                actual_commit = raw_document["header"]["per_view_model_provenance"]["code_commit"]
            else:
                unit = next(u for u in raw_document["header"]["inference_units"]
                            if u["frame_index"] == frame["frame_index"] and u["view_ordinal"] == raw["view_ordinal"])
                _require(unit == provenance["inference_unit"], "Actual inference unit changed")
                actual_commit = unit["actual_inference_commit"]
            _require(actual_commit == provenance["actual_inference_commit"], "Actual inference commit changed")
            settings = []
            for outcome in frame["display_outcomes"]:
                if outcome["detector"] != candidate["detector"]:
                    continue
                setting = (outcome["detector"], outcome["arm"], outcome["confidence_threshold"])
                decisions = [d for d in traces[setting]["candidate_decisions"]
                             if d["candidate_index"] == candidate["detection"]["candidate_index"]]
                _require(len(decisions) == 1, "Missing original display candidate decision")
                settings.append({"arm": outcome["arm"], "confidence_threshold": outcome["confidence_threshold"],
                                 "state": retention_state(decisions[0]["disposition"], arm=outcome["arm"]),
                                 "interpretation": "Top-one alternatives reflect final choice, not a preprocessing top-twenty loss"
                                 if outcome["arm"] in ("yolo_top_one", "crop_top_one") else "Saved preprocessing and choice disposition",
                                 "saved_decision": decisions[0], "source": outcome["observations_source"]})
            focused_path = str(PurePosixPath(by_name["inspection.json"]["path"]).parent / "focus" / (frame["id"] + ".png"))
            saved_floor_index = floor[candidate["detector"]]["saved_frame_result"]["matched_candidate_index"]
            candidate_records.append({"saved_candidate": copy.deepcopy(candidate),
                                      "identity_key": list(candidate_key(frame, candidate)),
                                      "retention": {"saved_floor_selected_match": saved_floor_index == candidate["detection"]["candidate_index"],
                                                    "floor_report": floor[candidate["detector"]],
                                                    "display_settings": settings,
                                                    "top_twenty_at_0_01": cap_detail if cap_record and candidate["detector"] == "RF" and candidate["detection"]["candidate_index"] == cap_record["raw_floor_match_candidate_index"] else {"membership": "not_applicable", "reason": "Not the frozen cap-record candidate"}},
                                      "identity": _identity(candidate, by_name["findings.md"], asset_by_path.get(focused_path)),
                                      "localization": reference_residual(candidate["detection"], frame["annotation"])})
        ledger_frames.append({"inspection_source": inspection_source,
                              "saved_frame": {k: copy.deepcopy(v) for k, v in frame.items() if k not in ("candidates", "display_outcomes")},
                              "annotation_source": annotation_source, "candidates": candidate_records,
                              "display_outcomes": display,
                              "cap_record": {"saved_record": cap_record, "resolved_membership": cap_detail} if cap_record else None})
    return ledger_frames


def _reconcile_ledger(ledger_frames, proposal):
    candidates = [c for f in ledger_frames for c in f["candidates"]]
    outcomes = [o for f in ledger_frames for o in f["display_outcomes"]]
    weak = []
    no_floor = []
    for frame in ledger_frames:
        saved = frame["saved_frame"]
        if saved["cohort_role"] != "persistent_miss":
            continue
        index = saved["saved_floor_outcomes"]["RF"]["saved_frame_result"]["matched_candidate_index"]
        if index is None:
            no_floor.append(saved["id"])
        else:
            candidate = next(c for c in frame["candidates"] if c["saved_candidate"]["detector"] == "RF"
                             and c["saved_candidate"]["detection"]["candidate_index"] == index)
            _require(candidate["saved_candidate"]["detection"]["confidence"] < .2
                     and all(s["state"] == "confidence_rejected" for s in candidate["retention"]["display_settings"]),
                     "Persistent floor match is not consistently confidence-rejected")
            weak.append(saved["id"])
    caps = [f["cap_record"] for f in ledger_frames if f["cap_record"]]
    missed_caps = [c["saved_record"]["frame_id"] for c in caps
                   if c["saved_record"]["saved_top_twenty_frame_result"]["matched_candidate_index"] is None]
    _require(len(weak) == 15 and len(no_floor) == 5, "Persistent floor-match partition changed")
    _require(len(missed_caps) == 8, "Expected eight separate saved cap-loss frames")
    _require(set(missed_caps) == set(proposal["scope"]["fixed_cap_loss_frame_ids"]), "Saved cap-loss cohort changed")
    _require({c["saved_record"]["frame_id"] for c in caps} == set(weak), "Cap records do not cover weak matches")
    for cap in caps:
        membership = cap["resolved_membership"]["membership"]
        if membership != "unknown":
            missed = cap["saved_record"]["frame_id"] in missed_caps
            _require((membership == "saved_cap_rejected") == missed, "Cap report and original membership conflict")
    candidate_settings = sum(len(c["retention"]["display_settings"]) for c in candidates)
    _require(candidate_settings == 1060, "Expected 1,060 same-detector candidate-setting records")
    hidden = [c for f in ledger_frames if f["saved_frame"]["annotation"]["visibility"] == "not_visible" for c in f["candidates"]]
    _require(len(hidden) == 5 and all(all(c["localization"][k] is None for k in ("dx", "dy", "reference_distance_px")) for c in hidden),
             "Hidden-frame residuals must remain null")
    _require(sum(bool(o["saved_display_outcome"]["emitted_candidate_indices"]) for o in outcomes) == 410,
             "Expected 410 saved emissions and 230 abstentions")
    eligible_count = sum(f["saved_frame"]["annotation"]["localization_eligible"] for f in ledger_frames)
    _require(eligible_count == 27, "Expected 27 eligible reference centers")
    return {"same_detector_candidate_setting_records": candidate_settings,
            "persistent_confidence_loss_frame_ids": weak, "persistent_no_rf_floor_match_frame_ids": no_floor,
            "separate_0_01_cap_loss_frame_ids": missed_caps,
            "cap_membership_states": dict(Counter(c["resolved_membership"]["membership"] for c in caps)),
            "hidden_candidate_null_residual_records": len(hidden), "eligible_reference_frames": eligible_count,
            "saved_emissions": 410, "saved_abstentions": 230}


def run_diagnostic(proposal_path, approval_path, output_dir, *, root=None):
    root = Path(root or Path(__file__).resolve().parents[2]).resolve()
    proposal_path = Path(proposal_path)
    if not proposal_path.is_absolute():
        proposal_path = root / proposal_path
    approval_path = Path(approval_path)
    if not approval_path.is_absolute():
        approval_path = root / approval_path
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    verify_approval(root, proposal_path, proposal, approval)
    _require(proposal["schema_version"] == "candidate_retention_localization_diagnostic_proposal/v0.1",
             "Unsupported diagnostic proposal")
    state = _checkpoint(root)
    expected = proposal["preparation_checkpoint"]
    _require(state["branch"] == expected["branch"] and state["head"] == expected["head"],
             "Diagnostic checkpoint differs from approved preparation checkpoint")
    _require(state["index_empty"], "Diagnostic requires an empty index")
    implementation = Path(__file__).resolve()
    helper_paths = [implementation]
    tests = root / "tests/test_ball_candidate_retention_diagnostic.py"
    if tests.is_file():
        helper_paths.append(tests)
    helper_hashes = [{"path": p.relative_to(root).as_posix(), "sha256": _sha256(p)} for p in helper_paths]
    embargoes = _embargoes(root, proposal)
    evidence = _Evidence(root)
    evidence.bind(approval["proposal"])
    evidence.bind(approval["design_document"])
    evidence.bind({"path": approval_path.relative_to(root).as_posix(), "sha256": _sha256(approval_path)})
    for binding in proposal["evidence_bindings"]:
        evidence.bind(binding)
    by_name = {Path(b["path"]).name: b for b in proposal["evidence_bindings"]}
    completion = evidence.document(by_name["completion.json"])
    inspection = evidence.document(by_name["inspection.json"])
    cap = evidence.document(by_name["saved_cap_diagnosis.json"])
    _require(len(completion["assets"]) == 231 and len(inspection["input_bindings"]) == 177,
             "Original asset/input inventory count changed")
    for binding in [*completion["assets"], *inspection["input_bindings"]]:
        evidence.bind(binding)
    counts = validate_scope(proposal, inspection, cap)
    findings = _finding_passages(evidence, by_name["findings.md"])
    ledger_frames = build_ledger_frames(inspection, cap, evidence, by_name, completion)
    reconciliation = _reconcile_ledger(ledger_frames, proposal)
    ledger = {"schema_version": "ball_candidate_retention_localization_ledger/v0.1",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "proposal": approval["proposal"], "approval": {"path": approval_path.relative_to(root).as_posix(), "sha256": _sha256(approval_path)},
              "counts": counts, "reconciliation": reconciliation, "frames": ledger_frames, "existing_agent_findings": findings,
              "original_cap_diagnosis": cap, "selected_method": None, "selected_operating_point": None,
              "quality_gate": None, "new_human_identity_labels": False, "training_eligible": False,
              "limitations": ["Descriptive arithmetic only, no rematching", "Uncertainty is separate from raw distance",
                              "Selected cohort and repeated settings are not independent evaluation samples",
                              "Shared findings are not distributed as invented per-candidate identity verdicts"]}
    evidence.preserve()
    _embargoes(root, proposal)
    for binding in helper_hashes:
        verify_binding(root, binding)
    final_state = _checkpoint(root)
    _require(final_state == state, "Git checkpoint changed during diagnostic assembly")
    output = Path(output_dir)
    relative = (output if output.is_absolute() else root / output).resolve().relative_to(root).as_posix()
    _require(bool(_git(root, "check-ignore", "--", relative + "/case_ledger.json")), "Output must be ignored by Git")
    target = create_output_directory(root, output, proposal["proposed_outputs"]["root"])
    write_ledger_files(target, ledger)
    evidence.preserve()
    for binding in helper_hashes:
        verify_binding(root, binding)
    _require(_checkpoint(root) == state, "Git checkpoint changed during diagnostic output")
    integrity = {"schema_version": "ball_candidate_retention_localization_integrity/v0.1",
                 "creation_checkpoint": state, "final_checkpoint": final_state,
                 "implementation_source_hashes": helper_hashes,
                 "implementation_commit_role": "Creation HEAD; dirty implementation bytes separately hashed, never inference provenance",
                 "counts": counts, "reconciliation": reconciliation, "original_asset_count": 231, "original_input_count": 177,
                 "verified_bindings": [{"path": p, "sha256": h} for p, h in sorted(evidence.bindings.items())],
                 "resolved_json_pointers": evidence.pointers, "prior_bound_bytes_unchanged": True,
                 "embargoes": _embargoes(root, proposal), "sealed_holdout_contents_accessed": False,
                 "model_selector_evaluator_renderer_or_media_decode_executed": False,
                 "outputs": [{"path": (target / n).relative_to(root).as_posix(), "sha256": _sha256(target / n)}
                             for n in ("case_ledger.json", "summary.md")]}
    with (target / "integrity.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(integrity, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return {"output_dir": str(target), "counts": counts,
            "integrity_sha256": _sha256(target / "integrity.json")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run_diagnostic(args.proposal, args.approval, args.output_dir), indent=2))


if __name__ == "__main__":
    main()

"""Validate one frozen unreceipted publication; never render or score again."""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from . import crop_retention_experiment as original
from . import crop_retention_recovery as scoring_recovery
from . import crop_retention_render_recovery as rendering
from . import crop_retention_review as review
from . import crop_retention_evaluation as scoring
from .crop_retention_resources import BudgetJournal, run_supervised, wait_for_supervisor
from .development_experiments import canonical_sha256, read_json, safe_path

RENDER_COMMIT = "cd51bfc1336bba76e4b118b6cfe55d7f74a3b5a6"
RENDER_SPEC = "326ba1cec475aa32d172a76a2ea760ceffb3e9188631c16ed2b1af5914fab3cd"
RENDER_MANIFEST_SHA = "72f15b1d43750b00b49d0bd83c3e8ab0c4351064aeadad582008429580c00fcf"
PROPOSAL_SHA = "d2280805d52b9b2a5bc3e675f77ca16491793b62f3983987aa5ce7a5110ad8b8"
APPROVAL_SHA = "891eaf3d0837c8aa5e92e23d5cfc1fe537497cdb7f24354cd9931f3608c9c735"
PRESERVATION_SHA = "a400911f83b7408c6f9c5ddabf5eae47f704d9f73fed16f538ac135fc04d2106"
CHECKPOINT_SHA = "ae72b7d729e342dd5123c49e27d027315cf18e9ccd29280210dfd1d81d74d356"
PREFIX_COUNT = 2644
PREFIX_TIP = "1287e985661c4b76ba3a680e299f916bd01977268547a7b550df84199bb48ecc"
FAILED_RENDER = "e3ea5536e59d4cdc8fea72d45bc53241"
KNOWN_FAILURES = {"e1ba648def3f4e1f887332e850396e4c", "158f51be5ab34cdface57f4e0036b7d2", FAILED_RENDER}
SIXTH_WINDOW = "possession_003_frames_0150_0174_challenge_evaluation_development_v0_2"
SIXTH_MANIFEST_SHA = "5665beabdbdcf7da2c3ad70f11a90095e14f251bf0c9ffe8bd284fcac2eaa29e"
RECOVERY_ID = "rfdetr_medium_crop_candidate_retention_publication_recovery_v0_1"
MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/" + RECOVERY_ID + ".json"
OUTPUT_ROOT = original.OUTPUT_ROOT
PERMITTED_STAGES = ["verify", "recover"]
OUTPUTS = {"accept": "audit/publication_acceptance_cd51.json", "review-final": "review/manifest.json",
           "completion-audit": "audit/independent_publication_recovery_audit.json",
           "presentation": "audit/publication_recovery_review_guide.md"}
HELPERS = {"completion-audit": "audit/independent_publication_recovery_audit.py",
           "presentation": "audit/publication_recovery_review_guide.py"}
MANIFEST_FIELDS = {"schema_version", "recovery_id", "rendering_manifest", "publication_proposal", "authorization",
                   "preservation_audit", "resource_checkpoint", "implementation_validation", "output_root",
                   "permitted_stages", "selected_method", "selected_operating_point", "quality_gate"}
_require = original._require
verify_binding = original.verify_binding
file_binding = original.file_binding


def _pair(binding):
    return {k: binding[k] for k in ("path", "sha256")}


def _published(path):
    value = read_json(path)
    _require(value.get("content_sha256") == canonical_sha256({k: v for k, v in value.items() if k != "content_sha256"}),
             "Published recovery content hash differs")
    return value


def _files(root, folder):
    result = set()
    def fail(error):
        raise error
    for current, dirs, names in os.walk(folder, onerror=fail):
        for name in dirs + names:
            path = safe_path(root, (Path(current) / name).relative_to(root).as_posix())
            if name in names:
                _require(path.is_file(), "Nonregular recovery evidence")
                result.add(path.relative_to(root).as_posix())
    return result


def _absent(path):
    _require(not os.path.lexists(path), "Create-only recovery destination already exists: " + str(path))


def _validate_implementation(root, manifest):
    binding = manifest["implementation_validation"]
    _require(isinstance(binding, dict), "Publication recovery implementation validation is missing")
    certificate = read_json(verify_binding(root, binding))
    for flag in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                 "publication_failure_boundary_tests_passed"):
        _require(certificate.get(flag) is True, "Publication recovery validation is incomplete")
    for field in ("publication_proposal", "preservation_audit", "resource_checkpoint", "rendering_manifest", "authorization"):
        _require(certificate[field + "_sha256"] == manifest[field]["sha256"], "Validation belongs to another authority")
    required = {p.relative_to(root).as_posix() for folder in ("src", "tests") for p in (root / folder).rglob("*.py")}
    required.add("requirements.txt")
    bindings = certificate["source_bindings"]
    rendering._pairs(bindings)
    _require(required <= {b["path"] for b in bindings}, "Validation omits source dependencies or tests")
    helper_paths = {OUTPUT_ROOT + "/" + p for p in HELPERS.values()} | {OUTPUT_ROOT + "/audit/independent_render_recovery_audit.py"}
    rendering._pairs(certificate["helper_bindings"])
    _require(helper_paths == {b["path"] for b in certificate["helper_bindings"]}, "Unreviewed helper source")
    for b in bindings + certificate["helper_bindings"] + certificate["evidence_bindings"]:
        verify_binding(root, b)
    for name in required:
        original._git(root, "ls-files", "--error-unmatch", "--", name)
    return certificate


def _metadata(root, manifest_path, require_clean):
    """Only authorities, source certificates and resource/preservation metadata."""
    root, path = Path(root).resolve(), Path(manifest_path).resolve()
    commit = original._clean_checkpoint(root) if require_clean else original._git(root, "rev-parse", "HEAD")
    _require(path == root / MANIFEST_PATH, "Unexpected publication recovery manifest path")
    safe_path(root, path.relative_to(root).as_posix())
    manifest = read_json(path)
    _require(set(manifest) == MANIFEST_FIELDS
             and manifest["schema_version"] == "ball_crop_candidate_retention_publication_recovery/v0.1"
             and manifest["recovery_id"] == RECOVERY_ID and manifest["output_root"] == OUTPUT_ROOT
             and manifest["permitted_stages"] == PERMITTED_STAGES, "Unsupported publication recovery scope")
    _require(all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Recovery cannot select a method, operating point or quality gate")
    for field, digest in (("rendering_manifest", RENDER_MANIFEST_SHA), ("publication_proposal", PROPOSAL_SHA),
                          ("preservation_audit", PRESERVATION_SHA), ("resource_checkpoint", CHECKPOINT_SHA)):
        _require(manifest[field]["sha256"] == digest, "Publication authority differs from approved snapshot")
        verify_binding(root, manifest[field])
    _require(manifest["rendering_manifest"]["content_sha256"] == RENDER_SPEC, "Wrong original rendering specification")
    _require(manifest["authorization"]["sha256"] == APPROVAL_SHA, "Exact approved amendment changed")
    approval = read_json(verify_binding(root, manifest["authorization"]))
    _require(approval["schema_version"] == "ball_crop_candidate_retention_publication_recovery_approval/v0.1"
             and approval["proposal"] == manifest["publication_proposal"] and approval["approved_by"] == "ryan"
             and approval["implementation_authorized"] is True and approval["execution_authorized"] is True
             and approval["training_authorized"] is False and approval["git_mutations_authorized"] is False,
             "Exact publication recovery approval is missing")
    verify_binding(root, approval["original_approved_proposal"])
    old = rendering._metadata(root, root / manifest["rendering_manifest"]["path"], False)
    _require(old["spec_sha256"] == RENDER_SPEC, "Rendering specification changed")
    old["commit"] = RENDER_COMMIT
    # Existing source certificates remain immutable. The old broad required-file
    # inventory predates this new module; the new certificate covers the superset.
    prior_certificate = read_json(verify_binding(root, old["manifest"]["implementation_validation"]))
    for b in prior_certificate["source_bindings"] + prior_certificate["evidence_bindings"]:
        verify_binding(root, b)
    checkpoint = _published(verify_binding(root, manifest["resource_checkpoint"]))
    preservation = _published(verify_binding(root, manifest["preservation_audit"]))
    _require(checkpoint["commit"] == RENDER_COMMIT and checkpoint["spec_sha256"] == RENDER_SPEC
             and checkpoint["resource_event_count"] == PREFIX_COUNT and checkpoint["completed_attempts"] == 50
             and checkpoint["successful_attempts"] == 47 and checkpoint["failed_attempts"] == 3
             and checkpoint["sixth_window_adopted"] is False and checkpoint["comparison_audit_complete"] is False,
             "Incomplete preservation checkpoint")
    _require(_pair(checkpoint["preservation_audit"]) == manifest["preservation_audit"]
             and preservation["status"] == "preservation_verified_comparison_incomplete"
             and preservation["sixth_window_adopted"] is False and preservation["comparison_complete"] is False,
             "Preservation does not authorize acceptance")
    _require(checkpoint["resource_limits"] == old["proposal"]["resource_limits"], "Original budget cannot change")
    windows = preservation["review_windows"]
    _require(len(windows) == 6 and [w["window_id"] for w in windows] == [w["window_id"] for w in old["proposal"]["windows"]]
             and all(w["historical_success_binding_verified"] is (i < 5) for i, w in enumerate(windows))
             and windows[-1]["window_id"] == SIXTH_WINDOW and windows[-1]["manifest"]["sha256"] == SIXTH_MANIFEST_SHA
             and windows[-1]["failed_render_attempt_id"] == FAILED_RENDER, "Only the exact sixth publication is eligible")
    if require_clean:
        _validate_implementation(root, manifest)
        _require(subprocess.run(["git", "merge-base", "--is-ancestor", RENDER_COMMIT, "HEAD"], cwd=root).returncode == 0,
                 "Recovery must descend from the rendering checkpoint")
        for name in (MANIFEST_PATH, manifest["publication_proposal"]["path"], manifest["authorization"]["path"]):
            original._git(root, "ls-files", "--error-unmatch", "--", name)
    return {**old, "root": root, "manifest_path": path, "manifest": manifest, "approval": approval,
            "render_context": old, "checkpoint": checkpoint, "preservation": preservation,
            "commit": commit, "spec_sha256": canonical_sha256(manifest)}


def _expected_artifacts(context, stage, key):
    if stage in ("preflight", "verify"):
        _require(key in ("", *PERMITTED_STAGES), "Unknown verification role")
        return set()
    _require(stage in OUTPUTS and key == "", "Rendering, selection, scoring and unknown roles are forbidden")
    return {(context["output_root"] / OUTPUTS[stage]).relative_to(context["root"]).as_posix()}


def verify_history(root, context):
    root, output = Path(root).resolve(), context["output_root"]
    prefix = context["checkpoint"]["journal_prefix"]
    journal = BudgetJournal(output, context["proposal"]["resource_limits"])
    _require(len(prefix["events"]) == PREFIX_COUNT and len(journal.events) >= PREFIX_COUNT
             and prefix["chain_tip_sha256"] == PREFIX_TIP and journal.events[PREFIX_COUNT - 1]["sha256"] == PREFIX_TIP,
             "Frozen publication resource prefix changed")
    for i, b in enumerate(prefix["events"]):
        _require(verify_binding(root, b) == output / "resource_events" / f"{i:08d}.json", "Noncontiguous frozen journal")
    frozen = journal.events[:PREFIX_COUNT]
    starts = {e["attempt_id"]: e for e in frozen if e["kind"] == "started"}
    ends = {e["attempt_id"]: e for e in frozen if e["kind"] == "finished"}
    rows = prefix["attempts"]
    _require(len(rows) == len(starts) == len(ends) == 50
             and {r["attempt_id"] for r in rows} == set(starts) == set(ends)
             and {aid for aid, e in ends.items() if not e["success"]} == KNOWN_FAILURES,
             "Exact fifty-attempt, three-failure history required")
    for row in rows:
        aid = row["attempt_id"]
        start, end = starts[aid], ends[aid]
        _require(row["unit_key"] == start["unit_key"] and row["success"] is end["success"]
                 and row["completion_event_sha256"] == end["sha256"], "Historical attempt role changed")
        rendering._verify_seal(root, output, row["reservation"], aid, ".reservation.json", start)
        rendering._verify_seal(root, output, row["completion"], aid, ".completion.json", end)
        if not end["success"]:
            _require(row["worker_result"] is None and end["worker_result"] is None
                     and not (output / "attempts" / (aid + ".result.json")).exists(), "Failed attempt was backfilled")
        else:
            _require(row["worker_result"] is not None and end["worker_result"] is not None
                     and _pair(row["worker_result"]) == scoring_recovery._root_binding(root, output, end["worker_result"]),
                     "Historical success receipt changed")
            verify_binding(root, row["worker_result"])
    _require(math.isclose(sum(e["elapsed_seconds"] for e in ends.values()),
                          context["checkpoint"]["cumulative_active_seconds"], rel_tol=0, abs_tol=1e-7),
             "Historical active time changed")
    active = os.environ.get("BALL_RETENTION_ATTEMPT_ID")
    for aid, attempt in journal._attempts().items():
        if aid in starts:
            continue
        start, end = attempt["start"], attempt["finished"]
        bits = start["unit_key"].split(":")
        _require(len(bits) == 3 and bits[0] == "publication-recovery", "Unknown post-checkpoint worker")
        _require(start["selection_unit"] is False, "Recovery is not a selection unit")
        _expected_artifacts(context, bits[1], bits[2])
        reservation = output / "attempts" / (aid + ".reservation.json")
        _require(read_json(reservation) == {"event_sha256": start["sha256"]}, "New reservation seal differs")
        if end is None:
            _require(aid == active, "Unfinished worker requires investigation")
        else:
            _require(end["success"] is True and end["exit_code"] == 0 and end["worker_result"] is not None,
                     "New publication recovery failure requires investigation; no retry")
            _require(end["worker_result"]["path"] == "attempts/" + aid + ".result.json",
                     "Completion must bind its own worker receipt")
            _require(read_json(output / "attempts" / (aid + ".completion.json")) == {"event_sha256": end["sha256"]},
                     "New completion seal differs")
    elapsed = context["checkpoint"]["cumulative_active_seconds"]
    live, finished_stages = None, set()
    dependencies = {"review-final": "accept", "completion-audit": "review-final", "presentation": "completion-audit"}
    for event in journal.events[PREFIX_COUNT:]:
        if event["kind"] == "started":
            _require(live is None, "Overlapping recovery worker trees are forbidden")
            action = event["unit_key"].split(":")[1]
            _require(action not in dependencies or dependencies[action] in finished_stages,
                     "Dependent worker started before successful prerequisite completion")
            _require(math.isclose(event["reserved_seconds"], context["proposal"]["resource_limits"]["maximum_cumulative_seconds"] - elapsed,
                                  rel_tol=0, abs_tol=1e-7), "New worker reset or changed remaining allowance")
            live = event
        elif event["kind"] == "finished":
            _require(live is not None and event["attempt_id"] == live["attempt_id"], "Unowned recovery completion")
            limits = context["proposal"]["resource_limits"]
            _require(event["time_budget_seconds"] == live["reserved_seconds"] and event["elapsed_seconds"] <= live["reserved_seconds"]
                     and all(event[k] == 0 for k in ("time_overshoot_seconds", "memory_overshoot_bytes", "output_overshoot_bytes"))
                     and event["final_accounting_error"] is None and event["failure"] is None
                     and event["maximum_monitor_interval_seconds"] <= 1
                     and event["peak_worker_memory_bytes"] <= limits["maximum_worker_memory_bytes"]
                     and event["maximum_output_bytes"] <= event["final_accounting_output_bound_bytes"]
                     and event["final_accounting_output_bound_bytes"] <= limits["maximum_total_new_output_bytes"]
                     and event["minimum_free_disk_bytes"] >= limits["minimum_free_disk_bytes"],
                     "New completion violated unchanged resource rules")
            elapsed += event["elapsed_seconds"]
            finished_stages.add(live["unit_key"].split(":")[1])
            live = None
    return journal


def completed_records(root, context):
    root, output = Path(root).resolve(), context["output_root"]
    journal = verify_history(root, context)
    attempts = journal._attempts()
    records = {}
    previous_stage = {"review-final": "accept", "completion-audit": "review-final", "presentation": "completion-audit"}
    for event in journal.events[PREFIX_COUNT:]:
        if event["kind"] != "finished":
            continue
        b = scoring_recovery._root_binding(root, output, event["worker_result"])
        value = read_json(verify_binding(root, b))
        stage, key = value["stage"], value["key"]
        _require(value["commit"] == context["commit"] and value["spec_sha256"] == context["spec_sha256"]
                 and attempts[event["attempt_id"]]["start"]["unit_key"] == "publication-recovery:" + stage + ":" + key,
                 "New worker provenance differs")
        expected = _expected_artifacts(context, stage, key)
        _require(len(value["artifacts"]) == len(expected) and {r["path"] for r in value["artifacts"]} == expected,
                 "New receipt has missing or unapproved artifacts")
        for artifact in value["artifacts"]:
            verify_binding(root, artifact)
        if stage in OUTPUTS:
            _require(stage not in records and (stage not in previous_stage or previous_stage[stage] in records),
                     "Duplicate or out-of-order recovery receipt")
            records[stage] = {"attempt_id": event["attempt_id"], "result": value, "worker_result": b, "completion": event}
    return records


def _verify_preserved_inputs(root, context):
    """Rehash immutable inputs even after this worker writes its new result."""
    p = context["preservation"]
    old = p["preserved_old_evidence"]
    for key, count in (("completed_selection_manifests", 24), ("completed_trace_bindings", 600),
                       ("completed_scoring_artifacts", 8), ("partial_review_files", 10)):
        _require(len(old[key]) == count, "Incomplete preserved evidence")
    for value in old.values():
        for b in (value if isinstance(value, list) else [value]):
            path = verify_binding(root, b)
            _require("size_bytes" not in b or path.stat().st_size == b["size_bytes"], "Preserved byte size changed")
    for b in p["preserved_input_bindings"]:
        verify_binding(root, b)
    original._embargoes(root, context["proposal"])


def _validate_preserved(root, context):
    p = context["preservation"]
    old = p["preserved_old_evidence"]
    _verify_preserved_inputs(root, context)
    _require(_files(root, context["output_root"] / "observations") ==
             {b["path"] for b in old["completed_selection_manifests"] + old["completed_trace_bindings"]},
             "Unbound observations or traces")
    _require(_files(root, context["output_root"] / "evaluation") ==
             {b["path"] for b in old["completed_scoring_artifacts"]} | {old["failed_scoring_partial"]["path"]},
             "Unbound scoring evidence")
    original._embargoes(root, context["proposal"])
    expected = {b["path"] for b in old["partial_review_files"]}
    historical = {r["attempt_id"]: r for r in context["checkpoint"]["journal_prefix"]["attempts"]}
    for i, window in enumerate(p["review_windows"]):
        verify_binding(root, window["manifest"])
        _require(window["asset_count"] == len(window["assets"]) == 301, "Incomplete published asset snapshot")
        for b in window["assets"]:
            verify_binding(root, b)
        if i < 5:
            row = historical[window["successful_render_attempt_id"]]
            receipt = read_json(verify_binding(root, row["worker_result"]))
            _require(row["success"] is True and receipt["commit"] == RENDER_COMMIT and receipt["spec_sha256"] == RENDER_SPEC
                     and receipt["stage"] == "render" and receipt["key"] == window["window_id"]
                     and [_pair(b) for b in receipt["artifacts"]] == [_pair(window["manifest"])],
                     "Five historical render receipts must bind their exact manifests")
        expected.add(window["manifest"]["path"])
        expected.update(b["path"] for b in window["assets"])
    records = completed_records(root, context)
    for stage, name in OUTPUTS.items():
        path = safe_path(context["output_root"], name)
        if path.exists():
            _require(stage in records, "Unreceipted recovery result cannot authorize continuation")
        elif stage in records:
            raise ValueError("Receipted recovery artifact disappeared")
    if "review-final" in records:
        expected.add((context["output_root"] / OUTPUTS["review-final"]).relative_to(root).as_posix())
    _require(_files(root, context["output_root"] / "review") == expected, "Unexpected review-tree content")
    new_targets = {str(context["output_root"] / name) for name in OUTPUTS.values()}
    for name in p["absent_finalization_artifacts"]:
        if str(root / name) not in new_targets:
            _absent(safe_path(root, name))
    return records


def _render_provenance(old):
    return {"original_selection_spec_sha256": rendering.ORIGINAL_SPEC_SHA256,
            "original_selection_commit": rendering.ORIGINAL_COMMIT,
            "preserved_inventory": old["scoring_context"]["manifest"]["preserved_inventory"],
            "original_evaluation_spec_sha256": rendering.SCORING_SPEC_SHA256,
            "original_evaluation_commit": rendering.SCORING_COMMIT,
            "scoring_manifest": old["manifest"]["scoring_manifest"],
            "interruption_receipt": old["manifest"]["interruption_receipt"],
            "resource_checkpoint": old["manifest"]["resource_checkpoint"]}


def load_context(root, manifest_path):
    wait_for_supervisor()
    context = _metadata(root, manifest_path, True)
    context["_journal"] = verify_history(root, context)
    _validate_preserved(Path(root).resolve(), context)
    old = original.load_context(root, context["original_context"]["manifest_path"], require_clean=False,
                                verify_review_inputs=True, verify_scoring_inputs=True)
    old["commit"] = rendering.ORIGINAL_COMMIT
    context.update(original_context=old, inputs=old["inputs"])
    context["scoring_context"].update(original_context=old, inputs=old["inputs"])
    context["render_context"].update(original_context=old, inputs=old["inputs"], _journal=context["_journal"])
    context["render_context"]["recovery_provenance"] = _render_provenance(context["render_context"])
    return context


def load_reused_observations(root, context, unit):
    return scoring_recovery._load_reused_observations(root, context, unit, context["_journal"])


def load_reused_score(root, context, window_id):
    _require(window_id in {w["window_id"] for w in context["proposal"]["windows"]}, "Unknown scoring window")
    return scoring.load_window_score(root, context["scoring_context"], window_id)


def _validate_semantics(prepared, value):
    """Compare saved display metadata and missingness; never rematch candidates."""
    from .prepare_detection_visual_review import DetectionReviewView, _focus_point, ZOOM_HALF_SIZE_PX, ZOOM_FACTOR
    width, height = prepared.run.source_video.width_px, prepared.run.source_video.height_px
    views = [DetectionReviewView("saved", .01, 10, "descriptive_not_selected")] * 2
    for offset, frame in enumerate(prepared.run.frames):
        annotation = prepared.truth[frame.frame_index]
        focus, kind = _focus_point(annotation, frame, views, width, height)
        x, y = map(round, focus)
        expected = {"focus_type": kind, "focus_xy_px": list(focus), "requested_source_crop_xyxy_px":
                    [x - ZOOM_HALF_SIZE_PX, y - ZOOM_HALF_SIZE_PX, x + ZOOM_HALF_SIZE_PX + 1, y + ZOOM_HALF_SIZE_PX + 1],
                    "zoom_factor": ZOOM_FACTOR, "raw_unmarked_view_included": True}
        _require(value["frame_evidence"][offset]["closeup_regions"] == [{"arm": arm, **expected} for arm in review.ARMS],
                 "Saved closeup arm, focus or geometry differs")
        available = {d.candidate_index: d for d in frame.detections}
        status = ("localization_eligible" if annotation.localization_eligible else "not_visible_negative"
                  if annotation.annotation_status == "labeled" and annotation.visibility == "not_visible"
                  and annotation.game_ball_identity_certainty in ("certain", "probable") else "unscored")
        for key in review.VIEW_KEYS:
            observed = prepared.observations[key]["frames"][offset]
            report = prepared.reports[key]["frame_results"][offset]
            emitted = observed["emitted_candidate_indices"]
            _require(len(set(emitted)) == len(emitted)
                     and all(i in available and available[i].confidence >= .01 for i in emitted)
                     and (key not in review.PAIRS or len(emitted) <= 1), "Invalid saved emitted candidate indices")
            _require(observed["output_state"] == ("tentative_observation" if emitted else "no_accepted_observation"),
                     "Explicit missing observation state differs")
            if key in review.PAIRS:
                endpoint = observed["ranking"]["winner"]["endpoint"]
                expected_emitted = [endpoint[1]] if endpoint is not None and endpoint[0] == frame.frame_index else []
                reason = "current_endpoint" if expected_emitted else "empty_hypothesis" if endpoint is None else "earlier_endpoint_no_current_observation"
                _require(emitted == expected_emitted and observed["decision_reason"] == reason,
                         "Saved current endpoint or explicit missingness differs")
            matched = report["matched_candidate_index"]
            _require(report["annotation_status"] == annotation.annotation_status and report["visibility"] == annotation.visibility
                     and report["scoring_status"] == status and report["input_detection_count"] == len(emitted)
                     and report["accepted_detection_count"] == len(emitted) and (matched is None or matched in emitted),
                     "Saved report does not describe the emitted observations")
            _require((report["matched_center_error_px"] is None) is (matched is None)
                     and (report["matched_effective_center_error_px"] is None) is (matched is None),
                     "Missing match must preserve null center errors")
            if not emitted:
                _require(report["false_positive_count"] == report["non_visible_false_alarm_count"] == 0
                         and report["false_negative_count"] == int(status == "localization_eligible"),
                         "Saved empty observation outcome differs")


def validate_bundle(root, context, window_id, decode=True):
    _require(window_id in {w["window_id"] for w in context["proposal"]["windows"]}, "Unknown review window")
    old = context["render_context"]
    prepared = review.prepare_window(root, old, window_id, observation_loader=load_reused_observations,
                                     score_loader=load_reused_score)
    folder = context["output_root"] / "review/windows" / window_id
    value = review.validate_review_bundle(root, folder, prepared.header)
    _validate_semantics(prepared, value)
    snapshot = next(w for w in context["preservation"]["review_windows"] if w["window_id"] == window_id)
    verify_binding(root, snapshot["manifest"])
    _require({b["path"] for b in snapshot["assets"]} ==
             {(folder / b["path"]).relative_to(root).as_posix() for b in value["assets"]}, "Snapshot asset membership differs")
    validation = {"pngs_decoded": 0, "video": None, "final_source_frame": value["final_frame"]}
    from .prepare_detection_visual_review import ZOOM_PANEL_HEIGHT_PX, ZOOM_PANEL_WIDTH_PX
    width, height = prepared.run.source_video.width_px, prepared.run.source_video.height_px
    sizes = {"comparison": (review.TILE_HEIGHT * 4, review.TILE_WIDTH * 3),
             "closeups": (4 * ZOOM_PANEL_HEIGHT_PX, ZOOM_PANEL_WIDTH_PX),
             **{f"view_{i}": (height + review.NATIVE_HEADER, width + max(520, min(720, round(width * .34)))) for i in range(10)}}
    for b in value["assets"]:
        if b["path"].endswith(".png"):
            _require((b["height_px"], b["width_px"]) == sizes[b["path"].split("/")[0]],
                     "PNG layout differs from source dimensions and approved display geometry")
    if decode:
        for b in value["assets"]:
            if b["path"].endswith(".png"):
                pixels = review._read_png(folder, b)
                _require(pixels.shape == (b["height_px"], b["width_px"], 3), "Published PNG dimensions differ")
                validation["pngs_decoded"] += 1
        _require(validation["pngs_decoded"] == 300, "All three hundred PNGs must decode")
        window = prepared.window
        validation["video"] = review._verify_video(folder / "comparison_slow.mp4", window["start_frame_index"], window["end_frame_index"])
        _require(validation["video"] == value["video_verification"], "Independent video validation differs")
    prepared.verify()
    verify_binding(root, snapshot["manifest"])
    for b in snapshot["assets"]:
        verify_binding(root, b)
    return value, validation


def accept_publication(root, context):
    target = context["output_root"] / OUTPUTS["accept"]
    _absent(target)
    _require("accept" not in completed_records(root, context), "Acceptance already completed")
    snapshot = context["preservation"]["review_windows"][-1]
    _require(snapshot["window_id"] == SIXTH_WINDOW and snapshot["failed_render_attempt_id"] == FAILED_RENDER
             and snapshot["historical_success_binding_verified"] is False, "Wrong acceptance target")
    _, validation = validate_bundle(root, context, SIXTH_WINDOW, decode=True)
    value = {"schema_version": "ball_crop_retention_publication_acceptance/v0.1", "window_id": SIXTH_WINDOW,
             "original_failed_render_attempt_id": FAILED_RENDER, "original_renderer_commit": RENDER_COMMIT,
             "original_renderer_spec_sha256": RENDER_SPEC, "validation_commit": context["commit"],
             "validation_spec_sha256": context["spec_sha256"], "preservation_audit": context["manifest"]["preservation_audit"],
             "resource_checkpoint": context["manifest"]["resource_checkpoint"], "manifest": snapshot["manifest"],
             "assets": snapshot["assets"], "validation": validation, "human_visual_review": "pending"}
    value["content_sha256"] = canonical_sha256(value)
    review._write_json(target, value)
    return value


def _acceptance(root, context, records):
    _require("accept" in records, "New successful acceptance receipt required")
    value = _published(context["output_root"] / OUTPUTS["accept"])
    snapshot = context["preservation"]["review_windows"][-1]
    window = context["proposal"]["windows"][-1]
    expected_validation = {"pngs_decoded": 300, "video": {"decoded_frames": 25, "fps": 5.0,
                           "dimensions_px": [review.TILE_WIDTH * 3, review.TILE_HEIGHT * 4],
                           "first_source_frame": window["start_frame_index"], "last_source_frame": window["end_frame_index"]},
                           "final_source_frame": window["end_frame_index"]}
    _require(value["schema_version"] == "ball_crop_retention_publication_acceptance/v0.1"
             and value["window_id"] == SIXTH_WINDOW and value["original_failed_render_attempt_id"] == FAILED_RENDER
             and value["original_renderer_commit"] == RENDER_COMMIT and value["original_renderer_spec_sha256"] == RENDER_SPEC
             and value["validation_commit"] == context["commit"] and value["validation_spec_sha256"] == context["spec_sha256"]
             and value["preservation_audit"] == context["manifest"]["preservation_audit"]
             and value["resource_checkpoint"] == context["manifest"]["resource_checkpoint"]
             and value["manifest"] == snapshot["manifest"] and value["assets"] == snapshot["assets"]
             and value["validation"] == expected_validation and value["human_visual_review"] == "pending",
             "Acceptance provenance or validated content differs")
    return value


def finalize_review(root, context):
    target = context["output_root"] / OUTPUTS["review-final"]
    _absent(target)
    records = completed_records(root, context)
    _acceptance(root, context, records)
    windows = []
    for window in context["proposal"]["windows"]:
        validate_bundle(root, context, window["window_id"], decode=False)
        snapshot = next(w for w in context["preservation"]["review_windows"] if w["window_id"] == window["window_id"])
        windows.append({"window_id": window["window_id"], "manifest": _pair(snapshot["manifest"]),
                        "final_source_frame": window["end_frame_index"]})
    value = {"schema_version": "ball_crop_candidate_retention_review/v0.2",
             "experiment_spec_sha256": context["spec_sha256"], "code_commit": context["commit"],
             "original_renderer_commit": RENDER_COMMIT, "original_renderer_spec_sha256": RENDER_SPEC,
             "publication_acceptance": file_binding(root, context["output_root"] / OUTPUTS["accept"]),
             "acceptance_worker_result": records["accept"]["worker_result"], "windows": windows,
             "human_visual_review": "pending_six_new_floor_clips_only", "previous_motion_and_yolo_review": "complete_no_repeat",
             "selected_method": None, "selected_operating_point": None, "quality_gate": None}
    value["content_sha256"] = canonical_sha256(value)
    review._write_json(target, value)
    return value


def _worker(root, manifest_path, stage, key):
    _require(stage in ("verify", "preflight", "accept", "review-final"), "Only verification, acceptance and finalization dispatchable")
    wait_for_supervisor()
    context = load_context(root, manifest_path)
    _expected_artifacts(context, stage, key)
    active = context["_journal"]._attempts().get(os.environ["BALL_RETENTION_ATTEMPT_ID"])
    _require(active is not None and active["finished"] is None
             and active["start"]["unit_key"] == "publication-recovery:" + stage + ":" + key,
             "Worker dispatch differs from its supervised reservation")
    if stage == "accept":
        accept_publication(root, context)
    elif stage == "review-final":
        finalize_review(root, context)
    # Recheck input hashes after publication without treating this worker's own
    # result as accepted. A failure here leaves an unreceipted target and stops.
    for w in context["preservation"]["review_windows"]:
        for b in [w["manifest"], *w["assets"]]:
            verify_binding(root, b)
    _verify_preserved_inputs(root, context)
    fresh = _metadata(root, manifest_path, True)
    _require(fresh["commit"] == context["commit"] and fresh["manifest"] == context["manifest"],
             "Recovery source checkpoint or authority changed")
    verify_history(root, context)
    artifacts = [file_binding(root, Path(root) / name) for name in sorted(_expected_artifacts(context, stage, key))]
    result = {"stage": stage, "key": key, "spec_sha256": context["spec_sha256"], "commit": context["commit"], "artifacts": artifacts}
    path = safe_path(context["output_root"], Path(os.environ["BALL_RETENTION_RESULT_PATH"]).relative_to(context["output_root"]).as_posix())
    _require(path.name == os.environ["BALL_RETENTION_ATTEMPT_ID"] + ".result.json", "Wrong worker receipt target")
    review._write_json(path, result)
    return result


def run_recovery(root, manifest_path, *, stage="verify", dry_run=False):
    _require(stage in PERMITTED_STAGES, "Only verification or publication recovery permitted")
    root, manifest_path = Path(root).resolve(), Path(manifest_path).resolve()
    context = _metadata(root, manifest_path, not dry_run)
    if dry_run:
        return {"dry_run": True, "metadata_only": True, "saved_outputs_verified": False,
                "execution_requires_clean_tested_commit": True, "spec_sha256": context["spec_sha256"]}
    def dispatch(action, key=""):
        if action in HELPERS:
            helper = context["output_root"] / HELPERS[action]
            command = [sys.executable, "-B", str(helper)]
        else:
            command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_retention_publication_recovery", "--manifest",
                       str(manifest_path), "--repository-root", str(root), "--worker-stage", action, "--unit-key", key]
        return run_supervised(context["output_root"], "publication-recovery:" + action + ":" + key,
                              command, context["proposal"]["resource_limits"], cwd=root, selection_unit=False, require_result=True)
    receipts = [dispatch("preflight", stage)]
    if stage == "recover":
        # Resume only after a successful preflight has rejected any failed,
        # unfinished or unreceipted suffix. Parent reads resource metadata only.
        journal = BudgetJournal(context["output_root"], context["proposal"]["resource_limits"])
        done = {a["start"]["unit_key"].split(":")[1] for a in journal._attempts().values()
                if a["start"]["unit_key"].startswith("publication-recovery:") and a["finished"] and a["finished"]["success"]}
        for action in OUTPUTS:
            if action not in done:
                receipts.append(dispatch(action))
    return {"stage": stage, "successful_workers": len(receipts), "commit": context["commit"],
            "selection_executed": False, "scoring_executed": False, "rendering_executed": False,
            "new_model_calls": 0, "training_executed": False, "output_root": str(context["output_root"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=PERMITTED_STAGES, default="verify")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker-stage", choices=("verify", "preflight", "accept", "review-final"), help=argparse.SUPPRESS)
    parser.add_argument("--unit-key", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    path = (root / args.manifest).resolve()
    value = (_worker(root, path, args.worker_stage, args.unit_key) if args.worker_stage
             else run_recovery(root, path, stage=args.stage, dry_run=args.dry_run))
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()

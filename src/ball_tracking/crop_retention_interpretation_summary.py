"""Pure, bounded interpretation of an already passed audit and its guide.

Only explicitly allowed audit summaries are copied. Source pointers refer to
the supplied audit; they are never followed into another artifact. This module
has no file/process/model/media access and performs no scientific aggregation.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

MAX_TEXT_BYTES = 64 * 1024
ARMS = tuple("history_edge_" + a + "_cost_" + b for a in ("tight", "wide") for b in ("tight", "wide"))
ARM_NAMES = dict(zip(ARMS, ("TT", "TW", "WT", "WW")))
RADII = (5.0, 10.0, 15.0, 20.0, 30.0)
PURPOSES = ("representative_evaluation", "challenge_evaluation")
WINDOWS = tuple({"window_id": f"possession_{p:03d}_frames_{first:04d}_{last:04d}_{purpose}_development_v0_2",
                 "possession_id": f"possession_{p:03d}", "purpose": purpose,
                 "start_frame_index": first, "end_frame_index": last}
                for p, first, last, purpose in ((1, 50, 74, PURPOSES[0]), (1, 200, 224, PURPOSES[1]),
                    (2, 250, 274, PURPOSES[0]), (2, 25, 49, PURPOSES[1]), (3, 300, 324, PURPOSES[0]), (3, 150, 174, PURPOSES[1])))
COUNTS = ("eligible_frame_count", "not_visible_frame_count", "unscored_frame_count", "true_positive_count",
          "false_positive_count", "false_negative_count", "duplicate_false_positive_count",
          "non_visible_false_alarm_count", "non_visible_false_alarm_frame_count")
DENOMINATORS = COUNTS[:3]
GUIDE_METRICS = ("true_positive_count", "false_positive_count", "false_negative_count", "non_visible_false_alarm_count")
TEMPORAL = ("emitted_frame_count", "missing_frame_count", "frame_count", "emitted_frame_coverage")
AUDIT_REFERENCE = "../independent_publication_recovery_audit.json"
GUIDE_REFERENCE = "../publication_recovery_review_guide.md"
_MISSING = object()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _get(value, key):
    return value.get(key, _MISSING) if type(value) is dict else _MISSING


def _number(value, label, *, optional=False, count=False):
    if value is _MISSING and optional:
        return
    _require(type(value) in (int, float) and math.isfinite(value), "Missing/invalid numerical field: " + label)
    if count:
        _require(type(value) is int and value >= 0, "Invalid count: " + label)


def _section(text, heading, end_heading):
    marker = heading + "\n"
    _require(text.count(marker) == 1, "Guide section missing/duplicated: " + heading)
    value = text.split(marker, 1)[1]
    if end_heading is not None:
        _require(end_heading + "\n" in value, "Guide section order differs")
        value = value.split(end_heading + "\n", 1)[0]
    return value


def _table_rows(text):
    return [line for line in text.splitlines() if line.startswith("| ") and not line.startswith("| ---")]


def _frame_text(rows, purpose=None):
    _require(type(rows) is list, "Audited gain/loss summary is missing")
    windows = {w["window_id"]: w for w in WINDOWS}
    for row in rows:
        _require(type(row) is dict and type(row.get("frame_index")) is int
                and row.get("window_id") in windows, "Unsupported gain/loss summary")
        window = windows[row["window_id"]]
        _require(row.get("possession_id") == window["possession_id"]
                and window["start_frame_index"] <= row["frame_index"] <= window["end_frame_index"]
                and (purpose is None or window["purpose"] == purpose), "Gain/loss window labels differ")
    return "; ".join(f"{row['possession_id']} frame {row['frame_index']}" for row in rows) or "None"


def _guide_correspondence(guide, audit):
    """Compare published figures/labels directly; do not recompute the audit."""
    required_phrases = (
        "unchanged motion scorer can retain every saved candidate at confidence .01 instead of the first twenty",
        "Each clip contains 25 frames shown at 5 fps.",
        "left is the saved twenty-candidate cap and middle is all candidates",
        "same .01 confidence and 10-pixel localization radius",
        "Matches are true positives; false observations are false positives; missed eligible frames are false negatives.",
        "TT/TW/WT/WW refer to the frozen tight/wide edge and cost settings; none is selected as a winner.",
        "Missing observations (NULL) differ from missed eligible frames (false negatives)",
        "Higher-confidence .20/.35 equivalence references reuse existing results and are not extra trials.",
        "These copied deltas are all-candidate minus cap20 at .01.",
    )
    _require(all(phrase in guide for phrase in required_phrases), "Guide comparison definitions differ")
    clip_section = _section(guide, "## Review the six clips", "## Audited descriptive results")
    clip_rows = _table_rows(clip_section)
    _require(len(clip_rows) == 7 and clip_rows[0] == "| Window | Source frames | Clip | Final comparison | Final closeup |", "Guide clip table differs")
    for row, window in zip(clip_rows[1:], WINDOWS):
        label = window["possession_id"] + " " + window["purpose"].replace("_evaluation", "")
        prefix = f"| {label} | {window['start_frame_index']}–{window['end_frame_index']} | "
        _require(row.startswith(prefix) and "comparison_slow.mp4" in row
                and f"comparison/frame_{window['end_frame_index']:06d}.png" in row
                and f"closeups/frame_{window['end_frame_index']:06d}.png" in row, "Guide window/final-frame label differs")
    pool_map = {p["purpose"]: p for p in audit["pool_audits"]}
    for purpose, title, following in ((PURPOSES[0], "Representative pool", "### Challenge pool"),
                                     (PURPOSES[1], "Challenge pool", "## All audited radius comparisons")):
        section = _section(guide, "### " + title, following)
        pool = pool_map[purpose]
        cells = pool["fixed_floor_radius10_descriptive_cells"]
        denominator = cells[0]["saved_cap20"]
        expected = f"Audited common denominators: {denominator['eligible_frame_count']} localization-eligible frames, {denominator['not_visible_frame_count']} reviewed hidden frames, and {denominator['unscored_frame_count']} unscored frames."
        _require(expected in section, "Guide denominator differs from audit")
        expected_rows = ["| Setting | Matches cap20 → all | False observations cap20 → all | Missed eligible cap20 → all | Hidden alarms cap20 → all |"]
        for cell in cells:
            values = [f"{cell['saved_cap20'][key]} → {cell['new_all'][key]}" for key in GUIDE_METRICS]
            expected_rows.append("| " + " | ".join([ARM_NAMES[cell["arm"]], *values]) + " |")
            gains = _frame_text(cell["gained_match_frames"], purpose)
            losses = _frame_text(cell["lost_match_frames"], purpose)
            sentence = f"**{ARM_NAMES[cell['arm']]} gained localization matches:** {gains}. **Lost localization matches:** {losses}."
            _require(section.count(sentence) == 1, "Guide favorable/unfavorable changes differ")
        expected_rows.append("| Window | Setting | Missing observations cap20 → all | Emitted observations cap20 → all | Frames |")
        windows = {w["window_id"]: w for w in WINDOWS}
        for row in pool["fixed_floor_radius10_missingness_by_window"]:
            window = windows[row["window_id"]]
            before, after = row["saved_cap20"], row["new_all"]
            expected_rows.append(f"| {window['possession_id']} {window['start_frame_index']}–{window['end_frame_index']} | {ARM_NAMES[row['arm']]} | {before['missing_frame_count']} → {after['missing_frame_count']} | {before['emitted_frame_count']} → {after['emitted_frame_count']} | {before['frame_count']} |")
        _require(_table_rows(section) == expected_rows, "Guide pool figures/missingness rows differ from audit")
    radius_section = _section(guide, "## All audited radius comparisons", "## Provenance")
    expected_rows = ["| Pool | Setting | Radius px | Match delta | False-observation delta | Missed-eligible delta | Hidden-alarm delta |"]
    for pool in audit["pool_audits"]:
        for cell in pool["all_radius_cap_deltas"]:
            expected_rows.append("| " + " | ".join([pool["purpose"].replace("_evaluation", ""), ARM_NAMES[cell["arm"]], str(cell["radius_px"]),
                *(str(cell["metric_deltas"][k]) for k in GUIDE_METRICS)]) + " |")
    _require(_table_rows(radius_section) == expected_rows, "Guide all-radius comparisons differ from audit")
    provenance_section = _section(guide, "## Provenance", None)
    blocks = re.findall(r"```json\n(.*?)\n```", provenance_section, flags=re.S)
    _require(len(blocks) == 1, "Guide provenance missing/duplicated")
    provenance = json.loads(blocks[0])
    _require(provenance["execution_commit"] == audit["execution_code_commit"]
            and provenance["spec_sha256"] == audit["experiment_spec_sha256"]
            and provenance["scientific_scores_recomputed"] is False, "Guide/audit execution provenance differs")


def _validate_audit(audit):
    _require(type(audit) is dict and audit.get("schema_version") == "ball_crop_retention_independent_publication_recovery_audit/v0.1"
            and audit.get("status") == "passed", "Only the passed independent publication audit is supported")
    _require(_canonical({k: v for k, v in audit.items() if k != "content_sha256"}) == audit.get("content_sha256"), "Audit content digest differs")
    _require(all(audit.get(k, _MISSING) is None for k in ("selected_method", "selected_operating_point", "quality_gate")), "Audit contains or omits a decision constraint")
    _require(audit.get("human_visual_review") == "pending_six_new_floor_clips_only" and audit.get("prior_reviews") == "complete_no_repeat", "Historical audit review state differs")
    pools = audit.get("pool_audits")
    _require(type(pools) is list and len(pools) == 2 and {p.get("purpose") for p in pools} == set(PURPOSES), "Separate representative/challenge pools required")
    for pool in pools:
        purpose = pool["purpose"]
        for field, expected in (("fixed_floor_radius10_descriptive_cells", {(a, 10.0) for a in ARMS}),
                                ("all_radius_cap_deltas", {(a, r) for a in ARMS for r in RADII})):
            cells = pool.get(field)
            _require(type(cells) is list and len(cells) == len(expected)
                    and {(c.get("arm"), c.get("radius_px")) for c in cells} == expected, "All frozen settings/radii must be retained")
            for cell in cells:
                _require(cell.get("confidence_threshold") == .01 and cell.get("semantic_identity_judgments") is False,
                         "Only matched-confidence export-floor comparison without identity judgments is permitted")
                for policy in ("saved_cap20", "new_all"):
                    _require(type(cell.get(policy)) is dict, "Missing paired cap-policy summary")
                    for key in COUNTS:
                        _number(_get(cell[policy], key), key, optional=key not in (*DENOMINATORS, *GUIDE_METRICS), count=True)
                _require(type(cell.get("metric_deltas")) is dict, "Missing audited delta summaries")
                for key in COUNTS:
                    _number(_get(cell["metric_deltas"], key), key, optional=key not in GUIDE_METRICS)
                _frame_text(cell.get("gained_match_frames"), purpose)
                _frame_text(cell.get("lost_match_frames"), purpose)
                if field == "fixed_floor_radius10_descriptive_cells":
                    _require(cell["saved_cap20"]["eligible_frame_count"] == cells[0]["saved_cap20"]["eligible_frame_count"]
                            and all(cell[policy][k] == cells[0]["saved_cap20"][k] for policy in ("saved_cap20", "new_all") for k in DENOMINATORS), "Audited common denominators differ")
        radius10 = {cell["arm"]: cell for cell in pool["all_radius_cap_deltas"] if cell["radius_px"] == 10.0}
        _require(all(cell == radius10[cell["arm"]] for cell in pool["fixed_floor_radius10_descriptive_cells"]),
                 "Fixed display differs from its audited radius comparison")
        missing = pool.get("fixed_floor_radius10_missingness_by_window")
        windows = {w["window_id"]: w for w in WINDOWS if w["purpose"] == purpose}
        _require(type(missing) is list and len(missing) == 12
                and {(r.get("window_id"), r.get("arm")) for r in missing} == {(w, arm) for w in windows for arm in ARMS}, "Missingness windows/settings incomplete")
        for row in missing:
            _require(row.get("purpose") == purpose and row.get("possession_id") == windows[row["window_id"]]["possession_id"]
                    and row.get("confidence_threshold") == .01 and row.get("radius_px") == 10.0, "Missingness comparison labels differ")
            for policy in ("saved_cap20", "new_all"):
                value = row.get(policy)
                _require(type(value) is dict, "Missingness pair is missing")
                for key in TEMPORAL:
                    _number(_get(value, key), key, optional=key == "emitted_frame_coverage", count=key != "emitted_frame_coverage")
                _require(value["frame_count"] == 25, "Missingness window denominator differs")
    reviews = audit.get("review_audits")
    _require(type(reviews) is list and len(reviews) == 6
            and [r.get("window_id") for r in reviews] == [w["window_id"] for w in WINDOWS], "Audited review windows differ")
    for row, window in zip(reviews, WINDOWS):
        _require(row.get("final_source_frame") == window["end_frame_index"] and row.get("human_visual_review") == "pending"
                and row.get("independent_new_clip_decode", {}).get("decoded_frames") == 25, "Audited final-frame metadata differs")


def _copier(source_map):
    def copy(value, key, pointer, output_pointer):
        result = _get(value, key)
        source_map.append({"output_pointer": output_pointer, "input": "audit", "json_pointer": pointer,
                           "status": "unavailable" if result is _MISSING else "copied"})
        return {"status": "unavailable"} if result is _MISSING else result
    return copy


def _present(value):
    return "unavailable" if type(value) is dict and value.get("status") == "unavailable" else str(value)


def _link(text, pointer):
    return f"[{text}]({AUDIT_REFERENCE}#{pointer})"


def _pair_text(cell, key, pointer):
    return _link(_present(cell["saved_cap20"][key]) + " → " + _present(cell["new_all"][key]), pointer)


def _interpret(cell, pointer):
    descriptions = []
    for key, label in (("true_positive_count", "localized matches"), ("false_positive_count", "false observations"),
                       ("false_negative_count", "missed eligible frames"), ("non_visible_false_alarm_count", "hidden alarms")):
        delta = cell["metric_deltas"][key]
        change = "unavailable" if type(delta) is dict else "increased" if delta > 0 else "decreased" if delta < 0 else "unchanged"
        descriptions.append(label + " " + change)
    recovery = "present" if cell["gain_loss_presence"]["gains_present"] else "absent"
    regression = "present" if cell["gain_loss_presence"]["losses_present"] else "absent"
    return _link("; ".join(descriptions), pointer) + ". " + _link("Frame-level recoveries " + recovery, pointer + "/gained_match_frames") + "; " + _link("frame-level regressions " + regression, pointer + "/lost_match_frames") + ". No individual-frame payload is reproduced."


def build_summary(guide_text: str, audit: dict) -> tuple[dict, str]:
    """Return safe copied evidence and a bounded memo; never perform file I/O."""
    try:
        _require(type(guide_text) is str and len(guide_text.encode("utf-8")) <= MAX_TEXT_BYTES, "Guide exceeds 64 KiB or is not text")
        _validate_audit(audit)
        _guide_correspondence(guide_text, audit)
        source_map = []
        copy = _copier(source_map)
        result = {"schema_version": "ball_crop_retention_post_review_interpretation_summary/v0.1",
                  "scope": "Existing same-confidence/same-motion saved_cap20 versus new_all descriptive comparison only",
                  "pools": [], "resource_context": {}, "source_map": source_map,
                  "selected_method": None, "selected_operating_point": None, "quality_gate": None,
                  "new_scientific_aggregation": False, "new_experiment_authorized": False,
                  "human_review": "Later human-review record governs approval; historical pending fields are preserved and no repeat review is requested"}
        markdown = ["# What the completed candidate-retention comparison tells us", "",
            "The player-coordinate foundation is complete for the curated possessions. This comparison is part of ball-tracking development; possession understanding, matchup inference and defensive scoring remain later work.", "",
            "The comparison changes candidate retention while keeping the saved confidence floor and each motion setting fixed. The separate pools below show the tradeoffs. No tracker, operating point or quality gate is selected.", "",
            "Values below are copied from the passed audit. Arrows mean saved cap20 → all saved qualified candidates. Missing observations mean no emitted candidate; a false negative can instead involve an emitted candidate that did not localize the reference. The source guide's pending-review text is historical; the later review record governs approval. No clip review is requested again.", ""]
        for pi, pool in enumerate(audit["pool_audits"]):
            pp, op = f"/pool_audits/{pi}", f"/pools/{pi}"
            out = {"purpose": copy(pool, "purpose", pp + "/purpose", op + "/purpose")}
            for field in ("fixed_floor_radius10_descriptive_cells", "all_radius_cap_deltas"):
                out[field] = []
                for ci, cell in enumerate(pool[field]):
                    cp, oc = f"{pp}/{field}/{ci}", f"{op}/{field}/{ci}"
                    row = {k: copy(cell, k, cp + "/" + k, oc + "/" + k) for k in ("arm", "confidence_threshold", "radius_px")}
                    for policy in ("saved_cap20", "new_all", "metric_deltas"):
                        row[policy] = {k: copy(cell[policy], k, cp + "/" + policy + "/" + k, oc + "/" + policy + "/" + k) for k in COUNTS}
                    row["gain_loss_presence"] = {"gains_present": bool(cell["gained_match_frames"]), "losses_present": bool(cell["lost_match_frames"])}
                    for name, source in (("gains_present", "gained_match_frames"), ("losses_present", "lost_match_frames")):
                        source_map.append({"output_pointer": oc + "/gain_loss_presence/" + name, "input": "audit", "json_pointer": cp + "/" + source, "status": "qualitative_presence"})
                    out[field].append(row)
            field = "fixed_floor_radius10_missingness_by_window"
            out[field] = []
            for ri, row in enumerate(pool[field]):
                rp, orp = f"{pp}/{field}/{ri}", f"{op}/{field}/{ri}"
                copied = {k: copy(row, k, rp + "/" + k, orp + "/" + k) for k in ("window_id", "purpose", "possession_id", "arm", "confidence_threshold", "radius_px")}
                for policy in ("saved_cap20", "new_all"):
                    copied[policy] = {k: copy(row[policy], k, rp + "/" + policy + "/" + k, orp + "/" + policy + "/" + k) for k in TEMPORAL}
                out[field].append(copied)
            result["pools"].append(out)
            title = "Representative pool" if out["purpose"] == PURPOSES[0] else "Challenge pool"
            cells = out["fixed_floor_radius10_descriptive_cells"]
            base = pp + "/fixed_floor_radius10_descriptive_cells/0"
            markdown += [f"## {title}", "", "Common audited denominators: " + "; ".join(_link(_present(cells[0]["saved_cap20"][key]) + " " + label,
                base + "/saved_cap20/" + key) for key, label in (("eligible_frame_count", "eligible frames"), ("not_visible_frame_count", "hidden frames"), ("unscored_frame_count", "unscored frames"))) + ".",
                "", "Hidden-frame evidence in this pool is limited to " + _link(_present(cells[0]["saved_cap20"]["not_visible_frame_count"]) + " reviewed hidden frames", base + "/saved_cap20/not_visible_frame_count") + "; it cannot establish robust hidden-ball performance.",
                "", "Display comparison: confidence " + _link(str(cells[0]["confidence_threshold"]), base + "/confidence_threshold")
                + ", localization radius " + _link(str(cells[0]["radius_px"]) + " source pixels", base + "/radius_px") + ".", "",
                "| Setting | Matches | False observations | Missed eligible | Hidden alarms | Duplicate false positives | Hidden-alarm frames |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
            display_keys = (*GUIDE_METRICS, "duplicate_false_positive_count", "non_visible_false_alarm_frame_count")
            for ci, cell in enumerate(cells):
                cp = f"{pp}/fixed_floor_radius10_descriptive_cells/{ci}"
                markdown.append("| " + " | ".join([ARM_NAMES[cell["arm"]], *(_pair_text(cell, key, cp) for key in display_keys)]) + " |")
            for ci, cell in enumerate(cells):
                markdown += ["", "**" + ARM_NAMES[cell["arm"]] + ":** " + _interpret(cell, f"{pp}/fixed_floor_radius10_descriptive_cells/{ci}")]
            markdown += ["", "Window-level missingness is copied without creating a pool total or a new rate.", "",
                "| Window | Setting | Missing observations | Emitted observations | Window frames |", "| --- | --- | --- | --- | --- |"]
            for ri, row in enumerate(out[field]):
                rp = f"{pp}/{field}/{ri}"
                markdown.append("| " + " | ".join([_link(row["window_id"], rp + "/window_id"), ARM_NAMES[row["arm"]],
                    _pair_text(row, "missing_frame_count", rp), _pair_text(row, "emitted_frame_count", rp),
                    _link(str(row["saved_cap20"]["frame_count"]), rp + "/saved_cap20/frame_count")]) + " |")
            markdown += ["", "The remaining audited radius comparisons are preserved below, including unfavorable deltas. These are repeated views of the same development evidence, not independent trials.", "",
                "| Setting | Radius, source px | Match delta | False-observation delta | Missed-eligible delta | Hidden-alarm delta |", "| --- | --- | --- | --- | --- | --- |"]
            for ci, cell in enumerate(out["all_radius_cap_deltas"]):
                cp = f"{pp}/all_radius_cap_deltas/{ci}"
                markdown.append("| " + " | ".join([ARM_NAMES[cell["arm"]], _link(str(cell["radius_px"]), cp + "/radius_px"),
                    *(_link(_present(cell["metric_deltas"][key]), cp + "/metric_deltas/" + key) for key in GUIDE_METRICS)]) + " |")
            markdown.append("")
        resource = audit.get("resource_audit", {})
        for key in ("prior_active_seconds", "remaining_seconds_before_current_audit"):
            value = _get(resource, key)
            _number(value, key, optional=True)
            result["resource_context"][key] = copy(resource, key, "/resource_audit/" + key, "/resource_context/" + key)
        result["resource_context"]["scope"] = "Historical pre-audit resource snapshot, not the later completed budget and not a per-setting cost comparison"
        limitations = [
            "Only retention at the saved export floor changes. This does not identify the combined effect of changing confidence and cap.",
            "The guide's [.20/.35 structural-equivalence references](" + GUIDE_REFERENCE + "#audited-descriptive-results) reuse cap20 evidence; they are not newly executed uncapped trials.",
            "Candidate burden is not single-output tracker accuracy. A larger heuristic path score is not calibrated confidence or evidence of greater accuracy.",
            "Localization matches are not certified ball identities. Candidate retention, wrong-object selection and inaccurate centers remain different issues.",
            "Diagnostic examples are not evaluation denominators. Repeated frames, radii, thresholds and crop hypotheses are not independent samples.",
            "The small hidden-frame sample comes from one episode and cannot establish robust hidden-ball performance.",
            "Missing fields remain unavailable. No deeper reports, per-frame payloads, traces, annotations or media were consulted by this pure summary builder.",
            "No preferred method, operating point, quality gate, training split, generalization claim or new experiment is authorized.",
        ]
        questions = ["In a separately specified study, how could retention errors be distinguished from wrong-object selection and center-localization errors?",
                     "What additional independent evidence would be needed to evaluate hidden-ball behavior without changing the sealed holdouts?"]
        result["limitations"], result["unresolved_questions"] = limitations, questions
        result["checks"] = {"guide_audit_correspondence": True, "complete_frozen_summary_rows_preserved": True,
                            "raw_or_per_frame_payloads_copied": False, "scientific_values_recomputed": False}
        markdown += ["## Resource context", "", "The audit records a historical pre-audit snapshot: "
            + _link(_present(result["resource_context"]["prior_active_seconds"]) + " active seconds consumed", "/resource_audit/prior_active_seconds") + "; "
            + _link(_present(result["resource_context"]["remaining_seconds_before_current_audit"]) + " seconds remaining then", "/resource_audit/remaining_seconds_before_current_audit")
            + ". These values are not the later completed budget or per-setting costs. No per-setting resource comparison is available in the copied summaries.", "",
            "## Limits and unresolved questions", "", *["- " + value for value in limitations], "", *["- " + value for value in questions], "",
            "Source correspondence was checked against [the existing guide](" + GUIDE_REFERENCE + "#audited-descriptive-results). Numerical links point only into the passed audit; they do not authorize opening additional evidence.", ""]
        memo = "\n".join(markdown)
        _require(len(memo.encode("utf-8")) <= MAX_TEXT_BYTES, "Complete readable summary exceeds 64 KiB; no rows were truncated")
        json.dumps(result, ensure_ascii=False, allow_nan=False)
        return result, memo
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError("Unsupported or missing guide/audit field relationship") from error

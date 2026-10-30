"""Pure post-selection metrics; no I/O, inference, fitting, or authorization.

``score_timeline`` accepts the evaluation package's native ``frames`` (embedded
FrameAnnotation mappings, or null), ``source_video`` dimensions and ``time_base``.
Each frame needs an explicit ``segment_id``/``block_id`` and
``exposure_role``/``reference_role`` (block defaults are accepted). Camera cuts
must have distinct segment IDs. ``state='withheld'`` denotes protected rows;
they must contain neither annotations, PNGs nor points.

Automatic observations use the existing select_observation producer fields.
Their supplied series is asserted automatic unless ``point_origin`` explicitly
says inferred/manual. Those points count absent in automatic metrics, but are
still published points. Optional published_observations is a complete separate
series of {source_frame_index, source_pts_ticks, points:[{point_id,
center_xy_px, point_origin}]}. It must retain every supplied selected point.

Optional wrong_object_judgments bind frame/PTS/point_id/center_xy_px to a
decision (confirmed_wrong_object, not_wrong_object, unknown) and evidence.
Distance errors alone never establish object identity. Missing judgments stay
pending. A caller must supply source/evidence provenance and human review
separately; this module cannot grant acceptance or authorize a second fit.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
import math
from types import SimpleNamespace

from .annotations import FrameAnnotation


MATCH_RADIUS_PX = 10
MISSING_LIMIT = Fraction(1, 5)
WRONG_OBJECT_LIMIT = Fraction(3, 25)
RECOVERY_LIMIT = Fraction(3, 25)
ORIGINS = {"automatic", "inferred", "manual"}
UNSCORED_BOUNDARIES = {"protected_boundary", "native_discontinuity", "exposure_subset_boundary"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, label, minimum=0):
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
             f"{label} must be an integer >= {minimum}")
    return value


def _point(value):
    if value is None:
        return None
    _require(isinstance(value, (list, tuple)) and len(value) == 2, "Point must have two coordinates")
    _require(all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                 for v in value), "Point coordinates must be finite numbers")
    return list(value)


def _time(value):
    return {"seconds": float(value), "exact_seconds": str(value)}


def _gate(status, **details):
    return {"status": status, **details}


def _combine(statuses):
    values = set(statuses)
    return ("fail" if "fail" in values else "inconclusive" if "inconclusive" in values
            else "pass" if "pass" in values else "not_applicable")


def _index(rows, name):
    if isinstance(rows, dict):
        rows = rows["frames"]
    indexed = {}
    for row in rows:
        index = _integer(row["source_frame_index"], f"{name} frame index")
        _require(index not in indexed, f"Duplicate {name} frame {index}")
        indexed[index] = row
    return indexed


def _category(annotation):
    if annotation is None or annotation.annotation_status == "unlabeled":
        return "reference_unlabeled"
    if annotation.annotation_status == "excluded":
        return "reference_excluded"
    if annotation.localization_eligible:
        return "eligible"
    if annotation.visibility == "not_visible":
        return "certain_hidden" if annotation.game_ball_identity_certainty == "certain" else "uncertain_hidden"
    return "indeterminate" if annotation.visibility == "indeterminate" else "visible_unlocalizable"


def _normalize(timeline, observations, published_observations, judgments):
    frames = timeline["frames"]
    _require(bool(frames), "Native timeline must not be empty")
    base = Fraction(timeline["time_base"])
    _require(base > 0, "Native time base must be positive")
    source = timeline["source_video"]
    width = _integer(source["width_px"], "Source width", 1)
    height = _integer(source["height_px"], "Source height", 1)
    bounds = SimpleNamespace(width_px=width, height_px=height)
    observed = _index(observations, "observation")
    published = None if published_observations is None else _index(published_observations, "published")
    native_ids = [f["source_frame_index"] for f in frames]
    _require(len(set(native_ids)) == len(native_ids) and native_ids == sorted(native_ids),
             "Native frames must be unique and ascending")
    permitted = {f["source_frame_index"] for f in frames if f.get("state") != "withheld"}
    _require(permitted <= observed.keys() <= set(native_ids), "Observation/native frame coverage differs")
    if published is not None:
        _require(permitted <= published.keys() <= set(native_ids), "Published/native frame coverage differs")
    reviews = {}
    for review in judgments or []:
        key = (_integer(review["source_frame_index"], "Wrong-object frame index"), review["point_id"])
        _integer(review["source_pts_ticks"], "Wrong-object PTS")
        if "time_base" in review:
            _require(Fraction(review["time_base"]) == base, "Wrong-object time base differs")
        _require(key not in reviews, "Duplicate wrong-object point judgment")
        _require(review["decision"] in {"confirmed_wrong_object", "not_wrong_object", "unknown"},
                 "Invalid wrong-object decision")
        _require(bool(review.get("evidence")), "Wrong-object judgment needs explicit evidence")
        reviews[key] = review
    consumed = set()
    rows = []
    continuity = -1
    for offset, frame in enumerate(frames):
        index = _integer(frame["source_frame_index"], "Native frame index")
        pts = _integer(frame["source_pts_ticks"], "Native PTS")
        duration = _integer(frame["duration_ticks"], "Native duration", 1)
        if "time_base" in frame:
            _require(Fraction(frame["time_base"]) == base, "Frame time base differs")
        protected = frame.get("state") == "withheld"
        annotation = frame.get("annotation")
        if protected:
            _require(annotation is None and frame.get("png") is None
                     and frame.get("baseline_observation") is None,
                     "Protected row contains reference/pixels/baseline output")
            segment, exposure = "withheld", "protected_withheld"
        else:
            segment = frame.get("segment_id", frame.get("block_id", timeline.get("segment_id", timeline.get("block_id"))))
            exposure = frame.get("exposure_role", frame.get("reference_role", timeline.get("exposure_role", timeline.get("reference_role"))))
            _require(isinstance(segment, str) and bool(segment), "Explicit source segment identity required")
            _require(isinstance(exposure, str) and bool(exposure), "Explicit exposure role required")
        parsed = None if annotation is None else FrameAnnotation.from_mapping(annotation, offset, bounds)
        _require(parsed is None or parsed.frame_index == index, "Annotation/native frame join differs")
        category = "withheld" if protected else _category(parsed)
        observation = observed.get(index)
        selected = None
        origin = "automatic"
        inference_status = "withheld"
        if observation is not None:
            _require(_integer(observation["source_pts_ticks"], "Observation PTS") == pts,
                     "Observation/native PTS join differs")
            if "time_base" in observation:
                _require(Fraction(observation["time_base"]) == base, "Observation time base differs")
            if "source_png" in observation:
                _require(observation["source_png"] == frame.get("png"), "Observation/native PNG join differs")
            inference_status = observation["inference_status"]
            _require(inference_status in {"completed", "withheld"},
                     "Only completed/policy-withheld observations are scoreable; a tooling failure is not a model miss")
            selected = _point(observation["center_xy_px"])
            origin = observation.get("point_origin", "automatic")
            _require(origin in ORIGINS, "Unknown selected point origin")
            _require(selected is None or inference_status == "completed", "Incomplete observation contains a point")
            if protected:
                _require(inference_status == "withheld" and observation.get("temporal_contributions") == 0
                         and observation.get("candidates") == [] and observation.get("mean_heatmap_sha256") is None
                         and observation.get("selected_candidate_index") is None and observation.get("native_score") is None,
                         "Protected observation must explicitly withhold all inference, contributions and candidates")
        _require(not protected or selected is None, "Protected row contains a selected point")
        points = [] if selected is None else [{"point_id": "selected", "center_xy_px": selected, "point_origin": origin}]
        if published is not None and index in published:
            entry = published[index]
            _require(_integer(entry["source_pts_ticks"], "Published PTS") == pts,
                     "Published/native PTS join differs")
            if "time_base" in entry:
                _require(Fraction(entry["time_base"]) == base, "Published time base differs")
            points = []
            seen = set()
            for point in entry["points"]:
                point_id = point["point_id"]
                _require(isinstance(point_id, str) and point_id and point_id not in seen, "Invalid/duplicate published point ID")
                seen.add(point_id)
                center = _point(point["center_xy_px"])
                _require(center is not None and point["point_origin"] in ORIGINS, "Invalid published point")
                points.append({"point_id": point_id, "center_xy_px": center, "point_origin": point["point_origin"]})
            _require(selected is None or any(p["center_xy_px"] == selected and p["point_origin"] == origin for p in points),
                     "Published series omitted the selected point")
        _require(not protected or not points, "Protected row contains published coordinates")
        for point in points:
            key = (index, point["point_id"])
            review = reviews.get(key)
            if review is not None:
                _require(review["source_pts_ticks"] == pts and _point(review["center_xy_px"]) == point["center_xy_px"],
                         "Wrong-object judgment/native point join differs")
                consumed.add(key)
            point["wrong_object_decision"] = "pending" if review is None else review["decision"]
            point["wrong_object_evidence"] = None if review is None else review["evidence"]
        automatic = selected if origin == "automatic" else None
        eligible = category == "eligible"
        error = None if not eligible or automatic is None else math.dist(automatic, parsed.geometry.center_xy_px)
        outcome = "withheld" if protected else "unscored"
        if eligible:
            outcome = "missing" if automatic is None else (
                "matched" if error <= MATCH_RADIUS_PX and 0 <= automatic[0] < width and 0 <= automatic[1] < height else "wrong")
        before = "source_start"
        if rows:
            previous = rows[-1]
            _require(pts > previous["source_pts_ticks"], "Native PTS must strictly increase")
            _require(pts >= previous["source_pts_ticks"] + previous["duration_ticks"],
                     "Native display intervals must not overlap")
            before = ("protected_boundary" if protected or previous["reference_category"] == "withheld"
                      else "segment_boundary" if segment != previous["segment_id"]
                      else "native_discontinuity" if index != previous["source_frame_index"] + 1
                      or pts != previous["source_pts_ticks"] + previous["duration_ticks"] else None)
            previous["boundary_after"] = before
        if before is not None:
            continuity += 1
        decisions = [p["wrong_object_decision"] for p in points]
        rows.append({"source_frame_index": index, "source_pts_ticks": pts, "duration_ticks": duration,
                     "time_base": str(base), "segment_id": segment, "exposure_role": exposure,
                     "continuity_segment_id": continuity, "boundary_before": before, "boundary_after": "source_end",
                     "reference_category": category, "visibility": None if parsed is None else parsed.visibility,
                     "absence_reason": None if parsed is None else parsed.absence_reason,
                     "identity_certainty": None if parsed is None else parsed.game_ball_identity_certainty,
                     "localization_eligible": eligible, "automatic_center_xy_px": automatic,
                     "inference_status": inference_status, "outcome": outcome, "raw_center_error_px": error,
                     "uncertainty_adjusted_error_px": None if error is None else max(0, error - parsed.geometry.uncertainty_radius_px),
                     "published_points": points, "certain_hidden_emissions": len(points) if category == "certain_hidden" else 0,
                     "wrong_object_review_status": "not_applicable" if not points else
                     "pending" if any(d in {"pending", "unknown"} for d in decisions) else "reviewed"})
    _require(consumed == reviews.keys(), "Wrong-object judgment has no matching published point")
    return rows


def _span(rows):
    base = Fraction(rows[0]["time_base"])
    duration = sum((Fraction(row["duration_ticks"]) * base for row in rows), Fraction())
    return {"start_frame_index": rows[0]["source_frame_index"], "end_frame_index": rows[-1]["source_frame_index"],
            "frame_indices": [r["source_frame_index"] for r in rows], "frames": len(rows),
            "start_pts_ticks": rows[0]["source_pts_ticks"],
            "end_exclusive_pts_ticks": rows[-1]["source_pts_ticks"] + rows[-1]["duration_ticks"],
            "time_base": str(base), "duration": _time(duration),
            "segment_id": rows[0]["segment_id"],
            "exposure_role": rows[0]["exposure_role"] if len({r["exposure_role"] for r in rows}) == 1 else "mixed",
            "exposure_roles": sorted({r["exposure_role"] for r in rows})}


def _adjacent(previous, row):
    return (previous["continuity_segment_id"] == row["continuity_segment_id"]
            and previous["source_frame_index"] + 1 == row["source_frame_index"]
            and previous["source_pts_ticks"] + previous["duration_ticks"] == row["source_pts_ticks"])


def _runs(rows, predicate):
    result, current = [], []
    for row in rows:
        if current and (not _adjacent(current[-1], row) or not predicate(row)):
            result.append(current)
            current = []
        if predicate(row):
            current.append(row)
    if current:
        result.append(current)
    return result


def _duration(rows):
    return sum((Fraction(r["duration_ticks"]) * Fraction(r["time_base"]) for r in rows), Fraction())


def _gaps(rows):
    known = _runs(rows, lambda r: r["outcome"] == "missing")
    possible = _runs(rows, lambda r: r["automatic_center_xy_px"] is None and
                     r["reference_category"] not in {"certain_hidden", "withheld"})
    uncertain = [run for run in possible if any(not r["localization_eligible"] for r in run)]
    known_reports = [{**_span(run), "status": "fail" if _duration(run) > MISSING_LIMIT else "pass",
                      "left_boundary": run[0]["boundary_before"], "right_boundary": run[-1]["boundary_after"]}
                     for run in known]
    uncertain_reports = [{**_span(run), "status": "inconclusive" if _duration(run) > MISSING_LIMIT else "pass",
                          "unknown_frame_indices": [r["source_frame_index"] for r in run if not r["localization_eligible"]],
                          "reason": "Reference uncertainty may conceal a continuously eligible missing run."}
                         for run in uncertain]
    boundary_censored = [{**_span(run), "status": "inconclusive", "reason": "Missing run reaches an unscored scope boundary."}
                         for run in known if run[0]["boundary_before"] in UNSCORED_BOUNDARIES
                         or run[-1]["boundary_after"] in UNSCORED_BOUNDARIES]
    status = _combine([r["status"] for r in known_reports + uncertain_reports + boundary_censored])
    if status == "not_applicable" and any(r["localization_eligible"] for r in rows):
        status = "pass"
    return {"gate": _gate(status, limit=_time(MISSING_LIMIT), failure_comparator=">"),
            "known_runs": known_reports, "uncertain_possible_runs": uncertain_reports,
            "scope_censored_runs": boundary_censored,
            "worst_known_duration": _time(max((_duration(r) for r in known), default=Fraction()))}


def _recoveries(rows):
    events = []
    for chunk in _runs(rows, lambda r: True):
        i = 0
        while i < len(chunk):
            start = chunk[i]
            if start["visibility"] != "not_visible" or start["absence_reason"] != "occluded":
                i += 1
                continue
            j = i + 1
            while j < len(chunk) and not chunk[j]["localization_eligible"]:
                j += 1
            intervening = chunk[i:j]
            source_uncertain = any(r["identity_certainty"] != "certain" and r["visibility"] == "not_visible"
                                   or r["reference_category"] in {"indeterminate", "reference_unlabeled", "reference_excluded"}
                                   or r["absence_reason"] == "out_of_frame" for r in intervening)
            event = {"occlusion_start_frame_index": start["source_frame_index"], "occlusion_to_return": _span(intervening),
                     "return_frame_index": None, "first_correct_frame_index": None, "latency": None,
                     "stability_frame_indices": [], "status": "inconclusive", "censored": True, "reasons": []}
            if j == len(chunk):
                event["reasons"].append("No eligible return before " + str(chunk[-1]["boundary_after"]))
                events.append(event)
                break
            event["return_frame_index"] = chunk[j]["source_frame_index"]
            k = j
            while k < len(chunk) and chunk[k]["localization_eligible"]:
                k += 1
            window = chunk[j:k]
            event["eligible_return_window"] = _span(window)
            correct = next((n for n, r in enumerate(window) if r["outcome"] == "matched"), None)
            if correct is None:
                observed_duration = Fraction(window[-1]["source_pts_ticks"] + window[-1]["duration_ticks"]
                                             - window[0]["source_pts_ticks"]) * Fraction(window[0]["time_base"])
                # A missing display interval covering the deadline establishes
                # failure. End exactly at the deadline leaves an unseen frame
                # at that PTS which could still be a timely correct return.
                deadline_observed = observed_duration > RECOVERY_LIMIT
                event["status"] = "fail" if deadline_observed else "inconclusive"
                event["censored"] = not deadline_observed
                event["reasons"].append("No correct observation by the observed deadline." if deadline_observed else
                                         "Eligible return window ended before the recovery deadline was observed.")
            else:
                first = window[correct]
                latency = Fraction(first["source_pts_ticks"] - window[0]["source_pts_ticks"]) * Fraction(first["time_base"])
                stable = window[correct:correct + 3]
                event.update(first_correct_frame_index=first["source_frame_index"], latency=_time(latency),
                             stability_frame_indices=[r["source_frame_index"] for r in stable], censored=len(stable) < 3)
                late = latency > RECOVERY_LIMIT
                unstable = any(r["outcome"] != "matched" for r in stable)
                if late:
                    event["reasons"].append("First correct observation is later than 120 ms.")
                if unstable:
                    event["reasons"].append("First correct observation is not followed by two consecutive correct eligible frames.")
                if len(stable) < 3:
                    event["reasons"].append("Fewer than three consecutive eligible frames remain from first correct observation.")
                event["status"] = "fail" if late or unstable else "inconclusive" if len(stable) < 3 else "pass"
            if source_uncertain:
                event["status"], event["censored"] = "inconclusive", True
                event["reasons"].append("Occlusion identity or the intervening source evidence is uncertain.")
            events.append(event)
            i = k
    return {"gate": _gate(_combine(e["status"] for e in events), limit=_time(RECOVERY_LIMIT),
                          success_comparator="<=", consecutive_correct_frames=3),
            "events": events, "scored_event_count": sum(e["status"] in {"pass", "fail"} for e in events),
            "censored_event_count": sum(e["censored"] for e in events)}


def _wrong_objects(rows):
    confirmed = _runs(rows, lambda r: any(p["wrong_object_decision"] == "confirmed_wrong_object" for p in r["published_points"]))
    pending = [r for r in rows if r["wrong_object_review_status"] == "pending"]
    candidates = _runs(rows, lambda r: r["outcome"] == "wrong")
    reports = [{**_span(run), "status": "fail" if _duration(run) >= WRONG_OBJECT_LIMIT else "pass"} for run in confirmed]
    censored = [{**_span(run), "status": "inconclusive",
                 "reason": "Confirmed wrong-object run reaches an unscored scope boundary."}
                for run in confirmed if run[0]["boundary_before"] in UNSCORED_BOUNDARIES
                or run[-1]["boundary_after"] in UNSCORED_BOUNDARIES]
    status = "fail" if any(r["status"] == "fail" for r in reports) else "inconclusive" if pending or censored else (
        "pass" if any(r["published_points"] for r in rows) else "not_applicable")
    return {"gate": _gate(status, limit=_time(WRONG_OBJECT_LIMIT), failure_comparator=">="),
            "confirmed_runs": reports, "geometric_error_candidate_runs": [_span(run) for run in candidates],
            "scope_censored_runs": censored,
            "pending_frame_indices": [r["source_frame_index"] for r in pending],
            "pending_points": sum(p["wrong_object_decision"] in {"pending", "unknown"} for r in rows for p in r["published_points"]),
            "interpretation": "Geometric errors are review candidates, never automatic proof of a wrong object."}


def _metrics(rows):
    counts = Counter(r["outcome"] for r in rows)
    eligible = sum(counts[k] for k in ("matched", "wrong", "missing"))
    categories = Counter(r["reference_category"] for r in rows)
    hidden = sum(r["certain_hidden_emissions"] for r in rows)
    gaps, recoveries, objects = _gaps(rows), _recoveries(rows), _wrong_objects(rows)
    gates = {"correct_fraction": _gate("not_applicable" if not eligible else "pass" if 100 * counts["matched"] >= 95 * eligible else "fail"),
             "wrong_fraction": _gate("not_applicable" if not eligible else "pass" if 100 * counts["wrong"] <= eligible else "fail"),
             "certain_hidden_emissions": _gate("not_applicable" if not categories["certain_hidden"] else "fail" if hidden else "pass"),
             "missing_continuity": gaps["gate"], "recovery": recoveries["gate"], "wrong_object_runs": objects["gate"]}
    required_matches = (95 * eligible + 99) // 100
    maximum_wrong = eligible // 100
    return {"frames": len(rows), "eligible_frames": eligible, "matched": counts["matched"], "wrong": counts["wrong"],
            "missing": counts["missing"], "unscored": counts["unscored"], "withheld": counts["withheld"],
            "reference_categories": dict(sorted(categories.items())),
            "fractions": {k: {"numerator": counts[k], "denominator": eligible,
                               "value": counts[k] / eligible if eligible else None} for k in ("matched", "wrong", "missing")},
            "certain_hidden_emitted_points": hidden,
            "certain_hidden_emitted_frames": sum(r["certain_hidden_emissions"] > 0 for r in rows),
            "uncertain_hidden_emitted_points": sum(len(r["published_points"]) for r in rows if r["reference_category"] == "uncertain_hidden"),
            "unknown_intervals": [{**_span(run), "categories": sorted({r["reference_category"] for r in run})}
                                  for run in _runs(rows, lambda r: r["reference_category"] not in {"eligible", "certain_hidden", "withheld"})],
            "missing_runs": gaps, "recoveries": recoveries, "wrong_objects": objects,
            "gates": gates, "quantitative_status": _combine(g["status"] for g in gates.values()),
            "resolution_trigger_deficits": {"eligible_errors": counts["wrong"] + counts["missing"],
                "required_matches": required_matches, "maximum_wrong": maximum_wrong,
                "additional_matches_needed": max(0, required_matches - counts["matched"]),
                "wrong_to_correct_needed": max(0, counts["wrong"] - maximum_wrong),
                "minimum_recoverable_errors_for_strict_majority": (counts["wrong"] + counts["missing"]) // 2 + 1,
                "trigger_status": "not_assessed", "fit_authorized_by_this_report": False}}


def _cohort_rows(rows, role):
    """Censor omitted exposure intervals without treating them as source cuts."""
    selected = []
    for i, row in enumerate(rows):
        if row["exposure_role"] != role:
            continue
        row = dict(row)
        if i and rows[i - 1]["exposure_role"] != role and row["boundary_before"] is None:
            row["boundary_before"] = "exposure_subset_boundary"
        if i + 1 < len(rows) and rows[i + 1]["exposure_role"] != role and row["boundary_after"] is None:
            row["boundary_after"] = "exposure_subset_boundary"
        selected.append(row)
    return selected


def score_timeline(timeline, automatic_observations, *, published_observations=None, wrong_object_judgments=None):
    """Return JSON-serializable per-frame, per-exposure and aggregate metrics.

    Aggregate metrics are descriptive when exposure roles differ. Apply the
    plan separately to each possession; protected omissions and human visual
    acceptance are never resolved by an aggregate quantitative result.
    """
    rows = _normalize(timeline, automatic_observations, published_observations, wrong_object_judgments)
    summary = _metrics(rows)
    return {"schema_version": "completion_post_selection_scoring/v0.1", "block_id": timeline.get("block_id"),
            "game_id": timeline.get("game_id"), "possession_id": timeline.get("possession_id"),
            "time_base": str(Fraction(timeline["time_base"])),
            "matching": "inclusive raw 10-source-pixel distance with in-image bounds; uncertainty diagnostic only",
            "automatic_series": "inferred and manual points count absent",
            "published_series": "explicit" if published_observations is not None else "supplied selected-point series",
            "summary": summary,
            "cohorts": {role: {"scope": "descriptive exposure subset; omitted native intervals are censored",
                               **_metrics(_cohort_rows(rows, role))}
                        for role in sorted({r["exposure_role"] for r in rows})},
            "frame_results": rows, "full_possession_acceptance": "not_assessed",
            "limits": ["No protected evaluation or human trajectory acceptance is authorized by this pure report.",
                       "Source segments, exposure roles, accepted references and publication completeness are caller evidence.",
                       "Pending object-identity judgments remain inconclusive; localization distance cannot establish object identity.",
                       "Resolution deficits alone do not satisfy the conditional fallback trigger."]}

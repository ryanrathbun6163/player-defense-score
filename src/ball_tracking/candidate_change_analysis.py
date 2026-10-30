"""Compare sealed existing choices and image margins; never produce a track."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from types import SimpleNamespace

from .annotations import FrameAnnotation
from .completion_scoring import _category

ROOT = Path(__file__).resolve().parents[2]
CONFIG = "configs/ball_tracking/proposals/candidate_change_comparison_v0_1.json"
OUTPUT = "data/outputs/ball_tracking/candidate_change_comparison_v0_1"
FEATURES = ("point", "cls", "peak", "native_mass")
OUTCOMES = ("matched", "wrong", "missing")
STATES = ("both_observed_same_coordinate", "both_observed_different_coordinate",
          "source_observed_target_missing", "source_missing_target_observed", "both_missing")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def bind(path, root=ROOT):
    path = Path(path)
    data = path.read_bytes()
    return {"path": path.resolve().relative_to(root.resolve()).as_posix(),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write_once(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


class Reader:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.bindings = {}

    def data(self, link):
        path = (self.root / link["path"]).resolve()
        check(path.is_relative_to(self.root), "Input outside repository")
        actual = bind(path, self.root)
        check(actual == {k: link[k] for k in actual}, "Input binding differs: " + link["path"])
        self.bindings[actual["path"]] = actual
        return path.read_bytes()

    def json(self, link):
        return json.loads(self.data(link))

    def lines(self, link):
        return [json.loads(line) for line in self.data(link).splitlines()]


def indexed(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[k] for k in fields)
        check(key not in result, "Duplicate row identity")
        result[key] = row
    return result


def outcome(point, reference, width, height):
    if reference is None:
        return "unscored", None
    if point is None:
        return "missing", None
    distance = math.dist(point, reference)
    valid = 0 <= point[0] < width and 0 <= point[1] < height
    return ("matched" if valid and distance <= 10 else "wrong"), distance


def transport_choice(block, frame, native, observation, query, score, descriptor, pool):
    """Consume actual producer records. No proximity or rounded-coordinate join."""
    for key in ("source_frame_index", "source_pts_ticks"):
        check(observation[key] == native[key] == frame[key] == pool[key], "Frame/PTS mismatch")
    check(observation["time_base"] == native["time_base"] == block["time_base"] == pool["time_base"], "Time base mismatch")
    check(observation["source_png"] == native["source_png"] == frame["png"], "PNG identity mismatch")
    check(observation["mean_heatmap_sha256"] == native["mean_heatmap_sha256"] == pool["mean_heatmap_sha256"], "Mean identity mismatch")
    point, selected = observation["center_xy_px"], observation["selected_candidate_index"]
    source = block["source_video"]
    bounds = SimpleNamespace(width_px=source["width_px"], height_px=source["height_px"])
    annotation = FrameAnnotation.from_mapping(frame["annotation"], 0, bounds)
    category = _category(annotation)  # Explicit reuse of accepted parser/category semantics.
    reference = list(annotation.geometry.center_xy_px) if category == "eligible" else None
    result, distance = outcome(point, reference, bounds.width_px, bounds.height_px)
    identity = None
    native_index = None
    if selected is None:
        check(observation["state"] == "missing" and point is None and query is None, "Missing choice fabricated")
        features = {name: None for name in FEATURES}
        reasons = {name: "missing_selection" for name in FEATURES}
        extraction, geometry, input_id, query_id = "missing_selection", "missing_selection", None, None
    else:
        check(observation["state"] == "observed" and len(point) == 2
              and all(math.isfinite(v) for v in point), "Invalid observed choice")
        if query is None:
            features = {name: None for name in FEATURES}
            reasons = {name: "cache_unavailable" for name in FEATURES}
            extraction, geometry, input_id, query_id = "unknown_extraction", "cache_unavailable", None, None
        else:
            check(query["source_video"] == source and query["source_role"] == "checkpoint_validation", "Source/role mismatch")
            check(all(query[k] == frame[k] for k in ("source_frame_index", "source_pts_ticks", "duration_ticks"))
                  and query["block_id"] == block["block_id"] and query["time_base"] == block["time_base"]
                  and query["source_png"] == observation["source_png"] and query["center_xy_px"] == point,
                  "Query geometry/clock/PNG mismatch")
            if query["cohort"] == "HOU_stress":
                check(query["observation"] == observation, "Stress observation identity mismatch")
                if selected < len(native["candidates"]):
                    c = native["candidates"][selected]
                    check(point == [c["center_x"], c["center_y"]] and observation["native_score"] == c["native_score"], "Stress native prefix mismatch")
                    native_index = selected
                extraction = "native_component" if native_index is not None else "broad_weak_selected"
                identity = [query["stress_choice_source"]["sha256"], selected]
            else:
                check(query["cohort"] == "HOU_main", "Unexpected query cohort")
                c = pool["candidates"][selected]
                check(query["candidate"] == c and c["candidate_index"] == selected
                      and point == [c["center_x"], c["center_y"]], "Main candidate identity mismatch")
                native_index = c["original_index"]
                if native_index is not None:
                    check(native_index == selected and all(c.get(k) == v for k, v in native["candidates"][selected].items()), "Native prefix differs")
                extraction = c["extraction"]
                identity = [query["main_pool"]["sha256"], selected]
            if native_index is not None:
                identity = [source["sha256"], frame["source_frame_index"], observation["mean_heatmap_sha256"], "native", native_index]
            query_id, input_id, geometry = query["query_id"], query["input_id"], query["geometry"]["status"]
            check(score is not None and score["query_id"] == query_id and score["input_id"] == input_id
                  and score["block_id"] == block["block_id"] and score["frame"] == frame["source_frame_index"], "Score query join differs")
            features, reasons = {}, {}
            for name in ("cls", "point"):
                readout = score["readouts"][name]
                features[name] = readout["margin"]
                if features[name] is None:
                    reasons[name] = readout["reason"]
            check(descriptor is not None and descriptor["query_id"] == query_id, "Descriptor query join differs")
            features["peak"] = descriptor["features"]["peak"]
            if features["peak"] is None:
                reasons["peak"] = descriptor.get("feature_unknown_reasons", {}).get("peak", "saved_peak_unavailable")
            features["native_mass"] = observation["native_score"] if native_index is not None else None
            if native_index is None:
                reasons["native_mass"] = "incomparable_nonnative_extraction"
            for name, value in features.items():
                check(value is None or (not isinstance(value, bool) and math.isfinite(value)), "Invalid feature value")
    return {"state": observation["state"], "center_xy_px": point, "selected_candidate_index": selected,
            "query_id": query_id, "input_id": input_id, "candidate_identity": identity,
            "native_index": native_index, "extraction": extraction, "geometry_status": geometry,
            "features": features, "feature_unknown_reasons": reasons, "reference_category": category,
            "outcome": result, "localization_distance_px": distance, "reference_xy_px": reference,
            "native_score_as_emitted": observation["native_score"],
            "selection_diagnostic": observation.get("selection_diagnostic"),
            "source_png": observation["source_png"], "mean_heatmap_sha256": observation["mean_heatmap_sha256"]}


def compare_choices(source, target):
    present_a, present_b = source["state"] == "observed", target["state"] == "observed"
    category = source["reference_category"]
    check(category == target["reference_category"], "Reference category mismatch")
    same = present_a and present_b and source["center_xy_px"] == target["center_xy_px"]
    state = ("both_observed_same_coordinate" if same else "both_observed_different_coordinate" if present_a and present_b else
             "source_observed_target_missing" if present_a else "source_missing_target_observed" if present_b else "both_missing")
    transition = source["outcome"] + "->" + target["outcome"]
    discriminating = category == "eligible" and state == "both_observed_different_coordinate" and {source["outcome"], target["outcome"]} == {"matched", "wrong"}
    detail = {}
    for name in FEATURES:
        a, b = source["features"][name], target["features"][name]
        if name == "native_mass" and (source["native_index"] is None or target["native_index"] is None):
            a = b = None
        reason = None
        if a is None or b is None:
            reason = {"source": source["feature_unknown_reasons"].get(name), "target": target["feature_unknown_reasons"].get(name)}
            if name == "native_mass" and (source["native_index"] is None or target["native_index"] is None):
                reason["pair"] = "incomparable_nonnative_extraction"
        delta = None if a is None or b is None else b - a
        preference = "unavailable" if delta is None else "target" if delta > 0 else "source" if delta < 0 else "tie"
        correct = ("not_discrimination_pair" if not discriminating else "unavailable" if delta is None else "tie" if delta == 0 else
                   "correct_side" if (preference == "source") == (source["outcome"] == "matched") else "wrong_side")
        detail[name] = {"delta_target_minus_source": delta, "preference": preference,
                        "correct_side_status": correct, "unavailable_reason": reason}
    return {"choice_state": state, "coordinate_agreement": same,
            "candidate_identity_agreement": bool(present_a and present_b and source["candidate_identity"] is not None
                                                  and source["candidate_identity"] == target["candidate_identity"]),
            "reference_category": category, "outcome_transition": transition,
            "exactly_one_correct_observed_pair": discriminating, "features": detail,
            "visibility_interpretation": "neither_emission_valid" if category == "certain_hidden" and present_a and present_b else
                                         "not_localization_scored" if category != "eligible" else "localization_only_not_semantic_identity",
            "extraction_pair": source["extraction"] + "->" + target["extraction"],
            "padding_pair": source["geometry_status"] + "->" + target["geometry_status"]}


def summarize(rows):
    result = {"declared_rows": len(rows), "choice_states": {s: 0 for s in STATES},
              "reference_categories": {}, "eligible_transition_matrix": {a + "->" + b: 0 for a in OUTCOMES for b in OUTCOMES},
              "two_observed": 0, "distinct_coordinates": 0, "exactly_one_correct_pairs": 0,
              "candidate_identity_agreements": 0, "features": {}, "joint_preference_signs": {}, "point_vs_control_correct_side": {}}
    categories, signs = Counter(), Counter()
    for r in rows:
        result["choice_states"][r["choice_state"]] += 1
        categories[r["reference_category"]] += 1
        result["candidate_identity_agreements"] += r["candidate_identity_agreement"]
        result["two_observed"] += r["choice_state"].startswith("both_observed")
        result["distinct_coordinates"] += r["choice_state"] == "both_observed_different_coordinate"
        result["exactly_one_correct_pairs"] += r["exactly_one_correct_observed_pair"]
        if r["reference_category"] == "eligible":
            result["eligible_transition_matrix"][r["outcome_transition"]] += 1
        signs["|".join(r["features"][f]["preference"] for f in FEATURES)] += 1
    result["reference_categories"], result["joint_preference_signs"] = dict(categories), dict(signs)
    for name in FEATURES:
        preference = Counter(r["features"][name]["preference"] for r in rows)
        disc = [r for r in rows if r["exactly_one_correct_observed_pair"]]
        eligible = categories["eligible"]
        result["features"][name] = {
            "all_rows_preference": dict(preference),
            "complete_observed_pairs": len(rows) - preference["unavailable"],
            "unavailable_rows_including_missing": preference["unavailable"],
            "distinct_coordinate_complete_pairs": sum(r["choice_state"] == "both_observed_different_coordinate" and r["features"][name]["preference"] != "unavailable" for r in rows),
            "exactly_one_correct": dict(Counter(r["features"][name]["correct_side_status"] for r in disc)),
            "exactly_one_correct_total": len(disc),
            "eligible_rows_outside_discrimination_pairs": eligible - len(disc),
            "unscored_reference_rows": len(rows) - eligible}
    for control in ("cls", "peak", "native_mass"):
        result["point_vs_control_correct_side"][control] = dict(Counter(
            r["features"]["point"]["correct_side_status"] + "|" + r["features"][control]["correct_side_status"]
            for r in rows if r["exactly_one_correct_observed_pair"]))
    return result


def grouped(rows, field):
    groups = defaultdict(list)
    for row in rows:
        for key in row[field] if field == "tags" else [row[field]]:
            groups[key].append(row)
    return {key: summarize(values) for key, values in groups.items()}


def load_choices(root=ROOT):
    """Full source/consumer transport; called only by the authorized run."""
    root = Path(root).resolve()
    reader = Reader(root)
    config = reader.json(bind(root / CONFIG, root))
    check(config["schema_version"] == "candidate_change_comparison/v0.1" and config["population"]["frames"] == 960,
          "Unexpected declared scope")
    reader.data(config["protocol"])
    inventory = reader.json(config["inventory"])
    joins = indexed(reader.lines(config["choice_cache_joins"]), ("block_id", "frame", "arm"))
    analysis = reader.json(config["inputs"]["point_analysis"])
    for link in config["inputs"].values():
        reader.data(link)
    inputs = {link["path"]: link for link in inventory["bindings"]}
    package_link = next(link for link in inputs.values() if link["path"].endswith("paired_review_inputs_v0_1.json"))
    query_link = next(link for link in inputs.values() if link["path"].endswith("attempt_003/queries.jsonl"))
    package = reader.json(package_link)
    queries = indexed(reader.lines(query_link), ("query_id",))
    scores = indexed(analysis["query_margin_rows"], ("query_id",))
    diagnostics = indexed(analysis["joined_HOU_frame_diagnostics"], ("block_id", "frame"))
    original = reader.json(config["inputs"]["original_comparison"])
    followup = reader.json(config["inputs"]["followup_comparison"])
    old = indexed(original["records"], ("block_id",))
    new = indexed(followup["records"], ("block_id",))
    declared = {b["block_id"]: b for b in config["population"]["blocks"]}
    frames_out = []
    for entry in package["blocks"]:
        block = entry["block"]
        bid = block["block_id"]
        if bid not in declared:
            continue
        check(block["human_review"]["status"] == "accepted" and block["role"] == "checkpoint_validation", "Reference authority differs")
        for link in block["reference_bindings"]:
            reader.data(link)
        check(block["source_video"] == declared[bid]["source_video"] and block["range_inclusive"] == declared[bid]["range_inclusive"], "Declared block differs")
        previous, current = old[bid,], new[bid,]
        pools = indexed(reader.lines(current["pool_source"]), ("source_frame_index",))
        series, saved_scores, links = {}, {}, {}
        for arm in config["population"]["arms"]:
            link = previous["variants"][arm] if arm in previous["variants"] else current["variants"][arm]
            data = reader.json(link)
            check(data["block_id"] == bid, "Wrong series block")
            if arm != "native":
                check(data["references_used_in_selection"] is False, "Reference-conditioned producer")
            series[arm] = indexed(data["observations"], ("source_frame_index",))
            links[arm] = link
            score_link = current["control_scores"][arm] if arm in current["control_scores"] else current["scores"][arm]
            saved_scores[arm] = indexed(reader.json(score_link)["frame_results"], ("source_frame_index",))
        for frame, original_native in zip(block["frames"], entry["candidate_observations"], strict=True):
            fi = frame["source_frame_index"]
            native, pool, diag = series["native"][fi,], pools[fi,], diagnostics[bid, fi]
            check(native == original_native, "Native baseline differs")
            choices = {}
            for arm in config["population"]["arms"]:
                observation = series[arm][fi,]
                cached = joins[bid, fi, arm]
                qid = cached["query_id"]
                query = queries.get((qid,))
                check(cached["center_xy_px"] == observation["center_xy_px"] and cached["selected_candidate_index"] == observation["selected_candidate_index"]
                      and cached["state"] == observation["state"], "Prepared choice join differs")
                descriptor = None
                if query is not None:
                    check(query["main_pool"] == current["pool_source"]
                          and query["stress_choice_source"] == previous["variants"]["sequence_weak"], "Query source binding differs")
                    descriptor = diag["stress"] if arm == "sequence_weak" else diag["candidates"][observation["selected_candidate_index"]]
                choice = transport_choice(block, frame, native, observation, query, scores.get((qid,)), descriptor, pool)
                saved = saved_scores[arm][fi,]
                check(all(saved[k] == frame[k] for k in ("source_frame_index", "source_pts_ticks", "duration_ticks"))
                      and saved["time_base"] == block["time_base"]
                      and saved["reference_category"] == choice["reference_category"]
                      and saved["outcome"] == choice["outcome"]
                      and saved["automatic_center_xy_px"] == choice["center_xy_px"], "Saved scorer transport differs")
                check(choice["input_id"] == cached["input_id"], "Input cache identity differs")
                choice["series_binding"] = links[arm]
                choices[arm] = choice
            check(choices["native"]["reference_category"] == diag["reference_category"], "Category diagnostic differs")
            frames_out.append({"block_id": bid, "frame": fi, "source_video": block["source_video"],
                               "source_pts_ticks": frame["source_pts_ticks"], "duration_ticks": frame["duration_ticks"],
                               "time_base": block["time_base"], "choices": choices})
        expected = {(f["source_frame_index"],) for f in block["frames"]}
        check(all(set(s) == expected for s in [pools, *series.values(), *saved_scores.values()]), "Dropped/extra source frame")
    check(len(frames_out) == 960 and len(joins) == 6720, "Full declared census differs")
    check(Counter(f["choices"]["native"]["reference_category"] for f in frames_out) == config["population"]["reference_categories"], "Reference partition differs")
    return config, reader, frames_out, analysis["historical_separate"]


def frame_tags(frame):
    choices = frame["choices"]
    native, strong, broad = (choices[n] for n in ("native", "motion_and_speed", "sequence_weak"))
    tags = []
    if native["outcome"] in OUTCOMES and native["reference_category"] == "eligible":
        tags.append({"matched": "all842_native_correct", "wrong": "all19_native_wrong", "missing": "all21_native_missing_eligible"}[native["outcome"]])
    if native["reference_category"] != "eligible":
        tags.append("all_" + native["reference_category"])
    if frame["block_id"].endswith("e01") and 194 <= frame["frame"] <= 203:
        tags.append("e01_frames194_203_ten_recoveries")
    if frame["block_id"].endswith("e05") and 14 <= frame["frame"] <= 19:
        tags.append("e05_frames14_19_six_below_.01_broad_gains")
    if native["outcome"] == "missing" and broad["outcome"] == "matched":
        tags.append("all21_old_broad_gains_from_native_missing")
    if native["outcome"] != "matched" and strong["outcome"] == "matched":
        tags.append("six_corrected_strong_gains")
    if native["outcome"] == "matched" and strong["outcome"] != "matched":
        tags.append("27_corrected_strong_losses_including_two_missing")
    return tags


def make_rows(frames, contrasts):
    rows = []
    for contrast in contrasts:
        label = contrast["source"] + "__to__" + contrast["target"]
        for frame in frames:
            a, b = (frame["choices"][contrast[k]] for k in ("source", "target"))
            tags = frame_tags(frame)
            tags += sorted({c["geometry_status"] for c in (a, b)} & {"complete_source_crop", "padded_source_crop"})
            tags += sorted({"native_extraction" if c["native_index"] is not None else "weak_extraction"
                            for c in (a, b) if c["state"] == "observed"})
            row = {"row_id": f"{label}:{frame['block_id']}:{frame['frame']}", "contrast": label, "role": contrast["role"],
                   **{k: frame[k] for k in ("block_id", "frame", "source_pts_ticks", "duration_ticks", "time_base")},
                   "source_arm": contrast["source"], "target_arm": contrast["target"],
                   "source_choice": a, "target_choice": b, "tags": tags, **compare_choices(a, b)}
            rows.append(row)
    return rows


def summarize_contrast(rows):
    cross = Counter("|".join((r["block_id"], r["reference_category"], r["choice_state"], r["outcome_transition"])) for r in rows)
    return {"all": summarize(rows), "episodes": grouped(rows, "block_id"),
            "episodes_by_category": {bid: grouped([r for r in rows if r["block_id"] == bid], "reference_category")
                                     for bid in dict.fromkeys(r["block_id"] for r in rows)},
            "categories": grouped(rows, "reference_category"), "transitions": grouped(rows, "outcome_transition"),
            "choice_states": grouped(rows, "choice_state"), "extraction_pairs": grouped(rows, "extraction_pair"),
            "padding_pairs": grouped(rows, "padding_pair"), "tags": grouped(rows, "tags"),
            "episode_category_state_transition_cross_tab": dict(cross)}


def resources():
    result = {"process_cpu_seconds": os.times().user + os.times().system}
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Memory(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        values = Memory(); values.cb = ctypes.sizeof(values)
        kernel = ctypes.WinDLL("kernel32"); kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi"); psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Memory), wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(values), values.cb):
            result.update(peak_process_working_set_bytes=values.PeakWorkingSetSize, current_process_working_set_bytes=values.WorkingSetSize)
    return result


def execute(root=ROOT):
    root = Path(root).resolve()
    directory = root / OUTPUT
    reader = Reader(root)
    freeze = reader.json(bind(directory / "execution_freeze.json", root))
    check(freeze["authorized_CPU_analysis"] is True, "Execution authority missing")
    check(freeze["config"] == bind(root / CONFIG, root), "Frozen design differs")
    for link in freeze["implementation_and_tests"]:
        reader.data(link)
    destination = directory / "analysis_v0_1"
    check(not destination.exists(), "Preserve prior attempt; no automatic overwrite")
    destination.mkdir()
    started = time.perf_counter()
    write_once(destination / "started.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(),
                                              "freeze": bind(directory / "execution_freeze.json", root)})
    try:
        config, inputs, frames, historical = load_choices(root)
        rows = make_rows(frames, config["population"]["contrasts"])
        check(len(rows) == config["population"]["contrast_frame_rows"], "Contrast census differs")
        checks = Counter(tag for frame in frames for tag in frame_tags(frame))
        check(all(checks[tag] == n for tag, n in {"all842_native_correct": 842, "all19_native_wrong": 19,
              "all21_native_missing_eligible": 21, "all21_old_broad_gains_from_native_missing": 21,
              "six_corrected_strong_gains": 6, "27_corrected_strong_losses_including_two_missing": 27}.items()), "Named cohort differs")
        choices_path = destination / "choices.jsonl"
        with choices_path.open("x", encoding="utf-8", newline="\n") as stream:
            for frame in frames:
                stream.write(json.dumps(frame, allow_nan=False, separators=(",", ":")) + "\n")
        pairs_path = destination / "comparisons.jsonl"
        with pairs_path.open("x", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")
        summaries = {name: summarize_contrast([r for r in rows if r["contrast"] == name]) for name in dict.fromkeys(r["contrast"] for r in rows)}
        arm_census = {}
        for arm in config["population"]["arms"]:
            group = [f["choices"][arm] for f in frames]
            arm_census[arm] = {"states": dict(Counter(c["state"] for c in group)),
                              "eligible_outcomes": dict(Counter(c["outcome"] for c in group if c["reference_category"] == "eligible")),
                              "certain_hidden_emissions": sum(c["reference_category"] == "certain_hidden" and c["state"] == "observed" for c in group),
                              "uncertain_hidden_emissions": sum(c["reference_category"] == "uncertain_hidden" and c["state"] == "observed" for c in group)}
        exceptions = {"harmful_feature_preferences": [], "beneficial_revisions": [], "unavailable_features_including_missing_and_incomparable_mass": [], "hidden_emission_agreements": []}
        for row in rows:
            if any(d["correct_side_status"] == "wrong_side" for d in row["features"].values()):
                exceptions["harmful_feature_preferences"].append(row["row_id"])
            if row["target_choice"]["outcome"] == "matched" and row["source_choice"]["outcome"] in ("wrong", "missing"):
                exceptions["beneficial_revisions"].append(row["row_id"])
            if any(d["preference"] == "unavailable" for d in row["features"].values()):
                exceptions["unavailable_features_including_missing_and_incomparable_mass"].append(row["row_id"])
            if row["reference_category"] == "certain_hidden" and row["choice_state"].startswith("both_observed"):
                exceptions["hidden_emission_agreements"].append(row["row_id"])
        completed = {"status": "completed_reference_assisted_diagnosis_no_new_policy", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                     "elapsed_seconds": time.perf_counter() - started, "freeze": bind(directory / "execution_freeze.json", root),
                     "resources_before_completion_serialization": resources(),
                     "source": bind(Path(__file__), root), "inputs": list(inputs.bindings.values()),
                     "choices": bind(choices_path, root), "comparisons": bind(pairs_path, root),
                     "frames": len(frames), "contrast_frame_rows": len(rows), "arm_census": arm_census,
                     "frame_tags_overlapping": dict(checks), "contrasts": summaries, "exception_row_ids": exceptions,
                     "historical_appendix_reused_unchanged": historical,
                     "known_adverse_evidence_unchanged": config["known_adverse_evidence_must_accompany_results"],
                     "new_model_calls": 0, "new_selector_runs": 0, "new_tracking_outputs": 0, "new_training_updates": 0,
                     "new_labels": 0, "protected_access": False, "human_trajectory_acceptance": None,
                     "limits": ["Exposed HOU development; overlapping contrasts/tags and neighboring frames are not independent.",
                                "Parser/category kernel reused; outcomes checked against original saved scores.",
                                "Cached margins reused; no model/token/cosine recomputation or new semantic labels.",
                                "Relative ordering cannot establish visibility or compare image evidence against missing.",
                                "No trajectory, policy, thresholds, fitting or automatic acceptance follows."]}
        write_once(destination / "completed.json", completed)
        return {"status": completed["status"], "completed": bind(destination / "completed.json", root), "elapsed_seconds": completed["elapsed_seconds"]}
    except Exception as error:
        write_once(destination / "failed.json", {"error_type": type(error).__name__, "error": str(error),
                                                "elapsed_seconds": time.perf_counter() - started})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(execute()))


if __name__ == "__main__":
    main()

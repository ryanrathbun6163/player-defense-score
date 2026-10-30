"""Separate fixed-zero veto arm over immutable saved continuous emissions.

Pure metadata functions: no source images, inference, sampling, or file writes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import copy
import math

from . import nba_temporal_gap_selection as geometry

SCHEMA = "nba_ball_distractor_policy/v0.1"
EMISSION_FIELDS = ("selected_center_xy_px", "selected_provenance_id", "selected_pool_record_index",
                   "selected_coordinate_group", "selected_component", "selected_native_score")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def key(row):
    return row.get("continuous_source_id", row.get("candidate_id")), row["source_frame_index"]


def parse_key(value):
    if isinstance(value, tuple) and len(value) == 2:
        cid,index = value
    elif isinstance(value,str):
        text = value[len("emission:"):] if value.startswith("emission:") else value
        cid,index = text.rsplit(":",1); index = int(index)
    else:
        raise ValueError("Expected source/frame tuple or emission:source:frame key")
    require(isinstance(cid,str) and cid and type(index) is int and index >= 0, "Invalid emission key")
    return cid,index


def emission_key(cid, index):
    return f"emission:{cid}:{index}"


def emission(row):
    return {field: copy.deepcopy(row.get(field)) for field in EMISSION_FIELDS}


def finite_logit(value):
    require(not isinstance(value,bool), "Boolean is not a logit")
    result = float(value)
    require(math.isfinite(result), "Nonfinite emission logit")
    return result


def index_selection(selection):
    """Independently validate all producer representations and native timelines."""
    require(selection["schema_version"] == "nba_temporal_gap_continuous/v0.1", "Saved continuous selection schema differs")
    sources, indexed, segments, flat, windows, protected = {}, {}, [], [], [], []
    for source in selection["sources"]:
        cid = source["candidate_id"]
        require(cid not in sources, "Duplicate source")
        sources[cid] = source
        local = {}
        for segment in source["segments"]:
            require(segment["candidate_id"] == cid, "Segment source differs")
            lo,hi = segment["range_inclusive"]
            rows = segment["frames"]
            require([r["source_frame_index"] for r in rows] == list(range(lo,hi+1)), "Segment has missing/reordered native frames")
            require(all(a["source_pts_ticks"] < b["source_pts_ticks"] for a,b in zip(rows,rows[1:])), "Segment native PTS are not increasing")
            for row in rows:
                pair = key(row)
                require(pair[0] == cid and pair not in indexed and row["segment_id"] == segment["segment_id"], "Duplicate frame or segment join differs")
                require(row["source_video"] == source["source_video"] and row["source_frame"]["source_frame_index"] == pair[1]
                        and row["source_frame"]["source_pts_ticks"] == row["source_pts_ticks"], "Native source/frame/PTS differs")
                require(not any(a <= pair[1] <= b for a,b in source["protected_ranges"]), "Protected frame entered processed segment")
                before,selected,decision = row["baseline_center_xy_px"],row["selected_center_xy_px"],row["decision"]
                require((decision == "preserved_original" and before is not None and before == selected)
                        or (decision == "filled_saved_candidate" and before is None and selected is not None)
                        or (decision == "abstained" and before is None and selected is None), "Saved original/fill/missing semantics differ")
                if selected is not None:
                    index = row["selected_pool_record_index"]
                    records = row["candidate_pool"]["records"]
                    require(type(index) is int and 0 <= index < len(records), "Selected pool index invalid")
                    record = records[index]; component = record["component"]
                    require(row["selected_provenance_id"] == record["provenance_id"] and row["selected_component"] == component
                            and selected == [component["center_x"],component["center_y"]]
                            and row["selected_native_score"] == component["native_score"], "Saved selected coordinate/provenance differs from producer pool")
                indexed[pair] = row; local[pair[1]] = row
            segments.append((source,segment)); windows.append(segment); flat.extend(rows)
        timeline = source["frames"]
        require(len({r["source_frame_index"] for r in timeline}) == len(timeline), "Duplicate timeline position")
        require(all(a["source_frame_index"]+1 == b["source_frame_index"] and a["source_pts_ticks"] < b["source_pts_ticks"] for a,b in zip(timeline,timeline[1:])), "Timeline frames/PTS not contiguous")
        require(timeline and timeline[-1]["source_pts_ticks"] < source["source_end_exclusive_pts_ticks"], "Invalid native final hold")
        seen = set()
        for row in timeline:
            index = row["source_frame_index"]
            withheld = any(a <= index <= b for a,b in source["protected_ranges"])
            require(row["candidate_id"] == cid, "Timeline source differs")
            if withheld:
                require(row["decision"] == "withheld" and row["segment_id"] is None and row["baseline_center_xy_px"] is None
                        and all(row.get(k) is None for k in EMISSION_FIELDS) and index not in local, "Protected timeline carries an observation")
                protected.append((cid,index))
            else:
                require(index in local and row == local[index], "Nested timeline/segment decision differs")
                seen.add(index)
        require(seen == set(local), "Timeline omitted processed frames")
    require(selection["frames"] == flat, "Top-level frames differ from nested segment frames")
    require(selection["windows"] == windows, "Top-level windows differ from source segments")
    return sources,indexed,segments,protected


def _scoremap(scoremap, indexed):
    result = {}
    for raw,value in scoremap.items():
        pair = parse_key(raw)
        require(pair not in result, "Duplicate normalized emission score key")
        result[pair] = finite_logit(value)
    expected = {pair for pair,row in indexed.items() if row["selected_center_xy_px"] is not None}
    require(set(result) == expected, "Scores must cover exactly saved emissions; no missing/protected positions")
    return result


def _filled_gaps(segments, indexed, scores):
    gaps, memberships, ids = [], {}, set()
    for source,segment in segments:
        cid = source["candidate_id"]
        for gap in segment["gaps"]:
            gid = gap["gap_id"]
            require(gid not in ids, "Duplicate saved gap ID"); ids.add(gid)
            lo,hi = gap["source_frame_range_inclusive"]
            require(segment["range_inclusive"][0] <= lo <= hi <= segment["range_inclusive"][1], "Gap escapes native segment")
            fills = [indexed[cid,i] for i in range(lo,hi+1)]
            require(all(r["gap_id"] == gid and r["baseline_center_xy_px"] is None for r in fills), "Gap frame membership differs")
            if gap["status"] != "filled":
                require(all(r["selected_center_xy_px"] is None for r in fills), "Abstained gap has a saved fill")
                continue
            require(all(r["decision"] == "filled_saved_candidate" for r in fills), "Filled gap has incomplete saved output")
            anchors = gap["anchors"]
            require(isinstance(anchors,list) and len(anchors) == 2
                    and [a["source_frame_index"] for a in anchors] == [lo-1,hi+1], "Filled gap requires two adjacent original anchors")
            members = []
            for anchor in anchors:
                pair = cid,anchor["source_frame_index"]
                require(pair in indexed, "Anchor missing from same saved selection")
                row = indexed[pair]
                require(row["segment_id"] == segment["segment_id"] and row["decision"] == "preserved_original"
                        and row["baseline_center_xy_px"] == anchor["baseline_center_xy_px"]
                        and row["source_pts_ticks"] == anchor["source_pts_ticks"], "Gap anchor is not the bound original point")
                members.append({"candidate_id":cid,"source_frame_index":pair[1],"role":"original_anchor","logit":scores[pair]})
            members.extend({"candidate_id":cid,"source_frame_index":r["source_frame_index"],"role":"saved_fill","logit":scores[key(r)]} for r in fills)
            failed = [m for m in members if m["logit"] <= 0]
            result = {"gap_id":gid,"candidate_id":cid,"segment_id":segment["segment_id"],"source_frame_range_inclusive":[lo,hi],
                "members":members,"failed_members":failed,"retained":not failed,
                "reason":"all_original_anchors_and_fills_strictly_positive" if not failed else "gap_member_nonpositive"}
            gaps.append(result)
            for row in fills:
                require(key(row) not in memberships, "Fill belongs to multiple gaps")
                memberships[key(row)] = result
    require(set(memberships) == {pair for pair,row in indexed.items() if row["decision"] == "filled_saved_candidate"}, "Saved fill not bound to exactly one complete gap")
    return gaps,memberships


def _segment_end(source,segment):
    following = segment["range_inclusive"][1]+1
    next_row = next((r for r in source["frames"] if r["source_frame_index"] == following),None)
    return next_row["source_pts_ticks"] if next_row else source["source_end_exclusive_pts_ticks"]


def missing_intervals(sources):
    result = []
    for source in sources:
        for segment in source["segments"]:
            rows = segment["frames"]; final_end = _segment_end(source,segment)
            for arm in ("saved","policy"):
                runs,offset = [],0
                def missing(row):
                    return (row["saved_emission"]["selected_center_xy_px"] if arm == "saved" else row["selected_center_xy_px"]) is None
                while offset < len(rows):
                    if not missing(rows[offset]):
                        offset += 1; continue
                    start = offset
                    while offset < len(rows) and missing(rows[offset]): offset += 1
                    end_pts = rows[offset]["source_pts_ticks"] if offset < len(rows) else final_end
                    runs.append({"source_frame_range_inclusive":[rows[start]["source_frame_index"],rows[offset-1]["source_frame_index"]],
                        "frames":offset-start,"start_pts_ticks":rows[start]["source_pts_ticks"],"end_exclusive_pts_ticks":end_pts,
                        "duration_ticks":end_pts-rows[start]["source_pts_ticks"],"duration_seconds":(end_pts-rows[start]["source_pts_ticks"])/90000})
                result.append({"candidate_id":source["candidate_id"],"segment_id":segment["segment_id"],"arm":arm,
                    "intervals":runs,"missing_frames":sum(r["frames"] for r in runs),"missing_duration_ticks":sum(r["duration_ticks"] for r in runs)})
    return result


def apply(selection, scoremap):
    """Veto originals individually and existing fills only as whole saved gaps."""
    sources,indexed,segments,protected = index_selection(selection)
    scores = _scoremap(scoremap,indexed); gaps,memberships = _filled_gaps(segments,indexed,scores)
    rows = []; by_key = {}
    for original in selection["frames"]:
        pair = key(original); before = emission(original); logit = scores.get(pair)
        if original["decision"] == "abstained":
            retained,decision,reason = False,"original_missing","saved_missing_unchanged"
        elif original["decision"] == "preserved_original":
            retained = logit >= 0
            decision = "retained_original" if retained else "vetoed_original"
            reason = "original_nonnegative" if retained else "original_negative"
        else:
            retained = memberships[pair]["retained"]
            decision = "retained_gap_fill" if retained else "revoked_gap_fill"
            reason = memberships[pair]["reason"]
        row = {"candidate_id":pair[0],"source_frame_index":pair[1],"source_pts_ticks":original["source_pts_ticks"],
            "container_pts_ticks":original.get("container_pts_ticks"),"source_frame":copy.deepcopy(original["source_frame"]),
            "segment_id":original["segment_id"],"gap_id":original["gap_id"],"saved_decision":original["decision"],
            "original_baseline_center_xy_px":copy.deepcopy(original["baseline_center_xy_px"]),"saved_emission":before,
            **(copy.deepcopy(before) if retained else {field:None for field in EMISSION_FIELDS}),
            "logit":logit,"policy_decision":decision,"reason":reason,
            "removed":before["selected_center_xy_px"] is not None and not retained,
            "direct_negative":logit is not None and logit < 0,
            "removed_only_by_gap_dependency":decision == "revoked_gap_fill" and logit > 0}
        rows.append(row); by_key[pair] = row
    output_sources = []
    for source in selection["sources"]:
        cid = source["candidate_id"]
        timeline = []
        for original in source["frames"]:
            pair = cid,original["source_frame_index"]
            if pair in by_key:
                timeline.append(by_key[pair])
            else:
                timeline.append({**copy.deepcopy(original),"policy_decision":"withheld","logit":None,"removed":False,
                                 "saved_emission":emission(original)})
        output_sources.append({**copy.deepcopy({k:v for k,v in source.items() if k not in {"frames","segments"}}),
            "frames":timeline,"segments":[{"segment_id":s["segment_id"],"range_inclusive":copy.deepcopy(s["range_inclusive"]),
                "frames":[by_key[key(r)] for r in s["frames"]]} for s in source["segments"]]})
    return {"schema_version":SCHEMA,"arm":"fixed_zero_appearance_veto","frames":rows,"sources":output_sources,"gaps":gaps,
        "summary":{"processed_frames":len(rows),"protected_frames":len(protected),"saved_emissions":len(scores),
            "retained_emissions":sum(r["selected_center_xy_px"] is not None for r in rows),
            "original_missing_positions":sum(r["saved_decision"] == "abstained" for r in rows),
            "decisions":dict(Counter(r["policy_decision"] for r in rows)),"revoked_gaps":sum(not g["retained"] for g in gaps),
            "direct_negative_removals":sum(r["removed"] and r["direct_negative"] for r in rows),
            "positive_fill_dependency_removals":sum(r["removed_only_by_gap_dependency"] for r in rows)},
        "missing_intervals":missing_intervals(output_sources),"new_coordinates":0,"new_fills":0,
        "human_trajectory_review":"pending","adopted":False}


def _validate_policy(policy, selection):
    _,indexed,_,_ = index_selection(selection)
    actual = {key(r):r for r in policy["frames"]}
    require(len(actual) == len(policy["frames"]) and list(actual) == list(indexed), "Policy frame inventory/order differs")
    for pair,before in indexed.items():
        after = actual[pair]
        require(after["saved_emission"] == emission(before) and after["source_frame"] == before["source_frame"]
                and after["source_pts_ticks"] == before["source_pts_ticks"] and after["segment_id"] == before["segment_id"], "Policy source or saved point/provenance changed")
        if after["selected_center_xy_px"] is not None:
            require(emission(after) == emission(before) and before["selected_center_xy_px"] is not None, "Policy introduced or changed a coordinate/provenance")
        else:
            require(all(after.get(field) is None for field in EMISSION_FIELDS), "Missing policy point retains selected provenance")
        require(after["removed"] == (before["selected_center_xy_px"] is not None and after["selected_center_xy_px"] is None), "Policy removed flag differs")
    # Validate the complete transport package, including protected slots, native
    # segment endings and gap dependencies, from its declared finite logits.
    scores = {pair:actual[pair]["logit"] for pair,row in indexed.items() if row["selected_center_xy_px"] is not None}
    expected = apply(selection,scores)
    require(all(policy.get(field) == value for field,value in expected.items()), "Policy package differs from fixed veto rule or native timeline")
    return indexed,actual


def _score_rows(reference_rows, indexed, applied, saved_field):
    result = []; seen = set()
    for reference in reference_rows:
        pair = key(reference)
        require(pair in indexed and pair not in seen, "Reference source/frame missing or duplicated")
        seen.add(pair); saved = indexed[pair]; proposed = applied[pair]
        require(reference[saved_field] == saved, "Reference saved decision differs from exact continuous selection")
        require(reference["source_video"] == saved["source_video"], "Reference source video differs")
        scoring = {**reference,"source_frame":saved["source_frame"],
                   "old":{"pool":{"contributor_planes":[None]*saved["original_observation"]["temporal_contributions"]}}}
        components = [r["component"] for r in saved["candidate_pool"]["records"]]
        before = geometry.score_point(scoring,saved["selected_center_xy_px"],components)
        require(before == reference["selected"], "Frozen ten-pixel score did not reproduce exactly")
        after = geometry.score_point(scoring,proposed["selected_center_xy_px"],components)
        result.append({"candidate_id":pair[0],"source_frame_index":pair[1],"reference_cohort":reference.get("cohort"),
            "is_control":reference.get("is_control",False),"before":before,"after":after,"removed":proposed["removed"]})
    return result


def _semantic_report(rows, scores, indexed, applied, label_status):
    cases = []; ids = set()
    for row in rows:
        rid = row["row_id"]; require(rid not in ids,"Duplicate semantic case ID"); ids.add(rid)
        pair = key(row); require(pair in indexed,"Semantic case outside permitted saved context")
        require(row["role"] in {"fit","check"} and row["classification"] in {"ball","other_object","unresolved"}, "Invalid semantic class or role")
        saved = indexed[pair]; point = row.get("center_xy_px")
        emitted = point is not None and point == saved["selected_center_xy_px"]
        if "emitted_in_saved_selection" in row:
            require(row["emitted_in_saved_selection"] == emitted,"Semantic emitted flag does not match exact saved point")
        if emitted and row.get("provenance_ids"):
            require(saved["selected_provenance_id"] in row["provenance_ids"],"Semantic emitted provenance differs")
        logit = finite_logit(scores[rid]) if rid in scores else None
        if point is None:
            require(row["classification"] == "unresolved" and logit is None,"Unavailable contrast has a score or class")
        if row["classification"] == "unresolved":
            outcome = "unscored"
        else:
            require(logit is not None,"Resolved semantic case has no score")
            require(isinstance(row.get("physical_object_instance_id"),str) and row["physical_object_instance_id"],
                    "Resolved semantic case has no physical object group")
            outcome = "correct" if (logit > 0 if row["classification"] == "ball" else logit < 0) else "tie" if logit == 0 else "incorrect"
        new_detector = row["origin"] in {"saved_detector_candidate","saved_emission_reference"}
        cases.append({"row_id":rid,"candidate_id":pair[0],"source_frame_index":pair[1],"role":row["role"],
            "origin":row["origin"],"classification":row["classification"],"subtype":row.get("subtype"),
            "block_id":row.get("block_id"),"episode_id":row.get("episode_id"),"logit":logit,"outcome":outcome,
            "physical_object_instance_id":row.get("physical_object_instance_id"),
            "crop_key":None if point is None else [pair[0],pair[1],math.floor(point[0])-32,math.floor(point[1])-32],
            "emitted_in_saved_selection":emitted,"emission_removed":emitted and applied[pair]["removed"],
            "emission_policy_decision":applied[pair]["policy_decision"] if emitted else None,
            "new_detector_reference":new_detector,"human_reference_status":label_status if new_detector or row["origin"] == "source_authored_contrast" else "previously_accepted"})
    grouped = defaultdict(list)
    for case in cases:
        if case["classification"] != "unresolved":
            grouped[(case["role"],case["candidate_id"],case["source_frame_index"],case["physical_object_instance_id"])].append(case)
    object_groups = []
    for group_key,members in grouped.items():
        for field in ("classification","block_id","episode_id"):
            require(len({r[field] for r in members}) == 1, "Physical object group has conflicting semantic metadata")
        crops = defaultdict(list)
        for row in members: crops[tuple(row["crop_key"])].append(row)
        distinct = []
        for crop_key,aliases in crops.items():
            require(all(abs(r["logit"]-aliases[0]["logit"]) <= 1e-12 for r in aliases), "Same native crop has inconsistent logits")
            distinct.append({"crop_key":list(crop_key),"row_ids":[r["row_id"] for r in aliases],
                             "logit":aliases[0]["logit"],"outcome":aliases[0]["outcome"]})
        outcome = "correct" if all(r["outcome"] == "correct" for r in distinct) else "incorrect" if any(r["outcome"] == "incorrect" for r in distinct) else "tie"
        object_groups.append({"group_key":list(group_key),"role":group_key[0],"candidate_id":group_key[1],"source_frame_index":group_key[2],
            "physical_object_instance_id":group_key[3],"classification":members[0]["classification"],"block_id":members[0]["block_id"],
            "episode_id":members[0]["episode_id"],"row_ids":[r["row_id"] for r in members],"distinct_crops":distinct,"outcome":outcome,
            "all_required_distinct_crops_correct":outcome == "correct"})
    checks = [r for r in cases if r["role"] == "check"]
    resolved = [r for r in checks if r["classification"] != "unresolved"]
    balls = [r for r in resolved if r["classification"] == "ball"]
    old = [r for r in resolved if r["origin"] == "existing_accepted_reference"]
    negatives = [r for r in resolved if r["classification"] == "other_object" and r["emitted_in_saved_selection"] and r["new_detector_reference"]]
    blocks = {r["block_id"] for r in negatives if r["block_id"]}
    episodes = {(r["block_id"],r["episode_id"]) for r in negatives if r["block_id"] and r["episode_id"]}
    other_types = {r["subtype"] for r in resolved if r["classification"] == "other_object"}
    gate_checks = {"all_excluded_balls_strictly_positive":bool(balls) and all(r["outcome"] == "correct" for r in balls),
        "old_ten_checks_all_correct":len(old) == 10 and all(r["outcome"] == "correct" for r in old),
        "new_emitted_others_negative_and_removed":bool(negatives) and all(r["logit"] < 0 and r["emission_removed"] for r in negatives),
        "new_emitted_other_two_blocks_and_episodes":len(blocks) >= 2 and len(episodes) >= 2,
        "new_emitted_other_head_and_nonhead":any(r["subtype"] == "head" for r in negatives) and any(r["subtype"] not in {None,"head"} for r in negatives),
        "excluded_head_and_clothing_present":{"head","clothing"} <= other_types}
    check_groups = [r for r in object_groups if r["role"] == "check"]
    negative_groups = {(r["candidate_id"],r["source_frame_index"],r["physical_object_instance_id"]) for r in negatives}
    return {"label_status":label_status,"cases":cases,"check_counts":dict(Counter(r["outcome"] for r in checks)),
        "check_counts_unit":"correlated labeled crop/alias rows; unresolved rows are unscored",
        "physical_object_groups":object_groups,"check_group_counts":dict(Counter(r["outcome"] for r in check_groups)),
        "check_group_counts_by_class":{label:dict(Counter(r["outcome"] for r in check_groups if r["classification"] == label)) for label in ("ball","other_object")},
        "group_unit":"source/frame/physical object; success requires every distinct native crop correct; groups within episodes remain correlated",
        "new_emitted_other_group_count":len(negative_groups),
        "checks":gate_checks,"all_semantic_checks_passed":all(gate_checks.values()),
        "new_emitted_other_rows":[r["row_id"] for r in negatives],"new_emitted_other_blocks":sorted(blocks),
        "new_emitted_other_episodes":[list(v) for v in sorted(episodes)],
        "unselected_check_rows":[r["row_id"] for r in checks if not r["emitted_in_saved_selection"]],
        "unknown_rows_unscored":[r["row_id"] for r in cases if r["classification"] == "unresolved"],
        "unknown_removals_are_successes":False}


def evaluate(policy, selection, old_790_report, gap_evaluation, *, gates, label_rows=None, label_scores=None,
             prior_object_assessment=None, label_status="provisional_ai_human_review_pending"):
    """Reproduce frozen geometric scores, deduplicate protection, keep semantics separate."""
    require(gates["localization_radius_px_inclusive"] == 10 and gap_evaluation["metric"]["raw_match_radius_px"] == 10
            and gap_evaluation["metric"]["boundary"] == "inclusive", "Frozen inclusive ten-pixel metric changed")
    indexed,applied = _validate_policy(policy,selection)
    old_scores = _score_rows(old_790_report["frames"],indexed,applied,"decision")
    additional = _score_rows(gap_evaluation["new_frames"],indexed,applied,"exact_saved_decision")
    controls = _score_rows(gap_evaluation.get("reused_controls",[]),indexed,applied,"exact_saved_decision")
    old_matched = {key(r) for r in old_scores if r["before"]["outcome"] == "matched"}
    new_matched = {key(r) for r in additional if r["before"]["outcome"] == "matched"}
    expected_old = gates["old790_exact_match_retention"]
    require(dict(Counter(cid for cid,_ in old_matched)) == expected_old, "Old matched cohort differs from frozen protection counts")
    require(len(new_matched) == gates["new_eligible_match_retention"], "Additional eligible matched cohort differs")
    prior = {parse_key(v) for v in gates["prior_gains_exact"]}
    require(all(pair in indexed and indexed[pair]["selected_center_xy_px"] is not None for pair in prior),"Accepted prior gain absent from saved selection")
    cohorts = {"old_790_matches":old_matched,"additional_eligible_matches":new_matched,"prior_accepted_gains":prior}
    protected = []
    for pair in sorted(set().union(*cohorts.values())):
        exact = emission(applied[pair]) == emission(indexed[pair])
        protected.append({"candidate_id":pair[0],"source_frame_index":pair[1],"cohorts":[name for name,keys in cohorts.items() if pair in keys],
            "retained_exact_coordinate_and_provenance":exact,"policy_decision":applied[pair]["policy_decision"]})
    cohort_summary = {name:{"required":len(keys),"retained_exact":sum(emission(applied[p]) == emission(indexed[p]) for p in keys),
                           "lost_keys":[emission_key(*p) for p in sorted(keys) if emission(applied[p]) != emission(indexed[p])]} for name,keys in cohorts.items()}
    changed_reference = old_scores+additional+controls
    no_new_wrong = not any(r["after"]["outcome"] == "wrong" and r["before"]["outcome"] != "wrong" for r in changed_reference)
    no_new_alarm = not any(r["after"]["outcome"] == "hidden_alarm" and r["before"]["outcome"] != "hidden_alarm" for r in changed_reference)
    pilot = defaultdict(list)
    for row in old_scores:
        if row["is_control"] and row["reference_cohort"] == "pilot_control": pilot[row["candidate_id"]].append(row)
    pilot_summary = {cid:{"rows":len(rows),"before_matched":sum(r["before"]["outcome"] == "matched" for r in rows),
        "after_matched":sum(r["after"]["outcome"] == "matched" for r in rows)} for cid,rows in pilot.items()}
    exposed = {}
    for name,desired in (("exposed_head_episode_suppress",False),("exposed_near_head_ball_retain",True)):
        result = []
        for raw in gates[name]:
            pair = parse_key(raw); require(pair in indexed and indexed[pair]["selected_center_xy_px"] is not None,"Exposed regression point missing")
            passed = emission(applied[pair]) == emission(indexed[pair]) if desired else applied[pair]["selected_center_xy_px"] is None
            result.append({"candidate_id":pair[0],"source_frame_index":pair[1],"passed":passed,"evidence_status":"exposed_qualitative_regression_not_new_class_truth"})
        exposed[name] = result
    semantics = _semantic_report(label_rows or [],label_scores or {},indexed,applied,label_status)
    geometry_evidence = defaultdict(list)
    for cohort,rows in (("old790",old_scores),("new27",additional),("reused7",controls)):
        for row in rows: geometry_evidence[key(row)].append({"cohort":cohort,"before_outcome":row["before"]["outcome"]})
    appearance = defaultdict(list)
    for row in semantics["cases"]:
        if row["emitted_in_saved_selection"]: appearance[key(row)].append({"row_id":row["row_id"],"class":row["classification"],"status":row["human_reference_status"]})
    qualitative = {} if prior_object_assessment is None else {key(r):r["assessment"] for r in prior_object_assessment["rows"]}
    removals = []
    for row in policy["frames"]:
        if not row["removed"]: continue
        pair = key(row); reasons = []
        if not geometry_evidence[pair]: reasons.append("no_geometric_reference")
        if any(r["before_outcome"] == "unscored" for r in geometry_evidence[pair]): reasons.append("geometric_reference_unscored")
        if any(r["class"] == "unresolved" for r in appearance[pair]): reasons.append("appearance_reference_unresolved")
        if qualitative.get(pair) == "unresolved": reasons.append("prior_qualitative_judgment_unresolved")
        removals.append({"candidate_id":pair[0],"source_frame_index":pair[1],"segment_id":row["segment_id"],"source_pts_ticks":row["source_pts_ticks"],
            "saved_emission":row["saved_emission"],"logit":row["logit"],"policy_decision":row["policy_decision"],"gap_id":row["gap_id"],
            "direct_negative":row["direct_negative"],"removed_only_by_gap_dependency":row["removed_only_by_gap_dependency"],
            "geometry_evidence":geometry_evidence[pair],"appearance_evidence":appearance[pair],"prior_qualitative_assessment":qualitative.get(pair),
            "unscored_or_unknown_reasons":reasons,"unknown_removal_counts_as_success":False})
    checks = {"all_protected_points_exact":all(r["retained_exact_coordinate_and_provenance"] for r in protected),
        "no_new_wrong_outputs":no_new_wrong,"no_new_hidden_alarms":no_new_alarm,
        "nba_easy_controls_preserved":bool(pilot_summary) and all(r["rows"] == r["before_matched"] == r["after_matched"] == gates["nba_easy_controls_match_each"] for r in pilot_summary.values()),
        **{name:all(r["passed"] for r in rows) for name,rows in exposed.items()},**semantics["checks"]}
    return {"schema_version":"nba_ball_distractor_policy_evaluation/v0.1","metric":{"match_radius_px":10,"boundary":"inclusive","uncertainty_relaxes_radius":False},
        "old_790_frames":old_scores,"additional_reference_frames":additional,"reused_control_frames":controls,
        "protected_union":protected,"protected_union_count":len(protected),"protection_cohorts":cohort_summary,
        "pilot_controls":pilot_summary,"exposed_qualitative_regressions":exposed,"semantics":semantics,
        "removals":removals,"unscored_or_unknown_removals":[r for r in removals if r["unscored_or_unknown_reasons"]],
        "missing_intervals":policy["missing_intervals"],"checks":checks,"all_reported_numeric_and_semantic_checks_passed":all(checks.values()),
        "pre_fit_adequacy":"must_be_evaluated_separately_from_frozen_reference_groups","human_reference_status":label_status,
        "human_trajectory_review":"pending","adopted":False,"geometric_matches_do_not_establish_object_identity":True}

"""Prepare accepted, fixed-context post-selection inputs without model execution.

Historical reference roles remain attached to every label. The 225 protected
slots contain timing only; they cannot enter an inference block or image read.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from pathlib import Path
import hashlib
import math

from .annotations import FrameAnnotation
from .completion_references import accepted_inventory, presentation_timeline
from .completion_training_package import CAMPAIGN, Evidence, read, require
from .wasb_experiment import canonical

SCHEMA = "completion_evaluation_package/v0.1"
ROLE = "post_selection_evaluation_only"
INVENTORY = f"{CAMPAIGN}/accepted_reference_inventory_after_batch_23.json"
SCOPE = "configs/ball_tracking/selections/nba_temporal_gap_continuous_v0_1.json"
BASELINE_SHA = "09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98"
PRIMARY_RECIPE = "configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json"
NFHS_POLICY = {"heatmap_threshold": .3, "triplet_stride": 1, "overlap_policy": "all_available_mean",
               "selection": "largest_component_mass", "device": "cuda"}
NBA_POLICY = {"heatmap_threshold": .3, "triplet_stride": 1, "aggregation": "mean_aligned_complete_native_triplets",
              "padding": "none", "resampling": "none", "selection": "largest_component_mass", "device": "cuda"}


def validate_component_selection(row):
    candidates = row["candidates"]
    require([c["candidate_index"] for c in candidates] == list(range(len(candidates))), "Candidate order differs")
    if candidates:
        selected = min(candidates, key=lambda c: (-c["native_score"], c["candidate_index"]))
        require(row["state"] == "observed" and row["selected_candidate_index"] == selected["candidate_index"]
                and row["center_xy_px"] == [selected["center_x"], selected["center_y"]]
                and row["native_score"] == selected["native_score"]
                and all(math.isfinite(v) for v in (*row["center_xy_px"], row["native_score"])),
                "Saved center differs from stable mass component selection")
    else:
        require(row["state"] == "missing" and row["center_xy_px"] is None
                and row["native_score"] is None and row["selected_candidate_index"] is None,
                "Empty saved components must stay missing")


def normalize_block(block):
    """Validate native chronology and reference joins; never alter label roles."""
    require(block["role"] == ROLE, "Evaluation role changed")
    frames = block["frames"]
    indices = [f["source_frame_index"] for f in frames]
    require(len(frames) >= 3 and indices == list(range(indices[0], indices[-1] + 1)),
            "Evaluation context is not consecutive")
    require(Fraction(block["time_base"]) > 0, "Invalid time base")
    source = type("Bounds", (), block["source_video"])()
    for position, frame in enumerate(frames):
        require(frame["state"] == "permitted", "Protected slot in inference context")
        require(not any(lo <= indices[position] <= hi for lo, hi in block.get("protected_ranges", [])),
                "Protected index in inference context")
        require(type(frame["source_pts_ticks"]) is int and type(frame["duration_ticks"]) is int
                and frame["duration_ticks"] > 0, "Invalid native presentation interval")
        if position + 1 < len(frames):
            require(frame["source_pts_ticks"] + frame["duration_ticks"] == frames[position + 1]["source_pts_ticks"],
                    "Native presentation gap")
        if frame["annotation"] is not None:
            annotation = FrameAnnotation.from_mapping(frame["annotation"], position, source)
            require(annotation.frame_index == indices[position] and annotation.annotation_status == "labeled",
                    "Reference/source frame join differs")
        require(frame["baseline_observation"]["source_frame_index"] == indices[position],
                "Baseline/source frame join differs")
        require(frame["baseline_observation"]["temporal_contributions"] ==
                sum(start <= position <= start + 2 for start in range(max(0, position - 2), min(position + 1, len(frames) - 2))),
                "Saved baseline temporal context differs")
    block["range_inclusive"] = [indices[0], indices[-1]]
    block["source_id"] = block["source_video"]["sha256"]
    return block


def validate_timeline(timeline):
    frames = timeline["frames"]
    require([f["source_frame_index"] for f in frames] == list(range(timeline["source_video"]["frame_count"])),
            "Curated timeline census differs")
    for frame in frames:
        protected = any(lo <= frame["source_frame_index"] <= hi for lo, hi in timeline["protected_ranges"])
        require((frame["state"] == "withheld") == protected, "Withheld band differs")
        if protected:
            require(frame["block_id"] is None and not any(k in frame for k in
                    ("png", "annotation", "baseline_observation", "candidate_observation", "player_records")),
                    "Protected slot carries pixels, labels or observations")
    return timeline


def _png(evidence, value, block_id, index, source, verify):
    if value is None or not evidence.path(value["path"]).is_file():
        evidence.missing.append({"block_id": block_id, "source_frame_index": index, "png": value})
        return value
    result = dict(value)
    if verify:
        result.update(evidence.bind(value["path"], value))
    if "rgb_sha256" not in result:
        if verify:
            from PIL import Image
            with Image.open(evidence.path(value["path"])) as image:
                require(image.size == (source["width_px"], source["height_px"]), "PNG dimensions differ")
                result["rgb_sha256"] = hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
        else:
            result["rgb_sha256"] = None
    return result


def _baseline(row):
    index = row.get("source_frame_index", row.get("frame_index"))
    return {"source_frame_index": index, "center_xy_px": row["center_xy_px"],
            "native_score": row.get("native_score"),
            "temporal_contributions": row.get("temporal_contributions", row.get("contribution_count")),
            "state": row["state"], "original_record": row}


def bind_selected_result(evidence, path):
    if path is None:
        return None
    result = read(evidence.path(path))
    require(result.get("schema_version") == "completion_training_result/v0.1"
            and result.get("status") == "completed" and result.get("post_selection_references_used") is False
            and result.get("protected_evaluation_authorized") is False,
            "Selected checkpoint requires completed fixed-validation selection")
    recipe_binding = evidence.bind(PRIMARY_RECIPE)
    recipe = read(evidence.path(PRIMARY_RECIPE))
    require(recipe["schema_version"] == "ball_completion_primary_recipe/v0.1"
            and recipe["status"] == "frozen_before_model_execution"
            and recipe["protected_evaluation_authorized"] is False, "Primary recipe differs")
    package, schedule = evidence.bound_json(recipe["package"]), evidence.bound_json(recipe["sampling_schedule"])
    require(type(result["completed_epochs"]) is int and 5 <= result["completed_epochs"] <= 20
            and result["completed_updates"] == sum(len(epoch["batches"]) for epoch in schedule["epochs"][:result["completed_epochs"]]),
            "Completed fit census differs from the fixed epoch schedule")
    expected_identity = {"recipe": recipe_binding, "package_sha256": canonical(package), "schedule_sha256": canonical(schedule)}
    require(result["identity"] == expected_identity, "Selected result is not from the current frozen primary package")
    reports = [evidence.bound_json(entry) for entry in result["validation_reports"]]
    require([r["epoch"] for r in reports] == list(range(result["completed_epochs"] + 1)), "Validation epoch census differs")
    for report in reports:
        require(report["identity"] == expected_identity and report["protected_frames"] == 0
                and report["post_selection_curated_labels_used"] is False and report["det_or_tor_used"] is False
                and report["threshold"] == .3 and report["strict_threshold"] is True
                and report["selection"] == "largest_component_mass_then_stable_index"
                and report["aggregation"] == "ascending_float32_aligned_contributor_mean", "Validation policy or identity differs")
    from .completion_training_policy import choose_checkpoint
    chosen = choose_checkpoint(reports)
    require(result["selection"] == {k: v for k, v in chosen.items() if k != "selected_report"}
            and result["selected_checkpoint"] == chosen["selected_report"]["checkpoint"],
            "Selected checkpoint disagrees with fixed validation reports")
    return {"training_result": evidence.bind(path), "checkpoint": evidence.bind(
        result["selected_checkpoint"]["path"], result["selected_checkpoint"]),
        "selection": result["selection"], "protected_evaluation_authorized": False}


def build_package(root, curated_inventory_path=INVENTORY, selected_result_path=None, *, verify_png_files=True):
    """Bind fixed accepted inputs; optional selected result enables later inference.

    Metadata preview may skip PNG checks, but is explicitly not execution-ready.
    No source video is opened and no model or scoring routine is called.
    """
    root = Path(root).resolve(); evidence = Evidence(root)
    inventory = read(evidence.path(curated_inventory_path))
    require(inventory["totals"] == {"accepted_permitted": 1273, "permitted": 1273, "uncovered": 0},
            "Complete accepted curated census required")
    config_path = "configs/ball_tracking/completion_campaign/reference_batch_23_v0_1.json"
    config = read(root / config_path)
    config["additional_accepted_references"] = inventory["accepted_campaign_reference_entries"]
    accepted, authorities = accepted_inventory(root, config)
    require(len(accepted) == 1273, "Accepted census differs")
    contract = read(root / config["source_contract"])
    scope = read(root / SCOPE)
    nfhs_inputs_path = f"{CAMPAIGN}/training_inputs_nfhs_v0_1/package_inputs.json"
    nfhs_inputs = read(root / nfhs_inputs_path)
    gap = evidence.bound_json(config["accepted_gap_reference"])
    gap_preparation_path = "data/outputs/ball_tracking/nba/gap_anchor_reference_v0_1/preparation.json"
    require(gap["bindings"]["preparation"]["path"] == gap_preparation_path, "Gap source preparation authority differs")
    gap_preparation = evidence.bound_json(gap["bindings"]["preparation"])
    assets, roles, cohorts = {}, {}, []
    for block in nfhs_inputs["blocks"]:
        for frame in block["frames"]:
            key = (block["possession_id"], frame["source_frame_index"])
            assets[key] = frame["png"]
    for frame in gap_preparation["frames"]:
        assets.setdefault((frame["continuous_source_id"], frame["source_frame_index"]), frame["raw_png"])
    for entry in inventory["authorities"]:
        if entry.get("role") in {"historical_training", "checkpoint_selection_development"}:
            doc = evidence.bound_json(entry)
            for row in doc["annotations"]:
                roles[(doc["possession_id"], row["frame_index"])] = entry["role"]
            if entry["role"] == "checkpoint_selection_development":
                cohorts.append({"cohort_id": Path(entry["path"]).stem,
                    "source_id": doc["possession_id"], "role": entry["role"], "reference": entry,
                    "frame_indices": [r["frame_index"] for r in doc["annotations"]],
                    "comparison_context": "complete_permitted_segment", "regression_screen": True})
    for row in gap["new_annotations"]:
        roles[(row["continuous_source_id"], row["source_frame_index"])] = "post_selection_development"
    for entry in inventory["accepted_campaign_reference_entries"]:
        doc = evidence.bound_json(entry)
        for frame in doc["frames"]:
            key = (doc["possession_id"], frame["source_frame_index"])
            assets[key] = frame["source_png"]; roles[key] = ROLE
    blocks, timelines, baseline_bindings = [], [], []
    for possession in contract["possessions"]:
        pid, source = possession["possession_id"], possession["source_video"]
        native_entry = next(e for e in nfhs_inputs["native_timing_bindings"] if Path(e["path"]).name == f"{pid}_packet_timing.json")
        native = presentation_timeline(evidence.bound_json(native_entry), source["frame_count"])
        source_scope = next(s for s in scope["sources"] if s["candidate_id"] == pid)
        from .completion_baseline import validate_observations
        full_baseline = evidence.bound_json(source_scope["timeline_observations"])
        validate_observations(possession, full_baseline, BASELINE_SHA)
        require([s["range_inclusive"] for s in source_scope["segments"]] == possession["visible_segments"],
                "Saved baseline segments differ from exact protected complement")
        timeline = {"possession_id": pid, "source_video": source, "time_base": native[0]["native_time_base"],
                    "protected_ranges": possession["protected_ranges"], "player_context": evidence.bind(
                        possession["player_context"]["path"], possession["player_context"]),
                    "player_context_display_only": True, "native_timing": native_entry, "frames": []}
        permitted = {}
        for segment in source_scope["segments"]:
            lo, hi = segment["range_inclusive"]; block_id = segment["segment_id"]
            saved = evidence.bound_json(segment["observations"])
            require(saved["segment"] == [lo, hi] and saved["identity"]["weights"]["sha256"] == BASELINE_SHA
                    and saved["identity"]["source_video"] == source and saved["identity"]["inference"] == NFHS_POLICY,
                    "Retained baseline identity or inference policy differs")
            baseline_bindings.append(segment["observations"])
            require([r["frame_index"] for r in saved["frames"]] == list(range(lo, hi + 1)), "Baseline census differs")
            frames = []
            for index, observation in zip(range(lo, hi + 1), saved["frames"], strict=True):
                validate_component_selection(observation)
                require(all(full_baseline["frames"][index][k] == v for k, v in observation.items()),
                        "Segment/full baseline record transport differs")
                key = (pid, index); timing = native[index]
                require(key in accepted and key in roles, "Missing accepted reference or original role")
                frame = {"source_frame_index": index, "source_pts_ticks": timing["native_pts_ticks"],
                    "duration_ticks": timing["native_duration_ticks"], "state": "permitted", "block_id": block_id,
                    "png": _png(evidence, assets.get(key), block_id, index, source, verify_png_files),
                    "annotation": accepted[key], "reference_role": roles[key], "baseline_observation": _baseline(observation)}
                frames.append(frame); permitted[index] = frame
            blocks.append(normalize_block({"block_id": block_id, "domain": "nfhs", "game_id": pid,
                "possession_id": pid, "role": ROLE, "source_video": source, "time_base": timeline["time_base"],
                "protected_ranges": possession["protected_ranges"], "frames": frames,
                "baseline_binding": segment["observations"], "context_policy": "complete_permitted_segment_no_padding"}))
        for timing in native:
            index = timing["source_frame_index"]
            timeline["frames"].append(permitted.get(index, {"source_frame_index": index,
                "source_pts_ticks": timing["native_pts_ticks"], "duration_ticks": timing["native_duration_ticks"],
                "state": "withheld", "block_id": None}))
        timelines.append(validate_timeline(timeline))
    # Accepted NBA references retain separate named cohorts, including pilot controls.
    nba_labels = {}
    for kind, path in (("pilot_control", "data/outputs/ball_tracking/nba/reviewed_pilot_v0_1/reference.json"),
                       ("hard_example", "data/outputs/ball_tracking/nba/hard_example_reference_v0_1/accepted/reference.json")):
        document = read(root / path)
        require(document["status"] == "human_accepted_assisted_reference", "NBA references not accepted")
        evidence.bound_json(document["acceptance"])
        authority = evidence.bind(path); authorities += [authority, document["acceptance"]]
        for reference in document["references"]:
            cid = reference["candidate_id"]
            require(len(reference["frames"]) == len(reference["annotations"])
                    and (kind != "pilot_control" or len(reference["frames"]) == 60), "Fixed reference/control count differs")
            cohorts.append({"cohort_id": f"{cid}:{kind}:{reference.get('window_id', 'pilot')}", "source_id": cid,
                "role": "historical_training" if cid.startswith("sac_") else "excluded_development",
                "frame_indices": [f["source_frame_index"] for f in reference["frames"]], "reference": authority,
                "comparison_context": "original_complete_action_core", "pilot_control": kind == "pilot_control",
                "regression_screen": cid.startswith("sas_det") or kind == "pilot_control"})
            for frame, annotation in zip(reference["frames"], reference["annotations"], strict=True):
                key = (cid, frame["source_frame_index"])
                require(key not in nba_labels or nba_labels[key] == annotation, "Conflicting NBA references")
                nba_labels[key] = annotation
    for item in gap["new_annotations"]:
        cid = item["continuous_source_id"]
        if not cid.startswith("possession_"):
            key = (cid, item["source_frame_index"])
            require(key not in nba_labels or nba_labels[key] == item["annotation"], "Conflicting gap reference")
            nba_labels[key] = item["annotation"]
    for cid in sorted({r["continuous_source_id"] for r in gap["new_annotations"]}):
        cohorts.append({"cohort_id": f"{cid}:accepted_gap_references", "source_id": cid,
            "role": "post_selection_development", "reference": config["accepted_gap_reference"],
            "frame_indices": [r["source_frame_index"] for r in gap["new_annotations"] if r["continuous_source_id"] == cid],
            "comparison_context": "complete_permitted_segment_or_original_action_core",
            "regression_screen": not cid.startswith("sac_")})
    for source_scope in (s for s in scope["sources"] if s["kind"] == "nba"):
        manifest = evidence.bound_json(source_scope["source_manifest"])
        cid, source = manifest["candidate_id"], manifest["source_video"]
        require(source == source_scope["source_video"], "NBA source identity differs")
        segment = source_scope["segments"][0]
        saved = evidence.bound_json(segment["observations"])
        require(saved["checkpoint"]["sha256"] == BASELINE_SHA, "NBA retained checkpoint differs")
        require(saved["inference"] == NBA_POLICY and saved["candidate_id"] == cid
                and saved["game_id"] == manifest["game_id"], "NBA retained inference policy or identity differs")
        require([f["source_frame_index"] for f in manifest["frames"]] ==
                [f["source_frame_index"] for f in saved["frames"]], "NBA baseline frame census differs")
        frames = []; block_id = segment["segment_id"]
        ticks = [f["source_pts_ticks"] for f in manifest["frames"]] + [manifest["source_end_exclusive_pts_ticks"]]
        for offset, (frame, observation) in enumerate(zip(manifest["frames"], saved["frames"], strict=True)):
            validate_component_selection(observation)
            require(observation["segment_source_frame_range_inclusive"] == segment["range_inclusive"]
                    and observation["inference_status"] == "completed" and observation["time_base"] == manifest["time_base"],
                    "NBA retained temporal segment differs")
            index = frame["source_frame_index"]
            require(frame["source_pts_ticks"] == observation["source_pts_ticks"] and frame["png"] == observation["source_png"],
                    "NBA source/baseline native join differs")
            frames.append({"source_frame_index": index, "source_pts_ticks": ticks[offset],
                "duration_ticks": ticks[offset + 1] - ticks[offset], "state": "permitted", "block_id": block_id,
                "png": _png(evidence, frame["png"], block_id, index, source, verify_png_files),
                "annotation": nba_labels.get((cid, index)),
                "reference_role": "historical_training" if cid.startswith("sac_") else "excluded_development",
                "baseline_observation": _baseline(observation)})
        blocks.append(normalize_block({"block_id": block_id, "candidate_id": cid, "domain": "nba", "game_id": manifest["game_id"],
            "role": ROLE, "source_video": source, "time_base": manifest["time_base"], "frames": frames,
            "baseline_binding": segment["observations"], "source_manifest": source_scope["source_manifest"],
            "context_policy": "original_complete_action_core_no_padding"}))
        baseline_bindings.append(segment["observations"])
    require(len(blocks) == 8 and sum(len(b["frames"]) for b in blocks) == 3975, "Fixed context census differs")
    selected = bind_selected_result(evidence, selected_result_path)
    ready = verify_png_files and not evidence.missing and all(f["png"].get("rgb_sha256") for b in blocks for f in b["frames"])
    return {"schema_version": SCHEMA, "status": "prepared_inputs_selected_method_pending" if selected is None else "selected_method_inputs_prepared",
        "inference_blocks": blocks, "curated_timelines": timelines, "regression_cohorts": cohorts,
        "selected_method": selected, "execution_ready": bool(ready and selected), "png_assets_verified": bool(ready),
        "missing_png_assets": evidence.missing, "protected_evaluation_authorized": False,
        "counts": {"curated_permitted": 1273, "curated_timeline": 1498, "protected_withheld": 225,
                   "inference_frames": sum(len(b["frames"]) for b in blocks), "inference_blocks": len(blocks),
                   "reference_roles": dict(Counter(roles[k] for k in accepted))},
        "reference_bindings": authorities, "baseline_bindings": baseline_bindings,
        "bindings": [evidence.bind(p) for p in (curated_inventory_path, config_path, config["source_contract"], SCOPE,
            nfhs_inputs_path, gap_preparation_path, "docs/ball_tracking_completion_plan.md")],
        "baseline_checkpoint_sha256": BASELINE_SHA,
        "inference_policy": {"threshold": .3, "threshold_operator": ">", "resolution_wh": [512, 288],
            "aggregation": "ascending_float32_aligned_contributor_mean", "selection": "largest_component_mass_then_stable_index",
            "triplet_stride": 1, "padding": False, "resampling": False, "interpolation": False},
        "tor": {"game_id": "0022500843", "status": "no_existing_fixed_context_or_accepted_reference_cohort",
                "training_eligible": False, "checkpoint_selection_eligible": False,
                "authority": evidence.bind("configs/ball_tracking/selections/nba_development_selection_proposal_v0_1.json")},
        "bounded_gap_additions": {"kept_separate_from_automatic_metrics": True,
            "accepted_review": evidence.bind("configs/ball_tracking/reviews/nba_temporal_gap_selection_visual_review_v0_1.json")},
        "model_calls": 0, "scoring_calls": 0, "source_video_decodes": 0,
        "human_trajectory_acceptance": None, "full_clip_pass_claimed": False}

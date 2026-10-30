"""One frozen causal candidate-only comparison over saved WASB observations.

No model, heatmap, source pixels, annotations or player positions enter selection.
Current component mass is an ordering signal, not a probability. A persistent
false candidate can still maintain an incorrect path; this experiment tests it.
"""
from __future__ import annotations

import argparse
import ast
import math
import subprocess
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .wasb_development_observation import binding, validate_scope
from .wasb_experiment import bound_path, canonical, read_json, repository_path, write_once

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/ball_tracking/wasb_experiments/wasb_motion_selection_v0_1.json"
POLICY = {
    "algorithm": "causal_short_memory_prediction_gate/v0.1",
    "gate_diagonal_fraction_per_frame": 0.06,
    "minimum_relative_native_mass": 0.5,
    "maximum_missing_frames": 2,
    "velocity_history_points": 2,
    "velocity_cap_diagonal_fraction_per_frame": 0.06,
    "startup_and_reacquisition": "native_mass_maximum_immediate",
    "selection_order": "prediction_distance_then_descending_mass_then_candidate_index",
    "future_selection_context_frames": 0,
    "interpolation": "none",
}


def selection_digest():
    names = {"native_winner", "center", "select_segment", "select_timeline"}
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    return canonical({node.name: ast.dump(node, include_attributes=False) for node in tree.body
                      if isinstance(node, ast.FunctionDef) and node.name in names})


def native_winner(candidates):
    return min(candidates, key=lambda c: (-c["native_score"], c["candidate_index"])) if candidates else None


def center(candidate):
    return [candidate["center_x"], candidate["center_y"]] if candidate is not None else None


def select_segment(frames, width, height, policy):
    """Consume candidate-only rows; return existing indices, never new centers."""
    if policy != POLICY:
        raise ValueError("This comparison accepts exactly the frozen policy")
    allowance = math.hypot(width, height) * policy["gate_diagonal_fraction_per_frame"]
    history, missing, decisions = [], 0, []
    previous_index = None
    for row in frames:
        index, candidates = row["frame_index"], row["candidates"]
        if previous_index is not None and index != previous_index + 1:
            raise ValueError("Selector segments must be consecutive")
        previous_index = index
        if missing > policy["maximum_missing_frames"]:
            history = []
        winner = native_winner(candidates)
        prediction, gate, distances = None, None, []
        selected = None
        if winner is None:
            reason = "no_candidate"
        elif not history:
            selected = winner
            reason = "native_mass_start_or_restart"
        else:
            last_index, last_center = history[-1]
            velocity = [0.0, 0.0]
            if len(history) == 2:
                before_index, before_center = history[0]
                velocity = [(last_center[d] - before_center[d]) / (last_index - before_index) for d in range(2)]
                speed = math.hypot(*velocity)
                cap = math.hypot(width, height) * policy["velocity_cap_diagonal_fraction_per_frame"]
                if speed > cap:
                    velocity = [v * cap / speed for v in velocity]
            elapsed = index - last_index
            prediction = [last_center[d] + elapsed * velocity[d] for d in range(2)]
            gate = allowance * elapsed
            eligible = []
            for candidate in candidates:
                distance = math.dist(center(candidate), prediction)
                mass_ok = candidate["native_score"] >= winner["native_score"] * policy["minimum_relative_native_mass"]
                accepted = mass_ok and distance <= gate
                distances.append({"candidate_index": candidate["candidate_index"],
                                  "prediction_distance_px": distance, "relative_mass_passed": mass_ok,
                                  "gate_passed": distance <= gate, "eligible": accepted})
                if accepted:
                    eligible.append((distance, -candidate["native_score"], candidate["candidate_index"], candidate))
            if eligible:
                selected = min(eligible, key=lambda item: item[:3])[3]
                reason = "motion_candidate"
            else:
                reason = "motion_abstention"
        history_before = [{"frame_index": i, "center_xy_px": xy} for i, xy in history]
        if selected is None:
            missing += 1
        else:
            history = (history + [(index, center(selected))])[-2:]
            missing = 0
        decisions.append({"frame_index": index,
                          "selected_candidate_index": None if selected is None else selected["candidate_index"],
                          "reason": reason, "history": history_before, "prediction_xy_px": prediction,
                          "gate_radius_px": gate, "candidate_checks": distances,
                          "consecutive_missing_outputs": missing})
    return decisions


def validate_observations(observations, possession, training_blocks):
    """Independently check actual producer rows, selections, scope and flags."""
    source = possession["source_video"]
    for key in ("possession_id", "source_video", "visible_segments", "protected_ranges"):
        if observations.get(key) != possession[key]:
            raise ValueError(f"Saved observation {key} differs")
    if observations.get("schema_version") != "unlabeled_ball_development_observations/v0.1":
        raise ValueError("Unexpected cached observation schema")
    if observations.get("reference_labels") is not None or observations.get("threshold_status") != "0.3_development_candidate":
        raise ValueError("Expected unlabeled frozen 0.3 observations")
    frames = observations["frames"]
    if [r["frame_index"] for r in frames] != list(range(source["frame_count"])):
        raise ValueError("Saved timeline must cover every frame exactly once")
    for row in frames:
        index = row["frame_index"]
        training = any(b["possession_id"] == possession["possession_id"]
                       and b["start_frame_index"] <= index <= b["end_frame_index"] for b in training_blocks)
        if type(row["training_frame"]) is not bool or row["training_frame"] != training:
            raise ValueError("Producer training membership differs from bound training blocks")
        protected = any(a <= index <= b for a, b in possession["protected_ranges"])
        if protected:
            if (row["state"] != "withheld" or row["candidates"] or row["selected_candidate_index"] is not None
                    or row["center_xy_px"] is not None or row["native_score"] is not None
                    or row["segment"] is not None or row["contribution_count"] != 0):
                raise ValueError("Protected row contains an observation")
            continue
        segment = next((s for s in possession["visible_segments"] if s[0] <= index <= s[1]), None)
        if row["segment"] != segment or segment is None or row["contribution_count"] not in (1, 2, 3):
            raise ValueError("Observation segment/contribution metadata differs")
        candidates = row["candidates"]
        if [c["candidate_index"] for c in candidates] != list(range(len(candidates))):
            raise ValueError("Producer candidate namespace differs")
        for candidate in candidates:
            for key in ("center_x", "center_y", "native_score"):
                value = candidate[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Candidate coordinates/mass must be finite numbers")
            if candidate["native_score"] < 0:
                raise ValueError("Native mass must be nonnegative")
        winner = native_winner(candidates)
        if (row["selected_candidate_index"] != (winner["candidate_index"] if winner else None)
                or row["center_xy_px"] != center(winner)
                or row["native_score"] != (winner["native_score"] if winner else None)
                or row["state"] != ("observed" if winner else "missing")):
            raise ValueError("Saved native-mass control does not match actual candidates")


def select_timeline(observations, possession, policy):
    decisions = {}
    source = possession["source_video"]
    # The algorithm receives only indices and current candidate evidence.
    for start, end in possession["visible_segments"]:
        inputs = [{"frame_index": row["frame_index"], "candidates": row["candidates"]}
                  for row in observations["frames"][start:end + 1]]
        decisions.update({d["frame_index"]: d for d in select_segment(inputs, source["width_px"], source["height_px"], policy)})
    frames = []
    for row in observations["frames"]:
        decision = decisions.get(row["frame_index"])
        index = None if decision is None else decision["selected_candidate_index"]
        selected = next((c for c in row["candidates"] if c["candidate_index"] == index), None)
        frames.append({**row, "is_training_frame": row["training_frame"],
                       "baseline_candidate_index": row["selected_candidate_index"],
                       "baseline_center_xy_px": row["center_xy_px"], "baseline_native_score": row["native_score"],
                       "selected_candidate_index": index, "center_xy_px": center(selected),
                       "native_score": None if selected is None else selected["native_score"],
                       "state": "withheld" if decision is None else ("observed" if selected else "missing"),
                       "changed": index != row["selected_candidate_index"], "selection_audit": decision})
    return {"schema_version": "wasb_motion_selection_timeline/v0.1", "possession_id": possession["possession_id"],
            "source_video": source, "visible_segments": possession["visible_segments"],
            "protected_ranges": possession["protected_ranges"], "policy": policy,
            "model_provenance": observations["model_provenance"], "frames": frames,
            "reference_labels_used_for_selection": False, "selected_operating_point": None}


def load_inputs(root, config_path):
    config = read_json(config_path)
    if config.get("schema_version") != "wasb_motion_selection_comparison/v0.1" or config.get("selection") != POLICY:
        raise ValueError("Unexpected comparison schema/policy")
    obs_config = read_json(bound_path(root, config["observation_config"]))
    summary = read_json(bound_path(root, config["observation_summary"]))
    split = read_json(bound_path(root, obs_config["split_metadata"]))
    training = read_json(bound_path(root, obs_config["training_config"]))
    validate_scope(obs_config, split)
    if config["rendering"] != obs_config["rendering"] or config["evaluation_radius_px"] != 10.0:
        raise ValueError("Rendering or unchanged evaluation radius differs")
    saved = {item["possession_id"]: item for item in summary["possessions"]}
    if set(saved) != {p["possession_id"] for p in obs_config["possessions"]}:
        raise ValueError("Saved possession inventory differs")
    observations = {}
    for possession in obs_config["possessions"]:
        pid = possession["possession_id"]
        data = read_json(bound_path(root, saved[pid]["observations"]))
        validate_observations(data, possession, training["training_blocks"])
        if data["training_completion"] != obs_config["training_completion"]:
            raise ValueError("Observation training lineage differs")
        observations[pid] = data
    return config, obs_config, split, observations, saved


def execute(root, config_path, *, check_only=False):
    config, obs_config, split, observations, saved = load_inputs(root, config_path)
    if check_only:
        return {"status": "actual_saved_producer_records_verified", "frames": sum(len(d["frames"]) for d in observations.values()),
                "labels_read": False, "model_calls": 0}
    from .wasb_training import training_lock
    from .wasb_motion_evaluation import evaluate_comparison
    from .wasb_motion_review import render_comparison
    output = repository_path(root, config["output_root"], "data/outputs")
    if output == repository_path(root, obs_config["output_root"]):
        raise ValueError("Comparison must not overwrite its input")
    output.mkdir(parents=True, exist_ok=True)
    with training_lock(output / "comparison.lock"):
        began = time.perf_counter()
        attempt = output / "invocations" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex + ".json")
        receipt = {"status": "started", "config": binding(root, config_path), "model_calls": 0,
                   "source": binding(root, Path(__file__)), "git_head": subprocess.check_output(
                       ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()}
        write_once(attempt.with_suffix(".started.json"), receipt)
        try:
            write_once(output / "experiment.json", config)
            selection_identity = {"config": receipt["config"], "algorithm_sha256": selection_digest(),
                                  "inputs": {pid: item["observations"] for pid, item in saved.items()}}
            selection_receipt = output / "selection_completion.json"
            if selection_receipt.exists():
                completed = read_json(selection_receipt)
                if completed["identity"] != selection_identity:
                    raise ValueError("Completed selection input/policy/algorithm differs")
                selection_bindings = completed["selections"]
                timelines = {pid: read_json(bound_path(root, file)) for pid, file in selection_bindings.items()}
                receipt["selection_reused"] = True
            else:
                timelines = {}
                for possession in obs_config["possessions"]:
                    pid = possession["possession_id"]
                    target = output / pid / "selection.json"
                    timeline = select_timeline(observations[pid], possession, config["selection"])
                    timeline["input_observations"] = saved[pid]["observations"]
                    timeline["selector_source"] = receipt["source"]
                    write_once(target, timeline)
                    timelines[pid] = timeline
                # Persist every selection before opening any annotation authority.
                selection_bindings = {pid: binding(root, output / pid / "selection.json") for pid in timelines}
                write_once(selection_receipt, {"selections": selection_bindings,
                    "identity": selection_identity, "labels_read_for_selection": False})
                receipt["selection_reused"] = False
            receipt["selection_seconds"] = time.perf_counter() - began
            evaluator_sources = {name: binding(root, Path(__file__).with_name(name)) for name in (
                "wasb_motion_evaluation.py", "point_evaluation.py", "annotations.py",
                "wasb_adaptation_experiment.py", "wasb_calibration.py")}
            evaluation_identity = {"selections": selection_bindings, "sources": evaluator_sources,
                                   "split": obs_config["split_metadata"], "radius_px": config["evaluation_radius_px"]}
            write_once(output / "evaluation_identity.json", evaluation_identity)
            evaluation_receipt = output / "evaluation_completion.json"
            if evaluation_receipt.exists():
                completed = read_json(evaluation_receipt)
                if completed["identity"] != evaluation_identity:
                    raise ValueError("Completed evaluation identity differs")
                comparison = read_json(bound_path(root, completed["comparison"]))
                for window in comparison["windows"]:
                    bound_path(root, window["annotation"])
                receipt["evaluation_reused"] = True
            else:
                comparison = evaluate_comparison(root, split, timelines)
                write_once(output / "comparison.json", comparison)
                write_once(evaluation_receipt, {"identity": evaluation_identity,
                    "comparison": binding(root, output / "comparison.json")})
                receipt["evaluation_reused"] = False
            receipt["selection_and_evaluation_seconds"] = time.perf_counter() - began
            reviews = {}
            for possession in obs_config["possessions"]:
                pid = possession["possession_id"]
                reviews[pid] = render_comparison(root, obs_config, possession, timelines[pid], output / pid)
                print(f"{pid}: cached selection, paired scoring and review complete", flush=True)
            summary = {"schema_version": "wasb_motion_selection_summary/v0.1", "config": receipt["config"],
                "selection_outputs": selection_bindings, "comparison": binding(root, output / "comparison.json"),
                "reviews": reviews, "counts": {pid: {
                    "baseline_observed": sum(r["baseline_candidate_index"] is not None for r in t["frames"]),
                    "motion_observed": sum(r["selected_candidate_index"] is not None for r in t["frames"]),
                    "changed": sum(r["changed"] for r in t["frames"]),
                    "withheld": sum(r["state"] == "withheld" for r in t["frames"])} for pid, t in timelines.items()},
                "human_visual_review": "pending", "selected_operating_point": None,
                "limitations": ["Same-game development comparison; no independent generalization claim",
                    "Training frames participate in unlabeled context but never scoring",
                    "Candidate-only selection cannot fill any originally empty frame",
                    "Geometric errors do not by themselves identify the wrong object"]}
            write_once(output / "summary.json", summary)
            receipt.update(status="completed", summary=binding(root, output / "summary.json"))
            return summary
        except BaseException as error:
            receipt.update(status="failed", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
            raise
        finally:
            receipt["elapsed_seconds"] = time.perf_counter() - began
            write_once(attempt, receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    result = execute(ROOT, repository_path(ROOT, args.config), check_only=args.check_only)
    print(result if args.check_only else {"status": "completed", "counts": result["counts"]}, flush=True)


if __name__ == "__main__":
    main()

"""Package retained observations and reviewed player context without inference.

The original reviews are reused byte-for-byte. Source packet timestamps are
read without decoding source pixels; only already-masked review videos decode.
Output availability and historical labeled accuracy remain separate measures.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import html
import json
import math
from pathlib import Path
import subprocess

from .wasb_development_observation import (
    HEADER_HEIGHT, POLICY, binding, complement_ranges, verify_rendered_video,
)
from .wasb_experiment import bound_path, read_json, repository_path, write_once

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/ball_tracking/completion_campaign/baseline_v0_1.json"


def packet_timeline(metadata, expected_count):
    """Sort encoded packets by presentation time, retaining the native origin."""
    streams = metadata["streams"]
    if len(streams) != 1:
        raise ValueError("Expected one selected video stream")
    time_base = Fraction(streams[0]["time_base"])
    packets = sorted(metadata["packets"], key=lambda p: int(p["pts"]))
    if len(packets) != expected_count:
        raise ValueError("Packet count differs from reviewed frame count")
    first = int(packets[0]["pts"])
    result = []
    for index, packet in enumerate(packets):
        pts, duration = int(packet["pts"]), int(packet["duration"])
        if duration <= 0 or (index and pts <= int(packets[index - 1]["pts"])):
            raise ValueError("Video packet timing is missing, duplicated or nonpositive")
        if index and pts != int(packets[index - 1]["pts"]) + int(packets[index - 1]["duration"]):
            raise ValueError("Packet duration does not reach the next presentation timestamp")
        result.append({"native_pts": pts, "native_time_base": str(time_base),
                       "native_timestamp_seconds": float(pts * time_base),
                       "playback_timestamp_seconds": float((pts - first) * time_base),
                       "duration_seconds": float(duration * time_base)})
    return result


def source_packet_metadata(path):
    # -show_packets demuxes compressed packets; it does not decode video frames.
    process = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=time_base,r_frame_rate,avg_frame_rate,nb_frames:packet=pts,duration",
        "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(process.stdout)


def validate_observations(possession, observations, checkpoint_sha256):
    """Check the saved producer record directly, including temporal exclusions."""
    count = possession["source_video"]["frame_count"]
    protected = possession["protected_ranges"]
    segments = possession["visible_segments"]
    if complement_ranges(count, protected) != segments:
        raise ValueError("Permitted segments are not exactly the protected complement")
    if (observations["source_video"] != possession["source_video"]
            or observations["visible_segments"] != segments
            or observations["protected_ranges"] != protected
            or observations["possession_id"] != possession["possession_id"]):
        raise ValueError("Observation source or scope differs")
    provenance = observations["model_provenance"]
    if provenance["weights"]["sha256"] != checkpoint_sha256 or provenance["inference"] != POLICY:
        raise ValueError("Saved output is not the retained checkpoint/policy")
    frames = observations["frames"]
    if [row["frame_index"] for row in frames] != list(range(count)):
        raise ValueError("Saved producer timeline is incomplete or duplicated")
    contributor_counts = {}
    if [segment["segment"] for segment in observations["segments"]] != segments:
        raise ValueError("Saved temporal segments differ")
    for segment in observations["segments"]:
        start, end = segment["segment"]
        triplets = segment["triplets"]
        if [t["input_frame_indices"] for t in triplets] != [list(range(i, i + 3)) for i in range(start, end - 1)]:
            raise ValueError("Temporal input crossed a protected boundary or lost alignment")
        for triplet in triplets:
            for index in triplet["input_frame_indices"]:
                contributor_counts[index] = contributor_counts.get(index, 0) + 1
    for row in frames:
        index = row["frame_index"]
        withheld = any(low <= index <= high for low, high in protected)
        if withheld:
            if (row["state"] != "withheld" or row["center_xy_px"] is not None
                    or row["native_score"] is not None or row["candidates"]
                    or row["selected_candidate_index"] is not None
                    or row["contribution_count"] != 0 or row["segment"] is not None
                    or row["training_frame"]):
                raise ValueError("Protected frame carries observation or training data")
            continue
        if row["segment"] not in segments or not row["segment"][0] <= index <= row["segment"][1]:
            raise ValueError("Frame assigned to wrong temporal segment")
        if row["contribution_count"] != contributor_counts[index]:
            raise ValueError("Saved contribution count differs from actual triplets")
        candidates = row["candidates"]
        if [c["candidate_index"] for c in candidates] != list(range(len(candidates))):
            raise ValueError("Candidate indices are incomplete or repeated")
        if candidates:
            selected = min(candidates, key=lambda c: (-c["native_score"], c["candidate_index"]))
            if (row["state"] != "observed" or row["selected_candidate_index"] != selected["candidate_index"]
                    or row["center_xy_px"] != [selected["center_x"], selected["center_y"]]
                    or row["native_score"] != selected["native_score"]
                    or not all(math.isfinite(value) for value in (*row["center_xy_px"], row["native_score"]))):
                raise ValueError("Selected observation differs from saved native-mass candidate")
        elif (row["state"] != "missing" or row["center_xy_px"] is not None
                or row["native_score"] is not None or row["selected_candidate_index"] is not None):
            raise ValueError("Empty component set must remain explicitly missing")


def player_records(path, possession):
    players = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            index = int(row["frame_index"])
            if any(start <= index <= end for start, end in possession["visible_segments"]):
                players.setdefault(index, []).append({
                    "player_id": row["player_id"], "floor_xy_px": [float(row["floor_x"]), float(row["floor_y"])],
                    "original_timestamp_seconds": float(row["timestamp_sec"]),
                    "identity_status": row["identity_status"], "reconciled_team": row["reconciled_team"]})
    return players


def frame_records(possession, observations, times, players):
    records = []
    for original, timestamp in zip(observations["frames"], times, strict=True):
        index, state = original["frame_index"], original["state"]
        display = [] if state == "withheld" else players.get(index, [])
        if any(abs(p["original_timestamp_seconds"] - timestamp["playback_timestamp_seconds"]) > 1e-6 for p in display):
            raise ValueError("Reviewed player time differs from synchronized playback time")
        records.append({**original, **timestamp, "possession_id": possession["possession_id"],
            "observation_type": "image_based_observation" if state == "observed" else state,
            "missing_reason": {"observed": None, "missing": "no_component_strictly_above_0.3",
                               "withheld": "protected_holdout_and_buffer"}[state],
            "confidence": {"value": original["native_score"], "kind": "component_heatmap_mass",
                           "calibrated_probability": None, "is_probability": False},
            "source_video_sha256": possession["source_video"]["sha256"],
            "checkpoint_sha256": observations["model_provenance"]["weights"]["sha256"],
            "reference_eligibility": "not_determined_by_this_package",
            "reviewed_players_display_only": display})
    return records


def missing_intervals(frames):
    """Availability gaps only: this does not infer reference visibility."""
    intervals, run = [], []

    def finish():
        if run:
            intervals.append({"start_frame_index": run[0]["frame_index"], "end_frame_index": run[-1]["frame_index"],
                "frame_count": len(run), "start_playback_seconds": run[0]["playback_timestamp_seconds"],
                "duration_seconds": float(sum(Fraction(str(r["duration_seconds"])) for r in run)),
                "reference_visibility": "not_assessed", "eligible_gap_gate": "inconclusive"})
            run.clear()

    for row in frames:
        if row["state"] == "missing":
            if run and row["segment"] != run[-1]["segment"]:
                finish()
            run.append(row)
        else:
            finish()
    finish()
    return intervals


def historical_accuracy(comparison):
    totals = {"eligible": 0, "matched": 0, "wrong": 0, "missing": 0, "hidden_frames": 0, "hidden_alarms": 0}
    possessions = {}
    for window in comparison["windows"]:
        report = window["baseline_report"]
        counts = {"eligible": report["eligible_frame_count"], "matched": report["true_positive_count"],
                  "wrong": sum(r["scoring_status"] == "localization_eligible" and r["accepted_detection_count"] > 0
                               and r["matched_candidate_index"] is None for r in report["frame_results"]),
                  "missing": sum(r["scoring_status"] == "localization_eligible" and r["accepted_detection_count"] == 0
                                 for r in report["frame_results"]),
                  "hidden_frames": report["not_visible_frame_count"],
                  "hidden_alarms": report["non_visible_false_alarm_frame_count"]}
        scope = possessions.setdefault(window["possession_id"], {key: 0 for key in totals})
        for key, value in counts.items():
            scope[key] += value
            totals[key] += value
    return {"context": "Previously scored six development windows, same longer-context native-mass baseline",
            "new_scoring_performed": False, "radius_source_pixels_inclusive": comparison["localization_radius_px"],
            "totals": totals, "possessions": possessions,
            "limits": "Exposed same-game development references; not accuracy over all 1273 permitted frames"}


def index_html(summary, root):
    # Absolute local URLs keep the index usable regardless of its output folder.
    def url(bound):
        return html.escape((root / bound["path"]).resolve().as_uri(), quote=True)
    sections = []
    for item in summary["possessions"]:
        counts = item["availability"]
        sections.append(f'<section><h2>{html.escape(item["possession_id"])}</h2>'
            f'<p>{counts["observed"]} model points; {counts["missing"]} missing; {counts["withheld"]} protected. '
            f'Longest availability gap: {item["longest_missing_interval"]["duration_seconds"]:.2f}s. These are not accuracy counts.</p>'
            f'<video controls preload="metadata" src="{url(item["review_video"])}"></video>'
            f'<p><a href="{url(item["frame_records"])}">Every frame and player/ball provenance</a> · '
            f'<a href="{url(item["missing_intervals"])}">Explicit missing intervals</a> · '
            f'<a href="{url(item["verified_final_frame"])}">Actual final frame</a></p></section>')
    total = summary["frame_count"]
    counts = summary["availability"]
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Retained ball baseline</title>'
        '<style>body{max-width:1080px;margin:40px auto;padding:0 20px;background:#101820;color:#eef2f4;font:17px/1.6 sans-serif}' \
        'a{color:#83d3ff}video{width:100%;background:black}section{margin:38px 0}h1,h2{line-height:1.2}</style>' \
        '<h1>Retained player/ball development baseline</h1>' \
        f'<p>{total:,} timeline frames: {total - counts["withheld"]:,} permitted and {counts["withheld"]} protected blackouts. '
        'Saved WASB observations and reviewed player identities are unchanged. '
        f'{counts["observed"]} model points and {counts["missing"]} missing frames measure availability, not accuracy. '
        'No inference, training, interpolation or player rerun was performed.</p>' \
        '<p>These exact three synchronized videos were reviewed by Ryan on October 8. Their historical header says review pending; '
        'the later bound review receipt records completion. That review did not accept the ball phase or confirm every point.</p>' \
        '<p>The separate six-window longer-context reference result is 131/145 matches, one geometric error, 13 missing and zero alarms on five hidden frames. '
        'P003/164 is the geometric error; this does not itself identify a wrong object. Full permitted-frame accuracy and the new continuity/recovery gates remain unassessed.</p>' \
        '<p>Known AI review cues: P001/247 changes to an apparent distractor; P001/440→441 appears to recover from a false arm/torso selection; '
        'P003/63→64 changes from the visible ball to a player side/arm. These are qualitative, previously recorded observations, not new accepted labels.</p>' \
        '<p>The separately accepted three-point gap increment remains preserved and unapplied here. The broader fourteen-fill rule is not adopted.</p>' \
        ''.join(sections) + '<p>Ball centers stay in source image coordinates. Player IDs are display context; no airborne-ball court projection is applied.</p></html>')


def execute(root, config_path):
    config = read_json(config_path)
    if config["schema_version"] != "ball_completion_baseline/v0.1":
        raise ValueError("Unsupported completion baseline config")
    output = repository_path(root, config["output_root"], "data/outputs")
    output.mkdir(parents=True, exist_ok=True)
    source_config = read_json(bound_path(root, config["observation_config"]))
    old_summary = read_json(bound_path(root, config["observation_summary"]))
    human_review = read_json(bound_path(root, config["completed_human_review"]))
    comparison = read_json(bound_path(root, config["historical_longer_context_comparison"]))
    for key in ("campaign_approval", "accepted_bounded_gap_review", "retained_checkpoint"):
        bound_path(root, config[key])
    if human_review["summary"]["sha256"] != config["observation_summary"]["sha256"]:
        raise ValueError("Completed human review belongs to another baseline")
    results = []
    for possession, saved, reviewed in zip(source_config["possessions"], old_summary["possessions"], human_review["clips"], strict=True):
        pid = possession["possession_id"]
        if saved["possession_id"] != pid or reviewed["possession_id"] != pid:
            raise ValueError("Possession review ordering differs")
        observations = read_json(bound_path(root, saved["observations"]))
        validate_observations(possession, observations, config["retained_checkpoint"]["sha256"])
        review = saved["review"]
        if (review["video"] != reviewed["video"] or review["identity"]["observations"] != saved["observations"]
                or review["identity"]["player_context"] != possession["player_context"]
                or review["identity"]["source_video"] != possession["source_video"]):
            raise ValueError("Review transport binding differs from observations/source/players")
        bound_path(root, reviewed["render_receipt"])
        bound_path(root, review["decoded_final_frame"])
        source_path = bound_path(root, possession["source_video"])
        metadata = source_packet_metadata(source_path)
        times = packet_timeline(metadata, possession["source_video"]["frame_count"])
        if any(abs(t["duration_seconds"] - 1 / 25) > 1e-9 for t in times):
            raise ValueError("Original constant-rate review cannot represent this native source timing")
        players = player_records(bound_path(root, possession["player_context"]), possession)
        frames = frame_records(possession, observations, times, players)
        folder = output / pid
        folder.mkdir(exist_ok=True)
        records_path, gaps_path = folder / "frames.json", folder / "missing_intervals.json"
        write_once(folder / "native_packet_timing.json", metadata)
        write_once(records_path, {"schema_version": "ball_completion_frame_records/v0.1",
            "original_observations": saved["observations"], "source_video": possession["source_video"],
            "player_context": possession["player_context"], "model_provenance": observations["model_provenance"],
            "timing": "native packet presentation timestamp plus playback offset from first source PTS",
            "frames": frames})
        gaps = missing_intervals(frames)
        write_once(gaps_path, {"scope": "all automatic-output missing intervals, independent of reference visibility", "intervals": gaps})
        final_path = folder / "verified_final_frame.png"
        video_path = bound_path(root, review["video"])
        verification_path = folder / "video_verification.json"
        if verification_path.exists():
            verification = read_json(verification_path)
            if (verification["video"] != review["video"]
                    or verification["frame_records"] != binding(root, records_path)):
                raise ValueError("Saved verification names another video or timeline")
            bound_path(root, verification["decoded_final_frame"])
        else:
            import cv2
            cv2.setNumThreads(1)
            checked = verify_rendered_video(video_path, frames,
                (possession["source_video"]["height_px"] + HEADER_HEIGHT, possession["source_video"]["width_px"], 3), final_path)
            verification = {"video": review["video"], "frame_records": binding(root, records_path),
                            "decoded_final_frame": binding(root, final_path), **checked}
            write_once(verification_path, verification)
        # Reload the actual emitted records; compare every original producer field.
        emitted = read_json(records_path)["frames"]
        if len(emitted) != len(observations["frames"]) or any(
                any(actual[key] != value for key, value in old.items())
                for actual, old in zip(emitted, observations["frames"], strict=True)):
            raise ValueError("Serialized consumer records altered original observations")
        counts = {state: sum(r["state"] == state for r in emitted) for state in ("observed", "missing", "withheld")}
        if counts != saved["counts"]:
            raise ValueError("Repackaged availability differs from reviewed baseline")
        results.append({"possession_id": pid, "frame_records": binding(root, records_path),
            "native_packet_timing": binding(root, folder / "native_packet_timing.json"),
            "source_video": possession["source_video"], "player_context": possession["player_context"],
            "review_video": review["video"], "verified_final_frame": binding(root, final_path),
            "video_verification": binding(root, verification_path), "completed_human_review": config["completed_human_review"],
            "availability": counts, "training_exposed_frames": sum(r["training_frame"] for r in frames),
            "missing_intervals": binding(root, gaps_path), "longest_missing_interval": max(gaps, key=lambda g: g["duration_seconds"]),
            "accuracy_over_complete_permitted_census": None, "phase_status": "incomplete_not_evaluated"})
    summary = {"schema_version": "ball_completion_baseline_package/v0.1", "config": binding(root, config_path),
        "implementation": binding(root, Path(__file__)), "possessions": results,
        "frame_count": sum(sum(p["availability"].values()) for p in results),
        "availability": {state: sum(p["availability"][state] for p in results) for state in ("observed", "missing", "withheld")},
        "historical_labeled_accuracy": historical_accuracy(comparison),
        "historical_accuracy_source": config["historical_longer_context_comparison"],
        "accepted_bounded_three_gains": {"applied_to_this_baseline": False, "review": config["accepted_bounded_gap_review"]},
        "broader_fourteen_fills_adopted": False, "inference_calls": 0, "training_runs": 0,
        "source_pixel_decodes": 0, "protected_model_inputs": 0, "player_pipeline_reruns": 0,
        "phase_status": "incomplete_new_references_and_final_evaluation_required"}
    write_once(output / "summary.json", summary)
    index_path = output / "index.html"
    markup = index_html(summary, root)
    if index_path.exists() and index_path.read_text(encoding="utf-8") != markup:
        raise ValueError("Existing index differs; preserve it rather than overwrite")
    if not index_path.exists():
        index_path.write_text(markup, encoding="utf-8")
    return {"summary": binding(root, output / "summary.json"), "index": binding(root, index_path),
            "frame_count": summary["frame_count"], "availability": summary["availability"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(json.dumps(execute(ROOT, repository_path(ROOT, args.config)), indent=2))

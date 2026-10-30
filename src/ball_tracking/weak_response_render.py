"""Render a completed fixed NBA selector comparison, one context in RAM.

This CPU-only wrapper does not choose, score, infer or train. Completed block
receipts permit explicit resumption while retaining every interrupted attempt.
The original complete candidate pools remain in their bound JSONL sources.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import html
import json
from pathlib import Path
import time
import traceback
import uuid

from . import weak_response_experiment as experiment
from . import weak_response_review as review
from .weak_response_capture import bind, bound, canonical, read, write_once, validate_context

ROOT = Path(__file__).resolve().parents[2]
OUT = "data/outputs/ball_tracking/weak_response_v0_1"
COMPARISON = OUT + "/comparison_v0_1/completed.json"
VARIANTS = ("sequence_strong", "sequence_weak")
SCHEMA = "weak_response_complete_render/v0.1"


def check(condition, message):
    if not condition:
        raise ValueError(message)


def publish(path, value):
    """Resume only an exactly identical interrupted publication, never overwrite."""
    if Path(path).exists():
        check(read(path) == value, "Existing publication differs: " + str(path))
    else:
        write_once(path, value)


def preflight(root, comparison_path, variant):
    root = Path(root).resolve()
    check(variant in VARIANTS, "Unknown comparison variant")
    comparison_link = bind(root, root / comparison_path)
    comparison = read(bound(root, comparison_link))
    check(comparison["status"] == "completed" and comparison["protected_evaluation_authorized"] is False
          and comparison["model_adopted"] is False and comparison["human_trajectory_acceptance"] is None
          and comparison["new_training_updates"] == comparison["new_model_calls"] == 0,
          "Complete permitted fixed comparison required")
    for source in comparison["source"]:
        bound(root, source)
    bound(root, comparison["config"])
    bound(root, comparison["checkpoint"])
    package = read(bound(root, comparison["paired_inputs"]))
    check(package["protected_evaluation_authorized"] is False
          and package["candidate"]["checkpoint"] == comparison["checkpoint"], "Comparison source/control differs")
    entries, records = package["blocks"], comparison["records"]
    ids = [entry["block"]["block_id"] for entry in entries]
    check(len(entries) == len(records) == len(set(ids)) == 8
          and sum(len(entry["block"]["frames"]) for entry in entries) == 3662
          and ids == [record["block_id"] for record in records], "Complete eight-context comparison required")
    for entry, record in zip(entries, records, strict=True):
        validate_context(entry)
        body = read(bound(root, record["variants"][variant]))
        check(body["block_id"] == record["block_id"] and body["variant"] == variant
              and body["pool_source"] == record["pool_source"]
              and body["references_used_in_selection"] is False, "Chosen record/context/source differs")
        native = read(bound(root, record["variants"]["native"]))
        check(native["block_id"] == record["block_id"]
              and native["observations"] == entry["candidate_observations"], "Native control changed")
    identity = {"schema_version": SCHEMA, "comparison": comparison_link,
        "variant": variant, "paired_inputs": comparison["paired_inputs"], "checkpoint": comparison["checkpoint"],
        "comparison_source": comparison["source"],
        "render_source": [bind(root, root / f"src/ball_tracking/{name}.py") for name in
            ("weak_response_render", "weak_response_review", "completion_sac_references")],
        "candidate_pool_policy": "native_only" if variant == "sequence_strong" else "all",
        "candidate_pool_projection": list(experiment.SELECTOR_FIELDS),
        "human_visual_acceptance": None, "model_adopted": False,
        "protected_evaluation_authorized": False, "model_calls": 0}
    return entries, records, identity


def block_identity(identity, entry, record):
    return {"comparison": identity["comparison"], "variant": identity["variant"],
        "block_id": record["block_id"], "block_sha256": canonical(entry["block"]),
        "native_record": record["variants"]["native"],
        "native_observations_sha256": canonical(entry["candidate_observations"]),
        "choice_record": record["variants"][identity["variant"]], "pool_source": record["pool_source"],
        "candidate_pool_policy": identity["candidate_pool_policy"],
        "candidate_pool_projection": identity["candidate_pool_projection"],
        "render_source": identity["render_source"]}


def verify_block_receipt(root, receipt, expected_identity, block):
    check(receipt["status"] == "completed" and receipt["identity"] == expected_identity,
          "Completed block render identity differs")
    result = read(bound(root, receipt["render_receipt"]))
    started = read(bound(root, receipt["render_started"]))
    check(started["provenance"] == expected_identity and started["input_identity"] == result["input_identity"],
          "Actual render start does not bind the chosen comparison records")
    final = block["frames"][-1]
    check(result["block_id"] == block["block_id"] and result["block_sha256"] == canonical(block)
          and result["decoded_frames"] == result["native_pts_packet_frame_duration_checks"] == len(block["frames"])
          and result["actual_final_native_frame"] == final["source_frame_index"]
          and result["actual_final_source_pts_ticks"] == final["source_pts_ticks"]
          and result["actual_final_duration_ticks"] == final["duration_ticks"]
          and result["added_final_hold_ticks"] == 0 and result["all_decoded_native_keys_verified"] is True
          and result["human_visual_acceptance"] is None and result["candidate_pools_duplicated_in_review"] is False,
          "Completed native frame/final interval evidence differs")
    check(result["input_identity"]["candidate_pool_source"] == expected_identity["pool_source"]
          and result["input_identity"]["baseline_sha256"] == expected_identity["native_observations_sha256"]
          and result["input_identity"]["candidate_pool_policy"] == expected_identity["candidate_pool_policy"]
          and result["input_identity"]["candidate_pool_projection"] == expected_identity["candidate_pool_projection"],
          "Completed review pool transport differs")
    for key in ("video", "actual_final_frame", "frame_records", "encoded_probe"):
        bound(root, result[key])
    return result


def verify_completed(root, result, identity, entries, records):
    check(result["status"] == "completed" and result["identity"] == identity
          and result["native_frames"] == 3662 and len(result["blocks"]) == 8,
          "Completed full review differs")
    bound(root, result["index"])
    bound(root, result["summary"])
    for entry, record, block in zip(entries, records, result["blocks"], strict=True):
        receipt = read(bound(root, block["completion"]))
        actual = verify_block_receipt(root, receipt, block_identity(identity, entry, record), entry["block"])
        check(actual == block["render"], "Master/block render publication differs")
    return result


def execute(root=ROOT, *, comparison_path=COMPARISON, variant, resume=False):
    root = Path(root).resolve()
    entries, records, identity = preflight(root, comparison_path, variant)
    output = root / OUT / f"review_{variant}_v0_1"
    check(not output.exists() or resume, "Existing review requires --resume; preserve all attempts")
    output.mkdir(parents=True, exist_ok=True)
    publish(output / "identity.json", identity)
    if (output / "completed.json").exists():
        return verify_completed(root, read(output / "completed.json"), identity, entries, records)
    run = output / "attempts" / uuid.uuid4().hex
    run.mkdir(parents=True)
    began = time.perf_counter()
    write_once(run / "started.json", {"identity": identity, "created_at_utc": datetime.now(timezone.utc).isoformat()})
    rendered, reused, published = 0, 0, []
    try:
        for entry, record in zip(entries, records, strict=True):
            block, native = entry["block"], entry["candidate_observations"]
            expected = block_identity(identity, entry, record)
            folder = output / "blocks" / experiment.key(block["block_id"])
            folder.mkdir(parents=True, exist_ok=True)
            complete_path = folder / "completed.json"
            if complete_path.exists():
                result = verify_block_receipt(root, read(complete_path), expected, block)
                reused += 1
                print(json.dumps({"event": "reused_verified_render", "variant": variant, "block_id": block["block_id"]}), flush=True)
            else:
                body = read(bound(root, record["variants"][variant]))
                pools = experiment.pool_rows(root, bound(root, record["pool_source"]), block, native)
                if variant == "sequence_strong":
                    pools = [[candidate for candidate in pool if candidate["original_index"] is not None] for pool in pools]
                observations = experiment.materialize_choices(body, pools)
                render_entry = {"block": block, "baseline_observations": native,
                    "candidate_observations": observations, "candidate_pool_source": record["pool_source"],
                    "candidate_pool_policy": identity["candidate_pool_policy"],
                    "candidate_pool_projection": identity["candidate_pool_projection"]}
                attempt = folder / "attempts" / uuid.uuid4().hex
                result = review.render_block(root, render_entry, attempt, provenance=expected)
                receipt = {"status": "completed", "identity": expected,
                           "render_started": bind(root, attempt / "started.json"),
                           "render_receipt": bind(root, attempt / "render_receipt.json")}
                verify_block_receipt(root, receipt, expected, block)
                write_once(complete_path, receipt)
                rendered += 1
                del pools, observations, render_entry, body
                gc.collect()
                print(json.dumps({"event": "rendered_verified", "variant": variant, "block_id": block["block_id"],
                    "native_frames": len(block["frames"]), "elapsed_seconds": time.perf_counter() - began}), flush=True)
            published.append({"block_id": block["block_id"], "completion": bind(root, complete_path), "render": result})
        check(sum(item["render"]["decoded_frames"] for item in published) == 3662, "Incomplete final review")
        sections = []
        for item in published:
            result = item["render"]
            links = {name: (root / result[name]["path"]).relative_to(output).as_posix()
                     for name in ("video", "actual_final_frame", "frame_records")}
            sections.append(f'<section><h2>{html.escape(item["block_id"])}</h2>'
                f'<video controls preload="metadata" src="{html.escape(links["video"], quote=True)}"></video>'
                f'<p>Actual final native frame: {result["actual_final_native_frame"]}. '
                f'<a href="{html.escape(links["actual_final_frame"], quote=True)}">Final frame</a> | '
                f'<a href="{html.escape(links["frame_records"], quote=True)}">Every frame and timestamp</a></p></section>')
        page = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>NBA sequence review</title>'
            '<style>body{font:17px/1.5 system-ui;max-width:1400px;margin:32px auto;padding:0 20px}video{width:100%}</style>'
            f'<h1>NBA sequence review: {html.escape(variant)}</h1><p>Orange/left: cosine-nine native research control. '
            'Cyan/right: fixed sequence candidate. Green: accepted reference where available. All eight supplied '
            'contexts, 3,662 native frames and final intervals are included. Missing choices and uncertain references '
            'remain explicit. Candidate pools are retained once in their bound scientific sources; video records '
            'retain exact chosen indices, geometry, pool counts and digests. Human trajectory and object-identity '
            'review remains pending. No model adoption or ball-phase pass is claimed.</p>' + ''.join(sections) + '</html>')
        index = output / "index.html"
        if index.exists():
            check(index.read_text(encoding="utf-8") == page, "Existing master index differs")
        else:
            index.write_text(page, encoding="utf-8")
        summary = {"schema_version": SCHEMA, "identity": identity, "blocks": published, "native_frames": 3662,
                   "human_visual_acceptance": None, "protected_evaluation_authorized": False, "model_adopted": False}
        publish(output / "summary.json", summary)
        result = {**summary, "status": "completed", "summary": bind(root, output / "summary.json"),
                  "index": bind(root, index), "completion_attempt": run.relative_to(root).as_posix(),
                  "rendered_blocks_this_attempt": rendered, "reused_completed_blocks": reused,
                  "elapsed_seconds_this_attempt": time.perf_counter() - began}
        verify_completed(root, result, identity, entries, records)
        write_once(output / "completed.json", result)
        write_once(run / "completed.json", {"completion": bind(root, output / "completed.json"),
            "rendered_blocks": rendered, "reused_blocks": reused, "elapsed_seconds": time.perf_counter() - began})
        return result
    except BaseException as error:
        write_once(run / "failed.json", {"identity": identity, "error": str(error), "traceback": traceback.format_exc(),
            "rendered_blocks": rendered, "reused_blocks": reused, "elapsed_seconds": time.perf_counter() - began})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--comparison", default=COMPARISON)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.run:
        result = execute(comparison_path=args.comparison, variant=args.variant, resume=args.resume)
        print(json.dumps({key: result[key] for key in
            ("status", "native_frames", "index", "rendered_blocks_this_attempt", "reused_completed_blocks", "elapsed_seconds_this_attempt")}))
    else:
        entries, _, identity = preflight(ROOT, args.comparison, args.variant)
        print(json.dumps({"status": "render_preflight_only_no_pixels", "contexts": len(entries), "native_frames": 3662,
                          "identity": identity}))


if __name__ == "__main__":
    main()

"""Assemble accepted references into fixed training and selection roles.

This metadata-only producer never decodes videos, runs a model, or changes labels.
The complete curated census is bound for later evaluation; its new labels never
enter training or checkpoint selection. Historical NFHS roles stay explicit.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from pathlib import Path
import hashlib
import json

from .annotations import FrameAnnotation, SourceVideo, load_annotations
from .completion_nba_acceptance import accepted_nba_reference
from .completion_sac_acceptance import accepted_sac_reference
from .completion_references import accepted_inventory, presentation_timeline
from .completion_sac_references import _packet_census
from .nba_wasb_adaptation import _selected_reference
from .wasb_training import annotation_kind, build_training_manifest

SCHEMA = "completion_training_package/v0.1"
STATUS = "accepted_references_prepared_for_freeze"
CAMPAIGN = "data/outputs/ball_tracking/completion_campaign_v0_1"
NBA_TRAINING_GAMES = {"0022500829", "0022400868", "0022400866"}
NBA_VALIDATION_GAME = "0022400879"
EXCLUDED_GAMES = {"0022500828", "0022500843"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Evidence:
    """Hash each unchanged local file once per build; never open image pixels."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.cache = {}
        self.missing = []

    def path(self, name):
        p = (self.root / name).resolve()
        require(p.is_relative_to(self.root), "Evidence path escapes repository")
        return p

    def bind(self, name, expected=None):
        p = self.path(name)
        stat = p.stat()
        key = (p, stat.st_size, stat.st_mtime_ns)
        if key not in self.cache:
            digest = hashlib.sha256()
            with p.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            self.cache[key] = {"path": p.relative_to(self.root).as_posix(),
                               "sha256": digest.hexdigest(), "bytes": stat.st_size}
        actual = self.cache[key]
        if expected:
            require(all(actual[k] == expected[k] for k in ("sha256", "bytes") if k in expected),
                    "Evidence binding changed: " + str(name))
        return dict(actual)

    def bound_json(self, entry):
        self.bind(entry["path"], entry)
        return read(self.path(entry["path"]))

    def png(self, value, block_id, frame_index):
        require(isinstance(value, dict) and all(value.get(k) for k in ("path", "sha256", "rgb_sha256")),
                "PNG needs original file and native RGB hash bindings")
        if not self.path(value["path"]).is_file():
            self.missing.append({"block_id": block_id, "source_frame_index": frame_index, "png": value})
            return dict(value)
        return {**self.bind(value["path"], value), "rgb_sha256": value["rgb_sha256"]}


def normalize_block(block):
    """Validate an emitted block, retaining original annotations and native time."""
    require(block["role"] in {"training", "checkpoint_validation"}, "Unsupported block role")
    require(block["domain"] in {"nba", "nfhs"}, "Unsupported block domain")
    game = block["game_id"]
    if block["domain"] == "nba":
        require(game not in EXCLUDED_GAMES, "Excluded NBA game")
        required = "training" if game in NBA_TRAINING_GAMES else "checkpoint_validation" if game == NBA_VALIDATION_GAME else None
        require(block["role"] == required, "NBA parent-game role changed")
    else:
        require(game == block["possession_id"], "NFHS game_id must identify its possession")
    frames = block["frames"]
    require(len(frames) >= 3, "Temporal block requires at least three frames")
    indices = [f["source_frame_index"] for f in frames]
    require(indices == list(range(indices[0], indices[-1] + 1)), "Nonconsecutive or duplicate native frames")
    require(Fraction(block["time_base"]) > 0, "Invalid native time base")
    bounds = type("Bounds", (), block["source_video"])()
    for position, frame in enumerate(frames):
        require(type(frame["source_pts_ticks"]) is int and type(frame["duration_ticks"]) is int
                and frame["duration_ticks"] > 0, "Invalid native timing")
        annotation = FrameAnnotation.from_mapping(frame["annotation"], position, bounds)
        require(annotation.annotation_status == "labeled" and annotation.frame_index == indices[position],
                "Native annotation/frame join differs")
        if position + 1 < len(frames):
            require(frames[position + 1]["source_pts_ticks"] - frame["source_pts_ticks"] == frame["duration_ticks"],
                    "Native PTS gap or changed duration")
        frame["kind"] = annotation_kind(annotation)
        frame["valid_output_channel"] = frame["kind"] != "masked"
    block["source_id"] = block["source_video"]["sha256"]
    block["range_inclusive"] = [indices[0], indices[-1]]
    return block


def compose_triplets(blocks):
    """Only within-block native chronology; unknown channels stay loss-masked."""
    usable, excluded, seen = [], [], set()
    block_ids = set()
    for block in blocks:
        require(block["role"] == "training", "Validation/evaluation block cannot produce training triplets")
        require(block["block_id"] not in block_ids, "Duplicate training block ID")
        block_ids.add(block["block_id"])
        normalize_block(block)
        for frame in block["frames"]:
            key = (block["source_id"], frame["source_frame_index"])
            require(key not in seen, "Duplicate training native source frame")
            seen.add(key)
        for offset in range(len(block["frames"]) - 2):
            frames = block["frames"][offset:offset + 3]
            ids = [f["source_frame_index"] for f in frames]
            item = {"triplet_id": f"{block['block_id']}/frame_{ids[0]:06d}",
                    "block_id": block["block_id"], "domain": block["domain"], "game_id": block["game_id"],
                    "source_id": block["source_id"], "frame_indices": ids,
                    "valid_output_channels": [f["valid_output_channel"] for f in frames]}
            (usable if any(item["valid_output_channels"]) else excluded).append(item)
    return usable, excluded


def guard_partition(training, validation, protected):
    seen, block_ids = {}, set()
    for wanted, blocks in (("training", training), ("checkpoint_validation", validation)):
        for block in blocks:
            normalize_block(block)
            require(block["role"] == wanted, "Block placed into the wrong package partition")
            require(block["block_id"] not in block_ids, "Repeated block ID across partitions")
            block_ids.add(block["block_id"])
            for f in block["frames"]:
                key = (block["source_id"], f["source_frame_index"])
                require(key not in seen, "Training/validation native frames overlap")
                seen[key] = wanted
                if block["domain"] == "nfhs":
                    require(not any(lo <= key[1] <= hi for lo, hi in protected[block["possession_id"]]),
                            "Protected NFHS frame in model context")
    return len(seen)


def _new_nba(root, evidence, inventory, roles):
    blocks, bindings = [], []
    episodes = {e["episode_id"]: e for e in roles["episodes"]}
    require(len(inventory["accepted_nba_reference_entries"]) == 24, "Expected all24 accepted NBA batches")
    for entry in inventory["accepted_nba_reference_entries"]:
        header = evidence.bound_json(entry)
        reader = accepted_sac_reference if header["schema_version"] == "completion_sac_reference_accepted/v0.1" else accepted_nba_reference
        doc, authority = reader(root, entry)
        bindings.extend(authority)
        ep = episodes[doc["episode_id"]]
        require(doc["role"] == ep["role"] and doc["game_id"] == ep["game_id"], "Fixed NBA episode role differs")
        require(doc["training_eligible"] == (doc["role"] == "training")
                and doc["checkpoint_selection_eligible"] == (doc["role"] == "checkpoint_validation"), "Accepted NBA role flags differ")
        source = doc["source_metadata"]
        require(source["sha256"] == ep["source"]["sha256"], "NBA source changed")
        frames = []
        for f, row in zip(doc["frames"], doc["annotations"]):
            frames.append({"source_frame_index": f["source_frame_index"], "source_pts_ticks": f["native_pts_ticks"],
                           "duration_ticks": f["native_duration_ticks"],
                           "png": evidence.png(f["source_png"], doc["episode_id"], f["source_frame_index"]), "annotation": row})
        require(len(frames) == len(doc["frames"]) == len(doc["annotations"]) == ep["new_frame_judgments"], "Accepted NBA census differs")
        blocks.append(normalize_block({"block_id": doc["episode_id"], "domain": "nba", "game_id": doc["game_id"],
            "role": doc["role"], "source_video": {"path": source["path"], "sha256": source["sha256"],
                "width_px": source["width"], "height_px": source["height"], "frame_count": source["decoded_frames"]},
            "time_base": source["time_base"], "frames": frames, "reference_bindings": authority,
            "reference_origin": doc["annotation_origin"], "human_review": doc["human_review"],
            "selection_category": ep["selection_category"], "observed_source_content": ep["observed_source_content"]}))
    require(sum(len(b["frames"]) for b in blocks) == 3839, "New NBA total differs")
    return blocks, bindings


def _retained_sac(root, evidence, old, roles):
    blocks, bindings = [], []
    # Reuse native packet timing from the accepted SAC campaign source, including
    # the last retained frame duration; never guess it from nominal FPS.
    packet_path = f"{CAMPAIGN}/nba_reference_batch_19/source_packet_timing.json"
    accepted19 = read(root / f"{CAMPAIGN}/nba_reference_batch_19/accepted/reference.json")
    packet_binding = evidence.bind(packet_path, accepted19["evidence"]["source_packet_timing"])
    episode = next(e for e in roles["episodes"] if e["episode_id"] == accepted19["episode_id"])
    packets = _packet_census(episode, read(evidence.path(packet_path)))
    source_count = episode["source"]["decoded_frames"]
    for spec in old["nba_training_windows"]:
        entry = old["nba_references"][spec["reference_kind"]]
        document = evidence.bound_json(entry)
        reference = _selected_reference(root, document, spec)
        bindings.append(evidence.bind(entry["path"], entry))
        source = reference["source_video"]
        require(source["frame_count"] == source_count
                and source["sha256"] == episode["source"]["sha256"], "Retained SAC source identity differs")
        frames = []
        for f, row in zip(reference["frames"], reference["annotations"]):
            index = f["source_frame_index"]
            require(index + 1 < len(packets), "SAC final interval needs following global PTS")
            pts = packets[index]["pts"]
            duration = packets[index + 1]["pts"] - pts
            require(f["source_pts_ticks"] == pts and reference["time_base"] == episode["source"]["time_base"],
                    "Retained SAC native timing authority differs")
            frames.append({"source_frame_index": index, "source_pts_ticks": pts,
                           "duration_ticks": duration, "raw_packet_duration_ticks": packets[index].get("duration"),
                           "duration_authority": "next_global_presentation_pts",
                           "png": evidence.png(f["png"], spec["window_id"], index),
                           "annotation": row})
        require([frames[0]["source_frame_index"], frames[-1]["source_frame_index"]] == spec["source_frame_range_inclusive"], "Retained SAC range changed")
        blocks.append(normalize_block({"block_id": spec["window_id"], "domain": "nba", "game_id": spec["game_id"],
            "role": "training", "source_video": source, "time_base": reference["time_base"], "frames": frames,
            "reference_bindings": [evidence.bind(entry["path"], entry), packet_binding],
            "original_reference_bindings": reference["bindings"], "reference_origin": reference["origin"],
            "human_review": reference["human_review"], "historical_replay": True}))
    return blocks, bindings + [packet_binding]


def _nfhs(root, evidence, old):
    config = evidence.bound_json(old["nfhs_training_config"])
    manifest, label_sets = build_training_manifest(root, config)
    require(manifest["counts"]["reviewed_frames"] == 150, "Historical NFHS training count differs")
    transfer = evidence.bound_json(config["transfer_config"])
    input_path = f"{CAMPAIGN}/training_inputs_nfhs_v0_1/package_inputs.json"
    inputs_binding = evidence.bind(input_path)
    inputs = read(evidence.path(input_path))
    require(inputs["status"] == "passed" and inputs["frames"] == 300 and inputs["protected_application_frames"] == 0,
            "NFHS source preparation incomplete")
    by_id = {b["block_id"]: b for b in inputs["blocks"]}
    require(len(by_id) == 11, "NFHS fixed context inventory differs")
    native = {}
    timing_authorities = []
    for entry in inputs["native_timing_bindings"]:
        pid = Path(entry["path"]).name.removesuffix("_packet_timing.json")
        source = next(b["source_video"] for b in inputs["blocks"] if b["possession_id"] == pid)
        native[pid] = presentation_timeline(evidence.bound_json(entry), source["frame_count"])
        timing_authorities.append(evidence.bind(entry["path"], entry))
    specs = [(b, "training") for b in config["training_blocks"]] + [(b, "checkpoint_validation") for b in transfer["windows"]]
    blocks, authorities = [], [inputs_binding, evidence.bind(old["nfhs_training_config"]["path"], old["nfhs_training_config"]), evidence.bind(config["transfer_config"]["path"], config["transfer_config"]), *timing_authorities]
    for spec, role in specs:
        block_id = spec["window_id"]; prepared = by_id[block_id]
        require(prepared["role"] == role and prepared["source_video"] == spec["source_video"], "NFHS prepared source/role differs")
        if role == "training":
            rows = [a.to_dict() for a in label_sets[block_id].annotations]
            refs = [evidence.bind(s["annotation"]["path"], s["annotation"]) for s in spec["annotation_segments"]]
        else:
            labels = load_annotations(evidence.path(spec["annotation"]["path"]))
            require(labels.review.status == "reviewed" and labels.source_video.to_dict() == spec["source_video"]
                    and labels.possession_id == spec["possession_id"], "NFHS development review/source differs")
            rows = [a.to_dict() for a in labels.annotations]
            refs = [evidence.bind(spec["annotation"]["path"], spec["annotation"])]
        authorities.extend(refs)
        require([r["frame_index"] for r in rows] == list(range(spec["start_frame_index"], spec["end_frame_index"] + 1)), "NFHS exact context/annotation census differs")
        require([f["source_frame_index"] for f in prepared["frames"]] == [r["frame_index"] for r in rows], "NFHS prepared pixel census differs")
        for frame in prepared["frames"]:
            timing = native[spec["possession_id"]][frame["source_frame_index"]]
            require(frame["source_pts_ticks"] == timing["native_pts_ticks"]
                    and frame["duration_ticks"] == timing["native_duration_ticks"]
                    and prepared["time_base"] == timing["native_time_base"],
                    "NFHS source timing differs from bound native packet authority")
        frames = [{**f, "png": evidence.png(f["png"], block_id, f["source_frame_index"]), "annotation": row}
                  for f, row in zip(prepared["frames"], rows)]
        blocks.append(normalize_block({"block_id": block_id, "domain": "nfhs", "game_id": spec["possession_id"],
            "possession_id": spec["possession_id"], "role": role, "source_video": spec["source_video"],
            "time_base": prepared["time_base"], "frames": frames, "reference_bindings": refs + [inputs_binding],
            "historical_role": "historical_training" if role == "training" else "checkpoint_selection_development",
            "context_policy": "original_fixed_block_no_padding_no_cross_boundary_context"}))
    return blocks, authorities


def build_package(root, curated_inventory_path):
    """Return the complete accepted package; caller separately freezes its recipe."""
    root = Path(root).resolve(); evidence = Evidence(root)
    inventory_path = evidence.path(curated_inventory_path)
    curated = read(inventory_path)
    require(curated["totals"] == {"accepted_permitted": 1273, "permitted": 1273, "uncovered": 0}, "Complete accepted curated census is required")
    cfg = read(root / "configs/ball_tracking/completion_campaign/reference_batch_23_v0_1.json")
    cfg["additional_accepted_references"] = curated["accepted_campaign_reference_entries"]
    accepted, curated_authorities = accepted_inventory(root, cfg)
    require(len(accepted) == 1273, "Curated accepted authority census differs")
    contract = read(root / cfg["source_contract"])
    protected = {p["possession_id"]: p["protected_ranges"] for p in contract["possessions"]}
    roles_path = "configs/ball_tracking/completion_campaign/source_roles_v0_1.json"
    roles = read(root / roles_path)
    nba_path = f"{CAMPAIGN}/accepted_nba_reference_inventory_after_batch_24.json"
    nba_inventory = read(root / nba_path)
    evidence.bind(roles_path, nba_inventory["source_roles"])
    blocks, authorities = _new_nba(root, evidence, nba_inventory, roles)
    old_path = "configs/ball_tracking/wasb_experiments/nba_wasb_adaptation_v0_1.json"
    old = read(root / old_path)
    old_blocks, old_authorities = _retained_sac(root, evidence, old, roles)
    nfhs_blocks, nfhs_authorities = _nfhs(root, evidence, old)
    blocks += old_blocks + nfhs_blocks
    training = [b for b in blocks if b["role"] == "training"]
    validation = [b for b in blocks if b["role"] == "checkpoint_validation"]
    unique = guard_partition(training, validation, protected)
    triplets, masked = compose_triplets(training)
    counts = {"training_frames": sum(len(b["frames"]) for b in training),
              "validation_frames": sum(len(b["frames"]) for b in validation),
              "training_blocks": len(training), "validation_blocks": len(validation),
              "training_triplets": len(triplets), "excluded_all_masked_triplets": len(masked),
              "unique_model_source_frames": unique, "curated_evaluation_census": len(accepted),
              "new_nba_training_frames": 2879, "new_nba_validation_frames": 960,
              "retained_sac_training_frames": 300, "retained_nfhs_training_frames": 150,
              "nfhs_selection_frames": 150}
    require(counts["training_frames"] == 3329 and counts["validation_frames"] == 1110, "Package role totals differ")
    kinds = {role: dict(Counter(f["kind"] for b in selected for f in b["frames"]))
             for role, selected in (("training", training), ("checkpoint_validation", validation))}
    return {"schema_version": SCHEMA, "status": STATUS, "counts": counts, "supervision_counts": kinds,
            "training_blocks": training, "validation_blocks": validation, "training_triplets": triplets,
            "excluded_all_masked_triplets": masked, "missing_png_assets": evidence.missing,
            "all_png_assets_available": not evidence.missing, "source_roles": evidence.bind(roles_path),
            "source_contract": evidence.bind(cfg["source_contract"]), "protected_ranges": protected,
            "accepted_nba_inventory": evidence.bind(nba_path), "historical_training_recipe": evidence.bind(old_path),
            "reference_bindings": authorities + old_authorities + nfhs_authorities,
            "curated_evaluation_only": {"inventory": evidence.bind(inventory_path), "authorities": curated_authorities,
                "frames": 1273, "new_campaign_rows_training_eligible": False,
                "new_campaign_rows_checkpoint_selection_eligible": False,
                "historical_roles_preserved": True, "labels_copied_into_training_from_census": 0},
            "coverage": [{"block_id": b["block_id"], "game_id": b["game_id"], "role": b["role"],
                          "selection_category": b.get("selection_category"), "observed_source_content": b.get("observed_source_content"),
                          "visibility_counts": dict(Counter(f["annotation"]["visibility"] for f in b["frames"]))}
                         for b in blocks if "selection_category" in b],
            "model_calls": 0, "source_video_decodes": 0, "protected_evaluation_authorized": False,
            "executable_recipe_frozen": False, "annotation_authorship_changed": False,
            "native_time_policy": "original_container_PTS_duration_per_source; no nominal-FPS reconstruction"}

"""Pure YOLO crop geometry and simple selectors; no model or file access."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .annotations import SourceVideo
from .detections import BallDetectionRun, ModelProvenance, SCHEMA_VERSION
from .development_experiments import canonical_sha256, closed, require_digest
from .temporal_association import THRESHOLDS
from .tiled_candidates import combine_views, crop_views, finite_nonnegative

ARMS = ("yolo_all_exported", "yolo_top_one", "yolo_top_twenty")
SCHEMA = "ball_yolo_crop_observations/v0.1"
CANDIDATE_SCHEMA = "ball_yolo_crop_candidates/v0.1"
VIEW_FIELDS = {"view", "prediction", "elapsed_seconds", "cuda_peak_allocated_bytes", "attempt_id"}


@dataclass(frozen=True)
class SelectorConfig:
    arm: str
    confidence_threshold: float

    def __post_init__(self):
        if (self.arm not in ARMS or isinstance(self.confidence_threshold, bool)
                or not isinstance(self.confidence_threshold, (int, float))
                or self.confidence_threshold not in THRESHOLDS):
            raise ValueError("Undeclared YOLO selector/confidence")

    def to_dict(self):
        return asdict(self)

    @property
    def variant_id(self):
        return self.arm + "_" + canonical_sha256(self.to_dict())[:16]

    @classmethod
    def from_mapping(cls, value):
        return cls(**closed(value, set(cls.__dataclass_fields__), "YOLO selector config"))


def experiment_grid():
    return tuple(SelectorConfig(arm, threshold) for threshold in THRESHOLDS for arm in ARMS)


def make_frame(index, source_png, records, source, model):
    """Translate local geometry, retaining view provenance and all duplicates."""
    if type(index) is not int or not 0 <= index < source.frame_count:
        raise ValueError("Invalid source frame")
    if not isinstance(records, list) or len(records) != 4:
        raise ValueError("Exactly four completed crop records required")
    geometry_records = []
    from .yolo11x_adapter import validate_prediction
    for record, view in zip(records, crop_views()):
        r = closed(record, VIEW_FIELDS, "YOLO crop record")
        if r["view"] != view or not isinstance(r["attempt_id"], str) or not r["attempt_id"]:
            raise ValueError("Crop identity/attempt mismatch")
        finite_nonnegative(r["elapsed_seconds"], "crop seconds")
        if type(r["cuda_peak_allocated_bytes"]) is not int or r["cuda_peak_allocated_bytes"] < 0:
            raise ValueError("Invalid crop peak memory")
        validate_prediction(r["prediction"], model)
        geometry_records.append({"view": view, "candidates": r["prediction"]["candidates"],
                                 "elapsed_seconds": r["elapsed_seconds"],
                                 "cuda_peak_allocated_bytes": r["cuda_peak_allocated_bytes"]})
    candidates = combine_views(geometry_records, source, model)
    return {"frame_index": index, "source_png": source_png, "views": records,
            "candidates": candidates, "unique_project_crop_units": 4,
            "elapsed_seconds": sum(r["elapsed_seconds"] for r in records)}


def make_output(header, frames):
    return {"schema_version": CANDIDATE_SCHEMA, "header": header, "frames": frames,
            "content_sha256": canonical_sha256({"header": header, "frames": frames})}


def validate_output(value, header):
    value = closed(value, {"schema_version", "header", "frames", "content_sha256"}, "YOLO candidates")
    if (value["schema_version"] != CANDIDATE_SCHEMA or value["header"] != header
            or value["content_sha256"] != canonical_sha256({"header": header, "frames": value["frames"]})):
        raise ValueError("YOLO candidate content/provenance mismatch")
    w = header["window"]
    source = SourceVideo.from_mapping(w["source_video"])
    model = ModelProvenance.from_mapping(header["per_view_model_provenance"])
    expected = list(range(w["start_frame_index"], w["end_frame_index"] + 1))
    if not isinstance(value["frames"], list) or [f["frame_index"] for f in value["frames"]] != expected:
        raise ValueError("Incomplete candidate window")
    inventory = {r["frame_index"]: r["source_png"] for r in header["source_frames"]}
    for frame in value["frames"]:
        expected_frame = make_frame(frame["frame_index"], inventory[frame["frame_index"]], frame["views"], source, model)
        if canonical_sha256(frame) != canonical_sha256(expected_frame):
            raise ValueError("Candidate geometry/order/source differs from saved crop records")
    return value


def candidate_run(payload):
    """Typed evaluator view; original crop and postprocessing provenance stays in payload."""
    payload = validate_output(payload, payload["header"])
    w = payload["header"]["window"]
    model = ModelProvenance.from_mapping(payload["header"]["per_view_model_provenance"])
    model = replace(model, tiling_enabled=True, postprocessing_description=model.postprocessing_description
                    + "; four fixed crop union; source-coordinate translation; cross-crop duplicates retained")
    return BallDetectionRun.from_mapping({"schema_version": SCHEMA_VERSION,
        "detection_run_id": w["window_id"] + "_yolo11x", "annotation_set_id": w["annotation_set_id"],
        "possession_id": w["possession_id"], "source_video": w["source_video"],
        "window": {k: w[k] for k in ("start_frame_index", "end_frame_index")}, "model_provenance": model.to_dict(),
        "frames": [{"frame_index": f["frame_index"], "inference_status": "completed", "failure_reason": None,
                    "detections": [c["detection"] for c in f["candidates"]]} for f in payload["frames"]]})


def select_candidates(run, config, code_commit):
    require_digest(code_commit, "selector commit", 40)
    config = SelectorConfig.from_mapping(config.to_dict())
    run = BallDetectionRun.from_mapping(run.to_dict())
    if config.confidence_threshold < run.model_provenance.export_confidence_floor:
        raise ValueError("Selector threshold below exported floor")
    frames = []
    for frame in run.frames:
        if frame.inference_status != "completed" or frame.detections is None:
            raise ValueError("Selectors require complete detector frames")
        if any(b.confidence > a.confidence for a, b in zip(frame.detections, frame.detections[1:])):
            raise ValueError("Global candidate confidence order differs")
        accepted = [c.candidate_index for c in frame.detections if c.confidence >= config.confidence_threshold]
        count = {ARMS[0]: len(accepted), ARMS[1]: 1, ARMS[2]: 20}[config.arm]
        emitted = accepted[:count]
        frames.append({"frame_index": frame.frame_index, "horizon_start": frame.frame_index,
            "horizon_end": frame.frame_index, "emitted_candidate_indices": emitted,
            "candidate_decisions": [{"candidate_index": c.candidate_index, "disposition":
                "below_threshold" if c.candidate_index not in accepted else
                "emitted" if c.candidate_index in emitted else "outside_selector_cap"} for c in frame.detections],
            "ranking": None, "decision_reason": "simple_selector_emitted" if emitted else "no_qualifying_candidate",
            "output_state": "tentative_observation" if emitted else "no_accepted_observation"})
    return {"schema_version": SCHEMA, "variant_id": config.variant_id, "config": config.to_dict(),
        "ranking_code_commit": code_commit, "detector_code_commit": run.model_provenance.code_commit,
        "input_candidate_content_sha256": canonical_sha256(run.to_dict()), "source_video": run.source_video.to_dict(),
        "window": run.window.to_dict(), "possession_id": run.possession_id, "frames": frames,
        "score_semantics": "Original detector confidence; no calibrated cross-detector probability equivalence; no temporal ranking.",
        "selected_operating_point": None, "quality_gate": None}


def validate_observations(value, run):
    config = SelectorConfig.from_mapping(value.get("config"))
    expected = select_candidates(run, config, value.get("ranking_code_commit"))
    if canonical_sha256(value) != canonical_sha256(expected):
        raise ValueError("Saved YOLO selector observation differs")
    return config


def validate_saved_structure(value, run):
    """Check saved references and semantics without selecting candidates again."""
    closed(value, {"schema_version", "variant_id", "config", "ranking_code_commit", "detector_code_commit",
                  "input_candidate_content_sha256", "source_video", "window", "possession_id", "frames",
                  "score_semantics", "selected_operating_point", "quality_gate"}, "saved selector observation")
    config = SelectorConfig.from_mapping(value.get("config"))
    expected_fields = {"frame_index", "horizon_start", "horizon_end", "emitted_candidate_indices",
                       "candidate_decisions", "ranking", "decision_reason", "output_state"}
    if not isinstance(value.get("frames"), list) or len(value["frames"]) != len(run.frames):
        raise ValueError("Incomplete saved observation frames")
    for saved, frame in zip(value["frames"], run.frames):
        closed(saved, expected_fields, "saved selector frame")
        indices = saved["emitted_candidate_indices"]
        lookup = {c.candidate_index: c for c in frame.detections}
        qualifying = [c.candidate_index for c in frame.detections if c.confidence >= config.confidence_threshold]
        cap = {ARMS[0]: len(qualifying), ARMS[1]: 1, ARMS[2]: 20}[config.arm]
        if indices != qualifying[:cap]:
            raise ValueError("Saved emission differs from exact qualifying confidence prefix")
        if (any(type(saved[k]) is not int or saved[k] != frame.frame_index for k in ("frame_index", "horizon_start", "horizon_end"))
                or not isinstance(indices, list) or any(type(i) is not int or i not in lookup for i in indices)
                or len(indices) != len(set(indices)) or indices != sorted(indices)
                or any(lookup[i].confidence < config.confidence_threshold for i in indices)
                or (config.arm == ARMS[1] and len(indices) > 1) or (config.arm == ARMS[2] and len(indices) > 20)
                or saved["ranking"] is not None
                or saved["decision_reason"] != ("simple_selector_emitted" if indices else "no_qualifying_candidate")
                or saved["output_state"] != ("tentative_observation" if indices else "no_accepted_observation")):
            raise ValueError("Invalid saved emitted references/selector state")
        decisions = saved["candidate_decisions"]
        if not isinstance(decisions, list) or len(decisions) != len(lookup):
            raise ValueError("Saved decisions must cover every original candidate")
        for decision, candidate in zip(decisions, frame.detections):
            closed(decision, {"candidate_index", "disposition"}, "saved candidate decision")
            expected = ("below_threshold" if candidate.confidence < config.confidence_threshold else
                        "emitted" if candidate.candidate_index in indices else "outside_selector_cap")
            if (type(decision["candidate_index"]) is not int or decision["candidate_index"] != candidate.candidate_index
                    or decision["disposition"] != expected or (config.arm == ARMS[0] and expected == "outside_selector_cap")):
                raise ValueError("Saved candidate decisions differ from original references")
    return config

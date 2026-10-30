"""Frozen YOLO11x postprocessed-candidate adapter with synthetic-only warmup.

Imports of the optional detector runtime are lazy. Pure validation is usable
in the baseline environment and never reads project pixels or annotations.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import math
import os
import re
import sys
from pathlib import Path

from .detections import BallDetection, ModelProvenance

PACKAGE_VERSION = "8.4.171"
WEIGHTS_IDENTIFIER = "yolo11x.pt"
WEIGHTS_SHA256 = "7bc158aa95c0ebfdd87f70f01653c1131b93e92522dbe15c228bcd742e773a24"
MODEL_NAME = "Ultralytics YOLO11x Detect COCO"
RESIZE_MODE = "640x640 fixed square RGB letterbox; 640x360 content and 140px vertical pads; divide by255"
POSTPROCESSING = (
    "YOLO class32 sports ball mapped to COCO category37; best-class-only assignment; "
    "torchvision class-aware NMS IoU0.7/max_det300 per crop; predictor conf0 then inclusive0.01 export; "
    "original return order preserved; no global NMS, player/context or temporal rule"
)
INPUT_TRANSFORM = {
    "source_width_px": 1152, "source_height_px": 648,
    "input_width_px": 640, "input_height_px": 640,
    "resized_width_px": 640, "resized_height_px": 360,
    "scale_x": 640 / 1152, "scale_y": 360 / 648,
    "pad_left_px": 0, "pad_right_px": 0, "pad_top_px": 140, "pad_bottom_px": 140,
    "channel_order_input": "RGB", "predictor_array_channel_order": "BGR",
    "tensor_channel_order": "RGB", "normalization": "divide_by_255",
}
PREDICT_ARGS = {
    "imgsz": 640, "rect": False, "half": False, "quantize": 32, "batch": 1,
    "classes": [32], "conf": 0.0, "iou": 0.7, "max_det": 300,
    "agnostic_nms": False, "augment": False, "compile": False,
    "verbose": False, "save": False, "save_txt": False, "save_crop": False,
    "visualize": False, "stream": False, "device": 0,
}


class YOLOContractError(ValueError):
    """A changed or malformed detector contract must not create evidence."""


def _closed(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise YOLOContractError(f"Invalid {label} fields")
    return value


def _hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise YOLOContractError(f"Nonfinite/non-numeric {label}")
    return float(value)


def _integer(value, minimum, label):
    if type(value) is not int or value < minimum:
        raise YOLOContractError(f"Invalid {label}")
    return value


def validate_model_provenance(model):
    if not isinstance(model, ModelProvenance):
        model = ModelProvenance.from_mapping(model)
    expected = {"model_name": MODEL_NAME, "package_name": "ultralytics", "package_version": PACKAGE_VERSION,
                "weights_identifier": WEIGHTS_IDENTIFIER, "weights_sha256": WEIGHTS_SHA256,
                "precision": "float32", "input_width_px": 640, "input_height_px": 640,
                "resize_mode": RESIZE_MODE, "tiling_enabled": False,
                "target_class_id": 37, "target_class_name": "sports ball", "export_confidence_floor": .01,
                "postprocessing_description": POSTPROCESSING}
    if any(getattr(model, k) != v for k, v in expected.items()):
        raise YOLOContractError("Frozen per-crop model provenance changed")
    if not re.fullmatch(r"[0-9a-f]{40}", model.code_commit) or not model.device.startswith("cuda:"):
        raise YOLOContractError("Invalid model code/device provenance")
    return model


def _root_path(root, item):
    _closed(item, {"path", "sha256"}, "runtime file binding")
    path = (root / item["path"]).resolve()
    if not path.is_relative_to(root / "data/outputs/ball_tracking/yolo11x_runtime"):
        raise YOLOContractError("Runtime binding escapes its isolated directory")
    if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) or _hash(path) != item["sha256"]:
        raise YOLOContractError(f"Runtime file changed: {item['path']}")
    return path


def inspect_runtime(weights_path, runtime_record, code_commit, *, require_synthetic_validation=True):
    """Verify the frozen installed runtime without constructing a model."""
    root = Path(__file__).resolve().parents[2]
    weights_path = Path(weights_path).resolve()
    if runtime_record.get("schema_version") != "ball_yolo11x_runtime/v0.1":
        raise YOLOContractError("Unsupported runtime record")
    if require_synthetic_validation and runtime_record.get("synthetic_validation", {}).get("status") != "passed":
        raise YOLOContractError("Runtime synthetic validation must be completed before project use")
    if _root_path(root, runtime_record["weights"]) != weights_path or weights_path.name != WEIGHTS_IDENTIFIER:
        raise YOLOContractError("Wrong checkpoint path")
    if runtime_record["weights"]["sha256"] != WEIGHTS_SHA256:
        raise YOLOContractError("Wrong publisher checkpoint digest")
    if Path(runtime_record["python"]["executable"]).resolve() != Path(sys.executable).resolve():
        raise YOLOContractError("Use the isolated approved Python interpreter")
    if runtime_record["python"]["version"] != sys.version:
        raise YOLOContractError("Python build changed")
    packages = runtime_record["packages"]
    if not isinstance(packages, dict) or packages.get("ultralytics") != PACKAGE_VERSION:
        raise YOLOContractError("Wrong Ultralytics package version")
    installed_versions = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    if installed_versions != packages:
        raise YOLOContractError("Exact installed distribution inventory changed")
    for name, version in packages.items():
        if importlib.metadata.version(name) != version:
            raise YOLOContractError(f"Runtime distribution changed: {name}")
    installed = json.loads(_root_path(root, runtime_record["installed_files_manifest"]).read_text(encoding="utf-8"))
    if not isinstance(installed, list) or not installed:
        raise YOLOContractError("Missing installed runtime file inventory")
    if len({b["path"] for b in installed}) != len(installed):
        raise YOLOContractError("Duplicate runtime file inventory")
    for item in installed:
        _root_path(root, item)
    import torch
    import torchvision
    if not torch.cuda.is_available() or not hasattr(torchvision.ops, "nms"):
        raise YOLOContractError("Approved CUDA/torchvision NMS runtime unavailable")
    device = runtime_record["device"]
    actual = {"name": torch.cuda.get_device_name(0), "cuda_runtime": torch.version.cuda,
              "cudnn": torch.backends.cudnn.version(), "torch": torch.__version__, "torchvision": torchvision.__version__}
    if actual != {key: device[key] for key in actual}:
        raise YOLOContractError("CUDA runtime/device changed")
    return validate_model_provenance(ModelProvenance(
        MODEL_NAME, "ultralytics", PACKAGE_VERSION, WEIGHTS_IDENTIFIER, WEIGHTS_SHA256,
        code_commit, f"cuda:0 | gpu={actual['name']}; torch={actual['torch']}; cuda_runtime={actual['cuda_runtime']}; cudnn={actual['cudnn']}",
        "float32", 640, 640, RESIZE_MODE, False, 37, "sports ball", .01, POSTPROCESSING))


def validate_prediction(result, model_provenance):
    """Validate saved per-crop evidence with no optional detector imports."""
    validate_model_provenance(model_provenance)
    _closed(result, {"candidates", "postprocessing", "forward_accounting"}, "prediction")
    post = _closed(result["postprocessing"], {"source_class_id", "returned_candidates", "exported_candidate_sources", "cap_saturated", "input_transform"}, "postprocessing")
    if type(post["source_class_id"]) is not int or post["source_class_id"] != 32 or post["input_transform"] != INPUT_TRANSFORM:
        raise YOLOContractError("Source class or input transform changed")
    rows = post["returned_candidates"]
    if not isinstance(rows, list) or len(rows) > 300 or type(post["cap_saturated"]) is not bool or post["cap_saturated"] != (len(rows) == 300):
        raise YOLOContractError("Invalid postprocessor count/cap evidence")
    accepted = []
    for i, row in enumerate(rows):
        _closed(row, {"postprocessor_index", "bbox_xyxy_px", "confidence", "source_class_id"}, "returned candidate")
        if type(row["postprocessor_index"]) is not int or row["postprocessor_index"] != i or type(row["source_class_id"]) is not int or row["source_class_id"] != 32:
            raise YOLOContractError("Wrong postprocessor order or source class")
        box = row["bbox_xyxy_px"]
        if not isinstance(box, list) or len(box) != 4:
            raise YOLOContractError("Wrong candidate box shape")
        x1, y1, x2, y2 = [_number(v, "bbox coordinate") for v in box]
        score = _number(row["confidence"], "confidence")
        if not (0 <= x1 <= x2 <= 1152 and 0 <= y1 <= y2 <= 648 and 0 <= score <= 1):
            raise YOLOContractError("Out-of-bounds/degenerate candidate or confidence")
        if score >= .01:
            # Vendor inverse-letterbox clipping can collapse a rejected native
            # row at the image edge. Preserve it below the floor; exported
            # candidates still require strictly positive width and height.
            if x1 == x2 or y1 == y2:
                raise YOLOContractError("Degenerate exported candidate at or above confidence floor")
            accepted.append((score, (x1, y1, x2, y2), i))
    accepted.sort(key=lambda x: (-x[0], x[1], x[2]))
    expected, sources = [], []
    for index, (score, box, native_index) in enumerate(accepted):
        x1, y1, x2, y2 = box
        expected.append(BallDetection(candidate_index=index, class_id=37, class_name="sports ball", confidence=score,
                                      bbox_xyxy_px=box, center_xy_px=((x1+x2)/2, (y1+y2)/2)).to_dict())
        sources.append({"candidate_index": index, "postprocessor_index": native_index})
    if (json.dumps(result["candidates"], sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True)
            or json.dumps(post["exported_candidate_sources"], sort_keys=True) != json.dumps(sources, sort_keys=True)):
        raise YOLOContractError("Candidate filtering, geometry, order or source-index mapping changed")
    account = _closed(result["forward_accounting"], {"synthetic_forwards", "project_attempts", "project_forwards", "this_project_attempt_forwards", "preparation_complete"}, "forward accounting")
    _integer(account["synthetic_forwards"], 1, "synthetic forward count")
    attempts = _integer(account["project_attempts"], 1, "project attempt count")
    count = _integer(account["project_forwards"], 1, "project forward count")
    if count > attempts or type(account["this_project_attempt_forwards"]) is not int or account["this_project_attempt_forwards"] != 1 or account["preparation_complete"] is not True:
        raise YOLOContractError("Project pixels require completed synthetic warmup and exactly one forward per attempt")
    return result


class _NMSWarnings(logging.Handler):
    def __init__(self):
        super().__init__()
        self.timeouts = []

    def emit(self, record):
        message = record.getMessage()
        if "nms" in message.lower() and "time limit" in message.lower():
            self.timeouts.append(message)


class YOLO11xAdapter:
    """A lazy fixed detector; only explicit prepare() may initialize/warm it."""
    def __init__(self, weights_path, runtime_record, code_commit, *, model_factory=None, runtime_inspector=None):
        self.weights_path = Path(weights_path).resolve()
        self.runtime_record = runtime_record
        self.code_commit = code_commit
        self._model_factory = model_factory
        self._runtime_inspector = runtime_inspector or inspect_runtime
        self._yolo = self._network = self._inference_network = self._predictor = None
        self._phase = None
        self._counts = {"synthetic_forwards": 0, "project_attempts": 0, "project_forwards": 0, "preparation_complete": False}
        self.provenance = None
        self._cuda_peak_allocated_bytes = None

    @property
    def accounting(self):
        return dict(self._counts)

    @property
    def cuda_peak_allocated_bytes(self):
        if self._cuda_peak_allocated_bytes is None:
            raise YOLOContractError("No measured project-crop CUDA peak is available")
        return self._cuda_peak_allocated_bytes

    def _forward(self, module, args):
        if self._phase == "synthetic":
            self._counts["synthetic_forwards"] += 1
        elif self._phase == "project":
            self._counts["project_forwards"] += 1
        else:
            raise YOLOContractError("Unattributed detector forward")

    def _verify_live(self):
        if self._yolo.task != "detect" or self._yolo.model is not self._network:
            raise YOLOContractError("Wrong/changed detector task or network")
        names = self._yolo.names
        if not isinstance(names, dict) or set(names) != set(range(80)) or names[32] != "sports ball" or list(names.values()).count("sports ball") != 1:
            raise YOLOContractError("YOLO contiguous class mapping changed")
        if self._predictor.model.model is not self._inference_network:
            raise YOLOContractError("Inference network changed")
        parameters = list(self._inference_network.parameters())
        if not parameters or any(str(p.dtype) != "torch.float32" or p.device.type != "cuda" or p.device.index != 0 for p in parameters):
            raise YOLOContractError("Model must use CUDA device0 float32 parameters")
        stride = self._inference_network.stride.tolist()
        if stride != [8.0, 16.0, 32.0] or getattr(self._inference_network, "end2end", False):
            raise YOLOContractError("Wrong detection head/stride")
        if self._predictor is not None:
            if self._yolo.predictor is not self._predictor or self._predictor.done_warmup is not True:
                raise YOLOContractError("Fresh/unwarmed predictor cannot see project pixels")
            # This frozen SDK maps deprecated half=False to quantize. Inspect
            # the canonical FP32 option and actual copied inference parameters.
            for key in ("imgsz", "rect", "quantize", "batch", "classes", "conf", "iou", "max_det", "agnostic_nms", "augment", "compile"):
                if getattr(self._predictor.args, key) != PREDICT_ARGS[key]:
                    raise YOLOContractError(f"Live predictor option changed: {key}")

    def _call(self, bgr):
        from ultralytics.utils import LOGGER
        capture = _NMSWarnings()
        LOGGER.addHandler(capture)
        try:
            result = self._yolo.predict(bgr, **PREDICT_ARGS)
        finally:
            LOGGER.removeHandler(capture)
        if capture.timeouts:
            raise YOLOContractError("NMS timed out; no checkpoint may be published")
        return result

    def prepare(self):
        if self._counts["preparation_complete"]:
            self._verify_live()
            return self.accounting
        if self._yolo is not None:
            raise YOLOContractError("Failed preparation requires a fresh adapter")
        self.provenance = self._runtime_inspector(self.weights_path, self.runtime_record, self.code_commit)
        import numpy as np
        import torch
        import torchvision  # Pin vendor NMS dispatch before model construction.
        if not hasattr(torchvision.ops, "nms"):
            raise YOLOContractError("torchvision NMS missing")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        factory = self._model_factory
        if factory is None:
            config = self.weights_path.parent / "config"
            (config / "Ultralytics").mkdir(parents=True, exist_ok=True)
            os.environ.update(YOLO_CONFIG_DIR=str(config), YOLO_OFFLINE="true", YOLO_AUTOINSTALL="false",
                              TORCH_HOME=str(self.weights_path.parent / "torch_cache"))
            if "ultralytics" in sys.modules:
                from ultralytics.utils import USER_CONFIG_DIR
                if Path(USER_CONFIG_DIR).resolve() != (config / "Ultralytics").resolve():
                    raise YOLOContractError("Ultralytics was imported outside the isolated configuration")
            from ultralytics import YOLO
            factory = YOLO
        self._yolo = factory(str(self.weights_path))
        self._network = self._yolo.model
        # Functions survive the SDK's model deepcopy; a bound method would
        # deepcopy this adapter (including the predictor's unpicklable lock).
        def count_forward(module, args):
            self._forward(module, args)
        self._hook = self._network.register_forward_pre_hook(count_forward)
        self._phase = "synthetic"
        try:
            self._call(np.zeros((648, 1152, 3), dtype=np.uint8))
            self._predictor = self._yolo.predictor
            self._inference_network = self._predictor.model.model
            self._verify_live()
            if self._counts["synthetic_forwards"] < 1 or self._counts["project_forwards"]:
                raise YOLOContractError("Synthetic preparation was not observed")
        finally:
            self._phase = None
        if _hash(self.weights_path) != WEIGHTS_SHA256:
            raise YOLOContractError("Weights changed during model preparation")
        self._counts["preparation_complete"] = True
        return self.accounting

    def predict_frame(self, frame_rgb):
        import numpy as np
        import torch
        if not self._counts["preparation_complete"]:
            raise YOLOContractError("Call prepare() on synthetic pixels before project inference")
        if not isinstance(frame_rgb, np.ndarray) or frame_rgb.dtype != np.uint8 or frame_rgb.shape != (648, 1152, 3):
            raise YOLOContractError("Expected one1152x648 uint8 RGB crop")
        self._verify_live()
        torch.cuda.synchronize(0)
        torch.cuda.reset_peak_memory_stats(0)
        self._counts["project_attempts"] += 1
        before = self._counts["project_forwards"]
        self._phase = "project"
        try:
            results = self._call(frame_rgb[:, :, ::-1].copy())
        finally:
            self._phase = None
            torch.cuda.synchronize(0)
            self._cuda_peak_allocated_bytes = int(torch.cuda.max_memory_allocated(0))
        delta = self._counts["project_forwards"] - before
        if delta != 1:
            raise YOLOContractError("Expected exactly one project forward, without implicit warmup")
        self._verify_live()
        if not isinstance(results, list) or len(results) != 1 or tuple(results[0].orig_shape) != (648, 1152):
            raise YOLOContractError("Unexpected batched or resized detector results")
        rows = results[0].boxes.data.detach().cpu().tolist()
        returned = []
        for i, row in enumerate(rows):
            if len(row) != 6 or row[5] != 32:
                raise YOLOContractError("Unexpected result columns or class")
            returned.append({"postprocessor_index": i, "bbox_xyxy_px": row[:4], "confidence": row[4], "source_class_id": 32})
        accepted = [(r["confidence"], tuple(r["bbox_xyxy_px"]), r["postprocessor_index"]) for r in returned if r["confidence"] >= .01]
        accepted.sort(key=lambda x: (-x[0], x[1], x[2]))
        candidates, sources = [], []
        for i, (score, box, native_index) in enumerate(accepted):
            x1, y1, x2, y2 = box
            candidates.append(BallDetection(candidate_index=i, class_id=37, class_name="sports ball", confidence=score,
                                            bbox_xyxy_px=box, center_xy_px=((x1+x2)/2, (y1+y2)/2)).to_dict())
            sources.append({"candidate_index": i, "postprocessor_index": native_index})
        result = {"candidates": candidates,
                  "postprocessing": {"source_class_id": 32, "returned_candidates": returned,
                                     "exported_candidate_sources": sources, "cap_saturated": len(rows) == 300,
                                     "input_transform": dict(INPUT_TRANSFORM)},
                  "forward_accounting": {**self.accounting, "this_project_attempt_forwards": delta}}
        return validate_prediction(result, self.provenance)

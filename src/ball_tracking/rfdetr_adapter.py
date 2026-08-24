"""Strict image-only RF-DETR adapter for raw basketball candidates.

The adapter deliberately stops at per-frame detector evidence.  It performs no
tracking, temporal selection, court filtering, region-of-interest filtering,
non-maximum suppression, or one-ball post-selection.

Heavy dependencies and model construction are lazy so schema, review, and unit
test commands can import this module on CPU-only machines.
"""

from __future__ import annotations

import hashlib
import math
import operator
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .detections import BallDetection


MODEL_NAME = "RF-DETR Medium COCO"
PACKAGE_NAME = "rfdetr"
PACKAGE_VERSION = "1.9.1"
WEIGHTS_IDENTIFIER = "rf-detr-medium.pth"
WEIGHTS_SHA256 = (
    "749ff6071828aaffac63e204c4f4135ed3d6cdae4d702e086c360edc3b5768c8"
)

DEVICE = "cuda"
PRECISION = "float32"
INPUT_WIDTH_PX = 576
INPUT_HEIGHT_PX = 576
RESIZE_MODE = (
    "direct RGB bilinear resize to 576x576 without letterboxing or padding; "
    "antialias disabled; ImageNet channel normalization"
)
TILING_ENABLED = False

MODEL_QUERY_COUNT = 300
MODEL_LOGIT_SLOT_COUNT = 91
NUM_SELECT = MODEL_QUERY_COUNT * MODEL_LOGIT_SLOT_COUNT
PREDICT_THRESHOLD = 0.0
MIN_EXPORT_CONFIDENCE_FLOOR = 0.01

TARGET_CLASS_ID = 37
TARGET_CLASS_NAME = "sports ball"
TARGET_CLASS_NAME_INDEX = 32

POSTPROCESSING_DESCRIPTION = (
    "RF-DETR sigmoid scores with all 300 query x 91 logit pairs selected "
    "(num_select=27300); source-pixel box scaling and clipping; raw COCO "
    "class ID 37/name 'sports ball' filtering; adapter-side inclusive "
    "confidence-floor filtering; deterministic ordering; no NMS, ROI/court "
    "filter, tiling, temporal logic, deduplication, or top-one selection"
)


class RFDETRAdapterError(ValueError):
    """Raised when the RF-DETR adapter contract is violated."""


class RFDETRModelContractError(RFDETRAdapterError):
    """Raised when the loaded model differs from the frozen baseline."""


class RFDETRCandidateError(RFDETRAdapterError):
    """Raised when detector candidate arrays are malformed or inconsistent."""


def _require_positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise RFDETRCandidateError(f"{label} must be a positive integer")

    try:
        result = operator.index(value)
    except TypeError as error:
        raise RFDETRCandidateError(
            f"{label} must be a positive integer"
        ) from error

    if result <= 0:
        raise RFDETRCandidateError(f"{label} must be a positive integer")

    return result


def _require_nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise RFDETRCandidateError(f"{label} must be a nonnegative integer")

    try:
        result = operator.index(value)
    except TypeError as error:
        raise RFDETRCandidateError(
            f"{label} must be a nonnegative integer"
        ) from error

    if result < 0:
        raise RFDETRCandidateError(
            f"{label} must be a nonnegative integer"
        )

    return result


def _require_finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or isinstance(value, (str, bytes)):
        raise RFDETRCandidateError(f"{label} must be a finite number")

    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RFDETRCandidateError(
            f"{label} must be a finite number"
        ) from error

    if not math.isfinite(result):
        raise RFDETRCandidateError(f"{label} must be a finite number")

    return result


def _require_confidence(value: Any, label: str) -> float:
    confidence = _require_finite_number(value, label)

    if not 0.0 <= confidence <= 1.0:
        raise RFDETRCandidateError(f"{label} must be in [0, 1]")

    return confidence


def validate_export_confidence_floor(value: Any) -> float:
    """Validate the exact inclusive raw-candidate export floor."""

    floor = _require_confidence(value, "export_confidence_floor")

    if floor != MIN_EXPORT_CONFIDENCE_FLOOR:
        raise RFDETRCandidateError(
            "export_confidence_floor must equal the frozen baseline value "
            f"{MIN_EXPORT_CONFIDENCE_FLOOR}"
        )

    return floor


def _validate_exact_weights_path(value: Any, label: str) -> Path:
    if not isinstance(value, Path):
        raise RFDETRModelContractError(f"{label} must be a pathlib.Path")

    if not value.is_absolute():
        raise RFDETRModelContractError(f"{label} must be absolute")

    resolved = value.resolve()

    if value != resolved:
        raise RFDETRModelContractError(
            f"{label} must already be fully resolved; received {value!s}"
        )

    if resolved.name != WEIGHTS_IDENTIFIER:
        raise RFDETRModelContractError(
            f"{label} must name {WEIGHTS_IDENTIFIER!r}; received {resolved!s}"
        )

    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _as_sequence(value: Any, label: str) -> list[Any]:
    if value is None or isinstance(value, (str, bytes, Mapping)):
        raise RFDETRCandidateError(f"{label} must be an array")

    try:
        return list(value)
    except TypeError as error:
        raise RFDETRCandidateError(f"{label} must be an array") from error


def _read_detection_field(detections: Any, field: str) -> Any:
    try:
        value = getattr(detections, field)
    except Exception as error:
        raise RFDETRCandidateError(
            f"RF-DETR detections are missing {field!r}"
        ) from error

    if value is None:
        raise RFDETRCandidateError(
            f"RF-DETR detections are missing {field!r}"
        )

    return value


def _read_class_names(detections: Any) -> Any:
    data = _read_detection_field(detections, "data")

    if not isinstance(data, Mapping):
        raise RFDETRCandidateError("RF-DETR detections.data must be a mapping")

    if "class_name" not in data:
        raise RFDETRCandidateError(
            "RF-DETR detections.data is missing 'class_name'"
        )

    return data["class_name"]


def _validate_parallel_lengths(
    boxes: Sequence[Any],
    confidences: Sequence[Any],
    class_ids: Sequence[Any],
    class_names: Sequence[Any],
) -> None:
    lengths = {
        "xyxy": len(boxes),
        "confidence": len(confidences),
        "class_id": len(class_ids),
        "class_name": len(class_names),
    }

    if len(set(lengths.values())) != 1:
        raise RFDETRCandidateError(
            "RF-DETR candidate arrays must have identical lengths: "
            + ", ".join(
                f"{name}={length}" for name, length in lengths.items()
            )
        )


def adapt_rfdetr_candidates(
    detections: Any,
    *,
    source_width_px: Any,
    source_height_px: Any,
    export_confidence_floor: Any = MIN_EXPORT_CONFIDENCE_FLOOR,
) -> tuple[BallDetection, ...]:
    """Convert one RF-DETR result into strict, source-pixel ball candidates.

    Structural and numeric validation is performed before target-class and
    confidence filtering.  Persisted boxes are clipped to source bounds, and
    any target candidate that becomes degenerate after clipping is rejected.
    Duplicate candidates are intentionally retained.
    """

    width = _require_positive_integer(source_width_px, "source_width_px")
    height = _require_positive_integer(source_height_px, "source_height_px")
    floor = validate_export_confidence_floor(export_confidence_floor)
    boxes = _as_sequence(
        _read_detection_field(detections, "xyxy"),
        "detections.xyxy",
    )
    confidences = _as_sequence(
        _read_detection_field(detections, "confidence"),
        "detections.confidence",
    )
    class_ids = _as_sequence(
        _read_detection_field(detections, "class_id"),
        "detections.class_id",
    )
    class_names = _as_sequence(
        _read_class_names(detections),
        "detections.data['class_name']",
    )
    _validate_parallel_lengths(boxes, confidences, class_ids, class_names)
    retained: list[
        tuple[
            float,
            tuple[float, float, float, float],
            int,
        ]
    ] = []

    for original_position, (
        raw_box,
        raw_confidence,
        raw_class_id,
        raw_class_name,
    ) in enumerate(zip(boxes, confidences, class_ids, class_names)):
        label = f"RF-DETR candidate {original_position}"
        box_values = _as_sequence(raw_box, f"{label}.xyxy")

        if len(box_values) != 4:
            raise RFDETRCandidateError(
                f"{label}.xyxy must contain exactly four coordinates"
            )

        x1, y1, x2, y2 = (
            _require_finite_number(
                coordinate,
                f"{label}.xyxy[{coordinate_index}]",
            )
            for coordinate_index, coordinate in enumerate(box_values)
        )
        confidence = _require_confidence(
            raw_confidence,
            f"{label}.confidence",
        )
        class_id = _require_nonnegative_integer(
            raw_class_id,
            f"{label}.class_id",
        )

        if not isinstance(raw_class_name, str):
            raise RFDETRCandidateError(
                f"{label}.class_name must be a string"
            )

        is_target_id = class_id == TARGET_CLASS_ID
        is_target_name = raw_class_name == TARGET_CLASS_NAME

        if is_target_id != is_target_name:
            raise RFDETRCandidateError(
                f"{label} has inconsistent target class ID/name: "
                f"{class_id!r}/{raw_class_name!r}; expected "
                f"{TARGET_CLASS_ID!r}/{TARGET_CLASS_NAME!r}"
            )

        if not is_target_id or confidence < floor:
            continue

        clipped_box = (
            min(max(x1, 0.0), float(width)),
            min(max(y1, 0.0), float(height)),
            min(max(x2, 0.0), float(width)),
            min(max(y2, 0.0), float(height)),
        )
        clipped_x1, clipped_y1, clipped_x2, clipped_y2 = clipped_box

        if clipped_x1 >= clipped_x2 or clipped_y1 >= clipped_y2:
            raise RFDETRCandidateError(
                f"{label}.xyxy is degenerate after source-bound clipping: "
                f"{clipped_box!r}"
            )

        retained.append((confidence, clipped_box, original_position))

    retained.sort(
        key=lambda candidate: (
            -candidate[0],
            candidate[1][0],
            candidate[1][1],
            candidate[1][2],
            candidate[1][3],
            candidate[2],
        )
    )
    adapted = []

    for candidate_index, (confidence, box, _original_position) in enumerate(
        retained
    ):
        x1, y1, x2, y2 = box
        adapted.append(
            BallDetection(
                candidate_index=candidate_index,
                class_id=TARGET_CLASS_ID,
                class_name=TARGET_CLASS_NAME,
                confidence=confidence,
                bbox_xyxy_px=box,
                center_xy_px=((x1 + x2) / 2.0, (y1 + y2) / 2.0),
            )
        )

    return tuple(adapted)


def validate_coco_class_mapping(
    category_id_to_name: Any,
    class_names: Any,
) -> None:
    """Verify the package's sparse COCO ID/name mapping without inference."""

    if not isinstance(category_id_to_name, Mapping):
        raise RFDETRModelContractError(
            "COCO_CLASSES must be a category-ID-to-name mapping"
        )

    if class_names is None or isinstance(class_names, (str, bytes, Mapping)):
        raise RFDETRModelContractError("COCO_CLASS_NAMES must be an array")

    try:
        names = list(class_names)
    except TypeError as error:
        raise RFDETRModelContractError(
            "COCO_CLASS_NAMES must be an array"
        ) from error

    entries: list[tuple[int, str]] = []

    for raw_category_id, raw_class_name in category_id_to_name.items():
        if isinstance(raw_category_id, bool):
            raise RFDETRModelContractError(
                "COCO_CLASSES category IDs must be positive integers"
            )

        try:
            category_id = operator.index(raw_category_id)
        except TypeError as error:
            raise RFDETRModelContractError(
                "COCO_CLASSES category IDs must be positive integers"
            ) from error

        if category_id <= 0:
            raise RFDETRModelContractError(
                "COCO_CLASSES category IDs must be positive integers"
            )

        if not isinstance(raw_class_name, str) or not raw_class_name:
            raise RFDETRModelContractError(
                "COCO_CLASSES class names must be nonempty strings"
            )

        entries.append((category_id, raw_class_name))

    entries.sort(key=lambda item: item[0])
    ids = [category_id for category_id, _class_name in entries]
    mapped_names = [class_name for _category_id, class_name in entries]

    if len(ids) != len(names):
        raise RFDETRModelContractError(
            "COCO category IDs and class names must have identical lengths"
        )

    if mapped_names != names:
        raise RFDETRModelContractError(
            "COCO_CLASS_NAMES must exactly match COCO_CLASSES in sorted "
            "category-ID order"
        )

    if len(names) <= TARGET_CLASS_NAME_INDEX:
        raise RFDETRModelContractError(
            "COCO class mapping does not include the sports-ball name index"
        )

    category_id = ids[TARGET_CLASS_NAME_INDEX]
    class_name = names[TARGET_CLASS_NAME_INDEX]

    if category_id != TARGET_CLASS_ID or class_name != TARGET_CLASS_NAME:
        raise RFDETRModelContractError(
            "COCO sports-ball mapping changed: expected list position "
            f"{TARGET_CLASS_NAME_INDEX} to be "
            f"{TARGET_CLASS_ID!r}/{TARGET_CLASS_NAME!r}, received "
            f"{category_id!r}/{class_name!r}"
        )

    target_positions = [
        index for index, name in enumerate(names) if name == TARGET_CLASS_NAME
    ]
    target_ids = [
        category_id
        for category_id, name in entries
        if name == TARGET_CLASS_NAME
    ]

    if (
        target_positions != [TARGET_CLASS_NAME_INDEX]
        or target_ids != [TARGET_CLASS_ID]
    ):
        raise RFDETRModelContractError(
            "COCO mappings must contain exactly one sports-ball entry at "
            "raw category ID 37 and sorted name position 32"
        )


def _read_model_attribute(value: Any, attribute: str, label: str) -> Any:
    try:
        return getattr(value, attribute)
    except Exception as error:
        raise RFDETRModelContractError(
            f"loaded RF-DETR model is missing {label}"
        ) from error


def _require_model_value(
    actual: Any,
    expected: Any,
    label: str,
) -> None:
    if actual != expected:
        raise RFDETRModelContractError(
            f"loaded RF-DETR {label} must be {expected!r}; "
            f"received {actual!r}"
        )


def validate_loaded_model(model: Any, expected_weights_path: Path) -> None:
    """Verify a loaded model against the frozen, unoptimized CUDA baseline."""

    expected_path = _validate_exact_weights_path(
        expected_weights_path,
        "expected_weights_path",
    )

    _require_model_value(
        _read_model_attribute(model, "size", "variant size"),
        "rfdetr-medium",
        "variant size",
    )
    model_config = _read_model_attribute(
        model,
        "model_config",
        "model_config",
    )

    for attribute, expected in (
        ("resolution", INPUT_HEIGHT_PX),
        ("device", DEVICE),
        ("num_queries", MODEL_QUERY_COUNT),
        ("num_classes", MODEL_LOGIT_SLOT_COUNT - 1),
        ("num_select", NUM_SELECT),
    ):
        _require_model_value(
            _read_model_attribute(
                model_config,
                attribute,
                f"model_config.{attribute}",
            ),
            expected,
            f"model_config.{attribute}",
        )

    pretrain_weights = _read_model_attribute(
        model_config,
        "pretrain_weights",
        "model_config.pretrain_weights",
    )

    try:
        loaded_weights_path = Path(str(pretrain_weights))
    except (TypeError, ValueError, OSError) as error:
        raise RFDETRModelContractError(
            "loaded RF-DETR model_config.pretrain_weights must be a valid path"
        ) from error

    if not loaded_weights_path.is_absolute():
        raise RFDETRModelContractError(
            "loaded RF-DETR model_config.pretrain_weights must be absolute; "
            f"received {pretrain_weights!r}"
        )

    loaded_weights_path = loaded_weights_path.resolve()

    if loaded_weights_path != expected_path:
        raise RFDETRModelContractError(
            "loaded RF-DETR model_config.pretrain_weights must equal the exact "
            f"preflight-verified path {expected_path!s}; received "
            f"{loaded_weights_path!s}"
        )

    _require_model_value(
        _read_model_attribute(
            model,
            "_is_optimized_for_inference",
            "optimization state",
        ),
        False,
        "optimization state",
    )
    model_context = _read_model_attribute(model, "model", "model context")
    context_device = str(
        _read_model_attribute(model_context, "device", "model.device")
    )

    if context_device != DEVICE and not context_device.startswith(f"{DEVICE}:"):
        raise RFDETRModelContractError(
            "loaded RF-DETR model.device must be CUDA; "
            f"received {context_device!r}"
        )

    _require_model_value(
        _read_model_attribute(model_context, "resolution", "model.resolution"),
        INPUT_HEIGHT_PX,
        "model.resolution",
    )
    postprocess = _read_model_attribute(
        model_context,
        "postprocess",
        "model.postprocess",
    )
    _require_model_value(
        _read_model_attribute(
            postprocess,
            "num_select",
            "model.postprocess.num_select",
        ),
        NUM_SELECT,
        "model.postprocess.num_select",
    )
    live_model = _read_model_attribute(
        model_context,
        "model",
        "model.model",
    )
    _require_model_value(
        _read_model_attribute(
            live_model,
            "num_queries",
            "model.model.num_queries",
        ),
        MODEL_QUERY_COUNT,
        "model.model.num_queries",
    )
    class_embed = _read_model_attribute(
        live_model,
        "class_embed",
        "model.model.class_embed",
    )
    _require_model_value(
        _read_model_attribute(
            class_embed,
            "out_features",
            "model.model.class_embed.out_features",
        ),
        MODEL_LOGIT_SLOT_COUNT,
        "model.model.class_embed.out_features",
    )
    model_args = _read_model_attribute(model_context, "args", "model.args")
    _require_model_value(
        _read_model_attribute(
            model_args,
            "num_classes",
            "model.args.num_classes",
        ),
        MODEL_LOGIT_SLOT_COUNT - 1,
        "model.args.num_classes",
    )
    class_names = _as_sequence(
        _read_model_attribute(model, "class_names", "class_names"),
        "loaded RF-DETR class_names",
    )

    if len(class_names) != 80:
        raise RFDETRModelContractError(
            "loaded RF-DETR class_names must contain exactly 80 COCO names; "
            f"received {len(class_names)}"
        )

    _require_model_value(
        class_names[TARGET_CLASS_NAME_INDEX],
        TARGET_CLASS_NAME,
        f"class_names[{TARGET_CLASS_NAME_INDEX}]",
    )

    if class_names.count(TARGET_CLASS_NAME) != 1:
        raise RFDETRModelContractError(
            "loaded RF-DETR class_names must contain exactly one sports-ball "
            "entry"
        )
    parameters = _read_model_attribute(
        live_model,
        "parameters",
        "model.model.parameters",
    )

    if not callable(parameters):
        raise RFDETRModelContractError(
            "loaded RF-DETR model.model.parameters must be callable"
        )

    try:
        parameter_list = list(parameters())
    except Exception as error:
        raise RFDETRModelContractError(
            "could not inspect loaded RF-DETR parameter precision"
        ) from error

    if not parameter_list:
        raise RFDETRModelContractError(
            "loaded RF-DETR model has no parameters to inspect"
        )

    parameter_dtypes = {
        str(_read_model_attribute(parameter, "dtype", "parameter dtype"))
        for parameter in parameter_list
    }

    if parameter_dtypes != {"torch.float32"}:
        raise RFDETRModelContractError(
            "loaded RF-DETR parameters must all use torch.float32; "
            f"received {sorted(parameter_dtypes)!r}"
        )


class RFDETRBallAdapter:
    """Lazily run the frozen RF-DETR baseline on one RGB frame at a time."""

    def __init__(
        self,
        *,
        weights_path: Path,
        export_confidence_floor: Any = MIN_EXPORT_CONFIDENCE_FLOOR,
        model_factory: Callable[[Path], Any] | None = None,
        weights_hasher: Callable[[Path], str] | None = None,
    ) -> None:
        self.weights_path = _validate_exact_weights_path(
            weights_path,
            "weights_path",
        )
        self.export_confidence_floor = validate_export_confidence_floor(
            export_confidence_floor
        )
        if weights_hasher is not None and not callable(weights_hasher):
            raise RFDETRModelContractError("weights_hasher must be callable")
        self._model_factory = model_factory
        self._weights_hasher = (
            _sha256_file if weights_hasher is None else weights_hasher
        )
        self._model: Any | None = None

    def _verify_weights_hash(self, phase: str) -> str:
        try:
            actual_sha256 = self._weights_hasher(self.weights_path)
        except Exception as error:
            raise RFDETRModelContractError(
                f"could not hash frozen weights {phase} model construction: "
                f"{self.weights_path!s}: {error}"
            ) from error

        if actual_sha256 != WEIGHTS_SHA256:
            raise RFDETRModelContractError(
                f"frozen weights SHA-256 mismatch {phase} model construction: "
                f"expected {WEIGHTS_SHA256}, received {actual_sha256!r}"
            )

        return actual_sha256

    def _construct_model(self) -> Any:
        before_sha256 = self._verify_weights_hash("before")

        if self._model_factory is not None:
            model = self._model_factory(self.weights_path)
        else:
            from importlib.metadata import version

            installed_version = version(PACKAGE_NAME)

            if installed_version != PACKAGE_VERSION:
                raise RFDETRModelContractError(
                    f"installed {PACKAGE_NAME} version must be "
                    f"{PACKAGE_VERSION!r}; received {installed_version!r}"
                )

            from rfdetr import RFDETRMedium
            from rfdetr.assets.coco_classes import (
                COCO_CLASSES,
                COCO_CLASS_NAMES,
            )

            validate_coco_class_mapping(COCO_CLASSES, COCO_CLASS_NAMES)
            model = RFDETRMedium(
                device=DEVICE,
                resolution=INPUT_HEIGHT_PX,
                num_select=NUM_SELECT,
                pretrain_weights=str(self.weights_path),
            )

        after_sha256 = self._verify_weights_hash("after")

        if after_sha256 != before_sha256:
            raise RFDETRModelContractError(
                "frozen weights changed during model construction"
            )

        validate_loaded_model(model, self.weights_path)
        return model

    def _get_model(self) -> Any:
        if self._model is None:
            self._model = self._construct_model()

        return self._model

    def predict_frame(self, frame_rgb: Any) -> tuple[BallDetection, ...]:
        """Predict and adapt candidates for exactly one RGB uint8 frame."""

        import numpy as np

        if not isinstance(frame_rgb, np.ndarray):
            raise RFDETRAdapterError("frame_rgb must be one NumPy RGB frame")

        if frame_rgb.ndim != 3 or frame_rgb.shape[2] != 3:
            raise RFDETRAdapterError(
                "frame_rgb must have shape (height, width, 3), not a batch"
            )

        if frame_rgb.dtype != np.uint8:
            raise RFDETRAdapterError("frame_rgb must use uint8 RGB pixels")

        source_height_px = int(frame_rgb.shape[0])
        source_width_px = int(frame_rgb.shape[1])

        if source_width_px <= 0 or source_height_px <= 0:
            raise RFDETRAdapterError("frame_rgb dimensions must be positive")

        model = self._get_model()
        detections = model.predict(
            frame_rgb,
            threshold=PREDICT_THRESHOLD,
            shape=(INPUT_HEIGHT_PX, INPUT_WIDTH_PX),
            include_source_image=False,
        )

        if isinstance(detections, (list, tuple)):
            raise RFDETRCandidateError(
                "single-frame RF-DETR prediction returned batched results"
            )

        return adapt_rfdetr_candidates(
            detections,
            source_width_px=source_width_px,
            source_height_px=source_height_px,
            export_confidence_floor=self.export_confidence_floor,
        )


__all__ = [
    "DEVICE",
    "INPUT_HEIGHT_PX",
    "INPUT_WIDTH_PX",
    "MIN_EXPORT_CONFIDENCE_FLOOR",
    "MODEL_LOGIT_SLOT_COUNT",
    "MODEL_NAME",
    "MODEL_QUERY_COUNT",
    "NUM_SELECT",
    "PACKAGE_NAME",
    "PACKAGE_VERSION",
    "POSTPROCESSING_DESCRIPTION",
    "PRECISION",
    "PREDICT_THRESHOLD",
    "RESIZE_MODE",
    "RFDETRAdapterError",
    "RFDETRBallAdapter",
    "RFDETRCandidateError",
    "RFDETRModelContractError",
    "TARGET_CLASS_ID",
    "TARGET_CLASS_NAME",
    "TARGET_CLASS_NAME_INDEX",
    "TILING_ENABLED",
    "WEIGHTS_IDENTIFIER",
    "WEIGHTS_SHA256",
    "adapt_rfdetr_candidates",
    "validate_coco_class_mapping",
    "validate_export_confidence_floor",
    "validate_loaded_model",
]

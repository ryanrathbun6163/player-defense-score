"""Resumable, prediction-blind desktop editor for ball annotations.

The GUI is intentionally a thin layer over pure validation helpers.  Every
saved frame is rebuilt into the complete :class:`BallAnnotationSet` and
validated before an atomic file replacement, so a bad form value cannot leave
the draft JSON half-written.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Sequence

from src.ball_tracking.annotations import (
    ABSENCE_REASONS,
    ANNOTATION_STATUSES,
    DIFFICULTY_TAGS,
    IDENTITY_CERTAINTIES,
    VISIBILITY_STATES,
    AnnotationValidationError,
    BallAnnotationSet,
    FrameAnnotation,
    SourceVideo,
    load_annotations,
    verify_source_video,
)


class AnnotationEditorError(RuntimeError):
    """Raised when an annotation editing session cannot safely proceed."""


class FormValidationError(ValueError):
    """Raised when a form value cannot be converted to schema v0.1."""


@dataclass(frozen=True)
class DisplayTransform:
    """Location and size of a source frame displayed on a canvas."""

    origin_x: float
    origin_y: float
    display_width: float
    display_height: float
    source_width: int
    source_height: int


@dataclass(frozen=True)
class FrameFormValues:
    """GUI-independent representation of all editable per-frame fields."""

    annotation_status: str
    visibility: str | None = None
    absence_reason: str | None = None
    identity_certainty: str | None = None
    has_geometry: bool = False
    center_x: str | float | int | None = None
    center_y: str | float | int | None = None
    uncertainty_radius_px: str | float | int | None = None
    localization_eligible: bool = False
    difficulty_tags: tuple[str, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class AnnotationSession:
    """Verified inputs needed by the desktop editor."""

    annotation_path: Path
    repository_root: Path
    source_path: Path
    annotation_set: BallAnnotationSet


def fit_source_to_viewport(
    source_width: int,
    source_height: int,
    viewport_width: int,
    viewport_height: int,
) -> DisplayTransform:
    """Return an aspect-preserving, centered source-to-canvas transform."""

    dimensions = (
        source_width,
        source_height,
        viewport_width,
        viewport_height,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in dimensions
    ):
        raise ValueError("source and viewport dimensions must be integers")
    if any(value <= 0 for value in dimensions):
        raise ValueError("source and viewport dimensions must be positive")

    scale = min(
        viewport_width / source_width,
        viewport_height / source_height,
    )
    # Pillow receives integer resize dimensions.  Store those exact integers
    # in the transform so click mapping matches the pixels actually displayed.
    display_width = max(1, round(source_width * scale))
    display_height = max(1, round(source_height * scale))
    return DisplayTransform(
        origin_x=(viewport_width - display_width) / 2.0,
        origin_y=(viewport_height - display_height) / 2.0,
        display_width=display_width,
        display_height=display_height,
        source_width=source_width,
        source_height=source_height,
    )


def map_canvas_to_source(
    canvas_x: float,
    canvas_y: float,
    transform: DisplayTransform,
) -> tuple[float, float]:
    """Map an in-image canvas click to original source-pixel coordinates.

    The right and bottom edges are exclusive, matching the annotation schema's
    ``0 <= x < width`` and ``0 <= y < height`` rules.  Clicks in letterboxing
    are rejected instead of being silently clamped onto the image.
    """

    values = (canvas_x, canvas_y)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        for value in values
    ):
        raise FormValidationError("canvas coordinates must be finite numbers")

    relative_x = float(canvas_x) - transform.origin_x
    relative_y = float(canvas_y) - transform.origin_y
    if not (
        0.0 <= relative_x < transform.display_width
        and 0.0 <= relative_y < transform.display_height
    ):
        raise FormValidationError("cursor is outside the displayed source frame")

    return (
        relative_x * transform.source_width / transform.display_width,
        relative_y * transform.source_height / transform.display_height,
    )


def map_source_to_canvas(
    source_x: float,
    source_y: float,
    transform: DisplayTransform,
) -> tuple[float, float]:
    """Map a validated source-pixel point to the displayed canvas frame."""

    if not (
        0.0 <= source_x < transform.source_width
        and 0.0 <= source_y < transform.source_height
    ):
        raise FormValidationError("source point is outside the source frame")
    return (
        transform.origin_x
        + source_x * transform.display_width / transform.source_width,
        transform.origin_y
        + source_y * transform.display_height / transform.source_height,
    )


def uncertainty_radius_from_boundary(
    center_x: float,
    center_y: float,
    boundary_x: float,
    boundary_y: float,
) -> float:
    """Measure a source-pixel uncertainty radius from a visual boundary."""

    values = (center_x, center_y, boundary_x, boundary_y)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        for value in values
    ):
        raise FormValidationError(
            "center and uncertainty-boundary coordinates must be finite"
        )
    radius = math.hypot(boundary_x - center_x, boundary_y - center_y)
    if radius <= 0.0:
        raise FormValidationError(
            "uncertainty boundary must differ from the selected center"
        )
    return radius


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_required_number(
    value: str | float | int | None,
    label: str,
) -> float:
    if isinstance(value, bool) or value is None:
        raise FormValidationError(f"{label} is required")
    if isinstance(value, str) and not value.strip():
        raise FormValidationError(f"{label} is required")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise FormValidationError(f"{label} must be a number") from error
    if not math.isfinite(parsed):
        raise FormValidationError(f"{label} must be finite")
    return parsed


def normalize_form_values(form: FrameFormValues) -> FrameFormValues:
    """Clear values that are incompatible with the chosen workflow state.

    This is the same deterministic transition used by the GUI when status or
    visibility changes.  It prevents an old point from surviving after a user
    changes a frame to ``not_visible``, for example.
    """

    status = form.annotation_status
    if status in {"unlabeled", "excluded"}:
        return replace(
            form,
            visibility=None,
            absence_reason=None,
            identity_certainty=None,
            has_geometry=False,
            center_x=None,
            center_y=None,
            uncertainty_radius_px=None,
            localization_eligible=False,
            difficulty_tags=(),
        )

    if status != "labeled":
        return form

    visibility = form.visibility
    normalized = form
    if visibility == "not_visible":
        normalized = replace(
            normalized,
            has_geometry=False,
            center_x=None,
            center_y=None,
            uncertainty_radius_px=None,
            localization_eligible=False,
        )
    elif visibility == "indeterminate":
        normalized = replace(
            normalized,
            absence_reason=None,
            identity_certainty="ambiguous",
            has_geometry=False,
            center_x=None,
            center_y=None,
            uncertainty_radius_px=None,
            localization_eligible=False,
        )
    else:
        normalized = replace(normalized, absence_reason=None)

    if not normalized.has_geometry:
        normalized = replace(
            normalized,
            center_x=None,
            center_y=None,
            uncertainty_radius_px=None,
            localization_eligible=False,
        )
    if normalized.identity_certainty == "ambiguous":
        normalized = replace(normalized, localization_eligible=False)
    return normalized


def form_to_annotation_row(
    frame_index: int,
    form: FrameFormValues,
    source_video: SourceVideo,
) -> dict[str, Any]:
    """Convert form state to one strictly validated annotation row."""

    normalized = normalize_form_values(form)
    geometry = None
    if normalized.has_geometry:
        if normalized.visibility not in {"fully_visible", "partially_visible"}:
            raise FormValidationError(
                "geometry requires fully_visible or partially_visible"
            )
        center_x = _parse_required_number(normalized.center_x, "center x")
        center_y = _parse_required_number(normalized.center_y, "center y")
        uncertainty = _parse_required_number(
            normalized.uncertainty_radius_px,
            "uncertainty radius",
        )
        geometry = {
            "center_xy_px": [center_x, center_y],
            "source": (
                "observed_complete_ball_center"
                if normalized.visibility == "fully_visible"
                else "human_amodal_estimate"
            ),
            "uncertainty_radius_px": uncertainty,
        }

    row = {
        "frame_index": frame_index,
        "annotation_status": normalized.annotation_status,
        "visibility": normalized.visibility,
        "absence_reason": normalized.absence_reason,
        "game_ball_identity_certainty": normalized.identity_certainty,
        "geometry": geometry,
        "localization_eligible": normalized.localization_eligible,
        "difficulty_tags": sorted(set(normalized.difficulty_tags)),
        "notes": _optional_text(normalized.notes),
    }
    return FrameAnnotation.from_mapping(row, 0, source_video).to_dict()


def build_updated_payload(
    annotation_set: BallAnnotationSet,
    frame_row: dict[str, Any],
) -> dict[str, Any]:
    """Build and validate the complete payload containing one edited row."""

    if annotation_set.review.status != "draft":
        raise AnnotationEditorError("reviewed annotation sets are read-only")
    frame_index = frame_row.get("frame_index")
    payload = copy.deepcopy(annotation_set.to_dict())
    matching_indices = [
        index
        for index, row in enumerate(payload["annotations"])
        if row["frame_index"] == frame_index
    ]
    if len(matching_indices) != 1:
        raise FormValidationError(
            f"frame {frame_index!r} is not exactly once in the annotation window"
        )
    payload["annotations"][matching_indices[0]] = copy.deepcopy(frame_row)

    # Parsing the whole object is deliberate: exact frame coverage, top-level
    # metadata, review state, and every untouched row are checked before save.
    return BallAnnotationSet.from_mapping(payload).to_dict()


def atomic_save_frame(
    annotation_path: Path,
    annotation_set: BallAnnotationSet,
    frame_row: dict[str, Any],
) -> BallAnnotationSet:
    """Validate and atomically replace a draft after one completed frame."""

    path = annotation_path.resolve()
    if not path.is_file():
        raise AnnotationEditorError(f"annotation JSON does not exist: {path}")

    # Editors can remain open while another editor or review process updates
    # the same draft.  Re-read immediately before creating a temporary file so
    # this session cannot silently replace newer validated content.
    try:
        current_on_disk = load_annotations(path)
    except (FileNotFoundError, AnnotationValidationError) as error:
        raise AnnotationEditorError(
            "annotation file changed on disk or is no longer readable; "
            "nothing was written"
        ) from error
    if current_on_disk.to_dict() != annotation_set.to_dict():
        raise AnnotationEditorError(
            "annotation file changed on disk since this editor loaded it; "
            "nothing was written. Reload the editor before continuing"
        )

    payload = build_updated_payload(annotation_set, frame_row)
    updated = BallAnnotationSet.from_mapping(payload)
    serialized = json.dumps(
        updated.to_dict(),
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return updated


def _resolve_source_path(
    annotation_set: BallAnnotationSet,
    repository_root: Path,
) -> Path:
    root = repository_root.resolve()
    source_path = root.joinpath(*annotation_set.source_video.path.parts).resolve()
    try:
        source_path.relative_to(root)
    except ValueError as error:
        raise AnnotationEditorError(
            "resolved source-video path escapes the repository root"
        ) from error
    return source_path


def prepare_annotation_session(
    annotation_path: Path,
    repository_root: Path,
) -> AnnotationSession:
    """Strictly load a draft and verify its source before opening any GUI."""

    path = annotation_path.resolve()
    root = repository_root.resolve()
    annotation_set = load_annotations(path)
    if annotation_set.review.status != "draft":
        raise AnnotationEditorError(
            "reviewed annotation sets are read-only; create a new draft to edit"
        )
    verify_source_video(annotation_set, root)
    source_path = _resolve_source_path(annotation_set, root)
    return AnnotationSession(path, root, source_path, annotation_set)


def decode_exact_window_frames(session: AnnotationSession) -> tuple[Any, ...]:
    """Decode from frame zero sequentially and return only the exact window."""

    try:
        import cv2
        from PIL import Image
    except ImportError as error:
        raise AnnotationEditorError(
            "OpenCV and Pillow are required by the annotation editor"
        ) from error

    capture = cv2.VideoCapture(str(session.source_path))
    if not capture.isOpened():
        raise AnnotationEditorError(
            f"could not open verified source video: {session.source_path}"
        )

    window = session.annotation_set.window
    decoded = []
    try:
        for frame_index in range(window.end_frame_index + 1):
            success, bgr_frame = capture.read()
            if not success:
                raise AnnotationEditorError(
                    "source decode ended before required frame "
                    f"{frame_index}"
                )
            if frame_index < window.start_frame_index:
                continue
            height, width = bgr_frame.shape[:2]
            declared = session.annotation_set.source_video
            if (width, height) != (declared.width_px, declared.height_px):
                raise AnnotationEditorError(
                    f"decoded frame {frame_index} has {width}x{height}, expected "
                    f"{declared.width_px}x{declared.height_px}"
                )
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            decoded.append(Image.fromarray(rgb_frame))
    finally:
        capture.release()

    if len(decoded) != window.frame_count:
        raise AnnotationEditorError(
            f"decoded {len(decoded)} window frames, expected {window.frame_count}"
        )
    return tuple(decoded)


def first_unlabeled_index(annotation_set: BallAnnotationSet) -> int:
    """Return the first unfinished row, or the first row when all are done."""

    for index, annotation in enumerate(annotation_set.annotations):
        if annotation.annotation_status == "unlabeled":
            return index
    return 0


def _format_number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


class BallAnnotationEditor:
    """Tkinter UI for one verified draft annotation set."""

    def __init__(
        self,
        root: Any,
        session: AnnotationSession,
        frames: Sequence[Any],
    ) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk
        from PIL import ImageTk

        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        self.ImageTk = ImageTk
        self.root = root
        self.session = session
        self.annotation_set = session.annotation_set
        self.frames = tuple(frames)
        self.current_index = first_unlabeled_index(self.annotation_set)
        self._updating = False
        self._loaded_form: FrameFormValues | None = None
        self._frame_photo = None
        self._magnifier_photo = None
        self._transform: DisplayTransform | None = None
        self._last_status = ""
        self._last_visibility = ""

        if len(self.frames) != self.annotation_set.window.frame_count:
            raise AnnotationEditorError("GUI received the wrong number of frames")

        root.title(
            "Ball annotation — "
            f"{self.annotation_set.possession_id} "
            f"({self.annotation_set.window.start_frame_index}–"
            f"{self.annotation_set.window.end_frame_index})"
        )
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        root.bind("<Control-s>", lambda _event: self._save_and_advance())

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        self.canvas_width = max(640, min(1120, screen_width - 480))
        self.canvas_height = max(360, min(700, screen_height - 150))

        self._build_layout()
        self._load_current_frame()

    def _build_layout(self) -> None:
        tk = self.tk
        ttk = self.ttk
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            main,
            width=self.canvas_width,
            height=self.canvas_height,
            background="#101010",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.canvas.bind("<Button-1>", self._on_frame_click)
        self.canvas.bind(
            "<Button-3>",
            self._on_uncertainty_boundary_click,
        )
        self.canvas.bind("<Motion>", self._on_frame_motion)
        self.canvas.bind("<Leave>", lambda _event: self._hide_magnifier())

        controls = ttk.Frame(main, width=390)
        controls.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        self.frame_label_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        ttk.Label(
            controls,
            textvariable=self.frame_label_var,
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(controls, textvariable=self.progress_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        self.status_var = tk.StringVar()
        self.visibility_var = tk.StringVar()
        self.absence_var = tk.StringVar()
        self.certainty_var = tk.StringVar()
        self.geometry_var = tk.BooleanVar()
        self.center_x_var = tk.StringVar()
        self.center_y_var = tk.StringVar()
        self.uncertainty_var = tk.StringVar()
        self.eligible_var = tk.BooleanVar()
        self.geometry_source_var = tk.StringVar(value="none")

        row = 2
        row = self._add_combo(
            controls,
            row,
            "Annotation status",
            self.status_var,
            sorted(ANNOTATION_STATUSES),
        )
        row = self._add_combo(
            controls,
            row,
            "Visibility",
            self.visibility_var,
            [""] + sorted(VISIBILITY_STATES),
        )
        row = self._add_combo(
            controls,
            row,
            "Absence reason",
            self.absence_var,
            [""] + sorted(ABSENCE_REASONS),
        )
        row = self._add_combo(
            controls,
            row,
            "Ball identity certainty",
            self.certainty_var,
            [""] + sorted(IDENTITY_CERTAINTIES),
        )

        self.geometry_check = ttk.Checkbutton(
            controls,
            text="Defensible complete-ball center",
            variable=self.geometry_var,
            command=self._on_geometry_toggle,
        )
        self.geometry_check.grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        ttk.Label(controls, text="Geometry source").grid(
            row=row, column=0, sticky="w"
        )
        ttk.Label(controls, textvariable=self.geometry_source_var).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        ttk.Label(controls, text="Center x / y (source px)").grid(
            row=row, column=0, sticky="w"
        )
        point_frame = ttk.Frame(controls)
        point_frame.grid(row=row, column=1, sticky="ew")
        self.center_x_entry = ttk.Entry(
            point_frame, textvariable=self.center_x_var, width=10
        )
        self.center_y_entry = ttk.Entry(
            point_frame, textvariable=self.center_y_var, width=10
        )
        self.center_x_entry.pack(side="left")
        self.center_y_entry.pack(side="left", padx=(4, 0))
        row += 1

        ttk.Label(controls, text="Max plausible center error (px)").grid(
            row=row, column=0, sticky="w"
        )
        self.uncertainty_entry = ttk.Entry(
            controls, textvariable=self.uncertainty_var, width=12
        )
        self.uncertainty_entry.grid(row=row, column=1, sticky="w")
        row += 1
        self.eligible_check = ttk.Checkbutton(
            controls,
            text="Localization eligible",
            variable=self.eligible_var,
        )
        self.eligible_check.grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        tags_frame = ttk.LabelFrame(controls, text="Difficulty tags", padding=4)
        tags_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        self.tag_vars = {}
        self.tag_checks = {}
        for tag_index, tag in enumerate(sorted(DIFFICULTY_TAGS)):
            variable = tk.BooleanVar()
            check = ttk.Checkbutton(tags_frame, text=tag, variable=variable)
            check.grid(
                row=tag_index // 2,
                column=tag_index % 2,
                sticky="w",
                padx=(0, 8),
            )
            self.tag_vars[tag] = variable
            self.tag_checks[tag] = check
        row += 1

        ttk.Label(controls, text="Notes / audit explanation").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        self.notes_text = tk.Text(controls, height=4, width=44, wrap="word")
        self.notes_text.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1

        ttk.Label(
            controls,
            text=(
                "Left-click the best complete-ball center. Then right-click "
                "the farthest alternate center you would still consider "
                "plausible; the tool measures the error radius for you. In "
                "the 4× magnifier, gray grid spacing is 5 source pixels, white "
                "is the cursor, cyan is your center, and yellow is uncertainty. "
                "No detector predictions are shown."
            ),
            wraplength=370,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 6))
        row += 1

        buttons = ttk.Frame(controls)
        buttons.grid(row=row, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Previous", command=self._previous).pack(
            side="left"
        )
        ttk.Button(
            buttons,
            text="Save frame & next (Ctrl+S)",
            command=self._save_and_advance,
        ).pack(side="left", padx=6)
        ttk.Button(buttons, text="Next", command=self._next).pack(side="left")

        controls.columnconfigure(1, weight=1)
        self.status_var.trace_add("write", self._on_status_or_visibility_change)
        self.visibility_var.trace_add(
            "write", self._on_status_or_visibility_change
        )
        self.certainty_var.trace_add("write", self._on_simple_state_change)
        for variable in (
            self.center_x_var,
            self.center_y_var,
            self.uncertainty_var,
        ):
            variable.trace_add("write", self._on_geometry_value_change)

    def _add_combo(
        self,
        parent: Any,
        row: int,
        label: str,
        variable: Any,
        values: Sequence[str],
    ) -> int:
        self.ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        combo = self.ttk.Combobox(
            parent,
            textvariable=variable,
            values=tuple(values),
            state="readonly",
            width=26,
        )
        combo.grid(row=row, column=1, sticky="ew")
        if label == "Visibility":
            self.visibility_combo = combo
        elif label == "Absence reason":
            self.absence_combo = combo
        elif label == "Ball identity certainty":
            self.certainty_combo = combo
        return row + 1

    def _on_status_or_visibility_change(self, *_args: Any) -> None:
        if self._updating:
            return
        status = self.status_var.get()
        visibility = self.visibility_var.get()
        self._updating = True
        try:
            if status != self._last_status:
                self.visibility_var.set("")
                self.absence_var.set("")
                self.certainty_var.set("")
                self._clear_geometry()
                self._set_all_tags(False)
                visibility = ""
            elif visibility != self._last_visibility:
                self.absence_var.set("")
                self._clear_geometry()

            if status != "labeled":
                self.visibility_var.set("")
                self.absence_var.set("")
                self.certainty_var.set("")
                self._clear_geometry()
                self._set_all_tags(False)
            elif visibility == "not_visible":
                self._clear_geometry()
            elif visibility == "indeterminate":
                self.absence_var.set("")
                self.certainty_var.set("ambiguous")
                self._clear_geometry()
            elif visibility in {"fully_visible", "partially_visible"}:
                self.absence_var.set("")
        finally:
            self._updating = False
        self._last_status = self.status_var.get()
        self._last_visibility = self.visibility_var.get()
        self._sync_control_states()
        self._draw_geometry_overlay()

    def _on_simple_state_change(self, *_args: Any) -> None:
        if self._updating:
            return
        if self.certainty_var.get() == "ambiguous":
            self.eligible_var.set(False)
        self._sync_control_states()

    def _on_geometry_toggle(self) -> None:
        if not self.geometry_var.get():
            self._clear_geometry()
        self._sync_control_states()
        self._draw_geometry_overlay()

    def _on_geometry_value_change(self, *_args: Any) -> None:
        if not self._updating:
            self._draw_geometry_overlay()

    def _clear_geometry(self) -> None:
        self.geometry_var.set(False)
        self.center_x_var.set("")
        self.center_y_var.set("")
        self.uncertainty_var.set("")
        self.eligible_var.set(False)

    def _set_all_tags(self, selected: bool) -> None:
        for variable in self.tag_vars.values():
            variable.set(selected)

    def _sync_control_states(self) -> None:
        labeled = self.status_var.get() == "labeled"
        visibility = self.visibility_var.get()
        self.visibility_combo.configure(state="readonly" if labeled else "disabled")
        self.absence_combo.configure(
            state="readonly"
            if labeled and visibility == "not_visible"
            else "disabled"
        )
        self.certainty_combo.configure(
            state="readonly"
            if labeled and visibility != "indeterminate"
            else "disabled"
        )
        geometry_allowed = labeled and visibility in {
            "fully_visible",
            "partially_visible",
        }
        self.geometry_check.configure(
            state="normal" if geometry_allowed else "disabled"
        )
        geometry_enabled = geometry_allowed and self.geometry_var.get()
        entry_state = "normal" if geometry_enabled else "disabled"
        self.center_x_entry.configure(state=entry_state)
        self.center_y_entry.configure(state=entry_state)
        self.uncertainty_entry.configure(state=entry_state)
        eligible_allowed = (
            geometry_enabled
            and self.certainty_var.get() in {"certain", "probable"}
        )
        self.eligible_check.configure(
            state="normal" if eligible_allowed else "disabled"
        )
        if not eligible_allowed:
            self.eligible_var.set(False)
        for check in self.tag_checks.values():
            check.configure(state="normal" if labeled else "disabled")

        if not geometry_enabled:
            source = "none"
        elif visibility == "fully_visible":
            source = "observed_complete_ball_center"
        else:
            source = "human_amodal_estimate"
        self.geometry_source_var.set(source)

    def _form_from_annotation(self, annotation: FrameAnnotation) -> FrameFormValues:
        geometry = annotation.geometry
        return FrameFormValues(
            annotation_status=annotation.annotation_status,
            visibility=annotation.visibility,
            absence_reason=annotation.absence_reason,
            identity_certainty=annotation.game_ball_identity_certainty,
            has_geometry=geometry is not None,
            center_x=(
                None if geometry is None else _format_number(geometry.center_xy_px[0])
            ),
            center_y=(
                None if geometry is None else _format_number(geometry.center_xy_px[1])
            ),
            uncertainty_radius_px=(
                None
                if geometry is None
                else _format_number(geometry.uncertainty_radius_px)
            ),
            localization_eligible=annotation.localization_eligible,
            difficulty_tags=annotation.difficulty_tags,
            notes=annotation.notes,
        )

    def _collect_form(self) -> FrameFormValues:
        return FrameFormValues(
            annotation_status=self.status_var.get(),
            visibility=_optional_text(self.visibility_var.get()),
            absence_reason=_optional_text(self.absence_var.get()),
            identity_certainty=_optional_text(self.certainty_var.get()),
            has_geometry=self.geometry_var.get(),
            center_x=_optional_text(self.center_x_var.get()),
            center_y=_optional_text(self.center_y_var.get()),
            uncertainty_radius_px=_optional_text(self.uncertainty_var.get()),
            localization_eligible=self.eligible_var.get(),
            difficulty_tags=tuple(
                sorted(
                    tag
                    for tag, variable in self.tag_vars.items()
                    if variable.get()
                )
            ),
            notes=self.notes_text.get("1.0", "end-1c"),
        )

    def _apply_form(self, form: FrameFormValues) -> None:
        self._updating = True
        try:
            self.status_var.set(form.annotation_status)
            self.visibility_var.set(form.visibility or "")
            self.absence_var.set(form.absence_reason or "")
            self.certainty_var.set(form.identity_certainty or "")
            self.geometry_var.set(form.has_geometry)
            self.center_x_var.set("" if form.center_x is None else str(form.center_x))
            self.center_y_var.set("" if form.center_y is None else str(form.center_y))
            self.uncertainty_var.set(
                ""
                if form.uncertainty_radius_px is None
                else str(form.uncertainty_radius_px)
            )
            self.eligible_var.set(form.localization_eligible)
            for tag, variable in self.tag_vars.items():
                variable.set(tag in form.difficulty_tags)
            self.notes_text.delete("1.0", "end")
            if form.notes:
                self.notes_text.insert("1.0", form.notes)
        finally:
            self._updating = False
        self._last_status = self.status_var.get()
        self._last_visibility = self.visibility_var.get()
        self._sync_control_states()

    def _load_current_frame(self) -> None:
        annotation = self.annotation_set.annotations[self.current_index]
        form = self._form_from_annotation(annotation)
        self._apply_form(form)
        self._loaded_form = self._collect_form()
        total = len(self.annotation_set.annotations)
        completed = sum(
            item.annotation_status != "unlabeled"
            for item in self.annotation_set.annotations
        )
        self.frame_label_var.set(
            f"Frame {annotation.frame_index}  ({self.current_index + 1}/{total})"
        )
        self.progress_var.set(
            f"Completed {completed}/{total} — review remains draft"
        )
        self._render_frame()

    def _render_frame(self) -> None:
        from PIL import Image

        frame = self.frames[self.current_index]
        self._transform = fit_source_to_viewport(
            frame.width,
            frame.height,
            self.canvas_width,
            self.canvas_height,
        )
        transform = self._transform
        resized = frame.resize(
            (round(transform.display_width), round(transform.display_height)),
            Image.Resampling.LANCZOS,
        )
        self._frame_photo = self.ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(
            transform.origin_x,
            transform.origin_y,
            image=self._frame_photo,
            anchor="nw",
            tags="source_frame",
        )
        self._draw_geometry_overlay()

    def _draw_geometry_overlay(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("human_annotation")
        if not self.geometry_var.get() or self._transform is None:
            return
        try:
            source_x = float(self.center_x_var.get())
            source_y = float(self.center_y_var.get())
            canvas_x, canvas_y = map_source_to_canvas(
                source_x, source_y, self._transform
            )
        except (ValueError, FormValidationError):
            return
        radius = 7
        self.canvas.create_oval(
            canvas_x - radius,
            canvas_y - radius,
            canvas_x + radius,
            canvas_y + radius,
            outline="#00ffff",
            width=2,
            tags="human_annotation",
        )
        self.canvas.create_line(
            canvas_x - 11,
            canvas_y,
            canvas_x + 11,
            canvas_y,
            fill="#00ffff",
            width=1,
            tags="human_annotation",
        )
        self.canvas.create_line(
            canvas_x,
            canvas_y - 11,
            canvas_x,
            canvas_y + 11,
            fill="#00ffff",
            width=1,
            tags="human_annotation",
        )
        try:
            uncertainty = float(self.uncertainty_var.get())
        except ValueError:
            return
        if not math.isfinite(uncertainty) or uncertainty <= 0.0:
            return
        display_radius = (
            uncertainty
            * self._transform.display_width
            / self._transform.source_width
        )
        self.canvas.create_oval(
            canvas_x - display_radius,
            canvas_y - display_radius,
            canvas_x + display_radius,
            canvas_y + display_radius,
            outline="#ffff00",
            width=2,
            dash=(4, 3),
            tags="human_annotation",
        )

    def _on_frame_click(self, event: Any) -> None:
        if self._transform is None:
            return
        if not (
            self.status_var.get() == "labeled"
            and self.visibility_var.get() in {"fully_visible", "partially_visible"}
        ):
            self.messagebox.showwarning(
                "Choose a visible state",
                "Set status to labeled and visibility to fully_visible or "
                "partially_visible before placing a center.",
            )
            return
        try:
            source_x, source_y = map_canvas_to_source(
                event.x, event.y, self._transform
            )
        except FormValidationError:
            return
        self.geometry_var.set(True)
        self.center_x_var.set(_format_number(source_x))
        self.center_y_var.set(_format_number(source_y))
        if self.certainty_var.get() in {"certain", "probable"}:
            self.eligible_var.set(True)
        self._sync_control_states()
        self._draw_geometry_overlay()

    def _on_uncertainty_boundary_click(self, event: Any) -> None:
        if self._transform is None or not self.geometry_var.get():
            self.messagebox.showwarning(
                "Place the center first",
                "Left-click the best complete-ball center before setting its "
                "uncertainty boundary.",
            )
            return
        try:
            boundary_x, boundary_y = map_canvas_to_source(
                event.x,
                event.y,
                self._transform,
            )
            center_x = _parse_required_number(
                self.center_x_var.get(),
                "center x",
            )
            center_y = _parse_required_number(
                self.center_y_var.get(),
                "center y",
            )
            radius = uncertainty_radius_from_boundary(
                center_x,
                center_y,
                boundary_x,
                boundary_y,
            )
        except FormValidationError as error:
            self.messagebox.showwarning(
                "Uncertainty was not changed",
                str(error),
            )
            return
        self.uncertainty_var.set(_format_number(radius))
        self._draw_geometry_overlay()
        self._show_magnifier(boundary_x, boundary_y)

    def _on_frame_motion(self, event: Any) -> None:
        if self._transform is None:
            return
        try:
            source_x, source_y = map_canvas_to_source(
                event.x, event.y, self._transform
            )
        except FormValidationError:
            self._hide_magnifier()
            return
        self._show_magnifier(source_x, source_y)

    def _show_magnifier(self, source_x: float, source_y: float) -> None:
        from PIL import Image, ImageDraw

        frame = self.frames[self.current_index]
        half_size = 30
        center_x = round(source_x)
        center_y = round(source_y)
        patch_size = half_size * 2 + 1
        patch = Image.new("RGB", (patch_size, patch_size), "black")
        left = max(0, center_x - half_size)
        top = max(0, center_y - half_size)
        right = min(frame.width, center_x + half_size + 1)
        bottom = min(frame.height, center_y + half_size + 1)
        crop = frame.crop((left, top, right, bottom))
        patch.paste(
            crop,
            (left - (center_x - half_size), top - (center_y - half_size)),
        )
        magnified = patch.resize((244, 244), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(magnified)
        center = 122
        magnification = 4.0
        for source_offset in range(-25, 26, 5):
            grid_position = center + source_offset * magnification
            draw.line(
                (grid_position, 0, grid_position, 243),
                fill="#777777",
                width=1,
            )
            draw.line(
                (0, grid_position, 243, grid_position),
                fill="#777777",
                width=1,
            )

        try:
            selected_x = float(self.center_x_var.get())
            selected_y = float(self.center_y_var.get())
        except ValueError:
            selected_x = math.nan
            selected_y = math.nan
        selected_zoom_x = center + (selected_x - center_x) * magnification
        selected_zoom_y = center + (selected_y - center_y) * magnification
        if (
            math.isfinite(selected_zoom_x)
            and math.isfinite(selected_zoom_y)
            and 0 <= selected_zoom_x <= 243
            and 0 <= selected_zoom_y <= 243
        ):
            try:
                uncertainty = float(self.uncertainty_var.get())
            except ValueError:
                uncertainty = math.nan
            if math.isfinite(uncertainty) and uncertainty > 0.0:
                zoom_radius = uncertainty * magnification
                draw.ellipse(
                    (
                        selected_zoom_x - zoom_radius,
                        selected_zoom_y - zoom_radius,
                        selected_zoom_x + zoom_radius,
                        selected_zoom_y + zoom_radius,
                    ),
                    outline="#ffff00",
                    width=2,
                )
            draw.line(
                (
                    selected_zoom_x - 12,
                    selected_zoom_y,
                    selected_zoom_x + 12,
                    selected_zoom_y,
                ),
                fill="#00ffff",
                width=2,
            )
            draw.line(
                (
                    selected_zoom_x,
                    selected_zoom_y - 12,
                    selected_zoom_x,
                    selected_zoom_y + 12,
                ),
                fill="#00ffff",
                width=2,
            )
        draw.line(
            (center - 8, center, center + 8, center),
            fill="white",
            width=2,
        )
        draw.line(
            (center, center - 8, center, center + 8),
            fill="white",
            width=2,
        )
        draw.rectangle((0, 0, 243, 243), outline="white", width=2)
        self._magnifier_photo = self.ImageTk.PhotoImage(magnified)
        self.canvas.delete("magnifier")
        self.canvas.create_image(
            self.canvas_width - 8,
            8,
            image=self._magnifier_photo,
            anchor="ne",
            tags="magnifier",
        )

    def _hide_magnifier(self) -> None:
        if hasattr(self, "canvas"):
            self.canvas.delete("magnifier")

    def _is_dirty(self) -> bool:
        return (
            self._loaded_form is not None
            and self._collect_form() != self._loaded_form
        )

    def _confirm_discard(self) -> bool:
        if not self._is_dirty():
            return True
        return self.messagebox.askyesno(
            "Discard unsaved edits?",
            "This frame has unsaved changes. Discard them and continue?",
            icon="warning",
        )

    def _navigate(self, new_index: int) -> None:
        if new_index == self.current_index or not (0 <= new_index < len(self.frames)):
            return
        if not self._confirm_discard():
            return
        self.current_index = new_index
        self._load_current_frame()

    def _previous(self) -> None:
        self._navigate(self.current_index - 1)

    def _next(self) -> None:
        self._navigate(self.current_index + 1)

    def _save_and_advance(self) -> None:
        annotation = self.annotation_set.annotations[self.current_index]
        form = self._collect_form()
        if form.annotation_status == "unlabeled":
            self.messagebox.showwarning(
                "Frame is unfinished",
                "Choose labeled or excluded before completing this frame.",
            )
            return
        try:
            row = form_to_annotation_row(
                annotation.frame_index,
                form,
                self.annotation_set.source_video,
            )
            self.annotation_set = atomic_save_frame(
                self.session.annotation_path,
                self.annotation_set,
                row,
            )
        except (
            AnnotationEditorError,
            AnnotationValidationError,
            FormValidationError,
            OSError,
        ) as error:
            self.messagebox.showerror(
                "Frame was not saved",
                f"Nothing was written because validation/save failed:\n\n{error}",
            )
            return

        unfinished_after = [
            index
            for index, item in enumerate(self.annotation_set.annotations)
            if index > self.current_index and item.annotation_status == "unlabeled"
        ]
        unfinished_before = [
            index
            for index, item in enumerate(self.annotation_set.annotations)
            if index <= self.current_index and item.annotation_status == "unlabeled"
        ]
        if unfinished_after:
            self.current_index = unfinished_after[0]
        elif unfinished_before:
            self.current_index = unfinished_before[0]
        else:
            self.messagebox.showinfo(
                "Draft complete",
                "Every frame is completed. The file is still a draft; this editor "
                "never marks a set reviewed.",
            )
        self._load_current_frame()

    def _on_close(self) -> None:
        if not self._confirm_discard():
            return
        self.root.destroy()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Open a verified draft ball-annotation JSON in the prediction-blind "
            "desktop editor."
        )
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="Existing draft annotation JSON to edit",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        required=True,
        help="Repository root used to resolve and verify source_video.path",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        session = prepare_annotation_session(
            args.annotations,
            args.repository_root,
        )
        frames = decode_exact_window_frames(session)
        import tkinter as tk

        root = tk.Tk()
        BallAnnotationEditor(root, session, frames)
        root.mainloop()
    except (
        AnnotationEditorError,
        AnnotationValidationError,
        FileNotFoundError,
        OSError,
    ) as error:
        raise SystemExit(f"ball annotation editor error: {error}") from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

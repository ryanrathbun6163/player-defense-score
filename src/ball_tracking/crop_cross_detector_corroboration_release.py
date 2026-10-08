"""Owned release adapter for the frozen RF/YOLO corroboration comparison.

Importing this module performs no I/O. Production authority is checked before
scientific access; the parent reads only administrative records and metadata.
The artificial route uses explicit fixture files and cannot authorize a launch.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

from . import crop_cross_detector_corroboration as selector
from . import crop_cross_detector_corroboration_evaluation as evaluation
from . import crop_cross_detector_corroboration_review as review
from . import crop_retention_monitor as monitor
from . import crop_retention_resources as resources
from .annotations import BallAnnotationSet
from .development_experiments import canonical_sha256, require_digest

ID = "rfdetr_yolo_crop_corroboration_v0_1"
BASE_COMMIT = "b71c64d3fd46bb27072efa8644e90c1c222bb65c"
SCOPE_PATH = "configs/ball_tracking/proposals/rfdetr_yolo_crop_corroboration_release_v0_1.json"
SCOPE_SHA = "b81098c3aae5a89438d4c0cd621534abc806b5d9b099a5aa35211ce9be0d8ff2"
PROPOSAL_PATH = "docs/ball_crop_cross_detector_corroboration_release_proposal.md"
PROPOSAL_SHA = "ae28ca67f9464747d11cfb5c2d7b0f5883d3d776e2a1dc48be786bca570abf2e"
MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/" + ID + ".json"
APPROVAL_PATH = "configs/ball_tracking/reviews/rfdetr_yolo_crop_corroboration_execution_approval_v0_1.json"
ADMIN_ROOT = "data/outputs/t/corroboration_release_validation_b71c64d3fd46"
VALIDATION_EXTENSION_BINDING = {"path": ADMIN_ROOT + "/validation_extension_approval.json", "size_bytes": 3340,
                                "sha256": "9691953d2a7e73e47c5a607e0e69914aead1f3b1086956284652e33031dd9362"}
CERTIFICATE_PATH = ADMIN_ROOT + "/implementation_validation.json"
CHECKPOINT_PATH = ADMIN_ROOT + "/post_commit_execution_checkpoint.json"
HISTORY_PATH = ADMIN_ROOT + "/frozen_history.json"
PRIOR_HISTORY = {"path": "data/outputs/t/mean_impl_10e5fcb90f51/frozen_history.json",
                 "size_bytes": 2999767, "sha256": "010f3c3f31df54becd664e3c30938eb82413cd703add939874c4f8ef63d9ad52"}
MEAN_RESULT = "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/attempts/b36133afc62a4c9fb34547ab6ad2c4ac.result.json"
OUTPUT_ROOT = "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1"
OUTPUT_DIR = OUTPUT_ROOT + "/audit/cross_detector_corroboration_v0_1"
UNIT_KEY = "cross-detector-corroboration:study:"
MAX_RETURN_BYTES, MAX_RECEIPT_BYTES = 512 * 1024, 1024 * 1024
MAX_NEW_BYTES, MAX_SECONDS = 4 * 1024**3, 1200
RETRY_BASE_COMMIT = "3233d2cb1c2d3773bd109ac81ed8474a63c4d2c4"
RETRY_SCOPE_PATH = "configs/ball_tracking/proposals/rfdetr_yolo_crop_corroboration_retry_integration_v0_1.json"
RETRY_SCOPE_SHA = "f125ccc0ef2e4d732a0f807436c9d1ec9dab3d47b258f973af5a6e59c74daa80"
RETRY_PROPOSAL_PATH = "docs/ball_crop_cross_detector_corroboration_retry_integration_proposal.md"
RETRY_PROPOSAL_SHA = "bd03fd5c262135934802f27f7fe5bbcae3cb262bdc25476af5df7ae0da990863"
RETRY_MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/rfdetr_yolo_crop_corroboration_retry_v0_1.json"
RETRY_APPROVAL_PATH = "configs/ball_tracking/reviews/rfdetr_yolo_crop_corroboration_retry_execution_approval_v0_1.json"
RETRY_ADMIN_ROOT = "data/outputs/t/corroboration_retry_integration_3233d2c"
RETRY_CERTIFICATE_PATH = RETRY_ADMIN_ROOT + "/implementation_validation.json"
RETRY_CHECKPOINT_PATH = RETRY_ADMIN_ROOT + "/post_commit_execution_checkpoint.json"
RETRY_HISTORY_PATH = RETRY_ADMIN_ROOT + "/runtime_frozen_history.json"
RETRY_PREDECESSOR = "ac3a321649414170adf823deaa1b7b9e"
RETRY_BASELINE_BYTES, RETRY_MAX_SECONDS = 8875168842, 1198.875
RETRY_CHANGED_FILES = {"src/ball_tracking/crop_cross_detector_corroboration_release.py",
                       "tests/test_ball_crop_cross_detector_corroboration_release.py"}
HISTORY_GUARD_BASE_COMMIT = "154657cd42c9db7573ab0e2d6cab3bea8fa48ff3"
HISTORY_GUARD_SCOPE_PATH = "configs/ball_tracking/proposals/rfdetr_yolo_crop_corroboration_history_guard_correction_v0_1.json"
HISTORY_GUARD_SCOPE_SHA = "32b43a6dadcfe8d0c5187288957f56e0d5e3a7eca844193c2c2c25fe6059ed12"
HISTORY_GUARD_PROPOSAL = {"path": RETRY_ADMIN_ROOT + "/next_correction_proposal.json", "size_bytes": 3725,
                          "sha256": "8a3e7741e0083831305cd25350a8bd532a5271f30434f2c19d67e5ed480a9ba0"}
HISTORY_GUARD_ADMIN_ROOT = "data/outputs/t/corroboration_history_guard_154657c"
HISTORY_GUARD_MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/rfdetr_yolo_crop_corroboration_retry_v0_2.json"
HISTORY_GUARD_APPROVAL_PATH = "configs/ball_tracking/reviews/rfdetr_yolo_crop_corroboration_retry_execution_approval_v0_2.json"
HISTORY_GUARD_CERTIFICATE_PATH = HISTORY_GUARD_ADMIN_ROOT + "/implementation_validation.json"
HISTORY_GUARD_CHECKPOINT_PATH = HISTORY_GUARD_ADMIN_ROOT + "/post_commit_execution_checkpoint.json"
HISTORY_GUARD_PARENT_CERTIFICATE = {"path": RETRY_CERTIFICATE_PATH, "size_bytes": 162862,
                                    "sha256": "c2f86015149bc38ddeaf950c5e9de464bfc6cfe3e6ced0cd73a002f2ef6c3bea"}
HISTORY_GUARD_IMPLEMENTATION_APPROVAL = {"path": HISTORY_GUARD_ADMIN_ROOT + "/approval.json", "size_bytes": 155680,
                                        "sha256": "3491252f7fe439f063469bae83118a8eaf808cb39b013469a217aa391780674c"}
HISTORY_GUARD_PRODUCER_CONTRACT = {"path": HISTORY_GUARD_ADMIN_ROOT + "/producer_contract.json", "size_bytes": 2662,
                                 "sha256": "4dd5d29b9072cbd7e07892f6d656639f75ac98cc59cef502a9ce38675cf95f1c"}
HISTORY_GUARD_PRODUCER_TEST = ("test_ball_crop_cross_detector_corroboration_release.RetryHistoryTests."
                               "test_real_monitor_failure_record_is_accepted_by_retry_predecessor_guard")
ROLE_PHASE = {"rf_candidates": "selection", "yolo_candidates": "selection",
              "reviewed_annotations": "evaluation", "saved_control_observations": "evaluation",
              "saved_mean_observations": "evaluation", "saved_scoring_pool": "evaluation",
              "saved_mean_scoring_pool": "evaluation", "source_png": "review"}
ROLE_COUNTS = {"rf_candidates": 6, "yolo_candidates": 6, "reviewed_annotations": 6,
               "saved_control_observations": 12, "saved_mean_observations": 6,
               "saved_scoring_pool": 2, "saved_mean_scoring_pool": 2, "source_png": 150}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, "Duplicate JSON key")
            value[key] = item
        return value
    def invalid(value):
        raise ValueError("Nonfinite JSON number: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _read_admin(root, name, maximum):
    path = _safe(root, name)
    before = _stat(path)
    _require(0 < before["size_bytes"] <= maximum, "Administrative record exceeds its bound")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    _require(len(raw) == before["size_bytes"] and _stat(path) == before,
             "Administrative record changed during read")
    return raw


def _relative(value):
    _require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./-]+", value)
             and not value.startswith(("/", "."))
             and all(p not in ("", ".", "..") for p in value.split("/")), "Unsafe relative path")
    for part in value.split("/"):
        _require(not part.endswith(".") and not re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part),
                 "Windows reserved or alias path")
    return value


def _safe(root, relative):
    root = monitor._root_path(root)
    parts = _relative(relative).split("/")
    current = root
    for part in parts:
        current = current / part
        if current.exists() or current.is_symlink():
            info = current.lstat()
            _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                     "Path traverses a link or reparse point")
    _require(current.resolve().is_relative_to(root), "Path escapes the declared root")
    return current


def _stat(path):
    info = Path(path).lstat()
    _require(stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "Expected an ordinary immutable file")
    return {"size_bytes": info.st_size, "mtime_ns": info.st_mtime_ns,
            "device": info.st_dev, "inode": info.st_ino}


def _binding(path, raw):
    return {"path": path, "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _read_bound(root, binding, *, maximum=32 * 1024 * 1024, allow_empty=False):
    """Caller establishes whether this is an administrative or worker input."""
    require_digest(binding["sha256"], "bound file digest", 64)
    path = _safe(root, binding["path"])
    before = _stat(path)
    size = binding.get("size_bytes", before["size_bytes"])
    _require(type(size) is int and (0 if allow_empty else 1) <= size <= maximum and before["size_bytes"] == size,
             "Bound file size differs or exceeds allowance")
    with path.open("rb") as stream:
        raw = stream.read(size + 1)
    _require(len(raw) == size and _stat(path) == before and hashlib.sha256(raw).hexdigest() == binding["sha256"],
             "Bound file changed or digest differs")
    return raw


def _expected_output_names(windows):
    names = {"manifest.json", "provenance.json", "summary.json", "summary.md"}
    names.update("evaluation/" + p + ".json" for p in evaluation.POOLS)
    for w in windows:
        wid = w["window_id"]
        names.update((f"selection/{wid}/observations.json", f"evaluation/{wid}.json"))
        base = f"review/{wid}"
        names.update(base + "/" + name for name in ("comparison.mp4", "first.png", "last.png", "review_index.json"))
        for frame in range(w["start_frame_index"], w["end_frame_index"] + 1):
            names.update(f"{base}/native/{name}/frame_{frame:06d}.png" for name in review.VIEW_NAMES.values())
    return names


def validate_scope(scope, *, production=False):
    """Validate the complete file graph without accessing any declared file."""
    windows = scope["windows"]
    _require(len(windows) == 6 and len({w["window_id"] for w in windows}) == 6,
             "Exactly six distinct windows required")
    _require(Counter(w["purpose"] for w in windows) == Counter({p: 3 for p in evaluation.POOLS}),
             "Exactly three windows per separate pool required")
    for w in windows:
        _relative(w["window_id"])
        _require("/" not in w["window_id"] and type(w["start_frame_index"]) is int
                 and type(w["end_frame_index"]) is int and w["start_frame_index"] >= 0
                 and w["end_frame_index"] - w["start_frame_index"] == 24, "Invalid complete window")
    rows = scope["existing_scientific_files"]
    _require(len(rows) == 190 and len({r["path"].casefold() for r in rows}) == 190
             and Counter(r["role"] for r in rows) == Counter(ROLE_COUNTS), "Exact 190-input inventory required")
    inputs = {r["path"]: r for r in rows}
    ids = {w["window_id"] for w in windows}
    for row in rows:
        _relative(row["path"])
        require_digest(row["sha256"], "input digest", 64)
        _require(type(row["size_bytes"]) is int and 0 < row["size_bytes"] <= 128 * 1024**2,
                 "Input size is missing or excessive")
        _require(row["first_allowed_phase"] == ROLE_PHASE[row["role"]], "Input role/phase mismatch")
        _require(row.get("window_id") in ids or row["role"] in ("saved_scoring_pool", "saved_mean_scoring_pool"),
                 "Input belongs to another window")
    for w in windows:
        for key, role in (("crop_candidates", "rf_candidates"), ("yolo_candidates", "yolo_candidates")):
            b = w[key]
            _require(b["path"] in inputs and inputs[b["path"]]["role"] == role
                     and inputs[b["path"]]["window_id"] == w["window_id"]
                     and b["sha256"] == inputs[b["path"]]["sha256"], "Candidate window binding mismatch")
        subset = [r for r in rows if r.get("window_id") == w["window_id"]]
        _require(sum(r["role"] == "reviewed_annotations" for r in subset) == 1, "Missing window labels")
        _require(sorted(r["frame_index"] for r in subset if r["role"] == "source_png") ==
                 list(range(w["start_frame_index"], w["end_frame_index"] + 1)), "Incomplete source PNG inventory")
    _require(len(scope["saved_controls"]) == len(scope["saved_reports"]) == 12
             and len(scope["saved_mean_references"]) == 6, "Incomplete saved controls")
    for w in windows:
        wid = w["window_id"]
        for key in ("saved_controls", "saved_reports"):
            selected = [r for r in scope[key] if r["window_id"] == wid]
            _require(len(selected) == 2 and {r["config"]["arm"] for r in selected} == {evaluation.TOP, evaluation.TT},
                     "Incorrect saved control pairing")
        mean = [r for r in scope["saved_mean_references"] if r["window_id"] == wid]
        _require(len(mean) == 1 and mean[0]["expected_config"] == evaluation._control_config(evaluation.MEAN),
                 "Mean configuration differs")
    files = scope["outputs"]["files"]
    _relative(scope["outputs"]["directory"])
    _require(len(files) == 342 and len({r["path"].casefold() for r in files}) == 342
             and {r["path"] for r in files} == _expected_output_names(windows), "Exact 342-output inventory required")
    for row in files:
        _relative(row["path"])
        _require(type(row["maximum_bytes"]) is int and 0 < row["maximum_bytes"] <= MAX_NEW_BYTES,
                 "Invalid output size bound")
    _require(sum(r["maximum_bytes"] for r in files) < MAX_NEW_BYTES, "No aggregate room for administrative/temporary bytes")
    if production:
        _require(scope["study_id"] == ID and scope["outputs"]["directory"] == OUTPUT_DIR
                 and not scope.get("artificial_only"), "Production scope identity differs")
    else:
        _require(scope.get("artificial_only") is True and isinstance(scope.get("fixture_id"), str)
                 and scope["fixture_id"].startswith("synthetic:")
                 and all(w["window_id"].startswith("synthetic_") for w in windows)
                 and all(r["path"].startswith("data/synthetic/") for r in rows)
                 and scope["outputs"]["directory"].startswith("data/outputs/synthetic_"),
                 "Explicit artificial fixture scope required")
    return scope


_validate_scope = validate_scope


def candidate_run(payload, window, detector="rfdetr"):
    """Pure saved-format conversion: no loaders, inference or pointer access."""
    if detector == "rfdetr":
        from .crop_path_confidence_mean_experiment import candidate_run as convert
        projection = {k: v for k, v in window.items() if k != "yolo_candidates"}
        run = convert(payload, projection)
    elif detector == "yolo":
        from .yolo_crop_recovery import candidate_run as convert, unit
        from .tiled_candidates import crop_views
        declared = payload["header"]["window"]
        for key in ("window_id", "purpose", "annotation_set_id", "possession_id", "source_video",
                    "start_frame_index", "end_frame_index"):
            _require(declared[key] == window[key], "YOLO source/window/header differs")
        expected_units = [unit(window, frame, view) for frame in
                          range(window["start_frame_index"], window["end_frame_index"] + 1) for view in crop_views()]
        units = payload["header"]["inference_units"]
        unit_fields = tuple(expected_units[0])
        _require(len(units) == 100 and [{k: r[k] for k in unit_fields} for r in units] == expected_units,
                 "YOLO inference inventory omits/reorders/duplicates a crop unit")
        for row in units:
            require_digest(row["actual_inference_commit"], "YOLO actual inference commit", 40)
            _relative(row["checkpoint"]["path"])
            require_digest(row["checkpoint"]["sha256"], "inert YOLO checkpoint digest", 64)
        sources = payload["header"]["source_frames"]
        _require(len(sources) == 25 and [r["frame_index"] for r in sources] ==
                 list(range(window["start_frame_index"], window["end_frame_index"] + 1))
                 and all(r["window_id"] == window["window_id"] for r in sources)
                 and payload["header"]["crop_views"] == crop_views(), "YOLO source/crop inventory differs")
        for row in sources:
            _relative(row["source_png"]["path"])
            require_digest(row["source_png"]["sha256"], "inert source PNG digest", 64)
        run = convert(payload)
    else:
        raise ValueError("Unknown detector namespace")
    _require(run.source_video.to_dict() == window["source_video"] and run.possession_id == window["possession_id"]
             and run.annotation_set_id == window["annotation_set_id"]
             and [f.frame_index for f in run.frames] == list(range(window["start_frame_index"], window["end_frame_index"] + 1)),
             "Adapted candidate identity differs")
    return run


def yolo_candidate_run(payload, window):
    return candidate_run(payload, window, "yolo")


def _owned_paths(root, attempt_id):
    _require(isinstance(attempt_id, str) and re.fullmatch(r"[0-9a-f]{32}", attempt_id), "Owned attempt identity missing")
    base = _safe(root, OUTPUT_ROOT + "/attempts/" + attempt_id)
    _require(os.environ.get("BALL_RETENTION_ATTEMPT_ID") == attempt_id
             and Path(os.environ.get("BALL_RETENTION_START_GATE", "")).resolve() == Path(str(base) + ".start")
             and Path(os.environ.get("BALL_RETENTION_RESULT_PATH", "")).resolve() == Path(str(base) + ".result.json"),
             "Worker gate/result is outside its exact reservation")
    return base


def _ownership(root, attempt_id):
    base = _owned_paths(root, attempt_id)
    _require(Path(str(base) + ".start").is_file(), "Supervisor has not released the worker gate")
    supervisor_pid = os.environ.get("BALL_RETENTION_PARENT_PID")
    _require(isinstance(supervisor_pid, str) and re.fullmatch(r"[1-9][0-9]*", supervisor_pid),
             "Worker has no valid monitor-injected supervisor PID")
    owner = monitor._read_record(_safe(root, OUTPUT_ROOT + "/supervisor.lock"))
    _require(type(owner.get("pid")) is int and owner["pid"] == int(supervisor_pid)
             and resources._alive(owner["pid"]) and isinstance(owner.get("token"), str), "Worker has no live owning supervisor")


class PhaseAccess:
    """Worker-only scientific allowlist, with immutable six-selection sealing."""
    def __init__(self, root, scope, *, artificial=False, attempt_id=None):
        validate_scope(scope, production=not artificial)
        self.root, self.scope = Path(root).resolve(), scope
        self.artificial, self.attempt_id = artificial, attempt_id
        if not artificial:
            _ownership(self.root, attempt_id)
        self.rows = {r["path"]: r for r in scope["existing_scientific_files"]}
        self.metadata = {}
        for name, row in self.rows.items():
            actual = _stat(_safe(self.root, name))
            _require(actual["size_bytes"] == row["size_bytes"] and
                     ("preparation_metadata" not in row or actual == row["preparation_metadata"]),
                     "Scientific metadata changed before worker access")
            self.metadata[name] = actual
        self.phase, self.opened, self.log = "selection", set(), []
        self.access_log = self.log
        self.frozen, self.selection_content, self.evaluations = None, {}, set()
        self.sink = None

    def read(self, name):
        if not self.artificial:
            _ownership(self.root, self.attempt_id)
        _require(name in self.rows and ROLE_PHASE[self.rows[name]["role"]] == self.phase,
                 "Scientific input is undeclared or forbidden in this phase")
        if self.frozen is not None:
            self.sink.verify(self.frozen)
        _require(_stat(_safe(self.root, name)) == self.metadata[name], "Scientific input metadata changed")
        raw = _read_bound(self.root, self.rows[name], maximum=128 * 1024**2)
        _require(_stat(_safe(self.root, name)) == self.metadata[name], "Scientific input changed during read")
        self.opened.add(name)
        self.log.append({"phase": self.phase, "path": name, "role": self.rows[name]["role"]})
        return raw

    def json(self, name):
        _require(name in self.rows and self.rows[name]["role"] != "source_png", "Pixels are not JSON inputs")
        return _json(self.read(name))

    def freeze(self, bindings, sink):
        expected = {f"selection/{w['window_id']}/observations.json" for w in self.scope["windows"]}
        _require(self.phase == "selection" and self.frozen is None and len(bindings) == 6
                 and {sink.relative(b["path"]) for b in bindings} == expected,
                 "All six unique selections must freeze exactly once")
        sink.verify(bindings)
        self.frozen = deepcopy(bindings)
        self.sink = sink
        sink.selection_frozen = True
        self.phase = "evaluation"

    def evaluated(self, window_id):
        _require(self.phase == "evaluation" and window_id in {w["window_id"] for w in self.scope["windows"]}
                 and window_id not in self.evaluations, "Evaluation completion is invalid or repeated")
        self.evaluations.add(window_id)

    def begin_review(self, sink):
        _require(self.phase == "evaluation" and len(self.evaluations) == 6 and self.frozen is not None,
                 "All six evaluations must finish before pixels")
        sink.verify(self.frozen)
        self.phase = "review"

    render = begin_review

    def fail(self):
        self.phase = "failed"


class OutputSink:
    """Create-only publications and one verified generated-video temporary."""
    def __init__(self, root, scope):
        self.root = Path(root).resolve()
        self.directory = scope["outputs"]["directory"]
        files = scope["outputs"]["files"]
        _require(len(files) == len({r["path"].casefold() for r in files}), "Duplicate output path")
        for row in files:
            _relative(row["path"])
            _require(type(row["maximum_bytes"]) is int and 0 < row["maximum_bytes"] <= MAX_NEW_BYTES,
                     "Invalid output limit")
        self.folder = _safe(root, self.directory)
        _require(not self.folder.exists(), "Create-only output directory already exists")
        self.folder.mkdir(parents=True)
        self.bounds = {r["path"]: r["maximum_bytes"] for r in scope["outputs"]["files"]}
        self.bindings, self.metadata, self.videos = {}, {}, {}
        self.total, self.selection_frozen, self.closed = 0, False, False

    def relative(self, name):
        _require(name.startswith(self.directory + "/"), "Binding is outside new study directory")
        return name[len(self.directory) + 1:]

    def _target(self, relative):
        _require(not self.closed and relative in self.bounds and relative not in self.bindings
                 and not (self.selection_frozen and relative.startswith("selection/")), "Output is closed, undeclared, existing or frozen")
        target = _safe(self.folder, relative)
        _require(not target.exists(), "Create-only output already exists")
        return target

    def write(self, relative, raw):
        target = self._target(relative)
        _require(type(raw) is bytes and 0 < len(raw) <= self.bounds[relative], "Artifact exceeds its declared limit")
        _require(self.total + len(raw) + monitor.FINAL_RESERVE < MAX_NEW_BYTES, "Aggregate new-output allowance exceeded")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
            stream.flush()
        name = self.directory + "/" + relative
        binding = _binding(name, raw)
        _require(_read_bound(self.root, binding, maximum=self.bounds[relative]) == raw, "Output publication differs")
        self.bindings[relative], self.metadata[relative] = binding, {"path": name, **_stat(target)}
        self.total += len(raw)
        return deepcopy(binding)

    write_bytes = write

    def json(self, relative, value):
        return self.write(relative, _json_bytes(value))

    def verify(self, bindings):
        if isinstance(bindings, dict):
            bindings = [bindings]
        for b in bindings:
            name = self.relative(b["path"])
            _require(name in self.bindings and b == self.bindings[name], "Unknown sealed output")
            _require(_stat(_safe(self.folder, name)) == {k: v for k, v in self.metadata[name].items() if k != "path"},
                     "Sealed output metadata changed")
            _read_bound(self.root, b, maximum=self.bounds[name])

    def open_video(self, relative, fps, size):
        import cv2
        self._target(relative)
        _require(not self.videos and relative.endswith("/comparison.mp4") and fps == 5.0
                 and tuple(size) == (review.TILE_WIDTH * 3, review.TILE_HEIGHT), "Invalid generated-video request")
        temp = _safe(self.folder, "tmp/" + uuid.uuid4().hex + ".mp4")
        temp.parent.mkdir(exist_ok=True)
        writer = cv2.VideoWriter(str(temp), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
        _require(writer.isOpened(), "Cannot open owned review writer")
        self.videos[relative] = (temp, writer)
        return writer

    def verify_video(self, relative, count, fps, size):
        import cv2
        _require(relative in self.videos and count == 25 and fps == 5.0
                 and tuple(size) == (review.TILE_WIDTH * 3, review.TILE_HEIGHT), "Invalid generated-video verification")
        path, writer = self.videos[relative]
        writer.release()
        _require(0 < _stat(path)["size_bytes"] <= self.bounds[relative], "Generated video exceeds its bound")
        capture = cv2.VideoCapture(str(path))
        decoded = 0
        try:
            _require(capture.isOpened() and abs(capture.get(cv2.CAP_PROP_FPS) - fps) < .001, "Generated video FPS differs")
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                decoded += 1
                _require(decoded <= count and frame.shape == (size[1], size[0], 3), "Generated video dimensions/count differ")
            _require(decoded == count, "Generated video missing final frame")
        finally:
            capture.release()
        binding = self.write(relative, path.read_bytes())
        path.unlink()  # Only the verified owned UUID temporary, inside the new directory.
        path.parent.rmdir()
        del self.videos[relative]
        return binding

    def close_writers(self):
        for _, writer in self.videos.values():
            writer.release()

    def complete(self):
        _require(not self.closed and not self.videos and set(self.bindings) == set(self.bounds), "Incomplete output inventory or open video")
        self.verify(list(self.bindings.values()))
        actual = set()
        for folder, dirs, files in os.walk(self.folder):
            for name in dirs + files:
                _safe(self.folder, (Path(folder) / name).relative_to(self.folder).as_posix())
            actual.update((Path(folder) / name).relative_to(self.folder).as_posix() for name in files)
        _require(actual == set(self.bounds), "Undeclared output or temporary remains")
        self.closed = True
        return list(self.bindings.values()), list(self.metadata.values())


def _pointer(value, pointer, *, mean=False):
    pattern = r"/new_evaluation_reports/(0|1|2)" if mean else r"/evaluation_reports/(0|[1-9][0-9]*)"
    _require(isinstance(pointer, str) and re.fullmatch(pattern, pointer), "Undeclared report pointer form")
    parts = pointer.strip("/").split("/")
    return deepcopy(value[parts[0]][int(parts[1])])


def _saved_for_window(scope, access, window, rf, labels, pools):
    wid = window["window_id"]
    observations, reports = {}, {}
    for reference in (r for r in scope["saved_controls"] if r["window_id"] == wid):
        arm = reference["config"]["arm"]
        observations[arm] = evaluation.verify_saved_observations(access.json(reference["file"]["path"]), reference, rf)
    for reference in (r for r in scope["saved_reports"] if r["window_id"] == wid):
        arm = reference["config"]["arm"]
        report = _pointer(pools[reference["source"]["path"]], reference["source"]["json_pointer"])
        reports[arm] = evaluation.verify_saved_report(report, reference, observations[arm], rf, labels)
    reference = next(r for r in scope["saved_mean_references"] if r["window_id"] == wid)
    _require(reference["observations_json_pointer"] == "/observations", "Mean observation pointer differs")
    wrapper = access.json(reference["observations_file"])
    obs = wrapper["observations"]
    _require(obs["config"] == reference["expected_config"], "Mean observation settings differ")
    # These nested hashes are derived only here, after exact whole-file reads and sealing.
    derived = {"config": reference["expected_config"], "variant_id": obs["variant_id"],
               "observations_content_sha256": canonical_sha256(obs),
               "input_candidate_content_sha256": canonical_sha256(rf.to_dict()),
               "original_selection_commit": reference["original_selection_commit"],
               "original_detector_commit": rf.model_provenance.code_commit, "frame_count": 25}
    observations[evaluation.MEAN] = evaluation.verify_saved_observations(wrapper, derived, rf)
    report = _pointer(pools[reference["report_file"]], reference["report_json_pointer"], mean=True)
    report_reference = {"config": reference["expected_config"], "purpose": reference["purpose"],
                        "localization_radius_px": reference["expected_localization_radius_px"],
                        "report_content_sha256": canonical_sha256(report),
                        "observations_content_sha256": canonical_sha256(obs),
                        "original_selection_commit": reference["original_selection_commit"],
                        "original_evaluation_commit": reference["original_evaluation_commit"]}
    reports[evaluation.MEAN] = evaluation.verify_saved_report(report, report_reference, obs, rf, labels)
    return observations, reports


def _compact_summary(comparisons, pools, reviews, artificial):
    """Fixed lossless transport projections; full records live in evaluation files.

    Omit duplicate pool window bodies and raw candidate identity lists. Preserve
    every outcome/effect frame and encode paired errors as rows with shared
    column names, rather than repeating seven verbose keys for every match.
    """
    windows = []
    error_columns = ["frame_index", "old_error_px", "new_error_px", "difference_px",
                     "old_candidate_index", "new_candidate_index", "candidate_choice"]
    for original in comparisons:
        row = {k: deepcopy(original[k]) for k in ("window_id", "purpose", "possession_id", "first_frame", "last_frame",
               "summaries", "paired_transitions", "temporal_metrics", "startup", "startup_parity_required",
               "primary_effects", "recovery", "count_deltas", "window_regressions", "changed_emission_frames")}
        row["candidate_choices_against_top_one"] = {k: deepcopy(original["candidate_choices_against_top_one"][k])
                                                    for k in ("counts", "frame_indices")}
        row["candidate_availability"] = {k: deepcopy(original["candidate_availability"][k])
                                          for k in ("eligible_denominator", "original_rf", "corroborated")}
        row["paired_original_center_errors"] = {arm: [[r[k] for k in error_columns] for r in records]
                                                 for arm, records in original["paired_original_center_errors"].items()}
        windows.append(row)
    compact_pools = []
    for original in pools:
        row = {"purpose": original["purpose"], "window_count": original["window_count"],
               "runs_not_concatenated": True, "window_regressions": deepcopy(original["window_regressions"])}
        row["totals"] = {arm: {k: deepcopy(v) for k, v in totals.items() if k != "frames"}
                         for arm, totals in original["totals"].items()}
        row["paired_transitions"] = {arm: {kind: {before: {after: cell["count"] for after, cell in cells.items()}
                                                 for before, cells in states.items()} for kind, states in table.items()}
                                      for arm, table in original["paired_transitions"].items()}
        for key in ("primary_effects", "candidate_choices_against_top_one"):
            row[key] = {k: v["count"] for k, v in original[key].items()}
        row["candidate_availability"] = {"eligible_denominator": original["candidate_availability"]["eligible_denominator"],
                                          **{k: original["candidate_availability"][k]["count"] for k in ("original_rf", "corroborated")}}
        compact_pools.append(row)
    return {"schema_version": "ball_crop_corroboration_summary/v0.1", "study_id": ID,
            "artificial_only": artificial, "windows": windows, "pools": compact_pools,
            "paired_error_columns": error_columns, "interpretation": evaluation.development_interpretation(pools),
            "reviews": reviews, "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def run_comparison(scope, access, sink, commit, *, render=True, progress=None):
    """Use the tested pure functions; scientific bodies remain inside this worker."""
    require_digest(commit, "release implementation commit", 40)
    _require(access.scope is scope and sink.directory == scope["outputs"]["directory"] and access.phase == "selection",
             "Mismatched owned comparison context")
    _require(render is True or (access.artificial and callable(render)), "Complete six-clip rendering is required")
    def tick():
        if progress is not None:
            progress()
    runs, observations, bindings, origins, comparisons, review_data = {}, {}, [], {}, [], []
    try:
        for w in scope["windows"]:
            tick()
            wid = w["window_id"]
            rf_payload, yolo_payload = access.json(w["crop_candidates"]["path"]), access.json(w["yolo_candidates"]["path"])
            rf, yolo = candidate_run(rf_payload, w, "rfdetr"), candidate_run(yolo_payload, w, "yolo")
            origins[wid] = {"rf_file": deepcopy(w["crop_candidates"]), "yolo_file": deepcopy(w["yolo_candidates"]),
                            "yolo_original_header": deepcopy(yolo_payload["header"])}
            del rf_payload, yolo_payload
            obs = selector.select_candidates(rf, yolo, commit, progress=tick)
            observations[wid], runs[wid] = obs, (rf, yolo)
            access.selection_content[wid] = canonical_sha256(obs)
            bindings.append(sink.json(f"selection/{wid}/observations.json", obs))
        access.freeze(bindings, sink)
        sink.json("manifest.json", {"study_id": ID, "commit": commit, "attempt_id": access.attempt_id,
                  "selection_bindings": bindings, "all_six_frozen_before_scoring": True,
                  "scope_content_sha256": canonical_sha256(scope)})
        pools = {r["path"]: access.json(r["path"]) for r in scope["existing_scientific_files"]
                 if r["role"] in ("saved_scoring_pool", "saved_mean_scoring_pool")}
        for w in scope["windows"]:
            tick()
            wid, (rf, yolo) = w["window_id"], runs[w["window_id"]]
            label_row = next(r for r in scope["existing_scientific_files"] if r["role"] == "reviewed_annotations" and r["window_id"] == wid)
            labels = BallAnnotationSet.from_mapping(access.json(label_row["path"]))
            by_arm, saved = _saved_for_window(scope, access, w, rf, labels, pools)
            before = _json_bytes(saved)
            _require(canonical_sha256(observations[wid]) == access.selection_content[wid], "Frozen selection changed")
            new_report = evaluation.evaluate_selection(labels, rf, observations[wid], commit, yolo_run=yolo)
            by_arm[selector.ARM] = observations[wid]
            comparison = evaluation.compare_window(w, new_report, saved, by_arm)
            _require(_json_bytes(saved) == before, "Saved controls changed")
            comparisons.append(comparison)
            sink.json(f"evaluation/{wid}.json", {"new_report": new_report, "saved_reports": saved,
                      "comparison": comparison, "saved_report_references": [r for r in scope["saved_reports"] if r["window_id"] == wid],
                      "saved_mean_reference": next(r for r in scope["saved_mean_references"] if r["window_id"] == wid)})
            access.evaluated(wid)
            review_data.append((w, rf, labels, by_arm, {selector.ARM: new_report, **saved}))
        del pools
        aggregated = [evaluation.aggregate_pool([c for c in comparisons if c["purpose"] == p], p) for p in evaluation.POOLS]
        for pool in aggregated:
            sink.json("evaluation/" + pool["purpose"] + ".json", pool)
        access.begin_review(sink)
        renderer = review.render_window if render is True else render
        reviews = []
        for w, rf, labels, by_arm, reports in review_data:
            tick()
            wid = w["window_id"]
            _require(canonical_sha256(observations[wid]) == access.selection_content[wid], "Selection changed before rendering")
            sources = {r["frame_index"]: r for r in scope["existing_scientific_files"] if r["role"] == "source_png" and r["window_id"] == wid}
            def read_source(index):
                import cv2
                import numpy as np
                tick()
                _require(index in sources, "Unapproved source frame")
                pixels = cv2.imdecode(np.frombuffer(access.read(sources[index]["path"]), dtype=np.uint8), cv2.IMREAD_COLOR)
                _require(pixels is not None and pixels.shape == (rf.source_video.height_px, rf.source_video.width_px, 3),
                         "Bound source PNG dimensions differ")
                return pixels
            rendered = renderer(w, rf, labels, {a: by_arm[a] for a in review.ARMS}, {a: reports[a] for a in review.ARMS},
                                read_source=read_source, write_bytes=sink.write, open_video=sink.open_video, verify_video=sink.verify_video)
            sink.verify(rendered["index_binding"])
            reviews.append({"window_id": wid, "index_binding": rendered["index_binding"],
                            "clip": sink.directory + f"/review/{wid}/comparison.mp4", "frame_count": 25, "fps": 5,
                            "first_frame_index": w["start_frame_index"], "final_frame_index": w["end_frame_index"], "human_review": "pending"})
        _require(access.opened == set(access.rows), "Scientific access inventory incomplete or expanded")
        sink.verify(bindings)
        summary = _compact_summary(comparisons, aggregated, reviews, access.artificial)
        sink.json("summary.json", summary)
        lines = ["RF/YOLO corroboration development comparison", summary["interpretation"]["label"],
                 "Six new final-frame human reviews remain pending.",
                 "Suppressed false output is not recovered localization; agreement does not establish object identity."]
        for pool in aggregated:
            lines.append(pool["purpose"] + ": " + json.dumps(pool.get("totals", {}), sort_keys=True))
        sink.write("summary.md", ("\n".join(lines) + "\n").encode("utf-8"))
        sink.json("provenance.json", {"study_id": ID, "attempt_id": access.attempt_id, "commit": commit,
                  "scope_content_sha256": canonical_sha256(scope), "input_files": scope["existing_scientific_files"],
                  "source_origins": origins, "selection_freeze": bindings, "scientific_access_log": access.log,
                  "new_selection_calls": 6, "new_evaluation_calls": 6, "saved_control_replays": 0,
                  "source_video_decodes": 0, "model_calls": 0, "artificial_only": access.artificial})
        artifacts, metadata = sink.complete()
        access.phase = "complete"
        result = {"schema_version": "ball_crop_corroboration_worker_result/v0.1", "study_id": ID,
                  "attempt_id": access.attempt_id, "unit_key": UNIT_KEY, "commit": commit,
                  "scope_content_sha256": canonical_sha256(scope), "summary": summary,
                  "selection_bindings": bindings, "scientific_input_count": len(access.opened),
                  "scientific_access_log": deepcopy(access.log),
                  "artifacts": artifacts, "artifact_metadata": metadata, "artificial_only": access.artificial}
        _require(len(_json_bytes(result)) <= MAX_RECEIPT_BYTES, "Worker receipt exceeds its complete serialized bound")
        _require(len(_json_bytes(parent_return(result))) <= MAX_RETURN_BYTES, "Parent return exceeds its complete serialized bound")
        return result
    except BaseException:
        access.fail()
        raise
    finally:
        sink.close_writers()


def parent_return(result):
    value = {k: deepcopy(result[k]) for k in ("schema_version", "study_id", "attempt_id", "unit_key", "commit",
             "scope_content_sha256", "summary", "artifacts", "scientific_input_count", "artificial_only")}
    _require(len(_json_bytes(value)) <= MAX_RETURN_BYTES, "Complete parent return exceeds bound")
    return value


def run_artificial(root, scope, commit, *, render=True, progress=None):
    validate_scope(scope, production=False)
    _require(Path(root).resolve() != Path(__file__).resolve().parents[2], "Artificial route cannot use the repository root")
    access = PhaseAccess(root, scope, artificial=True)
    sink = OutputSink(root, scope)
    return run_comparison(scope, access, sink, commit, render=render, progress=progress)


def verify_history(journal, scope, phase="before", attempt_id=None):
    """Inspect an already loaded administrative journal; never open science."""
    _require(phase in ("before", "worker", "completed"), "Unknown history phase")
    expected = scope["preserved_history"]
    count = expected["resource_event_count"]
    _require(len(journal.events) >= count and count > 0 and journal.events[count - 1]["sha256"] == expected["resource_tip"],
             "Preserved resource prefix changed or truncated")
    old = object.__new__(resources.BudgetJournal)
    old.events, old.limits, old.root = journal.events[:count], journal.limits, journal.root
    attempts = old._attempts()
    _require(len(attempts) == expected["closed_attempts"] and all(a["finished"] is not None for a in attempts.values())
             and old.consumed() == expected["consumed_seconds"], "Preserved consumed budget changed")
    failed = {aid for aid, a in attempts.items() if a["finished"].get("success") is not True}
    _require(failed == set(expected["historic_failure_ids"]) and len(attempts) - len(failed) == expected["successes"],
             "Historical failure/success evidence changed")
    for aid, a in attempts.items():
        for suffix, event in (("reservation", a["start"]), ("completion", a["finished"])):
            p = Path(journal.root) / "attempts" / f"{aid}.{suffix}.json"
            _require(p.is_file() and monitor._read_record(p) == {"event_sha256": event["sha256"]},
                     "Historical administrative seal missing or changed")
    suffix = journal.events[count:]
    if phase == "before":
        _require(not suffix and not any(a["start"]["unit_key"] == UNIT_KEY for a in attempts.values()),
                 "Consumed attempt cannot retry or adopt a suffix")
    else:
        current = journal._attempts()
        _require(isinstance(attempt_id, str) and len(current) == len(attempts) + 1 and attempt_id in current,
                 "Unexpected active/completed attempt")
        a = current[attempt_id]
        _require(suffix and suffix[0] == a["start"] and all(e.get("attempt_id") == attempt_id for e in suffix)
                 and a["start"]["unit_key"] == UNIT_KEY and a["start"]["selection_unit"] is False
                 and 0 < a["start"]["reserved_seconds"] <= min(MAX_SECONDS, expected["remaining_seconds"]),
                 "New attempt reservation differs")
        _require((a["finished"] is None) if phase == "worker" else
                 (a["finished"] is not None and suffix[-1] == a["finished"] and a["finished"]["success"] is True),
                 "Attempt has not reached the required valid phase")
    return journal


class CorroborationJournal(resources.BudgetJournal):
    def __init__(self, output_root, limits, *, scope, baseline_bytes=0):
        self.scope, self.baseline_bytes = scope, baseline_bytes
        super().__init__(output_root, limits)

    def reserve(self, unit_key, selection_unit):
        _require(unit_key == UNIT_KEY and selection_unit is False, "Unknown corroboration reservation")
        verify_history(self, self.scope)
        seconds = min(MAX_SECONDS, self.limits["maximum_cumulative_seconds"] - self.consumed())
        _require(seconds > 0, "Scientific allowance exhausted")
        aid = uuid.uuid4().hex
        event = self.append("started", attempt_id=aid, unit_key=UNIT_KEY, selection_unit=False, reserved_seconds=seconds)
        resources._write_new(self.root / "attempts" / (aid + ".reservation.json"), {"event_sha256": event["sha256"]})
        return aid, seconds

    def append(self, kind, **details):
        measured = details.get("output_bytes") if kind == "sample" else details.get("final_accounting_output_bound_bytes")
        extra = monitor.FINAL_RESERVE if kind == "sample" else 0
        exceeds = measured is not None and measured - self.baseline_bytes + extra > MAX_NEW_BYTES
        if exceeds and kind == "sample":
            super().append(kind, **details)
            raise resources.ResourceLimitError("New attempt bytes exceed four GiB")
        if exceeds and kind == "finished":
            details.update(success=False, failure=details.get("failure") or "New attempt bytes exceed four GiB")
        return super().append(kind, **details)


def verify_retry_history(journal, context, phase="before", attempt_id=None):
    """Check the one explicitly approved retry without changing its old prefix."""
    _require(phase in ("before", "worker", "completed"), "Unknown retry history phase")
    retry, scope = context["retry"], context["scope"]
    expected = retry["retry_design"]["exact_starting_history"]
    count = expected["events"]
    _require(count == 3334 and expected["closed_attempts"] == 64
             and expected["successes"] == 59 and expected["failures"] == 5
             and expected["tip"] == "828394ce0efd82a6665e1bb919593d7208a231ee3ce5b584505fd0abd73d5847"
             and expected["consumed_seconds"] == 3548.648999999985
             and expected["cumulative_cap_seconds"] == journal.limits["maximum_cumulative_seconds"] == 14400,
             "Exact failed scientific predecessor history required")
    _require(len(journal.events) >= count and journal.events[count - 1]["sha256"] == expected["tip"],
             "Failed predecessor prefix changed or truncated")
    original_count = scope["preserved_history"]["resource_event_count"]
    _require(original_count == 3330 and journal.events[original_count - 1]["sha256"] == scope["preserved_history"]["resource_tip"],
             "Original pre-failure prefix changed")
    prior = object.__new__(resources.BudgetJournal)
    prior.events, prior.limits, prior.root = journal.events[:original_count], journal.limits, journal.root
    verify_history(prior, scope)
    old = object.__new__(resources.BudgetJournal)
    old.events, old.limits, old.root = journal.events[:count], journal.limits, journal.root
    attempts = old._attempts()
    _require(len(attempts) == 64 and all(a["finished"] is not None for a in attempts.values())
             and old.consumed() == expected["consumed_seconds"]
             and journal.limits["maximum_cumulative_seconds"] - old.consumed() == expected["remaining_seconds"],
             "Retry would reset failed scientific accounting")
    failed = {aid for aid, a in attempts.items() if a["finished"].get("success") is not True}
    _require(failed == set(expected["failed_attempt_ids"])
             == set(scope["preserved_history"]["historic_failure_ids"]) | {RETRY_PREDECESSOR},
             "Failed scientific attempts changed")
    predecessor = attempts.get(RETRY_PREDECESSOR)
    predecessor_log = f"attempts/{RETRY_PREDECESSOR}.log"
    # The monitor journals its exit-status wrapper. The separately bound audit
    # retains the worker's underlying diagnosis; those fields are not aliases.
    _require(predecessor is not None and predecessor["start"]["unit_key"] == UNIT_KEY
             and predecessor["start"]["selection_unit"] is False
             and predecessor["finished"].get("success") is False
             and predecessor["finished"].get("failure") ==
                 f"ResourceLimitError: Worker failed with exit code 1; see {Path(journal.root) / predecessor_log}"
             and type(predecessor["finished"].get("exit_code")) is int and predecessor["finished"]["exit_code"] == 1
             and predecessor["finished"].get("log_path") == predecessor_log
             and "worker_result" in predecessor["finished"] and predecessor["finished"]["worker_result"] is None
             and predecessor["finished"]["elapsed_seconds"] == 1.125
             and predecessor["finished"].get("charged_elapsed_seconds") == 1.125
             and old.consumed(UNIT_KEY) == 1.125
             and journal.events[original_count] == predecessor["start"]
             and journal.events[count - 1] == predecessor["finished"]
             and all(e.get("attempt_id") == RETRY_PREDECESSOR for e in journal.events[original_count:count]),
             "Exact failed same-unit attempt and charge required")
    for aid, attempt in attempts.items():
        for suffix, event in (("reservation", attempt["start"]), ("completion", attempt["finished"])):
            _require(monitor._read_record(Path(journal.root) / "attempts" / f"{aid}.{suffix}.json") ==
                     {"event_sha256": event["sha256"]}, "Failed-prefix reservation/completion seal changed")
    suffix = journal.events[count:]
    if phase == "before":
        _require(attempt_id is None and not suffix, "Consumed retry cannot reserve again or adopt a suffix")
        return journal
    current = journal._attempts()
    _require(isinstance(attempt_id, str) and attempt_id != RETRY_PREDECESSOR
             and set(current) == set(attempts) | {attempt_id}, "Unexpected retry attempt inventory")
    attempt = current[attempt_id]
    start = attempt["start"]
    _require(suffix and suffix[0] == start and all(e.get("attempt_id") == attempt_id for e in suffix)
             and start["unit_key"] == UNIT_KEY and start["selection_unit"] is False
             and start.get("predecessor_attempt_id") == RETRY_PREDECESSOR
             and start.get("retry_approval") == context["retry_approval_binding"]
             and start.get("original_scientific_scope") == {"path": SCOPE_PATH, "sha256": SCOPE_SHA}
             and start["reserved_seconds"] == min(MAX_SECONDS - old.consumed(UNIT_KEY), expected["remaining_seconds"])
             and 0 < start["reserved_seconds"] <= RETRY_MAX_SECONDS,
             "Retry reservation changed its unit, authority or old ceilings")
    _require((attempt["finished"] is None) if phase == "worker" else
             (attempt["finished"] is not None and suffix[-1] == attempt["finished"]
              and attempt["finished"].get("success") is True), "Retry has not reached the required successful phase")
    if phase == "completed":
        finished = attempt["finished"]
        _require(finished["time_budget_seconds"] == start["reserved_seconds"]
                 and 0 < finished["elapsed_seconds"] == finished["charged_elapsed_seconds"] <= start["reserved_seconds"],
                 "Retry completion changed or exceeded its reservation")
    return journal


class CorroborationRetryJournal(CorroborationJournal):
    """Same study and accounting policy; one separately authorized extra attempt."""
    def __init__(self, output_root, limits, *, context):
        self.context = context
        super().__init__(output_root, limits, scope=context["scope"], baseline_bytes=RETRY_BASELINE_BYTES)

    def reserve(self, unit_key, selection_unit):
        _require(unit_key == UNIT_KEY and selection_unit is False, "Unknown retry reservation")
        authority = self.context["retry_approval_binding"]
        _require(authority["path"] == self.context.get("retry_approval_path", RETRY_APPROVAL_PATH)
                 and _json(_read_bound(self.context["root"], authority, maximum=1024**2)) == self.context["retry_approval"],
                 "Retry approval changed before reservation")
        verify_retry_history(self, self.context)
        _require(not _safe(self.context["root"], OUTPUT_DIR).exists(), "Retry output directory already exists")
        seconds = min(MAX_SECONDS - self.consumed(UNIT_KEY),
                      self.limits["maximum_cumulative_seconds"] - self.consumed())
        _require(0 < seconds <= RETRY_MAX_SECONDS, "Original scientific retry allowance exhausted")
        aid = uuid.uuid4().hex
        event = self.append("started", attempt_id=aid, unit_key=UNIT_KEY, selection_unit=False,
                            reserved_seconds=seconds, predecessor_attempt_id=RETRY_PREDECESSOR,
                            retry_approval=self.context["retry_approval_binding"],
                            original_scientific_scope={"path": SCOPE_PATH, "sha256": SCOPE_SHA})
        resources._write_new(self.root / "attempts" / (aid + ".reservation.json"), {"event_sha256": event["sha256"]})
        return aid, seconds


def _verify_context_history(journal, context, phase="before", attempt_id=None):
    if context.get("retry") is not None:
        return verify_retry_history(journal, context, phase, attempt_id)
    return verify_history(journal, context["scope"], phase, attempt_id)


def _context_baseline(context):
    return RETRY_BASELINE_BYTES if context.get("retry") is not None else _baseline_bytes(context["history"]["preserved_files"])


def _git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _normalized_bindings(root, rows):
    normalized = []
    for row in rows:
        p = Path(row["path"])
        name = p.resolve().relative_to(Path(root).resolve()).as_posix() if p.is_absolute() else _relative(row["path"])
        normalized.append({"path": name, "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
    return sorted(normalized, key=lambda r: r["path"])


def _certificate(root, manifest, scope):
    binding = manifest["implementation_validation"]
    _require(binding["path"] == CERTIFICATE_PATH, "Unknown implementation certificate")
    cert = _json(_read_bound(root, binding, maximum=4 * 1024**2))
    _require(cert["schema_version"] == "ball_crop_cross_detector_corroboration_release_implementation/v0.1"
             and cert["scope"]["path"] == SCOPE_PATH and cert["scope"]["sha256"] == SCOPE_SHA
             and cert["stage1_validation"] == scope["stage1_validation"], "Certificate scope differs")
    rows = _normalized_bindings(root, cert["source_bindings"])
    actual_names = {p.relative_to(Path(root)).as_posix() for folder in ("src", "tests")
                    for p in (Path(root) / folder).rglob("*.py")} | {"requirements.txt"}
    _require(len(rows) == len(actual_names) == 187 and {r["path"] for r in rows} == actual_names, "Complete tested source inventory required")
    for row in rows:
        _read_bound(root, row, maximum=4 * 1024**2, allow_empty=True)
    _require(cert["approval"]["path"] == ADMIN_ROOT + "/approval.json", "Unknown implementation approval")
    approval = _json(_read_bound(root, cert["approval"], maximum=1024**2))
    preserved = _normalized_bindings(root, scope["preserved_worktree_bindings"] + [manifest["scope"], manifest["proposal"]])
    forbidden = ("scientific_body_access_authorized", "scientific_execution_authorized",
                 "administrative_scientific_journal_replay_authorized", "new_media_presentation_authorized",
                 "runtime_manifest_or_execution_approval_creation_authorized", "release_checkpoint_authorized",
                 "stage_authorized", "commit_authorized", "push_authorized", "pr_authorized", "merge_authorized")
    _require(approval["schema_version"] == "ball_crop_cross_detector_corroboration_release_implementation_approval/v0.1"
             and approval["status"] == "approved_release_implementation_and_artificial_validation_only"
             and approval["head"] == BASE_COMMIT
             and _normalized_bindings(root, approval["proposal_bindings"]) == _normalized_bindings(root, [manifest["scope"], manifest["proposal"]])
             and set(approval["implementation_files"]) == {"src/ball_tracking/crop_cross_detector_corroboration_release.py",
                                                         "tests/test_ball_crop_cross_detector_corroboration_release.py"}
             and len(preserved) == len({r["path"] for r in preserved}) == 18
             and _normalized_bindings(root, approval["preserved_worktree_bindings"]) == preserved
             and approval["artificial_validation_budget_seconds"] == 4200
             and approval["maximum_focused_seconds"] == 600 and approval["maximum_full_seconds"] == 3600
             and approval["prior_validation_consumed_seconds_preserved"] == ["2164.2970000000005", "2295.467999999999"]
             and approval["implementation_authorized"] is True and approval["artificial_validation_authorized"] is True
             and all(approval[k] is False for k in forbidden), "Implementation approval or preserved scope differs")
    for row in preserved:
        _read_bound(root, row, maximum=4 * 1024**2)
    extension, grant, allowance = cert.get("validation_extension"), None, 4200
    if extension is not None:
        _require(extension == VALIDATION_EXTENSION_BINDING, "Unknown additive validation approval")
        grant = _json(_read_bound(root, extension, maximum=1024**2))
        _require(grant["schema_version"] == "ball_crop_corroboration_release_validation_extension_approval/v0.1"
                 and grant["status"] == "approved_additive_artificial_validation_allowance"
                 and grant["approved_by"] == "Ryan"
                 and grant["implementation_approval"] == cert["approval"] and grant["scope"] == cert["scope"]
                 and grant["base_budget_seconds"] == 4200 and grant["additional_seconds"] == 600
                 and grant["cumulative_budget_seconds"] == 4800
                 and grant["maximum_focused_seconds"] == 600 and grant["maximum_full_seconds"] == 3600
                 and math.isclose(grant["consumed_seconds_at_approval"], 2145.594000000001, abs_tol=1e-8, rel_tol=0)
                 and len(grant["prior_validation_results"]) == len({b["path"] for b in grant["prior_validation_results"]}) == 4
                 and all(grant[k] is False for k in ("fresh_allowance_or_budget_reset", "scientific_execution_authorized",
                         "scientific_body_access_authorized", "real_resource_journal_access_authorized",
                         "new_media_presentation_authorized", "runtime_execution_authority_creation_authorized",
                         "git_mutations_authorized")), "Additive approval changed or resets consumed authority")
        allowance = grant["cumulative_budget_seconds"]
    receipts = {}
    for kind in ("focused", "full"):
        b = cert[kind + "_result"]
        _require(re.fullmatch(re.escape(ADMIN_ROOT) + "/" + kind + r"_[0-9]+_result\.json", b["path"]), "Unknown validation receipt")
        r = _json(_read_bound(root, b, maximum=4 * 1024**2))
        linked_extension = (r.get("validation_extension") is None and r.get("validation_extension_after") is None
                            if extension is None else
                            isinstance(r.get("validation_extension"), dict) and isinstance(r.get("validation_extension_after"), dict)
                            and _normalized_bindings(root, [r["validation_extension"]]) == _normalized_bindings(root, [extension])
                            == _normalized_bindings(root, [r["validation_extension_after"]]))
        _require(linked_extension and r.get("cumulative_validation_budget_seconds", 4200) == allowance,
                 "Successful validation receipt is not linked to its exact allowance")
        _require(r["success"] is True and r["returncode"] == 0 and r["failure"] is None
                 and r["owned_cleanup_verified"] is True and not r["cleanup_errors"]
                 and r["validator"] == r["validator_after"]
                 and _normalized_bindings(root, r["source_bindings"]) == rows == _normalized_bindings(root, r["source_bindings_after"])
                 and r["preservation_error"] is None
                 and _normalized_bindings(root, [r["approval"]]) == _normalized_bindings(root, [cert["approval"]])
                 == _normalized_bindings(root, [r["approval_after"]])
                 and _normalized_bindings(root, r["preserved_worktree_bindings_before"]) == preserved
                 == _normalized_bindings(root, r["preserved_worktree_bindings_after"])
                 and r["baseline_test_count"] == 1167 and r["failed_count"] == r["error_count"] == 0,
                 "Validation receipt is not a successful frozen-source check")
        receipts[kind] = r
    focused, full = receipts["focused"], receipts["full"]
    n = focused["expected_focused_test_count"]
    _require(type(n) is int and n > 0 and focused["test_count"] == focused["passed_count"] == n
             and focused["skipped_count"] == 0 and full["expected_focused_test_count"] == n
             and full["test_count"] == 1167 + n and full["passed_count"] == 1166 + n and full["skipped_count"] == 1
             and focused["validator"] == full["validator"]
             and 0 < focused["elapsed_seconds"] <= 600 and 0 < full["elapsed_seconds"] <= 3600
             and full["previously_consumed_seconds"] >= focused["previously_consumed_seconds"] + focused["elapsed_seconds"]
             and full["previously_consumed_seconds"] + full["elapsed_seconds"] <= allowance, "Validation counts/budget linkage differ")
    helper = dict(full["validator"])
    helper["path"] = Path(helper["path"]).resolve().relative_to(Path(root).resolve()).as_posix()
    _require(helper["path"] == ADMIN_ROOT + "/validate.py", "Unexpected validation supervisor")
    _read_bound(root, helper, maximum=1024**2)
    result_bindings = cert["validation_results"]
    directory = _safe(root, ADMIN_ROOT)
    result_names = {p.name for p in directory.glob("*_result.json")
                    if re.fullmatch(r"(focused|full)_[0-9]+_result\.json", p.name)}
    starts = {p.name.replace("_started.json", "_result.json") for p in directory.glob("*_started.json")}
    _require(len(result_bindings) == len(result_names) and
             {r["path"] for r in result_bindings} == {ADMIN_ROOT + "/" + n for n in result_names}
             and starts == result_names and cert["focused_result"] in result_bindings and cert["full_result"] in result_bindings,
             "Incomplete validation accounting inventory")
    records = [_json(_read_bound(root, b, maximum=4 * 1024**2)) for b in result_bindings]
    if grant is not None:
        previous = grant["prior_validation_results"]
        _require(all(b in result_bindings for b in previous), "Additive validation dropped or changed consumed receipts")
        prior_records = [r for b, r in zip(result_bindings, records) if b in previous]
        _require(math.isclose(sum(r["elapsed_seconds"] for r in prior_records), grant["consumed_seconds_at_approval"], abs_tol=1e-8, rel_tol=0)
                 and all(r["previously_consumed_seconds"] + r["elapsed_seconds"] <= grant["consumed_seconds_at_approval"] + 1e-8 for r in prior_records)
                 and focused["previously_consumed_seconds"] + 1e-8 >= grant["consumed_seconds_at_approval"],
                 "Additive validation consumption was reset or reordered")
    records.sort(key=lambda r: r["previously_consumed_seconds"])
    consumed = 0.0
    for r in records:
        elapsed = r["elapsed_seconds"]
        _require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed > 0
                 and math.isclose(r["previously_consumed_seconds"], consumed, abs_tol=1e-8, rel_tol=0),
                 "Validation correction budget history differs")
        consumed += elapsed
    _require(consumed <= allowance and records[-1] == full, "Full verification is not the final bounded validation")
    return cert


def _validate_manifest(manifest):
    required = {"schema_version", "study_id", "scope", "proposal", "execution_approval",
                "implementation_validation", "frozen_history", "post_commit_checkpoint",
                "selected_method", "selected_operating_point", "quality_gate"}
    _require(set(manifest) == required and manifest["schema_version"] == "ball_crop_corroboration_release_manifest/v0.1"
             and manifest["study_id"] == ID and manifest["scope"]["path"] == SCOPE_PATH
             and manifest["scope"]["sha256"] == SCOPE_SHA and manifest["proposal"]["path"] == PROPOSAL_PATH
             and manifest["proposal"]["sha256"] == PROPOSAL_SHA
             and manifest["execution_approval"]["path"] == APPROVAL_PATH
             and manifest["frozen_history"]["path"] == HISTORY_PATH
             and manifest["post_commit_checkpoint"] == CHECKPOINT_PATH
             and all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Exact future release manifest required")
    return manifest


def _require_tracked(root, names):
    tracked = set(_git(root, "ls-files").splitlines())
    _require(set(names) <= tracked, "All tested source and preserved work must be committed in the clean release")


def _retry_manifest(manifest):
    corrected = manifest.get("schema_version") == "ball_crop_corroboration_retry_release_manifest/v0.2"
    required = {"schema_version", "study_id", "scope", "proposal", "execution_approval",
                "integration_scope", "integration_proposal", "retry_approval", "implementation_validation",
                "frozen_history", "post_commit_checkpoint", "selected_method", "selected_operating_point", "quality_gate"}
    if corrected:
        required |= {"history_guard_scope", "history_guard_proposal"}
    _require(set(manifest) == required and manifest["schema_version"] ==
             ("ball_crop_corroboration_retry_release_manifest/v0.2" if corrected else "ball_crop_corroboration_retry_release_manifest/v0.1")
             and manifest["study_id"] == ID and manifest["scope"]["path"] == SCOPE_PATH
             and manifest["scope"]["sha256"] == SCOPE_SHA and manifest["proposal"]["path"] == PROPOSAL_PATH
             and manifest["proposal"]["sha256"] == PROPOSAL_SHA and manifest["execution_approval"]["path"] == APPROVAL_PATH
             and manifest["integration_scope"]["path"] == RETRY_SCOPE_PATH and manifest["integration_scope"]["sha256"] == RETRY_SCOPE_SHA
             and manifest["integration_proposal"]["path"] == RETRY_PROPOSAL_PATH
             and manifest["integration_proposal"]["sha256"] == RETRY_PROPOSAL_SHA
             and manifest["retry_approval"]["path"] == (HISTORY_GUARD_APPROVAL_PATH if corrected else RETRY_APPROVAL_PATH)
             and manifest["implementation_validation"]["path"] == (HISTORY_GUARD_CERTIFICATE_PATH if corrected else RETRY_CERTIFICATE_PATH)
             and manifest["frozen_history"]["path"] == RETRY_HISTORY_PATH
             and manifest["post_commit_checkpoint"] == (HISTORY_GUARD_CHECKPOINT_PATH if corrected else RETRY_CHECKPOINT_PATH)
             and all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Exact versioned retry manifest required")
    if corrected:
        _require(manifest["history_guard_scope"]["path"] == HISTORY_GUARD_SCOPE_PATH
                 and manifest["history_guard_scope"]["sha256"] == HISTORY_GUARD_SCOPE_SHA
                 and manifest["history_guard_proposal"] == HISTORY_GUARD_PROPOSAL,
                 "Unknown history-guard correction scope")
    return manifest


def _retry_source_transition(root, current_bindings, ancestor_bindings):
    current = _normalized_bindings(root, current_bindings)
    before = _normalized_bindings(root, ancestor_bindings)
    actual = {p.relative_to(Path(root)).as_posix() for folder in ("src", "tests")
              for p in (Path(root) / folder).rglob("*.py")} | {"requirements.txt"}
    prior_by_name = {b["path"]: b for b in before}
    _require(len(current) == len(before) == len(actual) == 187
             and {b["path"] for b in current} == set(prior_by_name) == actual
             and all(b["path"] in RETRY_CHANGED_FILES or b == prior_by_name[b["path"]] for b in current),
             "Retry changed or omitted a source outside its two-file scope")
    for binding in current:
        _read_bound(root, binding, maximum=4 * 1024**2, allow_empty=True)
    return current, before


def _retry_test_inventory(root, binding, current, helpers, declared_counts):
    binding = _normalized_bindings(root, [binding])[0]
    _require(re.fullmatch(re.escape(RETRY_ADMIN_ROOT) + r"/(test_inventory|focused_0[23]_test_inventory)\.json", binding["path"]),
             "Unknown integration test inventory")
    inventory = _json(_read_bound(root, binding, maximum=4 * 1024**2))
    _require(inventory["schema_version"] == "ball_crop_corroboration_retry_test_inventory/v0.1"
             and _normalized_bindings(root, inventory["source_bindings"]) == current
             and _normalized_bindings(root, inventory["helper_bindings"]) == helpers,
             "Test inventory is not bound to the final source/helpers")
    focused, ignored, full = (inventory[k] for k in ("focused_repository_ids", "ignored_lifecycle_ids", "full_repository_ids"))
    _require(all(isinstance(rows, list) and all(isinstance(v, str) and v for v in rows)
                 and len(rows) == len(set(rows)) for rows in (focused, ignored, full))
             and len(focused) >= 54 and len(ignored) == 17 and len(full) == 1167 + len(focused)
             and set(focused) <= set(full) and not (set(ignored) & set(full)),
             "Incomplete or duplicated frozen test-ID inventory")
    _require(declared_counts == {"repository_focused_test_count": len(focused),
                                "ignored_lifecycle_test_count": len(ignored), "full_test_count": len(full)},
             "Integration test count semantics differ")
    return {"focused": len(focused) + len(ignored), "full": len(full)}


def _retry_certificate(root, manifest, scope):
    """Verify historical evidence as history, then independently bind new bytes."""
    retry = _json(_read_bound(root, manifest["integration_scope"], maximum=4 * 1024**2))
    _require(manifest["implementation_validation"]["path"] == RETRY_CERTIFICATE_PATH, "Unknown retry certificate")
    cert = _json(_read_bound(root, manifest["implementation_validation"], maximum=4 * 1024**2))
    _require(cert["schema_version"] == "ball_crop_corroboration_retry_integration_validation/v0.1"
             and cert["status"] == "artificial_validation_passed_runtime_authority_unchanged"
             and cert["scope"] == manifest["integration_scope"] and cert["proposal"] == manifest["integration_proposal"],
             "Retry integration certificate identity differs")
    evidence = retry["evidence_reuse"]
    original = next(b for b in evidence["original_runtime_package"] if b["path"] == CERTIFICATE_PATH)
    expected_ancestors = [original, evidence["accepted_shutdown_certificate"]]
    _require(_normalized_bindings(root, cert["ancestor_certificates"]) == _normalized_bindings(root, expected_ancestors),
             "Retry certificate changed historical ancestors")
    ancestors = [_json(_read_bound(root, b, maximum=4 * 1024**2)) for b in expected_ancestors]
    _require(ancestors[0]["schema_version"] == "ball_crop_cross_detector_corroboration_release_implementation/v0.1"
             and ancestors[0]["stage1_validation"] == scope["stage1_validation"]
             and ancestors[1]["schema_version"] == "ball_crop_shutdown_implementation_validation/v0.1"
             and ancestors[1]["status"] == "artificial_validation_passed_runtime_authority_unchanged"
             and ancestors[1]["focused_counts"] == evidence["accepted_focused_counts"]
             and ancestors[1]["full_counts"] == evidence["accepted_full_counts"]
             and ancestors[1]["cumulative_validation_seconds"] == 9589.048999999992,
             "Historical artificial evidence differs")
    current, before = _retry_source_transition(root, cert["source_bindings"], ancestors[1]["source_bindings"])
    approval_binding = _normalized_bindings(root, [cert["approval"]])[0]
    _require(approval_binding["path"] == RETRY_ADMIN_ROOT + "/approval.json", "Unknown retry implementation approval")
    approval = _json(_read_bound(root, approval_binding, maximum=4 * 1024**2))
    _require(approval["schema_version"] == "ball_crop_corroboration_retry_integration_implementation_approval/v0.1"
             and approval["status"] == "approved_implementation_and_bounded_artificial_validation"
             and approval["approved_by"] == "Ryan" and isinstance(approval["user_statement"], str) and approval["user_statement"].strip()
             and approval["head"] == RETRY_BASE_COMMIT and set(approval["implementation_files"]) == RETRY_CHANGED_FILES
             and approval["scope_binding"] == manifest["integration_scope"] and approval["proposal_binding"] == manifest["integration_proposal"]
             and _normalized_bindings(root, approval["ancestor_source_bindings"]) == before
             and _normalized_bindings(root, approval["ancestor_certificates"]) == _normalized_bindings(root, expected_ancestors)
             and approval["prior_consumption_records"] == evidence["consumption_records"]
             and approval["previously_consumed_seconds"] == 9589.048999999992 and approval["prior_cap_seconds"] == 10200
             and approval["additional_seconds"] == approval["maximum_new_phase_seconds"] == 2800
             and approval["cumulative_validation_budget_seconds"] == 13000
             and approval["maximum_focused_invocations"] == 3 and approval["maximum_focused_seconds"] == 300
             and approval["maximum_full_invocations"] == 1 and approval["maximum_full_seconds"] == 2500
             and approval["closed_remainder_reusable"] is False
             and approval["maximum_sampled_memory_bytes"] == 8 * 1024**3
             and approval["maximum_new_output_bytes"] == 4 * 1024**3
             and approval["minimum_free_disk_bytes"] == 50 * 1024**3
             and approval["maximum_natural_shutdown_seconds"] == approval["maximum_forced_cleanup_seconds"] == 1
             and approval["prior_validation_consumed_seconds_preserved"] == ["2164.2970000000005", "2295.467999999999"]
             and all(approval[k] is True for k in ("implementation_authorized", "repository_source_edits_authorized",
                                                  "ignored_validator_implementation_authorized", "artificial_validation_authorized"))
             and all(approval[k] is False for k in ("scientific_body_access_authorized", "scientific_execution_authorized",
                       "real_resource_journal_replay_authorized", "runtime_authority_or_certificate_replacement_authorized")),
             "Retry implementation approval or additive allowance differs")
    old_protected = _normalized_bindings(root, ancestors[1]["preserved_worktree_bindings"])
    _require(len(old_protected) == 199 and _normalized_bindings(root, approval["ancestor_protected_bindings"]) == old_protected,
             "Retry omitted historical protected bindings")
    protected = _normalized_bindings(root, [b for b in old_protected if b["path"] not in RETRY_CHANGED_FILES]
                                    + [manifest["integration_scope"], manifest["integration_proposal"]])
    _require(_normalized_bindings(root, cert["preserved_worktree_bindings"]) == protected, "Retry protected scope differs")
    for binding in protected:
        _read_bound(root, binding, maximum=4 * 1024**2, allow_empty=True)
    for binding in evidence["old_helper_bindings"]:
        _read_bound(root, binding, maximum=1024**2)
    helpers = _normalized_bindings(root, cert["helper_bindings"])
    helper_names = {RETRY_ADMIN_ROOT + "/" + n for n in ("validate.py", "finalize_validation.py", "lifecycle.py", "test_lifecycle.py")}
    _require(len(helpers) == 4 and {b["path"] for b in helpers} == helper_names, "Incomplete integration helper inventory")
    for binding in helpers:
        _read_bound(root, binding, maximum=1024**2)
        if Path(binding["path"]).name in ("lifecycle.py", "test_lifecycle.py"):
            old = next(b for b in evidence["old_helper_bindings"] if Path(b["path"]).name == Path(binding["path"]).name)
            _require((binding["sha256"], binding["size_bytes"]) == (old["sha256"], old["size_bytes"]), "Lifecycle behavior changed")
    counts = _retry_test_inventory(root, cert["test_inventory"], current, helpers, cert["test_counts"])
    bindings = _normalized_bindings(root, cert["validation_results"])
    historical = _normalized_bindings(root, [r["binding"] for r in evidence["consumption_records"]])
    _require(len(historical) == 15 and all(b in bindings for b in historical), "Historical validation receipts dropped or altered")
    old_total = 0.0
    for row in evidence["consumption_records"]:
        record = _json(_read_bound(root, row["binding"], maximum=4 * 1024**2))
        _require(record["elapsed_seconds"] == row["elapsed_seconds"]
                 and record["previously_consumed_seconds"] == row["previously_consumed_seconds"]
                 and record.get("success") == row["success"] and record.get("failure") == row["failure"]
                 and math.isclose(row["previously_consumed_seconds"], old_total, rel_tol=0, abs_tol=1e-8),
                 "Historical validation charges changed")
        old_total += row["elapsed_seconds"]
    _require(math.isclose(old_total, 9589.048999999992, rel_tol=0, abs_tol=1e-8), "Historical validation budget reset")
    new_bindings = [b for b in bindings if b not in historical]
    directory = _safe(root, RETRY_ADMIN_ROOT)
    names = {p.name for p in directory.glob("*_result.json") if re.fullmatch(r"(focused_0[1-3]|full_01)_result\.json", p.name)}
    all_result_names = {p.name for p in directory.glob("*_result.json")}
    starts = {p.name.replace("_started.json", "_result.json") for p in directory.glob("*_started.json")}
    _require(2 <= len(new_bindings) <= 4 and names == all_result_names == starts
             and {b["path"] for b in new_bindings} == {RETRY_ADMIN_ROOT + "/" + n for n in names},
             "Integration validation invocation inventory is partial or expanded")
    records = []
    for binding in new_bindings:
        _require(re.fullmatch(re.escape(RETRY_ADMIN_ROOT) + r"/(focused_0[1-3]|full_01)_result\.json", binding["path"]),
                 "Unknown integration validation receipt")
        records.append((binding, _json(_read_bound(root, binding, maximum=4 * 1024**2))))
    records.sort(key=lambda pair: pair[1]["previously_consumed_seconds"])
    total, focused_seconds, full_count = old_total, 0.0, 0
    for binding, record in records:
        elapsed = record["elapsed_seconds"]
        _require(type(elapsed) in (float, int) and math.isfinite(elapsed) and elapsed > 0
                 and math.isclose(record["previously_consumed_seconds"], total, rel_tol=0, abs_tol=1e-8)
                 and record["cumulative_validation_budget_seconds"] == 13000, "Integration validation accounting is discontinuous")
        total += elapsed
        if record["phase"] == "focused":
            _require(full_count == 0 and Path(binding["path"]).name.startswith("focused_"), "Focused validation occurred after full")
            focused_seconds += elapsed
        else:
            _require(record["phase"] == "full" and Path(binding["path"]).name == "full_01_result.json" and elapsed <= 2500,
                     "Unknown or excessive full invocation")
            full_count += 1
    _require(full_count == 1 and focused_seconds <= 300 and total - old_total <= 2800 and total <= 13000
             and cert["cumulative_validation_seconds"] == total and cert["cumulative_validation_cap_seconds"] == 13000
             and math.isclose(cert["new_phase_seconds"], total - old_total, rel_tol=0, abs_tol=1e-8)
             and cert["new_focused_validation_seconds"] == focused_seconds and cert["new_full_invocation_count"] == 1,
             "Integration exceeded its additive validation allowance")
    successful = {}
    for kind in ("focused", "full"):
        binding = _normalized_bindings(root, [cert[kind + "_result"]])[0]
        _require(binding in new_bindings, "Accepted result is not a new integration invocation")
        record = next(r for b, r in records if b == binding)
        _require(record["phase"] == kind and record["success"] is True and record["returncode"] == 0
                 and record["failure"] is None and record["driver_exception"] is None
                 and record["owned_cleanup_verified"] is True and not record["cleanup_errors"]
                 and record["final_accounting_error"] is None and record["preservation_error"] is None
                 and record["failed_count"] == record["error_count"] == 0
                 and record["test_count"] == counts[kind] and record["skipped_count"] == (1 if kind == "full" else 0)
                 and record["passed_count"] == counts[kind] - record["skipped_count"]
                 and record["test_counts"] == cert["test_counts"]
                 and _normalized_bindings(root, [record["test_inventory"]]) == _normalized_bindings(root, [cert["test_inventory"]])
                 and _normalized_bindings(root, record["source_bindings"]) == current
                 == _normalized_bindings(root, record["source_bindings_after"])
                 and _normalized_bindings(root, record["helper_bindings"]) == helpers
                 == _normalized_bindings(root, record["helper_bindings_after"])
                 and _normalized_bindings(root, [record["approval"]]) == [approval_binding]
                 == _normalized_bindings(root, [record["approval_after"]])
                 and _normalized_bindings(root, [record["validation_extension"]]) == [approval_binding]
                 == _normalized_bindings(root, [record["validation_extension_after"]])
                 and _normalized_bindings(root, record["preserved_worktree_bindings_before"]) == protected
                 == _normalized_bindings(root, record["preserved_worktree_bindings_after"]),
                 "Accepted integration validation is not a successful frozen-source check")
        _require(0 < record["elapsed_seconds"] <= record["timeout_seconds"] <= (2500 if kind == "full" else 300)
                 and record["peak_rss_bytes"] <= approval["maximum_sampled_memory_bytes"]
                 and record["peak_observed_output_bytes"] + record["publication_reserve_bytes"] <= approval["maximum_new_output_bytes"]
                 and record["minimum_free_bytes"] - record["publication_reserve_bytes"] >= approval["minimum_free_disk_bytes"]
                 and record["publication_reserve_bytes"] >= monitor.FINAL_RESERVE,
                 "Accepted validation exceeded resource bounds")
        shutdown = record["shutdown"]
        observation = shutdown["telemetry"]["identity_observation_budget"]
        _require(shutdown["natural_shutdown_success"] is True and shutdown["failure"] is None
                 and shutdown["final_membership"] == [] and shutdown["owned_cleanup_verified"] is True
                 and shutdown["cleanup_errors"] == [] and 0 <= shutdown["elapsed_seconds"] <= shutdown["natural_shutdown_limit_seconds"] <= 1
                 and observation["maximum_incident_seconds"] == .05 and observation["maximum_total_seconds"] == .25
                 and observation["failed"] is False and 0 <= observation["consumed_seconds"] <= .25,
                 "Accepted validation did not prove bounded natural owned cleanup")
        stem = Path(binding["path"]).name.removesuffix("_result.json")
        for key, tested, infix in (("helper_snapshots", helpers, "_helper_"),
                                   ("implementation_snapshots", [b for b in current if b["path"] in RETRY_CHANGED_FILES], "_")):
            snapshots = _normalized_bindings(root, record[key])
            expected_snapshots = [{**b, "path": RETRY_ADMIN_ROOT + "/" + stem + infix + Path(b["path"]).name} for b in tested]
            _require(snapshots == sorted(expected_snapshots, key=lambda b: b["path"]), "Validated source/helper snapshot differs")
            for snapshot in snapshots:
                _read_bound(root, snapshot, maximum=4 * 1024**2)
        successful[kind] = record
    _require(records[-1][1] == successful["full"]
             and successful["full"]["previously_consumed_seconds"] >=
                 successful["focused"]["previously_consumed_seconds"] + successful["focused"]["elapsed_seconds"],
             "Final passing focused source did not precede the sole full run")
    return cert


def _history_guard_test_inventory(root, binding, current, helpers, counts, contract):
    binding = _normalized_bindings(root, [binding])[0]
    _require(re.fullmatch(re.escape(HISTORY_GUARD_ADMIN_ROOT) +
                         r"/(red_test_inventory|test_inventory|focused_03_test_inventory)\.json", binding["path"]),
             "Unknown history-guard test inventory")
    inventory = _json(_read_bound(root, binding, maximum=4 * 1024**2))
    _require(inventory["schema_version"] == "ball_crop_corroboration_history_guard_test_inventory/v0.1"
             and _normalized_bindings(root, inventory["source_bindings"]) == current
             and _normalized_bindings(root, inventory["helper_bindings"]) == helpers
             and inventory["producer_test_id"] == contract["test_id"], "History-guard inventory differs from tested bytes")
    focused, ignored, full = (inventory[k] for k in ("focused_repository_ids", "ignored_lifecycle_ids", "full_repository_ids"))
    _require(all(isinstance(rows, list) and all(isinstance(v, str) and v for v in rows)
                 and len(rows) == len(set(rows)) for rows in (focused, ignored, full))
             and len(focused) >= 84 and len(ignored) == 17 and len(full) == 1167 + len(focused)
             and set(focused) <= set(full) and not set(ignored) & set(full)
             and contract["test_id"] in focused,
             "History-guard test inventory drops prior coverage or the producer regression")
    _require(counts == {"repository_focused_test_count": len(focused), "ignored_lifecycle_test_count": len(ignored),
                        "full_test_count": len(full)}, "History-guard test counts differ")
    return {"focused": len(focused) + len(ignored), "full": len(full)}


def _history_guard_method(raw, contract):
    """Verify the frozen producer regression without importing or executing it."""
    tree = ast.parse(raw.decode("utf-8-sig"))
    for row in contract["ast_nodes"]:
        nodes = tree.body
        for name in row["qualified_name"].split("."):
            matches = [node for node in nodes if getattr(node, "name", None) == name]
            _require(len(matches) == 1, "Frozen producer regression is absent or ambiguous")
            node = matches[0]
            nodes = getattr(node, "body", [])
        digest = hashlib.sha256(ast.dump(node, include_attributes=False).encode("utf-8")).hexdigest()
        _require(digest == row["sha256"], "Frozen producer regression changed after RED")


def _history_guard_snapshots(root, binding, record, current, helpers, contract_binding, contract):
    stem = Path(binding["path"]).name.removesuffix("_result.json")
    for key, tested, infix in (("helper_snapshots", helpers, "_helper_"),
                               ("implementation_snapshots", [b for b in current if b["path"] in RETRY_CHANGED_FILES], "_")):
        snapshots = _normalized_bindings(root, record[key])
        expected = sorted([{**b, "path": HISTORY_GUARD_ADMIN_ROOT + "/" + stem + infix + Path(b["path"]).name}
                           for b in tested], key=lambda b: b["path"])
        _require(snapshots == expected, "History-guard tested source/helper snapshot differs")
        for snapshot in snapshots:
            raw = _read_bound(root, snapshot, maximum=4 * 1024**2)
            if key == "implementation_snapshots" and snapshot["path"].endswith("/" + stem + "_test_ball_crop_cross_detector_corroboration_release.py"):
                _history_guard_method(raw, contract)
    expected_contract = {**contract_binding, "path": HISTORY_GUARD_ADMIN_ROOT + "/" + stem + "_producer_contract.json"}
    _require(_normalized_bindings(root, [record["producer_contract_snapshot"]]) == [expected_contract],
             "Producer contract snapshot differs")
    _read_bound(root, expected_contract, maximum=1024**2)


def _history_guard_result(root, binding, record, current, helpers, protected, approval_binding, approval,
                          contract_binding, contract, inventory_binding, counts, *, red=False):
    _require(record["driver_exception"] is None and record["owned_cleanup_verified"] is True
             and record["cleanup_errors"] == [] and record["final_accounting_error"] is None
             and record["preservation_error"] is None
             and _normalized_bindings(root, record["source_bindings"]) == current
             == _normalized_bindings(root, record["source_bindings_after"])
             and _normalized_bindings(root, record["helper_bindings"]) == helpers
             == _normalized_bindings(root, record["helper_bindings_after"])
             and _normalized_bindings(root, record["preserved_worktree_bindings_before"]) == protected
             == _normalized_bindings(root, record["preserved_worktree_bindings_after"])
             and _normalized_bindings(root, [record["approval"]]) == [approval_binding]
             == _normalized_bindings(root, [record["approval_after"]])
             and _normalized_bindings(root, [record["validation_extension"]]) == [approval_binding]
             == _normalized_bindings(root, [record["validation_extension_after"]])
             and _normalized_bindings(root, [record["producer_contract"]]) == [contract_binding]
             and _normalized_bindings(root, [record["test_inventory"]]) == _normalized_bindings(root, [inventory_binding]),
             "History-guard result is not a preserved frozen-source check")
    _require(0 < record["elapsed_seconds"] <= record["timeout_seconds"] <= (2500 if record["phase"] == "full" else 300)
             and record["peak_rss_bytes"] <= approval["maximum_sampled_memory_bytes"]
             and record["peak_observed_output_bytes"] + record["publication_reserve_bytes"] <= approval["maximum_new_output_bytes"]
             and record["minimum_free_bytes"] - record["publication_reserve_bytes"] >= approval["minimum_free_disk_bytes"]
             and record["publication_reserve_bytes"] >= monitor.FINAL_RESERVE, "History-guard validation exceeded resource bounds")
    shutdown = record["shutdown"]
    observation = shutdown["telemetry"]["identity_observation_budget"]
    _require(shutdown["natural_shutdown_success"] is True and shutdown["failure"] is None
             and shutdown["final_membership"] == [] and shutdown["owned_cleanup_verified"] is True
             and shutdown["cleanup_errors"] == []
             and 0 <= shutdown["elapsed_seconds"] <= shutdown["natural_shutdown_limit_seconds"] <= 1
             and observation["maximum_incident_seconds"] == .05 and observation["maximum_total_seconds"] == .25
             and observation["failed"] is False and 0 <= observation["consumed_seconds"] <= .25,
             "History-guard validation did not prove bounded natural cleanup")
    outcome = {"test_id": contract["test_id"], "outcome": contract["expected_outcome"] if red else "success",
               "error_type": contract["expected_error_type"] if red else None,
               "error_message": contract["expected_error_message"] if red else None}
    _require(record["producer_contract_result"] == outcome, "The actual producer regression outcome differs")
    stem = Path(binding["path"]).name.removesuffix("_result.json")
    traces = {}
    for key, suffix in (("log", ".log"), ("active_test_telemetry", "_active_test.jsonl"),
                        ("lifecycle_telemetry", "_lifecycle.jsonl")):
        trace_binding = _normalized_bindings(root, [record[key]])[0]
        _require(trace_binding["path"] == HISTORY_GUARD_ADMIN_ROOT + "/" + stem + suffix,
                 "History-guard trace belongs to another invocation")
        traces[key] = _read_bound(root, trace_binding, maximum=16 * 1024**2, allow_empty=key == "lifecycle_telemetry")
    inventory = _json(_read_bound(root, inventory_binding, maximum=4 * 1024**2))
    expected_ids = ([contract["test_id"]] if red else sorted(inventory["focused_repository_ids"] + inventory["ignored_lifecycle_ids"])
                    if record["phase"] == "focused" else sorted(inventory["full_repository_ids"]))
    events = [_json(line) for line in traces["active_test_telemetry"].splitlines()]
    started_ids = [event["test_id"] for event in events if event["event"] == "start"]
    stopped_ids = [event["last_test_id"] for event in events if event["event"] == "stop"]
    actual_outcomes = [{key: event[key] for key in outcome} for event in events
                       if event["event"] == "outcome" and event["test_id"] == contract["test_id"]]
    _require(sorted(started_ids) == sorted(stopped_ids) == expected_ids and len(started_ids) == len(set(started_ids))
             and actual_outcomes == [outcome], "Raw telemetry does not establish exact producer outcome and test coverage")
    log = traces["log"].decode("utf-8", errors="replace")
    reported_counts = re.findall(r"^Ran (\d+) tests? in ", log, re.MULTILINE)
    summaries = re.findall(r"^(OK(?: \([^)]*\))?|FAILED \([^)]*\))\r?$", log, re.MULTILINE)
    skips = [line for line in log.splitlines() if " ... skipped " in line]
    _require(reported_counts and summaries and int(reported_counts[-1]) == record["test_count"]
             and summaries[-1] == record["unittest_summary"] and summaries[-1].startswith("FAILED" if red else "OK")
             and (not skips if record["phase"] == "focused" else len(skips) == 1
                  and "test_output_escape_and_symlink_traversal_are_rejected" in skips[0]
                  and "test_ball_detector_experiment_runner.PreflightTests" in skips[0]
                  and "skipped 'Directory symlinks are unavailable'" in skips[0]),
             "Raw unittest log or existing skip differs from the claimed result")
    if red:
        _require(record["phase"] == "focused" and record["validation_mode"] == "red"
                 and record["red_expected_failure_verified"] is True and record["success"] is False
                 and record["returncode"] == 1 and record["failure"] == "expected_producer_contract_red"
                 and all(record[k] == value for k, value in contract["expected_red_counts"].items()),
                 "RED did not demonstrate the exact original consumer defect")
    else:
        skipped = 1 if record["phase"] == "full" else 0
        _require(record["validation_mode"] == "green" and record["red_expected_failure_verified"] is False
                 and record["success"] is True and record["returncode"] == 0
                 and record["failure"] is None and record["failed_count"] == record["error_count"] == 0
                 and record["test_count"] == counts[record["phase"]] and record["skipped_count"] == skipped
                 and record["passed_count"] == record["test_count"] - skipped,
                 "Corrected producer regression and complete frozen tests did not pass")
    _history_guard_snapshots(root, binding, record, current, helpers, contract_binding, contract)


def _history_guard_certificate(root, manifest, scope):
    """Accept one bounded correction leaf while retaining its immutable parent."""
    correction = _json(_read_bound(root, manifest["history_guard_scope"], maximum=1024**2))
    _require(correction["schema_version"] == "ball_crop_corroboration_history_guard_correction_scope/v0.1"
             and correction["base_commit"] == HISTORY_GUARD_BASE_COMMIT and correction["study_id"] == ID
             and correction["proposal"] == manifest["history_guard_proposal"]
             and correction["scientific_scope"] == manifest["scope"] and correction["integration_scope"] == manifest["integration_scope"]
             and correction["frozen_history"] == manifest["frozen_history"]
             and correction["parent_certificate"] == HISTORY_GUARD_PARENT_CERTIFICATE,
             "History-guard correction changed scientific scope or its accepted parent")
    _read_bound(root, correction["runtime_refusal_audit"], maximum=1024**2)
    parent = _json(_read_bound(root, HISTORY_GUARD_PARENT_CERTIFICATE, maximum=4 * 1024**2))
    _require(parent["schema_version"] == "ball_crop_corroboration_retry_integration_validation/v0.1"
             and parent["status"] == "artificial_validation_passed_runtime_authority_unchanged"
             and parent["cumulative_validation_seconds"] == 11709.157999999989
             and parent["cumulative_validation_cap_seconds"] == 13000, "Accepted integration parent differs")
    cert = _json(_read_bound(root, manifest["implementation_validation"], maximum=4 * 1024**2))
    _require(cert["schema_version"] == "ball_crop_corroboration_history_guard_validation/v0.1"
             and cert["status"] == "artificial_validation_passed_runtime_authority_unchanged"
             and cert["scope"] == manifest["history_guard_scope"] and cert["proposal"] == manifest["history_guard_proposal"]
             and cert["red_expected_failure_verified"] is True and cert["parent_certificate"] == HISTORY_GUARD_PARENT_CERTIFICATE
             and _normalized_bindings(root, [cert["approval"]]) == [HISTORY_GUARD_IMPLEMENTATION_APPROVAL]
             and _normalized_bindings(root, [cert["producer_contract"]]) == [HISTORY_GUARD_PRODUCER_CONTRACT],
             "Unknown history-guard correction certificate")
    approval_binding, contract_binding = HISTORY_GUARD_IMPLEMENTATION_APPROVAL, HISTORY_GUARD_PRODUCER_CONTRACT
    approval = _json(_read_bound(root, approval_binding, maximum=4 * 1024**2))
    contract = _json(_read_bound(root, contract_binding, maximum=1024**2))
    current, before = _retry_source_transition(root, cert["source_bindings"], parent["source_bindings"])
    _require(approval["schema_version"] == "ball_crop_corroboration_history_guard_implementation_approval/v0.1"
             and approval["status"] == "approved_implementation_and_bounded_artificial_validation"
             and approval["approved_by"] == "Ryan" and isinstance(approval["user_statement"], str) and approval["user_statement"].strip()
             and approval["head"] == HISTORY_GUARD_BASE_COMMIT and set(approval["implementation_files"]) == RETRY_CHANGED_FILES
             and approval["repository_rule_path"] == "AGENTS.md"
             and approval["scope_binding"] == manifest["history_guard_scope"] and approval["proposal_binding"] == manifest["history_guard_proposal"]
             and approval["parent_certificate"] == HISTORY_GUARD_PARENT_CERTIFICATE
             and _normalized_bindings(root, approval["ancestor_source_bindings"]) == before
             and _normalized_bindings(root, approval["ancestor_protected_bindings"]) == _normalized_bindings(root, parent["preserved_worktree_bindings"])
             and approval["previously_consumed_seconds"] == 11709.157999999989 and approval["prior_cap_seconds"] == 13000
             and approval["additional_seconds"] == approval["maximum_new_phase_seconds"] == 2800
             and approval["cumulative_validation_budget_seconds"] == 15800 and approval["maximum_focused_invocations"] == 3
             and approval["maximum_focused_seconds"] == 300 and approval["maximum_full_invocations"] == 1
             and approval["maximum_full_seconds"] == 2500 and approval["closed_remainder_reusable"] is False
             and approval["maximum_sampled_memory_bytes"] == 8 * 1024**3 and approval["maximum_new_output_bytes"] == 4 * 1024**3
             and approval["minimum_free_disk_bytes"] == 50 * 1024**3
             and approval["maximum_natural_shutdown_seconds"] == approval["maximum_forced_cleanup_seconds"] == 1
             and approval["producer_regression_required"] is True
             and all(approval[k] is True for k in ("implementation_authorized", "repository_source_edits_authorized",
                      "repository_rule_edit_authorized", "ignored_validator_implementation_authorized", "artificial_validation_authorized"))
             and all(approval[k] is False for k in ("scientific_body_access_authorized", "scientific_execution_authorized",
                      "real_resource_journal_replay_authorized", "runtime_authority_or_certificate_replacement_authorized")),
             "History-guard implementation approval or closed-budget boundary differs")
    protected = _normalized_bindings(root, parent["preserved_worktree_bindings"] + [
        correction["repository_rule"], manifest["history_guard_scope"], correction["original_runtime_manifest"], correction["original_retry_approval"]])
    _require(len(protected) == 203 and len({b["path"] for b in protected}) == 203
             and protected == _normalized_bindings(root, approval["expected_preserved_bindings"])
             == _normalized_bindings(root, cert["preserved_worktree_bindings"]), "History-guard protected inventory differs")
    for binding in protected:
        _read_bound(root, binding, maximum=4 * 1024**2, allow_empty=True)
    prior = _normalized_bindings(root, parent["validation_results"])
    _require(len(prior) == 17 and prior == _normalized_bindings(root, cert["prior_validation_results"])
             == _normalized_bindings(root, approval["prior_validation_results"])
             and approval["prior_consumption_records"] == parent["consumption_records"],
             "History-guard correction dropped prior validation evidence")
    for binding in prior:
        _read_bound(root, binding, maximum=4 * 1024**2)
    _require(contract["schema_version"] == "ball_crop_corroboration_history_guard_producer_contract/v0.1"
             and _normalized_bindings(root, [contract["approval"]]) == [approval_binding]
             and contract["test_id"] == HISTORY_GUARD_PRODUCER_TEST
             and contract["test_file"] == "tests/test_ball_crop_cross_detector_corroboration_release.py"
             and contract["expected_outcome"] == "failure" and contract["expected_error_type"] == "AssertionError"
             and contract["expected_error_message"] == "Producer completion rejected by frozen retry guard: Exact failed same-unit attempt and charge required"
             and contract["expected_red_counts"] == {"test_count": 1, "passed_count": 0, "skipped_count": 0, "failed_count": 1, "error_count": 0}
             and contract["unmodified_contract_fields"] == ["failure", "success", "exit_code", "log_path", "worker_result"]
             and _normalized_bindings(root, [contract["red_consumer_source"]])[0] ==
                 next(b for b in before if b["path"] == "src/ball_tracking/crop_cross_detector_corroboration_release.py")
             and _normalized_bindings(root, contract["producer_bindings"]) ==
                 [b for b in before if b["path"] in ("src/ball_tracking/crop_retention_monitor.py", "src/ball_tracking/crop_retention_resources.py")],
             "Frozen producer/consumer regression contract differs")
    _history_guard_method(_read_bound(root, next(b for b in current if b["path"] == contract["test_file"]), maximum=4 * 1024**2), contract)
    helpers = _normalized_bindings(root, cert["helper_bindings"])
    _require(len(helpers) == 4 and {b["path"] for b in helpers} ==
             {HISTORY_GUARD_ADMIN_ROOT + "/" + n for n in ("validate.py", "finalize_validation.py", "lifecycle.py", "test_lifecycle.py")},
             "History-guard helper inventory differs")
    for binding in helpers:
        _read_bound(root, binding, maximum=1024**2)
        if Path(binding["path"]).name in ("lifecycle.py", "test_lifecycle.py"):
            ancestor = next(b for b in parent["helper_bindings"] if Path(b["path"]).name == Path(binding["path"]).name)
            _require((binding["sha256"], binding["size_bytes"]) == (ancestor["sha256"], ancestor["size_bytes"]), "Accepted lifecycle behavior changed")
    counts = _history_guard_test_inventory(root, cert["test_inventory"], current, helpers, cert["test_counts"], contract)
    directory = _safe(root, HISTORY_GUARD_ADMIN_ROOT)
    names = {p.name for p in directory.glob("*_result.json")}
    starts = {p.name.replace("_started.json", "_result.json") for p in directory.glob("*_started.json")}
    bindings = _normalized_bindings(root, cert["new_validation_results"])
    _require(3 <= len(bindings) <= 4 and names == starts and {b["path"] for b in bindings} ==
             {HISTORY_GUARD_ADMIN_ROOT + "/" + n for n in names}
             and all(re.fullmatch(r"(focused_0[1-3]|full_01)_result\.json", n) for n in names),
             "History-guard invocation inventory is partial or expanded")
    records = [(b, _json(_read_bound(root, b, maximum=4 * 1024**2))) for b in bindings]
    records.sort(key=lambda pair: pair[1]["previously_consumed_seconds"])
    evidence = cert["new_invocation_evidence"]
    _require(len(evidence) == len(records) and
             _normalized_bindings(root, [row["result"] for row in evidence]) == bindings,
             "History-guard invocation evidence is incomplete")
    for binding, record in records:
        row = next(row for row in evidence if _normalized_bindings(root, [row["result"]])[0] == binding)
        stem = Path(binding["path"]).name.removesuffix("_result.json")
        started_binding = _normalized_bindings(root, [row["started"]])[0]
        _require(row["name"] == stem and started_binding["path"] == HISTORY_GUARD_ADMIN_ROOT + "/" + stem + "_started.json",
                 "History-guard started authority belongs to another invocation")
        started = _json(_read_bound(root, started_binding, maximum=4 * 1024**2))
        _require(started and all(key in record and record[key] == value for key, value in started.items())
                 and _normalized_bindings(root, row["helper_snapshots"]) == _normalized_bindings(root, record["helper_snapshots"])
                 and _normalized_bindings(root, [row["test_inventory"]]) == _normalized_bindings(root, [record["test_inventory"]])
                 and _normalized_bindings(root, [row["producer_contract_snapshot"]]) ==
                     _normalized_bindings(root, [record["producer_contract_snapshot"]]),
                 "Started authority or invocation snapshot evidence differs from its result")
        for key, suffix in (("log", ".log"), ("active_test_telemetry", "_active_test.jsonl"),
                            ("lifecycle_telemetry", "_lifecycle.jsonl")):
            trace = _normalized_bindings(root, [record[key]])[0]
            _require(trace["path"] == HISTORY_GUARD_ADMIN_ROOT + "/" + stem + suffix,
                     "Preserved validation trace belongs to another invocation")
            _read_bound(root, trace, maximum=16 * 1024**2, allow_empty=key == "lifecycle_telemetry")
    total, focused_seconds, full_count, consumed = 11709.157999999989, 0.0, 0, []
    for binding, record in records:
        elapsed = record["elapsed_seconds"]
        _require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed > 0
                 and math.isclose(record["previously_consumed_seconds"], total, rel_tol=0, abs_tol=1e-8)
                 and record["cumulative_validation_budget_seconds"] == 15800, "History-guard consumed budget is discontinuous")
        total += elapsed
        consumed.append({"binding": binding, "success": record["success"], "failure": record["failure"],
                         "elapsed_seconds": elapsed, "cumulative_seconds": total})
        if record["phase"] == "focused":
            _require(full_count == 0 and Path(binding["path"]).name.startswith("focused_"), "History-guard focus occurred after full")
            focused_seconds += elapsed
        else:
            _require(record["phase"] == "full" and Path(binding["path"]).name == "full_01_result.json" and elapsed <= 2500,
                     "Unexpected history-guard full invocation")
            full_count += 1
    declared_consumed = [{**r, "binding": _normalized_bindings(root, [r["binding"]])[0]} for r in cert["new_consumption_records"]]
    _require(consumed == declared_consumed and full_count == 1 and focused_seconds <= 300
             and total - 11709.157999999989 <= 2800 and total <= 15800
             and cert["previously_consumed_seconds"] == 11709.157999999989
             and cert["cumulative_validation_seconds"] == total and cert["cumulative_validation_cap_seconds"] == 15800
             and math.isclose(cert["new_phase_seconds"], total - 11709.157999999989, rel_tol=0, abs_tol=1e-8)
             and cert["new_focused_validation_seconds"] == focused_seconds and cert["new_full_invocation_count"] == 1,
             "History-guard correction reset or exceeded its additive allowance")
    red_binding = _normalized_bindings(root, [cert["red_result"]])[0]
    _require(red_binding["path"] == HISTORY_GUARD_ADMIN_ROOT + "/focused_01_result.json" and records[0][0] == red_binding,
             "Correction lacks the original first RED invocation")
    red = records[0][1]
    red_sources = _normalized_bindings(root, red["source_bindings"])
    before_by_path = {b["path"]: b for b in before}
    _require(len(red_sources) == 187 and {b["path"] for b in red_sources} == set(before_by_path)
             and all(b["path"] == contract["test_file"] or b == before_by_path[b["path"]] for b in red_sources),
             "RED did not test the original unfixed consumer")
    _history_guard_test_inventory(root, red["test_inventory"], red_sources, helpers, red["test_counts"], contract)
    _history_guard_result(root, red_binding, red, red_sources, helpers, protected, approval_binding, approval,
                          contract_binding, contract, red["test_inventory"], counts, red=True)
    accepted = {}
    for phase in ("focused", "full"):
        binding = _normalized_bindings(root, [cert[phase + "_result"]])[0]
        _require(binding in bindings and binding != red_binding, "Accepted GREEN/full result is outside the correction phase")
        record = next(r for b, r in records if b == binding)
        _require(record["phase"] == phase and record["test_counts"] == cert["test_counts"]
                 and _normalized_bindings(root, [record["red_result"]]) == [red_binding], "Accepted correction result lacks its RED predecessor")
        _history_guard_result(root, binding, record, current, helpers, protected, approval_binding, approval,
                              contract_binding, contract, cert["test_inventory"], counts)
        accepted[phase] = (binding, record)
    _require(records[-1] == accepted["full"] and
             _normalized_bindings(root, [accepted["full"][1]["focused_result"]]) == [accepted["focused"][0]]
             and accepted["full"][1]["previously_consumed_seconds"] >=
                 accepted["focused"][1]["previously_consumed_seconds"] + accepted["focused"][1]["elapsed_seconds"],
             "Sole full run lacks its passing producer-backed GREEN gate")
    review = _json(_read_bound(root, accepted["full"][1]["implementation_review"], maximum=4 * 1024**2))
    _require(review["schema_version"] == "ball_crop_corroboration_history_guard_review/v0.1"
             and review["status"] == "independent_review_passed" and review["findings"] == []
             and review["producer_consumer_contract_review_passed"] is True
             and _normalized_bindings(root, [review["producer_contract"]]) == [contract_binding]
             and _normalized_bindings(root, [review["red_result"]]) == [red_binding]
             and _normalized_bindings(root, [review["test_inventory"]]) == _normalized_bindings(root, [cert["test_inventory"]])
             and _normalized_bindings(root, review["source_bindings"]) == current
             and _normalized_bindings(root, review["helper_bindings"]) == helpers,
             "Independent producer/consumer review is absent or stale")
    return cert


def _metadata(root, manifest_path=MANIFEST_PATH):
    if str(manifest_path).replace("\\", "/") in (RETRY_MANIFEST_PATH, HISTORY_GUARD_MANIFEST_PATH):
        return _retry_metadata(root, manifest_path)
    root = Path(root).resolve()
    _require(str(manifest_path).replace("\\", "/") == MANIFEST_PATH, "Only the exact future manifest is allowed")
    path = _safe(root, MANIFEST_PATH)
    if not path.is_file():
        raise PermissionError("Real corroboration execution requires separately approved exact runtime authority, tested certificate and clean-commit checkpoint")
    raw = _read_admin(root, MANIFEST_PATH, 1024**2)
    manifest = _validate_manifest(_json(raw))
    scope = _json(_read_bound(root, manifest["scope"], maximum=4 * 1024**2))
    validate_scope(scope, production=True)
    _read_bound(root, manifest["proposal"], maximum=1024**2)
    approval = _json(_read_bound(root, manifest["execution_approval"], maximum=1024**2))
    _require(approval.get("schema_version") == "ball_crop_corroboration_execution_approval/v0.1"
             and approval.get("study_id") == ID and approval.get("approved_by", "").lower() == "ryan"
             and approval.get("scope") == manifest["scope"] and approval.get("proposal") == manifest["proposal"]
             and all(approval.get(k) is True for k in ("scientific_execution_authorized", "administrative_history_verification_authorized",
                       "new_verified_media_presentation_authorized", "release_checkpoint_authorized"))
             and isinstance(approval.get("user_statement"), str) and bool(approval["user_statement"].strip()),
             "Separate real execution approval is absent or differs")
    _require(_git(root, "status", "--porcelain") == "", "Release requires clean committed work; preserve dirty files")
    commit = _git(root, "rev-parse", "HEAD")
    require_digest(commit, "actual release commit", 40)
    _require(commit != BASE_COMMIT and _git(root, "branch", "--show-current").startswith("codex/"), "Expected clean implementation feature branch")
    _git(root, "merge-base", "--is-ancestor", BASE_COMMIT, commit)
    for name in (MANIFEST_PATH, APPROVAL_PATH, SCOPE_PATH, PROPOSAL_PATH):
        _require(_git(root, "ls-files", "--", name) == name, "Release authority must be committed")
    cert = _certificate(root, manifest, scope)
    _require_tracked(root, [r["path"] for r in _normalized_bindings(root, cert["source_bindings"])] +
                     [r["path"] for r in scope["preserved_worktree_bindings"]] +
                     [MANIFEST_PATH, APPROVAL_PATH, SCOPE_PATH, PROPOSAL_PATH])
    for row in scope["preserved_worktree_bindings"]:
        _read_bound(root, row, maximum=4 * 1024**2)
    checkpoint = monitor._read_record(_safe(root, CHECKPOINT_PATH), limit=1024**2)
    _require(checkpoint.get("schema_version") == "ball_crop_corroboration_post_commit_checkpoint/v0.1"
             and checkpoint.get("commit") == commit and checkpoint.get("manifest") == _binding(MANIFEST_PATH, raw)
             and checkpoint.get("execution_approval") == manifest["execution_approval"]
             and checkpoint.get("implementation_validation") == manifest["implementation_validation"]
             and checkpoint.get("scope") == manifest["scope"] and checkpoint.get("clean") is True,
             "Missing or stale actual clean-commit checkpoint")
    frozen = _json(_read_bound(root, manifest["frozen_history"], maximum=16 * 1024**2))
    _require(frozen["preserved_history"] == scope["preserved_history"] and isinstance(frozen["preserved_files"], list)
             and len({r["path"] for r in frozen["preserved_files"]}) == len(frozen["preserved_files"]), "Frozen administrative history differs")
    _history_authority(root, frozen, scope)
    original = next(r for r in scope["administrative_binding_sources"] if r["path"] == "configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json")
    limits = _json(_read_bound(root, original, maximum=4 * 1024**2))["resource_limits"]
    for name in ("src/ball_tracking/crop_retention_monitor.py", "src/ball_tracking/crop_retention_resources.py"):
        _read_bound(root, next(r for r in scope["administrative_binding_sources"] if r["path"] == name), maximum=1024**2)
    for row in scope["existing_scientific_files"]:
        _require(_stat(_safe(root, row["path"])) == row["preparation_metadata"], "Scientific metadata differs from frozen scope")
    for name in scope["prediction_embargoes"]:
        _require(not _safe(root, name).exists(), "Original prediction embargo changed")
    return {"root": root, "scope": scope, "manifest": manifest, "manifest_binding": _binding(MANIFEST_PATH, raw),
            "commit": commit, "certificate": cert, "history": frozen, "limits": limits,
            "policy": monitor.monitoring_policy(limits), "output_root": _safe(root, OUTPUT_ROOT)}


def _retry_metadata(root, manifest_path=RETRY_MANIFEST_PATH):
    """The new authority is additive; never reinterpret the consumed v0.1 route."""
    root = Path(root).resolve()
    manifest_path = str(manifest_path).replace("\\", "/")
    corrected = manifest_path == HISTORY_GUARD_MANIFEST_PATH
    _require(manifest_path in (RETRY_MANIFEST_PATH, HISTORY_GUARD_MANIFEST_PATH), "Only the exact retry manifest is allowed")
    approval_path = HISTORY_GUARD_APPROVAL_PATH if corrected else RETRY_APPROVAL_PATH
    checkpoint_path = HISTORY_GUARD_CHECKPOINT_PATH if corrected else RETRY_CHECKPOINT_PATH
    base_commit = HISTORY_GUARD_BASE_COMMIT if corrected else RETRY_BASE_COMMIT
    if not _safe(root, manifest_path).is_file():
        raise PermissionError("Scientific retry requires its separate exact authority, tested certificate and clean checkpoint")
    raw = _read_admin(root, manifest_path, 1024**2)
    manifest = _retry_manifest(_json(raw))
    _require((manifest["schema_version"] == "ball_crop_corroboration_retry_release_manifest/v0.2") == corrected,
             "Retry manifest version does not match its authority path")
    correction = None
    if corrected:
        correction = _json(_read_bound(root, manifest["history_guard_scope"], maximum=1024**2))
        _read_bound(root, manifest["history_guard_proposal"], maximum=1024**2)
        prior_retry = _retry_manifest(_json(_read_bound(root, correction["original_runtime_manifest"], maximum=1024**2)))
        _read_bound(root, correction["original_retry_approval"], maximum=1024**2)
        _require(prior_retry["schema_version"] == "ball_crop_corroboration_retry_release_manifest/v0.1"
                 and prior_retry["retry_approval"] == correction["original_retry_approval"]
                 and prior_retry["implementation_validation"] == HISTORY_GUARD_PARENT_CERTIFICATE
                 and all(manifest[k] == prior_retry[k] for k in ("scope", "proposal", "execution_approval", "integration_scope",
                                                                "integration_proposal", "frozen_history")),
                 "History-guard correction changed its prior runtime/scientific authority")
    retry = _json(_read_bound(root, manifest["integration_scope"], maximum=4 * 1024**2))
    _read_bound(root, manifest["integration_proposal"], maximum=1024**2)
    _require(retry["schema_version"] == "ball_crop_corroboration_retry_integration_proposal/v0.1"
             and retry["proposal"] == manifest["integration_proposal"], "Frozen integration scope differs")
    original_binding = next(b for b in retry["evidence_reuse"]["original_runtime_package"] if b["path"] == MANIFEST_PATH)
    original = _validate_manifest(_json(_read_bound(root, original_binding, maximum=1024**2)))
    _require(all(manifest[k] == original[k] for k in ("scope", "proposal", "execution_approval")),
             "Retry changed original scientific authority")
    scope = _json(_read_bound(root, manifest["scope"], maximum=4 * 1024**2))
    validate_scope(scope, production=True)
    _read_bound(root, manifest["proposal"], maximum=1024**2)
    old_approval = _json(_read_bound(root, manifest["execution_approval"], maximum=1024**2))
    _require(old_approval["study_id"] == ID and old_approval["scope"] == manifest["scope"]
             and old_approval["proposal"] == manifest["proposal"] and old_approval["scientific_execution_authorized"] is True,
             "Original scientific approval differs")
    approval = _json(_read_bound(root, manifest["retry_approval"], maximum=1024**2))
    _require(approval["schema_version"] == ("ball_crop_corroboration_retry_execution_approval/v0.2" if corrected
                                          else "ball_crop_corroboration_retry_execution_approval/v0.1")
             and approval["study_id"] == ID and approval["approved_by"] == "Ryan"
             and isinstance(approval["user_statement"], str) and approval["user_statement"].strip()
             and approval["scope"] == manifest["scope"] and approval["original_execution_approval"] == manifest["execution_approval"]
             and approval["integration_scope"] == manifest["integration_scope"]
             and approval["integration_proposal"] == manifest["integration_proposal"]
             and approval["implementation_validation"] == manifest["implementation_validation"]
             and approval["failed_attempt_audit"] == retry["evidence_reuse"]["failed_attempt_audit"]
             and approval["predecessor_attempt_id"] == RETRY_PREDECESSOR and approval["unit_key"] == UNIT_KEY
             and type(approval["maximum_attempts"]) is int and approval["maximum_attempts"] == 1
             and approval["maximum_retry_seconds"] == RETRY_MAX_SECONDS and approval["fresh_budget"] is False
             and type(approval["new_verified_media_presentation_authorized"]) is bool
             and all(approval[k] is True for k in ("scientific_execution_authorized", "administrative_history_verification_authorized",
                                                  "release_checkpoint_authorized")),
             "Separate one-time scientific retry approval is absent or differs")
    if corrected:
        _require(all(approval[k] == manifest[k] for k in ("history_guard_scope", "history_guard_proposal"))
                 and all(approval[k] == correction[k] for k in ("parent_certificate", "original_runtime_manifest", "original_retry_approval")),
                 "Corrected runtime approval lacks its preserved authority lineage")
    _require(_git(root, "status", "--porcelain") == "", "Retry release requires clean committed work; preserve dirty files")
    commit = _git(root, "rev-parse", "HEAD")
    require_digest(commit, "actual retry release commit", 40)
    _require(commit != base_commit and _git(root, "branch", "--show-current") == "codex/ball-detector-baseline",
             "Expected clean tested retry feature branch")
    _git(root, "merge-base", "--is-ancestor", base_commit, commit)
    authorities = (RETRY_MANIFEST_PATH, RETRY_APPROVAL_PATH, RETRY_SCOPE_PATH, RETRY_PROPOSAL_PATH,
                   MANIFEST_PATH, APPROVAL_PATH, SCOPE_PATH, PROPOSAL_PATH)
    if corrected:
        authorities += (HISTORY_GUARD_MANIFEST_PATH, HISTORY_GUARD_APPROVAL_PATH, HISTORY_GUARD_SCOPE_PATH, "AGENTS.md")
    for name in authorities:
        _require(_git(root, "ls-files", "--", name) == name, "Retry and original authority must be committed")
    cert = (_history_guard_certificate if corrected else _retry_certificate)(root, manifest, scope)
    _require_tracked(root, [b["path"] for b in _normalized_bindings(root, cert["source_bindings"])]
                     + [b["path"] for b in _normalized_bindings(root, cert["preserved_worktree_bindings"])] + list(authorities))
    checkpoint = monitor._read_record(_safe(root, checkpoint_path), limit=1024**2)
    _require(checkpoint["schema_version"] == ("ball_crop_corroboration_retry_post_commit_checkpoint/v0.2" if corrected
                                            else "ball_crop_corroboration_retry_post_commit_checkpoint/v0.1")
             and checkpoint["commit"] == commit and checkpoint["clean"] is True
             and checkpoint["manifest"] == _binding(manifest_path, raw)
             and all(checkpoint[k] == manifest[k] for k in ("retry_approval", "implementation_validation", "scope",
                                                           "integration_scope", "frozen_history"))
             and checkpoint["predecessor_attempt_id"] == RETRY_PREDECESSOR
             and checkpoint["original_baseline_bytes"] == RETRY_BASELINE_BYTES,
             "Missing or stale actual clean retry checkpoint")
    if corrected:
        _require(all(checkpoint[k] == manifest[k] for k in ("history_guard_scope", "history_guard_proposal"))
                 and checkpoint["parent_certificate"] == HISTORY_GUARD_PARENT_CERTIFICATE,
                 "Corrected clean checkpoint lacks its exact lineage")
    frozen = _json(_read_bound(root, manifest["frozen_history"], maximum=16 * 1024**2))
    _retry_history_authority(root, frozen, scope, retry)
    original_limits = next(b for b in scope["administrative_binding_sources"]
                           if b["path"] == "configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json")
    limits = _json(_read_bound(root, original_limits, maximum=4 * 1024**2))["resource_limits"]
    for name in ("src/ball_tracking/crop_retention_monitor.py", "src/ball_tracking/crop_retention_resources.py"):
        _read_bound(root, next(b for b in scope["administrative_binding_sources"] if b["path"] == name), maximum=1024**2)
    for row in scope["existing_scientific_files"]:
        _require(_stat(_safe(root, row["path"])) == row["preparation_metadata"], "Scientific metadata differs from original scope")
    for name in scope["prediction_embargoes"]:
        _require(not _safe(root, name).exists(), "Original prediction embargo changed")
    return {"root": root, "scope": scope, "retry": retry, "retry_approval": approval,
            "retry_approval_binding": manifest["retry_approval"], "manifest": manifest,
             "manifest_path": manifest_path, "manifest_binding": _binding(manifest_path, raw), "retry_approval_path": approval_path,
            "commit": commit, "certificate": cert, "history": frozen, "limits": limits,
            "policy": monitor.monitoring_policy(limits), "output_root": _safe(root, OUTPUT_ROOT)}


def _retry_history_authority(root, frozen, scope, retry):
    expected = retry["retry_design"]["exact_starting_history"]
    history = {"resource_event_count": expected["events"], "resource_tip": expected["tip"],
               "closed_attempts": expected["closed_attempts"], "successes": expected["successes"],
               "historic_failure_ids": expected["failed_attempt_ids"], "consumed_seconds": expected["consumed_seconds"],
               "remaining_seconds": expected["remaining_seconds"]}
    baseline_binding = retry["retry_design"]["output_accounting"]["original_frozen_history"]
    preservation_binding = {"path": "data/outputs/t/corroboration_ownership_repair_3233d2c/preservation.json",
                            "size_bytes": 2348263, "sha256": "93a34635ec395f4f8a7fba86107bef43877566b874a667506329faef87cad08d"}
    _require(frozen["schema_version"] == "ball_crop_corroboration_retry_frozen_history/v0.1"
             and frozen["preserved_history"] == history and frozen["original_baseline_binding"] == baseline_binding
             and frozen["original_baseline_bytes"] == RETRY_BASELINE_BYTES
             and frozen["failed_attempt_audit"] == retry["evidence_reuse"]["failed_attempt_audit"]
             and frozen["preservation_source"] == preservation_binding, "Retry frozen-history authority differs")
    baseline = _json(_read_bound(root, baseline_binding, maximum=4 * 1024**2))
    preservation = _json(_read_bound(root, preservation_binding, maximum=4 * 1024**2))
    _require(len(baseline["preserved_files"]) == 6903 and _baseline_bytes(baseline["preserved_files"]) == RETRY_BASELINE_BYTES
             and len(frozen["preserved_files"]) == 6917 and frozen["preserved_files"] == preservation["output_root_files"]
             and frozen["preserved_directories"] == preservation["output_root_directories"]
             and frozen["external_preserved_files"] == preservation["external_preserved_files"] == baseline["external_preserved_files"]
             and frozen["protection"] == preservation["protection"] == baseline["protection"],
             "Retry rebased original byte accounting or changed preservation")
    original_files = {b["path"]: b for b in baseline["preserved_files"]}
    current_files = {b["path"]: b for b in frozen["preserved_files"]}
    _require(len(current_files) == 6917 and all(current_files.get(name) == row for name, row in original_files.items())
             and set(baseline["preserved_directories"]) <= set(frozen["preserved_directories"]),
             "Retry preservation drops pre-failure evidence")
    audit = _json(_read_bound(root, frozen["failed_attempt_audit"], maximum=1024**2))
    _require(audit["attempt_id"] == RETRY_PREDECESSOR and audit["status"] == "failed_before_worker_scientific_access_no_retry"
             and audit["current_event_count"] == 3334 and audit["current_resource_tip"] == expected["tip"]
             and audit["charged_seconds"] == 1.125 and audit["consumed_seconds"] == expected["consumed_seconds"]
             and audit["scientific_output_directory_created"] is False and audit["scientific_worker_access_reached"] is False,
             "Failed scientific startup evidence differs")
    _history_authority(root, frozen, scope)


def _history_authority(root, frozen, scope):
    """Verify historical administrative authorities; all scientific paths inert."""
    old = _json(_read_bound(root, PRIOR_HISTORY, maximum=4 * 1024**2))
    _require(old["schema_version"] == "ball_crop_path_confidence_mean_frozen_history/v0.1"
             and frozen["external_preserved_files"] == old["external_preserved_files"]
             and len(frozen["external_preserved_files"]) == 18
             and frozen["protection"] == old["protection"], "Earlier external preservation authority differs")
    previous = {r["path"]: r for r in old["preserved_files"]}
    current = {r["path"]: r for r in frozen["preserved_files"]}
    _require(all(current.get(name) == row for name, row in previous.items())
             and set(old["preserved_directories"]) <= set(frozen["preserved_directories"]),
             "New frozen inventory dropped or changed preserved history")
    bound = next(r for r in scope["administrative_binding_sources"] if r["path"] == MEAN_RESULT)
    mean = _json(_read_bound(root, bound, maximum=MAX_RECEIPT_BYTES))
    metadata, artifacts = mean["artifact_metadata"], mean["artifacts"]
    _require(len(metadata) == len(artifacts) == 636 and len({r["path"] for r in metadata}) == 636
             and {r["path"] for r in metadata} == {r["path"] for r in artifacts}
             and all(current.get(row["path"]) == row for row in metadata), "Reviewed mean artifact inventory differs")
    for row in old["human_review_bindings"]:
        _read_bound(root, row, maximum=MAX_RECEIPT_BYTES)
    # These are explicitly administrative completion receipts, not scientific
    # output bodies. The old pinned snapshot supplies their immutable hashes.
    for row in old["administrative_attempt_bindings"]:
        if row["path"].endswith(".result.json"):
            _read_bound(root, row, maximum=MAX_RECEIPT_BYTES)


def _inventory(root):
    """Bounded metadata-only inventory, including empty ordinary directories."""
    target = _safe(root, OUTPUT_ROOT)
    _require(target.is_dir(), "Preserved output root missing")
    deadline = time.monotonic() + 10.0
    files, directories = {}, {OUTPUT_ROOT}
    def fail(error):
        raise error
    for folder, dirs, names in os.walk(target, followlinks=False, onerror=fail):
        _require(time.monotonic() < deadline and len(files) + len(directories) < 100000,
                 "Preservation metadata scan exceeded its bound")
        for name in dirs + names:
            relative = (Path(folder) / name).relative_to(root).as_posix()
            path = _safe(root, relative)
            if name in dirs:
                _require(path.is_dir(), "Preserved directory changed during scan")
                directories.add(relative)
            else:
                files[relative] = _stat(path)
    _safe(root, OUTPUT_ROOT)
    return files, directories


def _preserved(context, phase="before", attempt_id=None):
    _require(phase in ("before", "worker", "completed"), "Unknown preservation phase")
    history, root = context["history"], context["root"]
    history_start = (history["preserved_history"]["resource_event_count"] if context.get("retry") is not None
                     else context["scope"]["preserved_history"]["resource_event_count"])
    rows, old_dirs = history["preserved_files"], history["preserved_directories"]
    for row in history["external_preserved_files"]:
        _require(_stat(_safe(root, row["path"])) == {k: row[k] for k in ("size_bytes", "mtime_ns", "device", "inode")},
                 "Prior external review metadata changed")
    protection = history["protection"]
    _require(len(protection["sealed_holdouts_metadata_only"]) == 3 and
             set(context["scope"]["prediction_embargoes"]) <= set(protection["preserved_absent_paths"]),
             "Sealed holdout or prediction embargo scope differs")
    for name in protection["preserved_absent_paths"]:
        _require(not _safe(root, name).exists(), "Protected absent path was created")
    _require(rows and len(rows) == len({r["path"].casefold() for r in rows}) and old_dirs
             and len(old_dirs) == len({p.casefold() for p in old_dirs}) and OUTPUT_ROOT in old_dirs,
             "Complete unique preservation inventory required")
    actual, directories = _inventory(root)
    old = {row["path"]: {k: row[k] for k in ("size_bytes", "mtime_ns", "device", "inode")} for row in rows}
    _require(all(name.startswith(OUTPUT_ROOT + "/") and actual.get(name) == value for name, value in old.items())
             and set(old_dirs) <= directories, "Preserved file/directory metadata changed")
    if phase == "before":
        _require(attempt_id is None and set(actual) == set(old) and directories == set(old_dirs),
                 "Frozen output inventory is partial or changed")
        return
    _require(isinstance(attempt_id, str) and re.fullmatch(r"[0-9a-f]{32}", attempt_id), "Invalid preservation attempt")
    prefix = OUTPUT_ROOT + "/attempts/" + attempt_id
    extra_files = set(actual) - set(old)
    exact = {prefix + suffix for suffix in (".reservation.json", ".completion.json", ".monitoring_policy.json",
                                           ".log", ".start", ".result.json")}
    if phase == "worker":
        exact.add(OUTPUT_ROOT + "/supervisor.lock")
    declared = {OUTPUT_DIR + "/" + r["path"] for r in context["scope"]["outputs"]["files"]}
    event_prefix = OUTPUT_ROOT + "/resource_events/"
    suffix = []
    for name in extra_files:
        if phase == "worker" and re.fullmatch(re.escape(event_prefix) + r"\.pending_([0-9]{8})\.json_[0-9a-f]{32}", name):
            _require(int(name.split(".pending_")[1][:8]) >= history_start,
                     "Pending publication overwrites preserved event")
            continue
        if name.startswith(event_prefix) and re.fullmatch(r"[0-9]{8}\.json", name[len(event_prefix):]):
            suffix.append(int(name[len(event_prefix):-5]))
            continue
        scanner = re.fullmatch(re.escape(prefix) + r"\.monitor/(owned\.start|[0-9]{6}\.(request|response)\.json)", name)
        if phase == "worker":
            scanner = scanner or re.fullmatch(re.escape(prefix) + r"\.monitor/\.pending_[0-9]{6}\.(request|response)\.json_[0-9a-f]{32}", name)
        temporary = name.startswith(prefix + ".temp/")
        generated_temp = phase == "worker" and re.fullmatch(re.escape(OUTPUT_DIR) + r"/tmp/[0-9a-f]{32}\.mp4", name)
        _require(name in exact or name in declared or scanner or temporary or generated_temp,
                 "Undeclared output-root addition")
    start = history_start
    _require(suffix and sorted(suffix) == list(range(start, start + len(suffix))), "Noncontiguous new resource suffix")
    allowed_dirs = set(old_dirs)
    for name in extra_files | declared:
        parent = Path(name).parent.as_posix()
        while parent.startswith(OUTPUT_ROOT):
            allowed_dirs.add(parent)
            if parent == OUTPUT_ROOT:
                break
            parent = Path(parent).parent.as_posix()
    allowed_dirs.update((prefix + ".monitor", prefix + ".temp"))
    _require(all(name in allowed_dirs or name.startswith(prefix + ".temp/") for name in directories),
             "Undeclared output-root directory")
    if phase == "completed":
        _require(declared <= set(actual) and {prefix + s for s in (".reservation.json", ".completion.json",
                 ".monitoring_policy.json", ".log", ".start", ".result.json")} <= set(actual),
                 "Completed output/owned-attempt inventory incomplete")


def _baseline_bytes(rows):
    identities = {}
    for row in rows:
        key = (row["device"], row["inode"])
        count, maximum = identities.get(key, (0, 0))
        identities[key] = (count + 1, max(maximum, row["size_bytes"]))
    return sum(count * maximum for count, maximum in identities.values())


def validate_return(result, context, attempt_id):
    """Parent checks transported facts and filesystem metadata, never bodies."""
    _require(len(_json_bytes(result)) <= MAX_RECEIPT_BYTES and result["schema_version"] == "ball_crop_corroboration_worker_result/v0.1"
             and result["study_id"] == ID and result["attempt_id"] == attempt_id and result["unit_key"] == UNIT_KEY
             and result["commit"] == context["commit"] and result["scope_content_sha256"] == canonical_sha256(context["scope"])
             and result["artificial_only"] is False and result["scientific_input_count"] == 190, "Worker receipt identity differs")
    expected = {OUTPUT_DIR + "/" + row["path"]: row["maximum_bytes"] for row in context["scope"]["outputs"]["files"]}
    artifacts, metadata = result["artifacts"], result["artifact_metadata"]
    _require(len(artifacts) == len(metadata) == 342 and {r["path"] for r in artifacts} == set(expected)
             and {r["path"] for r in metadata} == set(expected), "Returned output inventory differs")
    by_name = {r["path"]: r for r in metadata}
    for b in artifacts:
        require_digest(b["sha256"], "output digest", 64)
        _require(type(b["size_bytes"]) is int and 0 < b["size_bytes"] <= expected[b["path"]]
                 and by_name[b["path"]]["size_bytes"] == b["size_bytes"]
                 and _stat(_safe(context["root"], b["path"])) == {k: v for k, v in by_name[b["path"]].items() if k != "path"},
                 "Completed artifact metadata changed")
    selected = {OUTPUT_DIR + f"/selection/{w['window_id']}/observations.json" for w in context["scope"]["windows"]}
    _require(len(result["selection_bindings"]) == 6 and {r["path"] for r in result["selection_bindings"]} == selected
             and all(b in artifacts for b in result["selection_bindings"]), "Incomplete selection seal")
    summary = result["summary"]
    _require(_binding(OUTPUT_DIR + "/summary.json", _json_bytes(summary)) in artifacts,
             "Transported summary is not the published bound artifact")
    _require(summary["study_id"] == ID and summary["artificial_only"] is False
             and all(summary[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate"))
             and len(summary["windows"]) == len(summary["reviews"]) == 6
             and {w["window_id"] for w in summary["windows"]} == {w["window_id"] for w in context["scope"]["windows"]}
             and {p["purpose"] for p in summary["pools"]} == set(evaluation.POOLS), "Incomplete compact summary")
    _validate_summary(summary, context["scope"])
    rows = context["scope"]["existing_scientific_files"]
    log = result["scientific_access_log"]
    expected_access = {r["path"]: {"path": r["path"], "role": r["role"], "phase": r["first_allowed_phase"]} for r in rows}
    _require(len(log) == 190 and {r["path"] for r in log} == set(expected_access)
             and all(r == expected_access[r["path"]] for r in log)
             and [r["phase"] for r in log] == ["selection"] * 12 + ["evaluation"] * 28 + ["review"] * 150,
             "Worker scientific access is incomplete, expanded or out of phase")
    for w in context["scope"]["windows"]:
        r = next(r for r in summary["reviews"] if r["window_id"] == w["window_id"])
        _require(r["frame_count"] == 25 and r["fps"] == 5 and r["first_frame_index"] == w["start_frame_index"]
                 and r["final_frame_index"] == w["end_frame_index"] and r["human_review"] == "pending"
                 and r["index_binding"] in artifacts
                 and r["index_binding"]["path"] == OUTPUT_DIR + f"/review/{w['window_id']}/review_index.json"
                 and r["clip"] == OUTPUT_DIR + f"/review/{w['window_id']}/comparison.mp4",
                 "Review completion differs")
    _preserved(context, "completed", attempt_id)
    return parent_return(result)


def _validate_summary(summary, scope):
    """Reconcile transported counts and frame sets without opening scored files."""
    windows = summary["windows"]
    _require(summary["schema_version"] == "ball_crop_corroboration_summary/v0.1"
             and len(summary["pools"]) == 2 and len({r["window_id"] for r in summary["reviews"]}) == 6,
             "Summary identity/pool inventory differs")
    states = (*evaluation.STATES, *evaluation.HIDDEN_STATES, "ineligible")
    for declared in scope["windows"]:
        w = next(w for w in windows if w["window_id"] == declared["window_id"])
        expected = set(range(declared["start_frame_index"], declared["end_frame_index"] + 1))
        _require(w["purpose"] == declared["purpose"] and w["possession_id"] == declared["possession_id"]
                 and w["first_frame"] == min(expected) and w["last_frame"] == max(expected)
                 and set(w["summaries"]) == set(evaluation.ARMS), "Summary window identity differs")
        for arm in evaluation.ARMS:
            counts, frames = w["summaries"][arm]["counts"], w["summaries"][arm]["frame_indices"]
            _require(set(counts) == set(frames) == set(states)
                     and all(type(counts[s]) is int and counts[s] == len(frames[s]) and frames[s] == sorted(set(frames[s])) for s in states)
                     and sum(counts.values()) == 25 and set().union(*(set(frames[s]) for s in states)) == expected,
                     "Summary states do not partition the complete window")
            totals = w["summaries"][arm]
            _require(totals["frame_denominator"] == 25
                     and totals["eligible_denominator"] == sum(counts[s] for s in evaluation.STATES)
                     and totals["hidden_denominator"] == sum(counts[s] for s in evaluation.HIDDEN_STATES)
                     and totals["missed_eligible_count"] == counts["wrong_present"] + counts["missing"],
                     "Summary denominators differ")
        for arm in evaluation.CONTROLS:
            for kind, ss in (("eligible", evaluation.STATES), ("hidden", evaluation.HIDDEN_STATES)):
                table = w["paired_transitions"][arm][kind]
                _require(set(table) == set(ss) and all(set(table[s]) == set(ss) for s in ss), "Incomplete transition table")
                for before in ss:
                    for after in ss:
                        cell = table[before][after]
                        frames = sorted(set(w["summaries"][arm]["frame_indices"][before]) &
                                        set(w["summaries"][evaluation.ARM]["frame_indices"][after]))
                        _require(cell == {"count": len(frames), "frame_indices": frames}, "Transition counts/frames differ")
        choices = w["candidate_choices_against_top_one"]
        _require(set(choices["counts"]) == set(choices["frame_indices"]) == {"retained", "replaced", "suppressed", "both_missing"}
                 and all(choices["counts"][key] == len(values) and values == sorted(set(values))
                         for key, values in choices["frame_indices"].items())
                 and sum(choices["counts"].values()) == 25
                 and set().union(*(set(v) for v in choices["frame_indices"].values())) == expected,
                 "Candidate choice totals differ")
        for effect in w["primary_effects"].values():
            _require(effect["count"] == len(effect["frame_indices"]) and
                     effect["frame_indices"] == sorted(set(effect["frame_indices"])) and
                     set(effect["frame_indices"]) <= expected, "Effect frame count differs")
    reconstructed = []
    for pool in summary["pools"]:
        members = [w for w in windows if w["purpose"] == pool["purpose"]]
        _require(len(members) == pool["window_count"] == 3 and pool["runs_not_concatenated"] is True, "Pool window membership differs")
        for arm in evaluation.ARMS:
            expected_totals = {"counts": {s: sum(w["summaries"][arm]["counts"][s] for w in members) for s in states},
                               **{k: sum(w["summaries"][arm][k] for w in members) for k in
                                  ("frame_denominator", "eligible_denominator", "hidden_denominator", "missed_eligible_count")}}
            _require(pool["totals"][arm] == expected_totals, "Separate pool totals differ")
        for arm in evaluation.CONTROLS:
            for kind, ss in (("eligible", evaluation.STATES), ("hidden", evaluation.HIDDEN_STATES)):
                for before in ss:
                    for after in ss:
                        _require(pool["paired_transitions"][arm][kind][before][after] ==
                                 sum(w["paired_transitions"][arm][kind][before][after]["count"] for w in members),
                                 "Pool transition count differs")
        for key in pool["primary_effects"]:
            _require(pool["primary_effects"][key] == sum(w["primary_effects"][key]["count"] for w in members), "Pool effect count differs")
        for key in pool["candidate_choices_against_top_one"]:
            _require(pool["candidate_choices_against_top_one"][key] == sum(w["candidate_choices_against_top_one"]["counts"][key] for w in members),
                     "Pool candidate choice count differs")
        reconstructed.append({"purpose": pool["purpose"], "windows": members})
    _require(summary["interpretation"] == evaluation.development_interpretation(reconstructed), "Transported interpretation differs")


def _worker(root, manifest_path=MANIFEST_PATH):
    attempt_id = os.environ.get("BALL_RETENTION_ATTEMPT_ID")
    _owned_paths(root, attempt_id)  # Do not poll an arbitrary environment path.
    resources.wait_for_supervisor()  # Monitor resumes the process before publishing the gate.
    _ownership(root, attempt_id)  # Before metadata, journals or any scientific path.
    context = _metadata(root, manifest_path)
    journal = resources.BudgetJournal(context["output_root"], context["limits"])
    _verify_context_history(journal, context, "worker", attempt_id)
    _preserved(context, "worker", attempt_id)
    access = PhaseAccess(root, context["scope"], attempt_id=attempt_id)
    sink = OutputSink(root, context["scope"])
    deadline = time.monotonic() + journal._attempts()[attempt_id]["start"]["reserved_seconds"]
    def progress():
        _ownership(root, attempt_id)
        _require(time.monotonic() < deadline, "Worker deadline reached")
    result = run_comparison(context["scope"], access, sink, context["commit"], progress=progress)
    end = _metadata(root, manifest_path)
    _require(end["commit"] == context["commit"] and end["manifest_binding"] == context["manifest_binding"], "Release authority changed during execution")
    final_journal = resources.BudgetJournal(end["output_root"], end["limits"])
    _verify_context_history(final_journal, end, "worker", attempt_id)
    _preserved(end, "worker", attempt_id)
    path = _safe(root, OUTPUT_ROOT + "/attempts/" + attempt_id + ".result.json")
    raw = _json_bytes(result)
    _require(len(raw) <= MAX_RECEIPT_BYTES, "Worker receipt exceeds bound")
    with path.open("xb") as stream:
        stream.write(raw)
    return {"worker_result_written": True, "attempt_id": attempt_id}


def _successful_event(event, context, baseline):
    policy, aid = context["policy"], event["attempt_id"]
    ceiling = RETRY_MAX_SECONDS if context.get("retry") is not None else MAX_SECONDS
    _require(event["success"] is True and event["failure"] is None and event["exit_code"] == 0
             and event["owned_cleanup_verified"] is True and not event["cleanup_errors"]
             and event["final_accounting_error"] is None
             and event["monitoring_policy_sha256"] == resources._digest(policy)
             and event["monitoring_policy_path"] == f"attempts/{aid}.monitoring_policy.json"
             and event["log_path"] == f"attempts/{aid}.log"
             and event["monitor_samples"] > 0 and event["completed_scans"] >= 2,
             "Incomplete owned monitor completion")
    for field in ("time_overshoot_seconds", "memory_overshoot_bytes", "output_overshoot_bytes"):
        _require(event[field] == 0, "Monitored resource bound was exceeded")
    _require(0 < event["charged_elapsed_seconds"] == event["elapsed_seconds"] <= event["time_budget_seconds"] <= ceiling
             and event["peak_worker_memory_bytes"] <= policy["maximum_combined_rss_bytes"]
             and event["minimum_free_disk_bytes"] - monitor.FINAL_RESERVE >= policy["effective_minimum_free_disk_bytes"]
             and event["maximum_monitor_interval_seconds"] <= policy["maximum_fast_interval_seconds"]
             and event["final_accounting_output_bound_bytes"] == event["maximum_output_bytes"] + monitor.FINAL_RESERVE
             and event["final_accounting_output_bound_bytes"] <= policy["maximum_output_bytes"]
             and 0 <= event["final_accounting_output_bound_bytes"] - baseline <= MAX_NEW_BYTES,
             "Final monitored resources differ from approved bounds")
    scan = event["final_scan"]
    _require(isinstance(scan, dict) and scan["schema_version"] == monitor.RESPONSE_VERSION
             and scan["success"] is True and scan["error"] is None and scan["policy_sha256"] == resources._digest(policy)
             and 0 <= scan["output_bytes"] <= event["maximum_output_bytes"]
             and scan["requested_at"] <= scan["scan_started_at"] <= scan["completed_at"]
             and scan["completed_at"] - scan["requested_at"] < policy["scan_timeout_seconds"],
             "Final complete scan failed or differs")


def run_study(root, manifest_path=MANIFEST_PATH, dry_run=False):
    context = _metadata(root, manifest_path)
    scope = context["scope"]
    _preserved(context)
    journal = resources.BudgetJournal(context["output_root"], context["limits"])
    _verify_context_history(journal, context)
    _require(not _safe(root, OUTPUT_DIR).exists(), "Scientific output directory already exists")
    if dry_run:
        return {"study_id": ID, "ready": True, "commit": context["commit"], "scientific_body_reads": 0,
                "administrative_history_verified": True, "input_count": 190, "output_count": 342}
    baseline = _context_baseline(context)
    def factory(output, limits):
        if context.get("retry") is not None:
            return CorroborationRetryJournal(output, limits, context=context)
        return CorroborationJournal(output, limits, scope=scope, baseline_bytes=baseline)
    command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_cross_detector_corroboration_release",
               "--repository-root", str(context["root"]), "--manifest", context.get("manifest_path", MANIFEST_PATH), "--worker"]
    event = monitor.run_supervised(context["output_root"], UNIT_KEY, command, context["limits"], cwd=context["root"],
                                   selection_unit=False, require_result=True, journal_factory=factory)
    _require(event.get("success") is True, "Scientific attempt failed; preserve evidence and do not retry")
    aid = event["attempt_id"]
    _successful_event(event, context, baseline)
    final = _metadata(root, manifest_path)
    _require(final["commit"] == context["commit"] and final["manifest_binding"] == context["manifest_binding"], "Authority changed before release")
    verified = resources.BudgetJournal(context["output_root"], context["limits"])
    _verify_context_history(verified, final, "completed", aid)
    _require(event == verified._attempts()[aid]["finished"] and event["final_accounting_output_bound_bytes"] - baseline <= MAX_NEW_BYTES,
             "Final monitored completion/accounting differs")
    b = event["worker_result"]
    _require(b["path"] == "attempts/" + aid + ".result.json", "Receipt names another attempt")
    binding = {**b, "path": OUTPUT_ROOT + "/" + b["path"]}
    result = _json(_read_bound(root, binding, maximum=MAX_RECEIPT_BYTES))
    returned = validate_return(result, final, aid)
    returned["worker_receipt"] = binding
    _require(len(_json_bytes(returned)) <= MAX_RETURN_BYTES, "Entire administrative return exceeds bound")
    return returned


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--manifest", default=MANIFEST_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    _require(not (args.worker and args.dry_run), "Worker cannot obtain authority through dry run")
    result = _worker(args.repository_root, args.manifest) if args.worker else run_study(args.repository_root, args.manifest, args.dry_run)
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

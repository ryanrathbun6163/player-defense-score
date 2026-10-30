"""Additive, single-seed TAPNext++ adapter; no labels, scoring or source decoding.

The caller verifies the permitted block/image manifest and persists attempts.
Only create_adapter loads the released weights; tests may inject a CPU backend.
The support grid follows Google's Apache-2.0 VOTSp2026 implementation at PIN.
"""
from __future__ import annotations

import hashlib
import copy
import importlib
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import sys
from typing import Any

import numpy as np

PIN = "730cda1c730877cfedbe01bf87fb1cadb78a565d"
CHECKPOINT_SHA256 = "6cd0e793fdcface3063d63f8ed3819bcf74c2c0468fe1fef85acee4de2f3609f"
CHECKPOINT_BYTES = 2532283010
INPUT_SIZE = 512
COORDINATE_SIZE = 256
SUPPORT_COUNT = 64
QUERY_COUNT = 65
POLICY = "automatic_first_seed_tap_primary_one_rollout_per_block_v0_1"
INPUT_KEYS = {"source_frame_index", "source_pts_ticks", "duration_ticks", "time_base", "source_png", "wasb_observation"}
SEED_KEYS = {"source_frame_index", "source_pts_ticks", "inference_status", "point_origin", "center_xy_px", "native_score", "original_record_sha256"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _point(value):
    if value is None:
        return None
    require(isinstance(value, (list, tuple)) and len(value) == 2, "Point must contain two source coordinates")
    require(all(type(v) in (int, float) and math.isfinite(v) for v in value), "Nonfinite or invalid point")
    return [float(v) for v in value]


def _in_bounds(point, width, height):
    return point is not None and 0 <= point[0] < width and 0 <= point[1] < height


def project_wasb_observation(observation):
    """Project an actual emitted WASB record, retaining a digest of that record."""
    require(isinstance(observation, dict), "WASB observation must be a mapping")
    require(not ({"annotation", "reference", "geometry", "label", "localization_eligible"} & observation.keys()),
            "Reference-bearing records cannot enter the prediction interface")
    return {"source_frame_index": observation["source_frame_index"],
            "source_pts_ticks": observation["source_pts_ticks"],
            "inference_status": observation["inference_status"],
            "point_origin": observation.get("point_origin", "automatic"),
            "center_xy_px": _point(observation["center_xy_px"]),
            "native_score": observation.get("native_score"),
            "original_record_sha256": canonical(observation)}


def support_queries(seed_xy, width, height):
    """Real query first, then the exact upstream 64-point local support grid.

    Adapted from Google LLC's Apache-2.0 grid_support_points/local_support_points:
    https://github.com/google-deepmind/tapnet/blob/730cda1c730877cfedbe01bf87fb1cadb78a565d/tapnet/tapnextpp/votsp2026/tracker.py
    License: https://www.apache.org/licenses/LICENSE-2.0
    """
    query = np.asarray([seed_xy], dtype=np.float32)
    rx, ry = 32.0 * width / INPUT_SIZE, 32.0 * height / INPUT_SIZE
    cols = max(1, round(float(np.sqrt(SUPPORT_COUNT * (2 * rx) / (2 * ry)))))
    rows = max(1, int(np.ceil(SUPPORT_COUNT / cols)))
    xs = (np.arange(cols) + .5) * ((2 * rx) / cols)
    ys = (np.arange(rows) + .5) * ((2 * ry) / rows)
    gx, gy = np.meshgrid(xs, ys)
    local = np.stack([gx.ravel(), gy.ravel()], axis=-1).astype(np.float32)[:SUPPORT_COUNT]
    local = local - np.array([rx, ry], dtype=np.float32)
    local = local + query[0]
    local[:, 0] = np.clip(local[:, 0], 0, width - 1)
    local[:, 1] = np.clip(local[:, 1], 0, height - 1)
    return np.concatenate([query, local.astype(np.float32)], axis=0)


@dataclass
class TrackerFrame:
    positions_xy: np.ndarray
    coordinates_model_yx: np.ndarray
    coordinate_logits: np.ndarray
    visibility_logits: np.ndarray
    state: Any


class TorchTAPBackend:
    """Use the pinned producer/transforms, preserving logits discarded by its wrapper."""
    def __init__(self, wrapper, utils):
        require(wrapper.input_resolution == INPUT_SIZE and wrapper.MODEL_SIZE == COORDINATE_SIZE,
                "TAP input/coordinate resolution differs from the frozen policy")
        self.wrapper, self.utils = wrapper, utils

    def infer(self, rgb, query_points_xy, state):
        import torch
        model, device = self.wrapper._model, self.wrapper.device
        frame = self.utils.preprocess_frame(rgb[..., ::-1], device, INPUT_SIZE)
        query = None
        if query_points_xy is not None:
            points = self.utils.display_to_model(query_points_xy, rgb.shape[0], rgb.shape[1], COORDINATE_SIZE)
            query = self.utils.make_query_tensor(points, device)
        ctx = (torch.amp.autocast("cuda", dtype=torch.float16) if device.type == "cuda"
               else torch.amp.autocast("cpu", enabled=False))
        with torch.no_grad(), ctx:
            positions, logits, visibility, new_state = model(video=frame, query_points=query, state=state)
        require(tuple(positions.shape) == (1, 1, QUERY_COUNT, 2), "Unexpected upstream position shape")
        require(tuple(logits.shape) == (1, 1, QUERY_COUNT, 512), "Unexpected upstream coordinate-logit shape")
        require(tuple(visibility.shape) == (1, 1, QUERY_COUNT, 1), "Unexpected upstream visibility shape")
        model_yx = positions[0, 0].detach().cpu().float().numpy().copy()
        xy = self.utils.model_to_display(model_yx[:, ::-1].copy(), rgb.shape[0], rgb.shape[1], COORDINATE_SIZE)
        return TrackerFrame(xy, model_yx, logits[0, 0].detach().cpu().float().numpy().copy(),
                            visibility[0, 0, :, 0].detach().cpu().float().numpy().copy(), new_state)


class SingleSeedAdapter:
    """One automatic query per explicit block; hidden predictions never become points."""
    def __init__(self, backend):
        self.backend = backend
        self.block_id = None
        self.failed = False
        self.state = None

    def begin_block(self, block_id, width, height, time_base):
        require(isinstance(block_id, str) and block_id, "Block identifier is required")
        require(type(width) is int and type(height) is int and width > 0 and height > 0, "Invalid source dimensions")
        require(isinstance(time_base, str) and Fraction(time_base) > 0, "Invalid time base")
        self.block_id, self.width, self.height, self.time_base = block_id, width, height, time_base
        self.state, self.seed, self.last = None, None, None
        self.calls, self.failed = 0, False

    def observe(self, rgb, prediction_input):
        require(self.block_id is not None and not self.failed, "Begin a fresh block before using this adapter")
        require(isinstance(prediction_input, dict) and set(prediction_input) == INPUT_KEYS,
                "Prediction input must contain only the declared label-free fields")
        record = prediction_input
        for key in ("source_frame_index", "source_pts_ticks", "duration_ticks"):
            require(type(record[key]) is int and record[key] >= (1 if key == "duration_ticks" else 0),
                    "Invalid native frame/time field")
        require(record["time_base"] == self.time_base, "Time base changed within block")
        require(isinstance(rgb, np.ndarray) and rgb.dtype == np.uint8 and rgb.shape == (self.height, self.width, 3),
                "RGB must be source-sized uint8 with three channels")
        png = record["source_png"]
        require(isinstance(png, dict) and {"path", "sha256", "rgb_sha256"} <= png.keys()
                and not (png.keys() - {"path", "sha256", "rgb_sha256", "bytes", "frame_index"}),
                "Image binding must not contain reference metadata")
        require(hashlib.sha256(rgb.tobytes()).hexdigest() == png["rgb_sha256"], "RGB differs from bound image")
        if self.last is not None:
            require(record["source_frame_index"] == self.last[0] + 1
                    and record["source_pts_ticks"] == self.last[1] + self.last[2],
                    "Nonconsecutive native frames or display intervals require an explicit boundary reset")
        wasb = record["wasb_observation"]
        require(isinstance(wasb, dict) and set(wasb) == SEED_KEYS, "Invalid WASB seed projection")
        require(wasb["source_frame_index"] == record["source_frame_index"]
                and wasb["source_pts_ticks"] == record["source_pts_ticks"], "WASB/frame join differs")
        require(wasb["inference_status"] == "completed" and wasb["point_origin"] == "automatic",
                "Only completed automatic WASB observations can supply seeds")
        require(isinstance(wasb["original_record_sha256"], str) and len(wasb["original_record_sha256"]) == 64,
                "Original WASB record digest is required")
        baseline = _point(wasb["center_xy_px"])
        if wasb["native_score"] is not None:
            require(type(wasb["native_score"]) in (int, float) and math.isfinite(wasb["native_score"]), "Invalid WASB native score")
        seed_valid = _in_bounds(baseline, self.width, self.height)
        query = None
        seeded_now = self.seed is None and seed_valid
        if seeded_now:
            query = support_queries(baseline, self.width, self.height)
        raw, center = None, None
        reason = "before_first_valid_automatic_seed"
        if self.seed is not None or seeded_now:
            try:
                result = self.backend.infer(rgb, query, self.state)
                for values, shape in ((result.positions_xy, (QUERY_COUNT, 2)),
                                      (result.coordinates_model_yx, (QUERY_COUNT, 2)),
                                      (result.coordinate_logits, (QUERY_COUNT, 512)),
                                      (result.visibility_logits, (QUERY_COUNT,))):
                    require(isinstance(values, np.ndarray) and values.shape == shape and np.isfinite(values).all(),
                            "Nonfinite or malformed tracker output")
                require(result.state is not None, "Tracker returned no recurrent state")
                native = result.positions_xy[0].astype(float).tolist()
                visible = bool(result.visibility_logits[0] > 0)
                in_image = _in_bounds(native, self.width, self.height)
                center = native if visible and in_image else None
                reason = None if center is not None else "tracker_predicted_hidden" if not visible else "tracker_out_of_image"
                raw = {"center_xy_px": native,
                       "coordinates_model_yx": result.coordinates_model_yx[0].astype(float).tolist(),
                       "coordinate_logits_model_yx": result.coordinate_logits[0].astype(float).tolist(),
                       "visibility_logit": float(result.visibility_logits[0]),
                       "predicted_visible": visible, "in_source_bounds": in_image,
                       "support_count": SUPPORT_COUNT, "coordinate_resolution": COORDINATE_SIZE}
                self.state = result.state
                self.calls += 1
                if seeded_now:
                    self.seed = {"source_frame_index": record["source_frame_index"],
                                 "source_pts_ticks": record["source_pts_ticks"], "time_base": self.time_base,
                                 "center_xy_px": baseline, "wasb_record_sha256": wasb["original_record_sha256"],
                                 "support_queries_xy": query.astype(float).tolist()}
            except BaseException:
                self.failed = True
                raise
        self.last = (record["source_frame_index"], record["source_pts_ticks"], record["duration_ticks"])
        disagreement = (math.dist(baseline, raw["center_xy_px"])
                        if seed_valid and raw is not None and raw["in_source_bounds"] else None)
        return {"schema_version": "tapnext_observation/v0.1", "method": POLICY, "block_id": self.block_id,
                "source_frame_index": record["source_frame_index"], "source_pts_ticks": record["source_pts_ticks"],
                "duration_ticks": record["duration_ticks"], "time_base": self.time_base, "source_png": dict(png),
                "inference_status": "completed", "state": "observed" if center is not None else "missing",
                "center_xy_px": center, "point_origin": "automatic", "native_score": None,
                "missing_reason": reason, "tracker_raw": raw, "seed": copy.deepcopy(self.seed),
                "seeded_this_frame": seeded_now, "tracker_calls_in_block": self.calls,
                "wasb_observation": copy.deepcopy(wasb), "wasb_tracker_distance_px": disagreement}


def _verified_binding(root, binding):
    path = Path(binding["path"])
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    require(path.is_relative_to(root), "Asset binding escaped repository")
    size = binding.get("size_bytes", binding.get("bytes"))
    require(size is None or path.stat().st_size == size, "Asset byte count differs")
    require(file_sha256(path) == binding["sha256"], "Asset SHA256 differs")
    return path


def _checked_import_roots(asset_manifest, extracted_roots, verified_files):
    """Import only the extracted trees just verified, including cached children."""
    source = Path(asset_manifest["source_import_root"]).resolve()
    dependency = Path(asset_manifest["dependency_import_root"]).resolve()
    require(source == extracted_roots[0] / ("tapnet-" + PIN)
            and dependency == extracted_roots[1], "Import roots differ from verified extraction roots")
    require(source / "tapnet/__init__.py" in verified_files
            and dependency / "einops/__init__.py" in verified_files, "Package entry points were not verified")
    for name, module in tuple(sys.modules.items()):
        if name == "tapnet" or name.startswith("tapnet.") or name == "einops" or name.startswith("einops."):
            module_path = getattr(module, "__file__", None)
            if module_path is not None:
                require(Path(module_path).resolve() in verified_files,
                        "Conflicting preloaded dependency: " + name)
            else:
                # The pinned tapnextpp tree is a real PEP 420 namespace package:
                # it has no __init__.py / __file__, but must use the one verified
                # source directory, with verified descendant implementation files.
                expected = (source if name.split(".")[0] == "tapnet" else dependency).joinpath(*name.split(".")).resolve()
                spec = getattr(module, "__spec__", None)
                paths = [Path(p).resolve() for p in getattr(module, "__path__", ())]
                require(spec is not None and spec.origin is None
                        and spec.submodule_search_locations is not None
                        and paths == [expected]
                        and [Path(p).resolve() for p in spec.submodule_search_locations] == paths
                        and any(path.is_relative_to(expected) for path in verified_files),
                        "Conflicting preloaded namespace dependency: " + name)
    return [source, dependency]


def create_adapter(root, asset_manifest, *, device="cuda"):
    """Verify ready_asset_bindings.json, then load once; caller owns GPU permission."""
    root = Path(root).resolve()
    if not isinstance(asset_manifest, dict):
        path = Path(asset_manifest)
        asset_manifest = json.loads((path if path.is_absolute() else root / path).read_text(encoding="utf-8"))
    require(asset_manifest["source_commit"] == PIN, "TAP source commit differs")
    require(asset_manifest["checkpoint"]["sha256"] == CHECKPOINT_SHA256, "Released 512 checkpoint digest differs")
    checkpoint = _verified_binding(root, asset_manifest["checkpoint"])
    require(checkpoint.stat().st_size == CHECKPOINT_BYTES, "Released 512 checkpoint size differs")
    _verified_binding(root, asset_manifest["acquisition_manifest"])
    extracted_roots, verified_files = [], set()
    for key in ("source_files_manifest", "dependency_files_manifest"):
        manifest_path = _verified_binding(root, asset_manifest[key])
        files = json.loads(manifest_path.read_text(encoding="utf-8"))
        base = Path(files["root"]).resolve()
        require(base.is_relative_to(root), "Extracted asset root escaped repository")
        require(base == Path(asset_manifest[key]["root"]).resolve(), "Extraction root binding differs")
        extracted_roots.append(base)
        for entry in files["files"]:
            path = (base / entry["relative_path"]).resolve()
            require(path.is_relative_to(base), "Extracted asset escaped its root")
            verified_files.add(_verified_binding(root, {**entry, "path": str(path)}))
    import_paths = _checked_import_roots(asset_manifest, extracted_roots, verified_files)
    for path in reversed(import_paths):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    for name, expected in (("tapnet", import_paths[0]), ("einops", import_paths[1])):
        module = importlib.import_module(name)
        require(Path(module.__file__).resolve().is_relative_to(expected), "Conflicting preloaded dependency: " + name)
    from tapnet.tapnextpp.votsp2026 import model, utils
    _checked_import_roots(asset_manifest, extracted_roots, verified_files)
    require(all(Path(module.__file__).resolve().is_relative_to(import_paths[0]) for module in (model, utils)),
            "Conflicting preloaded TAP implementation")
    wrapper = model.TAPNextPP.from_checkpoint(checkpoint, device=device, input_resolution=INPUT_SIZE,
                                              half_precision=False, compile_model=False)
    return SingleSeedAdapter(TorchTAPBackend(wrapper, utils))

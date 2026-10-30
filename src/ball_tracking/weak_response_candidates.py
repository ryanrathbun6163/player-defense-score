"""CPU-only observed-candidate inventory for the NBA weak-response experiment.

No labels, model loads, inference, interpolation, candidate cap or selection live
here. Native components use the frozen producer's strict threshold, float32 mass
and row-major reduction arithmetic. Mass is not a calibrated probability.
"""
from __future__ import annotations

from copy import deepcopy
import math

import cv2
import numpy as np


DEFAULT_PARAMETERS = {
    "component_thresholds": [.3, .1, .03, .01, .003, .001, .0003, .0001, .00003, .00001],
    "strict_threshold": True,
    "connectivity": 8,
    "local_peak_floor": .00001,
    "local_peak_window": 5,
    "local_peak_centroid_fraction": .5,
    "dedup_source_pixels": 2.,
    "candidate_cap": None,
    "retain_native_candidates_exactly": True,
    "native_score_semantics": "Actual component or local-patch sigmoid mass, not probability; never compare mass across thresholds as confidence.",
}
NATIVE_FIELDS = ("center_x", "center_y", "heatmap_x", "heatmap_y", "native_score",
                 "component_pixels", "in_source_bounds")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _validate_map(heatmap, source_width, source_height):
    _require(isinstance(heatmap, np.ndarray) and heatmap.ndim == 2
             and min(heatmap.shape) > 0 and heatmap.dtype == np.float32
             and np.isfinite(heatmap).all() and (heatmap >= 0).all()
             and (heatmap <= 1).all(), "Expected a finite float32 sigmoid heatmap")
    _require(all(type(v) is int and v > 0 for v in (source_width, source_height)),
             "Source dimensions must be positive integers")


def inverse_affine(source_width, source_height, heatmap_width, heatmap_height):
    """Frozen resolution producer's float32 control-point construction, on CPU."""
    center = np.array([source_width / 2., source_height / 2.], np.float32)
    scale = np.float32(max(source_width, source_height))
    src, dst = np.zeros((3, 2), np.float32), np.zeros((3, 2), np.float32)
    src[0], src[1] = center, center + np.array([0, scale * -.5])
    dst[0] = [heatmap_width * .5, heatmap_height * .5]
    dst[1] = dst[0] + np.array([0, heatmap_width * -.5], np.float32)
    for points in (src, dst):
        direct = points[0] - points[1]
        points[2] = points[1] + np.array([-direct[1], direct[0]], np.float32)
    return cv2.getAffineTransform(dst, src)


def _groups(labels, count):
    """Group row-major foreground indices without an entire-map scan per label."""
    indices = np.flatnonzero(labels.ravel())
    if not len(indices):
        return
    values = labels.ravel()[indices]
    order = np.argsort(values, kind="stable")
    indices, values = indices[order], values[order]
    edges = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1, len(indices)]
    _require(len(edges) == count, "Connected-component label inventory differs")
    for left, right in zip(edges[:-1], edges[1:]):
        yield indices[left:right]


def _coordinate(xs, ys, weights, inverse, source_width, source_height):
    score = weights.sum()
    x = np.sum(np.array(xs) * weights) / score
    y = np.sum(np.array(ys) * weights) / score
    source_xy = np.dot(inverse, np.array([x, y, 1.], dtype=np.float32))
    return {"center_x": float(source_xy[0]), "center_y": float(source_xy[1]),
            "heatmap_x": float(x), "heatmap_y": float(y), "native_score": float(score),
            "component_pixels": int(weights.size),
            "in_source_bounds": bool(0 <= source_xy[0] < source_width
                                     and 0 <= source_xy[1] < source_height)}


def _components(heatmap, source_width, source_height, threshold, inverse):
    if np.max(heatmap) <= threshold:
        return [], []
    _, binary = cv2.threshold(heatmap, float(threshold), 1, cv2.THRESH_BINARY)
    count, labels = cv2.connectedComponents(binary.astype(np.uint8), connectivity=8)
    result, peaks = [], []
    width = heatmap.shape[1]
    for indices in _groups(labels, count):
        ys, xs = indices // width, indices % width
        weights = heatmap.ravel()[indices]
        result.append(_coordinate(xs, ys, weights, inverse, source_width, source_height))
        peaks.append(float(weights.max()))
    return result, peaks


def components(heatmap, source_width, source_height, threshold=.3):
    """Return exactly the frozen producer's component fields and arithmetic."""
    _validate_map(heatmap, source_width, source_height)
    _require(type(threshold) in (int, float) and math.isfinite(threshold)
             and 0 <= threshold <= 1, "Invalid threshold")
    inverse = inverse_affine(source_width, source_height, heatmap.shape[1], heatmap.shape[0])
    return _components(heatmap, source_width, source_height, threshold, inverse)[0]


def local_maxima(heatmap, source_width, source_height, *, floor=.00001, window=5,
                 relative_cutoff=.5):
    """Consolidate flat maxima; emit observed weighted centers in native patches.

    A plateau's representative is its pixel nearest the plateau centroid, with
    row-major tie breaking. The clipped window around that pixel contributes only
    values strictly greater than half the plateau peak. No interpolated points.
    """
    _validate_map(heatmap, source_width, source_height)
    _require(type(window) is int and window > 0 and window % 2 == 1, "Window must be odd")
    _require(math.isfinite(floor) and 0 <= floor <= 1
             and math.isfinite(relative_cutoff) and 0 < relative_cutoff < 1,
             "Invalid local maximum floor or relative cutoff")
    inverse = inverse_affine(source_width, source_height, heatmap.shape[1], heatmap.shape[0])
    maximum = cv2.dilate(heatmap, np.ones((window, window), np.uint8),
                         borderType=cv2.BORDER_CONSTANT, borderValue=-float("inf"))
    mask = ((heatmap == maximum) & (heatmap > floor)).astype(np.uint8)
    count, labels = cv2.connectedComponents(mask, connectivity=8)
    result, radius = [], window // 2
    height, width = heatmap.shape
    for plateau in _groups(labels, count):
        ys, xs = plateau // width, plateau % width
        distances = (xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2
        representative = int(np.argmin(distances))
        px, py = int(xs[representative]), int(ys[representative])
        peak = float(heatmap[py, px])
        x0, x1 = max(0, px-radius), min(width, px+radius+1)
        y0, y1 = max(0, py-radius), min(height, py+radius+1)
        patch = heatmap[y0:y1, x0:x1]
        local_ys, local_xs = np.where(patch > peak * relative_cutoff)
        weights = patch[local_ys, local_xs]
        row = _coordinate(local_xs+x0, local_ys+y0, weights, inverse,
                          source_width, source_height)
        row.update(extraction="local_maximum", threshold=float(floor), peak=peak,
                   extraction_index=len(result), original_index=None,
                   peak_heatmap_xy=[px, py], plateau_pixels=int(len(plateau)),
                   patch_bounds_xyxy=[x0, y0, x1, y1], relative_cutoff=float(relative_cutoff))
        result.append(row)
    return result


def extract_pool(heatmap, native_candidates, source_width, source_height, parameters=None):
    """Return ``(union, diagnostics)`` without selecting or reading references.

    Original candidates remain first, including native duplicates and out-of-
    image points. Weak duplicates within two source pixels keep their extraction
    provenance on the retained row. Every raw extraction is also in diagnostics,
    so deduplication cannot silently change a diagnostic availability ceiling.
    """
    parameters = deepcopy(DEFAULT_PARAMETERS if parameters is None else parameters)
    _require(parameters == DEFAULT_PARAMETERS, "This experiment accepts only its frozen extraction grid")
    _validate_map(heatmap, source_width, source_height)
    inverse = inverse_affine(source_width, source_height, heatmap.shape[1], heatmap.shape[0])
    by_threshold = {}
    for threshold in parameters["component_thresholds"]:
        rows, peaks = _components(heatmap, source_width, source_height, threshold, inverse)
        by_threshold[str(threshold)] = [{**row, "extraction": "threshold_component",
                                        "threshold": threshold, "peak": peak,
                                        "extraction_index": i, "original_index": None}
                                       for i, (row, peak) in enumerate(zip(rows, peaks))]
    native = by_threshold[str(parameters["component_thresholds"][0])]
    _require(len(native) == len(native_candidates), "Saved native component count differs")
    pool = []
    for index, (saved, recomputed) in enumerate(zip(native_candidates, native)):
        _require(saved.get("candidate_index", index) == index
                 and all(saved.get(k) == recomputed[k] for k in NATIVE_FIELDS),
                 "Saved native candidate differs from reconstructed map")
        row = deepcopy(saved)
        row.update(candidate_index=index, component_index=index, original_index=index, extraction="native_component",
                   threshold=parameters["component_thresholds"][0], peak=recomputed["peak"],
                   extraction_index=index, extraction_original_index=index, equivalent_extractions=[])
        pool.append(row)
    maxima = local_maxima(heatmap, source_width, source_height,
                         floor=parameters["local_peak_floor"], window=parameters["local_peak_window"],
                         relative_cutoff=parameters["local_peak_centroid_fraction"])
    weak = [row for key, rows in by_threshold.items()
            if float(key) != parameters["component_thresholds"][0] for row in rows] + maxima
    cell_size = parameters["dedup_source_pixels"]
    cells = {}
    def cell(row):
        return math.floor(row["center_x"] / cell_size), math.floor(row["center_y"] / cell_size)
    for row in pool:
        cells.setdefault(cell(row), []).append(row["component_index"])
    for original in weak:
        row = deepcopy(original)
        cx, cy = cell(row)
        neighbors = [i for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                     for i in cells.get((cx+dx, cy+dy), [])]
        duplicates = [i for i in neighbors
                      if math.hypot(row["center_x"]-pool[i]["center_x"],
                                    row["center_y"]-pool[i]["center_y"]) <= cell_size]
        if duplicates:
            pool[min(duplicates)]["equivalent_extractions"].append(row)
        else:
            row.update(candidate_index=len(pool), component_index=len(pool),
                       extraction_original_index=row["extraction_index"], equivalent_extractions=[])
            pool.append(row)
            cells.setdefault((cx, cy), []).append(row["component_index"])
    diagnostics = {"components_by_threshold": by_threshold, "local_maxima": maxima,
                   "native_count": len(native_candidates), "raw_weak_count": len(weak),
                   "pool_count": len(pool), "deduplicated_weak_count": len(native_candidates)+len(weak)-len(pool),
                   "in_source_bounds_count": sum(r["in_source_bounds"] for r in pool),
                   "candidate_count_cap": None, "dedup_source_pixels": cell_size,
                   "labels_used": False, "native_parity": True}
    return pool, diagnostics

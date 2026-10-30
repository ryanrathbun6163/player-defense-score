"""Fixed CPU descriptors of observed mean responses; no labels or selection.

Sampling uses source-pixel offsets and the inverse of the frozen producer's
heatmap-to-source affine. Response values are not calibrated probabilities.
"""
from __future__ import annotations

import math

import numpy as np

from .weak_response_candidates import inverse_affine


OFFSETS = np.asarray([(x, y) for y in range(-10, 11) for x in range(-10, 11)
                      if x * x + y * y <= 100], dtype=np.float64)
CORE = np.square(OFFSETS).sum(axis=1) <= 25
FEATURE_NAMES = ("peak", "core_ring_contrast", "entropy_concentration", "isotropy",
                 "negative_centroid_distance", "negative_spread")
EPSILON = 1e-12
OFFSETS.setflags(write=False)
CORE.setflags(write=False)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def source_to_heatmap(source_width, source_height, heatmap_width, heatmap_height):
    check(all(type(value) is int and value > 0 for value in
              (source_width, source_height, heatmap_width, heatmap_height)),
          "Positive integer source/map dimensions required")
    inverse = inverse_affine(source_width, source_height, heatmap_width, heatmap_height)
    return np.linalg.inv(np.vstack((inverse, [0., 0., 1.])))[:2]


def sample_source_points(mean, source_xy, source_width, source_height):
    """Bilinear float64 samples, or an explicit incomplete/invalid-patch reason.

    Out-of-source/map samples never receive padding, clamping or extrapolation.
    The final map row/column itself is valid: a zero-weight next pixel is not
    required. Only touched pixels are validated; the driver binds complete maps.
    """
    check(isinstance(mean, np.ndarray) and mean.ndim == 2 and mean.dtype == np.float32
          and min(mean.shape) > 0, "Expected a two-dimensional float32 saved mean")
    xy = np.asarray(source_xy, dtype=np.float64)
    check(xy.ndim == 2 and xy.shape[1] == 2 and len(xy) > 0
          and np.isfinite(xy).all(), "Finite source-pixel coordinates required")
    transform = source_to_heatmap(source_width, source_height, mean.shape[1], mean.shape[0])
    if not ((xy[:, 0] >= 0) & (xy[:, 0] < source_width)
            & (xy[:, 1] >= 0) & (xy[:, 1] < source_height)).all():
        return None, "incomplete_source_patch"
    mapped = np.column_stack((xy, np.ones(len(xy)))) @ transform.T
    x, y = mapped[:, 0], mapped[:, 1]
    if not ((x >= 0) & (x <= mean.shape[1] - 1)
            & (y >= 0) & (y <= mean.shape[0] - 1)).all():
        return None, "incomplete_heatmap_patch"
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    x1, y1 = np.minimum(x0 + 1, mean.shape[1] - 1), np.minimum(y0 + 1, mean.shape[0] - 1)
    dx, dy = x - x0, y - y0
    corners = np.stack((mean[y0, x0], mean[y0, x1], mean[y1, x0], mean[y1, x1])).astype(np.float64)
    coefficients = np.stack(((1 - dx) * (1 - dy), dx * (1 - dy), (1 - dx) * dy, dx * dy))
    touched = coefficients > 0
    used = corners[touched]
    if not (np.isfinite(used).all() and (used >= 0).all() and (used <= 1).all()):
        return None, "invalid_sampled_response"
    # Unused invalid neighbors do not contribute, including via 0 * NaN.
    values = np.sum(np.where(touched, corners, 0.) * coefficients, axis=0, dtype=np.float64)
    return values, None


def unknown(reason):
    return {"status": "unknown", "reason": reason, "sample_count": 317,
            "core_count": 81, "ring_count": 236,
            "features": dict.fromkeys(FEATURE_NAMES),
            "feature_unknown_reasons": {name: reason for name in FEATURE_NAMES}}


def describe_response(mean, center_xy_px, source_width, source_height):
    """Six declared higher-is-better descriptors of the fixed radius-ten disk."""
    if center_xy_px is None:
        return unknown("missing_selection")
    center = np.asarray(center_xy_px, dtype=np.float64)
    check(center.shape == (2,), "Two-coordinate candidate center required")
    if not np.isfinite(center).all():
        return unknown("nonfinite_candidate_center")
    values, reason = sample_source_points(mean, center + OFFSETS, source_width, source_height)
    if reason is not None:
        return unknown(reason)
    total = float(values.sum(dtype=np.float64))
    if total <= 0:
        return unknown("all_zero_response")
    weights = values / total
    core_mean, ring_mean = float(values[CORE].mean()), float(values[~CORE].mean())
    centroid = (OFFSETS * weights[:, None]).sum(axis=0, dtype=np.float64)
    centered = OFFSETS - centroid
    covariance = (centered * weights[:, None]).T @ centered
    eigenvalues = np.linalg.eigvalsh(covariance)
    largest, smallest = float(eigenvalues[-1]), max(0., float(eigenvalues[0]))
    reasons = {}
    if largest <= 0:
        isotropy = None
        reasons["isotropy"] = "zero_spatial_variance"
    else:
        isotropy = smallest / largest
    positive = weights[weights > 0]
    entropy = -float(np.sum(positive * np.log(positive), dtype=np.float64))
    features = {"peak": float(values.max()),
                "core_ring_contrast": (core_mean - ring_mean) / (core_mean + ring_mean + EPSILON),
                "entropy_concentration": 1. - entropy / math.log(len(OFFSETS)),
                "isotropy": isotropy,
                "negative_centroid_distance": -float(np.linalg.norm(centroid)),
                "negative_spread": -math.sqrt(max(0., float(np.trace(covariance))))}
    check(all(value is None or math.isfinite(value) for value in features.values()),
          "Nonfinite descriptor")
    return {"status": "partial" if reasons else "observed", "reason": None,
            "sample_count": 317, "core_count": 81, "ring_count": 236,
            "features": features, "feature_unknown_reasons": reasons}

"""Label-blind acceptance features and the frozen CPU S/J fitting recipe.

Callers own source binding, game nesting and target/weight membership. This
module accepts only observable fields for feature construction and never reads
images, annotations, datasets, models or files. Real-population execution is
the responsibility of the separately reviewed experiment runner.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


FEATURE_NAMES = (
    "quality_logit", "log1p_response_mass", "log1p_component_pixels", "padding_fraction",
    "native_indicator", "origin_unavailable", "response_missing", "component_missing",
    "padding_missing", "quality_minus_far_max", "quality_minus_near_max",
    "log1p_near_count", "log1p_far_count", "far_max_missing", "near_max_missing",
    "pool_unavailable",
)
BINARY_FEATURES = frozenset((
    "native_indicator", "origin_unavailable", "response_missing", "component_missing",
    "padding_missing", "far_max_missing", "near_max_missing", "pool_unavailable",
))
RADIUS = 20.0
RIDGE = 0.01


class FeatureIntegrityError(ValueError):
    """Observable fields or a frozen CPU fitting contract are invalid."""


class GateFitError(RuntimeError):
    """The attempted fit must be persisted, not accepted or silently retried."""

    def __init__(self, message, fit_record):
        super().__init__(message)
        self.fit_record = fit_record


def _require(condition, message):
    if not condition:
        raise FeatureIntegrityError(message)


def _finite(value, name, *, missing=False, nonnegative=False):
    if value is None and missing:
        return None
    _require(isinstance(value, (int, float)) and not isinstance(value, bool)
             and math.isfinite(value), name + " must be finite numeric")
    _require(not nonnegative or value >= 0, name + " must be nonnegative")
    return float(value)


def source_center(row):
    """Read only the saved producer/query center, never reference geometry."""
    if "center_xy_px" in row:
        value = row["center_xy_px"]
    else:
        source = row.get("source") or {}
        candidate = source.get("candidate")
        query = source.get("query")
        value = (candidate if candidate is not None else query or {}).get("center_xy_px")
    if value is None:
        return None
    _require(isinstance(value, (tuple, list)) and len(value) == 2, "source center must have two coordinates")
    return tuple(_finite(v, "source coordinate") for v in value)


def _observable(row):
    q = _finite(row.get("logit"), "quality logit", missing=True)
    center = source_center(row)
    _require((q is None) == (center is None), "observed score and source-center missingness differ")
    mass = _finite(row.get("native_score"), "response mass", missing=True, nonnegative=True)
    pixels = _finite(row.get("component_pixels"), "component pixels", missing=True, nonnegative=True)
    padding = _finite(row.get("padding_pixels"), "padding pixels", missing=True, nonnegative=True)
    _require(padding is None or padding <= 4096, "padding exceeds the saved 64px crop")
    origin = row.get("native_or_weak")
    _require(origin in {None, "native", "weak", "inapplicable_historical", "inapplicable_missing"},
             "unknown candidate origin")
    return q, center, mass, pixels, padding, origin


def _pool_groups(probe, pool):
    _require(isinstance(probe.get("frame_key"), str) and bool(probe["frame_key"]),
             "available main pool requires a frame identity")
    _require(isinstance(probe.get("fit"), str) and bool(probe["fit"]),
             "available main pool requires a base-scorer identity")
    groups = {}
    ids = set()
    for row in pool:
        key = row.get("row_key")
        _require(isinstance(key, str) and key not in ids, "missing or duplicate main-pool row key")
        ids.add(key)
        _require(row.get("cohort") not in {"HOU_stress", "historical"},
                 "external probes must not enter a main pool")
        for field in ("frame_key", "fit"):
            _require(probe.get(field) == row.get(field), "main-pool " + field + " differs from probe")
        q = _finite(row.get("logit"), "main-pool quality logit")
        center = source_center(row)
        _require(center is not None, "main-pool source center missing")
        # Python numeric tuple equality deliberately groups 4 and 4.0, but does
        # not round distinct fractional coordinates or mutate original rows.
        group = groups.setdefault(center, {"max_logit": q, "row_keys": []})
        group["max_logit"] = max(group["max_logit"], q)
        group["row_keys"].append(key)
    return groups


def build_feature_row(probe, main_pool):
    """Build one observable vector; None pool means unavailable, [] means empty.

    Probe/main-pool canonical fields are row_key, frame_key, fit, logit,
    center_xy_px, native_score, component_pixels, padding_pixels and
    native_or_weak. Existing saved-study nested source centers are also accepted.
    Neither labels nor reporting metadata are read or used to select neighbors.
    """
    key = probe.get("row_key")
    _require(isinstance(key, str) and bool(key), "probe row key missing")
    q, center, mass, pixels, padding, origin = _observable(probe)
    _require(probe.get("cohort") != "historical" or main_pool is None,
             "historical queries do not define a complete candidate pool")
    groups = None if main_pool is None else _pool_groups(probe, main_pool)
    out = {"row_key": key, "frame_key": probe.get("frame_key"), "fit": probe.get("fit"),
           "feature_names": list(FEATURE_NAMES), "Q": q, "M": None,
           "status": "missing_image" if q is None else "observed",
           "raw_features": None, "values": None,
           "pool_provenance": {"available": main_pool is not None,
                               "original_candidate_count": None if main_pool is None else len(main_pool),
                               "distinct_center_count": None if groups is None else len(groups),
                               "radius_source_pixels": RADIUS},
           "out_of_fitting_schema": probe.get("cohort") == "historical",
           "missing_input_fields": [name for name, val in
                                    (("native_score", mass), ("component_pixels", pixels),
                                     ("padding_pixels", padding)) if val is None]}
    if q is None:
        out["M_fallback_reason"] = "missing_image"
        return out
    near = far = None
    self_ids = []
    if groups is not None:
        self_ids = sorted(groups.get(center, {}).get("row_keys", []))
        near, far = [], []
        for xy, group in groups.items():
            if xy == center:
                continue
            distance = math.hypot(xy[0] - center[0], xy[1] - center[1])
            (near if distance <= RADIUS else far).append(group["max_logit"])
    near_max = max(near) if near else None
    far_max = max(far) if far else None
    values = (
        q, math.log1p(mass) if mass is not None else None,
        math.log1p(pixels) if pixels is not None else None,
        padding / 4096 if padding is not None else None,
        int(origin == "native"), int(origin not in {"native", "weak"}),
        int(mass is None), int(pixels is None), int(padding is None),
        q - far_max if far_max is not None else None,
        q - near_max if near_max is not None else None,
        math.log1p(len(near)) if near is not None else None,
        math.log1p(len(far)) if far is not None else None,
        int(far_max is None), int(near_max is None), int(groups is None),
    )
    _require(all(v is None or math.isfinite(v) for v in values), "nonfinite derived acceptance feature")
    out["values"] = list(values)
    out["raw_features"] = dict(zip(FEATURE_NAMES, values))
    out["M"] = q - far_max if far_max is not None else q
    out["M_fallback_reason"] = None if far_max is not None else (
        "pool_unavailable" if groups is None else "no_far_rival")
    out["pool_provenance"].update(excluded_self_row_keys=self_ids,
                                  near_center_count=None if near is None else len(near),
                                  far_center_count=None if far is None else len(far),
                                  near_max_quality=near_max, far_max_quality=far_max)
    return out


def build_feature_rows(probes, pools):
    """Build rows from pools indexed by (fit, frame_key), never by target label."""
    result = []
    keys = set()
    for probe in probes:
        key = probe["row_key"]
        _require(key not in keys, "duplicate probe row key")
        keys.add(key)
        if probe.get("cohort") == "historical":
            pool = None
        else:
            group = (probe.get("fit"), probe.get("frame_key"))
            _require(group in pools, "missing declared main pool")
            pool = pools[group]
        result.append(build_feature_row(probe, pool))
    return result


def _weights(weights, size):
    _require(len(weights) == size and size > 0, "empty or mismatched fitting weights")
    values = np.asarray([_finite(w, "objective weight", nonnegative=True) for w in weights],
                        dtype=np.float64)
    _require(bool(np.all(values > 0)), "fitting weights must be positive; missing membership is not zero")
    _require(math.isclose(math.fsum(values.tolist()), 1.0, rel_tol=1e-12, abs_tol=1e-12),
             "objective weights must sum to one")
    return values


def _matrix(rows, names):
    _require(names and len(names) == len(set(names)) and set(names) <= set(FEATURE_NAMES),
             "invalid feature selection")
    values = []
    for row in rows:
        _require(row.get("status") == "observed" and row.get("raw_features") is not None,
                 "missing-image row cannot be fitted/transformed")
        _require(tuple(row.get("feature_names", [])) == FEATURE_NAMES, "feature order differs")
        raw = row["raw_features"]
        _require(set(raw) == set(FEATURE_NAMES), "raw feature schema differs")
        _require(row.get("values") == [raw[k] for k in FEATURE_NAMES], "feature array/dictionary differs")
        encoded = []
        for name in names:
            value = _finite(raw[name], name, missing=name not in BINARY_FEATURES)
            if name in BINARY_FEATURES:
                _require(value in (0, 1), "binary feature outside zero/one")
            encoded.append(np.nan if value is None else value)
        values.append(encoded)
    return np.asarray(values, dtype=np.float64).reshape(len(rows), len(names))


def fit_standardizer(feature_rows, weights, feature_names=None):
    """Weighted fitting-only normalization; binary indicators remain unchanged."""
    names = list(FEATURE_NAMES if feature_names is None else feature_names)
    w = _weights(weights, len(feature_rows))
    matrix = _matrix(feature_rows, names)
    means, scales, details = [], [], []
    for j, name in enumerate(names):
        observed = ~np.isnan(matrix[:, j])
        count = int(observed.sum())
        item = {"feature": name, "observed_count": count,
                "missing_count": len(feature_rows) - count, "degeneracy": None}
        if name in BINARY_FEATURES:
            mean, scale = 0.0, 1.0
            item["normalization"] = "binary_unscaled"
        elif count == 0:
            mean, scale = 0.0, 1.0
            item.update(normalization="weighted_fitting_only", degeneracy="all_missing")
        else:
            x = matrix[observed, j]
            own_w = w[observed] / w[observed].sum(dtype=np.float64)
            mean = float(np.dot(own_w, x))
            if np.all(x == x[0]):
                mean, scale = float(x[0]), 1.0
                item["degeneracy"] = "zero_variance"
            else:
                variance = float(np.dot(own_w, np.square(x - mean)))
                scale = math.sqrt(variance)
                _require(math.isfinite(scale) and scale > 0, "nonfinite or lost feature variance")
            item["normalization"] = "weighted_fitting_only"
        _require(math.isfinite(mean) and math.isfinite(scale), "nonfinite scaler")
        item["observed_objective_mass"] = float(w[observed].sum(dtype=np.float64))
        means.append(mean); scales.append(scale); details.append(item)
    return {"feature_names": names, "means": means, "scales": scales,
            "binary_features": [n for n in names if n in BINARY_FEATURES],
            "fitting_row_count": len(feature_rows), "weight_sum": math.fsum(w.tolist()),
            "details": details, "imputation": "fitting_mean_then_standardized_zero"}


def transform_features(feature_rows, scaler):
    names = scaler["feature_names"]
    matrix = _matrix(feature_rows, names)
    means = np.asarray(scaler["means"], dtype=np.float64)
    scales = np.asarray(scaler["scales"], dtype=np.float64)
    _require(means.shape == scales.shape == (len(names),), "scaler shape differs")
    _require(bool(np.all(np.isfinite(means)) and np.all(np.isfinite(scales)) and np.all(scales > 0)),
             "invalid persisted scaler")
    for j, name in enumerate(names):
        if name in BINARY_FEATURES:
            _require(means[j] == 0 and scales[j] == 1, "binary indicators must remain unscaled")
    matrix = np.where(np.isnan(matrix), means[None, :], matrix)
    transformed = (matrix - means[None, :]) / scales[None, :]
    _require(bool(np.all(np.isfinite(transformed))), "nonfinite transformed feature")
    return transformed


def _objective(parameters, matrix, targets, weights):
    score = parameters[0] + matrix @ parameters[1:]
    bce = np.logaddexp(0.0, score) - targets * score
    residual = weights * (expit(score) - targets)
    loss = float(np.dot(weights, bce) + RIDGE / 2 * np.dot(parameters[1:], parameters[1:]))
    gradient = np.concatenate(([residual.sum(dtype=np.float64)],
                               matrix.T @ residual + RIDGE * parameters[1:]))
    _require(math.isfinite(loss) and bool(np.all(np.isfinite(gradient))), "nonfinite gate objective")
    return loss, gradient


def _array_binding(array):
    value = np.asarray(array, dtype="<f8", order="C")
    return {"dtype": "little_endian_float64", "shape": list(value.shape),
            "sha256": hashlib.sha256(value.tobytes(order="C")).hexdigest()}


def fit_gate(feature_rows, targets, weights, *, arm, fit_id):
    """Fit one frozen S/J recipe on supplied, already source-checked training rows."""
    _require(arm in {"S", "J"}, "unknown learned gate arm")
    _require(isinstance(fit_id, str) and bool(fit_id), "fit id missing")
    row_keys = [r["row_key"] for r in feature_rows]
    _require(len(row_keys) == len(set(row_keys)), "duplicate fitting row key")
    _require(len(targets) == len(feature_rows), "target length differs")
    y = np.asarray([_finite(v, "known fitting target") for v in targets], dtype=np.float64)
    _require(set(y.tolist()) == {0.0, 1.0}, "fitting targets must include both known binary classes")
    w = _weights(weights, len(feature_rows))
    names = ["quality_logit"] if arm == "S" else list(FEATURE_NAMES)
    scaler = fit_standardizer(feature_rows, weights, names)
    matrix = transform_features(feature_rows, scaler)
    initial = np.zeros(1 + len(names), dtype=np.float64)
    initial_loss, _ = _objective(initial, matrix, y, w)
    result = minimize(_objective, initial, args=(matrix, y, w), method="L-BFGS-B", jac=True,
                      bounds=[(None, None), (0.0, None)] if arm == "S" else None,
                      options={"maxiter": 10000, "ftol": 1e-12, "gtol": 1e-9})
    finite = bool(np.all(np.isfinite(result.x)) and math.isfinite(float(result.fun))
                  and np.all(np.isfinite(result.jac)))
    score = result.x[0] + matrix @ result.x[1:]
    finite = finite and bool(np.all(np.isfinite(score)))
    gradient = np.asarray(result.jac, dtype=np.float64)
    projected = gradient.copy()
    if arm == "S" and result.x[1] == 0 and gradient[1] > 0:
        projected[1] = 0
    accepted = bool(result.success and finite and (arm != "S" or result.x[1] >= 0))
    record = {
        "schema": "candidate_acceptance_gate_fit/v0.1", "status": "fitted" if accepted else "failed",
        "arm": arm, "fit_id": fit_id, "feature_names": names, "scaler": scaler,
        "intercept": float(result.x[0]) if math.isfinite(float(result.x[0])) else None,
        "coefficients": [float(x) if math.isfinite(float(x)) else None for x in result.x[1:]],
        "training_row_count": len(row_keys), "training_row_keys": row_keys,
        "training_arrays": {"features": _array_binding(matrix), "targets": _array_binding(y),
                            "weights": _array_binding(w)},
        "objective": "sum(weight*BCEWithLogits)+0.01/2*sum(beta^2); intercept unpenalized",
        "solver": {"method": "L-BFGS-B", "success": bool(result.success), "status": int(result.status),
                   "message": str(result.message), "iterations": int(result.nit), "function_evaluations": int(result.nfev),
                   "initial_loss": initial_loss, "final_loss": float(result.fun) if math.isfinite(float(result.fun)) else None,
                   "raw_gradient_inf_norm": float(np.max(np.abs(gradient))) if np.all(np.isfinite(gradient)) else None,
                   "projected_gradient_inf_norm": float(np.max(np.abs(projected))) if np.all(np.isfinite(projected)) else None,
                   "maxiter": 10000, "ftol": 1e-12, "gtol": 1e-9, "ridge": RIDGE},
        "constant_score_degeneracy": bool(arm == "S" and result.x[1] == 0),
        "calibrated_probability_claim": False,
    }
    if not accepted:
        raise GateFitError("Frozen gate fit did not satisfy success/finite contracts", record)
    return record


def score_gate(model, feature_rows):
    """Return row-aligned scalar gate scores, preserving absent-image slots."""
    _require(model.get("status") == "fitted", "cannot score an unaccepted gate")
    arm = model.get("arm")
    expected = ["quality_logit"] if arm == "S" else list(FEATURE_NAMES)
    _require(arm in {"S", "J"} and model["feature_names"] == expected
             and model["scaler"]["feature_names"] == expected, "model feature schema differs")
    beta = np.asarray([_finite(x, "gate coefficient") for x in model["coefficients"]], dtype=np.float64)
    intercept = _finite(model["intercept"], "gate intercept")
    _require(beta.shape == (len(expected),), "gate coefficient shape differs")
    _require(arm != "S" or beta[0] >= 0, "score-only slope reversed")
    observed = [r for r in feature_rows if r.get("status") == "observed"]
    matrix = transform_features(observed, model["scaler"])
    scores = (intercept + matrix @ beta).tolist()
    _require(all(math.isfinite(s) for s in scores), "nonfinite gate prediction")
    values = iter(scores)
    result = []
    for row in feature_rows:
        if row.get("status") == "observed":
            result.append(next(values))
        else:
            _require(row.get("status") == "missing_image" and row.get("Q") is None
                     and row.get("values") is None, "unknown missing score state")
            result.append(None)
    return result

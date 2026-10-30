"""One CPU origin-indicator ablation of the accepted 16-feature joint gate.

Accept unchanged saved feature records, validate all 16 values, then remove only
native_indicator and origin_unavailable. Source membership and execution freeze
are the runner's responsibility. This module reads no experiment files/images.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import minimize

from . import candidate_acceptance_features as original


REMOVED_FEATURES = ("native_indicator", "origin_unavailable")
FEATURE_NAMES = tuple(name for name in original.FEATURE_NAMES if name not in REMOVED_FEATURES)
GateFitError = original.GateFitError
FeatureIntegrityError = original.FeatureIntegrityError


def _validate_observed(rows):
    """Validate discarded columns too; ablation is not input-schema relaxation."""
    original._matrix(rows, list(original.FEATURE_NAMES))
    for row in rows:
        q = original._finite(row.get("Q"), "saved quality score")
        original._require(q == row["raw_features"]["quality_logit"], "saved quality differs from feature")


def fit_origin_gate(feature_rows, targets, weights, *, fit_id):
    """Fit A with the exact J objective, scaler and unconstrained solver recipe."""
    original._require(isinstance(fit_id, str) and bool(fit_id), "fit id missing")
    row_keys = [row["row_key"] for row in feature_rows]
    original._require(len(row_keys) == len(set(row_keys)), "duplicate fitting row key")
    original._require(len(targets) == len(feature_rows), "target length differs")
    y = np.asarray([original._finite(value, "known fitting target") for value in targets], dtype=np.float64)
    original._require(set(y.tolist()) == {0.0, 1.0}, "fitting targets must include both known binary classes")
    w = original._weights(weights, len(feature_rows))
    _validate_observed(feature_rows)
    names = list(FEATURE_NAMES)
    scaler = original.fit_standardizer(feature_rows, weights, names)
    matrix = original.transform_features(feature_rows, scaler)
    initial = np.zeros(1 + len(names), dtype=np.float64)
    initial_loss, _ = original._objective(initial, matrix, y, w)
    result = minimize(original._objective, initial, args=(matrix, y, w), method="L-BFGS-B", jac=True,
                      bounds=None, options={"maxiter": 10000, "ftol": 1e-12, "gtol": 1e-9})
    parameters = np.asarray(result.x, dtype=np.float64)
    gradient = np.asarray(result.jac, dtype=np.float64)
    finite = bool(parameters.shape == gradient.shape == initial.shape
                  and np.all(np.isfinite(parameters)) and math.isfinite(float(result.fun))
                  and np.all(np.isfinite(gradient)))
    if finite:
        finite = bool(np.all(np.isfinite(parameters[0] + matrix @ parameters[1:])))
    accepted = bool(result.success and finite)
    record = {
        "schema": "candidate_acceptance_origin_ablation_fit/v0.1", "status": "fitted" if accepted else "failed",
        "arm": "A", "fit_id": fit_id, "feature_names": names,
        "input_feature_names": list(original.FEATURE_NAMES), "removed_feature_names": list(REMOVED_FEATURES),
        "scaler": scaler,
        "intercept": float(parameters[0]) if parameters.size and math.isfinite(float(parameters[0])) else None,
        "coefficients": [float(value) if math.isfinite(float(value)) else None for value in parameters[1:]],
        "training_row_count": len(row_keys), "training_row_keys": row_keys,
        "training_arrays": {"features": original._array_binding(matrix), "targets": original._array_binding(y),
                            "weights": original._array_binding(w)},
        "objective": "sum(weight*BCEWithLogits)+0.01/2*sum(beta^2); intercept unpenalized",
        "solver": {"method": "L-BFGS-B", "success": bool(result.success), "status": int(result.status),
                   "message": str(result.message), "iterations": int(result.nit), "function_evaluations": int(result.nfev),
                   "initial_loss": initial_loss,
                   "final_loss": float(result.fun) if math.isfinite(float(result.fun)) else None,
                   "raw_gradient_inf_norm": float(np.max(np.abs(gradient))) if gradient.size and np.all(np.isfinite(gradient)) else None,
                   "projected_gradient_inf_norm": float(np.max(np.abs(gradient))) if gradient.size and np.all(np.isfinite(gradient)) else None,
                   "maxiter": 10000, "ftol": 1e-12, "gtol": 1e-9, "ridge": original.RIDGE},
        "constant_score_degeneracy": False,
        "calibrated_probability_claim": False,
    }
    if not accepted:
        raise GateFitError("Frozen origin-ablation fit did not satisfy success/finite contracts", record)
    return record


def score_origin_gate(model, feature_rows):
    """Return aligned A scores without changing missing-image or input records."""
    original._require(model.get("status") == "fitted", "cannot score an unaccepted gate")
    expected = list(FEATURE_NAMES)
    original._require(model.get("arm") == "A" and model.get("feature_names") == expected
                      and model["scaler"]["feature_names"] == expected
                      and model.get("input_feature_names") == list(original.FEATURE_NAMES)
                      and model.get("removed_feature_names") == list(REMOVED_FEATURES), "model feature schema differs")
    beta = np.asarray([original._finite(value, "gate coefficient") for value in model["coefficients"]], dtype=np.float64)
    intercept = original._finite(model["intercept"], "gate intercept")
    original._require(beta.shape == (len(expected),), "gate coefficient shape differs")
    observed = []
    for row in feature_rows:
        if row.get("status") == "observed":
            observed.append(row)
        else:
            original._require(row.get("status") == "missing_image" and row.get("Q") is None
                              and row.get("values") is None and row.get("raw_features") is None
                              and tuple(row.get("feature_names", [])) == original.FEATURE_NAMES,
                              "unknown missing score state")
    _validate_observed(observed)
    matrix = original.transform_features(observed, model["scaler"])
    scores = (intercept + matrix @ beta).tolist()
    original._require(all(math.isfinite(value) for value in scores), "nonfinite gate prediction")
    values = iter(scores)
    return [next(values) if row["status"] == "observed" else None for row in feature_rows]

"""Pure, fixed-recipe logistic head and label-only training weights.

No files, pixels, model backbone, source sampling, or tracking outputs are read
or changed here. Calling ``fit`` is one optimizer attempt, never a retry loop.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import copy
import math
import warnings

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from .nba_appearance_feature_screen import normalize_feature

DIMENSIONS = 384
PENALTY = 0.005
OPTIONS = {"maxiter": 500, "maxfun": 2000, "maxcor": 10, "maxls": 40, "ftol": 1e-12, "gtol": 1e-8}
WEIGHT_SCHEMA = "nba_ball_distractor_classifier_weights/v0.1"
FIT_SCHEMA = "nba_ball_distractor_classifier_fit/v0.1"
DETECTOR_ORIGINS = {"saved_detector_candidate", "existing_accepted_reference"}
AUTHORED_ORIGIN = "source_authored_contrast"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reference_rows(preparation, proposal):
    """Transport new proposals plus exact old classes/centers and new grouping."""
    rows = copy.deepcopy(proposal["rows"])
    require([r["row_id"] for r in rows] == [r["row_id"] for r in preparation["new_review_rows"]], "New reference census/order differs")
    controls = preparation["reused_controls"]
    grouping = proposal["reused_grouping"]
    require([r["candidate_key"] for r in grouping] == [c["accepted_candidate"]["candidate_key"] for c in controls], "Existing grouping census/order differs")
    for control, group in zip(controls, grouping, strict=True):
        candidate, label, block = (control[k] for k in ("accepted_candidate", "accepted_row", "historical_block"))
        require(group["accepted_classification_unchanged"] == label["classification"] and group["role"] == block["role"]
                and group["block_id"] == block["block_id"], "Existing accepted class or role changed")
        rows.append({"row_id": candidate["candidate_key"], "origin": "existing_accepted_reference", "role": block["role"],
            "block_id": block["block_id"], "continuous_source_id": candidate["continuous_source_id"],
            "source_frame_index": candidate["source_frame_index"], "center_xy_px": copy.deepcopy(candidate["center_xy_px"]),
            "classification": label["classification"], "subtype": label["subtype"],
            "physical_object_instance_id": group["physical_object_instance_id"], "episode_id": group["episode_id"],
            "duplicate_of_row_id": None})
    return rows


def _group_key(row):
    return (row["continuous_source_id"], row["source_frame_index"], row["physical_object_instance_id"])


def _crop_key(row):
    point = np.asarray(row["center_xy_px"], dtype=np.float64)
    require(point.shape == (2,) and np.isfinite(point).all(), "Invalid crop center")
    return (row["continuous_source_id"], row["source_frame_index"], math.floor(point[0])-32, math.floor(point[1])-32)


def build_weights(rows):
    """Freeze label-only masses: pools -> blocks -> objects -> distinct crops.

    A distinct crop is the fixed native64 source box, not a floating-point
    center or provenance alias. Supplemental authored views of a sampled
    same-frame object are unused even when their crop box differs.
    """
    rows = list(rows); by_id = {}; groups = {}; excluded = []
    for row in rows:
        rid = row["row_id"]
        require(isinstance(rid, str) and rid and rid not in by_id, "Row IDs must be unique nonempty strings")
        by_id[rid] = row
        require(row["role"] in {"fit", "check"}, "Unknown reference role")
        if row["role"] != "fit":
            excluded.append({"row_id": rid, "reason": "excluded_check"})
            continue
        require(row["classification"] in {"ball", "other_object", "unresolved"}, "Unknown fit class")
        if row["classification"] == "unresolved":
            excluded.append({"row_id": rid, "reason": "unresolved"})
            continue
        require(row["origin"] in DETECTOR_ORIGINS | {AUTHORED_ORIGIN}, "Unknown training origin")
        require(all(isinstance(row[k], str) and row[k] for k in ("continuous_source_id", "block_id", "physical_object_instance_id", "episode_id")), "Resolved fit row lacks source/block/object/episode")
        require(type(row["source_frame_index"]) is int and row["source_frame_index"] >= 0, "Invalid native frame index")
        require(row["origin"] != AUTHORED_ORIGIN or row["classification"] == "other_object", "Authored contrasts must be other objects")
        _crop_key(row)
        key = _group_key(row)
        if key in groups:
            previous = groups[key][0]
            require(all(row[k] == previous[k] for k in ("classification", "subtype", "block_id", "episode_id")), "Conflicting class, subtype, block or episode within one object")
        groups.setdefault(key, []).append(row)
    # Explicit duplicate declarations must agree with the sealed object groups.
    for members in groups.values():
        for row in members:
            duplicate = row.get("duplicate_of_row_id")
            if duplicate is None:
                continue
            require(row["origin"] == AUTHORED_ORIGIN and duplicate in by_id, "Invalid supplemental duplicate reference")
            target = by_id[duplicate]
            require(target["role"] == "fit" and target["classification"] == "other_object" and target["origin"] in DETECTOR_ORIGINS
                    and _group_key(target) == _group_key(row), "Supplemental duplicate must join a resolved detector object")
    samples, object_records, crop_owner = [], [], {}
    for key, members in groups.items():
        detector = [r for r in members if r["origin"] in DETECTOR_ORIGINS]
        used = detector or members
        if detector:
            excluded.extend({"row_id": r["row_id"], "reason": "supplemental_same_object_duplicate"}
                            for r in members if r["origin"] == AUTHORED_ORIGIN)
        first = used[0]
        pool = "ball" if first["classification"] == "ball" else "detector_other" if detector else "authored_other"
        distinct = {}
        for row in used:
            crop = _crop_key(row)
            require(crop not in crop_owner or crop_owner[crop] == key, "Identical source crop assigned to different physical object groups")
            crop_owner[crop] = key
            distinct.setdefault(crop, []).append(row)
        object_record = {"group_key": list(key), "block_id": first["block_id"], "pool": pool,
                         "classification": first["classification"], "distinct_crop_count": len(distinct), "sample_indices": []}
        for crop, aliases in distinct.items():
            representative = aliases[0]
            object_record["sample_indices"].append(len(samples))
            samples.append({"representative_row_id": representative["row_id"], "row_ids": [r["row_id"] for r in aliases],
                "group_key": list(key), "block_id": first["block_id"], "pool": pool, "label": int(pool == "ball"),
                "crop_key": list(crop), "crop_xyxy_px": [crop[2], crop[3], crop[2]+64, crop[3]+64],
                "center_xy_px": copy.deepcopy(representative["center_xy_px"])})
        object_records.append(object_record)
    counts = Counter(g["pool"] for g in object_records)
    require(counts["ball"] > 0 and counts["detector_other"] > 0, "Both positive and real detector-negative groups are required")
    ga, gd = counts["authored_other"], counts["detector_other"]
    authored_mass = 0.5*min(0.5, ga/(ga+gd))
    masses = {"ball": 0.5, "authored_other": authored_mass, "detector_other": 0.5-authored_mass}
    occupied = {}
    for pool, mass in masses.items():
        blocks = defaultdict(list)
        for group in object_records:
            if group["pool"] == pool:
                blocks[group["block_id"]].append(group)
        occupied[pool] = sorted(blocks)
        require(bool(blocks) or mass == 0, "Nonzero mass has no training groups")
        for block_groups in blocks.values():
            for group in block_groups:
                value = mass/len(blocks)/len(block_groups)/group["distinct_crop_count"]
                for index in group["sample_indices"]:
                    samples[index]["weight"] = value
                    samples[index]["alias_weight_each"] = value/len(samples[index]["row_ids"])
    total = math.fsum(s["weight"] for s in samples)
    require(math.isclose(total, 1., rel_tol=0., abs_tol=1e-12), "Training weights do not sum to one")
    return {"schema_version": WEIGHT_SCHEMA, "count_unit": "source/frame/physical-object; distinct floor-centered native64 crops",
        "samples": samples, "groups": object_records, "pool_group_counts": {p: counts[p] for p in masses},
        "pool_masses": masses, "occupied_blocks": occupied, "weight_sum": total, "excluded_rows": excluded,
        "features_consulted": False, "excluded_labels_consulted_for_weights": False}


def _training_arrays(features, labels, weights):
    x, y, q = (np.asarray(v, dtype=np.float64) for v in (features, labels, weights))
    require(x.ndim == 2 and x.shape[1] == DIMENSIONS and len(x) > 0 and y.shape == q.shape == (len(x),), "Training array shapes differ")
    require(np.isfinite(x).all() and np.isfinite(y).all() and np.isfinite(q).all(), "Nonfinite training input")
    require(np.allclose(np.linalg.norm(x,axis=1), 1., rtol=0., atol=1e-12), "Training features must be L2-normalized")
    require(np.isin(y, [0.,1.]).all() and set(y) == {0.,1.}, "Training requires both binary classes")
    require((q > 0).all() and math.isclose(math.fsum(q),1.,rel_tol=0.,abs_tol=1e-12), "Positive training weights must sum to one")
    require(all(math.isclose(math.fsum(q[y == label]),.5,rel_tol=0.,abs_tol=1e-12) for label in (0.,1.)), "Class weight masses must each equal one half")
    return np.ascontiguousarray(x), y, q


def objective(parameters, features, labels, weights):
    """Stable weighted logistic objective and exact 385-dimensional gradient."""
    theta = np.asarray(parameters, dtype=np.float64)
    require(theta.shape == (DIMENSIONS+1,) and np.isfinite(theta).all(), "Expected finite 385 parameters")
    x,y,q = _training_arrays(features, labels, weights)
    with np.errstate(over="ignore",invalid="ignore"):
        logits = x@theta[:-1]+theta[-1]
        value = np.dot(q,np.logaddexp(0.,logits)-y*logits)+PENALTY*np.dot(theta[:-1],theta[:-1])
        residual = q*(expit(logits)-y)
        gradient = np.concatenate((x.T@residual+2*PENALTY*theta[:-1], [np.sum(residual)]))
    require(np.isfinite(logits).all() and np.isfinite(value) and np.isfinite(gradient).all(), "Nonfinite objective or gradient")
    return float(value), np.ascontiguousarray(gradient)


def fit_matrix(features, labels, weights):
    """One fixed optimizer call; invalid input/nonconvergence is a saved result."""
    record = {"schema_version": FIT_SCHEMA, "status": "invalid_fit", "parameters": None, "dimensions": DIMENSIONS,
        "penalty": PENALTY, "bias_penalty": 0., "initial_parameters": "all_zero", "method": "L-BFGS-B",
        "options": copy.deepcopy(OPTIONS), "boundary": 0., "calibrated": False, "optimizer_calls": 0,
        "optimizer_warnings": []}
    try:
        x,y,q = _training_arrays(features,labels,weights)
    except (ValueError, TypeError) as error:
        return {**record,"reason":"invalid_input","error_type":type(error).__name__,"error":str(error)}
    try:
        record["optimizer_calls"] = 1
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                result = minimize(objective, np.zeros(DIMENSIONS+1,dtype=np.float64), args=(x,y,q), method="L-BFGS-B", jac=True, options=copy.deepcopy(OPTIONS))
            finally:
                record["optimizer_warnings"] = [{"category": w.category.__name__, "message": str(w.message)} for w in caught]
        theta = np.asarray(result.x,dtype=np.float64)
        final_finite = theta.shape == (DIMENSIONS+1,) and np.isfinite(theta).all()
        record.update({"optimizer_success":bool(result.success), "optimizer_status":int(result.status), "message":str(result.message),
            "iterations":int(result.nit), "function_evaluations":int(result.nfev), "gradient_evaluations":int(result.njev),
            "final_parameters":theta.tolist() if final_finite else None})
        if not final_finite:
            return {**record,"reason":"nonfinite_final_parameters"}
        value,gradient = objective(theta,x,y,q)
        reported = float(result.fun)
        record.update({"objective":value,"reported_objective":reported if math.isfinite(reported) else None,
            "gradient_max_abs":float(np.max(np.abs(gradient))),"sample_count":len(x)})
        if not math.isfinite(reported) or not math.isclose(reported,value,rel_tol=1e-10,abs_tol=1e-12):
            return {**record,"reason":"invalid_final_objective"}
        if not result.success:
            return {**record,"reason":"optimizer_nonconvergence"}
        return {**record,"status":"converged_fit","reason":None,"parameters":theta.tolist()}
    except Exception as error:
        return {**record,"reason":"optimizer_error","error_type":type(error).__name__,"error":str(error)}


def fit(features_by_row_id, weight_manifest):
    """Normalize each distinct crop's descriptor; excluded rows are never read."""
    try:
        require(weight_manifest["schema_version"] == WEIGHT_SCHEMA, "Weight manifest schema differs")
        samples = weight_manifest["samples"]; features, labels, weights = [], [], []
        for sample in samples:
            feature = normalize_feature(features_by_row_id[sample["representative_row_id"]])
            for rid in sample["row_ids"]:
                if rid in features_by_row_id:
                    require(np.array_equal(feature, normalize_feature(features_by_row_id[rid])), "Same native crop has inconsistent alias features")
            features.append(feature); labels.append(sample["label"]); weights.append(sample["weight"])
    except (KeyError, ValueError, TypeError) as error:
        return {"schema_version":FIT_SCHEMA,"status":"invalid_fit","reason":"invalid_input","parameters":None,
            "optimizer_calls":0,"optimizer_warnings":[],"error_type":type(error).__name__,"error":str(error)}
    return fit_matrix(features,labels,weights)


def score_feature(parameters, feature):
    theta = np.asarray(parameters,dtype=np.float64)
    require(theta.shape == (DIMENSIONS+1,) and np.isfinite(theta).all(), "Expected finite 385 parameters")
    logit = float(np.dot(theta[:-1],normalize_feature(feature))+theta[-1])
    require(math.isfinite(logit), "Nonfinite logit")
    return logit


def decision(logit):
    value = float(logit)
    require(math.isfinite(value), "Decision requires a finite logit")
    return "ball_supported" if value > 0 else "other_supported" if value < 0 else "abstain"


def score(features_by_row_id, fitted):
    """Uncalibrated logits at the frozen zero boundary; never score an invalid fit."""
    require(fitted["status"] == "converged_fit" and fitted["parameters"] is not None, "Cannot score an invalid fit")
    return {rid: score_feature(fitted["parameters"], feature) for rid,feature in features_by_row_id.items()}

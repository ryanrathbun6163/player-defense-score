"""Small offline candidate comparison; no labels, pixels, model or interpolation.

Rewards are research costs, not probabilities. Both candidate arms use the same
rule. Weak candidates require strong model evidence before and after, but those
anchors are hypotheses: a persistent wrong object can still win.
"""
from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
from scipy.spatial import cKDTree


def _points(pool):
    return np.asarray([[c["center_x"], c["center_y"]] for c in pool], dtype=np.float64).reshape(-1, 2)


def _strong(candidate):
    return candidate.get("original_index") is not None


def _validate(pools, seconds, width, params):
    if not pools or len(pools) != len(seconds) or not math.isfinite(width) or width <= 0:
        raise ValueError("Nonempty aligned candidate/time sequence and positive source width required")
    if any(not math.isfinite(t) for t in seconds) or any(b <= a for a, b in zip(seconds, seconds[1:])):
        raise ValueError("Native times must be finite and strictly increasing")
    for pool in pools:
        if [c["candidate_index"] for c in pool] != list(range(len(pool))):
            raise ValueError("Candidate positions and indices must agree")
        for c in pool:
            if not all(math.isfinite(c[k]) for k in ("center_x", "center_y", "native_score")) or c["native_score"] <= 0:
                raise ValueError("Candidates need finite observed coordinates and positive response mass")
    numeric = ("strong_reward", "strong_relative_mass_weight", "minimum_strong_reward", "weak_reward",
               "missing_reward", "switch_missing_cost", "motion_scale_widths_per_second", "motion_cost_weight",
               "maximum_speed_widths_per_second", "weak_anchor_horizon_seconds")
    if any(not math.isfinite(params[k]) or params[k] < 0 for k in numeric):
        raise ValueError("Invalid prospective sequence costs")
    if min(params["motion_scale_widths_per_second"], params["maximum_speed_widths_per_second"],
           params["weak_anchor_horizon_seconds"]) <= 0:
        raise ValueError("Positive motion/time scales required")
    if not params["weak_requires_strong_before_and_after"]:
        raise ValueError("This experiment requires two-ended weak support")


def supported_candidates(pools, seconds, width, params):
    """Geometry-only feasibility relative to all strong hypotheses, never labels."""
    horizon = params["weak_anchor_horizon_seconds"]
    speed = width * params["maximum_speed_widths_per_second"]
    strong_points = [_points([c for c in pool if _strong(c) and c["in_source_bounds"]]) for pool in pools]
    admitted, support = [], []
    for i, pool in enumerate(pools):
        points = _points(pool)
        weak = np.asarray([not _strong(c) and c["in_source_bounds"] for c in pool], dtype=bool)
        witnesses = []
        for direction in (-1, 1):
            found = np.full(len(pool), -1, dtype=int)
            j = i + direction
            while 0 <= j < len(pools) and abs(seconds[j] - seconds[i]) <= horizon + 1e-12:
                pending = np.flatnonzero(weak & (found < 0))
                if not len(pending):
                    break
                delta = abs(seconds[j] - seconds[i])
                if len(strong_points[j]):
                    distance = np.linalg.norm(points[pending, None, :] - strong_points[j][None, :, :], axis=2)
                    found[pending[np.any(distance <= speed * delta, axis=1)]] = j
                j += direction
            witnesses.append(found)
        flags, details = [], []
        for k, c in enumerate(pool):
            if not c["in_source_bounds"]:
                flags.append(False); details.append({"reason": "outside_source"}); continue
            if _strong(c):
                flags.append(True); details.append({"reason": "native_strong"}); continue
            before, after = (None if v[k] < 0 else int(v[k]) for v in witnesses)
            allowed = before is not None and after is not None
            flags.append(allowed)
            details.append({"reason": "two_ended_model_support" if allowed else "unbracketed_weak",
                            "before_position": before, "after_position": after})
        admitted.append(np.asarray(flags, dtype=bool)); support.append(details)
    return admitted, support


def _edges(left, right, dt, width, params, left_valid, right_valid):
    """Exact feasible edges; spatial indexing avoids an uncapped K-by-K table."""
    a, b = np.flatnonzero(left_valid), np.flatnonzero(right_valid)
    if not len(a) or not len(b):
        return np.array([], dtype=int), np.array([], dtype=int), np.array([], dtype=float)
    ap, bp = _points(left)[a], _points(right)[b]
    radius = width * dt * params["maximum_speed_widths_per_second"]
    # Inflate the query by one representable float, then use the exact original
    # <= distance test. This includes boundary pairs despite tree-rounding.
    neighbors = cKDTree(ap).query_ball_tree(cKDTree(bp), np.nextafter(radius, np.inf))
    ai = np.repeat(np.arange(len(a)), [len(v) for v in neighbors])
    bi = np.asarray([j for values in neighbors for j in values], dtype=int)
    distance = np.linalg.norm(ap[ai] - bp[bi], axis=1)
    keep = distance <= radius
    costs = -params["motion_cost_weight"] * np.square(distance[keep] /
        (width * dt * params["motion_scale_widths_per_second"]))
    return a[ai[keep]], b[bi[keep]], costs


def choose_sequence(pools, seconds, source_width, parameters):
    """Return indices/null and diagnostic costs from candidate-only inputs.

    Only model pools and source timing/width enter. Reference annotations cannot
    seed a path. All original choices can change. Deterministic ties use stable
    candidate order; the explicit missing option exists even for nonempty pools.
    """
    _validate(pools, seconds, source_width, parameters)
    admitted, support = supported_candidates(pools, seconds, source_width, parameters)
    unary = []
    for pool, flags in zip(pools, admitted, strict=True):
        largest = max((c["native_score"] for c in pool if _strong(c) and c["in_source_bounds"]), default=1.0)
        values = np.full(len(pool) + 1, -np.inf, np.float64)
        values[-1] = parameters["missing_reward"]
        for j, c in enumerate(pool):
            if not flags[j]:
                continue
            values[j] = max(parameters["minimum_strong_reward"], parameters["strong_reward"] +
                            parameters["strong_relative_mass_weight"] * math.log(c["native_score"] / largest)) if _strong(c) else parameters["weak_reward"]
        unary.append(values)
    forward, parents = [unary[0].copy()], []
    for i in range(1, len(pools)):
        previous = forward[-1]
        left, right, costs = _edges(pools[i-1], pools[i], seconds[i]-seconds[i-1], source_width,
                                   parameters, admitted[i-1], admitted[i])
        edge_scores = previous[left] + costs
        values = np.full(len(pools[i])+1, previous[-1]-parameters["switch_missing_cost"])
        np.maximum.at(values, right, edge_scores)
        predecessor = np.full(len(values), len(pools[i-1]), dtype=int)
        ties = edge_scores == values[right]
        np.minimum.at(predecessor, right[ties], left[ties])
        missing_scores = previous - parameters["switch_missing_cost"]
        missing_scores[-1] = previous[-1]
        predecessor[-1] = int(np.argmax(missing_scores))
        values[-1] = missing_scores[predecessor[-1]]
        forward.append(unary[i] + values)
        parents.append(predecessor)
    last = int(np.argmax(forward[-1]))
    selected = [last]
    for predecessor in reversed(parents):
        last = int(predecessor[last]); selected.append(last)
    selected.reverse()
    backward = [None] * len(pools)
    backward[-1] = np.zeros(len(pools[-1])+1, np.float64)
    for i in range(len(pools)-2, -1, -1):
        left, right, costs = _edges(pools[i], pools[i+1], seconds[i+1]-seconds[i], source_width,
                                   parameters, admitted[i], admitted[i+1])
        future = unary[i+1]+backward[i+1]
        values = np.full(len(pools[i])+1, future[-1]-parameters["switch_missing_cost"])
        np.maximum.at(values, left, costs+future[right])
        missing_scores = future - parameters["switch_missing_cost"]
        missing_scores[-1] = future[-1]
        values[-1] = float(np.max(missing_scores))
        backward[i] = values
    diagnostics = []
    for i, index in enumerate(selected):
        marginal = forward[i] + backward[i]
        best = float(marginal[index])
        other = np.delete(marginal, index)
        finite = other[np.isfinite(other)]
        margin = best-float(finite.max()) if len(finite) else None
        diagnostics.append({"selected_pool_position": None if index == len(pools[i]) else index,
            "admitted_candidates": int(admitted[i].sum()), "pool_candidates": len(pools[i]),
            "global_alternative_margin": margin, "margin_semantics": "research objective units, not confidence",
            "selected_support": None if index == len(pools[i]) else support[i][index]})
    return [d["selected_pool_position"] for d in diagnostics], {"objective": float(np.max(forward[-1])),
        "frames": diagnostics, "reference_inputs_used": False, "interpolated_points": 0}


def observation_rows(native, pools, selected, details, variant, *, copy_pools=True):
    if len(native) != len(pools) or len(pools) != len(selected) or len(selected) != len(details["frames"]):
        raise ValueError("Selection transport length mismatch")
    rows = []
    for original, pool, index, diagnostic in zip(native, pools, selected, details["frames"], strict=True):
        row = deepcopy(original)
        row["candidates"] = deepcopy(pool) if copy_pools else pool
        row["selected_candidate_index"] = index
        row["state"] = "missing" if index is None else "observed"
        row["center_xy_px"] = None if index is None else [pool[index]["center_x"], pool[index]["center_y"]]
        row["native_score"] = None if index is None else pool[index]["native_score"]
        row["selection_method"] = variant
        row["selection_diagnostic"] = deepcopy(diagnostic)
        row["original_selected_candidate_index"] = original["selected_candidate_index"]
        row["original_center_xy_px"] = deepcopy(original["center_xy_px"])
        rows.append(row)
    return rows

"""Owned, fixed-budget dual-view experiment; no ML or hardware access on import."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from importlib import metadata
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
import traceback

from . import candidate_acceptance_neural as io

ROOT = Path(__file__).resolve().parents[2]
BASE = "data/outputs/ball_tracking/dual_view_context_v0_1"
LAUNCH_BASE = BASE + "/launch_v0_1"
NEURAL_OUTPUT = BASE + "/attempt_001"
PREPARATION = BASE + "/preparation/attempt_001/prepared.json"
MONITOR = LAUNCH_BASE + "/monitoring/attempt_001"
MODULE = "src.ball_tracking.dual_view_context_experiment"
CONFIG = "configs/ball_tracking/proposals/dual_view_context_v0_1.json"
SPEC_SHA256 = "d78189654b2070ad11544c8711fa8fa357ed65171a85e9d69f149697e9109fbe"
PROTOCOL = "docs/ball_tracking_dual_view_context_protocol.md"
PROTOCOL_SHA256 = "63a92ba5700cf0aec2e9128d4b9fbe63977df555fd51bf4533c4f101dd77f889"
EXPECTED_BRANCH = "codex/ball-detector-baseline"
EXPECTED_HEAD = "8c040fca385dd8fffa0d7a13c45c53e79950bae1"
ORIGINAL = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1/attempt_005"
FIT_NAMES = ("leave_chi_out", "leave_den_out", "leave_sac_out", "all_nba")
ARMS = ("LL", "LC")
SEED, SHUFFLE_SEED, EPOCHS, BATCH_SIZE = 20261030, 20261028, 6, 32
MAX_TOTAL_SECONDS, CLEANUP_RESERVE_SECONDS = 5400, 30
GPU = io.GPU
CALL_BUDGETS = {"local_capture": (2776, 88742), "training": (19740, 630864),
                "scoring": (5554, 177484), "local_parity": (4, 128), "auxiliary_parity": (8, 256)}
COUNTER_EXPECTED = {key: value for kind, (calls, presentations) in CALL_BUDGETS.items()
                    for key, value in ((kind+"_forwards_attempted", calls),
                                       (kind+"_forwards_returned", calls),
                                       (kind+"_candidate_presentations", presentations))}
COUNTER_EXPECTED["optimizer_updates"] = 19740
REQUIRED_IMPLEMENTATION = {
    "src/ball_tracking/dual_view_context_experiment.py", "src/ball_tracking/dual_view_context_model.py",
    "src/ball_tracking/dual_view_context_data.py", "tests/test_dual_view_context_experiment.py",
    "tests/test_dual_view_context_model.py", "tests/test_dual_view_context_data.py",
    "src/ball_tracking/candidate_acceptance_neural.py", "src/ball_tracking/candidate_quality_model.py",
    "src/ball_tracking/candidate_quality_pilot.py", "src/ball_tracking/candidate_quality_data.py",
    "src/ball_tracking/candidate_quality_native_cable_resume.py", "src/ball_tracking/continuation_owned_guard.py",
    "src/ball_tracking/point_feature_inference.py", "src/ball_tracking/nba_appearance_feature_screen.py",
    "src/ball_tracking/annotations.py", "src/ball_tracking/nba_annotations.py",
    "src/ball_tracking/nba_wasb_diagnostic.py", "src/ball_tracking/wasb_adapter.py",
    "src/ball_tracking/wasb_experiment.py", "src/ball_tracking/weak_response_capture.py",
    "src/ball_tracking/candidate_quality_cable_reference_diagnostic.py",
    "src/ball_tracking/candidate_quality_post_driver_resume.py", "src/ball_tracking/candidate_quality_resume.py",
}
CONTROL_FILES = {ORIGINAL + f"/{fit}/{name}" for fit in FIT_NAMES for name in
                 ("initial_tensor_fingerprints.json", "final_tensor_fingerprints.json", "final_trainable.pth")}
check, read, rows = io.check, io.read, io.rows
binding, bound, write_once, append, stamp = io.binding, io.bound, io.write_once, io.append, io.stamp
validate_readiness = io.validate_readiness


def basic_binding(link):
    return {key: link[key] for key in ("path", "bytes", "sha256")}


def batches(keys):
    for offset in range(0, len(keys), BATCH_SIZE):
        yield keys[offset:offset+BATCH_SIZE]


def epoch_order(weights, epoch):
    check(type(epoch) is int and 1 <= epoch <= EPOCHS, "Epoch outside frozen recipe")
    order = [row["row_key"] for row in weights]
    random.Random(SHUFFLE_SEED+epoch).shuffle(order)
    return order


def validate_loaded(loaded, spec):
    """Independently verify actual consumer membership, objective and workloads."""
    check(set(loaded["fits"]) == set(FIT_NAMES), "Four original fits required")
    all_rows = loaded["rows"]
    totals = Counter()
    plans = {plan["name"]: plan for plan in spec["training"]["fits"]}
    for fit in FIT_NAMES:
        item, plan = loaded["fits"][fit], plans[fit]
        weights = item["weights"]
        keys = [w["row_key"] for w in weights]
        check(len(keys) == len(set(keys)) == plan["fit_candidates"], "Fit membership count differs")
        check(all(key.startswith("p:") and key in all_rows for key in keys), "Only original package points may train")
        for weight in weights:
            row = all_rows[weight["row_key"]]
            check(row["game_id"] in plan["fit_game_ids"] and row["game_id"] not in plan["held_out_game_ids"]
                  and weight["target"] in (0, 1), "Fit game/known-target membership differs")
            mass = weight["objective_weight"]
            check(isinstance(mass, (int, float)) and math.isfinite(mass) and mass > 0
                  and math.isclose(weight["training_multiplier"], len(keys)*mass, rel_tol=1e-12),
                  "Original loss mass/multiplier differs")
        check(math.isclose(math.fsum(w["objective_weight"] for w in weights), 1., abs_tol=1e-10),
              "Objective weight mass differs")
        check(item["saved_Q_checkpoint"] == plan["saved_Q_checkpoint"], "Wrong fold Q checkpoint")
        capture_keys = []
        check([g["name"] for g in item["capture_groups"]] ==
              (["package", "external", "BKN"] if fit == "all_nba" else ["package"]), "Capture stream layout differs")
        check([g["name"] for g in item["score_groups"]] ==
              (["package_all", "external", "BKN"] if fit == "all_nba" else ["package_held", "training_health"]),
              "Final scoring stream layout differs")
        for group in item["capture_groups"]:
            group_keys = group["row_keys"]
            check(len(group_keys) == len(set(group_keys)) > 0 and set(group_keys) <= set(all_rows),
                  "Duplicate/unknown capture identity")
            capture_keys.extend(group_keys)
            totals["local_capture_calls"] += math.ceil(len(group_keys)/BATCH_SIZE)
            totals["local_capture_presentations"] += len(group_keys)
        check(len(capture_keys) == len(set(capture_keys)) and set(keys) <= set(capture_keys),
              "Capture missing fit row or reuses a key")
        package = item["capture_groups"][0]["row_keys"]
        check(len(package) == plan["needed_local_frozen_feature_rows_fit_union_package_score"],
              "Original package union differs")
        for group in item["score_groups"]:
            group_keys = group["row_keys"]
            check(len(group_keys) == len(set(group_keys)) > 0 and set(group_keys) <= set(capture_keys),
                  "Score stream lacks captured local feature or duplicates identity")
            if group["name"] == "training_health":
                check(group_keys == keys, "Training-health order must equal original fitting order")
            if group["name"] == "package_held":
                check(len(group_keys) == plan["package_score_candidates"]
                      and all(all_rows[k]["game_id"] in plan["held_out_game_ids"] for k in group_keys),
                      "Held game score membership differs")
            totals["scoring_calls"] += len(ARMS)*math.ceil(len(group_keys)/BATCH_SIZE)
            totals["scoring_presentations"] += len(ARMS)*len(group_keys)
        check(set(item["saved_Q_scores"]) <= set(capture_keys) and item["saved_Q_scores"],
              "Saved Q comparison identities missing")
        calls = EPOCHS*math.ceil(len(keys)/BATCH_SIZE)
        presentations = EPOCHS*len(keys)
        check(calls == plan["steps_six_epochs"] and presentations == plan["presentations_six_epochs"],
              "Original update/exposure budget differs")
        totals["training_calls"] += len(ARMS)*calls
        totals["training_presentations"] += len(ARMS)*presentations
    for kind in ("local_capture", "training", "scoring"):
        check((totals[kind+"_calls"], totals[kind+"_presentations"]) == CALL_BUDGETS[kind],
              "Declared physical workload differs: " + kind)
    return dict(totals)


def validate_authorization(authorization, freeze_binding, specification):
    check(authorization.get("execution_approved") is True
          and authorization.get("execution_freeze") == freeze_binding
          and authorization.get("specification") == specification and authorization.get("scope") == COUNTER_EXPECTED
          and authorization.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and isinstance(authorization.get("user_statement"), str) and authorization["user_statement"].strip(),
          "Authorization must bind this freeze, specification and exact workload")
    check(all(authorization.get(key) is False for key in
              ("automatic_retry", "automatic_extension", "protected_access_approved", "new_labels_approved", "selector_approved")),
          "Authorization exceeds fixed experiment scope")


def preflight(root=ROOT, require_authorization=True, *, require_approval=None):
    """Read/hash-only guard. No Torch import, model construction or GPU query."""
    if require_approval is not None:
        require_authorization = require_approval
    root = Path(root).resolve()
    spec, specification = read(root/CONFIG), binding(root, root/CONFIG)
    check(specification["sha256"] == SPEC_SHA256 and spec["protocol"]["path"] == PROTOCOL
          and spec["protocol"]["sha256"] == PROTOCOL_SHA256, "Frozen design differs")
    for name, version in io.RUNTIME.items():
        check(metadata.version(name) == version, "Pinned runtime metadata differs: " + name)
    options = {"cwd": root, "text": True, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    check(subprocess.check_output(["git", "branch", "--show-current"], **options).strip() == EXPECTED_BRANCH,
          "Frozen project branch differs")
    check(subprocess.check_output(["git", "rev-parse", "HEAD"], **options).strip() == EXPECTED_HEAD,
          "Frozen project HEAD differs")
    check(not subprocess.check_output(["git", "diff", "--cached", "--name-only"], **options).strip(),
          "Index must remain empty")
    from . import dual_view_context_model as model_api
    model_api.local_contract(root)
    freeze_file = root/LAUNCH_BASE/"execution_freeze.json"
    freeze = read(freeze_file)
    check(freeze.get("status") == "frozen_for_authorized_execution"
          and freeze.get("specification") == specification and freeze.get("protocol") == spec["protocol"]
          and freeze.get("launch_base") == LAUNCH_BASE and freeze.get("neural_output") == NEURAL_OUTPUT,
          "Freeze identity, destination or specification differs")
    check(not (root/NEURAL_OUTPUT).exists(), "Output already exists; retry/resume is not authorized")
    implementation, inputs = freeze.get("implementation", []), freeze.get("inputs", [])
    check(REQUIRED_IMPLEMENTATION <= {link["path"] for link in implementation}, "Runtime source/test bindings missing")
    index = {link["path"]: link for link in inputs}
    check(len(index) == len(inputs) and CONTROL_FILES <= set(index)
          and index.get(PREPARATION) == freeze.get("prepared"), "Frozen original control/preparation coverage differs")
    for plan in spec["training"]["fits"]:
        for name in ("weights", "manifest", "saved_Q_checkpoint", "saved_Q_scores"):
            check(index.get(plan[name]["path"]) == plan[name], "Frozen original fit input missing: " + name)
    check(isinstance(freeze.get("review"), list) and freeze["review"], "Independent review missing")
    for link in [spec["protocol"], *implementation, *inputs, freeze["focused_tests"], *freeze["review"]]:
        bound(root, link)
    from . import dual_view_context_data as data
    loaded = data.load_prepared(root, verify=True)
    validate_loaded(loaded, spec)
    if require_authorization:
        freeze_binding = binding(root, freeze_file)
        auth_file = root/LAUNCH_BASE/"execution_authorization.json"
        validate_authorization(read(auth_file), freeze_binding, specification)
        readiness = read(root/LAUNCH_BASE/"launch_readiness.json")
        validate_readiness(readiness, freeze_binding, binding(root, auth_file))
        for link in readiness["sources"]:
            bound(root, link)
    check("torch" not in sys.modules, "Torch imported before authorized runtime")
    return spec, freeze


def validate_policy(policy):
    check(policy.get("module") == MODULE and policy.get("arguments") == ["--run", "--monitor", MONITOR]
          and policy.get("sample_seconds") == 2 and policy.get("temperature_stop_C") == 80
          and policy.get("telemetry_timeout_seconds") == 5 and policy.get("grace_seconds") == 10
          and policy.get("automatic_retry") is False and policy.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and policy.get("soft_stop_seconds") == MAX_TOTAL_SECONDS-CLEANUP_RESERVE_SECONDS
          and policy.get("gpu_uuid") == GPU, "Owned supervisor policy differs")


def remaining_wall_seconds(policy, now=None):
    return io.remaining_wall_seconds(policy, now)


def validate_counters(counters):
    check(counters == COUNTER_EXPECTED, "Exact backbone forward/presentation/update accounting differs")


def call_started(counters, kind, journal, details):
    key = kind+"_forwards_attempted"
    check(kind in CALL_BUDGETS and counters[key] < COUNTER_EXPECTED[key], "Forward budget exhausted")
    counters[key] += 1
    append(journal, {"event": kind+"_start", **details, "counters": dict(counters)})


def call_returned(counters, kind, journal, details):
    returned, presentations = kind+"_forwards_returned", kind+"_candidate_presentations"
    check(counters[returned] < counters[kind+"_forwards_attempted"], "Return without attempted forward")
    check(counters[presentations]+details["batch_count"] <= COUNTER_EXPECTED[presentations], "Presentation budget exceeded")
    counters[returned] += 1
    counters[presentations] += details["batch_count"]
    append(journal, {"event": kind+"_return", **details, "counters": dict(counters)})


def restore_control(model, checkpoint, fit):
    import torch
    check(checkpoint.get("fit") == fit and checkpoint.get("epoch") == 6, "Saved Q identity/endpoint differs")
    state = checkpoint["trainable_state"]
    parameters = {n: p for n, p in model.named_parameters() if p.requires_grad}
    check(set(state) == set(parameters), "Saved Q trainable names differ")
    with torch.no_grad():
        for name, parameter in parameters.items():
            value = state[name]
            check(isinstance(value, torch.Tensor) and value.device.type == "cpu" and value.dtype == torch.float32
                  and value.shape == parameter.shape and bool(torch.isfinite(value).all()), "Saved Q tensor differs: " + name)
            parameter.copy_(value.to(device=parameter.device))


def verify_saved_Q(captured, saved, all_rows):
    """Protect scalar signs and canonical package winners without replacing controls."""
    import numpy as np
    check(set(saved) <= set(captured) and saved, "Missing original score overlap")
    keys = list(saved)
    old, new = np.array([saved[k] for k in keys]), np.array([captured[k] for k in keys])
    check(np.isfinite(old).all() and np.isfinite(new).all()
          and np.allclose(new, old, atol=1e-5, rtol=1e-6), "Captured Q logits differ from saved controls")
    check(np.array_equal(old > 0, new > 0), "Captured Q zero-boundary sign changed")
    frames = defaultdict(list)
    for key in keys:
        row = all_rows[key]
        if key.startswith(("p:", "b:")) or (key.startswith("e:") and row.get("cohort") == "HOU_main"):
            frames[(key[:2], row["frame_key"])].append(key)
    for group in frames.values():
        # Original point-quality selector breaks exact score ties by candidate ID.
        winner_old = min(group, key=lambda k: (-saved[k], all_rows[k]["original_id"]))
        winner_new = min(group, key=lambda k: (-captured[k], all_rows[k]["original_id"]))
        check(winner_old == winner_new, "Recaptured Q canonical fixed choice changed")
    return {"overlap_rows": len(keys), "canonical_frame_choices": len(frames), "atol": 1e-5, "rtol": 1e-6,
            "max_absolute_difference": float(np.max(np.abs(old-new))), "all_signs_identical": True,
            "all_canonical_winner_ids_identical": True, "original_scalar_files_unchanged": True}


def parameter_deltas(model, initial_state):
    """Quantify actual auxiliary/head changes independently of hash inequality."""
    import torch
    stats = {group: {"squared_L2": 0., "max_absolute": 0., "changed_values": 0, "parameters": 0}
             for group in ("backbone", "head")}
    actual = {name: p for name, p in model.named_parameters() if p.requires_grad}
    check(set(actual) == set(initial_state), "Initial delta state parameter names differ")
    for name, parameter in actual.items():
        initial = initial_state[name]
        current = parameter.detach().cpu()
        check(current.shape == initial.shape and current.dtype == initial.dtype == torch.float32,
              "Parameter delta shape/dtype differs")
        delta = current.to(dtype=torch.float64)-initial.to(dtype=torch.float64)
        check(bool(torch.isfinite(delta).all()), "Nonfinite final parameter delta")
        item = stats[name.split(".", 1)[0]]
        item["squared_L2"] += float((delta*delta).sum())
        item["max_absolute"] = max(item["max_absolute"], float(delta.abs().max()))
        item["changed_values"] += int((delta != 0).sum())
        item["parameters"] += delta.numel()
    for item in stats.values():
        item["L2"] = math.sqrt(item.pop("squared_L2"))
        check(item["L2"] > 0 and item["changed_values"] > 0, "Trainable group did not change")
    return stats


def open_caches(root, loaded):
    import numpy as np
    opened = {}
    try:
        for link in [*loaded["caches"]["local"], loaded["caches"]["context"]]:
            path = io.owned_path(root, link["path"])
            check(link["path"] not in opened, "Duplicate pixel cache")
            cache = np.load(path, mmap_mode="r", allow_pickle=False)
            check(list(cache.shape) == link["shape"] and str(cache.dtype) == link["dtype"], "Pixel cache contract differs")
            opened[link["path"]] = cache
        return opened
    except BaseException:
        close_caches(opened)
        raise


def close_caches(caches):
    for cache in caches.values():
        if getattr(cache, "_mmap", None) is not None:
            cache._mmap.close()


def input_arrays(loaded, caches, keys, arm):
    """Actual worker consumer, shared by CPU fixture tests and all runtime paths."""
    import numpy as np
    from .dual_view_context_model import preprocess_raw
    check(arm in ARMS and 0 < len(keys) <= BATCH_SIZE, "Invalid input arm/batch")
    pixels, points = [], []
    for key in keys:
        row = loaded["rows"][key]
        if arm == "LL":
            location = row["local_cache"]
            raw = caches[location["path"]][location["index"]]
            weights = row["local_point_weights"]
        else:
            raw = caches[loaded["caches"]["context"]["path"]][row["context_cache_index"]]
            weights = row["context_point_weights"]
        pixels.append(preprocess_raw(raw, arm))
        points.append(weights)
    return np.stack(pixels), np.asarray(points, dtype=np.float64)


def score_rows(keys, logits, fit, arm, group, offset):
    check(len(keys) == len(logits) and all(isinstance(v, (int, float)) and math.isfinite(v) for v in logits),
          "Score transport contains missing/nonfinite values")
    return [{"row_key": key, "quality_logit": value, "fit": fit, "arm": arm, "group": group,
             "feature_index": offset+i} for i, (key, value) in enumerate(zip(keys, logits, strict=True))]


def run(root, monitor, arguments):
    root = Path(root).resolve()
    check(monitor == MONITOR and list(arguments) == ["--run", "--monitor", MONITOR], "Only declared owned launch is allowed")
    spec, freeze = preflight(root, require_authorization=True)
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root/monitor, MODULE, arguments)
    policy = read(root/monitor/"policy.json")
    validate_policy(policy)
    remaining = remaining_wall_seconds(policy)
    from .candidate_quality_native_cable_resume import verify_runtime_driver
    driver = verify_runtime_driver(policy["gpu_uuid"])
    out = root/NEURAL_OUTPUT
    out.mkdir(parents=True, exist_ok=False)
    began, done, caches, feature_caches = time.monotonic(), threading.Event(), {}, {}
    counters = dict.fromkeys(COUNTER_EXPECTED, 0)
    freeze_binding = binding(root, root/LAUNCH_BASE/"execution_freeze.json")
    write_once(out/"started.json", {"at_utc": stamp(), "ownership": ownership, "driver": driver,
               "execution_freeze": freeze_binding, "prepared": freeze["prepared"],
               "execution_authorization": binding(root, root/LAUNCH_BASE/"execution_authorization.json"),
               "launch_readiness": binding(root, root/LAUNCH_BASE/"launch_readiness.json"),
               "settings_changed_by_worker": False, "new_work_only": True})

    def deadline():
        if not done.wait(max(0., remaining-CLEANUP_RESERVE_SECONDS)):
            (root/monitor/"STOP").touch(exist_ok=True)

    def continuation_check():
        check(not (root/monitor/"STOP").exists(), "Owned supervisor requested STOP")
        remaining_wall_seconds(policy)

    threading.Thread(target=deadline, daemon=True).start()
    try:
        continuation_check()
        check("torch" not in sys.modules, "Torch imported before authorized deterministic runtime")
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        import numpy as np
        import torch
        from . import candidate_quality_model as original_model
        from . import candidate_quality_pilot as pilot
        from . import dual_view_context_model as model_api
        from . import dual_view_context_data as data
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        loaded = data.load_prepared(root, verify=True)
        validate_loaded(loaded, spec)
        caches = open_caches(root, loaded)
        journal, local_artifacts, all_scores, results = out/"journal.jsonl", [], [], []
        feature_locations, capture_checks = {}, []

        def input_batch(keys, arm):
            pixels, points = input_arrays(loaded, caches, keys, arm)
            return torch.from_numpy(pixels).to("cuda"), torch.from_numpy(points).to("cuda")

        def local_batch(fit, keys):
            values = np.stack([feature_caches[feature_locations[fit][key][0]][feature_locations[fit][key][1]] for key in keys])
            return torch.from_numpy(values).to("cuda")

        # Capture every local fold representation and verify every original overlap
        # before any auxiliary optimizer/model fitting can begin.
        for fit in FIT_NAMES:
            continuation_check()
            item = loaded["fits"][fit]
            fit_dir = out/"local_capture"/fit
            fit_dir.mkdir(parents=True, exist_ok=False)
            model = original_model.build_model(root, device="cuda", execution_authorized=True)
            checkpoint = torch.load(bound(root, item["saved_Q_checkpoint"]), map_location="cpu", weights_only=True)
            restore_control(model, checkpoint, fit)
            del checkpoint
            expected = read(root/ORIGINAL/fit/"final_tensor_fingerprints.json")
            before = {"frozen": original_model.frozen_fingerprint(model),
                      "trainable_groups": pilot.trainable_group_fingerprints(model)}
            check(before["frozen"] == expected["frozen"] and before["trainable_groups"] == expected["trainable_groups"],
                  "Restored Q checkpoint fingerprints differ")
            model.eval()
            locations, captured, first = {}, {}, True
            for group in item["capture_groups"]:
                name, keys = group["name"], group["row_keys"]
                feature_path, score_path = fit_dir/(name+"_features.npy"), fit_dir/(name+".jsonl")
                check(not feature_path.exists(), "Local feature output already exists")
                matrix = np.lib.format.open_memmap(feature_path, mode="w+", dtype=np.float64, shape=(len(keys), 384))
                try:
                    with score_path.open("x", encoding="utf-8", newline="\n") as stream, torch.inference_mode():
                        offset = 0
                        for batch in batches(keys):
                            continuation_check()
                            pixels, points = input_batch(batch, "LL")
                            details = {"fit": fit, "group": name, "row_keys": batch, "batch_count": len(batch)}
                            call_started(counters, "local_capture", journal, details)
                            logits, features = model.forward_with_features(pixels, points)
                            call_returned(counters, "local_capture", journal, details)
                            if first:
                                continuation_check()
                                check(len(batch) == 32, "Local parity must use exactly32 actual first points")
                                call_started(counters, "local_parity", journal, details)
                                parity = pilot.first_batch_parity(model, pixels, points, features)
                                call_returned(counters, "local_parity", journal, details)
                                write_once(fit_dir/"producer_parity.json", parity)
                                first = False
                            values, array = logits.detach().cpu().tolist(), features.detach().cpu().numpy()
                            check(array.dtype == np.float64 and array.shape == (len(batch), 384)
                                  and np.isfinite(array).all(), "Local feature serialization differs")
                            matrix[offset:offset+len(batch)] = array
                            for i, (key, value) in enumerate(zip(batch, values, strict=True)):
                                captured[key] = value
                                locations[key] = (feature_path.relative_to(root).as_posix(), offset+i)
                                stream.write(json.dumps({"row_key": key, "quality_logit": value, "fit": fit,
                                                         "group": name, "feature_index": offset+i}, allow_nan=False)+"\n")
                            stream.flush()
                            os.fsync(stream.fileno())
                            offset += len(batch)
                            del pixels, points, logits, features
                        check(offset == len(keys), "Local feature transport count differs")
                    matrix.flush()
                finally:
                    matrix._mmap.close()
                feature_key = feature_path.relative_to(root).as_posix()
                feature_caches[feature_key] = np.load(feature_path, mmap_mode="r", allow_pickle=False)
                local_artifacts.append({**binding(root, score_path), "fit": fit, "group": name, "rows": len(keys),
                                        "features": binding(root, feature_path)})
            parity = verify_saved_Q(captured, item["saved_Q_scores"], loaded["rows"])
            write_once(fit_dir/"saved_Q_overlap_parity.json", parity)
            check(original_model.frozen_fingerprint(model) == before["frozen"]
                  and pilot.trainable_group_fingerprints(model) == before["trainable_groups"]
                  and all(p.grad is None for p in model.parameters()), "Local capture changed Q or created gradients")
            write_once(fit_dir/"frozen_Q_preservation.json", {"before": before, "after_identical": True,
                       "checkpoint": item["saved_Q_checkpoint"], "optimizer_updates": 0})
            feature_locations[fit] = locations
            capture_checks.append({"fit": fit, **parity})
            del model
            torch.cuda.empty_cache()
            print(json.dumps({"event": "local_capture_complete", "fit": fit, "parity": parity}), flush=True)
        check(all(counters[k] == COUNTER_EXPECTED[k] for k in counters if k.startswith("local_")),
              "Local capture/parity stage budget differs")
        write_once(out/"all_local_capture_verified_before_fitting.json", {"checks": capture_checks,
                   "counters": dict(counters), "local_captures": local_artifacts, "optimizer_updates": 0})

        def score_group(model, fit, arm, group, fit_dir):
            name, keys = group["name"], group["row_keys"]
            score_dir = fit_dir/"scores"
            score_dir.mkdir(exist_ok=True)
            score_path = score_dir/(name+".jsonl")
            point_path, cls_path = score_dir/(name+"_point.npy"), score_dir/(name+"_cls.npy")
            check(not point_path.exists() and not cls_path.exists(), "Auxiliary feature output already exists")
            point_array = np.lib.format.open_memmap(point_path, mode="w+", dtype=np.float64, shape=(len(keys), 384))
            cls_array = np.lib.format.open_memmap(cls_path, mode="w+", dtype=np.float64, shape=(len(keys), 384))
            try:
                with score_path.open("x", encoding="utf-8", newline="\n") as stream, torch.inference_mode():
                    offset = 0
                    for batch in batches(keys):
                        continuation_check()
                        pixels, points = input_batch(batch, arm)
                        local = local_batch(fit, batch)
                        details = {"fit": fit, "arm": arm, "group": name, "row_keys": batch, "batch_count": len(batch)}
                        call_started(counters, "scoring", journal, details)
                        logits, point, cls = model.forward_with_features(local, pixels, points)
                        call_returned(counters, "scoring", journal, details)
                        values = logits.detach().cpu().tolist()
                        point_array[offset:offset+len(batch)] = point.detach().cpu().numpy()
                        cls_array[offset:offset+len(batch)] = cls.detach().cpu().numpy()
                        for row in score_rows(batch, values, fit, arm, name, offset):
                            stream.write(json.dumps(row, allow_nan=False)+"\n")
                        stream.flush()
                        os.fsync(stream.fileno())
                        offset += len(batch)
                        del local, pixels, points, logits, point, cls
                    check(offset == len(keys), "Final score identity transport count differs")
                point_array.flush()
                cls_array.flush()
            finally:
                point_array._mmap.close()
                cls_array._mmap.close()
            return {**binding(root, score_path), "fit": fit, "arm": arm, "group": name,
                    "role": group["role"], "rows": len(keys), "point_features": binding(root, point_path),
                    "CLS_features": binding(root, cls_path)}

        initial_reference, initial_trainable = None, None
        for fit in FIT_NAMES:
            item = loaded["fits"][fit]
            weights = item["weights"]
            by_key = {w["row_key"]: w for w in weights}
            expected_steps = EPOCHS*math.ceil(len(weights)/BATCH_SIZE)
            for arm in ARMS:
                continuation_check()
                fit_dir = out/"fits"/fit/arm
                fit_dir.mkdir(parents=True, exist_ok=False)
                write_once(fit_dir/"fit_manifest.json", {"fit": fit, "arm": arm, "weights": weights,
                           "score_groups": item["score_groups"], "shuffle_seed_base": SHUFFLE_SEED, "epochs": EPOCHS,
                           "prepared": freeze["prepared"], "execution_freeze": freeze_binding})
                random.seed(SEED)
                np.random.seed(SEED)
                torch.manual_seed(SEED)
                torch.cuda.manual_seed_all(SEED)
                model = model_api.build_model(root, device="cuda", execution_authorized=True)
                frozen_before = model_api.frozen_fingerprint(model)
                trainable_before = pilot.trainable_group_fingerprints(model)
                initial = {"frozen": frozen_before, "trainable_groups": trainable_before}
                if initial_reference is None:
                    initial_reference = initial
                    initial_trainable = {n: p.detach().cpu().clone() for n, p in model.named_parameters() if p.requires_grad}
                    io.save_checkpoint_once(out/"shared_initial_trainable.pth", {"trainable_state": initial_trainable,
                                            "seed": SEED, "head_seed_reset_after_encoder_load": True,
                                            "fingerprints": initial, "freeze_sha256": freeze_binding["sha256"]})
                check(initial == initial_reference, "Eight auxiliary/head initial states must be identical")
                write_once(fit_dir/"initial_tensor_fingerprints.json", initial)
                write_once(fit_dir/"trainable_parameters.json", model_api.trainable_manifest(model))
                optimizer = torch.optim.AdamW(model_api.optimizer_parameter_groups(model), betas=(.9, .999), eps=1e-8)
                fit_steps, visits, recoveries = 0, Counter(), []
                for epoch in range(1, EPOCHS+1):
                    model.train()
                    epoch_loss, group_losses, epoch_steps = 0., defaultdict(lambda: [0., 0., 0]), 0
                    order = epoch_order(weights, epoch)
                    for keys in batches(order):
                        continuation_check()
                        pixels, points = input_batch(keys, arm)
                        local = local_batch(fit, keys)
                        targets = torch.tensor([by_key[k]["target"] for k in keys], device="cuda", dtype=torch.float32)
                        scale = torch.tensor([by_key[k]["training_multiplier"] for k in keys], device="cuda", dtype=torch.float32)
                        optimizer.zero_grad(set_to_none=True)
                        details = {"fit": fit, "arm": arm, "epoch": epoch, "step": fit_steps,
                                   "row_keys": keys, "batch_count": len(keys)}
                        call_started(counters, "training", journal, details)
                        logits, point, cls = model.forward_with_features(local, pixels, points)
                        call_returned(counters, "training", journal, details)
                        first = fit_steps == 0
                        if first:
                            continuation_check()
                            check(len(keys) == 32, "Auxiliary parity requires32 actual first fitting points")
                            call_started(counters, "auxiliary_parity", journal, details)
                            parity = model_api.first_batch_parity(model, pixels, points, point, cls)
                            call_returned(counters, "auxiliary_parity", journal, details)
                            write_once(fit_dir/"initial_producer_parity.json", parity)
                        check(logits.shape == targets.shape, "Training target/logit shape differs")
                        losses = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
                        loss = (losses*scale).mean()
                        check(bool(torch.isfinite(loss)), "Nonfinite weighted training loss")
                        loss.backward()
                        if first:
                            write_once(fit_dir/"first_gradient_checks.json", pilot.check_first_gradients(model))
                        norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],
                                                              max_norm=1., error_if_nonfinite=True)
                        check(all(p.grad is None for p in model.parameters() if not p.requires_grad)
                              and local.grad is None and not local.requires_grad, "Frozen/local gradient appeared")
                        optimizer.step()
                        fit_steps += 1
                        epoch_steps += 1
                        counters["optimizer_updates"] += 1
                        check(counters["optimizer_updates"] <= COUNTER_EXPECTED["optimizer_updates"], "Update budget exceeded")
                        visits.update(keys)
                        weighted = (losses*scale).detach().cpu().tolist()
                        for key, value in zip(keys, weighted, strict=True):
                            weight = by_key[key]
                            group = weight.get("target_group", loaded["rows"][key].get("target_group", str(weight["target"])))
                            contribution = value/len(weights)
                            epoch_loss += contribution
                            bucket = group_losses[group]
                            bucket[0] += contribution
                            bucket[1] += weight["objective_weight"]
                            bucket[2] += 1
                        append(journal, {"event": "optimizer_update", **details, "step": fit_steps,
                                         "weighted_batch_loss": float(loss.detach().cpu()),
                                         "gradient_norm_before_clip": float(norm.detach().cpu()), "counters": dict(counters)})
                        del local, pixels, points, targets, scale, logits, point, cls, losses, loss, norm
                    check(epoch_steps == math.ceil(len(weights)/BATCH_SIZE)
                          and all(visits[k] == epoch for k in by_key), "Epoch exact exposures differ")
                    append(out/"epochs.jsonl", {"fit": fit, "arm": arm, "epoch": epoch,
                           "online_weighted_BCE": epoch_loss, "group_loss_objective_mass_count": dict(group_losses),
                           "note": "Original full-epoch objective contribution; model changes within epoch; not validation"})
                    continuation_check()
                    recovery = fit_dir/f"recovery_epoch_{epoch:02d}.pth"
                    io.save_checkpoint_once(recovery, {"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                        "optimizer_state": optimizer.state_dict(), "epoch": epoch, "fit": fit, "arm": arm,
                        "fit_steps": fit_steps, "counters": dict(counters), "actual_exposures": dict(visits),
                        "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                        "torch_rng": torch.get_rng_state(), "cuda_rng": torch.cuda.get_rng_state_all(),
                        "freeze_sha256": freeze_binding["sha256"], "purpose": "Recovery requires separate authorization; epoch6 fixed endpoint"})
                    recoveries.append(binding(root, recovery))
                    append(out/"recovery_checkpoints.jsonl", recoveries[-1])
                    print(json.dumps({"fit": fit, "arm": arm, "epoch": epoch, "steps": fit_steps,
                                      "online_weighted_BCE": epoch_loss}), flush=True)
                check(fit_steps == expected_steps and set(visits) == set(by_key)
                      and all(value == EPOCHS for value in visits.values()), "Final fit exposure/update budget differs")
                write_once(fit_dir/"actual_exposure.json", [{"row_key": k, "visits": visits[k]} for k in by_key])
                check(model_api.frozen_fingerprint(model) == frozen_before, "Frozen auxiliary tensors changed")
                trainable_after = pilot.trainable_group_fingerprints(model)
                check(all(trainable_after[g] != trainable_before[g] for g in trainable_before), "Auxiliary/head did not both change")
                write_once(fit_dir/"final_tensor_fingerprints.json", {"frozen": frozen_before, "trainable_groups": trainable_after,
                           "frozen_unchanged": True, "backbone_and_head_changed": True})
                write_once(fit_dir/"parameter_deltas.json", parameter_deltas(model, initial_trainable))
                checkpoint = fit_dir/"final_trainable.pth"
                io.save_checkpoint_once(checkpoint, {"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                                        "epoch": EPOCHS, "fit": fit, "arm": arm, "fit_steps": fit_steps,
                                        "freeze_sha256": freeze_binding["sha256"]})
                model.eval()
                scores = [score_group(model, fit, arm, group, fit_dir) for group in item["score_groups"]]
                all_scores.extend(scores)
                result = {"fit": fit, "arm": arm, "steps": fit_steps, "checkpoint": binding(root, checkpoint),
                          "recovery_checkpoints": recoveries, "scores": scores,
                          "fit_manifest": binding(root, fit_dir/"fit_manifest.json"),
                          "actual_exposure": binding(root, fit_dir/"actual_exposure.json"),
                          "health": [binding(root, fit_dir/name) for name in ("initial_tensor_fingerprints.json",
                                     "final_tensor_fingerprints.json", "first_gradient_checks.json", "initial_producer_parity.json",
                                     "parameter_deltas.json")],
                          "frozen_tensors_unchanged": True, "cumulative_counters": dict(counters)}
                write_once(fit_dir/"completed.json", result)
                results.append(result)
                del model, optimizer
                torch.cuda.empty_cache()
        continuation_check()
        validate_counters(counters)
        check(len(results) == 8 and sum(counters[k+"_forwards_returned"] for k in CALL_BUDGETS) == 28082
              and sum(counters[k+"_candidate_presentations"] for k in CALL_BUDGETS) == 897474,
              "Physical backbone workload total differs")
        result = {"status": "completed_exact_frozen_workload", "at_utc": stamp(), "elapsed_seconds": time.monotonic()-began,
                  "execution_freeze": freeze_binding, "prepared": freeze["prepared"], "counters": dict(counters),
                  "fits": results, "all_scores": all_scores, "local_captures": local_artifacts,
                  "local_capture_checks": capture_checks, "initial_tensors_identical_all_eight": initial_reference,
                  "shared_initial_trainable": binding(root, out/"shared_initial_trainable.pth"),
                  "automatic_retry": False, "automatic_extension": False, "selector_changed": False,
                  "fitting_games": ["0022400868", "0022400866", "0022500829"], "independent_CPU_audit_required": True}
        write_once(out/"completed.json", result)
        return result
    except BaseException as error:
        write_once(out/"failed.json", {"at_utc": stamp(), "elapsed_seconds": time.monotonic()-began,
                   "error": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
                   "counters": dict(counters), "automatic_retry": False})
        raise
    finally:
        done.set()
        close_caches(caches)
        close_caches(feature_caches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--monitor", "--owned-monitor", dest="monitor")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.run:
        print(json.dumps(run(args.root, args.monitor, sys.argv[1:])), flush=True)
    else:
        preflight(args.root, require_authorization=False)
        print(json.dumps({"status": "metadata_preflight_passed_no_runtime", "expected_counters": COUNTER_EXPECTED}), flush=True)


if __name__ == "__main__":
    main()

"""Supervised, fixed-budget producer-transfer comparison; no runtime on import.

Four fresh Q+ fits consume the frozen six prefix schedules. Original Q models
are reused only for the 461 newly scored challenge points. No J or selection.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
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
BASE = "data/outputs/ball_tracking/candidate_producer_transfer_v0_1"
LAUNCH_BASE = BASE + "/launch_v0_1"
NEURAL_OUTPUT = BASE + "/attempt_001"
PREPARATION = BASE + "/preparation/attempt_001/prepared.json"
MONITOR = LAUNCH_BASE + "/monitoring/attempt_001"
MODULE = "src.ball_tracking.candidate_producer_transfer_experiment"
CONFIG = "configs/ball_tracking/proposals/candidate_producer_transfer_v0_1.json"
SPEC_SHA256 = "3970d0d1050661e9a947cd27636ac533d1612342ffefabf6b6bee0f7ecb7ab3c"
ORIGINAL = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1/attempt_005"
FIT_NAMES = ("leave_chi_out", "leave_den_out", "leave_sac_out", "all_nba")
SEED, CYCLES, BATCH_SIZE = 20261028, 6, 32
MAX_TOTAL_SECONDS, CLEANUP_RESERVE_SECONDS = 5400, 30
GPU = io.GPU
COUNTS = {"new_quality_fits": 4, "old_control_fits_rerun": 0,
          "optimizer_updates": 9870, "training_presentations": 315432,
          "scoring_forwards": 1014, "scoring_presentations": 32341,
          "producer_parity_forwards": 4, "producer_parity_presentations": 128,
          "CPU_gate_fits": 0, "total_neural_forwards": 10888,
          "total_candidate_presentations": 347901}
COUNTER_EXPECTED = {"training_forwards_attempted": 9870, "training_forwards_returned": 9870,
                    "optimizer_updates": 9870, "training_candidate_presentations": 315432,
                    "scoring_forwards_attempted": 1014, "scoring_forwards_returned": 1014,
                    "scoring_candidate_presentations": 32341, "parity_forwards_attempted": 4,
                    "parity_forwards_returned": 4, "parity_candidate_presentations": 128}
REQUIRED_IMPLEMENTATION = {
    "src/ball_tracking/candidate_producer_transfer_experiment.py",
    "tests/test_candidate_producer_transfer_experiment.py",
    "src/ball_tracking/candidate_producer_transfer_data.py",
    "tests/test_candidate_producer_transfer_data.py",
    "src/ball_tracking/candidate_acceptance_neural.py",
    "src/ball_tracking/candidate_quality_data.py",
    "src/ball_tracking/candidate_quality_model.py",
    "src/ball_tracking/candidate_quality_pilot.py",
    "src/ball_tracking/candidate_quality_native_cable_resume.py",
    "src/ball_tracking/continuation_owned_guard.py",
    "src/ball_tracking/point_feature_inference.py",
    "src/ball_tracking/nba_appearance_feature_screen.py",
}
CONTROL_FILES = {ORIGINAL + f"/{fit}/{name}" for fit in FIT_NAMES for name in
                 ("initial_tensor_fingerprints.json", "final_tensor_fingerprints.json", "final_trainable.pth")}
check, read, rows = io.check, io.read, io.rows
binding, bound, write_once, append, stamp = io.binding, io.bound, io.write_once, io.append, io.stamp
validate_readiness = io.validate_readiness


def validate_fit_schedule(plan, weights, schedules, training_rows):
    """Verify membership, original budget, augmented scaling and every actual ID."""
    keys = [row['training_row_key'] for row in weights]
    check(len(keys) == len(set(keys)) == plan['augmented_known_candidates'], "Augmented weight membership differs")
    expected = [key for key, row in training_rows.items()
                if row['domain'] == 'nba' and row['target'] is not None and row['game_id'] in plan['fit_games']]
    check(keys == expected, "Fit membership/order or held-game exclusion differs")
    for weight in weights:
        row = training_rows[weight['training_row_key']]
        check(row['candidate_id'] == weight['candidate_id'] and row['target'] in (0, 1), "Fitting identity or target differs")
        value = weight['objective_weight']
        check(isinstance(value, (int, float)) and math.isfinite(value) and value > 0
              and math.isclose(weight['training_multiplier'], len(keys) * value, rel_tol=1e-12), "Augmented loss multiplier differs")
    check(math.isclose(math.fsum(w['objective_weight'] for w in weights), 1.0, abs_tol=1e-10), "Objective mass differs")
    check(len(schedules) == CYCLES and 0 < plan['original_known_candidates'] <= len(keys), "Sampled-cycle count/quota differs")
    quota, visits, steps = plan['original_known_candidates'], Counter(), 0
    batches = [min(BATCH_SIZE, quota-i) for i in range(0, quota, BATCH_SIZE)]
    check(plan['batch_sizes_per_round'] == batches, "Original partial-batch sequence differs")
    for number, schedule in enumerate(schedules, 1):
        order = list(keys)
        random.Random(SEED + number).shuffle(order)
        order = order[:quota]
        check(schedule['fit'] == plan['fit'] and schedule['round'] == number
              and schedule['seed'] == SEED + number and schedule['population'] == len(keys)
              and schedule['quota'] == quota and schedule['training_row_keys'] == order
              and schedule['batch_sizes'] == batches, "Frozen sampled-cycle schedule differs")
        visits.update(order)
        steps += len(batches)
    check(set(visits) == set(keys) and min(visits.values()) >= 1, "Known candidate omitted from all cycles")
    check(steps == plan['optimizer_updates'] and sum(visits.values()) == plan['training_presentations'], "Fit budget differs")
    return visits


def validate_loaded(loaded):
    fits = loaded['fits']
    check(list(fits) == list(FIT_NAMES), "Four fit order differs")
    for fit, item in fits.items():
        check(item['plan']['fit'] == fit, "Fit name differs")
        validate_fit_schedule(item['plan'], item['weights'], item['schedules'], loaded['training_rows'])
    scoring = loaded['scoring_plan']
    check(len(scoring) == 11, "Scoring segment count differs")
    segments = {(g['fit'], g['owner'], g['population']) for g in scoring}
    check(len(segments) == len(scoring), "Duplicate scoring segment")
    for group in scoring:
        check(group['fit'] in fits and group['owner'] in ('new_treatment', 'saved_Q_control'), "Unknown score route")
        check(len(group['ids']) == len(set(group['ids'])) == group['scores']
              and group['forwards'] == math.ceil(group['scores']/BATCH_SIZE), "Score budget/identity differs")
        if group['owner'] == 'saved_Q_control':
            check(group['fit'] != 'all_nba' and group['population'] == 'added_held_challenge', "Control inference exceeds new inputs")
        if group['population'] in ('original_held_NBA', 'added_held_challenge'):
            for key in group['ids']:
                row = loaded['union_candidates'][key]
                check(row['game_id'] == group['game_id'] and row['game_id'] not in fits[group['fit']]['plan']['fit_games'], "Held scoring source leaked into fitting")
    check(sum(g['scores'] for g in scoring) == COUNTS['scoring_presentations']
          and sum(g['forwards'] for g in scoring) == COUNTS['scoring_forwards'], "Total scoring budget differs")
    check(sum(p['plan']['optimizer_updates'] for p in fits.values()) == COUNTS['optimizer_updates']
          and sum(p['plan']['training_presentations'] for p in fits.values()) == COUNTS['training_presentations'], "Total training budget differs")


def validate_authorization(authorization, freeze_binding, specification):
    check(authorization.get('execution_approved') is True
          and authorization.get('execution_freeze') == freeze_binding
          and authorization.get('specification') == specification and authorization.get('scope') == COUNTS
          and authorization.get('max_total_seconds') == MAX_TOTAL_SECONDS
          and isinstance(authorization.get('user_statement'), str) and authorization['user_statement'].strip(),
          "Authorization must bind this freeze, specification and exact workload")
    check(all(authorization.get(key) is False for key in
              ('automatic_retry', 'automatic_extension', 'protected_access_approved', 'new_labels_approved', 'selector_approved')),
          "Authorization exceeds fixed experiment scope")


def preflight(root=ROOT, require_approval=False):
    """Metadata/hash-only guard before Torch, model construction or GPU access."""
    root = Path(root).resolve()
    spec, specification = read(root / CONFIG), binding(root, root / CONFIG)
    check(specification['sha256'] == SPEC_SHA256 and spec['counts'] == COUNTS, "Frozen design differs")
    for name, version in io.RUNTIME.items():
        check(metadata.version(name) == version, "Pinned runtime metadata differs: " + name)
    check(binding(root, root / io.DINO_LIBRARY)['sha256'] == io.DINO_LIBRARY_SHA256, "Pinned DINO implementation differs")
    options = {'cwd': root, 'text': True, 'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)}
    check(subprocess.check_output(['git', 'branch', '--show-current'], **options).strip() == spec['branch'], "Branch differs")
    check(subprocess.check_output(['git', 'rev-parse', 'HEAD'], **options).strip() == spec['head'], "HEAD differs")
    check(not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], **options).strip(), "Index must remain empty")
    freeze_file = root / LAUNCH_BASE / 'execution_freeze.json'
    freeze = read(freeze_file)
    check(freeze.get('status') == 'frozen_for_authorized_execution'
          and freeze.get('specification') == specification and freeze.get('protocol') == spec['protocol']
          and freeze.get('launch_base') == LAUNCH_BASE and freeze.get('neural_output') == NEURAL_OUTPUT,
          "Freeze identity, destination or specification differs")
    check(not (root / NEURAL_OUTPUT).exists(), "Output already exists; retry/resume is not authorized")
    implementation, inputs = freeze.get('implementation', []), freeze.get('inputs', [])
    check(REQUIRED_IMPLEMENTATION <= {link['path'] for link in implementation}, "Runtime source/test bindings missing")
    index = {link['path']: link for link in inputs}
    check(len(index) == len(inputs) and CONTROL_FILES <= set(index), "Frozen input/control health coverage differs")
    check(all(index.get(link['path']) == link for link in spec['input_bindings'])
          and index.get(PREPARATION) == freeze.get('prepared'), "Frozen preparation/design coverage differs")
    check(isinstance(freeze.get('review'), list) and freeze['review'], "Independent review missing")
    for link in [spec['protocol'], *implementation, *inputs, freeze['focused_tests'], *freeze['review']]:
        bound(root, link)
    from . import candidate_producer_transfer_data as data
    loaded = data.load_prepared(root, verify=True)
    validate_loaded(loaded)
    if require_approval:
        freeze_binding = binding(root, freeze_file)
        auth_file = root / LAUNCH_BASE / 'execution_authorization.json'
        validate_authorization(read(auth_file), freeze_binding, specification)
        readiness = read(root / LAUNCH_BASE / 'launch_readiness.json')
        validate_readiness(readiness, freeze_binding, binding(root, auth_file))
        for link in readiness['sources']:
            bound(root, link)
    check('torch' not in sys.modules, "Torch imported before authorized runtime")
    return spec, freeze


def validate_policy(policy):
    check(policy.get('module') == MODULE and policy.get('arguments') == ['--run', '--monitor', MONITOR]
          and policy.get('sample_seconds') == 2 and policy.get('temperature_stop_C') == 80
          and policy.get('telemetry_timeout_seconds') == 5 and policy.get('grace_seconds') == 10
          and policy.get('automatic_retry') is False and policy.get('max_total_seconds') == MAX_TOTAL_SECONDS
          and policy.get('soft_stop_seconds') == MAX_TOTAL_SECONDS-CLEANUP_RESERVE_SECONDS
          and policy.get('gpu_uuid') == GPU, "Owned supervisor policy differs")


def remaining_wall_seconds(policy, now=None):
    return io.remaining_wall_seconds(policy, now)


def validate_counters(counters):
    check(counters == COUNTER_EXPECTED, "Exact forward/presentation/update accounting differs")


def call_started(counters, kind, journal, details):
    key = kind + '_forwards_attempted'
    check(kind in ('training', 'scoring', 'parity') and counters[key] < COUNTER_EXPECTED[key], "Forward budget exhausted")
    counters[key] += 1
    append(journal, {'event': kind + '_start', **details, 'counters': dict(counters)})


def score_rows(group, ids, values):
    check(len(ids) == len(values) and all(type(value) in (int, float) and math.isfinite(value) for value in values), "Nonfinite or missing score")
    return [{group['id_field']: key, 'quality_logit': value, 'fit': group['fit'],
             'owner': group['owner'], 'population': group['population']} for key, value in zip(ids, values, strict=True)]


def restore_control(model, checkpoint, fit):
    """Restore only the accepted source-held control after saving the treatment."""
    import torch
    check(checkpoint.get('fit') == fit and checkpoint.get('epoch') == 6, "Saved control identity/endpoint differs")
    state = checkpoint['trainable_state']
    parameters = {name: parameter for name, parameter in model.named_parameters() if parameter.requires_grad}
    check(set(state) == set(parameters), "Control trainable parameter names differ")
    with torch.no_grad():
        for name, parameter in parameters.items():
            tensor = state[name]
            check(isinstance(tensor, torch.Tensor) and tensor.device.type == 'cpu' and tensor.dtype == torch.float32
                  and tensor.shape == parameter.shape and bool(torch.isfinite(tensor).all()), "Control tensor differs: " + name)
            parameter.copy_(tensor.to(device=parameter.device))


def run(root, monitor, arguments):
    root = Path(root).resolve()
    check(monitor == MONITOR and list(arguments) == ['--run', '--monitor', MONITOR], "Only declared owned launch is allowed")
    _, freeze = preflight(root, require_approval=True)
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root / monitor, MODULE, arguments)
    policy = read(root / monitor / 'policy.json')
    validate_policy(policy)
    remaining = remaining_wall_seconds(policy)
    from .candidate_quality_native_cable_resume import verify_runtime_driver
    driver = verify_runtime_driver(policy['gpu_uuid'])
    out = root / NEURAL_OUTPUT
    out.mkdir(parents=True, exist_ok=False)
    began, done, caches = time.monotonic(), threading.Event(), {}
    counters = dict.fromkeys(COUNTER_EXPECTED, 0)
    freeze_binding = binding(root, root / LAUNCH_BASE / 'execution_freeze.json')
    write_once(out / 'started.json', {'at_utc': stamp(), 'ownership': ownership, 'driver': driver,
               'execution_freeze': freeze_binding, 'prepared': freeze['prepared'],
               'execution_authorization': binding(root, root / LAUNCH_BASE / 'execution_authorization.json'),
               'launch_readiness': binding(root, root / LAUNCH_BASE / 'launch_readiness.json'),
               'settings_changed_by_worker': False, 'new_work_only': True})

    def deadline():
        if not done.wait(max(0.0, remaining-CLEANUP_RESERVE_SECONDS)):
            (root / monitor / 'STOP').touch(exist_ok=True)

    def continuation_check():
        check(not (root / monitor / 'STOP').exists(), "Owned supervisor requested STOP")
        remaining_wall_seconds(policy)

    threading.Thread(target=deadline, daemon=True).start()
    try:
        continuation_check()
        check('torch' not in sys.modules, "Torch imported before authorized deterministic runtime")
        os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
        import numpy as np
        import torch
        from . import candidate_quality_model as model_api
        from . import candidate_quality_pilot as pilot
        from . import candidate_producer_transfer_data as data
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        loaded = data.load_prepared(root, verify=True)
        validate_loaded(loaded)
        caches = data.open_caches(root, loaded)
        journal, results, all_scores = out / 'journal.jsonl', [], []

        def input_batch(ids):
            pixels, points = data.batch_arrays(ids, loaded, caches)
            check(pixels.dtype == np.float32 and pixels.shape == (len(ids), 3, 224, 224)
                  and points.dtype == np.float64 and points.shape == (len(ids), 4)
                  and np.isfinite(pixels).all() and np.isfinite(points).all(), "Input array contract differs")
            return torch.from_numpy(pixels).to('cuda'), torch.from_numpy(points).to('cuda')

        def score_group(model, group, fit_dir):
            path = fit_dir / (group['owner'] + '_' + group['population'] + '.jsonl')
            seen, calls = [], 0
            with path.open('x', encoding='utf-8', newline='\n') as stream, torch.inference_mode():
                for ids in pilot.batches(group['ids'], BATCH_SIZE):
                    continuation_check()
                    pixels, points = input_batch(ids)
                    details = {'fit': group['fit'], 'owner': group['owner'], 'population': group['population'], 'ids': ids, 'batch_count': len(ids)}
                    call_started(counters, 'scoring', journal, details)
                    values = model(pixels, points).detach().cpu().tolist()
                    transported = score_rows(group, ids, values)
                    counters['scoring_forwards_returned'] += 1
                    counters['scoring_candidate_presentations'] += len(ids)
                    for row in transported:
                        stream.write(json.dumps(row, allow_nan=False) + '\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                    append(journal, {'event': 'scoring_return', **details, 'counters': dict(counters)})
                    seen.extend(ids)
                    calls += 1
                    del pixels, points
            check(seen == group['ids'] and calls == group['forwards'], "Score identity/order/call transport differs")
            return {**binding(root, path), **{key: group[key] for key in ('fit', 'owner', 'population')}, 'rows': len(seen)}

        for fit_name, item in loaded['fits'].items():
            continuation_check()
            plan, weights, schedules = item['plan'], item['weights'], item['schedules']
            fit_dir = out / fit_name
            fit_dir.mkdir(exist_ok=False)
            write_once(fit_dir / 'fit_manifest.json', {'plan': plan, 'weights': weights, 'schedules': schedules})
            planned_visits = validate_fit_schedule(plan, weights, schedules, loaded['training_rows'])
            multipliers = {w['training_row_key']: w['training_multiplier'] for w in weights}
            random.seed(SEED)
            np.random.seed(SEED)
            torch.manual_seed(SEED)
            torch.cuda.manual_seed_all(SEED)
            model = model_api.build_model(root, device='cuda', execution_authorized=True, seed=SEED)
            frozen_before = model_api.frozen_fingerprint(model)
            trainable_before = pilot.trainable_group_fingerprints(model)
            initial = {'frozen': frozen_before, 'trainable_groups': trainable_before}
            check(initial == read(root / ORIGINAL / fit_name / 'initial_tensor_fingerprints.json'), "Fresh initialization differs from accepted original control")
            write_once(fit_dir / 'initial_tensor_fingerprints.json', initial)
            write_once(fit_dir / 'trainable_parameters.json', model_api.trainable_manifest(model))
            optimizer = torch.optim.AdamW(model_api.optimizer_parameter_groups(model), betas=(.9, .999), eps=1e-8)
            fit_steps, actual_visits, recoveries = 0, Counter(), []
            for cycle, schedule in enumerate(schedules, 1):
                model.train()
                online_sum, group_losses, cycle_steps = 0.0, defaultdict(lambda: [0.0, 0.0, 0]), 0
                for keys in pilot.batches(schedule['training_row_keys'], BATCH_SIZE):
                    continuation_check()
                    batch = [loaded['training_rows'][key] for key in keys]
                    pixels, points = input_batch([row['candidate_id'] for row in batch])
                    targets = torch.tensor([row['target'] for row in batch], device='cuda', dtype=torch.float32)
                    scale = torch.tensor([multipliers[key] for key in keys], device='cuda', dtype=torch.float32)
                    optimizer.zero_grad(set_to_none=True)
                    details = {'fit': fit_name, 'cycle': cycle, 'step': fit_steps, 'training_row_keys': keys, 'batch_count': len(keys)}
                    call_started(counters, 'training', journal, details)
                    first = fit_steps == 0
                    if first:
                        logits, actual_features = model.forward_with_features(pixels, points)
                    else:
                        logits = model(pixels, points)
                    check(logits.shape == targets.shape and bool(torch.isfinite(logits).all()), "Invalid training logits")
                    counters['training_forwards_returned'] += 1
                    if first:
                        continuation_check()
                        call_started(counters, 'parity', journal, details)
                        parity = pilot.first_batch_parity(model, pixels, points, actual_features)
                        counters['parity_forwards_returned'] += 1
                        counters['parity_candidate_presentations'] += len(keys)
                        write_once(fit_dir / 'initial_producer_point_parity.json', parity)
                        append(journal, {'event': 'parity_return', **details, 'parity': parity, 'counters': dict(counters)})
                        del actual_features
                    losses = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction='none')
                    loss = (losses * scale).mean()
                    check(bool(torch.isfinite(loss)), "Nonfinite training loss")
                    loss.backward()
                    if first:
                        write_once(fit_dir / 'first_gradient_checks.json', pilot.check_first_gradients(model))
                    grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], max_norm=1.0, error_if_nonfinite=True)
                    check(all(p.grad is None for p in model.parameters() if not p.requires_grad), "Frozen gradient appeared")
                    optimizer.step()
                    fit_steps += 1
                    cycle_steps += 1
                    counters['optimizer_updates'] += 1
                    counters['training_candidate_presentations'] += len(keys)
                    actual_visits.update(keys)
                    batch_loss = float(loss.detach().cpu())
                    online_sum += batch_loss
                    weighted = (losses * scale).detach().cpu().tolist()
                    for key, row, value in zip(keys, batch, weighted, strict=True):
                        bucket = group_losses[row['target_group']]
                        bucket[0] += value / len(keys)
                        bucket[1] += multipliers[key] / len(keys)
                        bucket[2] += 1
                    append(journal, {'event': 'training_return', **details, 'step': fit_steps,
                                     'weighted_batch_loss': batch_loss, 'gradient_norm_before_clip': float(grad_norm.detach().cpu()),
                                     'counters': dict(counters)})
                    del pixels, points, targets, scale, logits, losses, loss, grad_norm
                check(cycle_steps == len(schedule['batch_sizes']), "Sampled cycle step count differs")
                append(out / 'cycles.jsonl', {'fit': fit_name, 'cycle': cycle,
                       'mean_online_batch_loss': online_sum/cycle_steps, 'group_batch_loss_mass_count': dict(group_losses),
                       'note': 'Sampled-cycle exposure-weighted online batch diagnostics; not full-union epoch losses or validation'})
                continuation_check()
                recovery = fit_dir / f'recovery_cycle_{cycle:02d}.pth'
                io.save_checkpoint_once(recovery, {'trainable_state': {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                    'optimizer_state': optimizer.state_dict(), 'cycle': cycle, 'fit': fit_name,
                    'fit_steps': fit_steps, 'counters': dict(counters), 'python_rng': random.getstate(), 'numpy_rng': np.random.get_state(),
                    'torch_rng': torch.get_rng_state(), 'cuda_rng': torch.cuda.get_rng_state_all(), 'freeze_sha256': freeze_binding['sha256'],
                    'purpose': 'Recovery only after separate authorization; fixed sampled cycle six remains endpoint'})
                recoveries.append(binding(root, recovery))
                append(out / 'recovery_checkpoints.jsonl', recoveries[-1])
                print(json.dumps({'fit': fit_name, 'cycle': cycle, 'steps': fit_steps, 'mean_online_batch_loss': online_sum/cycle_steps}), flush=True)
            check(fit_steps == plan['optimizer_updates'] and actual_visits == planned_visits, "Actual fit updates/exposures differ")
            write_once(fit_dir / 'actual_exposure.json', [{'training_row_key': key, 'visits': actual_visits[key]} for key in multipliers])
            check(model_api.frozen_fingerprint(model) == frozen_before, "Frozen backbone tensors changed")
            trainable_after = pilot.trainable_group_fingerprints(model)
            check(all(trainable_after[group] != trainable_before[group] for group in trainable_before), "Head/backbone did not both change")
            write_once(fit_dir / 'final_tensor_fingerprints.json', {'frozen': frozen_before, 'trainable_groups': trainable_after,
                       'frozen_unchanged': True, 'backbone_and_head_changed': True})
            checkpoint = fit_dir / 'final_trainable.pth'
            io.save_checkpoint_once(checkpoint, {'trainable_state': {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                                    'cycle': CYCLES, 'fit': fit_name, 'fit_steps': fit_steps, 'freeze_sha256': freeze_binding['sha256']})
            model.eval()
            score_bindings = []
            for group in loaded['scoring_plan']:
                if group['fit'] == fit_name and group['owner'] == 'new_treatment':
                    score_bindings.append(score_group(model, group, fit_dir))
            control_groups = [g for g in loaded['scoring_plan'] if g['fit'] == fit_name and g['owner'] == 'saved_Q_control']
            if control_groups:
                continuation_check()
                control_path = bound(root, plan['saved_control'])
                control = torch.load(control_path, map_location='cpu', weights_only=True)
                restore_control(model, control, fit_name)
                control_expected = read(root / ORIGINAL / fit_name / 'final_tensor_fingerprints.json')
                check(model_api.frozen_fingerprint(model) == control_expected['frozen']
                      and pilot.trainable_group_fingerprints(model) == control_expected['trainable_groups'], "Restored saved control fingerprint differs")
                write_once(fit_dir / 'saved_control_restore.json', {'checkpoint': plan['saved_control'], 'fingerprints': control_expected,
                           'zero_optimizer_updates': True, 'inference_scope': 'added_held_challenge_only'})
                del control
                model.eval()
                for group in control_groups:
                    score_bindings.append(score_group(model, group, fit_dir))
            all_scores.extend(score_bindings)
            result = {'fit': fit_name, 'steps': fit_steps, 'checkpoint': binding(root, checkpoint),
                      'recovery_checkpoints': recoveries, 'scores': score_bindings,
                      'fit_manifest': binding(root, fit_dir / 'fit_manifest.json'), 'actual_exposure': binding(root, fit_dir / 'actual_exposure.json'),
                      'frozen_tensors_unchanged': True, 'cumulative_counters': dict(counters),
                      'health': [binding(root, fit_dir / name) for name in ('initial_tensor_fingerprints.json', 'final_tensor_fingerprints.json',
                                  'trainable_parameters.json', 'initial_producer_point_parity.json', 'first_gradient_checks.json')]}
            if control_groups:
                result['control_restore'] = binding(root, fit_dir / 'saved_control_restore.json')
            write_once(fit_dir / 'completed.json', result)
            results.append(result)
            del optimizer, model
            torch.cuda.empty_cache()
        validate_counters(counters)
        result = {'status': 'completed_producer_transfer_experiment_no_adoption', 'at_utc': stamp(),
                  'elapsed_seconds': time.monotonic()-began, 'counters': counters, 'counts': COUNTS, 'fits': results,
                  'scores': all_scores, 'execution_freeze': freeze_binding, 'prepared': freeze['prepared'],
                  'model_adopted': False, 'old_studies_rerun': False, 'protected_access': False, 'new_labels': 0,
                  'settings_changed': False, 'automatic_retry': False, 'J_fits': 0, 'new_ranking_policy': False}
        write_once(out / 'completed.json', result)
        return result
    except BaseException as error:
        write_once(out / 'failed.json', {'at_utc': stamp(), 'elapsed_seconds': time.monotonic()-began,
                   'error': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc(),
                   'counters': counters, 'automatic_retry': False})
        raise
    finally:
        done.set()
        for cache in caches.values():
            if getattr(cache, '_mmap', None) is not None:
                cache._mmap.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--monitor')
    args = parser.parse_args()
    if args.run:
        print(json.dumps(run(ROOT, args.monitor, sys.argv[1:])), flush=True)
    else:
        spec, _ = preflight(ROOT)
        print(json.dumps({'status': 'metadata_preflight_passed_no_runtime', 'counts': spec['counts']}), flush=True)


if __name__ == '__main__':
    main()

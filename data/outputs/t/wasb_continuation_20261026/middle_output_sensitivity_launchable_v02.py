"""Prepare or explicitly execute one eight-call middle-output sensitivity probe.

Preparation is CPU-only and reads the existing permitted 768 cache. Execution
requires both completed comparisons, their saved-mean analysis, an explicit
checkpoint binding and an owned GPU supervisor. Repeated frames are synthetic
diagnostic inputs: no accuracy scoring, production substitution or adoption.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
FOLDER = Path(__file__).parent
MODE = 'native_vs_repeated_middle_v0.1'
MODULE = 'src.ball_tracking.continuation_temporal_diagnostic_v02'
LAUNCHER = ROOT / 'src/ball_tracking/continuation_temporal_diagnostic_v02.py'
CENTERS = (11075, 11084, 11093, 11099)
OUTPUT = ROOT / 'data/outputs/ball_tracking/wasb_continuation_v0_1/middle_output_sensitivity_v0_1'
GAP_HELPER = FOLDER / 'saved_det_gap_analysis.py'
GAP_HELPER_SHA = 'f1d08d0a6ac90d147f0aa3885be98369140842e36264b932b617bb0dbc55cf6e'
if hashlib.sha256(GAP_HELPER.read_bytes()).hexdigest() != GAP_HELPER_SHA:
    raise ValueError('Reviewed saved-mean helper changed')
spec = importlib.util.spec_from_file_location('saved_det_gap_metadata', GAP_HELPER)
gap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gap)
from src.ball_tracking import completion_evaluation as evaluation
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import nba_resolution_evaluation as prior
from src.ball_tracking import wasb_adapter
from src.ball_tracking import wasb_resolution as resolution
from src.ball_tracking.wasb_experiment import bound_path, canonical, read_json
from src.ball_tracking.continuation_owned_guard import verify_owned_worker
import cv2
import numpy as np
import torch

check, bind, write_once = runtime.check, runtime.binding, runtime.atomic_write_once


def stamp():
    return datetime.now(timezone.utc).isoformat()


def array_sha(array):
    return hashlib.sha256(array.tobytes()).hexdigest()


def prepare():
    check(not torch.cuda.is_initialized(), 'CPU preparation cannot start with a CUDA context')
    recipe, block, frames, _, sources = gap.context()
    source_recipe = read_json(bound_path(ROOT, recipe['source_recipe']))
    primary = read_json(bound_path(ROOT, source_recipe['parent_recipe']))
    check(source_recipe['parent_recipe']['path'] == evaluation.PRIMARY_RECIPE, 'Frozen adapter primary recipe differs')
    nfhs = read_json(bound_path(ROOT, primary['nfhs_training_config']))
    for record in source_recipe['code_bindings'] + primary['code_bindings'] + recipe['code_bindings']:
        bound_path(ROOT, record)
    upstream = []
    for relative, digest in wasb_adapter.SOURCE_SHA256.items():
        record = bind(ROOT, ROOT / nfhs['upstream_source'] / relative)
        check(record['sha256'] == digest, 'Pinned upstream model source differs')
        upstream.append(record)
    bound_path(ROOT, nfhs['pretrained_checkpoint'])
    cache_path = ROOT / recipe['evaluation_cache_root'] / prior.nba.key(block) / 'receipt.json'
    cache_link = bind(ROOT, cache_path)
    receipt = read_json(cache_path)
    expected = {'block_sha256': canonical(block), 'representation': 'affine_RGB_uint8_432x768',
        'resolution': gap.RESOLUTION, 'implementation': bind(ROOT, Path(prior.__file__)),
        'primitives': bind(ROOT, Path(resolution.__file__)), 'normalization': bind(ROOT, Path(runtime.__file__))}
    check(receipt['identity'] == expected and receipt['protected_reads'] == 0
          and receipt['annotation_targets_created'] == 0, 'Only existing exact permitted 768 cache allowed')
    # bound_path streams the large file hash; never loads the complete cache in RAM.
    array_path = bound_path(ROOT, receipt['array'])
    array = np.load(array_path, mmap_mode='r', allow_pickle=False)
    cache = prior.InputCache(ROOT, [block], cache_path.parent.parent)
    cache.arrays = {gap.BLOCK_ID: array}
    cache.positions = {gap.BLOCK_ID: {f['source_frame_index']: i for i, f in enumerate(block['frames'])}}
    cases, tensors = [], {}
    try:
        check(array.shape == (1231, 432, 768, 3) and array.dtype == np.uint8, 'Existing cache shape/dtype differs')
        for center in CENTERS:
            native = [center - 1, center, center + 1]
            for a, b in zip(native, native[1:]):
                check(frames[b]['source_pts_ticks'] - frames[a]['source_pts_ticks'] == frames[a]['duration_ticks'],
                      'Real native triplet timing is not consecutive')
            annotation = frames[center]['annotation']
            check(annotation['localization_eligible'] and annotation['geometry'] is not None,
                  'Only existing accepted localizable center references allowed')
            for condition, indices in (('native', native), ('repeated_center', [center] * 3)):
                name = f'frame_{center:06d}_{condition}'
                value = cache.inputs(gap.BLOCK_ID, indices)
                check(value.shape == (9, 432, 768) and value.dtype == torch.float32
                      and value.device.type == 'cpu' and bool(torch.isfinite(value).all()), 'Exact normalized CPU triplet required')
                # Verify actual cache consumer against separately concatenated frozen normalization.
                expected_value = torch.cat([runtime.normalized_tensor(array[index - 10668]) for index in indices])
                check(torch.equal(value, expected_value), 'Actual cache normalization transport changed')
                cases.append({'name': name, 'center_frame': center, 'condition': condition,
                    'input_image_frame_indices': indices, 'synthetic_input': condition == 'repeated_center',
                    'output_channel_image_slots': indices, 'middle_channel_index': 1,
                    'cached_rgb_sha256_by_slot': [array_sha(array[index - 10668]) for index in indices],
                    'normalized_float32_input_sha256': array_sha(value.numpy()),
                    'accepted_center_reference': annotation,
                    'native_source_bindings_by_slot': [frames[index]['png'] for index in indices],
                    'native_source_pts_by_image': [frames[index]['source_pts_ticks'] for index in indices],
                    'synthetic_timestamps_assigned': False})
                tensors[name] = value
            real, repeated = tensors[f'frame_{center:06d}_native'], tensors[f'frame_{center:06d}_repeated_center']
            check(torch.equal(real[3:6], repeated[3:6]) and torch.equal(repeated[:3], repeated[3:6])
                  and torch.equal(repeated[3:6], repeated[6:9]), 'Middle source pixels must remain exactly unchanged')
    finally:
        cache.close()
    implementations = [bind(ROOT, ROOT / f'src/ball_tracking/{name}.py') for name in
        ('completion_evaluation', 'wasb_adapted_adapter', 'wasb_adapter', 'completion_training_runtime',
         'nba_resolution_evaluation', 'wasb_resolution', 'gpu_supervision')]
    record = {'schema_version': 'middle_output_sensitivity_preparation/v0.1', 'status': 'prepared_cpu_only', 'mode': MODE,
        'helper': bind(ROOT, Path(__file__)), 'launcher': bind(ROOT, LAUNCHER), 'execution_module': MODULE,
            'owned_worker_guard': bind(ROOT, ROOT / 'src/ball_tracking/continuation_owned_guard.py'),
        'saved_mean_helper': bind(ROOT, GAP_HELPER), 'source_bindings': sources,
        'primary_recipe': source_recipe['parent_recipe'], 'nfhs_model_config': primary['nfhs_training_config'],
        'upstream_model_sources': upstream, 'pretrained_constructor_asset': nfhs['pretrained_checkpoint'],
        'implementations': implementations, 'cache_receipt': cache_link, 'cache_array': receipt['array'],
        'cache_array_full_sha256_verified': True, 'cache_reads': 'Only existing permitted affine uint8 frames; no PNG/video decode.',
        'cases': cases, 'centers': list(CENTERS), 'planned_forward_calls': 8, 'planned_optimizer_updates': 0,
        'model_calls': 0, 'model_tensor_loads': 0, 'source_pixel_reads': 0, 'protected_reads': 0, 'new_labels': 0,
        'CUDA_initialized': False, 'model_adopted': False, 'human_visual_acceptance': None,
        'interpretation': 'One real centered triplet is one contributor to the original native mean. Compare middle-channel sigmoid responses only; neither condition is scored as production accuracy.',
        'limit': 'Repeated-center inputs change temporal context and may be out of distribution. Sensitivity cannot establish a complete temporal/appearance causal explanation or a production remedy.'}
    check(not torch.cuda.is_initialized(), 'Preparation unexpectedly initialized CUDA')
    return record, tensors


def prerequisites(args, prepared):
    preparation_link = bind(ROOT, ROOT / args.preparation)
    check(read_json(ROOT / args.preparation) == prepared, 'Explicit preparation receipt differs from current source/cache/code')
    analysis_link = bind(ROOT, ROOT / args.saved_analysis)
    analysis = read_json(ROOT / args.saved_analysis)
    check(analysis['status'] == 'passed_saved_mean_diagnostic' and analysis['mode'] == 'both_continuations'
          and analysis['helper'] == prepared['saved_mean_helper'] and analysis['source_bindings']['recipe'] == prepared['source_bindings']['recipe']
          and analysis['source_bindings']['accepted_reference_transport'] == prepared['source_bindings']['accepted_reference_transport']
          and analysis['model_count'] == 10 and analysis['sampled_map_hashes_validated'] == 230,
          'Completed both-arm saved-mean analysis required')
    recipe, _, _, _, sources = gap.context()
    comparisons = gap.completed_comparisons(recipe, sources, False)
    actual_models = {(arm, model['epoch']): (complete_link, complete, published, model)
                     for arm, complete_link, complete, published in comparisons for model in published['models']}
    check(set(actual_models) == {(a, e) for a in ('constant', 'cosine') for e in range(6, 11)}, 'Complete10-model census differs')
    check(len(analysis['models']) == 10
          and {(item['arm'], item['absolute_epoch']) for item in analysis['models']} == set(actual_models),
          'Saved-mean analysis must contain each of ten models exactly once')
    for item in analysis['models']:
        complete_link, complete, published, model = actual_models[(item['arm'], item['absolute_epoch'])]
        check(published['model_adopted'] is published['ball_phase_accepted'] is published['protected_evaluation_authorized'] is False
              and published['human_trajectory_acceptance'] is None and published['optimizer_updates'] == published['new_labels'] == 0,
              'Diagnostic cannot inherit adoption or protected authorization')
        check(analysis['source_bindings'][item['arm'] + '_completion'] == complete_link
              and analysis['source_bindings'][item['arm'] + '_evaluation'] == complete['evaluation']
              and item['checkpoint'] == model['checkpoint']
              and item['receipt'] == next(r['receipt'] for r in model['records'] if r['block_id'] == gap.BLOCK_ID),
              'Saved means are stale or belong to another model')
        check(item['gap_outcomes'] == {'missing': 19} and item['gap_component_count'] == 0
              and [r['frame'] for r in item['gap_rows']] == list(gap.GAP)
              and all(r['outcome'] == 'missing' and r['independent_component_count'] == r['saved_component_count'] == 0
                      and r['global_peak'] <= .3 and r['sampled_mean_hash_matches_record'] for r in item['gap_rows']),
              'Conditional probe requires persistent weak/absent gap response in every completed checkpoint')
        bound_path(ROOT, item['receipt'])
        bound_path(ROOT, item['records'])
    checkpoint = {'path': Path(args.checkpoint).as_posix(), 'sha256': args.checkpoint_sha256, 'bytes': args.checkpoint_bytes}
    selected = actual_models[(args.arm, args.epoch)]
    check(checkpoint == selected[3]['checkpoint'], 'Explicit arm/absolute epoch/checkpoint binding differs')
    bound_path(ROOT, checkpoint)
    monitor = (ROOT / args.monitor).resolve()
    check(monitor.is_relative_to(ROOT / 'data/outputs'), 'Supervisor folder escaped outputs')
    policy = read_json(monitor / 'policy.json')
    owned = read_json(monitor / 'owned_process.json')
    ownership = verify_owned_worker(ROOT, monitor, MODULE, sys.argv[1:])
    return {'mode': MODE, 'arm': args.arm, 'absolute_epoch': args.epoch, 'checkpoint': checkpoint,
        'preparation': preparation_link, 'saved_mean_analysis': analysis_link,
        'comparison_completion': selected[0], 'comparison_evaluation': selected[1]['evaluation'],
        'training_result': selected[2]['identity']['training_result'],
        'supervisor_policy': bind(ROOT, monitor / 'policy.json'), 'owned_process': bind(ROOT, monitor / 'owned_process.json'),
        'owned_worker_verification': ownership,
        'forward_call_budget': 8, 'optimizer_updates': 0, 'protected_reads': 0, 'new_labels': 0,
        'synthetic_accuracy_scoring': False, 'production_substitution': False, 'model_adopted': False}


def run(args, prepared, tensors):
    identity = prerequisites(args, prepared)
    OUTPUT.mkdir(parents=True, exist_ok=False)  # No automatic repeat/resume of this diagnostic.
    write_once(OUTPUT / 'started.json', {'identity': identity, 'started_at_utc': stamp()})
    started_calls, completed_calls, results = 0, 0, []
    adapter = None
    try:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        adapter = evaluation.make_adapter(ROOT, {'selected_method': {
            'checkpoint': identity['checkpoint'], 'provenance': identity['training_result']}})
        adapter.model.eval()
        adapter.model.requires_grad_(False)
        check(not any(m.training for m in adapter.model.modules()), 'All model modules must stay in evaluation mode')
        buffers = {n: t.detach().cpu().clone() for n, t in adapter.model.named_buffers()}
        yy, xx = np.indices((432, 768))
        middle_maps = {}
        for case in prepared['cases']:
            check(started_calls < 8, 'Forward-call budget exhausted')
            name, center = case['name'], case['center_frame']
            value = tensors[name]
            check(array_sha(value.numpy()) == case['normalized_float32_input_sha256'], 'Prepared input changed')
            started_calls += 1
            write_once(OUTPUT / (name + '_started.json'), {'identity': identity, 'case': case, 'forward_call_number': started_calls})
            values = resolution._model_values(adapter.model, adapter.device, value, 768, 432)
            check(values.shape == (3, 432, 768) and values.dtype == np.float32
                  and np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all(), 'Raw sigmoid channel schema differs')
            path = OUTPUT / (name + '_sigmoid_channels.npy')
            with path.open('xb') as stream:
                np.save(stream, values, allow_pickle=False)
            middle = values[1]
            x, y = case['accepted_center_reference']['geometry']['center_xy_px']
            mask = (xx * 2.5 - x) ** 2 + (yy * 2.5 - y) ** 2 <= 100
            result = {'case': case, 'forward_call_number': started_calls, 'raw_sigmoid_channels': bind(ROOT, path),
                'channel_sha256': [array_sha(channel) for channel in values], 'middle_channel_index': 1,
                'middle_global_peak': float(middle.max()), 'middle_reference_circle_peak': float(middle[mask].max()),
                'middle_reference_circle_mean': float(middle[mask].mean()), 'reference_circle_source_radius_px': 10,
                'accuracy_score_computed': False, 'native_averaged_prediction_reconstructed': False}
            write_once(OUTPUT / (name + '_completed.json'), result)
            results.append(result)
            middle_maps[(center, case['condition'])] = middle.copy()
            completed_calls += 1
            print(json.dumps({'event': 'diagnostic_forward_complete', 'case': name, 'completed_calls': completed_calls}), flush=True)
        check(started_calls == completed_calls == 8, 'Exactly eight diagnostic forwards required')
        check(all(torch.equal(t.detach().cpu(), buffers[n]) for n, t in adapter.model.named_buffers()), 'Model buffers changed')
        pairs = []
        for center in CENTERS:
            real = next(r for r in results if r['case']['center_frame'] == center and r['case']['condition'] == 'native')
            repeated = next(r for r in results if r['case']['center_frame'] == center and r['case']['condition'] == 'repeated_center')
            a, b = middle_maps[(center, 'native')], middle_maps[(center, 'repeated_center')]
            pairs.append({'center_frame': center, 'middle_pixels_identical': True,
                'native_reference_peak': real['middle_reference_circle_peak'], 'repeated_reference_peak': repeated['middle_reference_circle_peak'],
                'repeated_minus_native_reference_peak': repeated['middle_reference_circle_peak'] - real['middle_reference_circle_peak'],
                'mean_absolute_middle_map_change': float(np.abs(b - a).mean()), 'causal_or_accuracy_conclusion_assigned': False})
        result = {'status': 'completed_diagnostic_only', 'identity': identity, 'cases': results, 'pairs': pairs,
            'adapter_provenance': adapter.provenance, 'forward_calls': 8, 'optimizer_updates': 0,
            'model_buffers_unchanged': True, 'new_labels': 0, 'protected_reads': 0, 'source_pixel_reads': 0,
            'human_visual_acceptance': None, 'model_adopted': False, 'ball_phase_accepted': False,
            'limits': [prepared['interpretation'], prepared['limit'], 'All three sigmoid channels retained; no logits, fitting, native-mean reconstruction or synthetic accuracy scoring.']}
        write_once(OUTPUT / 'completed.json', result)
        return {'status': result['status'], 'completion': bind(ROOT, OUTPUT / 'completed.json'), 'forward_calls': 8}
    except BaseException as error:
        write_once(OUTPUT / 'failed.json', {'identity': identity, 'error': str(error), 'traceback': traceback.format_exc(),
            'forward_calls_started': started_calls, 'forward_calls_completed': completed_calls,
            'automatic_retry': False, 'optimizer_updates': 0})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--run', action='store_true')
    parser.add_argument('--mode', required=True, choices=[MODE])
    parser.add_argument('--preparation')
    parser.add_argument('--saved-analysis')
    parser.add_argument('--arm', choices=['constant', 'cosine'])
    parser.add_argument('--epoch', type=int, choices=range(6, 11))
    parser.add_argument('--checkpoint')
    parser.add_argument('--checkpoint-sha256')
    parser.add_argument('--checkpoint-bytes', type=int)
    parser.add_argument('--monitor')
    args = parser.parse_args()
    required = ('preparation', 'saved_analysis', 'arm', 'epoch', 'checkpoint', 'checkpoint_sha256', 'checkpoint_bytes', 'monitor')
    check(all(getattr(args, k) is None for k in required) if args.prepare else all(getattr(args, k) is not None for k in required),
          'Preparation takes no execution arguments; execution requires every explicit binding and owned monitor')
    torch.set_num_threads(2)
    cv2.setNumThreads(1)
    began = time.perf_counter()
    try:
        prepared, tensors = prepare()
        if args.prepare:
            path = FOLDER / ('middle_sensitivity_preparation_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
            write_once(path, prepared)
            result = {'status': 'prepared_cpu_only', 'preparation': bind(ROOT, path), 'cases': 8, 'model_calls': 0,
                      'CUDA_initialized': torch.cuda.is_initialized(), 'elapsed_seconds': time.perf_counter() - began}
        else:
            result = run(args, prepared, tensors)
        print(json.dumps(result, indent=2), flush=True)
    except BaseException as error:
        path = FOLDER / ('middle_sensitivity_failure_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        write_once(path, {'status': 'failed_preserved', 'mode': args.mode, 'requested_execution': args.run,
            'error': str(error), 'traceback': traceback.format_exc(), 'elapsed_seconds': time.perf_counter() - began})
        raise


if __name__ == '__main__':
    main()

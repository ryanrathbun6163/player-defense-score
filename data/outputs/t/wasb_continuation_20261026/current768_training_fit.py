"""One explicit current768 training-fit census, prepared without model execution.

All native training triplets enter aligned observations. Only valid output
channels enter the unchanged focal loss. No fitting, new labels, validation
pixels, protected data, checkpoint selection or phase acceptance occurs.
"""
import argparse
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
FOLDER = Path(__file__).parent
MODE = 'current768_training_fit_v0.1'
MODULE = 'src.ball_tracking.continuation_training_fit_diagnostic'
LAUNCHER = ROOT / 'src/ball_tracking/continuation_training_fit_diagnostic.py'
RECIPE = ROOT / 'configs/ball_tracking/proposals/wasb_continuation_v0_1.json'
RECIPE_SHA = '46b76b16c12125f5dab1ffbb96fc1521e951997605c6018baece8253250910d4'
OUTPUT = ROOT / 'data/outputs/ball_tracking/wasb_continuation_v0_1/current_training_fit_v0_1'
GAP_HELPER = FOLDER / 'saved_det_gap_analysis.py'
GAP_HELPER_SHA = 'f1d08d0a6ac90d147f0aa3885be98369140842e36264b932b617bb0dbc55cf6e'
if hashlib.sha256(GAP_HELPER.read_bytes()).hexdigest() != GAP_HELPER_SHA:
    raise ValueError('Reviewed comparison metadata helper changed')
spec = importlib.util.spec_from_file_location('completed_continuation_metadata', GAP_HELPER)
gap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gap)
from src.ball_tracking import completion_training_assessment as original
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_resolution as resolution
from src.ball_tracking import wasb_training as training
from src.ball_tracking import wasb_adapter
from src.ball_tracking.wasb_experiment import bound_path, canonical, read_json
import cv2
import numpy as np
import torch

check, bind, write_once = runtime.check, runtime.binding, runtime.atomic_write_once
METRICS = ('frames', 'eligible_frames', 'matched', 'wrong', 'missing', 'certain_hidden_frames',
           'certain_hidden_emissions', 'uncertain_hidden_frames', 'uncertain_hidden_emissions', 'unscored')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def frame_metrics(block, record):
    """Partition actual emitted unique-frame scores; uncertainty stays separate."""
    groups = {}
    check(record['block_id'] == block['block_id'] and len(record['frame_results']) == len(block['frames']),
          'Actual scored producer/native frame census differs')
    for frame, scored in zip(block['frames'], record['frame_results'], strict=True):
        annotation = frame['annotation']
        check(scored['source_frame_index'] == frame['source_frame_index'] == annotation['frame_index']
              and scored['source_pts_ticks'] == frame['source_pts_ticks'] and scored['visibility'] == annotation['visibility'],
              'Actual scored producer/native annotation join differs')
        group = groups.setdefault(annotation['visibility'], {name: 0 for name in METRICS})
        group['frames'] += 1
        if annotation['localization_eligible']:
            check(scored['outcome'] in {'matched', 'wrong', 'missing'}, 'Eligible frame has unscored outcome')
            group['eligible_frames'] += 1
            group[scored['outcome']] += 1
        else:
            check(scored['outcome'] not in {'matched', 'wrong', 'missing'}, 'Ineligible reference scored as localization')
            if annotation['visibility'] == 'not_visible' and annotation['game_ball_identity_certainty'] in {'certain', 'probable'}:
                prefix = 'certain_hidden' if annotation['game_ball_identity_certainty'] == 'certain' else 'uncertain_hidden'
                check(scored['outcome'] in {'hidden_alarm', 'hidden_quiet'}, 'Hidden reference outcome differs')
                group[prefix + '_frames'] += 1
                group[prefix + '_emissions'] += int(scored['outcome'] == 'hidden_alarm')
            else:
                check(scored['outcome'] == 'unscored', 'Unlocalizable/indeterminate reference was scored')
                group['unscored'] += 1
    for key in ('eligible_frames', 'matched', 'wrong', 'missing', 'certain_hidden_emissions'):
        check(sum(group[key] for group in groups.values()) == record[key], 'Visibility partition differs from actual score')
    return groups


def sum_groups(target, source):
    for group, values in source.items():
        into = target.setdefault(group, {name: 0 for name in METRICS})
        for name in METRICS:
            into[name] += values[name]


def prepare():
    check(not torch.cuda.is_initialized(), 'Preparation must remain CPU-only')
    recipe_link = bind(ROOT, RECIPE)
    check(recipe_link['sha256'] == RECIPE_SHA, 'Frozen continuation recipe changed')
    recipe = read_json(RECIPE)
    source_recipe = read_json(bound_path(ROOT, recipe['source_recipe']))
    primary = read_json(bound_path(ROOT, source_recipe['parent_recipe']))
    package = read_json(bound_path(ROOT, primary['package']))
    nfhs = read_json(bound_path(ROOT, primary['nfhs_training_config']))
    for record in recipe['code_bindings'] + source_recipe['code_bindings'] + primary['code_bindings']:
        bound_path(ROOT, record)
    for record in package['reference_bindings']:
        bound_path(ROOT, record)
    check(recipe['resolution'] == {'width': 768, 'height': 432, 'target_radius': 3.75}
          and recipe['protected_evaluation_authorized'] is False and package['protected_evaluation_authorized'] is False,
          'Exact permitted768 training package required')
    view = original.training_view(package)
    blocks = view['training_blocks']
    census = {'blocks': len(blocks), 'unique_frames': sum(len(b['frames']) for b in blocks),
              'native_forward_calls': 0, 'supervised_triplets': 0, 'all_masked_triplets': 0,
              'supervised_channel_occurrences': 0, 'masked_channel_occurrences': 0}
    by_game, unique, exposure = {}, Counter(), Counter()
    source_cache = read_json(bound_path(ROOT, recipe['source_cache_preparation']))
    source_receipts = {item['path']: item for item in source_cache['blocks']}
    store = resolution.FrameStore(ROOT, package, ROOT / recipe['cache_root'])
    # Keep full-package cache identity, then remove every validation block before access.
    store.blocks = {b['block_id']: b for b in blocks}
    receipts = []
    for block in blocks:
        path = ROOT / recipe['cache_root'] / hashlib.sha256(block['block_id'].encode()).hexdigest()[:24] / 'receipt.json'
        check(path.exists(), 'Missing existing training cache: regeneration prohibited')
        link = bind(ROOT, path)
        check(source_receipts.get(link['path']) == link, 'Existing training cache no longer matches completed parent')
        receipts.append(link)
    try:
        with redirect_stdout(io.StringIO()):
            cache_report = store.prepare()
        check(cache_report['blocks'] == receipts and cache_report['unique_block_frames'] == 3329,
              'Training-only cache receipt census differs')
        preprocessing = []
        for block in blocks:
            key, frames = block['block_id'], block['frames']
            info = by_game.setdefault(block['game_id'], {'domain': block['domain'], 'blocks': 0, 'unique_frames': 0,
                 'native_forward_calls': 0, 'supervised_triplets': 0, 'all_masked_triplets': 0,
                 'unique_supervision': Counter(), 'channel_occurrences': Counter()})
            info['blocks'] += 1
            info['unique_frames'] += len(frames)
            for frame in frames:
                kind = training.annotation_kind(store.labels[key][frame['source_frame_index']])
                check(kind == frame['kind'] and frame['valid_output_channel'] == (kind != 'masked'),
                      'Parsed actual target kind/mask differs from package producer')
                category = frame['annotation']['visibility'] if kind == 'positive' else kind
                unique[category] += 1
                info['unique_supervision'][category] += 1
            contributor_counts = Counter()
            for offset in range(len(frames) - 2):
                triplet = frames[offset:offset + 3]
                valid = [f['valid_output_channel'] for f in triplet]
                census['native_forward_calls'] += 1
                info['native_forward_calls'] += 1
                mask_category = 'supervised_triplets' if any(valid) else 'all_masked_triplets'
                census[mask_category] += 1
                info[mask_category] += 1
                census['supervised_channel_occurrences'] += sum(valid)
                census['masked_channel_occurrences'] += 3 - sum(valid)
                for frame in triplet:
                    contributor_counts[frame['source_frame_index']] += 1
                    category = frame['annotation']['visibility'] if frame['kind'] == 'positive' else frame['kind']
                    exposure[category] += 1
                    info['channel_occurrences'][category] += 1
            check(list(contributor_counts.values()) == [1, 2] + [3] * (len(frames) - 4) + [2, 1],
                  'Full native boundary-contributor policy differs')
            for offset in sorted({0, (len(frames) - 3) // 2, len(frames) - 3}):
                indices = [f['source_frame_index'] for f in frames[offset:offset + 3]]
                actual = store.inputs(key, indices)
                expected = torch.cat([runtime.normalized_tensor(store.arrays[key][store.positions[key][i]]) for i in indices])
                check(torch.equal(actual, expected) and actual.shape == (9, 432, 768), 'Actual frozen768 cache normalization differs')
                preprocessing.append({'block_id': key, 'frame_indices': indices,
                    'normalized_input_sha256': hashlib.sha256(actual.numpy().tobytes()).hexdigest()})
        check(census == {'blocks': 26, 'unique_frames': 3329, 'native_forward_calls': 3277, 'supervised_triplets': 3103,
              'all_masked_triplets': 174, 'supervised_channel_occurrences': 9114, 'masked_channel_occurrences': 717},
              'Derived native/supervised budget differs from actual training producer')
        check(unique == Counter({'partially_visible': 2167, 'fully_visible': 774, 'hidden': 147, 'masked': 241}),
              'Unique training reference census differs')
        upstream = []
        for relative, digest in wasb_adapter.SOURCE_SHA256.items():
            link = bind(ROOT, ROOT / nfhs['upstream_source'] / relative)
            check(link['sha256'] == digest, 'Pinned model source differs')
            upstream.append(link)
        bound_path(ROOT, nfhs['pretrained_checkpoint'])
        implementations = [bind(ROOT, ROOT / f'src/ball_tracking/{name}.py') for name in
            ('completion_training_assessment', 'completion_training_runtime', 'wasb_resolution', 'wasb_training',
             'wasb_adapter', 'wasb_adapted_adapter', 'nba_wasb_diagnostic', 'annotations', 'gpu_supervision')]
        prepared = {'schema_version': 'current768_training_fit_preparation/v0.1', 'status': 'prepared_cpu_only', 'mode': MODE,
            'helper': bind(ROOT, Path(__file__)), 'launcher': bind(ROOT, LAUNCHER), 'execution_module': MODULE,
            'comparison_metadata_helper': bind(ROOT, GAP_HELPER), 'recipe': recipe_link,
            'source_recipe': recipe['source_recipe'], 'primary_recipe': source_recipe['parent_recipe'], 'package': primary['package'],
            'model_config': primary['nfhs_training_config'], 'pretrained_constructor_asset': nfhs['pretrained_checkpoint'],
            'upstream_model_sources': upstream, 'implementations': implementations,
            'source_cache_preparation': recipe['source_cache_preparation'], 'training_cache_receipts': receipts,
            'training_block_sha256': {b['block_id']: canonical(b) for b in blocks},
            'counts': census, 'by_game': by_game, 'unique_supervision': dict(unique), 'channel_occurrences': dict(exposure),
            'valid_pixel_denominator': 9114 * 432 * 768, 'exact_normalization_checks': preprocessing,
            'model_calls': 0, 'model_tensor_loads': 0, 'source_pixel_reads': 0, 'validation_pixel_reads': 0,
            'protected_reads': 0, 'new_labels': 0, 'optimizer_updates': 0, 'CUDA_initialized': False,
            'policy': {'threshold': .3, 'strict_threshold': True, 'match_radius_source_px': 10,
                'aggregation': 'ascending_float32_aligned_contributor_mean', 'triplet_stride': 1,
                'target_radius_working_px': 3.75, 'loss': 'frozen_clamped_gamma2_wbce',
                'precision': 'float32', 'loss_category_reduction': 'float64', 'augmentation': False,
                'all_masked_native_triplets_inferred_but_excluded_from_loss': True},
            'limits': ['One exhaustive unaugmented native pass, not the balanced augmented sampled batch-two optimizer objective.',
                'Unique-frame fit and repeated output-channel loss/exposure have different denominators.',
                'Training fit is descriptive; no generalization, convergence, checkpoint selection or ball-phase pass is established.',
                'No raw mean arrays/logits will be retained; every observation, component, mean digest and loss decomposition will be preserved.']}
        check(not torch.cuda.is_initialized(), 'CPU preparation initialized CUDA')
        return prepared, recipe, package, nfhs, store
    except BaseException:
        store.close()
        raise


def prerequisites(args, prepared, recipe):
    preparation_link = bind(ROOT, ROOT / args.preparation)
    check(read_json(ROOT / args.preparation) == prepared, 'Current source/cache differs from explicit preparation')
    comparisons = gap.completed_comparisons(recipe, {'recipe': prepared['recipe']}, False)
    chosen = [(link, complete, published, model) for arm, link, complete, published in comparisons
              for model in published['models'] if arm == args.arm and model['epoch'] == args.epoch]
    check(len(chosen) == 1, 'Explicit diagnostic arm/absolute epoch required')
    link, complete, published, model = chosen[0]
    checkpoint = {'path': Path(args.checkpoint).as_posix(), 'sha256': args.checkpoint_sha256, 'bytes': args.checkpoint_bytes}
    check(model['checkpoint'] == checkpoint and bool(args.selection_reason.strip()), 'Explicit chosen checkpoint/reason differs')
    bound_path(ROOT, checkpoint)
    monitor = (ROOT / args.monitor).resolve()
    check(monitor.is_relative_to(ROOT / 'data/outputs'), 'Monitor escaped output directory')
    policy, owned = read_json(monitor / 'policy.json'), read_json(monitor / 'owned_process.json')
    check(policy['module'] == MODULE and policy['arguments'] == sys.argv[1:] and owned['pid'] == os.getpid()
          and owned['job_owns_descendants'] is True and not (monitor / 'finished.json').exists(), 'Active exact owned supervisor required')
    return {'schema_version': 'current768_training_fit_identity/v0.1', 'mode': MODE, 'preparation': preparation_link,
        'arm': args.arm, 'absolute_epoch': args.epoch, 'checkpoint': checkpoint, 'selection_reason': args.selection_reason.strip(),
        'both_completed_comparisons': {arm: link for arm, link, _, _ in comparisons},
        'chosen_comparison_evaluation': complete['evaluation'], 'training_result': published['identity']['training_result'],
        'supervisor_policy': bind(ROOT, monitor / 'policy.json'), 'owned_process': bind(ROOT, monitor / 'owned_process.json'),
        'native_forward_call_budget': 3277, 'optimizer_updates': 0, 'new_labels': 0, 'protected_evaluation_authorized': False,
        'checkpoint_selection_changed': False, 'model_adopted': False, 'ball_phase_accepted': False}


def assess_block(model, device, store, block, event):
    frames = [{'source_frame_index': f['source_frame_index'], 'source_pts_ticks': f['source_pts_ticks'], 'png': f['png']}
              for f in block['frames']]
    indexed = {f['source_frame_index']: f for f in block['frames']}
    source = block['source_video']
    manifest = {'source_video': source, 'time_base': block['time_base']}
    segment = {'kind': 'training_only_assessment', 'source_frame_range_inclusive': [frames[0]['source_frame_index'], frames[-1]['source_frame_index']]}
    totals, targets_by_frame, calls = original.empty_loss(), {}, 0
    def provide(selected):
        nonlocal calls
        indices = [f['source_frame_index'] for f in selected]
        event({'event': 'started', 'block_id': block['block_id'], 'frame_indices': indices})
        for old in list(targets_by_frame):
            if old < indices[0]:
                del targets_by_frame[old]
        for index in indices:
            if index not in targets_by_frame:
                targets_by_frame[index] = resolution.annotation_target(store.labels[block['block_id']][index],
                    source['width_px'], source['height_px'], width=768, height=432, radius=3.75)
        rows = [targets_by_frame[index] for index in indices]
        kinds = [row[2]['kind'] for row in rows]
        check(kinds == [indexed[i]['kind'] for i in indices]
              and [r[1] for r in rows] == [indexed[i]['valid_output_channel'] for i in indices], 'Actual target/mask transport differs')
        with torch.inference_mode():
            value = store.inputs(block['block_id'], indices).unsqueeze(0).to(device)
            logits = model(value)[0]
            check(logits.dtype == torch.float32 and logits.shape == (1, 3, 432, 768)
                  and bool(torch.isfinite(logits).all()), 'Actual768 assessment logits differ')
            targets = torch.from_numpy(np.stack([row[0] for row in rows])).unsqueeze(0).to(device)
            valid = torch.tensor([[row[1] for row in rows]], dtype=torch.bool, device=device)
            part = original.loss_breakdown(logits, targets, valid, kinds)
            values = logits.sigmoid()[0].cpu().numpy().astype(np.float32, copy=False)
        original.merge_loss(totals, part)
        calls += 1
        event({'event': 'completed', 'block_id': block['block_id'], 'frame_indices': indices, 'loss': part})
        return values
    observations = [resolution.select_observation(frame, mean, count, manifest, segment)
                    for frame, mean, count in resolution.stream_means(frames, provide)]
    score = runtime.scored_block(block, observations)
    return {**score, 'source_video': source, 'unique_frame_supervision': dict(Counter(f['kind'] for f in block['frames'])),
        'visibility_metrics': frame_metrics(block, score), 'loss': totals, 'observations': observations,
        'resources': {'model_calls': calls, 'source_video_decodes': 0, 'source_png_reads': 0,
                      'validation_png_reads': 0, 'protected_png_reads': 0, 'optimizer_updates': 0}}


def summarize(records):
    result = original.aggregate(records)
    domains = {}
    for row in records:
        sum_groups(result['sources'][row['game_id']].setdefault('visibility_metrics', {}), row['visibility_metrics'])
        sum_groups(domains.setdefault(row['domain'], {}), row['visibility_metrics'])
    result['unique_frame_visibility_by_domain'] = domains
    result['NBA_primary_sources'] = [game for game, source in result['sources'].items() if source['domain'] == 'nba']
    result['NFHS_secondary_sources'] = [game for game, source in result['sources'].items() if source['domain'] == 'nfhs']
    numerator = sum(c['term_sum'] for c in result['loss']['categories'].values())
    result['loss']['category_numerator_fractions'] = {k: v['term_sum'] / numerator if numerator else None
                                                   for k, v in result['loss']['categories'].items()}
    return result


def execute(args, prepared, recipe, package, nfhs, store):
    identity = prerequisites(args, prepared, recipe)
    OUTPUT.mkdir(parents=True, exist_ok=False)  # Preserve interrupted evidence; never silently repeat the budget.
    write_once(OUTPUT / 'started.json', {'identity': identity, 'counts': prepared['counts'], 'started_at_utc': stamp()})
    started, completed, records, receipts = 0, 0, [], []
    try:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        adapter = original.make_adapter(ROOT, nfhs, identity)
        adapter.model.eval().requires_grad_(False)
        before = original.model_digest(adapter.model)
        with (OUTPUT / 'native_triplets.jsonl').open('x', encoding='utf-8') as log:
            def event(row):
                nonlocal started, completed
                if row['event'] == 'started':
                    check(started < 3277, 'Exact forward-call budget exhausted')
                    started += 1
                else:
                    completed += 1
                log.write(json.dumps({**row, 'at_utc': stamp()}, allow_nan=False) + '\n')
                log.flush()
            for block in original.training_view(package)['training_blocks']:
                record = assess_block(adapter.model, adapter.device, store, block, event)
                check(original.model_digest(adapter.model) == before, 'Model parameters or buffers changed')
                path = OUTPUT / (hashlib.sha256(block['block_id'].encode()).hexdigest()[:24] + '_records.json')
                write_once(path, record)
                receipt_path = path.with_name(path.stem + '_receipt.json')
                write_once(receipt_path, {'identity': identity, 'block_sha256': canonical(block),
                    'record': bind(ROOT, path), 'model_tensors_unchanged': True})
                receipts.append(bind(ROOT, receipt_path))
                records.append(record)
                print(json.dumps({'event': 'training_block_assessed', 'block_id': block['block_id'],
                    'matched': record['matched'], 'eligible': record['eligible_frames'], 'forward_calls_completed': completed}), flush=True)
        summary = summarize(records)
        check(started == completed == summary['model_calls'] == 3277
              and summary['loss']['supervised_triplets'] == 3103 and summary['loss']['all_masked_triplets'] == 174
              and summary['loss']['supervised_channel_occurrences'] == 9114 and summary['loss']['masked_channel_occurrences'] == 717
              and summary['loss']['valid_pixel_denominator'] == prepared['valid_pixel_denominator'], 'Actual native/loss census differs')
        assessment = {'schema_version': 'current768_training_fit_assessment/v0.1', 'status': 'completed_training_only',
            'identity': identity, 'counts': prepared['counts'], **summary, 'block_receipts': receipts,
            'source_pixel_reads': 0, 'validation_pixel_reads': 0, 'protected_reads': 0, 'optimizer_updates': 0, 'new_labels': 0,
            'model_tensors_unchanged': True, 'checkpoint_selection_changed': False, 'model_adopted': False,
            'ball_phase_accepted': False, 'human_visual_acceptance': None, 'limits': prepared['limits']}
        write_once(OUTPUT / 'assessment.json', assessment)
        completion = {'status': 'completed', 'identity': identity, 'assessment': bind(ROOT, OUTPUT / 'assessment.json'),
                      'forward_calls': 3277, 'optimizer_updates': 0}
        write_once(OUTPUT / 'completed.json', completion)
        return {'status': 'completed_training_only', 'completion': bind(ROOT, OUTPUT / 'completed.json')}
    except BaseException as error:
        write_once(OUTPUT / 'failed.json', {'identity': identity, 'error': str(error), 'traceback': traceback.format_exc(),
            'forward_calls_started': started, 'forward_calls_completed': completed, 'automatic_retry': False,
            'failed_inference_is_not_missing': True, 'optimizer_updates': 0})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--run', action='store_true')
    parser.add_argument('--mode', required=True, choices=[MODE])
    parser.add_argument('--preparation')
    parser.add_argument('--arm', choices=['constant', 'cosine'])
    parser.add_argument('--epoch', type=int, choices=range(6, 11))
    parser.add_argument('--checkpoint')
    parser.add_argument('--checkpoint-sha256')
    parser.add_argument('--checkpoint-bytes', type=int)
    parser.add_argument('--selection-reason')
    parser.add_argument('--monitor')
    args = parser.parse_args()
    keys = ('preparation', 'arm', 'epoch', 'checkpoint', 'checkpoint_sha256', 'checkpoint_bytes', 'selection_reason', 'monitor')
    check(all(getattr(args, k) is None for k in keys) if args.prepare else all(getattr(args, k) is not None for k in keys),
          'Preparation takes no execution arguments; run requires explicit checkpoint/selection/monitor bindings')
    torch.set_num_threads(2)
    cv2.setNumThreads(1)
    began, store = time.perf_counter(), None
    try:
        prepared, recipe, package, nfhs, store = prepare()
        if args.prepare:
            path = FOLDER / ('current768_training_fit_preparation_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
            write_once(path, prepared)
            result = {'status': 'prepared_cpu_only', 'preparation': bind(ROOT, path), 'counts': prepared['counts'],
                'normalization_checks': len(prepared['exact_normalization_checks']), 'model_calls': 0,
                'CUDA_initialized': torch.cuda.is_initialized(), 'elapsed_seconds': time.perf_counter() - began}
        else:
            result = execute(args, prepared, recipe, package, nfhs, store)
        print(json.dumps(result, indent=2), flush=True)
    except BaseException as error:
        path = FOLDER / ('current768_training_fit_failure_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        write_once(path, {'status': 'failed_preserved', 'requested_execution': args.run, 'error': str(error),
                         'traceback': traceback.format_exc(), 'elapsed_seconds': time.perf_counter() - began})
        raise
    finally:
        if store is not None:
            store.close()


if __name__ == '__main__':
    main()

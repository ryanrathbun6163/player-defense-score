"""CPU-only inspection of already-saved DET means; never runs a model.

--parent preserves the existing five-epoch 768 comparison. --continuations
requires both completed arm comparisons and reports every absolute epoch6-10.
It hashes small source JSON records and sampled mean slices. The full large
mean-file digests are transported from receipts, not recomputed. Every output
gets a fresh exclusive filename, preserving previous analyses and failures.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
import traceback

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).parent
RECIPE = ROOT / 'configs/ball_tracking/proposals/wasb_continuation_v0_1.json'
RECIPE_SHA = '46b76b16c12125f5dab1ffbb96fc1521e951997605c6018baece8253250910d4'
INPUTS = ROOT / 'data/outputs/ball_tracking/wasb_resolution_v0_1/paired_nba_review_inputs_v0_1.json'
INPUTS_SHA = 'a45c7085d8d3c7dec5940b950606660d506398c0c0923e6459faa5c10a698599'
PRIOR_AUDIT = ROOT / 'data/outputs/t/nba_resolution_resume_20261026/resolution_comparison_audit_20261026T163833143856Z.json'
BLOCK_ID = 'sas_det_q1_c02:10668-11898'
GAP = tuple(range(11075, 11094))
RECOVERY = (11098, 11099, 11100, 11101)
RESOLUTION = {'width': 768, 'height': 432, 'target_radius': 3.75}
CHECKS = 0


def check(value, message):
    global CHECKS
    CHECKS += 1
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def bind(path):
    path = Path(path).resolve()
    check(path.is_relative_to(ROOT), 'Binding escaped repository')
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def verified(record):
    path = (ROOT / record['path']).resolve()
    check(bind(path) == record, 'Changed bound input: ' + record['path'])
    return path


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def context():
    recipe_link, input_link = bind(RECIPE), bind(INPUTS)
    check(recipe_link['sha256'] == RECIPE_SHA and input_link['sha256'] == INPUTS_SHA, 'Frozen recipe/review changed')
    recipe, inputs = read(RECIPE), read(INPUTS)
    check(recipe['status'] == 'frozen_before_model_execution' and recipe['resolution'] == RESOLUTION
          and recipe['new_labels'] == 0 and recipe['protected_evaluation_authorized'] is False, 'Closed permitted scope')
    candidates = [entry['block'] for entry in inputs['blocks'] if entry['block']['block_id'] == BLOCK_ID]
    check(len(candidates) == 1, 'Exact original DET context required')
    block = candidates[0]
    check(block['source_video']['width_px'] == 1920 and block['source_video']['height_px'] == 1080
          and block['time_base'] == '1/90000' and not block.get('protected_ranges'), 'Exact native affine/timing domain')
    check(len(block['frames']) == 1231 and all(f['state'] == 'permitted' for f in block['frames']), 'Permitted native frame census')
    check([f['source_frame_index'] for f in block['frames']] == list(range(10668, 11899)), 'Native frame order changed')
    by_index = {f['source_frame_index']: f for f in block['frames']}
    references = []
    for index in GAP:
        frame, annotation = by_index[index], by_index[index]['annotation']
        check(annotation['localization_eligible'] and annotation['visibility'] == 'partially_visible'
              and annotation['game_ball_identity_certainty'] == 'probable'
              and annotation['geometry']['uncertainty_radius_px'] == 8.0, 'Accepted gap reference changed')
        references.append({'frame': index, 'source_pts_ticks': frame['source_pts_ticks'], 'duration_ticks': frame['duration_ticks'],
            'visibility': annotation['visibility'], 'identity_certainty': annotation['game_ball_identity_certainty'],
            'geometry': annotation['geometry'], 'difficulty_tags': annotation['difficulty_tags']})
    check(sum(row['duration_ticks'] for row in references) == 28530, 'Known eligible gap duration changed')
    sources = {'recipe': recipe_link, 'accepted_reference_transport': input_link,
               'source_evaluation': recipe['source_evaluation'], 'source_fit': recipe['source_completed']}
    return recipe, block, by_index, references, sources


def completed_comparisons(recipe, sources, parent):
    if parent:
        audit_link = bind(PRIOR_AUDIT)
        audit = read(PRIOR_AUDIT)
        check(audit['status'] == 'passed' and audit['mode'] == 'comparison'
              and audit['evaluation'] == recipe['source_evaluation'] and audit['fit_completion'] == recipe['source_completed']
              and audit['independently_reconstructed_768_mean_frames'] == 13510, 'Prior complete independent audit differs')
        complete_link = audit['completion']
        complete = read(verified(complete_link))
        published = read(verified(recipe['source_evaluation']))
        check(complete['status'] == 'completed' and complete['evaluation'] == recipe['source_evaluation']
              and complete['identity'] == published['identity'] and published['status'] == 'completed_evaluation'
              and published['schema_version'] == 'nba_resolution_comparison/v0.1'
              and [m['epoch'] for m in published['models']] == [1, 2, 3, 4, 5], 'Completed five-model parent comparison required')
        sources['prior_independent_full_comparison_audit'] = audit_link
        return [('parent_resolution', complete_link, complete, published)]
    results = []
    # Both arms must be complete before any new checkpoint is analyzed.
    for arm in ('constant', 'cosine'):
        path = ROOT / recipe['arms'][arm]['evaluation_output_root'] / 'completed.json'
        check(path.exists(), 'Both completed comparisons required; missing ' + arm)
    for arm in ('constant', 'cosine'):
        complete_link = bind(ROOT / recipe['arms'][arm]['evaluation_output_root'] / 'completed.json')
        complete = read(ROOT / complete_link['path'])
        published = read(verified(complete['evaluation']))
        fit_link = bind(ROOT / recipe['arms'][arm]['output_root'] / 'completed.json')
        fit = read(ROOT / fit_link['path'])
        check(complete['schema_version'] == published['schema_version'] == 'wasb_continuation_comparison/v0.1'
              and complete['status'] == 'completed' and published['status'] == 'completed_evaluation'
              and complete['identity'] == published['identity'] and published['arm'] == arm
              and published['identity']['recipe'] == sources['recipe'] and published['identity']['arm'] == arm
              and published['identity']['source_evaluation'] == recipe['source_evaluation']
              and published['identity']['training_result'] == fit_link and published['identity']['training_identity'] == fit['identity']
              and fit['arm'] == fit['identity']['arm'] == arm and fit['status'] == 'completed'
              and fit['completed_epochs'] == 10 and fit['new_completed_epochs'] == 5 and fit['completed_updates'] == 15520,
              'Arm-specific complete producer ancestry required')
        check([m['epoch'] for m in published['models']] == [6, 7, 8, 9, 10]
              and all(m['arm'] == arm and m['name'] == f"continuation_{arm}_epoch{m['epoch']}" for m in published['models']),
              'All five absolute epochs required per arm')
        sources[arm + '_fit'] = fit_link
        results.append((arm, complete_link, complete, published))
    return results


def model_analysis(arm, complete, published, model, block, by_index):
    links = [link for link in model['records'] if link['block_id'] == BLOCK_ID]
    check(len(links) == 1, 'Unique actual DET model record required')
    receipt_link = links[0]['receipt']
    receipt = read(verified(receipt_link))
    expected = {'comparison': published['identity'], 'checkpoint': model['checkpoint'],
                'block_sha256': canonical(block), 'validation_source': None}
    if arm != 'parent_resolution':
        expected['epoch'] = model['epoch']
    check(receipt['identity'] == expected and receipt['new_model_calls'] == 1229
          and receipt['reused_observation_frames'] == 0, 'Actual native DET receipt identity differs')
    body = read(verified(receipt['records']))
    check(body['block_id'] == BLOCK_ID and body['checkpoint'] == model['checkpoint']
          and body['resolution'] == RESOLUTION and body['validation_source'] is None, 'Actual DET body identity differs')
    if arm != 'parent_resolution':
        check(body['arm'] == arm and body['epoch'] == model['epoch'] and body['model'] == model['name'],
              'Actual body arm/absolute epoch/model differs')
    check(len(body['observations']) == len(body['score']['frame_results']) == 1231, 'Native body census differs')
    score = {r['source_frame_index']: r for r in body['score']['frame_results']}
    observations = {r['source_frame_index']: r for r in body['observations']}
    check(len(score) == len(observations) == 1231, 'Duplicate native producer rows')
    map_link = receipt['mean_heatmaps']
    path = (ROOT / map_link['path']).resolve()
    check(path.is_relative_to(ROOT) and path.stat().st_size == map_link['bytes'], 'Saved mean-map size/path differs')
    maps = np.load(path, mmap_mode='r', allow_pickle=False)
    rows = []
    try:
        check(maps.shape == (1231, 432, 768) and maps.dtype == np.float32, 'Exact saved map shape/dtype required')
        yy, xx = np.indices((432, 768))
        # Exact frozen 1920x1080 -> 768x432 affine has no translation.
        source_x, source_y = xx * 2.5, yy * 2.5
        for index in GAP + RECOVERY:
            frame, observation, scored = by_index[index], observations[index], score[index]
            check(observation['source_pts_ticks'] == frame['source_pts_ticks'] and observation['time_base'] == '1/90000'
                  and observation['source_png']['sha256'] == frame['png']['sha256']
                  and observation['inference_status'] == 'completed' and observation['temporal_contributions'] == 3,
                  'Completed same-native-frame transport with three contributors required')
            mean = maps[index - 10668]
            digest = hashlib.sha256(mean.tobytes()).hexdigest()
            check(digest == observation['mean_heatmap_sha256'], 'Sampled raw mean differs from recorded digest')
            check(np.isfinite(mean).all() and (mean >= 0).all() and (mean <= 1).all(), 'Sampled mean range differs')
            x, y = frame['annotation']['geometry']['center_xy_px']
            mask = (source_x - x) ** 2 + (source_y - y) ** 2 <= 100
            peak = float(mean.max())
            binary = (mean > .3).astype(np.uint8)
            components = int(cv2.connectedComponents(binary, connectivity=8)[0] - 1)
            check(components == len(observation['candidates']), 'Reconstructed component count differs')
            selected = observation['center_xy_px']
            # Four float32 ULPs conservatively cover three nonnegative additions/division.
            bound = min(1.0, peak * 3 + float(np.spacing(np.float32(peak * 3))) * 4)
            rows.append({'frame': index, 'outcome': scored['outcome'], 'state': observation['state'],
                'reference_center_xy_px': [x, y], 'global_peak': peak, 'local_10_source_px_peak': float(mean[mask].max()),
                'strict_threshold': .3, 'above_threshold_pixels': int(binary.sum()),
                'saved_component_count': len(observation['candidates']), 'independent_component_count': components,
                'selected_candidate_index': observation['selected_candidate_index'],
                'selected_reference_error_px': None if selected is None else math.dist(selected, [x, y]),
                'temporal_contributors': 3, 'single_contributor_global_upper_bound': bound,
                'any_single_contributor_over_threshold_ruled_out': bound <= .3,
                'sampled_mean_sha256': digest, 'sampled_mean_hash_matches_record': True})
    finally:
        maps._mmap.close()
    gap = rows[:19]
    surroundings = []
    for index in range(11070, 11106):
        frame, obs, scored = by_index[index], observations[index], score[index]
        annotation = frame['annotation']
        surroundings.append({'frame': index, 'visibility': annotation['visibility'],
            'localization_eligible': annotation['localization_eligible'], 'reference_category': scored['reference_category'],
            'outcome': scored['outcome'], 'state': obs['state'], 'component_count': len(obs['candidates'])})
    return {'arm': arm, 'model': model['name'], 'absolute_epoch': model['epoch'], 'checkpoint': model['checkpoint'],
        'receipt': receipt_link, 'records': receipt['records'], 'mean_maps_declared_binding': map_link,
        'full_mean_file_hash_recomputed': False, 'raw_mean_slices_hashed': len(rows),
        'gap_outcomes': dict(Counter(r['outcome'] for r in gap)),
        'gap_global_peak_range': [min(r['global_peak'] for r in gap), max(r['global_peak'] for r in gap)],
        'gap_local_10_source_px_peak_range': [min(r['local_10_source_px_peak'] for r in gap), max(r['local_10_source_px_peak'] for r in gap)],
        'gap_component_count': sum(r['saved_component_count'] for r in gap),
        'gap_all_single_contributor_over_threshold_ruled_out': all(r['any_single_contributor_over_threshold_ruled_out'] for r in gap),
        'gap_rows': gap, 'recovery_reference_rows': rows[19:], 'surrounding_scored_and_unscored_rows': surroundings}


def run(parent):
    recipe, block, frames, references, sources = context()
    comparisons = completed_comparisons(recipe, sources, parent)
    models = []
    for arm, complete_link, complete, published in comparisons:
        check(published['model_adopted'] is published['ball_phase_accepted'] is published['protected_evaluation_authorized'] is False
              and published['human_trajectory_acceptance'] is None and published['optimizer_updates'] == published['new_labels'] == 0,
              'Diagnostic cannot claim adoption or protected authorization')
        sources[arm + '_completion'] = complete_link
        sources[arm + '_evaluation'] = complete['evaluation']
        for model in published['models']:
            models.append(model_analysis(arm, complete, published, model, block, frames))
    motion = []
    for indices in (GAP, RECOVERY):
        centers = [frames[i]['annotation']['geometry']['center_xy_px'] for i in indices]
        steps = [math.dist(a, b) for a, b in zip(centers, centers[1:])]
        motion.append({'frame_range': [indices[0], indices[-1]], 'source_reference_step_px_min': min(steps),
            'source_reference_step_px_median': statistics.median(steps), 'source_reference_step_px_max': max(steps),
            'limit': 'Differences of accepted uncertain centers, not precise physical velocity or camera-compensated motion.'})
    visuals = [ROOT / 'data/outputs/t/nba_resolution_resume_20261026/paired_review_ai_observations.json',
               ROOT / 'data/outputs/t/nba_resolution_resume_20261026/paired_review_visuals_v0_1/det_gap_11075_11093_actual_crops.png',
               ROOT / 'data/outputs/t/nba_first_visual_diagnosis_20261026/inspection_notes.json']
    sources['prior_visual_evidence'] = [bind(p) for p in visuals]
    return {'status': 'passed_saved_mean_diagnostic', 'mode': 'parent' if parent else 'both_continuations',
        'source_bindings': sources, 'block_id': BLOCK_ID, 'source_dimensions': [1920, 1080], 'working_dimensions': [768, 432],
        'accepted_gap_references': references, 'eligible_gap_frames': 19, 'eligible_gap_duration_exact_seconds': '317/1000',
        'gap_reference_placement_uncertainty_px': 8, 'match_radius_source_px_unchanged': 10,
        'motion_context': motion, 'models': models, 'model_count': len(models),
        'sampled_map_hashes_validated': len(models) * 23,
        'interpretation_rules': [
            'No above-threshold component means component ranking cannot recover that frame.',
            'Sigmoid values are uncalibrated model responses, not correctness probabilities.',
            'The maximum possible individual nonnegative contributor is bounded by three times the global mean peak, with a small float32 allowance.',
            'A bound below0.3 rules out an individual above0.3 contributor being removed solely by averaging.',
            'Unscored surrounding references remain unscored; no interpolation or assumed immediate recovery at11094.',
            'Saved peak measurements distinguish response/selection mechanisms, not the causal origin of appearance suppression.'
        ],
        'prior_visual_findings_retained': 'Hand/forearm overlap, blur and sideline lettering at the accepted reference region; no causal attribution or new label.',
        'conditional_next_diagnostic': 'After both comparisons, inspect these saved means and exact existing inputs first. An optional eight-call real-versus-repeated-frame probe remains a separate proposal, not authorized or launched here.',
        'limits': ['Full large mean-file digests are transported from bound receipts, not recomputed here; sampled slices are individually rehashed.',
                   'Parent full-output audit is retained as prior evidence; this is not a repeat of its472085 checks.',
                   'No full scientific audit, new model selection, human trajectory acceptance, or phase pass is claimed.',
                   'No model tensors, inference, source-pixel decoding, protected inputs, new labels or optimizer operations.'],
        'production_imports': 0, 'GPU_calls': 0, 'model_calls': 0, 'model_tensor_loads': 0,
        'source_pixel_reads': 0, 'protected_reads': 0, 'new_labels': 0, 'optimizer_updates': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--parent', action='store_true')
    mode.add_argument('--continuations', action='store_true')
    args = parser.parse_args()
    cv2.setNumThreads(1)
    began = time.perf_counter()
    try:
        result = run(args.parent)
    except BaseException as error:
        result = {'status': 'failed_preserved', 'mode': 'parent' if args.parent else 'both_continuations',
                  'error': str(error), 'traceback': traceback.format_exc()}
    result.update(helper=bind(Path(__file__)), checks=CHECKS, at_utc=datetime.now(timezone.utc).isoformat(),
                  elapsed_seconds=time.perf_counter() - began)
    path = FOLDER / ('saved_det_gap_' + result['mode'] + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'receipt': bind(path), 'checks': result['checks'],
                      'model_count': result.get('model_count'), 'sampled_map_hashes_validated': result.get('sampled_map_hashes_validated'),
                      'elapsed_seconds': result['elapsed_seconds'], 'error': result.get('error')}, indent=2), flush=True)
    raise SystemExit(0 if result['status'] == 'passed_saved_mean_diagnostic' else 1)


if __name__ == '__main__':
    main()

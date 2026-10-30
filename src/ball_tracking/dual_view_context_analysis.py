"""CPU-only fixed-protocol dual-view analysis; no model loading or policy adoption.

Original Q/J choices, labels, missing slots and source roles are immutable.  New
scores are joined by canonical identity and fit, never by positional coincidence.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path

from . import candidate_acceptance_evaluation as evaluation

STUDY = Path('data/outputs/ball_tracking/dual_view_context_v0_1')
DESIGN = Path('data/outputs/ball_tracking/dual_view_context_design_v0_1/population_review')
ORIGINAL = Path('data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/analysis')
BKN = Path('data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/analysis')
QROOT = Path('data/outputs/ball_tracking/candidate_quality_pilot_v0_1')
PROPOSAL = Path('configs/ball_tracking/proposals/dual_view_context_v0_1.json')
ARMS = ('Q', 'LL', 'LC', 'J')
NEW_ARMS = ('LL', 'LC')
PROTECTED = ('protected_policy_row_keys', 'protected_weak_candidate_row_keys',
             'protected_HOU_stress_query_row_keys')
EXTRA_SLICES = ('native_outcome', 'local_padding', 'context_padding', 'boundary_state',
                'known_negative_reference_geometry', 'treatment_score_status', 'historical_role')
CALL_BUDGETS = {'local_capture': (2776, 88742), 'training': (19740, 630864),
                'scoring': (5554, 177484), 'local_parity': (4, 128), 'auxiliary_parity': (8, 256)}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()] if Path(path).suffix == '.jsonl' else json.load(stream)


def binding(root, path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=path.relative_to(Path(root).resolve()).as_posix(), bytes=path.stat().st_size, sha256=digest)


def verify(root, item):
    path = (Path(root) / item['path']).resolve()
    require(path.is_relative_to(Path(root).resolve()), 'Binding escapes project')
    actual = binding(root, path)
    require(all(actual[k] == item[k] for k in ('bytes', 'sha256')), 'Changed input: ' + item['path'])
    return path


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def write_rows(path, rows):
    count = 0
    with Path(path).open('x', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n')
            count += 1
    return count


def accepted(row, arm):
    value = evaluation.score(row, arm)
    return value is not None and value > 0


def canonical(row):
    if row.get('cohort') == 'BKN_diagnostic':
        return 'b:' + row['candidate_id']
    return ('e:' + row['query_id']) if row.get('query_id') else ('p:' + row['candidate_id'])


def unique(rows, key, description):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), 'Duplicate ' + description)
    return result


def expected_groups(root, proposal, registry, package):
    """Authoritative memberships, including all outer training-health rows."""
    groups, captures, weights = {}, {}, {}
    package_ids = [r['candidate_id'] for r in package]
    require(package_ids == registry['original_package_ids'], 'Original package ordering changed')
    for fit in proposal['training']['fits']:
        name = fit['name']
        weights[name] = read(verify(root, fit['weights']))
        train = {'p:' + r['candidate_id'] for r in weights[name]}
        require(len(train) == fit['fit_candidates'], 'Training membership changed')
        held = {'p:' + r['candidate_id'] for r in package
                if name == 'all_nba' or r['game_id'] in fit['held_out_game_ids']}
        group = 'package_all' if name == 'all_nba' else 'package_held'
        groups[(name, group)] = held
        if name != 'all_nba':
            groups[(name, 'training_health')] = train
        captures[(name, 'package')] = train | held
    groups[('all_nba', 'external')] = {'e:' + k for k in registry['allowed_external_query_ids']}
    groups[('all_nba', 'BKN')] = {'b:' + k for k in registry['BKN_candidate_ids']}
    captures[('all_nba', 'external')] = groups[('all_nba', 'external')]
    captures[('all_nba', 'BKN')] = groups[('all_nba', 'BKN')]
    require(sum(map(len, groups.values())) == 88742, 'Final per-arm inventory differs')
    require(sum(map(len, captures.values())) == 88742, 'Capture inventory differs')
    return groups, captures, weights


def validate_score_segment(rows, expected, fit, arm=None, group=None):
    require(len(rows) == len(expected), 'Score segment count differs')
    index = unique(rows, 'row_key', 'score identity')
    require(set(index) == set(expected), 'Score identities differ: ' + str((fit, arm, group)))
    if any('feature_index' in row for row in rows):
        require([row.get('feature_index') for row in rows] == list(range(len(rows))),
                'Saved feature-row indices do not align with score rows')
    for row in rows:
        require(row.get('fit') == fit, 'Wrong score fold')
        if arm is not None:
            require(row.get('arm') == arm, 'Wrong score arm')
        if group is not None:
            require(row.get('group') == group, 'Wrong score group')
        value = row.get('quality_logit', row.get('logit'))
        require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
                'Nonfinite or absent score')
        row['quality_logit'] = float(value)
    return {key: row['quality_logit'] for key, row in index.items()}


def load_scores(root, completion, groups, captures):
    require(completion['status'] == 'completed_exact_frozen_workload', 'Neural execution not complete')
    counters = {key: value for kind, (calls, presentations) in CALL_BUDGETS.items()
                for key, value in ((kind+'_forwards_attempted', calls), (kind+'_forwards_returned', calls),
                                   (kind+'_candidate_presentations', presentations))}
    counters['optimizer_updates'] = 19740
    require(completion['counters'] == counters, 'Completed physical workload differs')
    verify(root, completion['execution_freeze'])
    verify(root, completion['prepared'])
    fits = completion['fits']
    require(len(fits) == 8 and {(r['fit'], r['arm']) for r in fits} ==
            {(fit, arm) for fit, _ in groups for arm in NEW_ARMS}, 'Eight fit/arm inventory differs')
    steps = {'leave_chi_out':2244, 'leave_den_out':2238, 'leave_sac_out':2100, 'all_nba':3288}
    for fit in fits:
        require(fit['steps'] == steps[fit['fit']] and fit['frozen_tensors_unchanged'], 'Fit updates/frozen status differs')
    records = completion.get('all_scores') or [r for f in fits for r in f['scores']]
    expected_segments = {(fit, arm, group) for fit, group in groups for arm in NEW_ARMS}
    require(len(records) == len(expected_segments), 'Score segment inventory differs')
    seen, routed, bindings = set(), {}, []
    for record in records:
        key = (record['fit'], record['arm'], record['group'])
        require(key in expected_segments and key not in seen, 'Extra/duplicate score segment')
        seen.add(key)
        fit, arm, group = key
        rows = read(verify(root, record))
        require(all('feature_index' in row for row in rows), 'Missing saved auxiliary-feature row index')
        require(record['rows'] == len(rows), 'Completion score count differs')
        values = validate_score_segment(rows, groups[(fit, group)], fit, arm, group)
        for row_key, value in values.items():
            identity = (fit, arm, row_key)
            require(identity not in routed, 'Duplicate final scoring identity')
            routed[identity] = value
        bindings.append({k: record[k] for k in ('path', 'bytes', 'sha256')})
    capture_records = completion['local_captures']
    require(len(capture_records) == 6, 'Local capture segment inventory differs')
    seen, old_q = set(), {}
    for record in capture_records:
        # Workers may name the package union by its explicit score population.
        group = record['group']
        canonical_group = 'package' if group in ('package', 'package_union', 'package_held', 'package_all') else group
        key = (record['fit'], canonical_group)
        require(key in captures and key not in seen, 'Extra/duplicate capture segment')
        seen.add(key)
        rows = read(verify(root, record))
        require(all('feature_index' in row for row in rows), 'Missing saved local-feature row index')
        require(record['rows'] == len(rows), 'Capture count differs')
        values = validate_score_segment(rows, captures[key], record['fit'], group=group)
        old_q.update({(record['fit'], k): v for k, v in values.items()})
        bindings.append({k: record[k] for k in ('path', 'bytes', 'sha256')})
    require(len(routed) == 177484 and len(old_q) == 88742, 'Final/capture row inventory differs')
    return routed, old_q, bindings


def geometry_slices(row, geometry=None):
    """Geometry is descriptive and never changes an accepted reference label."""
    target = row.get('target_group')
    row['boundary_state'] = ('boundary_unknown_training_mask' if target == 'boundary_unknown' else
                             'other_unknown_training_mask' if target == 'masked_unknown' else
                             'within_recorded_boundary_uncertainty' if row.get('within_recorded_uncertainty_of_match_boundary') else 'not_boundary_unknown')
    row['local_padding'] = ('missing_or_unavailable' if row.get('padding_pixels') is None else
                            'padded' if row['padding_pixels'] > 0 else 'complete')
    center = row.get('center_xy_px')
    video = row.get('source_video') or {}
    width = row.get('width_px', video.get('width_px'))
    height = row.get('height_px', video.get('height_px'))
    row['context_padding'] = 'missing_or_unavailable'
    if center is not None and width is not None and height is not None:
        left, top = math.floor(center[0]) - 96, math.floor(center[1]) - 96
        area = max(0, min(width, left + 192) - max(0, left)) * max(0, min(height, top + 192) - max(0, top))
        row['context192_padding_pixels'] = 192 * 192 - area
        row['context_padding'] = 'padded' if area < 192 * 192 else 'complete'
    row['known_negative_reference_geometry'] = 'not_a_known_distant_negative'
    if geometry:
        row['reference_in_crop_geometry'] = geometry
        if target == 'eligible_distant_miss':
            row['known_negative_reference_geometry'] = ('outside192' if not geometry['in_context192'] else
                'inside192_inside_nominal56' if geometry['in_nominal_effective_local56'] else 'inside192_outside_nominal56')
    return row


def attach_scores(original, routed, omitted, missing, frame_index, geometry):
    result = []
    for old in original:
        row = {**old, 'scores': dict(old['scores']), 'original_Q_J_unchanged': True}
        key = canonical(row)
        row['canonical_row_key'] = key
        query = row.get('query_id')
        status = 'DET_metadata_only_not_scored_by_design' if query in omitted else 'original_missing_selection' if query in missing else 'scored'
        row['treatment_score_status'] = status
        for arm in NEW_ARMS:
            identity = (row['fit'], arm, key)
            if status == 'scored':
                require(identity in routed, 'Missing treatment score: ' + str(identity))
                row['scores'][arm] = routed[identity]
            else:
                require(identity not in routed, 'Forbidden score for missing/DET row')
                row['scores'][arm] = None
        frame = frame_index.get(row.get('frame_key'), {})
        row['native_outcome'] = frame.get('native_outcome')
        result.append(geometry_slices(row, geometry.get(row.get('candidate_id'))))
    return result


def join_policies(original, candidates):
    index = unique(candidates, 'row_key', 'candidate analysis identity')
    result = []
    for old in original:
        require(old['point_chosen_before_acceptance'] and not old['fallback_allowed'], 'Original choice contract changed')
        point = index.get(old['chosen_row_key']) if old.get('chosen_row_key') else None
        require((point is not None) == bool(old.get('chosen_row_key')), 'Original chosen point missing')
        scores = dict(old['scores'])
        if point:
            require(point['frame_key'] == old['frame_key'] and point['evaluation_category'] == old['evaluation_category'],
                    'Fixed choice label/frame changed')
            require(all(scores.get(a) == point['scores'].get(a) for a in ('Q', 'J')), 'Fixed choice Q/J changed')
        scores.update({arm: point['scores'][arm] if point else None for arm in NEW_ARMS})
        row = {**old, 'scores': scores, 'treatment_score_status': point['treatment_score_status'] if point else 'original_missing_choice'}
        for name in EXTRA_SLICES:
            if name not in row:
                row[name] = point.get(name) if point else None
        result.append(row)
    return result


def bkn_normalized(saved_frames, saved_candidates, saved_policies):
    frames = [{**r, 'context': 'BKN_diagnostic', 'fit': 'all_nba', 'cohort': 'BKN_diagnostic',
               'eligible': r['reference_category'] == 'eligible', 'native_outcome': r['native_success_group']}
              for r in saved_frames]
    fi = {r['frame_key']: r for r in frames}
    candidates = []
    for old in saved_candidates:
        frame = fi[old['frame_key']]
        candidates.append({**old, 'row_key': 'BKN_diagnostic|' + old['candidate_id'], 'query_id': None,
            'cohort': 'BKN_diagnostic', 'context': 'BKN_diagnostic', 'fit': 'all_nba',
            'visibility': frame['visibility'], 'difficulty_tags': frame['annotation'].get('difficulty_tags', []),
            'target_group': 'BKN_diagnostic_no_fitting_target'})
    ci = {r['candidate_id']: r for r in candidates}
    policies = []
    for old in saved_policies:
        frame = fi[old['frame_key']]
        point = ci.get(old.get('candidate_id'))
        policies.append({**old, 'context': 'BKN_diagnostic', 'fit': 'all_nba', 'cohort': 'fixed_policy',
            'block_id': frame['block_id'], 'game_id': frame['game_id'], 'eligible': frame['eligible'],
            'native_outcome': frame['native_outcome'], 'chosen_row_key': point['row_key'] if point else None,
            'target_group': 'BKN_diagnostic_no_fitting_target'})
    return frames, candidates, policies


def paired(rows):
    for row in rows:
        state = {arm: accepted(row, arm) if evaluation.score(row, arm) is not None else None for arm in ARMS}
        transitions = {arm: 'not_comparable_by_design' if row.get('treatment_score_status') == 'DET_metadata_only_not_scored_by_design' else
                       'not_comparable_missing_score' if state['LC'] is None or state[arm] is None else
                       ('agreement_accept' if state['LC'] else 'agreement_reject') if state['LC'] == state[arm]
                       else 'new_accept' if state['LC'] else 'new_reject' for arm in ('LL', 'Q', 'J')}
        yield {k: row.get(k) for k in ('row_key', 'canonical_row_key', 'frame_key', 'context', 'fit', 'game_id', 'block_id',
                'cohort', 'policy', 'chosen_row_key', 'candidate_id', 'query_id', 'evaluation_category', 'target_group',
                'native_or_weak', 'native_outcome', 'treatment_score_status')} | {
                    'scores': row['scores'], 'accepted_at_zero': state, 'LC_vs': transitions,
                    'score_availability': {arm: evaluation.score(row, arm) is not None for arm in ARMS}}


def grouped(rows, policy=False, detailed=True):
    groups = evaluation.grouped(rows, policy, detailed)
    if detailed:
        for row in rows:
            for scope in evaluation.scopes(row, policy):
                for family in EXTRA_SLICES:
                    key = evaluation.token({**scope, 'family': family, 'value': row.get(family)})
                    groups[key].append(row)
    return groups


def tables(rows, policy=False, curves=False):
    # DET is transported as metadata only, not evaluated as a new rejection.
    rows = [r for r in rows if r.get('treatment_score_status') != 'DET_metadata_only_not_scored_by_design']
    for key, members in sorted(grouped(rows, policy, detailed=not curves).items()):
        for arm in ARMS:
            yield {**json.loads(key), 'arm': arm,
                   'unit': 'fixed_policy_context_frame' if policy else 'candidate_context_slot',
                   **(evaluation.curve(members, arm) if curves else evaluation.aggregate(members, arm)),
                   'overlapping_views_not_additive': True}


def metric_checks(rows, comparator, context, scope):
    groups = defaultdict(list)
    for row in rows:
        if row['context'] == context:
            groups[(row['game_id'], row.get('block_id') if scope == 'block' else None, row['policy'])].append(row)
    result = []
    for (game, block, policy), members in sorted(groups.items()):
        counts = {arm: evaluation.aggregate(members, arm)['counts'] for arm in (comparator, 'LC')}
        for metric, larger in (('correct_kept', True), ('wrong_eligible_kept', False), ('hidden_emission_frames', False)):
            before, after = counts[comparator][metric], counts['LC'][metric]
            result.append(dict(context=context, game_id=game, block_id=block, policy=policy, comparator=comparator,
                metric=metric, baseline=before, LC=after, passed=after >= before if larger else after <= before,
                strict_improvement=after > before if larger else after < before, denominator=len(members)))
    return result


def gate(policies, comparator):
    cells = metric_checks(policies, comparator, 'nba_out_of_fold', 'game')
    losses = [r['row_key'] for r in policies if r['context'] == 'nba_out_of_fold'
              and r['evaluation_category'] == 'eligible_match' and accepted(r, comparator) and not accepted(r, 'LC')]
    return dict(passed=bool(cells) and all(r['passed'] for r in cells) and any(r['strict_improvement'] for r in cells) and not losses,
                comparator=comparator, checks=cells, strict_primary_cells=sum(r['strict_improvement'] for r in cells),
                lost_correct_policy_identities=losses, strict_gain_required=True)


def decisions(policies, candidates, protected):
    primary, component = gate(policies, 'LL'), gate(policies, 'Q')
    ci, pi = {r['row_key']: r for r in candidates}, {r['row_key']: r for r in policies}
    losses, counts = {}, {}
    for name in PROTECTED:
        values = protected[name]
        index = pi if name == 'protected_policy_row_keys' else ci
        require(all(k in index and index[k]['evaluation_category'] == 'eligible_match' and accepted(index[k], 'Q') for k in values),
                'Protected identities not retained exactly: ' + name)
        losses[name] = [k for k in values if not accepted(index[k], 'LC')]
        counts[name] = len(values)
    hou = metric_checks(policies, 'Q', 'HOU_development', 'block')
    new_errors = [r['row_key'] for r in policies if r['context'] == 'HOU_development'
                  and r['evaluation_category'] in ('eligible_miss', 'certain_hidden')
                  and accepted(r, 'LC') and not accepted(r, 'Q')]
    component.update(protected_identity_counts=counts, exact_protected_losses=losses,
        protected_sets_overlap=True, HOU_episode_policy_checks=hou, HOU_new_error_policy_identities=new_errors)
    component['passed'] = component['passed'] and bool(hou) and all(r['passed'] for r in hou) and not new_errors and not any(losses.values())
    j_groups = defaultdict(list)
    for row in policies:
        j_groups[(row['context'], row['policy'])].append(row)
    j = []
    for (context, policy), members in sorted(j_groups.items()):
        correct_losses = [r['row_key'] for r in members if r['evaluation_category'] == 'eligible_match' and accepted(r, 'J') and not accepted(r, 'LC')]
        counts_by_arm = {a: evaluation.aggregate(members, a) for a in ('J', 'LC')}
        j.append(dict(context=context, policy=policy, denominator=len(members), at_zero=counts_by_arm,
            newly_correct_J_rejected=[r['row_key'] for r in members if r['evaluation_category'] == 'eligible_match' and accepted(r, 'LC') and not accepted(r, 'J')],
            rejected_errors_J_kept=[r['row_key'] for r in members if r['evaluation_category'] in ('eligible_miss', 'certain_hidden') and accepted(r, 'J') and not accepted(r, 'LC')],
            lost_J_correct=correct_losses,
            new_errors_J_rejected=[r['row_key'] for r in members if r['evaluation_category'] in ('eligible_miss', 'certain_hidden') and accepted(r, 'LC') and not accepted(r, 'J')]))
    error_increases = [c for context in sorted({r['context'] for r in policies})
                       for c in metric_checks(policies, 'J', context, 'game') if c['metric'] != 'correct_kept' and not c['passed']]
    return dict(primary_context_gate=primary, component_Q_gate=component, saved_J_comparison=j,
        J_drop_in_readiness_precluded=any(r['lost_J_correct'] for r in j) or bool(error_increases),
        J_error_increase_cells=error_increases, selected_threshold=None, selected_checkpoint_epoch=6,
        adopted=False, tracker_complete=False, achieved_95_percent=False,
        fixed_Q_top_raw_correct_ceiling=dict(correct=2542, eligible=2811, fraction=2542/2811),
        saved_J_quality_top=dict(correct=2541, eligible=2811, fraction=2541/2811),
        interpretation='Context gate and Q component gate evaluated independently at fixed zero; no threshold rescue or automatic integration.',
        limits=['Held source is held from these scorers, not the detector training.',
                'HOU and BKN were exposed; BKN is diagnostic only and HOU is a preservation veto.',
                'Field of view and scale/resampling change jointly.',
                'No independence assumption for adjacent frames, overlapping candidates or three folds.',
                'Healthy training with poor held results does not uniquely identify coverage, representation or optimization.'])


def ranking(frames, candidates):
    pools = defaultdict(list)
    for row in candidates:
        if row['cohort'] in ('package', 'HOU_main', 'BKN_diagnostic'):
            pools[row['frame_key']].append(row)
    for frame in frames:
        pool = pools[frame['frame_key']]
        matches = [r for r in pool if r['evaluation_category'] == 'eligible_match']
        result = {k: frame.get(k) for k in ('frame_key', 'context', 'fit', 'game_id', 'block_id', 'source_frame_index', 'eligible', 'reference_category', 'native_outcome')}
        result.update(pool_candidates=len(pool), matching_candidates=len(matches), empty_pool=not pool,
                      diagnostic_only=True, new_emitted_policy=False, arms={})
        for arm in ARMS:
            observed = [r for r in pool if evaluation.score(r, arm) is not None]
            m = [r for r in observed if r['evaluation_category'] == 'eligible_match']
            wrong = [r for r in observed if r['evaluation_category'] == 'eligible_miss']
            best = max((r['scores'][arm] for r in m), default=None)
            rival = max((r['scores'][arm] for r in wrong), default=None)
            top_value = max((r['scores'][arm] for r in observed), default=None)
            tied = sorted(r['row_key'] for r in observed if r['scores'][arm] == top_value)
            state = ('not_eligible' if not frame.get('eligible') else 'empty_pool' if not pool else
                     'no_matching_candidate' if not matches else 'matching_score_unavailable' if best is None else
                     'strict_match_first' if rival is None or best > rival else 'match_tied_first' if best == rival else 'match_not_first')
            result['arms'][arm] = dict(state=state, observed_candidates=len(observed), missing_scores=len(pool)-len(observed),
                maximum_match=best, maximum_wrong=rival, margin=None if best is None or rival is None else best-rival,
                best_match_rank_min=None if best is None else 1+sum(r['scores'][arm] > best for r in observed),
                best_match_rank_max=None if best is None else sum(r['scores'][arm] >= best for r in observed),
                top_tied_row_keys=tied, positive_matching_candidates=sum(accepted(r, arm) for r in m),
                positive_matching_weak_candidates=sum(accepted(r, arm) for r in m if r['native_or_weak'] == 'weak'),
                positive_hidden_candidates=sum(accepted(r, arm) for r in observed if r['evaluation_category'] == 'certain_hidden'))
        result['LC_vs'] = {a: dict(baseline_state=result['arms'][a]['state'], LC_state=result['arms']['LC']['state'],
            gained_strict_match_first=result['arms']['LC']['state'] == 'strict_match_first' and result['arms'][a]['state'] != 'strict_match_first',
            lost_strict_match_first=result['arms']['LC']['state'] != 'strict_match_first' and result['arms'][a]['state'] == 'strict_match_first',
            match_margin_delta=(result['arms']['LC']['margin'] - result['arms'][a]['margin'])
            if result['arms']['LC']['margin'] is not None and result['arms'][a]['margin'] is not None else None) for a in ('LL', 'Q')}
        yield result


def ranking_tables(rows):
    groups = defaultdict(list)
    for row in rows:
        for scope in ('context', 'game', 'block'):
            for native in ('all', row.get('native_outcome')):
                key = (row['context'], scope, row.get('game_id') if scope != 'context' else None,
                       row.get('block_id') if scope == 'block' else None, native)
                groups[key].append(row)
    for (context, scope, game, block, native), members in sorted(groups.items(), key=lambda item: str(item[0])):
        yield dict(context=context, scope=scope, game_id=game, block_id=block, native_outcome=native,
            frames=len(members), eligible_frames=sum(bool(r['eligible']) for r in members),
            empty_frames=sum(r['empty_pool'] for r in members), eligible_frames_with_match=sum(bool(r['eligible']) and r['matching_candidates'] > 0 for r in members),
            arms={a: dict(states=dict(Counter(r['arms'][a]['state'] for r in members)),
                positive_match_frames=sum(r['arms'][a]['positive_matching_candidates'] > 0 for r in members),
                positive_weak_match_frames=sum(r['arms'][a]['positive_matching_weak_candidates'] > 0 for r in members),
                hidden_emission_frames=sum(r['arms'][a]['positive_hidden_candidates'] > 0 for r in members)) for a in ARMS},
            LC_vs={a: dict(gained_strict_match_first=sum(r['LC_vs'][a]['gained_strict_match_first'] for r in members),
                          lost_strict_match_first=sum(r['LC_vs'][a]['lost_strict_match_first'] for r in members)) for a in ('LL', 'Q')},
            overlapping_views_not_additive=True, new_emitted_policy=False)


def bce(logit, target):
    return max(logit, 0.0) - logit * target + math.log1p(math.exp(-abs(logit)))


def captured_Q_parity(candidates, captured):
    """Independent CPU comparison against saved controls, never substitution."""
    errors = []
    seen = set()
    for row in candidates:
        if row.get('treatment_score_status') != 'scored':
            continue
        key = (row['fit'], canonical(row))
        require(key not in seen, 'Duplicate saved-control comparison identity')
        seen.add(key)
        old, new = row['scores']['Q'], captured[key]
        require(math.isclose(old, new, rel_tol=1e-6, abs_tol=1e-5) and (old>0)==(new>0) and (old==0)==(new==0),
                'Captured Q disagrees with immutable saved control: '+str(key))
        errors.append(abs(old-new))
    return dict(saved_control_comparisons=len(errors), maximum_absolute_difference=max(errors, default=0.0),
                absolute_tolerance=1e-5, relative_tolerance=1e-6, identical_zero_signs=True,
                saved_Q_controls_replaced=False)


def training_health(weights, package, routed, captured_q):
    index = {r['candidate_id']: r for r in package}
    details, summaries = [], []
    for fit, fit_weights in weights.items():
        for weight in fit_weights:
            row = index[weight['candidate_id']]
            target = row['target']
            require(target in (0, 1), 'Unknown target in training health')
            key = 'p:' + row['candidate_id']
            scores = {a: routed[(fit, a, key)] for a in NEW_ARMS}
            scores['Q_captured'] = captured_q[(fit, key)]
            details.append(dict(fit=fit, row_key=key, target=target, target_group=row['target_group'],
                game_id=row['game_id'], block_id=row['block_id'], native_or_weak=row['native_or_weak'],
                objective_weight=weight['objective_weight'], training_multiplier=weight['training_multiplier'],
                scores=scores, BCE={a: bce(s, target) for a, s in scores.items()},
                signed_margin={a: s * (2*target-1) for a, s in scores.items()}))
        members = [r for r in details if r['fit'] == fit]
        require(math.isclose(sum(r['objective_weight'] for r in members), 1.0, abs_tol=1e-10), 'Objective mass changed')
        for target_group in ('all', 'positive', 'eligible_distant_miss', 'certain_hidden'):
            subset = members if target_group == 'all' else [r for r in members if r['target_group'] == target_group]
            for arm in ('Q_captured', *NEW_ARMS):
                margins = sorted(r['signed_margin'][arm] for r in subset)
                summaries.append(dict(fit=fit, target_group=target_group, arm=arm, rows=len(subset),
                    final_weighted_BCE=sum(r['BCE'][arm] * r['training_multiplier'] for r in subset)/len(members),
                    contribution_denominator_all_fit_rows=len(members), unweighted_BCE=sum(r['BCE'][arm] for r in subset)/len(subset),
                    target_correct_strict_sign=sum(r['signed_margin'][arm] > 0 for r in subset),
                    exact_zero_logits=sum(r['scores'][arm] == 0 for r in subset),
                    margin_min=margins[0], margin_median=margins[len(margins)//2], margin_max=margins[-1],
                    final_epoch=6, used_for_checkpoint_selection=False,
                    Q_control_kind='newly_captured_original_Q_same_fit; saved comparison logits unchanged'))
    return details, summaries


def preserved_cases(protected, candidates, policies):
    ci = {r['row_key']: r for r in candidates}
    result = {}
    for name in ('all21_external_stress_recovery_queries', 'all6_below_001_queries'):
        result[name] = []
        for old in protected[name]:
            row = ci[old['row_key']]
            require(row['scores']['Q'] == old['old_Q'], 'Named recovery old Q changed')
            result[name].append({**old, 'scores': row['scores'], 'accepted_at_zero': {a: accepted(row, a) for a in ARMS},
                                 'treatment_score_status': row['treatment_score_status']})
    result['named_case_groups'] = {}
    for name, group in protected['named_case_groups'].items():
        rows = [ci[k] for k in group['candidate_row_keys']]
        frames = set(group['frame_keys'])
        result['named_case_groups'][name] = {**group,
            'candidate_zero': {a: evaluation.aggregate(rows, a) for a in ARMS},
            'fixed_policy_zero': {p: {a: evaluation.aggregate([r for r in policies if r['frame_key'] in frames and r['policy'] == p], a)
                                    for a in ARMS} for p in ('native', 'quality_top')}, 'candidates': list(paired(rows))}
    result.update(negative_controls_are_inventory_not_invented_positive_veto=True, overlapping_groups_not_additive=True)
    return result


def historical_choices(choices, contrasts, candidates):
    queries = {r['query_id']: r for r in candidates if r.get('query_id')}
    def extend(old):
        point = queries.get(old.get('query_id'))
        require((point['scores']['Q'] if point else None) == old['scores']['Q'], 'Saved historical choice Q changed')
        scores = dict(old['scores'])
        scores.update({a: point['scores'][a] if point else None for a in NEW_ARMS})
        return {**old, 'scores': scores, 'accepted_at_zero': {a: scores.get(a) is not None and scores[a] > 0 for a in ARMS}}
    new_choices = [extend(r) for r in choices]
    new_contrasts = []
    for row in contrasts:
        source, target = extend(row['source']), extend(row['target'])
        deltas = {a: target['scores'].get(a)-source['scores'].get(a)
                  if target['scores'].get(a) is not None and source['scores'].get(a) is not None else None for a in ARMS}
        new_contrasts.append({**row, 'source': source, 'target': target, 'delta_target_minus_source': deltas, 'new_choice_created': False})
    return new_choices, new_contrasts


def analyze(root, completion_path=None, output_dir=None):
    root = Path(root).resolve()
    completion_path = Path(completion_path) if completion_path else root/STUDY/'attempt_001/completed.json'
    if not completion_path.is_absolute(): completion_path = root/completion_path
    out = Path(output_dir) if output_dir else root/STUDY/'analysis'
    if not out.is_absolute(): out = root/out
    require(not out.exists(), 'Analysis output exists; preserve it and use a fresh output directory')
    proposal = read(root/PROPOSAL)
    inputs = [binding(root, completion_path), binding(root, root/PROPOSAL)]
    verify(root, proposal['protocol'])
    for item in proposal['design_evidence']:
        verify(root, item)
    inputs += [proposal['protocol'], *proposal['design_evidence']]
    population = read(root/DESIGN/'population_workload.json')
    old_manifest = read(verify(root, population['protected_identity_manifest']['binding']))
    comparator_inventory = read(root/DESIGN/'saved_J_comparator_inventory.json')
    approved = {r['path']: r for r in population['inputs'] + old_manifest['source_bindings'] +
                comparator_inventory['bindings'] + proposal['design_evidence'] +
                [f['saved_Q_scores'] for f in proposal['training']['fits']]}
    def source(path):
        require(path.as_posix() in approved, 'Source not bound to frozen design: ' + str(path))
        verify(root, approved[path.as_posix()])
        inputs.append(binding(root, root/path))
        return read(root/path)
    registry = source(DESIGN/'score_registry_ids.json')
    protected = source(DESIGN/'existing_protected_identity_sets.json')
    require([len(protected[k]) for k in PROTECTED] == [6207, 547, 745], 'Protected set counts changed')
    geometry = {r['candidate_id']: r for r in source(DESIGN/'reference_in_crop_rows.json')['rows']}
    package = source(QROOT/'preparation/candidates.jsonl')
    groups, captures, weights = expected_groups(root, proposal, registry, package)
    inputs += [f['weights'] for f in proposal['training']['fits']]
    completion = read(completion_path)
    routed, captured_q, score_bindings = load_scores(root, completion, groups, captures)
    inputs.extend(score_bindings)
    original_candidates = source(ORIGINAL/'candidate_scores.jsonl')
    frames = source(ORIGINAL/'frame_registry.jsonl')
    original_policies = source(ORIGINAL/'fixed_policy_rows.jsonl')
    require([len(original_candidates), len(frames), len(original_policies)] == [31430, 4289, 8578], 'Original full inventory changed')
    bframes, bcandidates, bpolicies = bkn_normalized(source(BKN/'frames.jsonl'), source(BKN/'candidates.jsonl'), source(BKN/'policies.jsonl'))
    require([len(bframes), len(bcandidates), len(bpolicies)] == [360, 3480, 720], 'BKN inventory changed')
    frames += bframes
    fi = unique(frames, 'frame_key', 'frame')
    omitted, missing = set(registry['omitted_DET_metadata_ids']), set(registry['missing_external_query_ids'])
    candidates = attach_scores(original_candidates + bcandidates, routed, omitted, missing, fi, geometry)
    policies = join_policies(original_policies + bpolicies, candidates)
    # Insample original-Q and treatment scores are a separate view, never pooled
    # with the outer held source, and saved J is inapplicable to the changed Q fit.
    all_q = {r['candidate_id']: r['quality_logit'] for r in source(QROOT/'attempt_005/all_nba/package_scores.jsonl')}
    insample = []
    for row in candidates:
        if row['context'] == 'nba_out_of_fold':
            copy = {**row, 'context': 'nba_in_sample', 'fit': 'all_nba',
                    'row_key': 'nba_in_sample|' + row['candidate_id'], 'frame_key': 'nba_in_sample|' + row['frame_id'],
                    'scores': {'Q': all_q[row['candidate_id']], 'J': None,
                               **{a: routed[('all_nba', a, canonical(row))] for a in NEW_ARMS}},
                    'J_unavailable_reason': 'saved_J_not_refit_or_substituted_with_allNBA_Q', 'original_Q_J_unchanged': None}
            insample.append(copy)
    candidates += insample
    frames += [{**r, 'context': 'nba_in_sample', 'fit': 'all_nba', 'frame_key': 'nba_in_sample|' + r['frame_id']}
               for r in frames if r['context'] == 'nba_out_of_fold']
    require(len(insample) == 18813 and len(policies) == 9298, 'Separate view inventory changed')
    parity = captured_Q_parity(candidates, captured_q)
    require(parity['saved_control_comparisons'] == 53694, 'Saved Q overlap inventory differs')
    rank = list(ranking(frames, candidates))
    health_rows, health_summary = training_health(weights, package, routed, captured_q)
    decision = decisions(policies, candidates, protected)
    cases = preserved_cases(protected, candidates, policies)
    choices, contrasts = historical_choices(source(ORIGINAL/'source_choices.jsonl'), source(ORIGINAL/'contrast_views.jsonl'), candidates)
    require(len(choices) == len(contrasts) == 6720, 'Historical choice/contrast inventory changed')
    metadata = [r for r in candidates if r['treatment_score_status'] == 'DET_metadata_only_not_scored_by_design']
    absent = [r for r in candidates if r['treatment_score_status'] == 'original_missing_selection']
    require(len(metadata) == 18 and len(absent) == 11, 'Excluded/missing inventories changed')
    summary = dict(schema='dual_view_context_analysis/v0.1', status='completed_CPU_analysis_no_adoption',
        utc=datetime.now(timezone.utc).isoformat(), source_completion=inputs[0],
        candidate_rows=len(candidates), original_candidate_rows=31430, BKN_candidate_rows=3480,
        separate_allNBA_in_sample_rows=len(insample), fixed_policy_rows=len(policies), frame_rows=len(frames),
        final_scores=len(routed), captured_Q_scores=len(captured_q), training_health_rows=len(health_rows),
        independent_captured_Q_parity=parity,
        DET_metadata_only_rows=len(metadata), original_missing_slots=len(absent),
        candidate_context_counts=dict(Counter(r['context'] for r in candidates)),
        frame_context_counts=dict(Counter(r['context'] for r in frames)),
        reference_geometry_known_negative_counts=dict(Counter(r['known_negative_reference_geometry'] for r in candidates if r['context']=='nba_out_of_fold' and r['target_group']=='eligible_distant_miss')),
        original_package_empty_frames=sum(r['empty_pool'] for r in rank if r['context'] in ('nba_out_of_fold', 'nfhs_secondary')),
        fixed_policy_eligible_accuracy=[dict(context=c, policy=p,
            eligible_frames=sum(bool(r.get('eligible')) for r in members),
            at_zero={a:dict(correct_kept=analysis_counts['counts']['correct_kept'],
                           denominator=sum(bool(r.get('eligible')) for r in members),
                           fraction=analysis_counts['counts']['correct_kept']/sum(bool(r.get('eligible')) for r in members)
                           if any(r.get('eligible') for r in members) else None)
                     for a in ARMS for analysis_counts in [evaluation.aggregate(members,a)]})
            for c in sorted({r['context'] for r in policies}) for p in ('native','quality_top')
            for members in [[r for r in policies if r['context']==c and r['policy']==p]]],
        primary_context_gate_passed=decision['primary_context_gate']['passed'], component_Q_gate_passed=decision['component_Q_gate']['passed'],
        original_fixed_policy_counts={c: {p: {a: evaluation.aggregate([r for r in policies if r['context']==c and r['policy']==p], a)
              for a in ARMS} for p in ('native', 'quality_top')} for c in sorted({r['context'] for r in policies})},
        historical_roles={str(role): {a: evaluation.aggregate([r for r in candidates if r['context']=='historical' and r.get('historical_role')==role and r['treatment_score_status']=='scored'], a)
              for a in ARMS} for role in sorted({r.get('historical_role') for r in candidates if r['context']=='historical'}, key=str)},
        threshold_chosen=None, new_policy=False, unknown_reference_labels_preserved=True,
        boundary_note='Unknown training targets remain masked; original fixed10px evaluation categories are unchanged. Boundary rows are excluded from known-negative geometry and training-health populations.',
        views_overlap_and_are_not_additive=True, input_bindings=inputs)
    require(summary['original_package_empty_frames'] == 21, 'Empty package frames lost')
    out.mkdir(parents=True)
    outputs = {}
    for name, rows in [('candidates.jsonl', candidates), ('policies.jsonl', policies), ('frames.jsonl', frames),
                       ('paired_candidates.jsonl', paired(candidates)), ('paired_policies.jsonl', paired(policies)),
                       ('candidate_zero_tables.jsonl', tables(candidates)), ('policy_zero_tables.jsonl', tables(policies, True)),
                       ('candidate_curves.jsonl', tables(candidates, curves=True)), ('policy_curves.jsonl', tables(policies, True, True)),
                       ('full_pool_ranking.jsonl', rank), ('ranking_tables.jsonl', ranking_tables(rank)),
                       ('training_health_rows.jsonl', health_rows), ('training_health_summary.jsonl', health_summary),
                       ('source_choices.jsonl', choices), ('contrast_views.jsonl', contrasts),
                       ('DET_metadata_only.jsonl', metadata), ('missing_original_slots.jsonl', absent)]:
        count = write_rows(out/name, rows)
        outputs[name] = {**binding(root, out/name), 'rows': count}
    for name, data in [('decision.json', decision), ('preserved_cases.json', cases)]:
        write_json(out/name, data)
        outputs[name] = binding(root, out/name)
    summary['outputs'] = outputs
    write_json(out/'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--completion')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    result = analyze(args.root, args.completion, args.output_dir)
    print(json.dumps({k: result[k] for k in ('status', 'candidate_rows', 'fixed_policy_rows', 'final_scores',
                      'primary_context_gate_passed', 'component_Q_gate_passed')}, indent=2))


if __name__ == '__main__':
    main()

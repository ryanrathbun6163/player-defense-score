"""Frozen-policy producer-transfer analysis. Saved scores only; no model imports."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import traceback

from . import candidate_acceptance_evaluation as evaluation

STUDY = Path('data/outputs/ball_tracking/candidate_producer_transfer_v0_1')
DESIGN = Path('data/outputs/ball_tracking/candidate_producer_transfer_design_v0_1')
PROPOSAL = Path('configs/ball_tracking/proposals/candidate_producer_transfer_v0_1.json')
ARMS = ('Q', 'Q_plus', 'J')
PRIMARY_CONTEXTS = ('nba_out_of_fold', 'HOU_development')
COMPLETION_STATUS = 'completed_producer_transfer_experiment_no_adoption'
EXPECTED_COUNTERS = dict(training_forwards_attempted=9870, training_forwards_returned=9870,
                         optimizer_updates=9870, training_candidate_presentations=315432,
                         scoring_forwards_attempted=1014, scoring_forwards_returned=1014,
                         scoring_candidate_presentations=32341, parity_forwards_attempted=4,
                         parity_forwards_returned=4, parity_candidate_presentations=128)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def binding(root, path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=path.resolve().relative_to(Path(root).resolve()).as_posix(),
                bytes=path.stat().st_size, sha256=digest)


def verify(root, item):
    path = (Path(root) / item['path']).resolve()
    require(path.is_relative_to(Path(root).resolve()), 'Binding escapes project')
    require(binding(root, path) == {k: item[k] for k in ('path', 'bytes', 'sha256')},
            'Changed binding: ' + item['path'])
    return path


def read(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()] if Path(path).suffix == '.jsonl' else json.load(stream)


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def write_rows(path, rows):
    count = 0
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
            count += 1
    return count


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def accepted(row, arm):
    value = evaluation.score(row, arm)
    return value is not None and value > 0


def segment_key(row):
    return row['fit'], row['owner'], row['population']


def validate_segment(plan, rows):
    """Exact routing, order, finite observations; missing slots never enter a call."""
    require(len(rows) == plan['scores'] == len(plan['ids']), 'Score segment length differs')
    require([r.get(plan['id_field']) for r in rows] == plan['ids'], 'Score IDs/order differ')
    require(len(set(plan['ids'])) == len(plan['ids']), 'Duplicate declared score IDs')
    for row in rows:
        require(segment_key(row) == segment_key(plan), 'Score source/owner/population differs')
        require(finite(row.get('quality_logit')), 'Nonfinite/missing/malformed observed score')
    return {identifier: row['quality_logit'] for identifier, row in zip(plan['ids'], rows, strict=True)}


def join_candidates(original, routed):
    result = []
    used = set()
    for row in original:
        if row['cohort'] == 'package':
            population = 'original_held_NBA' if row['context'] == 'nba_out_of_fold' else 'NFHS_secondary'
            identifier = row['candidate_id']
        else:
            population = 'original_external_registry'
            identifier = row['query_id']
        key = (row['fit'], 'new_treatment', population, identifier)
        if row['scores']['Q'] is None:
            require(key not in routed, 'Original missing slot acquired a score')
            value = None
        else:
            require(key in routed, 'Observed original candidate score missing')
            value = routed[key]
            require(finite(value), 'Malformed treatment score')
            used.add(key)
        result.append({**row, 'scores': {**row['scores'], 'Q_plus': value},
                       'Q_plus_score_route': dict(fit=row['fit'], owner='new_treatment', population=population, identifier=identifier)})
    expected = {key for key in routed if key[1] == 'new_treatment' and key[2] != 'added_held_challenge'}
    require(used == expected, 'Extra or omitted original score transport')
    require(len({r['row_key'] for r in result}) == len(result), 'Duplicate original row identity')
    return result


def join_policies(original, candidates):
    index = {r['row_key']: r for r in candidates}
    result = []
    for row in original:
        require(row['point_chosen_before_acceptance'] is True and row['fallback_allowed'] is False,
                'Original policy contract changed')
        chosen = row['chosen_row_key']
        if chosen is None:
            require(row['scores']['Q'] is None and row['evaluation_category'] == 'missing_choice', 'Malformed absent fixed choice')
            value = None
        else:
            require(chosen in index, 'Fixed choice missing from original pool')
            point = index[chosen]
            require(point['frame_key'] == row['frame_key'] and point['scores']['Q'] == row['scores']['Q']
                    and point['evaluation_category'] == row['evaluation_category'], 'Original fixed choice changed')
            value = point['scores']['Q_plus']
        result.append({**row, 'scores': {**row['scores'], 'Q_plus': value},
                       'Q_plus_changes_only_acceptance': True, 'treatment_reranking': False})
    return result


def paired(rows, arms=ARMS):
    for row in rows:
        old, new = accepted(row, 'Q'), accepted(row, 'Q_plus')
        delta = None if row['scores']['Q'] is None else row['scores']['Q_plus'] - row['scores']['Q']
        yield {**{k: row.get(k) for k in ('row_key', 'frame_key', 'context', 'fit', 'game_id', 'block_id',
                   'source_frame_index', 'cohort', 'policy', 'chosen_row_key', 'candidate_id', 'query_id',
                   'evaluation_category', 'target_group', 'native_or_weak', 'historical_role')},
               'scores': dict(row['scores']), 'accepted_at_zero': {a: accepted(row, a) for a in arms},
               'Q_plus_vs_Q': ('missing' if row['scores']['Q'] is None else
                              'agreement_accept' if old and new else 'agreement_reject' if not old and not new
                              else 'new_accept' if new else 'new_reject'), 'Q_plus_minus_Q': delta}


def zero_tables(rows, policy=False, arms=ARMS):
    for key, members in sorted(evaluation.grouped(rows, policy).items()):
        for arm in arms:
            yield {**json.loads(key), 'arm': arm, **evaluation.aggregate(members, arm),
                   'unit': 'fixed_policy_context_frame' if policy else 'candidate_context_slot',
                   'overlapping_views_not_additive': True}


def full_curves(rows, policy=False, arms=ARMS):
    for key, members in sorted(evaluation.grouped(rows, policy, detailed=False).items()):
        for arm in arms:
            yield {**json.loads(key), 'arm': arm, **evaluation.curve(members, arm),
                   'unit': 'fixed_policy_context_frame' if policy else 'candidate_context_slot'}


def paired_tables(rows, policy=False):
    for key, members in sorted(evaluation.grouped(rows, policy).items()):
        transitions = Counter()
        for row in members:
            old, new = accepted(row, 'Q'), accepted(row, 'Q_plus')
            state = ('missing' if row['scores']['Q'] is None else 'agreement_accept' if old and new else
                     'agreement_reject' if not old and not new else 'new_accept' if new else 'new_reject')
            transitions[(row['evaluation_category'], state)] += 1
        yield {**json.loads(key), 'denominator':len(members),
               'transitions':[dict(evaluation_category=c, transition=s, rows=n) for (c,s),n in sorted(transitions.items())],
               'all_exact_row_identities_saved_separately':True, 'overlapping_views_not_additive':True}


def protection_sets(policies, candidates):
    return {
        'protected_policy_row_keys': {r['row_key'] for r in policies if r['context'] in PRIMARY_CONTEXTS
                                      and r['evaluation_category'] == 'eligible_match' and accepted(r, 'Q')},
        'protected_weak_candidate_row_keys': {r['row_key'] for r in candidates if r['context'] in PRIMARY_CONTEXTS
                                             and r['native_or_weak'] == 'weak' and r['evaluation_category'] == 'eligible_match' and accepted(r, 'Q')},
        'protected_HOU_stress_query_row_keys': {r['row_key'] for r in candidates if r['cohort'] == 'HOU_stress'
                                              and r['evaluation_category'] == 'eligible_match' and accepted(r, 'Q')},
    }


def decide(policies, candidates, manifest):
    frozen = protection_sets(policies, candidates)
    for key, values in frozen.items():
        require(values == set(manifest[key]) and len(values) == len(manifest[key]), 'Frozen protection set differs: ' + key)
    primary, external, strict = [], [], []
    groups = defaultdict(list)
    for row in policies:
        if row['context'] in PRIMARY_CONTEXTS:
            groups[(row['context'], row['game_id'], row['policy'])].append(row)
    for (context, game, policy), rows in sorted(groups.items()):
        counts = {a: evaluation.aggregate(rows, a)['counts'] for a in ('Q', 'Q_plus')}
        for metric, larger in (('correct_kept', True), ('wrong_eligible_kept', False), ('hidden_candidates', False)):
            old, new = counts['Q'][metric], counts['Q_plus'][metric]
            good = new >= old if larger else new <= old
            better = new > old if larger else new < old
            item = dict(context=context, game_id=game, policy=policy, metric=metric, Q=old, Q_plus=new,
                        passed=good, strict_improvement=better, denominator=len(rows))
            (primary if context == 'nba_out_of_fold' else external).append(item)
            if context == 'nba_out_of_fold' and better:
                strict.append(item)
    require(primary and external, 'Missing primary/external comparison cells')
    indices = {'protected_policy_row_keys': {r['row_key']: r for r in policies},
               'protected_weak_candidate_row_keys': {r['row_key']: r for r in candidates},
               'protected_HOU_stress_query_row_keys': {r['row_key']: r for r in candidates}}
    losses = {key: sorted(k for k in values if not accepted(indices[key][k], 'Q_plus')) for key, values in frozen.items()}
    passed = all(r['passed'] for r in primary + external) and bool(strict) and not any(losses.values())
    return dict(fixed_zero_component_criterion_passed=passed, NBA_checks=primary, HOU_checks=external,
                strict_NBA_improvements=strict, protection_counts={k: len(v) for k, v in frozen.items()},
                exact_protected_losses=losses,
                exact_policy_losses_by_context={c: [k for k in losses['protected_policy_row_keys'] if indices['protected_policy_row_keys'][k]['context'] == c] for c in PRIMARY_CONTEXTS},
                strict_weak_point_veto_is_new_and_stronger_than_selected_policy_retention=True,
                selected_threshold=None, model_adopted=False, tracker_complete=False,
                interpretation='Component promise at fixed zero only' if passed else 'Prespecified fixed-zero component criterion failed; no threshold rescue',
                limits=['Saved J is contextual, not refitted or a pass comparator.', 'Curves and added challenge points are descriptive, not selection criteria.',
                        'HOU is an exposed external veto.', 'No new-scene, whole-pipeline unseen-game or95% claim.'])


def ranking_diagnostics(frames, candidates):
    pools = defaultdict(list)
    for row in candidates:
        if row['cohort'] in ('package', 'HOU_main'):
            pools[row['frame_key']].append(row)
    for frame in frames:
        pool = pools[frame['frame_key']]
        result = {k: frame.get(k) for k in ('frame_key', 'context', 'game_id', 'block_id', 'source_frame_index', 'eligible', 'native_outcome')}
        result.update(original_pool_rows=len(pool), diagnostic_only=True, new_emitted_policy=False)
        result['arms'] = {}
        for arm in ARMS:
            observed = [r for r in pool if evaluation.score(r, arm) is not None]
            matches = [r for r in observed if r['evaluation_category'] == 'eligible_match']
            rivals = [r for r in observed if r['evaluation_category'] != 'eligible_match']
            match = max((r['scores'][arm] for r in matches), default=None)
            rival = max((r['scores'][arm] for r in rivals), default=None)
            ordered = sorted(observed, key=lambda r: (-r['scores'][arm], r['candidate_id'] or r['query_id']))
            top = ordered[0] if ordered else None
            ties = [r['row_key'] for r in ordered if r['scores'][arm] == top['scores'][arm]] if top else []
            rank = ('not_eligible' if not frame.get('eligible') else 'no_matching_candidate' if match is None else
                    'strict_match_first' if rival is None or match > rival else 'match_tied_first' if match == rival else 'match_not_first')
            result['arms'][arm] = dict(state=rank, maximum_match=match, maximum_nonmatch=rival,
                                      margin=None if match is None or rival is None else match-rival,
                                      diagnostic_top_row_key=top['row_key'] if top else None, top_tied_row_keys=ties,
                                      matching_candidate_rows=len(matches), positive_matching_candidates=sum(accepted(r, arm) for r in matches),
                                      weak_positive_matching_candidates=sum(accepted(r, arm) for r in matches if r['native_or_weak']=='weak'))
        yield result


def ranking_tables(rows):
    groups=defaultdict(list)
    for row in rows:
        for scope in ('context','game','block'):
            for native in ('all',row.get('native_outcome')):
                key=(row['context'],scope,row.get('game_id') if scope!='context' else None,
                     row.get('block_id') if scope=='block' else None,native)
                groups[key].append(row)
    for (context,scope,game,block,native),members in sorted(groups.items(),key=lambda item:str(item[0])):
        for arm in ARMS:
            yield dict(context=context,scope=scope,game_id=game,block_id=block,native_outcome=native,
                       arm=arm,denominator=len(members),states=dict(Counter(r['arms'][arm]['state'] for r in members)),
                       any_positive_match_frames=sum(r['arms'][arm]['positive_matching_candidates']>0 for r in members),
                       any_positive_weak_match_frames=sum(r['arms'][arm]['weak_positive_matching_candidates']>0 for r in members),
                       diagnostic_only=True,new_emitted_policy=False,overlapping_views_not_additive=True)


def old_case_transport(choices, contrasts, candidates):
    queries = {r['query_id']: r for r in candidates if r.get('query_id')}
    def value(query_id, old):
        point = queries.get(query_id)
        require((point['scores']['Q'] if point else None) == old, 'Case old Q differs')
        return point['scores']['Q_plus'] if point else None
    new_choices = []
    for row in choices:
        q = value(row.get('query_id'), row['scores']['Q'])
        new_choices.append({**row, 'scores': {**row['scores'], 'Q_plus': q},
                            'accepted_at_zero': {**row['accepted_at_zero'], 'Q_plus': q is not None and q > 0},
                            'new_choice_created': False})
    new_contrasts = []
    for row in contrasts:
        sides = {}
        for side in ('source', 'target'):
            old = row[side]
            q = value(old.get('query_id'), old['scores']['Q'])
            sides[side] = {**old, 'scores': {**old['scores'], 'Q_plus': q},
                           'accepted_at_zero': {**old['accepted_at_zero'], 'Q_plus': q is not None and q > 0}}
        a, b = sides['source']['scores']['Q_plus'], sides['target']['scores']['Q_plus']
        new_contrasts.append({**row, **sides, 'delta_target_minus_source': {**row['delta_target_minus_source'],
                              'Q_plus': b-a if a is not None and b is not None else None}, 'new_choice_created': False})
    return new_choices, new_contrasts


def contrast_tables(rows):
    groups=defaultdict(list)
    for row in rows:
        for tag in ['all']+sorted(set(row.get('tags') or [])):
            groups[(row['contrast'],row.get('role'),tag)].append(row)
    for (contrast,role,tag),members in sorted(groups.items(),key=lambda item:str(item[0])):
        for arm in ARMS:
            transitions=Counter()
            comparable=correct_first=tied=wrong_first=0
            for row in members:
                source,target=row['source'],row['target']
                transitions[(source['original_outcome'],target['original_outcome'],source['accepted_at_zero'][arm],target['accepted_at_zero'][arm])]+=1
                if {source['original_outcome'],target['original_outcome']}=={'matched','wrong'}:
                    a,b=source['scores'][arm],target['scores'][arm]
                    if a is not None and b is not None:
                        comparable+=1
                        delta=(a-b) if source['original_outcome']=='matched' else (b-a)
                        correct_first+=delta>0;tied+=delta==0;wrong_first+=delta<0
            yield dict(contrast=contrast,role=role,tag=tag,arm=arm,denominator=len(members),
                       accepted_pair_states=[dict(source_outcome=s,target_outcome=t,source_accepted=a,target_accepted=b,rows=n)
                                             for (s,t,a,b),n in sorted(transitions.items(),key=lambda item:str(item[0]))],
                       both_observed_correct_wrong_pairs=comparable,correct_score_higher=correct_first,
                       score_tied=tied,wrong_score_higher=wrong_first,overlapping_tags_not_additive=True)


def historical_tables(rows):
    groups=defaultdict(list)
    for row in rows:
        if row['context']=='historical':
            key=(row.get('historical_role'),row.get('historical_source',{}).get('accepted_classification'))
            groups[key].append(row)
    for (role,classification),members in sorted(groups.items(),key=lambda item:str(item[0])):
        yield dict(historical_role=role,accepted_classification=classification,rows=len(members),
                   at_zero={a:evaluation.aggregate(members,a) for a in ARMS},
                   paired_changes=[r for r in paired(members) if r['Q_plus_vs_Q'] in ('new_accept','new_reject')],
                   separate_semantic_diagnostic_not_localization_or_fitting=True)


def case_views(saved, manifest, candidates, policies):
    ci = {r['row_key']: r for r in candidates}
    result = {}
    for name, group in manifest['named_case_groups'].items():
        rows = [ci[k] for k in group['candidate_row_keys']]
        p = [r for r in policies if r['frame_key'] in set(group['frame_keys'])]
        result[name] = {**group, 'candidate_at_zero': {a: evaluation.aggregate(rows, a) for a in ARMS},
                        'fixed_policy_at_zero': {policy: {a: evaluation.aggregate([r for r in p if r['policy']==policy], a) for a in ARMS}
                                                 for policy in ('native', 'quality_top')},
                        'paired_candidate_changes': [r for r in paired(rows) if r['Q_plus_vs_Q'] in ('new_accept','new_reject')]}
    return {**saved, 'producer_transfer_named_case_views': result,
            'all21_external_stress_recovery_queries': [ci[r['row_key']] for r in manifest['all21_external_stress_recovery_queries']],
            'all6_below_001_queries': [ci[r['row_key']] for r in manifest['all6_below_001_queries']],
            'overlapping_views_not_additive': True}


def added_challenge(additions, frames, routed):
    byframe = {r['frame_id']: r for r in frames if r['context']=='nba_out_of_fold'}
    result = []
    for row in additions:
        frame = byframe[row['frame_id']]
        fit = frame['fit']
        keys = [(fit, owner, 'added_held_challenge', row['candidate_id']) for owner in ('saved_Q_control', 'new_treatment')]
        require(all(k in routed for k in keys), 'Missing added source-held challenge score')
        category = {'positive':'eligible_match','eligible_distant_miss':'eligible_miss','certain_hidden':'certain_hidden'}[row['target_group']]
        result.append({**frame, **row, 'row_key':'added_held_challenge|'+row['candidate_id'],
                       'frame_key':frame['frame_key'], 'context':'added_held_challenge', 'cohort':'added_challenge',
                       'fit':fit, 'evaluation_category':category, 'scores':{'Q':routed[keys[0]], 'Q_plus':routed[keys[1]]},
                       'error_selected_diagnostic_only':True, 'inserted_into_inference_pool':False})
    require(len(result)==len({r['candidate_id'] for r in result}), 'Duplicate challenge row')
    return result


def load_inputs(root, completion_path):
    root = Path(root)
    proposal = read(root/PROPOSAL)
    verify(root, proposal['protocol'])
    for item in proposal['input_bindings']:
        verify(root, item)
    manifest = read(verify(root, proposal['evaluation']['manifest']))
    for item in manifest['source_bindings'] + manifest['frozen_registry_bindings']:
        verify(root, item)
    sources = {Path(b['path']).name:b for b in manifest['source_bindings']}
    saved = {name:read(root/sources[name]['path']) for name in ('candidate_scores.jsonl','frame_registry.jsonl',
             'fixed_policy_rows.jsonl','source_choices.jsonl','contrast_views.jsonl','preserved_controls_and_cases.json')}
    require([len(saved[n]) for n in ('candidate_scores.jsonl','frame_registry.jsonl','fixed_policy_rows.jsonl','source_choices.jsonl','contrast_views.jsonl')]
            == [31430,4289,8578,6720,6720], 'Original complete inventories differ')
    require(sum(r['scores']['Q'] is None for r in saved['candidate_scores.jsonl'])==11, 'Original missing inventory differs')
    population = read(verify(root, proposal['population']['manifest']))
    addition_link = population['files']['added_candidates.jsonl']
    additions = read(verify(root, addition_link))
    require(len(additions)==461, 'Finite challenge population differs')
    workload = read(root/DESIGN/'feasibility/workload.json')
    scoring_plan = read(verify(root, workload['scoring_plan']))
    completion = read(completion_path)
    require(completion['status']==COMPLETION_STATUS, 'Neural run not cleanly completed')
    require(completion['counts']==proposal['counts']==workload['counts'], 'Neural declared workload differs')
    require(completion['counters']==EXPECTED_COUNTERS, 'Actual attempted/returned neural counters differ')
    verify(root, completion['execution_freeze'])
    records = completion['scores']
    require(len(records)==len({segment_key(r) for r in records})==len(scoring_plan), 'Extra/duplicate/missing score segment')
    record_index = {segment_key(r):r for r in records}
    require(set(record_index)=={segment_key(p) for p in scoring_plan}, 'Neural routing inventory differs')
    routed = {}
    for plan in scoring_plan:
        record = record_index[segment_key(plan)]
        require(record['rows']==plan['scores'], 'Score binding row count differs')
        raw = read(verify(root, record))
        for identifier, value in validate_segment(plan, raw).items():
            routed[(*segment_key(plan),identifier)] = value
    require(len(routed)==32341, 'Exact observed scoring scope differs')
    return dict(proposal=proposal, manifest=manifest, saved=saved, additions=additions, routed=routed,
                completion=completion, input_bindings=[binding(root, completion_path), binding(root, root/PROPOSAL),
                binding(root, root/DESIGN/'feasibility/workload.json'), proposal['evaluation']['manifest'],
                proposal['population']['manifest'], workload['scoring_plan'], addition_link])


def analyze(root, completion_path=None, output_dir=None):
    root = Path(root).resolve()
    completion_path = Path(completion_path) if completion_path is not None else root/STUDY/'attempt_001/completed.json'
    if not completion_path.is_absolute(): completion_path=root/completion_path
    output_dir = Path(output_dir) if output_dir is not None else root/STUDY/'analysis'
    if not output_dir.is_absolute(): output_dir=root/output_dir
    require(output_dir.resolve().is_relative_to((root/STUDY).resolve()), 'Analysis output escapes new study')
    output_dir.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    try:
        write_json(output_dir/'started.json', dict(status='saved_score_analysis_started', at_utc=datetime.now(timezone.utc).isoformat(),
                                                   neural_completion=binding(root, completion_path)))
        inputs = load_inputs(root, completion_path)
        saved, manifest = inputs['saved'], inputs['manifest']
        candidates = join_candidates(saved['candidate_scores.jsonl'], inputs['routed'])
        policies = join_policies(saved['fixed_policy_rows.jsonl'], candidates)
        frames = saved['frame_registry.jsonl']
        choices, contrasts = old_case_transport(saved['source_choices.jsonl'],saved['contrast_views.jsonl'],candidates)
        challenge = added_challenge(inputs['additions'],frames,inputs['routed'])
        decision = decide(policies,candidates,manifest)
        counts, outputs = {}, []
        def rows(name, value):
            counts[name.removesuffix('.jsonl')] = write_rows(output_dir/name,value)
            outputs.append(binding(root,output_dir/name))
        def obj(name,value):
            write_json(output_dir/name,value);outputs.append(binding(root,output_dir/name))
        rows('candidate_scores.jsonl',candidates)
        rows('frame_registry.jsonl',frames)
        rows('fixed_policy_rows.jsonl',policies)
        rows('paired_candidate_rows.jsonl',paired(candidates))
        rows('paired_policy_rows.jsonl',paired(policies))
        rows('paired_candidate_tables.jsonl',paired_tables(candidates))
        rows('paired_policy_tables.jsonl',paired_tables(policies,True))
        rows('candidate_zero_tables.jsonl',zero_tables(candidates))
        rows('policy_zero_tables.jsonl',zero_tables(policies,True))
        rows('candidate_curves.jsonl',full_curves(candidates))
        rows('policy_curves.jsonl',full_curves(policies,True))
        rankings=list(ranking_diagnostics(frames,candidates))
        rows('ranking_diagnostics.jsonl',rankings)
        rows('ranking_tables.jsonl',ranking_tables(rankings))
        rows('source_choices.jsonl',choices)
        rows('contrast_views.jsonl',contrasts)
        rows('contrast_zero_tables.jsonl',contrast_tables(contrasts))
        rows('historical_rows.jsonl',(r for r in candidates if r['context']=='historical'))
        rows('historical_semantic_tables.jsonl',historical_tables(candidates))
        rows('added_challenge_scores.jsonl',challenge)
        rows('added_challenge_paired.jsonl',paired(challenge,('Q','Q_plus')))
        rows('added_challenge_paired_tables.jsonl',paired_tables(challenge))
        rows('added_challenge_zero_tables.jsonl',zero_tables(challenge,arms=('Q','Q_plus')))
        rows('added_challenge_curves.jsonl',full_curves(challenge,arms=('Q','Q_plus')))
        obj('preserved_controls_and_cases.json',case_views(saved['preserved_controls_and_cases.json'],manifest,candidates,policies))
        obj('decision.json',decision)
        pooled=[]
        for context in sorted({r['context'] for r in policies}):
            for policy in ('native','quality_top'):
                for arm in ARMS:
                    own=[r for r in policies if r['context']==context and r['policy']==policy]
                    pooled.append(dict(context=context,policy=policy,arm=arm,**evaluation.aggregate(own,arm)))
        obj('summary.json',dict(counts=counts,at_zero_by_context_and_policy=pooled,
                               fixed_zero_component_criterion_passed=decision['fixed_zero_component_criterion_passed'],
                               exact_protected_loss_counts={k:len(v) for k,v in decision['exact_protected_losses'].items()},
                               missing_scores_each_arm={a:sum(r['scores'][a] is None for r in candidates) for a in ARMS},
                               legacy_logit_and_zero_state_fields_retain_original_Q=True,
                               selected_threshold=None,adoption=False,new_neural_calls=0,new_fits=0,old_experiments_rerun=False))
        # Completion appears only after all required output records were saved and bound.
        completed=dict(status='completed_producer_transfer_saved_score_analysis_no_adoption',
                       at_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,
                       counts=counts,outputs=outputs,input_bindings=inputs['input_bindings'],
                       neural_completion=binding(root,completion_path),execution_freeze=inputs['completion']['execution_freeze'],
                       new_neural_calls=0,new_fits=0,automatic_retry=False,model_adopted=False)
        write_json(output_dir/'completed.json',completed)
        return completed
    except BaseException as exc:
        write_json(output_dir/'failed.json',dict(status='failed_saved_score_analysis_preserved_no_retry',
                                                 error=repr(exc),traceback=traceback.format_exc(),elapsed_seconds=time.monotonic()-start))
        raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--completion',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    print(json.dumps(analyze(args.root,args.completion,args.output),indent=2))


if __name__=='__main__':main()

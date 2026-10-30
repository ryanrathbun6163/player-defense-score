import copy
import math
from pathlib import Path
import unittest

from src.ball_tracking import dual_view_context_analysis as analysis


def point(key, q=1, ll=1, lc=1, category='eligible_match', context='nba_out_of_fold', frame=None):
    return dict(row_key=key, candidate_id=key, query_id=None, frame_key=frame or key+'frame',
        context=context, fit='leave_chi_out' if context=='nba_out_of_fold' else 'all_nba',
        game_id='CHI' if context=='nba_out_of_fold' else 'HOU', block_id='block',
        cohort='package' if context=='nba_out_of_fold' else 'HOU_main',
        native_or_weak='native', evaluation_category=category,
        target_group='positive' if category=='eligible_match' else 'eligible_distant_miss',
        scores={'Q':q, 'LL':ll, 'LC':lc, 'J':q}, treatment_score_status='scored')


def policy(key, **kwargs):
    return {**point(key, **kwargs), 'policy':'native', 'chosen_row_key':'candidate:'+key,
            'point_chosen_before_acceptance':True, 'fallback_allowed':False}


def empty_protection():
    return {key:[] for key in analysis.PROTECTED}


class GatesAndTransport(unittest.TestCase):
    def test_gain_cannot_hide_lost_correct_identity(self):
        rows = [policy('lost', ll=1, lc=-1), policy('gain1', ll=-1, lc=1), policy('gain2', ll=-1, lc=1)]
        result = analysis.gate(rows, 'LL')
        self.assertTrue(all(c['passed'] for c in result['checks']))
        self.assertEqual(result['strict_primary_cells'], 1)
        self.assertEqual(result['lost_correct_policy_identities'], ['lost'])
        self.assertFalse(result['passed'])

    def test_game_regression_cannot_be_pooled_away(self):
        rows = [policy('a', ll=1, lc=-1), policy('b', ll=-1, lc=1), policy('c', ll=-1, lc=1)]
        rows[1]['game_id'] = rows[2]['game_id'] = 'DEN'
        result = analysis.gate(rows, 'LL')
        self.assertFalse(result['passed'])
        self.assertTrue(any(not c['passed'] and c['game_id']=='CHI' for c in result['checks']))

    def test_equal_arms_do_not_pass_strict_gain_gate(self):
        self.assertFalse(analysis.gate([policy('same')], 'LL')['passed'])

    def test_new_HOU_error_identity_veto_even_equal_error_count(self):
        rows = [policy('gain', q=-1, ll=-1, lc=1),
                policy('old_error', q=1, lc=-1, category='eligible_miss', context='HOU_development'),
                policy('new_error', q=-1, lc=1, category='eligible_miss', context='HOU_development')]
        result = analysis.decisions(rows, [], empty_protection())['component_Q_gate']
        self.assertTrue(all(c['passed'] for c in result['HOU_episode_policy_checks']))
        self.assertEqual(result['HOU_new_error_policy_identities'], ['new_error'])
        self.assertFalse(result['passed'])

    def test_HOU_episode_regression_cannot_be_pooled_away(self):
        rows = [policy('gain', q=-1, lc=1), policy('hou_loss', q=1, lc=-1, context='HOU_development'),
                policy('hou_gain', q=-1, lc=1, context='HOU_development')]
        rows[-1]['block_id'] = 'different_episode'
        result = analysis.decisions(rows, [], empty_protection())['component_Q_gate']
        self.assertFalse(result['passed'])
        self.assertTrue(any(not c['passed'] for c in result['HOU_episode_policy_checks']))

    def test_policy_choice_never_reranked(self):
        chosen = point('original', q=2, lc=-2)
        rival = point('rival', q=1, lc=100, frame=chosen['frame_key'])
        old = {**policy('fixed'), 'chosen_row_key':chosen['row_key'], 'scores':{'Q':2, 'J':2},
               'frame_key':chosen['frame_key'], 'policy':'quality_top'}
        result = analysis.join_policies([old], [chosen, rival])[0]
        self.assertEqual(result['chosen_row_key'], 'original')
        self.assertEqual(result['scores']['LC'], -2)
        self.assertFalse(result['fallback_allowed'])

    def test_unknowns_do_not_become_errors_and_hidden_unit_is_frames(self):
        rows = [point('hidden1', category='certain_hidden', frame='same'),
                point('hidden2', category='certain_hidden', frame='same'),
                point('unknown', category='masked_unknown')]
        counts = analysis.evaluation.aggregate(rows, 'LC')['counts']
        self.assertEqual(counts['hidden_candidates'], 2)
        self.assertEqual(counts['hidden_emission_frames'], 1)
        self.assertEqual(counts['wrong_eligible_kept'], 0)
        self.assertEqual(counts['unknown_kept'], 1)
        frames = [dict(frame_key='same', eligible=False, context='nba_out_of_fold', reference_category='hidden'),
                  dict(frame_key='unknownframe', eligible=False, context='nba_out_of_fold', reference_category='masked')]
        rank = list(analysis.ranking(frames, rows))
        summaries = list(analysis.ranking_tables(rank))
        self.assertTrue(all(r['eligible_frames']==0 for r in summaries))
        self.assertTrue(all(r['arms']['LC']['states']=={'not_eligible':len(rank)} for r in summaries if r['scope']=='context' and r['native_outcome']=='all'))

    def test_full_pool_ties_empty_and_missing_match(self):
        rows = [point('match', lc=3, frame='f'), point('wrong', lc=3, category='eligible_miss', frame='f')]
        frames = [dict(frame_key='f', eligible=True), dict(frame_key='empty', eligible=True)]
        rank = list(analysis.ranking(frames, rows))
        self.assertEqual(rank[0]['arms']['LC']['state'], 'match_tied_first')
        self.assertEqual(rank[0]['arms']['LC']['best_match_rank_min'], 1)
        self.assertEqual(rank[0]['arms']['LC']['best_match_rank_max'], 2)
        self.assertEqual(rank[0]['arms']['LC']['top_tied_row_keys'], ['match','wrong'])
        self.assertEqual(rank[1]['arms']['LC']['state'], 'empty_pool')

    def test_zero_and_tie_breakpoint_strictness(self):
        rows = [point('zero', lc=0), point('tie1', lc=1), point('tie2', lc=1)]
        self.assertFalse(analysis.accepted(rows[0], 'LC'))
        curve = analysis.evaluation.curve(rows, 'LC')
        at_one = next(p for p in curve['points'] if p.get('threshold')==1)
        self.assertEqual(at_one['tied_candidates'], 2)
        self.assertEqual(at_one['counts'][0], 0)
        at_zero = next(p for p in curve['points'] if p.get('threshold')==0)
        self.assertEqual(at_zero['counts'][0], 2)
        self.assertIsNone(curve['threshold_chosen'])

    def test_score_segments_reject_fold_mismatch_duplicates_nonfinite(self):
        good = [dict(row_key='p:a', quality_logit=1, fit='leave_chi_out', arm='LC', group='package_held')]
        self.assertEqual(analysis.validate_score_segment(good, {'p:a'}, 'leave_chi_out', 'LC', 'package_held'), {'p:a':1})
        for field, value in [('fit','all_nba'), ('arm','LL'), ('group','training_health'), ('quality_logit',float('nan'))]:
            bad = copy.deepcopy(good); bad[0][field]=value
            with self.assertRaises(ValueError):
                analysis.validate_score_segment(bad, {'p:a'}, 'leave_chi_out', 'LC', 'package_held')
        with self.assertRaises(ValueError):
            analysis.validate_score_segment(good*2, {'p:a','p:b'}, 'leave_chi_out', 'LC', 'package_held')
        bad = copy.deepcopy(good); bad[0]['feature_index']=1
        with self.assertRaises(ValueError):
            analysis.validate_score_segment(bad, {'p:a'}, 'leave_chi_out', 'LC', 'package_held')

    def test_captured_control_tolerance_never_allows_sign_change(self):
        row = point('saved',q=1e-8)
        with self.assertRaises(ValueError):
            analysis.captured_Q_parity([row],{('leave_chi_out','p:saved'):-1e-8})
        result=analysis.captured_Q_parity([row],{('leave_chi_out','p:saved'):1e-8})
        self.assertEqual(result['maximum_absolute_difference'],0)
        self.assertFalse(result['saved_Q_controls_replaced'])

    def test_DET_metadata_and_missing_are_not_new_rejections(self):
        rows = [dict(point('det'), treatment_score_status='DET_metadata_only_not_scored_by_design', scores={'Q':1,'J':1,'LL':None,'LC':None}),
                dict(point('missing'), treatment_score_status='original_missing_selection', scores={'Q':None,'J':None,'LL':None,'LC':None})]
        paired = list(analysis.paired(rows))
        self.assertEqual(paired[0]['LC_vs']['Q'], 'not_comparable_by_design')
        self.assertEqual(paired[1]['LC_vs']['Q'], 'not_comparable_missing_score')
        self.assertIsNone(paired[0]['accepted_at_zero']['LC'])
        tables = list(analysis.tables(rows))
        self.assertTrue(all(t['denominator']==1 for t in tables))

    def test_boundary_unknown_not_known_negative_geometry(self):
        row = dict(point('boundary', category='eligible_miss'), target_group='boundary_unknown',
                   center_xy_px=[3.5,4.1], width_px=1280, height_px=720, padding_pixels=10)
        geometry = dict(in_context192=True, in_nominal_effective_local56=True)
        result = analysis.geometry_slices(row, geometry)
        self.assertEqual(result['known_negative_reference_geometry'], 'not_a_known_distant_negative')
        self.assertEqual(result['evaluation_category'], 'eligible_miss')
        self.assertEqual(result['boundary_state'], 'boundary_unknown_training_mask')
        self.assertEqual(result['context_padding'], 'padded')

    def test_final_weighted_BCE_uses_original_multiplier(self):
        package = [dict(candidate_id='a', target=1, target_group='positive', game_id='CHI', block_id='b', native_or_weak='native'),
                   dict(candidate_id='b', target=0, target_group='eligible_distant_miss', game_id='CHI', block_id='b', native_or_weak='weak'),
                   dict(candidate_id='c', target=0, target_group='certain_hidden', game_id='CHI', block_id='b', native_or_weak='weak')]
        weights = {'fit':[dict(candidate_id=k, objective_weight=w, training_multiplier=3*w) for k,w in [('a',.5),('b',.25),('c',.25)]]}
        routed = {('fit',a,'p:'+k):v for a in ('LL','LC') for k,v in [('a',2),('b',-3),('c',-4)]}
        captured = {('fit','p:'+k):0 for k in 'abc'}
        rows, summary = analysis.training_health(weights, package, routed, captured)
        total = next(s for s in summary if s['arm']=='LC' and s['target_group']=='all')
        self.assertAlmostEqual(total['final_weighted_BCE'], .5*analysis.bce(2,1)+.25*analysis.bce(-3,0)+.25*analysis.bce(-4,0))
        old = next(s for s in summary if s['arm']=='Q_captured' and s['target_group']=='all')
        self.assertAlmostEqual(old['final_weighted_BCE'], math.log(2))
        self.assertFalse(total['used_for_checkpoint_selection'])


class ActualSavedPopulationTransport(unittest.TestCase):
    """Uses actual saved records, never reruns inference or fabricates results.

    LL/LC=Q below is an explicitly synthetic identity-transport fixture only.
    It cannot constitute evidence for either experimental arm.
    """
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        if not (cls.root/analysis.ORIGINAL/'candidate_scores.jsonl').exists():
            raise unittest.SkipTest('Saved scientific artifacts unavailable')
        r = cls.root
        cls.original = analysis.read(r/analysis.ORIGINAL/'candidate_scores.jsonl')
        cls.frames = analysis.read(r/analysis.ORIGINAL/'frame_registry.jsonl')
        policies = analysis.read(r/analysis.ORIGINAL/'fixed_policy_rows.jsonl')
        bframes, bcandidates, bpolicies = analysis.bkn_normalized(
            analysis.read(r/analysis.BKN/'frames.jsonl'), analysis.read(r/analysis.BKN/'candidates.jsonl'), analysis.read(r/analysis.BKN/'policies.jsonl'))
        cls.frames += bframes
        cls.registry = analysis.read(r/analysis.DESIGN/'score_registry_ids.json')
        cls.protected = analysis.read(r/analysis.DESIGN/'existing_protected_identity_sets.json')
        omitted = set(cls.registry['omitted_DET_metadata_ids'])
        missing = set(cls.registry['missing_external_query_ids'])
        routed = {(row['fit'],arm,analysis.canonical(row)):row['scores']['Q'] for row in cls.original+bcandidates
                  if row['scores']['Q'] is not None and row.get('query_id') not in omitted for arm in ('LL','LC')}
        geometry = {r['candidate_id']:r for r in analysis.read(r/analysis.DESIGN/'reference_in_crop_rows.json')['rows']}
        cls.candidates = analysis.attach_scores(cls.original+bcandidates, routed, omitted, missing,
                                               {r['frame_key']:r for r in cls.frames}, geometry)
        cls.policies = analysis.join_policies(policies+bpolicies, cls.candidates)

    def test_every_original_choice_and_Q_J_score_preserved(self):
        self.assertEqual(len(self.candidates),34910)
        self.assertEqual(len(self.policies),9298)
        decision = analysis.decisions(self.policies, self.candidates, self.protected)
        self.assertFalse(decision['primary_context_gate']['passed'])
        self.assertFalse(decision['component_Q_gate']['passed'])
        self.assertEqual(decision['component_Q_gate']['protected_identity_counts'], dict(zip(analysis.PROTECTED,[6207,547,745])))
        self.assertFalse(any(decision['component_Q_gate']['exact_protected_losses'].values()))
        self.assertEqual(decision['component_Q_gate']['HOU_new_error_policy_identities'], [])
        self.assertEqual(sum(r['treatment_score_status']=='DET_metadata_only_not_scored_by_design' for r in self.candidates),18)
        self.assertEqual(sum(r['treatment_score_status']=='original_missing_selection' for r in self.candidates),11)
        native = [r for r in self.policies if r['context']=='nba_out_of_fold' and r['policy']=='native']
        top = [r for r in self.policies if r['context']=='nba_out_of_fold' and r['policy']=='quality_top']
        self.assertEqual(analysis.evaluation.aggregate(native,'Q')['counts']['correct_kept'],2309)
        self.assertEqual(analysis.evaluation.aggregate(top,'J')['counts']['correct_kept'],2541)

    def test_full_pools_include_empty_HOU_BKN_and_named_recoveries(self):
        ranks = list(analysis.ranking(self.frames,self.candidates))
        self.assertEqual(len(ranks),4649)
        self.assertEqual(sum(r['context']=='HOU_development' for r in ranks),960)
        self.assertEqual(sum(r['context']=='BKN_diagnostic' for r in ranks),360)
        self.assertEqual(sum(r['empty_pool'] and r['context'] in ('nba_out_of_fold','nfhs_secondary') for r in ranks),21)
        self.assertEqual(sum(r['eligible'] and r['context']=='nba_out_of_fold' for r in ranks),2811)
        cases=analysis.preserved_cases(self.protected,self.candidates,self.policies)
        self.assertEqual(len(cases['all21_external_stress_recovery_queries']),21)
        self.assertEqual(len(cases['all6_below_001_queries']),6)
        self.assertTrue(all(r['scores']['Q']==r['scores']['LC'] for r in cases['all21_external_stress_recovery_queries']))

    def test_canonical_full_scoring_and_training_memberships(self):
        package=analysis.read(self.root/analysis.QROOT/'preparation/candidates.jsonl')
        proposal=analysis.read(self.root/analysis.PROPOSAL)
        groups,captures,weights=analysis.expected_groups(self.root,proposal,self.registry,package)
        self.assertEqual(sum(map(len,groups.values())),88742)
        self.assertEqual(sum(map(len,captures.values())),88742)
        self.assertEqual(sum(len(v) for k,v in groups.items() if k[1]=='training_health'),35048)
        for fit in ('leave_chi_out','leave_den_out','leave_sac_out'):
            self.assertFalse(groups[(fit,'package_held')] & groups[(fit,'training_health')])


if __name__ == '__main__':
    unittest.main()

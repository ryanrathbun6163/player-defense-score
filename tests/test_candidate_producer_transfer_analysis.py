import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.ball_tracking import candidate_producer_transfer_analysis as analysis


def row(key, q, new, category='eligible_match', context='nba_out_of_fold', weak=False):
    return dict(row_key=key,frame_key=context+'|frame',candidate_id=key,query_id=None,
                context=context,fit='leave_chi_out' if context=='nba_out_of_fold' else 'all_nba',
                game_id='CHI' if context=='nba_out_of_fold' else 'HOU',block_id='block',source_frame_index=0,
                cohort='package' if context=='nba_out_of_fold' else 'HOU_main',
                native_or_weak='weak' if weak else 'native',evaluation_category=category,
                target_group='positive' if category=='eligible_match' else 'eligible_distant_miss',
                target=1 if category=='eligible_match' else 0,scores={'Q':q,'Q_plus':new,'J':q})


def policy(key,q,new,category='eligible_match',context='nba_out_of_fold'):
    value=row(key,q,new,category,context)
    value.update(policy='native',cohort='fixed_policy',chosen_row_key='candidate|'+key,
                 point_chosen_before_acceptance=True,fallback_allowed=False)
    return value


def manifest(policies,candidates):
    return {key:sorted(values) for key,values in analysis.protection_sets(policies,candidates).items()}


class TransferAnalysisTests(unittest.TestCase):
    def test_segments_require_exact_order_route_and_finite_values(self):
        plan=dict(fit='leave_chi_out',owner='new_treatment',population='original_held_NBA',
                  id_field='candidate_id',ids=['a','b'],scores=2)
        rows=[{**{k:plan[k] for k in ('fit','owner','population')},'candidate_id':identifier,'quality_logit':value}
              for identifier,value in [('a',0.0),('b',-2.0)]]
        self.assertEqual(analysis.validate_segment(plan,rows),{'a':0.0,'b':-2.0})
        for bad in (list(reversed(rows)),rows[:1],rows+[rows[0]]):
            with self.assertRaises(ValueError):analysis.validate_segment(plan,bad)
        for bad_value in (None,True,float('nan'),float('inf'),'1'):
            bad=copy.deepcopy(rows);bad[0]['quality_logit']=bad_value
            with self.assertRaises(ValueError):analysis.validate_segment(plan,bad)
        bad=copy.deepcopy(rows);bad[0]['fit']='all_nba'
        with self.assertRaises(ValueError):analysis.validate_segment(plan,bad)

    def test_fixed_choice_does_not_rerank_or_fall_back(self):
        a,b=row('a',2,-1),row('b',1,7,'eligible_miss')
        selected=policy('quality_top|frame',2,0)
        selected.update(policy='quality_top',chosen_row_key='a',quality_top_tied_row_keys=['a'])
        original=copy.deepcopy(selected)
        joined=analysis.join_policies([selected],[a,b])[0]
        self.assertEqual(joined['chosen_row_key'],'a')
        self.assertEqual(joined['quality_top_tied_row_keys'],['a'])
        self.assertEqual(joined['scores']['Q_plus'],-1)
        self.assertFalse(analysis.accepted(joined,'Q_plus'))
        self.assertEqual(selected,original)

    def test_missing_choice_is_not_filled_from_another_point(self):
        missing=policy('p',None,None,'missing_choice')
        missing['chosen_row_key']=None
        joined=analysis.join_policies([missing],[row('b',2,3)])[0]
        self.assertIsNone(joined['scores']['Q_plus'])

    def test_original_missing_query_is_retained_and_cannot_gain_a_score(self):
        missing=row('m',None,None,'missing','HOU_development')
        missing.update(cohort='HOU_stress',query_id='missing_query',candidate_id=None)
        joined=analysis.join_candidates([missing],{})
        self.assertIsNone(joined[0]['scores']['Q_plus'])
        with self.assertRaises(ValueError):
            analysis.join_candidates([missing],{('all_nba','new_treatment','original_external_registry','missing_query'):0.2})

    def test_unknowns_are_preserved_but_boundary_fitting_unknown_miss_is_error(self):
        unknown=row('u',-1,2,'masked_unknown')
        boundary=row('b',-1,2,'eligible_miss');boundary['target']=None;boundary['target_group']='boundary_unknown'
        tally=analysis.evaluation.aggregate([unknown,boundary],'Q_plus')
        self.assertEqual(tally['counts']['unknown_kept'],1)
        self.assertEqual(tally['counts']['wrong_eligible_kept'],1)
        self.assertEqual(tally['denominator'],2)

    def test_offsetting_correct_gain_cannot_hide_protected_identity_loss(self):
        policies=[policy('lost',1,-1),policy('gained',-1,1),policy('wrong',1,-1,'eligible_miss'),
                  policy('hou',1,1,context='HOU_development')]
        result=analysis.decide(policies,[],manifest(policies,[]))
        self.assertFalse(result['fixed_zero_component_criterion_passed'])
        self.assertEqual(result['exact_protected_losses']['protected_policy_row_keys'],['lost'])
        self.assertTrue(result['strict_NBA_improvements'])
        self.assertTrue(all(x['passed'] for x in result['NBA_checks']))

    def test_strict_unchosen_weak_veto_and_all_stress_probes_are_separate(self):
        policies=[policy('gain',-1,1),policy('hou',1,1,context='HOU_development')]
        weak=row('unchosen_weak',1,-1,weak=True)
        stress=row('stress_native',1,-1,context='HOU_development');stress['cohort']='HOU_stress'
        old_failed=row('old_failed_weak',-1,-5,weak=True)
        candidates=[weak,stress,old_failed]
        result=analysis.decide(policies,candidates,manifest(policies,candidates))
        self.assertFalse(result['fixed_zero_component_criterion_passed'])
        self.assertEqual(result['exact_protected_losses']['protected_weak_candidate_row_keys'],['unchosen_weak'])
        self.assertEqual(result['exact_protected_losses']['protected_HOU_stress_query_row_keys'],['stress_native'])
        self.assertNotIn('old_failed_weak',str(result['exact_protected_losses']))

    def test_hou_nonregression_veto_and_nba_strict_gain(self):
        unchanged=[policy('nba',1,1),policy('hou',1,1,context='HOU_development')]
        self.assertFalse(analysis.decide(unchanged,[],manifest(unchanged,[]))['fixed_zero_component_criterion_passed'])
        gaining=[policy('nba',-1,1),policy('hou',1,1,context='HOU_development')]
        self.assertTrue(analysis.decide(gaining,[],manifest(gaining,[]))['fixed_zero_component_criterion_passed'])
        gaining.append(policy('hou_wrong',-1,1,'eligible_miss','HOU_development'))
        self.assertFalse(analysis.decide(gaining,[],manifest(gaining,[]))['fixed_zero_component_criterion_passed'])

    def test_modified_protection_manifest_is_rejected(self):
        policies=[policy('nba',1,1),policy('hou',1,1,context='HOU_development')]
        frozen=manifest(policies,[]);frozen['protected_policy_row_keys']=[]
        with self.assertRaises(ValueError):analysis.decide(policies,[],frozen)

    def test_curve_ties_strict_zero_endpoints_and_missing(self):
        rows=[row('correct',1,1),row('wrong',1,1,'eligible_miss'),
              row('hidden',0,0,'certain_hidden'),row('missing',None,None,'missing')]
        curve=analysis.evaluation.curve(rows,'Q_plus')
        names=curve['measure_columns']
        threshold={p['threshold']:p for p in curve['points'] if p['kind']=='threshold'}
        self.assertEqual(threshold[1]['tied_candidates'],2)
        self.assertEqual(sum(threshold[1]['counts']),0)
        self.assertEqual(threshold[0]['counts'][names.index('correct_kept')],1)
        self.assertEqual(threshold[0]['counts'][names.index('wrong_eligible_kept')],1)
        self.assertEqual(threshold[0]['counts'][names.index('hidden_candidates')],0)
        self.assertEqual(curve['points'][-1]['counts'][names.index('hidden_candidates')],1)
        self.assertEqual(curve['missing_scores'],1)
        self.assertIsNone(curve['threshold_chosen'])

    def test_ranking_is_descriptive_and_keeps_unknown_rivals(self):
        a,b=row('a',2,1),row('b',1,1,'eligible_miss')
        frame=dict(frame_key=a['frame_key'],context=a['context'],game_id='CHI',block_id='block',eligible=True)
        result=list(analysis.ranking_diagnostics([frame],[a,b]))[0]
        self.assertEqual(result['arms']['Q']['state'],'strict_match_first')
        self.assertEqual(result['arms']['Q_plus']['state'],'match_tied_first')
        self.assertEqual(result['arms']['Q_plus']['top_tied_row_keys'],['a','b'])
        self.assertFalse(result['new_emitted_policy'])

    def test_failed_analysis_preserves_receipt_and_refuses_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);complete=root/'completed.json';complete.write_text('{}')
            out=root/analysis.STUDY/'analysis'
            with mock.patch.object(analysis,'load_inputs',side_effect=ValueError('deliberate malformed frozen binding')):
                with self.assertRaises(ValueError):analysis.analyze(root,complete,out)
            self.assertTrue((out/'started.json').exists())
            self.assertIn('deliberate malformed',json.loads((out/'failed.json').read_text())['error'])
            self.assertFalse((out/'completed.json').exists())
            with self.assertRaises(FileExistsError):analysis.analyze(root,complete,out)


if __name__=='__main__':unittest.main()

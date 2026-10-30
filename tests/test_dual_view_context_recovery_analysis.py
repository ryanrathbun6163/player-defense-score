"""Recovered accounting is explicit; inherited scientific metric code is exact."""
import ast
import copy
from pathlib import Path
import unittest

from src.ball_tracking import dual_view_context_recovery_analysis as analysis


def completion():
    logical={key:value for kind,(calls,presentations) in analysis.CALL_BUDGETS.items()
        for key,value in ((kind+'_forwards_attempted',calls),(kind+'_forwards_returned',calls),
                          (kind+'_candidate_presentations',presentations))}
    logical['optimizer_updates']=19740
    physical=dict(logical)
    for field in ('training_forwards_attempted','training_forwards_returned','optimizer_updates'):
        physical[field]+=67
    physical['training_candidate_presentations']+=2144
    budget={'local_capture':(0,0),'training':(7626,243834),'scoring':(2754,88032),
            'local_parity':(0,0),'auxiliary_parity':(2,64)}
    continuation={key:value for kind,(calls,presentations) in budget.items()
        for key,value in ((kind+'_forwards_attempted',calls),(kind+'_forwards_returned',calls),
                          (kind+'_candidate_presentations',presentations))}
    continuation['optimizer_updates']=7626
    return dict(status='completed_exact_recovered_logical_workload',counters=physical,
        physical_counters=copy.deepcopy(physical),logical_counters=logical,continuation_counters=continuation)


class RecoveryAnalysisTests(unittest.TestCase):
    def test_actual_physical_counts_include_discarded_updates(self):
        result=analysis.validate_completion_accounting(completion())
        self.assertEqual(result['actual_combined_physical_counters']['optimizer_updates'],19807)
        self.assertEqual(result['logical_endpoint_counters']['optimizer_updates'],19740)
        self.assertEqual(result['discarded_physical_optimizer_updates'],67)
        self.assertEqual(result['physical_backbone_presentations'],899618)
        self.assertEqual(sum(v for k,v in result['actual_combined_physical_counters'].items() if k.endswith('_forwards_returned')),28149)

    def test_no_projection_of_logical_counters_as_physical(self):
        record=completion();record['counters']=dict(record['logical_counters'])
        with self.assertRaises(ValueError):analysis.validate_completion_accounting(record)

    def test_no_unreviewed_work_or_silent_recapture(self):
        for field in ('optimizer_updates','local_capture_forwards_returned','scoring_candidate_presentations'):
            record=completion();record['continuation_counters'][field]+=1
            with self.assertRaises(ValueError):analysis.validate_completion_accounting(record)
        record=completion();record['status']='completed_exact_frozen_workload'
        with self.assertRaises(ValueError):analysis.validate_completion_accounting(record)

    def test_all_inherited_metric_and_transport_functions_identical(self):
        root=Path(__file__).resolve().parents[1]/'src/ball_tracking'
        def functions(path):
            return {node.name:ast.dump(node,include_attributes=False) for node in ast.parse(path.read_text()).body
                    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
        old=functions(root/'dual_view_context_analysis.py')
        new=functions(root/'dual_view_context_recovery_analysis.py')
        self.assertEqual(set(new)-set(old),{'validate_completion_accounting'})
        self.assertEqual({key for key in old if old[key]!=new[key]},{'load_scores','analyze'})
        # In particular, no gate, ranking, BCE, score-label, slice or case rule changed.
        for key in ('gate','decisions','ranking','training_health','paired','tables','preserved_cases','captured_Q_parity'):
            self.assertEqual(old[key],new[key])


if __name__=='__main__':unittest.main()

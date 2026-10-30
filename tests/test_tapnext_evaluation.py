"""Actual TAP producer transport and unchanged scoring; synthetic CPU media only."""
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import tapnext_adapter as adapter
from src.ball_tracking import tapnext_evaluation as evaluation
from src.ball_tracking import completion_evaluation as original
from src.ball_tracking.completion_evaluation_package import _baseline
from src.ball_tracking.completion_training_runtime import atomic_write_once, binding
from src.ball_tracking.wasb_experiment import canonical, read_json
from tests import test_completion_evaluation as evaluation_fixtures
from tests import test_completion_nba_comparison_render as nba_fixtures


class Backend:
    def __init__(self, width, height, points, visibility):
        self.width, self.height, self.points, self.visibility = width, height, points, visibility
        self.calls = 0

    def infer(self, rgb, query, state):
        point = self.points[self.calls]
        yx = np.array([point[1]*256/self.height, point[0]*256/self.width], np.float32)
        xy = yx[::-1] * np.array([self.width/256, self.height/256], np.float32)
        visible = self.visibility[self.calls]
        self.calls += 1
        return adapter.TrackerFrame(np.tile(xy,(65,1)), np.tile(yx,(65,1)),
            np.zeros((65,512),np.float32), np.full(65,visible,np.float32), {"step":self.calls})


def produce(root, block, points=None, visibility=None):
    n = len(block['frames'])
    points = points or [[20,12]]*n
    backend = Backend(block['source_video']['width_px'], block['source_video']['height_px'],
                      points, visibility or [1.]*n)
    tracker = adapter.SingleSeedAdapter(backend)
    tracker.begin_block(block['block_id'], backend.width, backend.height, block['time_base'])
    result = []
    for frame, baseline in zip(block['frames'],original.baseline_observations(block),strict=True):
        with Image.open(root/frame['png']['path']) as image:
            rgb = np.asarray(image).copy()
        result.append(tracker.observe(rgb, {'source_frame_index':frame['source_frame_index'],
            'source_pts_ticks':frame['source_pts_ticks'],'duration_ticks':frame['duration_ticks'],
            'time_base':block['time_base'],'source_png':frame['png'],
            'wasb_observation':adapter.project_wasb_observation(baseline)}))
    return result


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = evaluation_fixtures.EvaluationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.block = self.fixture.block()

    def test_actual_adapter_records_serialize_and_validate_without_wasb_fields(self):
        rows = produce(self.root,self.block,visibility=[1,0,1,-1])
        path = self.root/'observations.json'
        atomic_write_once(path,rows)
        checked = evaluation.validate_observations(self.block,read_json(path))
        self.assertEqual(checked['model_calls'],4)
        self.assertEqual([r['center_xy_px'] for r in rows],[[20.,12.],None,[20.,12.],None])
        self.assertTrue(all('temporal_contributions' not in r and 'candidates' not in r for r in rows))
        self.assertEqual(rows[1]['tracker_raw']['center_xy_px'],[20.,12.])

    def test_before_seed_and_block_reset_are_actual_producer_states(self):
        original_record = deepcopy(self.block['frames'][0]['baseline_observation']['original_record'])
        original_record.update(state='missing',center_xy_px=None,native_score=None,candidates=[],selected_candidate_index=None)
        self.block['frames'][0]['baseline_observation'] = _baseline(original_record)
        rows = produce(self.root,self.block)
        self.assertEqual(rows[0]['missing_reason'],'before_first_valid_automatic_seed')
        self.assertEqual(evaluation.validate_observations(self.block,rows)['model_calls'],3)
        self.assertTrue(rows[1]['seeded_this_frame'])
        changed=deepcopy(rows)
        changed[2]['seeded_this_frame']=True
        with self.assertRaisesRegex(ValueError,'seed/reseed'):
            evaluation.validate_observations(self.block,changed)

    def test_stale_failure_manual_transform_and_hidden_leak_rejected(self):
        rows=produce(self.root,self.block,visibility=[1,0,1,1])
        mutations=[('source_pts_ticks',1),('inference_status','failed'),('point_origin','manual'),
                   ('temporal_contributions',3),('tracker_calls_in_block',8)]
        for field,value in mutations:
            changed=deepcopy(rows);changed[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                evaluation.validate_observations(self.block,changed)
        changed=deepcopy(rows);changed[1]['center_xy_px']=[20,12]
        with self.assertRaisesRegex(ValueError,'visibility'):
            evaluation.validate_observations(self.block,changed)
        changed=deepcopy(rows);changed[0]['tracker_raw']['coordinates_model_yx'][0]+=1
        with self.assertRaisesRegex(ValueError,'coordinate transform'):
            evaluation.validate_observations(self.block,changed)
        changed=deepcopy(rows);changed[0]['wasb_observation']['original_record_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'baseline projection'):
            evaluation.validate_observations(self.block,changed)

    def test_protected_transport_rejected_before_any_source_read(self):
        rows=produce(self.root,self.block)
        block=deepcopy(self.block);block['protected_ranges']=[[0,0]]
        with patch.object(evaluation.nba,'source_rgb',side_effect=AssertionError('No pixel read')):
            with self.assertRaises(ValueError):evaluation.validate_observations(block,rows)


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.fixture=evaluation_fixtures.EvaluationTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root

    def package(self, wrong_source=None):
        package,_=self.fixture.package()
        package['selected_method']={'method_kind':evaluation.METHOD,'checkpoint':{'path':'TAP.ckpt','sha256':'synthetic','size_bytes':1},
                                    'policy':{'id':adapter.POLICY}}
        for cid in ['nba_a','nba_b']:
            block=self.fixture.block(cid,domain='nba',n=60)
            block.pop('possession_id');block['candidate_id']=cid
            package['inference_blocks'].append(block)
        inventory=[{'cohort_id':f'guard_{i}','source_id':'possession_001','frame_indices':list(range(4)),
                    'regression_screen':True,'role':'checkpoint_selection_development'} for i in range(11)]
        inventory += [{'cohort_id':cid,'source_id':cid,'frame_indices':list(range(60)),
                       'regression_screen':True,'pilot_control':True,'role':'excluded_development'} for cid in ['nba_a','nba_b']]
        inventory += [{'cohort_id':f'descriptive_{i}','source_id':'possession_002','frame_indices':list(range(4)),
                       'regression_screen':False,'role':'training_exposure'} for i in range(3)]
        package['regression_cohorts']=inventory
        records={}
        for block in package['inference_blocks']:
            source=block.get('possession_id',block.get('candidate_id'))
            points=[[50,30]]*len(block['frames']) if source==wrong_source else None
            records[block['block_id']]={'block_sha256':canonical(block),'observations':produce(self.root,block,points)}
        return package,records

    def test_actual_scoring_envelope_preserves16cohorts13guards_and_unknown_review(self):
        package,records=self.package()
        pb={'path':'package.json','sha256':'synthetic'}
        result=evaluation.score_package(package,records,pb)
        self.assertEqual(len(result['regression_cohorts']),16)
        self.assertEqual(sum(c['status']=='pass' for c in result['regression_cohorts']),13)
        self.assertEqual(sum(c['status']=='descriptive_training_exposure' for c in result['regression_cohorts']),3)
        self.assertIsNone(result['training_result']);self.assertIsNone(result['selection'])
        self.assertEqual(result['prospective_regression_status'],'pass')
        evaluation.curated.validate_evaluation(package,result,pb)
        for timeline,comparison in zip(package['curated_timelines'],result['curated_comparisons']):
            evaluation.curated.validate_timeline(timeline,comparison)
            self.assertEqual(comparison['selected_metrics']['summary']['matched'],4)
            self.assertEqual(comparison['selected_metrics']['summary']['withheld'],1)
            self.assertEqual(comparison['selected_metrics']['summary']['gates']['wrong_object_runs']['status'],'inconclusive')
        self.assertFalse(result['full_clip_pass_claimed'])
        headline=evaluation.scorecard_html(result)
        self.assertIn('13/13 pass',headline)
        self.assertIn('4/4',headline)
        self.assertIn('Certain-hidden emissions',headline)

    def test_guard_failure_and_descriptive_result_stay_distinct(self):
        package,records=self.package(wrong_source='possession_002')
        result=evaluation.score_package(package,records,{'path':'p','sha256':'s'})
        self.assertEqual(result['prospective_regression_status'],'pass')
        self.assertEqual(result['permitted_development_screen']['possession_002']['wrong'],4)
        package,records=self.package(wrong_source='possession_001')
        self.assertEqual(evaluation.score_package(package,records,{'path':'p','sha256':'s'})['prospective_regression_status'],'fail')
        package['regression_cohorts'].pop()
        with self.assertRaisesRegex(ValueError,'inventory'):
            evaluation.score_package(package,records,{'path':'p','sha256':'s'})


@unittest.skipUnless(shutil.which('ffprobe'),'ffprobe required for CPU media transport')
class RenderingTests(unittest.TestCase):
    def test_actual_vfr_tap_media_and_final_interval_roundtrip(self):
        fixture=nba_fixtures.NbaComparisonRenderTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        rows=produce(fixture.root,fixture.block,visibility=[1,0,1,-1])
        result=evaluation.render_nba_block(fixture.root,fixture.block,rows,fixture.root/'data/outputs/tap',{'synthetic':True})
        self.assertEqual(result['decoded_frames'],4)
        self.assertEqual(result['actual_final_native_frame'],103)
        self.assertEqual(result['actual_final_duration_ticks'],1440)
        self.assertEqual(result['total_duration_ticks'],5940)
        self.assertEqual(result['added_final_hold_ticks'],0)
        transported=read_json(fixture.root/result['frame_records']['path'])
        self.assertEqual([r['selected_observation'] for r in transported['frames']],rows)
        self.assertTrue(all('candidates' not in r['selected_observation'] for r in transported['frames']))
        with self.assertRaises(FileExistsError):
            evaluation.render_nba_block(fixture.root,fixture.block,rows,fixture.root/'data/outputs/tap',{})

    def test_actual_curated_encoder_has_exact_native_pts_including_black_final(self):
        fixture=evaluation_fixtures.EvaluationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        package,_=fixture.package()
        block,timeline=package['inference_blocks'][0],package['curated_timelines'][0]
        rows=produce(fixture.root,block)
        comparison={'possession_id':timeline['possession_id'],
            'baseline_observations':original.baseline_observations(block),'selected_observations':rows}
        for label in ['baseline','selected']:
            comparison[label+'_metrics']=evaluation.score_timeline(timeline,comparison[label+'_observations'])
        with patch.object(evaluation.curated,'read_players',return_value={}):
            result=evaluation.curated.render_possession(fixture.root,timeline,comparison,fixture.root/'data/outputs/curated')
        probe=evaluation.nba.probe_encoded_video(fixture.root/result['video']['path'])
        self.assertEqual(evaluation.validate_curated_timing(probe,timeline),5)
        self.assertEqual(result['protected_black_frames'],1)
        changed=deepcopy(timeline);changed['frames'][-1]['duration_ticks']+=1
        with self.assertRaisesRegex(ValueError,'final interval'):
            evaluation.validate_curated_timing(probe,changed)


if __name__=='__main__':unittest.main()

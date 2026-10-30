"""Original component/cache producers drive this saved-pool consumer's checks."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.ball_tracking import nba_candidate_preservation as experiment
from src.ball_tracking import nba_action_observation as producer
from src.ball_tracking import nba_wasb_diagnostic as d
from tests import test_nba_adaptation_regression_diagnostic as cache_fixture
from tests.test_nba_hard_example_diagnostic import label

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / 'configs/ball_tracking/selections/nba_candidate_preservation_v0_1.json'


def plane(pixels):
    values = np.zeros((288, 512), np.float32)
    for (x, y), value in pixels.items(): values[y, x] = value
    return values


def emitted(values):
    frame = {'source_frame_index': 3, 'source_pts_ticks': 10800, 'png': {'path': 'synthetic.png'}}
    manifest = {'candidate_id': 'synthetic', 'game_id': 'fixture', 'approved_role': 'target_case_development', 'time_base': '1/90000',
                'source_video': {'width_px': 512, 'height_px': 288}, 'frames': [frame]}
    observation = producer.select_observation(frame, values, 3, manifest,
        {'kind': 'development_window', 'source_frame_range_inclusive': [1, 5]})
    return observation, manifest


class CandidatePreservationTests(unittest.TestCase):
    def test_actual_components_strict_threshold_duplicates_and_inclusive_radius(self):
        mean = plane({(50, 50): .6, (100, 100): .4, (150, 150): .3})
        observation, _ = emitted(mean)
        contributor = plane({(50, 50): .8, (100, 100): .4, (200, 200): np.nextafter(np.float32(.3), np.float32(1))})
        pool = experiment.build_pool('old', 'synthetic', 3, observation,
                                     [(1, 2, contributor), (2, 1, contributor)], (512, 288))
        self.assertEqual(pool['mean_record_count'], 2)
        self.assertEqual([r['component'] for r in pool['records'][:2]], observation['candidates'])
        self.assertEqual(len(pool['records']), 8)
        self.assertEqual([g['record_indices'] for g in pool['coordinate_groups']], [[0, 2, 5], [1, 3, 6], [4, 7]])
        self.assertEqual(len({tuple(r['provenance_id']) for r in pool['records']}), 8)
        result = experiment.evaluate_pool(pool, label(3, (40, 50)))
        self.assertTrue(result['mean']['available']); self.assertTrue(result['union']['ambiguous'])
        self.assertEqual(result['union']['matching_records'], 3)
        self.assertEqual(result['incremental_nonmatching_in_image_records'], 4)
        self.assertEqual(result['incremental_nonmatching_in_image_coordinates'], 1)
        self.assertFalse(experiment.evaluate_pool(pool, label(3, (39.9999, 50)))['union']['available'])
        # Exact coordinate equality groups provenance; nearby floats are not merged.
        changed = copy.deepcopy(pool['records'][:2]); changed[1]['component']['center_x'] = 50.000001
        changed[1]['component']['center_y'] = 50
        self.assertEqual(len(experiment.coordinate_groups(changed)), 2)

    def test_label_changes_cannot_change_pool_and_contributor_match_is_not_prediction(self):
        observation, manifest = emitted(plane({}))
        original = copy.deepcopy(observation)
        pool = experiment.build_pool('old', 'synthetic', 3, observation, [(1, 2, plane({(50, 50): .8}))], (512, 288))
        encoded = json.dumps(pool, sort_keys=True)
        good = experiment.evaluate_pool(pool, label(3))
        other = experiment.evaluate_pool(pool, label(3, (100, 100)))
        self.assertTrue(good['newly_available']); self.assertFalse(other['union']['available'])
        self.assertEqual(json.dumps(pool, sort_keys=True), encoded)
        self.assertEqual(observation, original)
        self.assertEqual(observation['state'], 'missing')
        score = d.score_reference({**manifest, 'annotations': [label(3)]}, {'frames': [observation]})['frame_results'][0]
        self.assertEqual(score['outcome'], 'missing'); self.assertFalse(score['raw_candidate_available'])

    def test_original_outside_mean_record_is_retained_but_cannot_match(self):
        observation, _ = emitted(plane({(50, 50): .8}))
        observation['candidates'][0]['center_x'] = -1
        pool = experiment.build_pool('old', 'synthetic', 3, observation, [], (512, 288))
        measured = experiment.evaluate_pool(pool, label(3, (0, 50)))['union']
        self.assertEqual(pool['records'][0]['component'], observation['candidates'][0])
        self.assertEqual(measured['raw_records'], 1); self.assertEqual(measured['out_of_image_records'], 1)
        self.assertFalse(measured['available']); self.assertTrue(measured['empty'])

    def test_hidden_unknown_and_added_burden_preserve_null_geometry(self):
        observation, _ = emitted(plane({}))
        pool = experiment.build_pool('old', 'synthetic', 3, observation, [(1, 2, plane({(50, 50): .8}))], (512, 288))
        hidden = label(3); hidden.update(geometry=None, localization_eligible=False, visibility='not_visible')
        result = experiment.evaluate_pool(pool, hidden)
        self.assertTrue(result['newly_nonempty_hidden'])
        self.assertIsNone(result['union']['available']); self.assertIsNone(result['union']['matching_records'])
        self.assertIsNone(result['incremental_nonmatching_in_image_coordinates'])
        unknown = copy.deepcopy(hidden); unknown['game_ball_identity_certainty'] = 'uncertain'
        self.assertEqual(experiment.eligibility(unknown), 'unknown')
        self.assertIsNone(experiment.evaluate_pool(pool, unknown)['newly_nonempty_hidden'])

    def test_configured_screen_uses_old_non_anchor_gains_and_reports_context_separately(self):
        absent, _ = emitted(plane({})); present, _ = emitted(plane({(50, 50): .8}))
        gained = experiment.evaluate_pool(experiment.build_pool('old', 's', 3, absent, [(1, 2, plane({(50, 50): .8}))], (512, 288)), label(3))
        unchanged = experiment.evaluate_pool(experiment.build_pool('old', 's', 3, absent, [], (512, 288)), label(3))
        def row(group, index, anchor, context, old_gain=True):
            return {'candidate_id': group, 'source_frame_index': index, 'window_id': group, 'analysis_group': group,
                'is_control': False, 'eligibility': 'eligible', 'annotation': label(index),
                'is_prior_anchor': anchor, 'inside_prior_context': context,
                **{arm: {'evaluation': copy.deepcopy(gained if arm == 'new' or old_gain else unchanged),
                         'original_score': {'outcome': 'missing'}} for arm in ('old', 'new')}}
        rows = [row('DET', 1, True, True), row('DET', 2, False, True), row('NFHS', 3, False, False)]
        scope = {'expected_mean_pool_available': {g: {'old': 0, 'new': 0} for g in ('DET', 'NFHS')}, 'limits': [],
            'usefulness_screen': {'primary_arm': 'old', 'groups': ['DET', 'NFHS'], 'minimum_newly_available_non_anchor_per_group': 1,
                                 'pass_meaning': 'consider selector only', 'fail_meaning': 'reject', 'costs': 'retain costs'}}
        summary = experiment.summarize(rows, scope)
        self.assertTrue(summary['usefulness_screen']['passed'])
        det = summary['by_analysis_group']['DET']['arms']['old']
        self.assertEqual(det['newly_available'], 2); self.assertEqual(det['newly_available_non_anchor'], 1)
        self.assertEqual(det['newly_available_outside_prior_context'], 0)
        self.assertFalse(summary['usefulness_screen']['candidate_or_model_promoted'])
        rows[2] = row('NFHS', 3, False, False, old_gain=False)
        self.assertFalse(experiment.summarize(rows, scope)['usefulness_screen']['passed'])

    def test_original_nfhs_producer_cache_mean_and_score_contracts(self):
        fixture = cache_fixture.OriginalNFHSProducerTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        source = fixture.source; cid = source['candidate_id']
        windows = {(cid, i): {'window_id': cid, 'cohort': 'nfhs_development', 'analysis_group': 'NFHS', 'is_control': False}
                   for i in source['source_frame_indices']}
        resources = {'triplet_cache_reads': [], 'attempted_cache_reads': 0, 'old_nfhs_mean_bundles': [],
                     'peak_rolling_triplet_arrays': 0, 'contributor_planes_measured': 0}
        before = {fixture.root / r['receipt']['path']: (fixture.root / r['receipt']['path']).read_bytes()
                  for arm in ('old', 'new') for r in source['triplets'][arm]}
        rows = experiment.analyze_source(fixture.root, source, fixture.authority, source['triplets'], windows,
            {'anchors': {(cid, 49)}, 'context': {(cid, i) for i in (47, 48, 49)}}, resources)
        self.assertEqual([len(r['old']['pool']['contributor_planes']) for r in rows], [3, 2, 1])
        self.assertEqual([r['old']['pool']['mean_record_count'] for r in rows], [1, 1, 1])
        self.assertEqual([r['old']['original_score']['outcome'] for r in rows], ['matched']*3)
        self.assertEqual([r['old']['evaluation']['union']['raw_records'] for r in rows], [4, 3, 2])
        self.assertEqual(resources['attempted_cache_reads'], 6); self.assertEqual(resources['contributor_planes_measured'], 12)
        self.assertEqual(resources['old_nfhs_mean_bundles'][0]['selected_planes_verified'], 3)
        for receipt in resources['triplet_cache_reads']:
            if receipt['arm'] == 'old':
                self.assertEqual(receipt['historical_producer_threshold'], .5)
                self.assertFalse(receipt['captured_png_and_pts_identity'])
        for path, content in before.items(): self.assertEqual(path.read_bytes(), content)

    def test_frozen_scope_counts_and_policy_header_cannot_misstate_implementation(self):
        scope = d.read_json(SCOPE)
        self.assertEqual(scope['policy'], experiment.POLICY)
        self.assertEqual([scope['totals'][k] for k in ('frames', 'frame_arm_rows', 'unique_triplet_bodies')], [790, 1580, 1580])
        self.assertEqual([scope['totals'][k] for k in ('eligible', 'hidden', 'unknown')], [652, 91, 47])
        changed = copy.deepcopy(scope); changed['policy']['nms'] = True
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'scope.json'; d.write_once(path, changed)
            with self.assertRaisesRegex(ValueError, 'policy differs'): experiment.load_plan(Path(folder), path)


if __name__ == '__main__': unittest.main()

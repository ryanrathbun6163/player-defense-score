"""Saved producer contracts and bounded metrics; no real model or media reads."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_adaptation_regression_diagnostic as diagnostic
from src.ball_tracking import nba_adaptation_comparison as comparison
from src.ball_tracking import nba_action_observation as action
from src.ball_tracking import nba_saved_heatmap_diagnostic as metrics
from src.ball_tracking import nba_wasb_diagnostic as d
from src.ball_tracking import wasb_calibration, wasb_experiment
from tests import test_nba_action_observation as action_fixture
from tests import test_nba_adaptation_comparison as comparison_fixture
from tests import test_nba_wasb_diagnostic as model_fixture
from tests.test_nba_hard_example_diagnostic import label

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / 'configs/ball_tracking/selections/nba_adaptation_regression_diagnostic_v0_1.json'


def descriptor(root, record, format):
    return {'start': record['first_source_frame_index'], 'format': format, 'producer_record': record,
            'cache': record['cache'], 'receipt': d.binding(root, (root / record['cache']['path']).with_suffix('.json'))}


class ScopeAndMeasurementTests(unittest.TestCase):
    def test_authorized_exact_scope_and_original_boundary_contributors(self):
        scope = d.read_json(SCOPE); diagnostic.validate_scope(scope)
        self.assertEqual([len(s['source_frame_indices']) for s in scope['sources']], [15, 14, 3, 5])
        self.assertEqual([scope['totals'][k] for k in ('frames', 'means', 'triplet_bodies', 'anchor_planes')], [37, 74, 94, 20])
        self.assertEqual(diagnostic.needed_starts([47, 48, 49], [25, 49]), [45, 46, 47])
        self.assertEqual(diagnostic.needed_starts([49], [25, 49]), [47])
        changed = copy.deepcopy(scope); changed['sources'][0]['source_frame_indices'].pop()
        with self.assertRaisesRegex(ValueError, 'frame scope'): diagnostic.validate_scope(changed)
        changed = copy.deepcopy(scope); changed['policy']['support_threshold_strict'] = .2
        with self.assertRaisesRegex(ValueError, 'measurement rule'): diagnostic.validate_scope(changed)

    def test_components_ties_inclusive_radius_alternatives_and_null_geometry(self):
        grid = metrics.source_grid(512, 288)
        mean = np.zeros((288, 512), np.float32); mean[50, 50] = .6; mean[100, 100] = .6; mean[150, 150] = .3
        frame = {'source_frame_index': 1, 'source_pts_ticks': 3600, 'png': {'path': 'fixture.png'}}
        manifest = {'source_video': {'width_px': 512, 'height_px': 288}, 'time_base': '1/90000'}
        obs = action.select_observation(frame, mean, 1, manifest, {'kind': 'development_window', 'source_frame_range_inclusive': [1, 3]})
        result = diagnostic.describe_plane(mean, [(1, 0, mean)], grid, obs, label(1, (90, 100)),
                                           {'old_selected_center': [50, 50], 'new_selected_center': [100, 100]}, (512, 288))
        self.assertEqual([c['mass_rank'] for c in result['components']], [1, 2])
        self.assertEqual(result['matching_alternative_indices'], [1])
        self.assertEqual(result['components'][1]['centroid_error_px'], 10)
        self.assertEqual(result['mean_metrics']['active_pixels_global'], 2)
        hidden = label(1); hidden.update(geometry=None, localization_eligible=False)
        result = diagnostic.describe_plane(mean, [(1, 0, mean)], grid, obs, hidden, {}, (512, 288))
        self.assertIsNone(result['mean_metrics']['local_peak']); self.assertIsNone(result['averaging']['support_lost_in_mean'])
        self.assertTrue(all(c['centroid_error_px'] is None for c in result['components']))
        # The same distance is not a matching alternative when outside source bounds.
        result = diagnostic.describe_plane(mean, [(1, 0, mean)], grid, obs, label(1, (90, 100)), {}, (80, 288))
        self.assertEqual(result['matching_alternative_indices'], [])

    def test_averaging_loss_and_fixed_location_response_are_separate_from_labels(self):
        values = [np.zeros((288, 512), np.float32) for _ in range(3)]
        values[0][50, 50] = .8; values[1][50, 50] = .04; values[2][50, 50] = .04
        for value in values: value[100, 100] = .5
        mean = metrics.reconstruct_mean(list(zip((1, 2, 3), values)))
        manifest = {'source_video': {'width_px': 512, 'height_px': 288}, 'time_base': '1/90000'}
        frame = {'source_frame_index': 3, 'source_pts_ticks': 10800, 'png': {'path': 'fixture.png'}}
        obs = action.select_observation(frame, mean, 3, manifest, {'kind': 'development_window', 'source_frame_range_inclusive': [1, 5]})
        result = diagnostic.describe_plane(mean, [(s, 3-s, p) for s, p in zip((1, 2, 3), values)],
                                           metrics.source_grid(512, 288), obs, label(3, (50, 50)),
                                           {'old_selected_center': [50, 50], 'new_selected_center': [100, 100]}, (512, 288))
        self.assertTrue(result['averaging']['support_lost_in_mean'])
        self.assertAlmostEqual(result['fixed_selection_locations']['new_selected_center']['metrics']['local_peak'], .5)
        self.assertEqual(result['original_observation']['center_xy_px'], [100, 100])

    def test_failed_attempt_is_preserved_and_completion_cannot_be_overwritten(self):
        parent = ROOT / 'data/outputs/t'; parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='regression_synthetic_', dir=parent) as folder:
            output = Path(folder); scope = d.read_json(SCOPE); scope['output_root'] = output.relative_to(ROOT).as_posix()
            path = output / 'scope.json'; d.write_once(path, scope)
            with patch.object(diagnostic, 'read_bound', return_value={}), patch.object(diagnostic, 'analyze_source', side_effect=RuntimeError('synthetic failure')):
                with self.assertRaisesRegex(RuntimeError, 'synthetic failure'): diagnostic.run(ROOT, path)
            failed = list(output.glob('attempts/*/failed.json')); self.assertEqual(len(failed), 1)
            original = failed[0].read_bytes(); self.assertEqual(d.read_json(failed[0])['resources']['model_calls'], 0)
            d.write_once(output / 'completion.json', {'sentinel': True})
            with self.assertRaisesRegex(ValueError, 'Preserve completed'): diagnostic.run(ROOT, path)
            self.assertEqual(failed[0].read_bytes(), original)
            self.assertEqual(d.read_json(output / 'completion.json'), {'sentinel': True})


class NativeTransportTests(unittest.TestCase):
    def test_actual_action_import_and_adaptation_producers_are_consumed_read_only(self):
        fixture = action_fixture.ActionObservationTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        observations, _ = fixture.infer(); before = {}
        for record in observations['triplet_caches']:
            desc = descriptor(fixture.root, record, 'native_action')
            sidecar = fixture.root / desc['receipt']['path']; before[sidecar] = sidecar.read_bytes()
            values, lineage = diagnostic.load_cache(fixture.root, desc, fixture.manifest, observations)
            self.assertEqual(values.shape, (3, 288, 512)); self.assertTrue(lineage['captured_png_and_pts_identity'])
        new_fixture = comparison_fixture.AdaptationComparisonTests(); new_fixture.setUp(); self.addCleanup(new_fixture.doCleanups)
        new = comparison.infer_manifest(new_fixture.root, new_fixture.manifest, new_fixture.old, new_fixture.context, model_fixture.FakeAdapter)
        desc = descriptor(new_fixture.root, new['triplet_caches'][0], 'native_adaptation')
        values, lineage = diagnostic.load_cache(new_fixture.root, desc, new_fixture.manifest, new)
        self.assertEqual(lineage['format'], 'native_adaptation')
        changed = copy.deepcopy(new_fixture.manifest); changed['frames'][0]['source_pts_ticks'] += 1
        with self.assertRaisesRegex(ValueError, 'PNG/PTS'): diagnostic.load_cache(new_fixture.root, desc, changed, new)
        for path, content in before.items(): self.assertEqual(path.read_bytes(), content)

    def test_missing_receipt_and_corruption_refuse_without_repair(self):
        fixture = comparison_fixture.AdaptationComparisonTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        observations = comparison.infer_manifest(fixture.root, fixture.manifest, fixture.old, fixture.context, model_fixture.FakeAdapter)
        desc = descriptor(fixture.root, observations['triplet_caches'][0], 'native_adaptation')
        sidecar = fixture.root / desc['receipt']['path']; original = sidecar.read_bytes(); sidecar.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)): diagnostic.load_cache(fixture.root, desc, fixture.manifest, observations)
        self.assertFalse(sidecar.exists()); sidecar.write_bytes(original)
        cache = fixture.root / desc['cache']['path']; cache.write_bytes(cache.read_bytes() + b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Cache binding'): diagnostic.load_cache(fixture.root, desc, fixture.manifest, observations)


class OriginalNFHSProducerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='regression_nfhs_'); self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)
        source = {'path': 'fixture.mp4', 'sha256': '0'*64, 'width_px': 512, 'height_px': 288, 'fps': 25.0, 'frame_count': 100}
        window = {'window_id': 'synthetic_nfhs', 'possession_id': 'fixture', 'source_video': source,
                  'start_frame_index': 45, 'end_frame_index': 49, 'annotation_set_id': 'fixture'}
        identity = {'weights': {'sha256': d.EXPANDED_SHA}, 'inference': {'heatmap_threshold': .5}}
        images = {i: np.zeros((288, 512, 3), np.uint8) for i in range(45, 50)}
        class Adapter:
            def predict_triplet(self, rgb):
                values = np.zeros((3, 288, 512), np.float32); values[:, 144, 256] = .4
                return {'heatmaps': values, 'frames': [{'transform': {'color_order': 'RGB'}}] * 3}
        with patch.object(wasb_experiment, 'decode_window', return_value=images), patch('torch.cuda.reset_peak_memory_stats'), patch('torch.cuda.synchronize'), patch('torch.cuda.max_memory_allocated', return_value=0):
            wasb_experiment.infer_window(self.root, {'inference': {'heatmap_threshold': .5}}, window, Adapter(), self.root/'old', identity)
        folder = self.root/'old'/window['window_id']
        for key, name in [('mean_heatmaps', 'mean_heatmaps.npz'), ('heatmap_receipt', 'points_receipt.json'), ('original_points', 'points.json'), ('inference_identity', 'inference_identity.json')]:
            window[key] = d.binding(self.root, folder/name)
        means = wasb_calibration.load_mean_heatmaps(self.root, window)
        points, _, components = wasb_calibration.point_runs_from_heatmaps(window, means, .3)
        baseline = {}
        for name, content in [('points', points), ('components', components), ('evaluation', {'fixture': True})]:
            path = self.root/(name+'.json'); d.write_once(path, content); baseline[name] = d.binding(self.root, path)
        frames = []
        for index, image in images.items():
            path = self.root/f'{index}.png'; Image.fromarray(image).save(path)
            frames.append({'source_frame_index': index, 'source_pts_ticks': index*3600,
                           'png': {'path': path.name, 'sha256': d.digest(path), 'rgb_sha256': hashlib.sha256(image.tobytes()).hexdigest()}})
        manifest = {'candidate_id': window['window_id'], 'game_id': 'fixture', 'approved_role': 'nfhs_development', 'source_video': source,
                    'time_base': '1/90000', 'frames': frames, 'preparation_identity': {'window': window}}
        old = comparison.baseline_nfhs(self.root, window, manifest, baseline)
        context = {'output': self.root/'new', 'config_binding': {'fixture': True}, 'training_binding': {'fixture': True}, 'training': {'checkpoint': {'sha256': '2'*64}}}
        new = comparison.infer_manifest(self.root, manifest, old, context, model_fixture.FakeAdapter)
        annotations = [label(i, (256, 144)) for i in range(45, 50)]
        source_record = {'candidate_id': window['window_id'], 'kind': 'nfhs', 'window': window, 'baseline': baseline,
                         'original_identity': window['inference_identity'], 'original_mean_bundle': window['mean_heatmaps'],
                         'source_frame_indices': [47, 48, 49], 'original_context_inclusive': [45, 49], 'anchors': [49], 'anchor_context_frames': {'49': [47, 48, 49]}, 'triplets': {}}
        for key, payload in [('input_manifest', manifest), ('annotation', {'source_video': source, 'annotations': annotations})]:
            path = self.root/(key+'.json'); d.write_once(path, payload); source_record[key] = d.binding(self.root, path)
        source_record['new_observations'] = d.binding(self.root, self.root/'new'/window['window_id']/'observations.json')
        source_record['triplets']['old'] = [{'start': i, 'format': 'nfhs_original', 'cache': d.binding(self.root, folder/f'triplet_{i:06d}.npz'),
                                           'receipt': d.binding(self.root, folder/f'triplet_{i:06d}.json')} for i in range(45, 48)]
        source_record['triplets']['new'] = [descriptor(self.root, r, 'native_adaptation') for r in new['triplet_caches']]
        self.source, self.manifest, self.identity = source_record, manifest, identity
        self.authority = {'training_completion': context['training'], 'comparison_score_report': {'windows': [comparison.compare_reference({**manifest, 'annotations': annotations}, old, new, 'fixture', 'nfhs_development')]}}

    def test_original_nfhs_means_calibration_scores_and_single_tail_contributor_match(self):
        accounting = {'triplet_cache_reads': [], 'old_nfhs_mean_bundles': [], 'peak_rolling_triplet_arrays': 0}; exported = []
        rows = diagnostic.analyze_source(self.root, self.source, self.authority, accounting, exported)
        self.assertEqual([len(r['old']['contributors']) for r in rows], [3, 2, 1])
        self.assertEqual([r['old']['original_score']['outcome'] for r in rows], ['matched']*3)
        self.assertEqual(len(exported), 2); self.assertEqual(len(accounting['triplet_cache_reads']), 6)
        self.assertEqual(accounting['old_nfhs_mean_bundles'][0]['stored_planes_loaded'], 5)
        self.assertTrue(all(r['historical_producer_threshold'] == .5 and not r['captured_png_and_pts_identity'] for r in accounting['triplet_cache_reads'] if r['arm'] == 'old'))
        # The historical >0.5 run is empty; its same saved means yield >0.3 components.
        original = d.read_json(self.root/self.source['window']['original_points']['path'])
        self.assertTrue(all(not f['candidates'] for f in original['frames']))

    def test_original_nfhs_identity_change_refuses_and_receipts_stay_unchanged(self):
        desc = self.source['triplets']['old'][0]; sidecar = self.root/desc['receipt']['path']; before = sidecar.read_bytes()
        diagnostic.load_cache(self.root, desc, self.manifest, nfhs_identity=self.identity)
        with self.assertRaisesRegex(ValueError, 'NFHS identity'):
            diagnostic.load_cache(self.root, desc, self.manifest, nfhs_identity={'changed': True})
        self.assertEqual(sidecar.read_bytes(), before)


if __name__ == '__main__': unittest.main()

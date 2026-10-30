"""Metadata and actual CPU consumer fixtures; no pretrained/neural execution."""
from copy import deepcopy
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from src.ball_tracking import dual_view_context_experiment as worker


class WorkerContractTests(unittest.TestCase):
    def test_import_has_no_torch_or_model_library_side_effects(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            'import sys; from src.ball_tracking import dual_view_context_experiment; '
            'assert not any(x in sys.modules for x in ("torch", "transformers", "numpy", "PIL"))'],
            cwd=worker.ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_six_original_full_epoch_orders_and_partial_batches(self):
        weights = [{'row_key': f'p:{i}'} for i in range(35)]
        for epoch in range(1, 7):
            expected = [row['row_key'] for row in weights]
            random.Random(20261028+epoch).shuffle(expected)
            self.assertEqual(worker.epoch_order(weights, epoch), expected)
            self.assertEqual([len(b) for b in worker.batches(expected)], [32, 3])
        for epoch in (0, 7, True):
            with self.assertRaises(ValueError):
                worker.epoch_order(weights, epoch)

    def test_exact_physical_budget_attempt_return_and_overflow_guards(self):
        self.assertEqual(sum(c for c, _ in worker.CALL_BUDGETS.values()), 28082)
        self.assertEqual(sum(p for _, p in worker.CALL_BUDGETS.values()), 897474)
        self.assertEqual(worker.COUNTER_EXPECTED['optimizer_updates'], 19740)
        worker.validate_counters(dict(worker.COUNTER_EXPECTED))
        with tempfile.TemporaryDirectory() as temp:
            journal = Path(temp)/'journal.jsonl'
            counters = dict.fromkeys(worker.COUNTER_EXPECTED, 0)
            details = {'batch_count': 32}
            with self.assertRaises(ValueError):
                worker.call_returned(counters, 'local_capture', journal, details)
            worker.call_started(counters, 'local_capture', journal, details)
            worker.call_returned(counters, 'local_capture', journal, details)
            self.assertEqual(counters['local_capture_forwards_attempted'], 1)
            self.assertEqual(counters['local_capture_candidate_presentations'], 32)
            self.assertEqual([r['event'] for r in worker.rows(journal)], ['local_capture_start', 'local_capture_return'])
            counters['local_capture_forwards_attempted'] = 2776
            with self.assertRaises(ValueError):
                worker.call_started(counters, 'local_capture', journal, details)
        changed = dict(worker.COUNTER_EXPECTED)
        changed['optimizer_updates'] -= 1
        with self.assertRaises(ValueError):
            worker.validate_counters(changed)

    def test_authorization_binds_exact_freeze_counts_and_no_expansion(self):
        freeze, spec = {'sha256': 'freeze'}, {'sha256': 'spec'}
        authorization = {'execution_approved': True, 'execution_freeze': freeze, 'specification': spec,
                         'scope': dict(worker.COUNTER_EXPECTED), 'max_total_seconds': 5400, 'user_statement': 'Move forward',
                         **dict.fromkeys(('automatic_retry', 'automatic_extension', 'protected_access_approved',
                                         'new_labels_approved', 'selector_approved'), False)}
        worker.validate_authorization(authorization, freeze, spec)
        for key, value in (('execution_approved', False), ('scope', {}), ('automatic_retry', True),
                           ('max_total_seconds', 5401), ('execution_freeze', {'sha256': 'other'})):
            changed = deepcopy(authorization)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                worker.validate_authorization(changed, freeze, spec)

    def test_saved_Q_parity_protects_signs_winners_and_distinct_roles(self):
        rows = {'p:a': {'frame_key': 'f', 'original_id': 'a'}, 'p:b': {'frame_key': 'f', 'original_id': 'b'},
                'b:c': {'frame_key': 'b', 'original_id': 'c'}, 'b:d': {'frame_key': 'b', 'original_id': 'd'},
                'e:a': {'frame_key': 'h', 'original_id': 'a', 'cohort': 'HOU_main'},
                'e:b': {'frame_key': 'h', 'original_id': 'b', 'cohort': 'HOU_main'},
                'e:s': {'frame_key': 'h', 'original_id': 's', 'cohort': 'HOU_stress'}}
        saved = {'p:a': 1., 'p:b': .5, 'b:c': -.5, 'b:d': -1., 'e:a': 2., 'e:b': 1., 'e:s': 9.}
        check = worker.verify_saved_Q(dict(saved), saved, rows)
        self.assertEqual(check['canonical_frame_choices'], 3)
        changed = dict(saved)
        changed['p:b'] = .6
        with self.assertRaises(ValueError):
            worker.verify_saved_Q(changed, saved, rows)
        nearzero = {'p:a': 1e-7, 'p:b': -1.}
        with self.assertRaisesRegex(ValueError, 'sign'):
            worker.verify_saved_Q({'p:a': -1e-7, 'p:b': -1.}, nearzero, rows)
        tied = {'p:a': 1., 'p:b': 1.+1e-7}
        with self.assertRaisesRegex(ValueError, 'choice'):
            worker.verify_saved_Q({'p:a': 1.+1e-7, 'p:b': 1.}, tied, rows)

    def test_actual_input_consumer_preserves_cache_indices_fractional_weights_and_pixels(self):
        from src.ball_tracking import dual_view_context_data as data
        from src.ball_tracking.dual_view_context_model import preprocess_raw
        rng = np.random.default_rng(41)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local = rng.integers(0, 256, (3, 64, 64, 3), dtype=np.uint8)
            context = rng.integers(0, 256, (2, 192, 192, 3), dtype=np.uint8)
            np.save(root/'local.npy', local, allow_pickle=False)
            np.save(root/'context.npy', context, allow_pickle=False)
            links = [{**worker.binding(root, root/name), 'shape': list(array.shape), 'dtype': 'uint8'}
                     for name, array in (('local.npy', local), ('context.npy', context))]
            rows = {}
            for key, local_index, context_index, xy in (('p:a', 2, 0, [7.2, 8.7]), ('e:b', 0, 1, [7.8, 8.1])):
                rows[key] = {'local_cache': {'path': 'local.npy', 'index': local_index},
                             'context_cache_index': context_index,
                             'local_point_weights': data.local_geometry(xy, 200, 200)['weights'],
                             'context_point_weights': data.context_geometry(xy, 200, 200)['weights']}
            loaded = {'rows': rows, 'caches': {'local': links[:1], 'context': links[1]}}
            caches = worker.open_caches(root, loaded)
            try:
                for arm in worker.ARMS:
                    pixels, weights = worker.input_arrays(loaded, caches, ['e:b', 'p:a'], arm)
                    expected_raw = [local[0], local[2]] if arm == 'LL' else [context[1], context[0]]
                    np.testing.assert_array_equal(pixels, np.stack([preprocess_raw(raw, arm) for raw in expected_raw]))
                    field = 'local_point_weights' if arm == 'LL' else 'context_point_weights'
                    np.testing.assert_array_equal(weights, np.array([rows[k][field] for k in ['e:b', 'p:a']]))
                    self.assertEqual(weights.dtype, np.float64)
                    self.assertNotEqual(weights[0].tolist(), weights[1].tolist())
                self.assertFalse(caches['local.npy'].flags.writeable)
                transported = worker.score_rows(['e:b', 'p:a'], [-.2, .5], 'all_nba', 'LC', 'external', 32)
                self.assertEqual([r['row_key'] for r in transported], ['e:b', 'p:a'])
                self.assertEqual([r['feature_index'] for r in transported], [32, 33])
            finally:
                worker.close_caches(caches)

    def test_real_saved_inventory_and_exact_workload_without_image_or_model_execution(self):
        from src.ball_tracking import dual_view_context_data as data
        loaded = data.inventory(worker.ROOT)
        spec = worker.read(worker.ROOT/worker.CONFIG)
        totals = worker.validate_loaded(loaded, spec)
        self.assertEqual(totals['local_capture_presentations'], 88742)
        self.assertEqual(totals['scoring_presentations'], 177484)
        changed = deepcopy(loaded)
        changed['fits']['leave_chi_out']['weights'][0]['training_multiplier'] *= 2
        with self.assertRaises(ValueError):
            worker.validate_loaded(changed, spec)


if __name__ == '__main__':
    unittest.main()

"""Bounded metadata/adversarial checks; no model construction or GPU calls."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import candidate_producer_transfer_experiment as worker


def fixture(additions=3):
    training = {}
    for index in range(36 + additions):
        prefix = 'cosine_current' if index < 36 else 'alternate_added'
        cid = f'candidate_{index}'
        key = prefix + '|' + cid
        training[key] = {'candidate_id': cid, 'training_row_key': key, 'domain': 'nba', 'game_id': 'fit_game',
                         'target': index % 2, 'target_group': 'positive' if index % 2 else 'eligible_distant_miss'}
    training['unknown'] = {'candidate_id': 'unknown', 'domain': 'nba', 'game_id': 'fit_game', 'target': None}
    training['held'] = {'candidate_id': 'held', 'domain': 'nba', 'game_id': 'held_game', 'target': 1}
    keys = [key for key in training if key not in ('unknown', 'held')]
    weights = [{'candidate_id': training[key]['candidate_id'], 'training_row_key': key,
                'objective_weight': 1/len(keys), 'training_multiplier': 1.0} for key in keys]
    plan = {'fit': 'example', 'fit_games': ['fit_game'], 'augmented_known_candidates': len(keys),
            'original_known_candidates': 36, 'batch_sizes_per_round': [32, 4],
            'optimizer_updates': 12, 'training_presentations': 216}
    schedules = []
    for number in range(1, 7):
        order = list(keys)
        random.Random(worker.SEED + number).shuffle(order)
        schedules.append({'fit': 'example', 'round': number, 'seed': worker.SEED + number,
                          'population': len(keys), 'quota': 36, 'training_row_keys': order[:36], 'batch_sizes': [32, 4]})
    return plan, weights, schedules, training


def authorization():
    return {'execution_approved': True, 'execution_freeze': {'sha256': 'freeze'},
            'specification': {'sha256': 'spec'}, 'scope': dict(worker.COUNTS), 'max_total_seconds': 5400,
            'user_statement': 'Move forward with implementing and running this experiment.',
            **dict.fromkeys(('automatic_retry', 'automatic_extension', 'protected_access_approved',
                            'new_labels_approved', 'selector_approved'), False)}


class MetadataScheduleTests(unittest.TestCase):
    def test_import_is_metadata_only(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            'import sys; from src.ball_tracking import candidate_producer_transfer_experiment; '
            'assert not any(x in sys.modules for x in ("torch", "numpy", "PIL", "transformers")); print("metadata-only")'],
            cwd=worker.ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'metadata-only')

    def test_zero_addition_specializes_to_original_six_full_shuffles(self):
        plan, weights, schedules, training = fixture(0)
        visits = worker.validate_fit_schedule(plan, weights, schedules, training)
        self.assertEqual(set(visits.values()), {6})
        for cycle, schedule in enumerate(schedules, 1):
            old = [w['training_row_key'] for w in weights]
            random.Random(worker.SEED + cycle).shuffle(old)
            self.assertEqual(schedule['training_row_keys'], old)
        self.assertEqual(sum(visits.values()), 216)

    def test_added_prefix_preserves_budget_tail_and_visits_all_members(self):
        plan, weights, schedules, training = fixture()
        visits = worker.validate_fit_schedule(plan, weights, schedules, training)
        self.assertEqual(sum(visits.values()), 216)
        self.assertEqual(len(visits), 39)
        self.assertGreaterEqual(min(visits.values()), 1)
        self.assertNotIn('unknown', visits)
        self.assertNotIn('held', visits)
        self.assertTrue(all(s['batch_sizes'] == [32, 4] for s in schedules))

    def test_unknown_held_reorder_reseed_tail_and_multiplier_are_rejected(self):
        for mutation in ('unknown', 'held', 'reorder', 'seed', 'tail', 'old_N_scale', 'duplicate', 'drop_cycle'):
            plan, weights, schedules, training = fixture()
            if mutation in ('unknown', 'held'):
                weights[0]['training_row_key'] = mutation
            elif mutation == 'reorder':
                schedules[0]['training_row_keys'][0:2] = schedules[0]['training_row_keys'][1::-1]
            elif mutation == 'seed':
                schedules[0]['seed'] += 1
            elif mutation == 'tail':
                schedules[0]['batch_sizes'] = [32, 7]
            elif mutation == 'old_N_scale':
                weights[0]['training_multiplier'] = 36/39
            elif mutation == 'duplicate':
                weights[1] = dict(weights[0])
            else:
                schedules.pop()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                worker.validate_fit_schedule(plan, weights, schedules, training)

    def test_saved_real_design_membership_schedules_and_exact_budget(self):
        design = worker.ROOT / 'data/outputs/ball_tracking/candidate_producer_transfer_design_v0_1'
        workload = worker.read(design / 'feasibility/workload.json')
        union = worker.rows(design / 'population/union_candidates.jsonl')
        loaded = {'training_rows': {r['training_row_key']: r for r in union},
                  'union_candidates': {r['candidate_id']: r for r in union}, 'fits': {},
                  'scoring_plan': worker.read(design / 'feasibility/scoring_plan.json')}
        for plan in workload['plans']:
            loaded['fits'][plan['fit']] = {'plan': plan, 'weights': worker.rows(worker.ROOT / plan['weights']['path']),
                'schedules': [worker.read(worker.ROOT / item['schedule']['path']) for item in plan['round_details']]}
        worker.validate_loaded(loaded)
        self.assertEqual(workload['counts'], worker.COUNTS)
        self.assertEqual([p['plan']['batch_sizes_per_round'][-1] for p in loaded['fits'].values()], [18, 8, 14, 20])
        external = [g for g in loaded['scoring_plan'] if g['population'] == 'original_external_registry']
        self.assertEqual(len(external), 1)
        self.assertEqual((external[0]['scores'], external[0]['forwards'], len(external[0]['missing_query_ids'])), (11787, 369, 11))
        self.assertNotIn('torch', sys.modules)


class OutputAndGuardTests(unittest.TestCase):
    def test_raw_score_transport_preserves_ties_sign_and_identity(self):
        group = {'fit': 'leave_chi_out', 'owner': 'new_treatment', 'population': 'original_held_NBA', 'id_field': 'candidate_id'}
        actual = worker.score_rows(group, ['a', 'b', 'c'], [0.0, -2.0, 2.0])
        self.assertEqual([r['candidate_id'] for r in actual], ['a', 'b', 'c'])
        self.assertEqual([r['quality_logit'] for r in actual], [0.0, -2.0, 2.0])
        self.assertTrue(all(set(r) == {'candidate_id', 'quality_logit', 'fit', 'owner', 'population'} for r in actual))
        for invalid in ([float('nan')], [float('inf')], [], [True]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                worker.score_rows(group, ['a'], invalid)

    def test_call_attempt_is_durable_and_excess_call_cannot_start(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'journal.jsonl'
            counters = dict.fromkeys(worker.COUNTER_EXPECTED, 0)
            worker.call_started(counters, 'training', path, {'training_row_keys': ['new|x'], 'batch_count': 1})
            event = worker.rows(path)[0]
            self.assertEqual(event['event'], 'training_start')
            self.assertEqual(event['training_row_keys'], ['new|x'])
            self.assertEqual(event['counters']['training_forwards_attempted'], 1)
            self.assertEqual(event['counters']['training_forwards_returned'], 0)
            counters['training_forwards_attempted'] = worker.COUNTER_EXPECTED['training_forwards_attempted']
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'budget'):
                worker.call_started(counters, 'training', path, {})
            self.assertEqual(before, path.read_bytes())

    def test_exact_accounting_rejects_extra_partial_and_missing_calls(self):
        worker.validate_counters(dict(worker.COUNTER_EXPECTED))
        for key in worker.COUNTER_EXPECTED:
            for delta in (-1, 1):
                bad = dict(worker.COUNTER_EXPECTED)
                bad[key] += delta
                with self.subTest(key=key, delta=delta), self.assertRaises(ValueError):
                    worker.validate_counters(bad)

    def test_authorization_requires_current_fixed_scope_and_no_expansion(self):
        item = authorization()
        worker.validate_authorization(item, {'sha256': 'freeze'}, {'sha256': 'spec'})
        for key, value in (('execution_approved', False), ('execution_freeze', {}), ('specification', {}),
                           ('user_statement', ''), ('automatic_retry', True), ('selector_approved', True),
                           ('max_total_seconds', 5401), ('new_labels_approved', True)):
            bad = deepcopy(item)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                worker.validate_authorization(bad, {'sha256': 'freeze'}, {'sha256': 'spec'})
        item['scope']['scoring_forwards'] += 1
        with self.assertRaises(ValueError):
            worker.validate_authorization(item, {'sha256': 'freeze'}, {'sha256': 'spec'})

    def test_owned_policy_deadline_and_fixed_cli_checked_before_preflight(self):
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        policy = {'module': worker.MODULE, 'arguments': ['--run', '--monitor', worker.MONITOR],
                  'sample_seconds': 2, 'temperature_stop_C': 80, 'telemetry_timeout_seconds': 5,
                  'grace_seconds': 10, 'automatic_retry': False, 'max_total_seconds': 5400,
                  'soft_stop_seconds': 5370, 'gpu_uuid': worker.GPU, 'created_at_utc': now.isoformat()}
        worker.validate_policy(policy)
        self.assertEqual(worker.remaining_wall_seconds(policy, now+timedelta(seconds=5369)), 31)
        with self.assertRaises(ValueError):
            worker.remaining_wall_seconds(policy, now+timedelta(seconds=5370))
        policy['arguments'] = ['--run']
        with self.assertRaises(ValueError):
            worker.validate_policy(policy)
        with patch.object(worker, 'preflight') as preflight:
            with self.assertRaisesRegex(ValueError, 'declared owned'):
                worker.run(worker.ROOT, 'old-monitor', ['--run', '--monitor', 'old-monitor'])
            preflight.assert_not_called()


if __name__ == '__main__':
    unittest.main()

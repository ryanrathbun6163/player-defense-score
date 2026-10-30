"""Single-retry operational guards and captured checkpoint transport, CPU only."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.ball_tracking import candidate_quality_retry_resume as recovery

ROOT = Path(__file__).resolve().parents[1]


class CandidateQualityRetryResumeTests(unittest.TestCase):
    def test_metadata_import_does_not_import_torch(self):
        code = "import sys; from src.ball_tracking import candidate_quality_retry_resume; assert 'torch' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_attempt_specific_approval_preserves_user_limit(self):
        old = recovery.read(ROOT / recovery.OUTPUT / 'post_driver_recovery_preparation_v0_1/execution_approval.json')
        frozen = {'path': 'retry/execution_freeze.json', 'bytes': 17, 'sha256': 'new-binding'}
        freeze = {'original_execution_approval': old['original_execution_approval']}
        approved = dict(old, execution_freeze=frozen, remaining_seconds=2437, attempt='attempt_004')
        recovery.validate_execution_approval(approved, frozen, freeze)
        for bad in (old, dict(approved, remaining_seconds=2946), dict(approved, attempt='attempt_003'),
                    dict(approved, automatic_retry=True), dict(approved, resume_approved=False),
                    dict(approved, selector_approved=True), dict(approved, protected_access_approved=True),
                    dict(approved, new_labels_approved=True), dict(approved, user_statement='')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                recovery.validate_execution_approval(bad, frozen, freeze)

    def test_actual_journals_support_separate_logical_and_physical_counts(self):
        counts = []
        presentations = 0
        starts = 0
        for relative in [recovery.OUTPUT + '/attempt_001/journal.jsonl',
                         recovery.OUTPUT + '/attempt_002/journal.jsonl',
                         recovery.OUTPUT + '/attempt_003/journal.jsonl',
                         'data/outputs/t/reference_clock_test_v0_1/attempt_001/journal.jsonl']:
            journal = recovery.rows(ROOT / relative)
            started = [row for row in journal if row['event'] == 'train_start']
            returned = [row for row in journal if row['event'] == 'train_return']
            counts.append(len(returned)); starts += len(started)
            presentations += sum(row['batch_count'] for row in started[:len(returned)])
        zero = dict.fromkeys(recovery.RECOVERED_COUNTERS, 0)
        got = recovery.accounting(zero)
        self.assertEqual(counts, [461, 587, 1015, 441])
        self.assertEqual(got['logical']['optimizer_updates'], 1496)
        self.assertEqual(got['logical']['training_candidate_presentations'], 47816)
        self.assertEqual(got['cumulative_physical_lower_bound']['optimizer_updates'], sum(counts))
        self.assertEqual(got['cumulative_physical_lower_bound']['training_forwards_attempted'], starts)
        self.assertEqual(got['cumulative_physical_lower_bound']['training_candidate_presentations'], presentations)
        self.assertEqual(got['prior_recorded_unsaved']['updates'], 567)
        self.assertEqual(got['separate_reference_clock_diagnostic']['returned_updates'], 441)
        full = dict(zero, training_forwards_attempted=8374, training_forwards_returned=8374,
                    optimizer_updates=8374, training_candidate_presentations=267616)
        complete = recovery.accounting(full)
        self.assertEqual(complete['logical']['optimizer_updates'], 9870)
        self.assertEqual(complete['logical']['training_candidate_presentations'], 315432)
        self.assertEqual(complete['cumulative_physical_lower_bound']['optimizer_updates'], 10878)
        self.assertEqual(complete['cumulative_physical_lower_bound']['training_candidate_presentations'], 347674)

    def test_attempt_directories_cannot_overwrite_previous_work(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            for number in range(1, 4):
                prior = out / f'attempt_{number:03d}'
                prior.mkdir(); (prior / 'evidence').write_bytes(b'preserved')
            new = recovery.make_attempt_directory(out)
            self.assertEqual(new.name, 'attempt_004')
            with self.assertRaises(FileExistsError):
                recovery.make_attempt_directory(out)
            self.assertTrue(all((out / f'attempt_{n:03d}/evidence').read_bytes() == b'preserved' for n in range(1, 4)))

    def test_budget_starts_at_supervisor_policy_and_reserves_cleanup(self):
        began = datetime(2026, 10, 29, tzinfo=timezone.utc)
        policy = {'created_at_utc': began.isoformat()}
        got = recovery.remaining_wall_seconds(policy, began + timedelta(seconds=100))
        self.assertEqual(got['remaining_seconds'], 2337)
        self.assertEqual(got['stop_wait_seconds'], 2307)
        self.assertEqual(got['prior_debit_seconds'], 1163)
        for delta in (-3, 2407, 2437, 3600):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                recovery.remaining_wall_seconds(policy, began + timedelta(seconds=delta))

    def test_actual_epoch_four_checkpoint_restore_and_rejections_on_cpu(self):
        # Reuse the independent transport test body from the frozen prior consumer,
        # but point it at the actual newer producer payload and this consumer.
        # No invented checkpoint, neural model, neural forward or CUDA call.
        import ast
        prior_source = (ROOT / 'tests/test_candidate_quality_post_driver_resume.py').read_text(encoding='utf-8')
        tree = ast.parse(prior_source)
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                      and node.name == 'test_captured_payload_restore_and_rejection_contract_on_cpu')
        code = next(node.value.value for node in method.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'code' for target in node.targets))
        code = code.replace('candidate_quality_post_driver_resume as r', 'candidate_quality_retry_resume as r')
        code = code.replace("base / 'post_driver_recovery_preparation_v0_1/checkpoint_audit.json'",
                            "root / r.PREPARATION / 'checkpoint_audit/checkpoint_audit.json'")
        code = code.replace("base / 'attempt_002/", "base / 'attempt_003/")
        code = code.replace("('epoch',1)", "('epoch',2)")
        code = code.replace("('fit_steps',747)", "('fit_steps',1495)")
        code = code.replace("dict(payload['new_attempt_counters'],optimizer_updates=748)",
                            "dict(payload['new_attempt_counters'],optimizer_updates=1496)")
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(report['restored_trainable_tensors'], 42)
        self.assertEqual(report['restored_optimizer_states'], 42)
        self.assertFalse(report['cuda_initialized'])


if __name__ == '__main__':
    unittest.main()

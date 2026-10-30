"""CPU actual-checkpoint restoration and replay accounting; no encoder/model call."""
from copy import deepcopy
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest
import zipfile

from src.ball_tracking import dual_view_context_resume as recovery


class RecoveryMetadataTests(unittest.TestCase):
    def test_metadata_import_never_loads_torch(self):
        run = subprocess.run([sys.executable, '-B', '-c',
            'import sys; from src.ball_tracking import dual_view_context_resume; '
            'assert not any(n in sys.modules for n in ("torch","numpy","PIL","transformers"))'],
            cwd=recovery.ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_exact_replay_prefix_all_full_batches_and_combined_physical_budget(self):
        root = recovery.ROOT
        manifest = recovery.read(root/recovery.PRIOR_OUTPUT/'fits/leave_sac_out/LC/fit_manifest.json')
        records = recovery.replay_records(root, manifest['weights'])
        self.assertEqual(list(records), list(range(1051, 1118)))
        self.assertEqual({r['batch_count'] for r in records.values()}, {32})
        self.assertEqual(sum(r['batch_count'] for r in records.values()), 2144)
        failed = recovery.read(root/recovery.PRIOR_FAILED)['counters']
        self.assertEqual({k: failed[k]+recovery.COUNTER_EXPECTED[k] for k in failed}, recovery.PHYSICAL_EXPECTED)
        self.assertEqual(sum(c for c, _ in recovery.CALL_BUDGETS.values()), 10382)
        self.assertEqual(sum(p for _, p in recovery.CALL_BUDGETS.values()), 331930)
        self.assertEqual(sum(recovery.PHYSICAL_EXPECTED[k+'_forwards_returned'] for k in recovery.CALL_BUDGETS), 28149)
        self.assertEqual(sum(recovery.PHYSICAL_EXPECTED[k+'_candidate_presentations'] for k in recovery.CALL_BUDGETS), 899618)
        self.assertEqual(recovery.PHYSICAL_EXPECTED['optimizer_updates'], 19807)
        self.assertEqual(recovery.MAX_TOTAL_SECONDS+recovery.PRIOR_CHARGED_SECONDS, 5400)
        self.assertEqual([len(b) for b in recovery.prior.batches(recovery.prior.epoch_order(manifest['weights'], 4))][-1], 14)
        bad = deepcopy(manifest['weights'])
        bad[0], bad[1] = bad[1], bad[0]
        with self.assertRaises(ValueError):
            recovery.replay_records(root, bad)


class ActualCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        import torch
        cls.torch = torch
        torch.set_num_threads(2)
        assert not torch.cuda.is_initialized()
        path = recovery.ROOT/recovery.CHECKPOINT
        actual = recovery.binding(recovery.ROOT, path)
        assert actual == {'path': recovery.CHECKPOINT, 'bytes': recovery.CHECKPOINT_BYTES, 'sha256': recovery.CHECKPOINT_SHA256}
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
        cls.checkpoint = torch.load(path, map_location='cpu', weights_only=False)
        cls.weights = recovery.read(recovery.ROOT/recovery.PRIOR_OUTPUT/'fits/leave_sac_out/LC/fit_manifest.json')['weights']

    def tearDown(self):
        self.assertFalse(self.torch.cuda.is_initialized())

    def test_actual_endpoint_optimizer_moments_and_RNG_payloads(self):
        result = recovery.validate_recovery_checkpoint(self.checkpoint, self.weights)
        self.assertEqual(result['fit_steps'], 1050)
        self.assertEqual(result['trainable_parameters'], 3698945)
        self.assertEqual(result['visits_each'], 3)
        self.assertGreater(result['CPU_Torch_rng_bytes'], 0)
        self.assertEqual(len(result['CUDA_rng_bytes']), 1)
        for key, value in (('epoch', 4), ('fit_steps', 1117), ('arm', 'LL'), ('freeze_sha256', 'changed')):
            modified = dict(self.checkpoint)
            modified[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                recovery.validate_recovery_checkpoint(modified, self.weights)

    def test_actual_parameter_and_AdamW_roundtrip_no_forward_or_step(self):
        torch = self.torch
        state = self.checkpoint['trainable_state']

        class ParameterCarrier(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.names = list(state)
                self.values = torch.nn.ParameterList([torch.nn.Parameter(torch.zeros_like(v)) for v in state.values()])

            def named_parameters(self, *args, **kwargs):
                return iter(zip(self.names, self.values))

        carrier = ParameterCarrier()
        groups = [{'params': [p for n, p in carrier.named_parameters() if n.startswith(prefix)], 'lr': lr, 'weight_decay': .01}
                  for prefix, lr in (('backbone.', 1e-5), ('head.', 1e-3))]
        optimizer = torch.optim.AdamW(groups, betas=(.9, .999), eps=1e-8)
        receipt = recovery.restore_recovery(carrier, optimizer, self.checkpoint, self.weights, restore_rng=False)
        self.assertTrue(receipt['trainable_and_optimizer_roundtrip_exact'])
        self.assertFalse(receipt['RNG_restored_to_runtime'])
        self.assertTrue(all(torch.equal(p, state[n]) for n, p in carrier.named_parameters()))
        self.assertTrue(all(p.grad is None for p in carrier.parameters()))
        self.assertEqual({float(s['step']) for s in optimizer.state.values()}, {1050.})

    def test_CPU_RNG_restores_exactly_and_CUDA_payload_stays_uninitialized(self):
        import numpy as np
        torch = self.torch
        saved_python, saved_numpy, saved_torch = random.getstate(), np.random.get_state(), torch.get_rng_state()
        try:
            def probe():
                random.setstate(self.checkpoint['python_rng'])
                np.random.set_state(self.checkpoint['numpy_rng'])
                torch.set_rng_state(self.checkpoint['torch_rng'])
                self.assertTrue(torch.equal(torch.get_rng_state(), self.checkpoint['torch_rng']))
                return [random.random() for _ in range(4)], np.random.random(4), torch.rand(4)
            first, second = probe(), probe()
            self.assertEqual(first[0], second[0])
            np.testing.assert_array_equal(first[1], second[1])
            self.assertTrue(torch.equal(first[2], second[2]))
            self.assertFalse(torch.cuda.is_initialized())
        finally:
            random.setstate(saved_python)
            np.random.set_state(saved_numpy)
            torch.set_rng_state(saved_torch)


if __name__ == '__main__':
    unittest.main()

"""Recovery-consumer tests; no neural model, forward, CUDA or training step.

The restore test uses the trusted, already-audited emitted checkpoint rather
than a fixture that invents the optimizer/RNG transport schema. CUDA RNG setter
dispatch is mocked; actual GPU restoration remains a supervised runtime check.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import candidate_quality_pilot as original
from src.ball_tracking import candidate_quality_post_driver_resume as recovery

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / original.OUTPUT


class CandidateQualityPostDriverResumeTests(unittest.TestCase):
    def test_metadata_import_does_not_import_torch(self):
        code = "import sys; from src.ball_tracking import candidate_quality_post_driver_resume; assert 'torch' not in sys.modules"
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_specific_execution_approval_cannot_be_inferred_from_preparation(self):
        # Start with the emitted prior approval, retaining its real transport fields.
        path = BASE / "recovery_preparation_v0_1/execution_approval.json"
        if not path.exists():
            self.skipTest("Requires recorded prior approval")
        old = original.read(path)
        freeze = {"original_execution_approval": old["original_execution_approval"]}
        new_binding = {"path": "new/execution_freeze.json", "bytes": 17, "sha256": "frozen-new"}
        approved = dict(old, execution_freeze=new_binding, remaining_seconds=2946,
                        attempt="attempt_003", driver_version="617.42", automatic_retry=False)
        recovery.validate_execution_approval(approved, new_binding, freeze)
        for bad in ({}, old, dict(approved, resume_approved=False), dict(approved, remaining_seconds=3126),
                    dict(approved, attempt="attempt_002"), dict(approved, driver_version="616.56"),
                    dict(approved, automatic_retry=True), dict(approved, selector_approved=True),
                    dict(approved, user_statement=""), dict(approved, execution_freeze=old["execution_freeze"])):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                recovery.validate_execution_approval(bad, new_binding, freeze)

    def test_launch_driver_query_rejects_changed_or_missing_device_without_gpu_access(self):
        identity = "captured-device-id"
        good = subprocess.CompletedProcess([], 0, identity + ", 617.42\n", "")
        with patch.object(recovery.subprocess, "run", return_value=good) as query:
            got = recovery.verify_runtime_driver(identity)
        self.assertEqual(got["driver_version"], "617.42")
        self.assertEqual(query.call_args.kwargs["timeout"], 5)
        for bad in (subprocess.CompletedProcess([], 1, "", "lost"),
                    subprocess.CompletedProcess([], 0, identity + ", 616.56\n", ""),
                    subprocess.CompletedProcess([], 0, "other, 617.42\n", ""),
                    subprocess.CompletedProcess([], 0, identity + ", 617.42\nextra\n", "")):
            with self.subTest(bad=bad), patch.object(recovery.subprocess, "run", return_value=bad), self.assertRaises(ValueError):
                recovery.verify_runtime_driver(identity)

    def test_preflight_without_execution_approval_uses_actual_captured_metadata(self):
        if not (BASE / "post_driver_recovery_preparation_v0_1/checkpoint_audit.json").exists():
            self.skipTest("Requires recorded epoch-two audit")
        code = r'''
import json,sys
from pathlib import Path
from unittest.mock import patch
from src.ball_tracking import candidate_quality_post_driver_resume as r
root=Path.cwd(); base=root/r.OUTPUT; prepare=base/r.PREPARATION
old=r.read(base/'recovery_preparation_v0_1/execution_freeze.json')
origin=r.read(base/'interruption_v0_1/partial_audit.json')
freeze={key:old[key] for key in ('original_execution_freeze','original_execution_approval',
 'prior_initial_fingerprints','prior_producer_parity','prior_gradient_checks')}
freeze.update(schema_version='candidate_quality_post_driver_recovery/v0.1',remaining_seconds=2946,
 prior_budget_debit_seconds=654,cleanup_reserve_seconds=30,
 previous_recovery_freeze=r.binding(root,base/'recovery_preparation_v0_1/execution_freeze.json'),
 previous_recovery_approval=r.binding(root,base/'recovery_preparation_v0_1/execution_approval.json'),
 checkpoint=r.binding(root,root/r.CHECKPOINT_PATH),
 checkpoint_audit=r.binding(root,prepare/'checkpoint_audit.json'),
 interruption_audit=r.binding(root,base/'recovery_preparation_v0_1/interruption_audit.json'),
 post_install_snapshot=r.binding(root,base/'studio_61742_install_v0_1/post_install_snapshot.json'),
 bindings=[r.binding(root,Path(r.__file__).resolve())])
actual_read=r.read
def read(path):
    if path == prepare/'execution_freeze.json': return freeze
    if path == prepare/'execution_approval.json': raise FileNotFoundError('No current execution approval')
    return actual_read(path)
with patch.object(r.previous,'preflight',return_value=({},old,origin)),patch.object(r,'read',side_effect=read):
    r.preflight(root,require_approval=False)
    try:r.preflight(root,require_approval=True)
    except FileNotFoundError:pass
    else:raise AssertionError('Missing post-driver approval was accepted')
assert 'torch' not in sys.modules
print(json.dumps({'status':'metadata_only_missing_approval_rejected'}))
'''
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_recovered_counters_match_actual_producer_audit(self):
        path = BASE / "post_driver_recovery_preparation_v0_1/checkpoint_audit.json"
        if not path.exists():
            self.skipTest("Requires accepted interrupted-run metadata")
        audit = original.read(path)
        recovered = recovery.RECOVERED_COUNTERS
        prior = recovery.PRIOR_PHYSICAL_COUNTERS
        partial = original.read(BASE / "recovery_preparation_v0_1/interruption_audit.json")
        self.assertEqual(recovered, audit["saved_logical_counters"])
        self.assertEqual(recovery.CHECKPOINT_ATTEMPT_COUNTERS, audit["saved_attempt_002_local_counters"])
        self.assertEqual(prior["optimizer_updates"], partial["cumulative_physical_lower_bound"]["training_updates_returned"])
        self.assertEqual(prior["training_candidate_presentations"], partial["cumulative_physical_lower_bound"]["training_candidate_presentations"])
        self.assertEqual(prior["parity_forwards_returned"], 1)
        self.assertEqual(recovered["parity_candidate_presentations"], 32)

    def test_full_completion_distinguishes_logical_and_physical_replay(self):
        new = dict.fromkeys(recovery.RECOVERED_COUNTERS, 0)
        new.update(optimizer_updates=9122, training_forwards_attempted=9122,
                   training_forwards_returned=9122, training_candidate_presentations=291524,
                   scoring_forwards_attempted=1572, scoring_forwards_returned=1572,
                   scoring_candidate_presentations=50232, parity_forwards_attempted=3,
                   parity_forwards_returned=3, parity_candidate_presentations=96)
        result = recovery.accounting(new)
        self.assertEqual(result["logical"]["optimizer_updates"], 9870)
        self.assertEqual(result["logical"]["training_candidate_presentations"], 315432)
        self.assertEqual(result["logical"]["parity_forwards_returned"], 4)
        self.assertEqual(result["logical"]["parity_candidate_presentations"], 128)
        self.assertEqual(result["cumulative_physical_lower_bound"]["optimizer_updates"], 10170)
        self.assertEqual(result["cumulative_physical_lower_bound"]["training_candidate_presentations"], 325032)
        self.assertEqual(result["prior_recorded_unsaved"], {"updates": 300, "training_candidate_presentations": 9600})
        self.assertEqual(result["prior_recorded_unsaved_by_attempt"]["attempt_002"]["updates"], 213)

    def test_new_attempt_cannot_overwrite_old_or_existing_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            old = out / "attempt_001"
            old.mkdir()
            (old / "evidence").write_bytes(b"original interruption")
            second = out / "attempt_002"
            second.mkdir()
            (second / "evidence").write_bytes(b"driver-loss interruption")
            created = recovery.make_attempt_directory(out)
            self.assertEqual(created, out / "attempt_003")
            self.assertEqual((old / "evidence").read_bytes(), b"original interruption")
            self.assertEqual((second / "evidence").read_bytes(), b"driver-loss interruption")
            with self.assertRaises((ValueError, FileExistsError)):
                recovery.make_attempt_directory(out)
            self.assertEqual((old / "evidence").read_bytes(), b"original interruption")

    def test_policy_clock_debits_startup_and_reserves_cleanup(self):
        start = datetime(2026, 10, 28, 23, 0, tzinfo=timezone.utc)
        policy = {"created_at_utc": start.isoformat()}
        got = recovery.remaining_wall_seconds(policy, start + timedelta(seconds=100))
        self.assertEqual(got["remaining_seconds"], 2846)
        self.assertEqual(got["stop_wait_seconds"], 2816)
        self.assertEqual(got["cleanup_reserve_seconds"], 30)
        # The budget is measured from supervisor policy, never worker entry.
        self.assertNotEqual(got["remaining_seconds"], 2946)
        for now in (start - timedelta(seconds=3), start + timedelta(seconds=2946),
                    start + timedelta(seconds=3600)):
            with self.subTest(now=now), self.assertRaises(ValueError):
                recovery.remaining_wall_seconds(policy, now)

    def test_captured_payload_restore_and_rejection_contract_on_cpu(self):
        audit_path = BASE / "post_driver_recovery_preparation_v0_1/checkpoint_audit.json"
        if not audit_path.exists():
            self.skipTest("Requires the authorized captured recovery checkpoint")
        # Isolate Torch and environment to this child; no parent CUDA mutation.
        code = r'''
import copy, json, os, random, sys
from pathlib import Path
from unittest.mock import patch
root = Path.cwd()
from src.ball_tracking import candidate_quality_pilot as p
from src.ball_tracking import candidate_quality_post_driver_resume as r
assert 'torch' not in sys.modules
assert os.environ['CUDA_VISIBLE_DEVICES'] == '-1'
base = root / p.OUTPUT
audit = p.read(base / 'post_driver_recovery_preparation_v0_1/checkpoint_audit.json')
checkpoint = p.bound(root, audit['checkpoint'])
started = p.read(base / 'attempt_002/started.json')
freeze_sha = started['original_execution_freeze']['sha256']
captured = p.read(base / 'attempt_002/leave_chi_out/trainable_parameters.json')
shapes = {row['name']: tuple(row['shape']) for row in captured}
import numpy as np
import torch
torch.set_num_threads(2)
assert not torch.cuda.is_initialized()
payload = torch.load(checkpoint, map_location='cpu', weights_only=False)
assert not torch.cuda.is_initialized()
r.validate_checkpoint_payload(payload, freeze_sha, shapes)

# Rejection checks use exact captured schema and alter one contract at a time.
for field, bad in [('fit','all_nba'), ('epoch',1), ('fit_steps',747), ('freeze_sha256','wrong')]:
    changed = dict(payload, **{field:bad})
    try: r.validate_checkpoint_payload(changed, freeze_sha, shapes)
    except ValueError: pass
    else: raise AssertionError('Accepted altered '+field)
try: r.validate_checkpoint_payload(payload, 'wrong-expected-freeze', shapes)
except ValueError: pass
else: raise AssertionError('Accepted wrong expected freeze')
changed = dict(payload, counters=dict(payload['counters'], optimizer_updates=1048))
try: r.validate_checkpoint_payload(changed, freeze_sha, shapes)
except ValueError: pass
else: raise AssertionError('Accepted durable physical count as recovered count')
for field,bad in [('recovery_freeze',dict(payload['recovery_freeze'],sha256='wrong')),
                  ('new_attempt_counters',dict(payload['new_attempt_counters'],optimizer_updates=748)),
                  ('accounting',dict(payload['accounting'],logical=payload['new_attempt_counters']))]:
    try: r.validate_checkpoint_payload(dict(payload,**{field:bad}),freeze_sha,shapes)
    except ValueError: pass
    else: raise AssertionError('Accepted altered producer '+field)
state = dict(payload['trainable_state'])
name = next(iter(state))
state[name] = state[name].double()
try: r.validate_checkpoint_payload(dict(payload, trainable_state=state), freeze_sha, shapes)
except ValueError: pass
else: raise AssertionError('Accepted altered dtype')
state = dict(payload['trainable_state'])
state[name] = state[name].unsqueeze(0)
try: r.validate_checkpoint_payload(dict(payload, trainable_state=state), freeze_sha, shapes)
except ValueError: pass
else: raise AssertionError('Accepted altered trainable shape')
state = dict(payload['trainable_state'])
state.pop(name)
try: r.validate_checkpoint_payload(dict(payload, trainable_state=state), freeze_sha, shapes)
except ValueError: pass
else: raise AssertionError('Accepted missing trainable tensor')
optimizer_bad = copy.deepcopy(payload['optimizer_state'])
optimizer_bad['param_groups'][0]['lr'] = .5
try: r.validate_checkpoint_payload(dict(payload, optimizer_state=optimizer_bad), freeze_sha, shapes)
except ValueError: pass
else: raise AssertionError('Accepted changed optimizer recipe')
optimizer_bad = copy.deepcopy(payload['optimizer_state'])
first_state = next(iter(optimizer_bad['state'].values()))
first_state['exp_avg'].view(-1)[0] = float('nan')
try: r.validate_checkpoint_payload(dict(payload, optimizer_state=optimizer_bad), freeze_sha, shapes)
except ValueError: pass
else: raise AssertionError('Accepted nonfinite optimizer moment')
optimizer_bad = copy.deepcopy(payload['optimizer_state'])
optimizer_bad['param_groups'][0]['params'][0],optimizer_bad['param_groups'][0]['params'][1] = (
    optimizer_bad['param_groups'][0]['params'][1],optimizer_bad['param_groups'][0]['params'][0])
try: r.validate_checkpoint_payload(dict(payload,optimizer_state=optimizer_bad),freeze_sha,shapes)
except ValueError: pass
else: raise AssertionError('Accepted reordered saved optimizer parameters')

# A named tensor container is not a neural model and has no forward method.
class ParameterBag:
    def __init__(self):
        self.values = {row['name']: torch.nn.Parameter(torch.zeros(row['shape'])) for row in captured}
        self.values['backbone.embeddings.cls_token'] = torch.nn.Parameter(torch.tensor([17.]), requires_grad=False)
    def named_parameters(self): return iter(self.values.items())
    def parameters(self): return iter(self.values.values())
model = ParameterBag()
groups = [{'params':[v for n,v in model.named_parameters() if v.requires_grad and n.startswith(prefix)],
           'lr':lr,'weight_decay':.01} for prefix,lr in [('backbone.',1e-5),('head.',1e-3)]]
optimizer = torch.optim.AdamW(groups, betas=(.9,.999),eps=1e-8)

# Compute expected next CPU RNG outputs independently from captured states.
py_expected = random.Random(); py_expected.setstate(payload['python_rng'])
np_expected = np.random.RandomState(); np_expected.set_state(payload['numpy_rng'])
torch_expected = torch.Generator(device='cpu'); torch_expected.set_state(payload['torch_rng'])
expected_draws = (py_expected.random(), np_expected.random_sample(4), torch.rand(4,generator=torch_expected))
random.seed(1); np.random.seed(1); torch.set_rng_state(torch.Generator().manual_seed(1).get_state())
cuda_calls = []
with patch.object(torch.cuda, 'set_rng_state_all', side_effect=lambda states: cuda_calls.append([s.clone() for s in states])):
    r.restore_checkpoint(model, optimizer, payload, freeze_sha, shapes)
for name, saved in payload['trainable_state'].items():
    assert torch.equal(model.values[name], saved), name
assert model.values['backbone.embeddings.cls_token'].item() == 17.
assert len(cuda_calls)==1 and len(cuda_calls[0])==len(payload['cuda_rng'])
assert all(torch.equal(a,b) for a,b in zip(cuda_calls[0],payload['cuda_rng']))
assert random.random()==expected_draws[0]
assert np.array_equal(np.random.random_sample(4),expected_draws[1])
assert torch.equal(torch.rand(4),expected_draws[2])
actual = optimizer.state_dict()
assert actual['param_groups']==payload['optimizer_state']['param_groups']
for key, state in actual['state'].items():
    assert set(state)==set(payload['optimizer_state']['state'][key])
    for field,value in state.items():
        assert torch.equal(value,payload['optimizer_state']['state'][key][field]), (key,field)
# Same-shape parameters cannot silently exchange live optimizer positions.
optimizer.param_groups[0]['params'][0], optimizer.param_groups[0]['params'][1] = (
    optimizer.param_groups[0]['params'][1], optimizer.param_groups[0]['params'][0])
try: r.restore_checkpoint(model, optimizer, payload, freeze_sha, shapes)
except ValueError: pass
else: raise AssertionError('Accepted reordered live optimizer parameters')
assert not torch.cuda.is_initialized()
assert 'transformers' not in sys.modules
print(json.dumps({'status':'passed_CPU_restore_contract_no_model_forward','restored_trainable_tensors':len(captured),
                  'restored_optimizer_states':len(actual['state']), 'cuda_initialized':False,'new_training_updates':0}))
'''
        env = dict(os.environ, CUDA_VISIBLE_DEVICES="-1", PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(report["restored_trainable_tensors"], 42)
        self.assertEqual(report["restored_optimizer_states"], 42)
        self.assertFalse(report["cuda_initialized"])


if __name__ == "__main__":
    unittest.main()

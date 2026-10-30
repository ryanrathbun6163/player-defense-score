"""Actual producer transport and fixed continuation boundaries; CPU only."""
import ast
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.ball_tracking import candidate_quality_native_cable_resume as recovery
from src.ball_tracking import candidate_quality_retry_resume as prior_worker

ROOT = Path(__file__).resolve().parents[1]


class CandidateQualityNativeCableResumeTests(unittest.TestCase):
    def test_metadata_import_and_scope_approval(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            "import sys;from src.ball_tracking import candidate_quality_native_cable_resume;assert 'torch' not in sys.modules"],
            cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        old = recovery.read(ROOT / prior_worker.PREPARATION / 'execution_approval.json')
        binding = dict(path='new/execution_freeze.json', bytes=1, sha256='test')
        freeze = {'original_execution_approval': old['original_execution_approval']}
        approval = dict(old, execution_freeze=binding, attempt='attempt_005', max_total_seconds=5400,
                        debug_mode_enabled=True)
        recovery.validate_execution_approval(approval, binding, freeze)
        for bad in (old, dict(approval, attempt='attempt_004'), dict(approval, max_total_seconds=2437),
                    dict(approval, debug_mode_enabled=False), dict(approval, resume_approved=False),
                    dict(approval, automatic_retry=True), dict(approval, protected_access_approved=True)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                recovery.validate_execution_approval(bad, binding, freeze)

    def test_actual_fit_manifests_require_zero_first_fit_updates_and_exact_remaining_work(self):
        base = ROOT / recovery.OUTPUT
        candidates = recovery.rows(base / 'preparation/candidates.jsonl')
        added = presentations = score_calls = score_presentations = parity = 0
        first_fit_new = None
        for name in recovery.original.FIT_NAMES:
            manifest = recovery.read(base / f'preparation/fits/{name}/manifest.json')
            epoch, existing_steps = recovery.fit_start(name)
            additional = len(range(epoch, 7))*manifest['steps_per_epoch']
            added += additional
            presentations += len(range(epoch, 7))*manifest['fitting_candidates']
            self.assertEqual(existing_steps+additional, manifest['total_training_steps'])
            parity += existing_steps == 0
            if name == 'leave_chi_out': first_fit_new = additional
            scored = [c for c in candidates if name == 'all_nba' or
                      (c['domain'] == 'nba' and c['game_id'] in manifest['held_out_game_ids'])]
            score_presentations += len(scored); score_calls += math.ceil(len(scored)/32)
        query_manifest = recovery.read(base / 'evaluation/completed.json')
        queries = recovery.rows(recovery.bound(ROOT, query_manifest['queries_registry']))
        emitted = [q for q in queries if q['input_id'] is not None]
        score_presentations += len(emitted); score_calls += math.ceil(len(emitted)/32)
        self.assertEqual((first_fit_new, added, presentations, parity), (0, 7626, 243708, 3))
        self.assertEqual((score_calls, score_presentations), (1572, 50232))
        self.assertEqual(len(queries)-len(emitted), 11)
        config = recovery.read(ROOT / recovery.original.CONFIG)
        self.assertEqual(added+2244, config['counts']['optimizer_updates'])
        self.assertEqual(presentations+71724, config['counts']['training_candidate_presentations'])

    def test_actual_diagnostic_counts_remain_separate_from_new_logical_progress(self):
        completed = recovery.read(ROOT / recovery.diagnostic.OUTPUT / 'attempt_001/completed.json')
        zero = dict.fromkeys(recovery.RECOVERED_COUNTERS, 0)
        got = recovery.accounting(zero)
        self.assertEqual(got['logical'], completed['accounting']['logical_replay_branch'])
        for key, value in completed['accounting']['cumulative_physical_lower_bound'].items():
            self.assertEqual(got['cumulative_physical_lower_bound'][key], value)
        new = dict(zero, training_forwards_attempted=7626, training_forwards_returned=7626,
                   optimizer_updates=7626, training_candidate_presentations=243708)
        full = recovery.accounting(new)
        self.assertEqual(full['logical']['optimizer_updates'], 9870)
        self.assertEqual(full['cumulative_physical_lower_bound']['optimizer_updates'], 11708)
        self.assertEqual(full['cumulative_physical_lower_bound']['training_forwards_attempted'], 11710)
        self.assertEqual(full['cumulative_physical_lower_bound']['training_forwards_returned'], 11709)
        self.assertEqual(full['cumulative_physical_lower_bound']['training_candidate_presentations'], 374206)

    def test_new_operational_watchdog_does_not_restore_lifted_remaining_hour_cap(self):
        began = datetime(2026, 10, 29, tzinfo=timezone.utc)
        policy = {'created_at_utc': began.isoformat()}
        got = recovery.remaining_wall_seconds(policy, began+timedelta(seconds=2100))
        self.assertEqual(got['remaining_seconds'], 3300)
        self.assertEqual(got['stop_wait_seconds'], 3270)
        self.assertFalse(got['historical_hour_budget_is_active_limit'])
        self.assertEqual(got['historical_exposure_seconds_preserved'], 1574)
        for delta in (-3, 5370, 5400):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                recovery.remaining_wall_seconds(policy, began+timedelta(seconds=delta))

    def test_training_math_and_scoring_loops_match_preserved_scientific_worker(self):
        def portions(module):
            tree = ast.parse(Path(module.__file__).read_text())
            run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
            batches = [n for n in ast.walk(run) if isinstance(n, ast.For)
                       and isinstance(n.target, ast.Name) and n.target.id == 'batch']
            train, score = batches
            begin = next(i for i, n in enumerate(train.body) if isinstance(n, ast.Assign)
                         and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'losses')
            return (ast.dump(ast.Module(body=train.body[begin:], type_ignores=[]), include_attributes=False),
                    ast.dump(score, include_attributes=False))
        self.assertEqual(portions(recovery), portions(prior_worker))

    def test_new_attempt_and_receipt_timestamps_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prior = root / 'attempt_004'; prior.mkdir(); (prior/'evidence').write_bytes(b'preserve')
            created = recovery.make_attempt_directory(root)
            self.assertEqual(created.name, 'attempt_005')
            with self.assertRaises(FileExistsError): recovery.make_attempt_directory(root)
            journal = created/'journal.jsonl'
            recovery.append(journal, {'event': 'test_receipt'})
            recovery.append(journal, {'event': 'original_time', 'at_utc': 'preserve-original'})
            records = recovery.rows(journal)
            self.assertEqual(datetime.fromisoformat(records[0]['at_utc']).utcoffset(), timedelta(0))
            self.assertEqual(records[1]['at_utc'], 'preserve-original')
            self.assertEqual((prior/'evidence').read_bytes(), b'preserve')

    def test_completed_first_fit_result_carries_exact_import_bridge_binding(self):
        # Execute the actual producer's metadata-emission node independently of
        # its GPU run. The input record uses the real audited source binding.
        tree = ast.parse(Path(recovery.__file__).read_text())
        node = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                    and any(isinstance(child, ast.Assign) and any(
                        isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                        and target.slice.value == 'diagnostic_endpoint_import' for target in child.targets)
                            for child in node.body))
        emission = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                           '<actual completed-result producer>', 'exec')
        audit = recovery.read(ROOT/recovery.PREPARATION/'checkpoint_audit/checkpoint_audit.json')
        with tempfile.TemporaryDirectory(dir=ROOT/'data/outputs/t', prefix='native_import_binding_test_') as folder:
            fit_dir = Path(folder)
            path = fit_dir/'diagnostic_endpoint_import.json'
            raw = json.dumps({'source_checkpoint': audit['checkpoint'], 'metadata_transport_test_only': True}).encode()
            path.write_bytes(raw)
            result = {'fit': 'leave_chi_out'}
            scope = dict(fit_name='leave_chi_out', result=result, root=ROOT, fit_dir=fit_dir, binding=recovery.binding)
            exec(emission, scope)
            self.assertEqual(result['diagnostic_endpoint_import'], {
                'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
            other = {'fit': 'leave_den_out'}
            exec(emission, dict(scope, fit_name='leave_den_out', result=other))
            self.assertNotIn('diagnostic_endpoint_import', other)
            path.unlink()
            with self.assertRaises(FileNotFoundError): exec(emission, scope)

    def test_actual_diagnostic_payload_restores_and_rejects_changed_origin_on_cpu(self):
        code = r'''
import copy,json,os,random,sys
from pathlib import Path
from unittest.mock import patch
from src.ball_tracking import candidate_quality_native_cable_resume as r
root=Path.cwd(); assert 'torch' not in sys.modules
audit=r.read(root/r.PREPARATION/'checkpoint_audit/checkpoint_audit.json')
source=r.bound(root,audit['checkpoint'])
manifest=r.read(root/r.diagnostic.OUTPUT/'attempt_001/leave_chi_out/trainable_parameters.json')
shapes={row['name']:tuple(row['shape']) for row in manifest}
import numpy as np
import torch
torch.set_num_threads(2)
assert not torch.cuda.is_initialized()
payload=torch.load(source,map_location='cpu',weights_only=False)
r.validate_checkpoint_payload(payload,r.ORIGINAL_FREEZE['sha256'],shapes)
bad_records=[dict(payload,epoch=5),dict(payload,fit_steps=1870),dict(payload,purpose='scientific completion'),
 dict(payload,diagnostic_freeze=dict(payload['diagnostic_freeze'],sha256='wrong')),
 dict(payload,original_execution_freeze=dict(payload['original_execution_freeze'],sha256='wrong')),
 dict(payload,diagnostic_counters=dict(payload['diagnostic_counters'],optimizer_updates=2244)),
 dict(payload,counters=dict(payload['counters'],optimizer_updates=4082))]
for changed in bad_records:
 try:r.validate_checkpoint_payload(changed,r.ORIGINAL_FREEZE['sha256'],shapes)
 except ValueError:pass
 else:raise AssertionError('Changed source identity/accounting accepted')
for field,value in [('lr',.1),('weight_decay',0.)]:
 optimizer=copy.deepcopy(payload['optimizer_state']);optimizer['param_groups'][0][field]=value
 try:r.validate_checkpoint_payload(dict(payload,optimizer_state=optimizer),r.ORIGINAL_FREEZE['sha256'],shapes)
 except ValueError:pass
 else:raise AssertionError('Changed optimizer recipe accepted')
optimizer=copy.deepcopy(payload['optimizer_state']);next(iter(optimizer['state'].values()))['exp_avg'].view(-1)[0]=float('nan')
try:r.validate_checkpoint_payload(dict(payload,optimizer_state=optimizer),r.ORIGINAL_FREEZE['sha256'],shapes)
except ValueError:pass
else:raise AssertionError('Nonfinite moments accepted')
class ParameterBag:
 def __init__(self):self.values={row['name']:torch.nn.Parameter(torch.zeros(row['shape'])) for row in manifest}
 def named_parameters(self):return iter(self.values.items())
 def parameters(self):return iter(self.values.values())
model=ParameterBag()
groups=[{'params':[v for n,v in model.named_parameters() if n.startswith(prefix)],'lr':lr,'weight_decay':.01}
 for prefix,lr in [('backbone.',1e-5),('head.',1e-3)]]
optimizer=torch.optim.AdamW(groups,betas=(.9,.999),eps=1e-8)
py_expected=random.Random();py_expected.setstate(payload['python_rng'])
np_expected=np.random.RandomState();np_expected.set_state(payload['numpy_rng'])
torch_expected=torch.Generator(device='cpu');torch_expected.set_state(payload['torch_rng'])
cuda_calls=[]
with patch.object(torch.cuda,'set_rng_state_all',side_effect=lambda states:cuda_calls.append([s.clone() for s in states])):
 summary=r.restore_checkpoint(model,optimizer,payload,r.ORIGINAL_FREEZE['sha256'],shapes)
assert summary['steps']==2244 and summary['epoch']==6
assert r.original.trainable_group_fingerprints(model)==audit['group_fingerprints']
assert len(cuda_calls)==1 and all(torch.equal(a,b) for a,b in zip(cuda_calls[0],payload['cuda_rng']))
assert random.random()==py_expected.random()
assert np.array_equal(np.random.random_sample(4),np_expected.random_sample(4))
assert torch.equal(torch.rand(4),torch.rand(4,generator=torch_expected))
assert optimizer.state_dict()['param_groups']==payload['optimizer_state']['param_groups']
for key,state in optimizer.state_dict()['state'].items():
 for field,value in state.items():assert torch.equal(value,payload['optimizer_state']['state'][key][field])
assert not torch.cuda.is_initialized()
assert 'transformers' not in sys.modules
print(json.dumps({'status':'passed_actual_diagnostic_payload_CPU_restore','steps':2244,'cuda_initialized':False,'model_forwards':0}))
'''
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertFalse(json.loads(result.stdout.strip())['cuda_initialized'])


if __name__ == '__main__':
    unittest.main()

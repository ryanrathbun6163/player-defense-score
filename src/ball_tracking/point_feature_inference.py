"""Frozen, resumable CPU DINO readout comparison; no fitting or selection.

Importing this module and metadata preparation never import Torch. Only a
root-frozen authorized run imports the CPU model. Outcome analysis is separate.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import sys
import time
import traceback
import uuid

import numpy as np
from PIL import Image

from . import nba_appearance_feature_screen as old
from .weak_response_capture import bind, bound, read, write_once

ROOT = Path(__file__).resolve().parents[2]
CONFIG = 'configs/ball_tracking/proposals/point_feature_comparison_v0_1.json'
OUTPUT = 'data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_comparison_v0_1'
TOKEN_INDICES = np.asarray([120, 121, 136, 137], dtype=np.int64)
TOKEN_INDICES.setflags(write=False)


def check(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def file_link(link):
    return {key: link[key] for key in ('path', 'bytes', 'sha256')}


def numpy_cpu(value):
    if hasattr(value, 'detach'):
        check(str(value.device) == 'cpu' and str(value.dtype) == 'torch.float32',
              'Output must be CPU float32')
        value = value.detach().numpy()
    check(isinstance(value, np.ndarray) and value.dtype == np.float32, 'Float32 array required')
    return value


def extract_witnesses(output):
    """Consume the actual Dinov2Model interface, preserving raw normalized tokens."""
    sequence = numpy_cpu(getattr(output, 'last_hidden_state', None))
    pooled = numpy_cpu(getattr(output, 'pooler_output', None))
    check(sequence.shape == (1, 257, 384) and pooled.shape == (1, 384), 'DINO output interface differs')
    check(np.array_equal(sequence[:, 0, :], pooled), 'Same-pass CLS/sequence parity differs')
    check(np.isfinite(sequence).all() and np.isfinite(pooled).all(), 'Nonfinite model output')
    return {'cls': np.ascontiguousarray(pooled[0]).copy(),
            'tokens': np.ascontiguousarray(sequence[0, TOKEN_INDICES]).copy(),
            'sequence_indices': TOKEN_INDICES.copy(),
            'sequence_sha256': sha(np.ascontiguousarray(sequence).tobytes()),
            'same_pass_CLS_exact': True}


def normalize(vector):
    vector = np.asarray(vector, dtype=np.float64)
    check(vector.shape == (384,), 'Descriptor dimension differs')
    if not np.isfinite(vector).all():
        return None, 'nonfinite_descriptor'
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm):
        return None, 'nonfinite_descriptor_norm'
    if norm == 0:
        return None, 'zero_norm_descriptor'
    return vector / norm, None


def point_readout(tokens, geometry):
    """Interpolate raw final-LayerNorm tokens in float64, then normalize once."""
    check(isinstance(tokens, np.ndarray) and tokens.shape == (4, 384)
          and tokens.dtype == np.float32, 'Expected four raw float32 token witnesses')
    weights = geometry['tokens']
    check([t['sequence_index'] for t in weights] == TOKEN_INDICES.tolist(), 'Query token identities differ')
    w = np.asarray([t['weight'] for t in weights], dtype=np.float64)
    check(np.isfinite(w).all() and (w >= 0).all() and abs(float(w.sum())-1) < 1e-12,
          'Invalid point interpolation weights')
    raw = np.sum(tokens.astype(np.float64) * w[:, None], axis=0, dtype=np.float64)
    unit, reason = normalize(raw)
    return raw, unit, reason


def cls_parity(cls, previous, atol=1e-5, rtol=1e-5):
    check(cls.shape == previous.shape == (384,) and cls.dtype == previous.dtype == np.float32,
          'CLS parity shape/dtype differs')
    finite = bool(np.isfinite(cls).all() and np.isfinite(previous).all())
    delta = np.abs(cls.astype(np.float64)-previous.astype(np.float64))
    matches = finite and bool(np.all(delta <= atol + rtol*np.abs(previous.astype(np.float64))))
    return {'passed': matches, 'atol': atol, 'rtol': rtol,
            'maximum_absolute_difference': float(delta.max()) if finite else None,
            'new_raw_float32_sha256': sha(cls.tobytes()), 'old_raw_float32_sha256': sha(previous.tobytes())}


def row_major_evidence(library_path):
    """Inspect pinned installed producer AST, without importing its Torch code."""
    tree = ast.parse(Path(library_path).read_text(encoding='utf-8'))
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    patch = ast.unparse(classes['Dinov2PatchEmbeddings'])
    embeddings = ast.unparse(classes['Dinov2Embeddings'])
    model = ast.unparse(classes['Dinov2Model'])
    expected = {
        'patch_projection': 'nn.Conv2d(num_channels, hidden_size, kernel_size=patch_size, stride=patch_size)' in patch,
        'row_major_flatten': 'self.projection(pixel_values).flatten(2).transpose(1, 2)' in patch,
        'CLS_prepend': 'torch.cat((cls_tokens, embeddings), dim=1)' in embeddings,
        'full_sequence_final_LayerNorm': 'sequence_output = self.layernorm(sequence_output)' in model,
        'CLS_from_same_sequence': 'pooled_output = sequence_output[:, 0, :]' in model,
        'sequence_returned': 'last_hidden_state=sequence_output' in model}
    check(all(expected.values()), 'Installed patch/sequence interpretation differs')
    return expected


def load_registries(root, preparation):
    inputs = [json.loads(line) for line in bound(root, preparation['input_registry']).read_text().splitlines()]
    queries = [json.loads(line) for line in bound(root, preparation['queries_registry']).read_text().splitlines()]
    by_input = defaultdict(list)
    check(len(inputs) == 10883 and len(queries) == 11798, 'Full preparation census differs')
    check(len({q['query_id'] for q in queries}) == len(queries), 'Query IDs repeated')
    for query in queries:
        if query['input_id'] is None:
            check(query['center_xy_px'] is None and query['geometry']['status'] == 'missing_selection', 'Missing query differs')
            continue
        geometry = query['geometry']; tokens = geometry['tokens']
        check([t['sequence_index'] for t in tokens] == TOKEN_INDICES.tolist(), 'Central patch identities differ')
        check(all(t['sequence_index'] == 1+16*t['row']+t['column'] for t in tokens), 'Patch grid indexing differs')
        check(abs(sum(t['weight'] for t in tokens)-1) < 1e-12 and all(t['weight'] >= 0 for t in tokens), 'Query weights differ')
        cx, cy = query['center_xy_px']; left, top = geometry['crop_box'][:2]
        check(geometry['point_input_xy'] == [4*(cx-left+.5)-.5-16, 4*(cy-top+.5)-.5-16], 'Point/source affine differs')
        by_input[query['input_id']].append(query)
    check(sum(q['input_id'] is None for q in queries) == 11 and len(by_input) == 10883, 'Unknown/input census differs')
    for item in inputs:
        check(sha(canonical(item['identity'])) == item['input_id'], 'Input identity hash differs')
        check(item['query_ids'] == [q['query_id'] for q in by_input[item['input_id']]], 'Query/input membership differs')
        for q in by_input[item['input_id']]:
            check(q['source_video'] == item['source_video'] and q['source_pts_ticks'] == item['source_pts_ticks']
                  and q['time_base'] == item['time_base'] and q['geometry']['crop_box'] == item['identity']['crop_box']
                  and q['source_png']['rgb_sha256'] == item['identity']['source_rgb_sha256'], 'Input/query provenance differs')
    return inputs, queries, by_input


def validate_config(config):
    check(config['schema_version'] == 'point_feature_comparison/v0.1'
          and config['status'] == 'approved_CPU_inference_no_fit' and config['output_root'] == OUTPUT,
          'Expected approved fixed comparison configuration')
    check(config['inference_authorized'] is True and config['protected_evaluation_authorized'] is False
          and config['new_training_updates'] == config['new_selector_runs'] == 0, 'Execution scope differs')
    required_execution = {'device':'cpu','dtype':'float32','batch_size':1,'torch_threads':4,'attention':'eager',
                          'model_mode':'eval','gradient_mode':'inference_mode','heartbeat_seconds':30}
    check(all(config['execution'].get(key) == value for key,value in required_execution.items()),
          'CPU execution configuration differs')
    check(all(config['CLS_parity'].get(key) == value for key,value in
              {'atol':1e-5,'rtol':1e-5,'cases':60,'inside_same_pass':True,'before_HOU_inference':True,
               'before_outcome_analysis':True}.items()), 'Historical CLS tolerance/order differs')
    check(config['readouts']['names'] == ['cls','point'] and config['readouts']['sequence_shape'] == [1,257,384]
          and config['readouts']['point_sequence_indices'] == TOKEN_INDICES.tolist(), 'Fixed readout differs')
    check(config['analysis']['seal_all_descriptors_before_reference_outcomes'] is True
          and config['reference_bank']['no_bank_self_match_check_metrics'] is True, 'Analysis boundary differs')


def prepare(root=ROOT):
    """Read metadata, source and saved vectors; never calculate a new descriptor."""
    root = Path(root).resolve(); config = read(root/CONFIG); validate_config(config)
    prior = read(bound(root, config['preparation'])); geometry = read(bound(root, config['geometry_freeze']))
    audit = read(bound(root, config['preparation_audit']))
    check(prior['freeze'] == config['geometry_freeze'] and prior['status'] == 'completed_CPU_preparation_no_inference',
          'Completed geometry preparation differs')
    check(audit['status'].lower().startswith('pass'), 'Independent preparation audit not passed')
    for key in ('proposal','history_research_reconciliation','WASB_research_control','source_roles'):
        bound(root,config[key])
    check(config['readouts']['geometry'] == geometry['geometry'], 'Frozen crop/point mapping differs')
    for key, prior_key in (('weights','verified_current_weights'),('config','verified_current_config'),
                           ('processor','verified_current_processor'),('library','verified_current_library'),
                           ('versions','current_versions')):
        check(config['model'][key] == geometry[prior_key], 'Declared model differs from prepared pin: '+key)
    for key in ('verified_current_weights','verified_current_config','verified_current_processor'):
        bound(root, geometry[key])
    for link in geometry['source']: bound(root, link)
    versions = {name:metadata.version(name) for name in geometry['current_versions']}
    check(versions == geometry['current_versions'], 'Model runtime versions differ')
    library = geometry['verified_current_library']; path = Path(library['path'])
    check(path.stat().st_size == library['bytes'] and sha(path.read_bytes()) == library['sha256'], 'Pinned library differs')
    evidence = row_major_evidence(path)
    inputs, queries, by_input = load_registries(root, prior)
    historical = [q for q in queries if q['cohort'] == 'historical']
    check(len(historical) == 60, 'Historical parity census differs')
    bank = [q for q in historical if q['source_role'] == 'reference_bank']
    check([q['query_id'] for q in bank] == config['reference_bank']['case_ids']
          and {q['query_id']:q['historical_case']['accepted_appearance']['classification'] for q in bank}
              == config['reference_bank']['classes'], 'Accepted bank identities/roles differ')
    for q in historical:
        record = read(bound(root, q['old_CLS']['feature']))
        vector = np.asarray(record['raw_cls_float32'], dtype=np.float32)
        check(sha(vector.tobytes()) == q['old_raw_CLS_sha256'] == record['raw_cls_sha256'], 'Saved CLS binding differs')
    check('torch' not in sys.modules, 'Metadata preparation imported Torch')
    result = {'status':'prepared_no_new_descriptors','created_at_utc':stamp(),'config':bind(root,root/CONFIG),
        'preparation':config['preparation'],'geometry_freeze':config['geometry_freeze'],'preparation_audit':config['preparation_audit'],
        'input_registry':prior['input_registry'],'query_registry':prior['queries_registry'],
        'weights':geometry['verified_current_weights'],'model_config':geometry['verified_current_config'],
        'processor':geometry['verified_current_processor'],'library':library,'versions':versions,
        'source':[bind(root,root/'src/ball_tracking/point_feature_inference.py'),
                  bind(root,root/'src/ball_tracking/nba_appearance_feature_screen.py'),
                  bind(root,root/'src/ball_tracking/weak_response_capture.py')],
        'row_major_evidence':evidence,'sequence_indices':TOKEN_INDICES.tolist(),'inputs':len(inputs),'queries':len(queries),
        'input_order':'unique historical inputs first, then remaining stable prepared registry order',
        'new_model_calls':0,'new_descriptors':0,'torch_imported':False,
        'zero_norm_policy':'Explicit unknown, retained in output; no fabricated unit vector',
        'nonfinite_or_contract_failure_policy':'Preserve raw failed output when CPU arrays are available; stop without complete seal'}
    write_once(root/OUTPUT/'prepared.json',result)
    return result


def save_npz(path, witness):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        np.savez(stream, cls=witness['cls'], tokens=witness['tokens'], sequence_indices=witness['sequence_indices'])


def validate_cached(root, record, item, config_binding):
    check(record['status'] == 'completed' and record['input'] == item and record['config'] == config_binding,
          'Cached witness identity differs')
    path = bound(root, record['witness'])
    with np.load(path, allow_pickle=False) as data:
        check(set(data.files) == {'cls','tokens','sequence_indices'} and data['cls'].shape == (384,)
              and data['tokens'].shape == (4,384) and data['cls'].dtype == data['tokens'].dtype == np.float32
              and np.array_equal(data['sequence_indices'],TOKEN_INDICES)
              and np.isfinite(data['cls']).all() and np.isfinite(data['tokens']).all(), 'Cached witness schema differs')
        check(sha(data['cls'].tobytes()) == record['CLS_float32_sha256'], 'Cached CLS bytes differ')
    check(all(r['passed'] for r in record['historical_CLS_parity']), 'Failed parity record cannot be reused')


def aggregate_journals(paths):
    """Count actual durable call starts/returns, including interrupted attempts."""
    counts = Counter(); started = set(); returned = set()
    for path in paths:
        with Path(path).open(encoding='utf-8') as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    counts['incomplete_journal_lines'] += 1
                    continue
                kind = row['event']
                if kind in ('forward_start','forward_returned'):
                    key = (str(Path(path).parent), row['input_id'])
                    (started if kind=='forward_start' else returned).add(key)
                    counts['forward_calls_attempted' if kind=='forward_start' else 'forward_calls_returned'] += 1
                elif kind in ('model_load_start','model_load_complete','input_sealed'):
                    counts[kind] += 1
    counts['forward_starts_without_recorded_return'] = len(started-returned)
    counts['journal_files'] = len(paths)
    return dict(counts)


def run(root=ROOT, resume=False):
    root = Path(root).resolve(); output = root/OUTPUT
    frozen = read(output/'prospective_freeze.json')
    prepared_path = output/'prepared.json'; prepared = read(prepared_path)
    check(frozen['prepared'] == bind(root,prepared_path) and frozen['config'] == prepared['config'], 'Root freeze differs')
    for link in frozen['source'] + prepared['source']: bound(root,link)
    config = read(bound(root,prepared['config'])); validate_config(config)
    prior = read(bound(root,prepared['preparation'])); bound(root,prepared['preparation_audit'])
    check(not (output/'completed.json').exists(), 'Completed inference cannot be overwritten')
    attempts = output/'attempts'; attempts.mkdir(parents=True,exist_ok=True)
    check(resume or not any(attempts.iterdir()), 'Prior attempt exists; use explicit --resume to preserve it')
    for key in ('weights','model_config','processor'): bound(root,prepared[key])
    check({name:metadata.version(name) for name in prepared['versions']} == prepared['versions'], 'Runtime versions changed')
    library = prepared['library']; check(sha(Path(library['path']).read_bytes()) == library['sha256'], 'Library changed')
    inputs, queries, by_input = load_registries(root,prior)
    historical_ids = {q['input_id'] for q in queries if q['cohort'] == 'historical'}
    ordered = [i for i in inputs if i['input_id'] in historical_ids] + [i for i in inputs if i['input_id'] not in historical_ids]
    attempt_id = uuid.uuid4().hex; attempt = attempts/attempt_id; attempt.mkdir()
    receipts = output/'input_records'; receipts.mkdir(exist_ok=True)
    identity = {'schema_version':'point_feature_attempt/v0.1','attempt_id':attempt_id,'pid':os.getpid(),
        'parent_pid':os.getppid(),'started_at_utc':stamp(),'config':prepared['config'],
        'freeze':bind(root,output/'prospective_freeze.json'),'prepared':bind(root,prepared_path),'resume':resume,
        'device':'cpu','new_training_updates':0,'new_selector_runs':0,'protected_evaluation_access':False}
    write_once(attempt/'started.json',identity)
    journal = (attempt/'events.jsonl').open('x',encoding='utf-8')
    counters = Counter(); began = last_heartbeat = time.perf_counter(); records=[]; parity_records=[]
    model = None; cached_image = None; cached_path = None; current_item = None
    def event(kind, **payload):
        row={'event':kind,'at_utc':stamp(),'pid':os.getpid(),**payload}
        journal.write(json.dumps(row,allow_nan=False)+'\n'); journal.flush(); os.fsync(journal.fileno())
        if kind in ('started','heartbeat','completed','failed'):
            print(json.dumps(row),flush=True)
    try:
        event('started',total_inputs=len(ordered),total_queries=len(queries),historical_inputs_first=len(historical_ids))
        check('torch' not in sys.modules, 'Torch was imported before guarded execution')
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        for item in ordered:
            current_item=item; destination=receipts/(item['input_id']+'.json')
            if destination.exists():
                record=read(destination); validate_cached(root,record,item,prepared['config']); counters['cached_inputs_reused']+=1
            else:
                if model is None:
                    counters['model_load_attempts']+=1; event('model_load_start',**dict(counters))
                    model=old.load_model(bound(root,prepared['model_config']),bound(root,prepared['weights']))
                    import torch
                    check(torch.get_num_threads()==4 and all(p.device.type=='cpu' and p.dtype==torch.float32 for p in model.parameters()),
                          'Loaded model runtime differs')
                    counters['model_loads_completed']+=1; event('model_load_complete',**dict(counters))
                link=item['source_png']
                if cached_path!=link['path']:
                    cached_image=Image.open(bound(root,file_link(link))).convert('RGB'); cached_path=link['path']
                    check(sha(cached_image.tobytes())==link['rgb_sha256'],'Source RGB changed'); counters['source_PNG_decodes']+=1
                query=by_input[item['input_id']][0]
                crop,image,chw=old.crop_and_preprocess(cached_image,query['center_xy_px'])
                check(sha(crop.tobytes())==item['crop64_rgb_sha256'] and sha(image.tobytes())==item['input224_rgb_sha256']
                      and sha(chw.tobytes())==item['input_chw_float32_sha256'],'Prepared model input differs')
                counters['forward_calls_attempted']+=1
                event('forward_start',input_id=item['input_id'],attempted_call=counters['forward_calls_attempted'])
                with torch.inference_mode():
                    actual=model(pixel_values=torch.from_numpy(chw).unsqueeze(0),return_dict=True)
                counters['forward_calls_returned']+=1
                event('forward_returned',input_id=item['input_id'],returned_call=counters['forward_calls_returned'])
                try:
                    witness=extract_witnesses(actual)
                except BaseException:
                    fault=attempt/(item['input_id']+'.failed_output.npz')
                    try:
                        with fault.open('xb') as stream:
                            np.savez(stream,sequence=numpy_cpu(actual.last_hidden_state),pooled=numpy_cpu(actual.pooler_output))
                    except BaseException as preserve_error:
                        event('failed_output_preservation_error',reason=str(preserve_error))
                    raise
                witness_path=attempt/'witnesses'/(item['input_id']+'.npz'); save_npz(witness_path,witness)
                parity=[]
                for q in by_input[item['input_id']]:
                    if q['cohort']=='historical':
                        saved=read(bound(root,q['old_CLS']['feature']))
                        previous=np.asarray(saved['raw_cls_float32'],dtype=np.float32)
                        check(sha(previous.tobytes())==q['old_raw_CLS_sha256'],'Old CLS changed')
                        parity.append({'query_id':q['query_id'],'old_feature':q['old_CLS']['feature'],**cls_parity(witness['cls'],previous)})
                _,cls_unknown=normalize(witness['cls'])
                point_unknown={}
                for q in by_input[item['input_id']]:
                    _,_,reason=point_readout(witness['tokens'],q['geometry'])
                    if reason: point_unknown[q['query_id']]=reason
                record={'schema_version':'point_feature_input/v0.1','status':'completed' if all(p['passed'] for p in parity) else 'failed_CLS_parity',
                    'config':prepared['config'],'attempt_id':attempt_id,'input':item,'witness':bind(root,witness_path),
                    'sequence_shape':[1,257,384],'sequence_sha256':witness['sequence_sha256'],'sequence_indices':TOKEN_INDICES.tolist(),
                    'same_pass_CLS_exact':True,'CLS_float32_sha256':sha(witness['cls'].tobytes()),
                    'CLS_unknown_reason':cls_unknown,'point_unknown_reasons':point_unknown,'historical_CLS_parity':parity,
                    'outcome_analysis_performed':False,'completed_at_utc':stamp()}
                write_once(attempt/(item['input_id']+'.result.json'),record)
                check(record['status']=='completed','Historical same-pass CLS parity failed')
                write_once(destination,record); counters['inputs_completed_new']+=1
                event('input_sealed',input_id=item['input_id'],receipt=bind(root,destination))
            records.append(bind(root,destination)); parity_records.extend(record['historical_CLS_parity'])
            if time.perf_counter()-last_heartbeat >= 30:
                event('heartbeat',completed_inputs=len(records),total_inputs=len(ordered),elapsed_seconds=time.perf_counter()-began,**dict(counters))
                last_heartbeat=time.perf_counter()
        check(len(records)==10883 and len(parity_records)==60 and all(p['passed'] for p in parity_records),'Final census/parity differs')
        event('completed',completed_inputs=len(records),elapsed_seconds=time.perf_counter()-began,**dict(counters))
        journal_paths=sorted(attempts.glob('*/events.jsonl'))
        result={**identity,'status':'completed_all_descriptors_sealed','completed_at_utc':stamp(),'elapsed_seconds':time.perf_counter()-began,
            'inputs':10883,'queries':11798,'missing_queries':11,'input_registry':prior['input_registry'],'query_registry':prior['queries_registry'],
            'input_records':records,'historical_CLS_parity':parity_records,'attempt_resources':dict(counters),
            'all_descriptors_sealed_before_outcome_analysis':True,'outcome_analysis_performed':False,
            'attempt_journals':[bind(root,p) for p in journal_paths],
            'all_attempts_resources':aggregate_journals(journal_paths),
            'source':prepared['source'],'new_training_updates':0,'new_selector_runs':0,'protected_evaluation_access':False}
        journal.close(); write_once(attempt/'completed.json',result); write_once(output/'completed.json',result)
        return result
    except BaseException as error:
        event('failed',reason=str(error),current_input_id=None if current_item is None else current_item['input_id'],**dict(counters))
        journal.close(); write_once(attempt/'failed.json',{**identity,'error':str(error),'traceback':traceback.format_exc(),
            'attempt_resources':dict(counters),'elapsed_seconds':time.perf_counter()-began,
            'successful_inputs_preserved':len(records),'current_input_id':None if current_item is None else current_item['input_id']})
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--run',action='store_true');mode.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    result=prepare() if args.prepare else run(resume=args.resume)
    print(json.dumps({'status':result['status']}),flush=True)


if __name__=='__main__': main()

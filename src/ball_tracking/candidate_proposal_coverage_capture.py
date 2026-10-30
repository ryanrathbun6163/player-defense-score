"""One alternate-producer capture; preparation/import are metadata-only.

The owned runtime reads only an explicitly stripped, NBA-training input manifest
and existing immutable RGB caches. Targets are joined by a separate consumer
after all means, native observations and weak pools have been sealed.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import shutil
import struct
import sys
import threading
import time
import traceback

from .training_response_capture import binding, bound, check, read, required_starts, stamp, write_once

ROOT = Path(__file__).resolve().parents[2]
BASE = 'data/outputs/ball_tracking/candidate_proposal_coverage_v0_1'
PREPARATION = BASE + '/preparation/prepared.json'
INPUTS = BASE + '/preparation/inputs.json'
COMPATIBILITY = BASE + '/preparation/cpu_compatibility.json'
LAUNCH_BASE = BASE + '/launch_v0_1'
CAPTURE_OUTPUT = BASE + '/attempt_001/capture'
MONITOR = LAUNCH_BASE + '/monitoring/attempt_001'
MODULE = 'src.ball_tracking.candidate_proposal_coverage_capture'
PROTOCOL = 'docs/ball_tracking_candidate_proposal_coverage_protocol.md'
CONFIG = 'configs/ball_tracking/proposals/candidate_proposal_coverage_v0_1.json'
OLD_PREP = 'data/outputs/ball_tracking/training_response_preparation_v0_1/prepared.json'
CHECKPOINT = 'data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/training/checkpoint.pth'
CHECKPOINT_SHA = '09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98'
GPU = 'GPU-f26f32f8-e85b-0d38-651e-d5c54097525b'
MAX_TOTAL_SECONDS, CLEANUP_RESERVE_SECONDS = 1800, 30
MAX_ARTIFACT_BYTES = 8*1024**3
COUNTS = {'blocks': 21, 'frames': 3179, 'forward_calls': 3137, 'imported_frames': 0,
          'parity_calls': 0, 'optimizer_updates': 0}
GAMES = {'0022400868': 960, '0022400866': 960, '0022500829': 1259}
WIDTH, HEIGHT = 768, 432
RUNTIME_NAMES = ('torch', 'numpy', 'opencv-python', 'Pillow', 'PyYAML')
SOURCE_NAMES = ('candidate_proposal_coverage_capture', 'training_response_capture', 'wasb_resolution',
                'weak_response_followup', 'weak_response_candidates', 'wasb_adapter',
                'wasb_adapted_adapter', 'completion_training_runtime', 'continuation_owned_guard',
                'gpu_supervision', 'candidate_acceptance_neural', 'candidate_quality_native_cable_resume')
REQUIRED_IMPLEMENTATION = {f'src/ball_tracking/{n}.py' for n in SOURCE_NAMES} | {
    'tests/test_candidate_proposal_coverage_capture.py'}
FRAME_FIELDS = {'source_frame_index', 'source_pts_ticks', 'duration_ticks', 'png'}
BLOCK_FIELDS = {'block_id', 'game_id', 'domain', 'role', 'source_video', 'time_base', 'range_inclusive', 'frames'}


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def append(path, value):
    with Path(path).open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def file_header(path):
    """Read only the NPY header; do not import NumPy or touch its array payload."""
    with Path(path).open('rb') as stream:
        check(stream.read(6) == b'\x93NUMPY', 'Invalid NPY magic')
        version = tuple(stream.read(2))
        check(version in ((1, 0), (2, 0)), 'Unsupported NPY version')
        size = 2 if version == (1, 0) else 4
        length = int.from_bytes(stream.read(size), 'little')
        check(0 < length <= 65536, 'Invalid NPY header length')
        header = ast.literal_eval(stream.read(length).decode('latin1'))
        check(set(header) == {'descr', 'fortran_order', 'shape'}, 'Unexpected NPY header')
        return {**header, 'header_bytes': stream.tell()}


def validate_input_block(block):
    check(set(block) == BLOCK_FIELDS and block['domain'] == 'nba' and block['role'] == 'training'
          and block['game_id'] in GAMES, 'Only stripped permitted NBA training blocks are allowed')
    frames = block['frames']
    check(len(frames) >= 3 and all(set(f) == FRAME_FIELDS for f in frames), 'Unexpected input frame fields or short block')
    indices = [f['source_frame_index'] for f in frames]
    check(indices == list(range(indices[0], indices[-1]+1)) and block['range_inclusive'] == [indices[0], indices[-1]],
          'Nonconsecutive or inconsistent native frame range')
    check(all(type(f['duration_ticks']) is int and f['duration_ticks'] > 0 for f in frames)
          and all(b['source_pts_ticks']-a['source_pts_ticks'] == a['duration_ticks'] for a, b in zip(frames, frames[1:])),
          'Native PTS/duration transport differs')


def strip_block(block):
    result = {k: block[k] for k in BLOCK_FIELDS if k != 'frames'}
    result['frames'] = [{k: frame[k] for k in FRAME_FIELDS} for frame in block['frames']]
    validate_input_block(result)
    return result


def validate_manifest(manifest):
    check(set(manifest) == {'schema_version', 'blocks'} and manifest['schema_version'] == 'proposal_capture_inputs/v0.1',
          'Unexpected input manifest schema')
    blocks = manifest['blocks']
    check(len(blocks) == 21 and len({b['block_id'] for b in blocks}) == 21, 'Block identity census differs')
    game_counts, identities = Counter(), set()
    for block in blocks:
        validate_input_block(block)
        game_counts[block['game_id']] += len(block['frames'])
        for frame in block['frames']:
            key = (block['source_video']['sha256'], frame['source_frame_index'], frame['source_pts_ticks'])
            check(key not in identities, 'Duplicate canonical source frame')
            identities.add(key)
    check(dict(game_counts) == GAMES and len(identities) == 3179
          and sum(len(b['frames'])-2 for b in blocks) == 3137, 'Exact source/frame/call census differs')


def prepare(root=ROOT):
    """Hash canonical metadata/cache/PNG bytes and inspect headers; never decode."""
    root = Path(root).resolve()
    check('torch' not in sys.modules, 'Preparation must run without Torch')
    destination = root / BASE / 'preparation'
    check(not destination.exists(), 'Preserve prior preparation; no automatic overwrite')
    old = read(root / OLD_PREP)
    specification = read(root / CONFIG)
    check(specification['counts'] == COUNTS and specification['checkpoint_sha256'] == CHECKPOINT_SHA
          and specification['input_resolution'] == [WIDTH, HEIGHT] and specification['no_training'] is True
          and specification['no_new_labels'] is True and specification['protected_evaluation_authorized'] is False,
          'Capture specification scope differs')
    bound(root, specification['protocol'])
    package = read(bound(root, old['package']))
    source_blocks = [b for b in package['training_blocks'] if b['domain'] == 'nba']
    manifest = {'schema_version': 'proposal_capture_inputs/v0.1', 'blocks': [strip_block(b) for b in source_blocks]}
    validate_manifest(manifest)
    check(package['protected_evaluation_authorized'] is False, 'Protected evaluation must remain closed')
    links = {}

    def verify(link):
        path = (root / link['path']).resolve()
        check(path.is_relative_to(root), 'Input path escaped repository')
        actual = binding(root, path)
        check(all(actual[k] == link[k] for k in ('sha256', 'bytes') if k in link), 'Input binding differs: '+link['path'])
        links[actual['path']] = actual
        return path

    verify(old['package'])
    verify(old['source_roles'])
    verify(old['model_config'])
    verify(old['constructor_asset'])
    links[CONFIG] = binding(root, root/CONFIG)
    links[OLD_PREP] = binding(root, root / OLD_PREP)
    checkpoint = binding(root, root / CHECKPOINT)
    check(checkpoint['sha256'] == CHECKPOINT_SHA and checkpoint['bytes'] == 6084071, 'Fixed checkpoint differs')
    verify(checkpoint)
    config = read(root / old['model_config']['path'])
    check(config['expected_split']['reviewed_frames'] == 150
          and all(b['possession_id'].startswith('possession_') for b in config['training_blocks']), 'Expanded NFHS provenance differs')
    for link in old['upstream_model_sources']:
        verify(link)
    cache_index = {b['block_id']: b for b in old['blocks']}
    blocks = []
    for source, block in zip(source_blocks, manifest['blocks'], strict=True):
        item = cache_index[block['block_id']]
        receipt = read(verify(item['cache_receipt']))
        check(receipt['block_id'] == block['block_id'] and receipt['block_sha256'] == canonical(source), 'Cache source block differs')
        check(receipt['identity']['representation'] == 'affine_RGB_uint8_432x768'
              and receipt['identity']['resolution_module_sha256'] == binding(root, root/'src/ball_tracking/wasb_resolution.py')['sha256']
              and receipt['identity']['normalization_module_sha256'] == binding(root, root/'src/ball_tracking/completion_training_runtime.py')['sha256'],
              'Cache preprocessing identity differs')
        cache = verify(receipt['warped_frames'])
        check(receipt['warped_frames'] == item['warped_frames'], 'Prepared cache binding differs')
        header = file_header(cache)
        check(header['shape'] == (len(block['frames']), HEIGHT, WIDTH, 3) and header['descr'] == '|u1'
              and header['fortran_order'] is False
              and cache.stat().st_size == header['header_bytes'] + len(block['frames'])*HEIGHT*WIDTH*3,
              'Canonical cache shape/dtype/payload size differs')
        for frame, saved in zip(block['frames'], receipt['verified_frames'], strict=True):
            check(saved['source_frame_index'] == frame['source_frame_index'] and saved['source_png'] == frame['png'], 'Cache/native PNG transport differs')
            png = verify(frame['png'])
            with png.open('rb') as stream:
                head = stream.read(33)
            check(head[:8] == b'\x89PNG\r\n\x1a\n' and head[12:16] == b'IHDR'
                  and struct.unpack('>II', head[16:24]) == (block['source_video']['width_px'], block['source_video']['height_px'])
                  and head[24:26] == bytes([8, 2]), 'Source PNG RGB/header dimensions differ')
        for link in source['reference_bindings']:
            verify(link)
        blocks.append({'block_id': block['block_id'], 'frames': len(block['frames']), 'game_id': block['game_id'],
                       'cache_receipt': item['cache_receipt'], 'warped_frames': receipt['warped_frames'],
                       'required_triplet_start_offsets': required_starts(len(block['frames']), set()),
                       'new_forward_calls': len(block['frames'])-2, 'import_offsets': {},
                       'input_block_sha256': canonical(block)})
    raw_bytes = 3179*HEIGHT*WIDTH*4
    storage_bytes = raw_bytes + 21*128 + 256*1024*1024
    check(shutil.disk_usage(root).free >= storage_bytes*2, 'Insufficient map/metadata disk headroom')
    sources = [binding(root, root/f'src/ball_tracking/{n}.py') for n in SOURCE_NAMES]
    destination.mkdir(parents=True, exist_ok=False)
    write_once(root / INPUTS, manifest)
    links[INPUTS] = binding(root, root / INPUTS)
    result = {'status': 'prepared_metadata_only_no_inference', 'created_at_utc': stamp(), 'counts': COUNTS,
              'protocol': binding(root, root/PROTOCOL), 'specification': links[CONFIG], 'package': old['package'], 'source_roles': old['source_roles'],
              'checkpoint': checkpoint, 'constructor_asset': links[old['constructor_asset']['path']], 'model_config': old['model_config'],
              'upstream_model_sources': old['upstream_model_sources'], 'source_root': config['upstream_source'],
              'inputs': links[INPUTS], 'blocks': blocks, 'input_bindings': list(links.values()), 'source': sources,
              'runtime': {name: metadata.version(name) for name in RUNTIME_NAMES},
              'raw_mean_payload_bytes': raw_bytes, 'npy_header_bytes': 21*128,
              'metadata_reserve_bytes': 256*1024*1024, 'required_output_headroom_bytes': storage_bytes*2,
              'artifact_stop_bytes': MAX_ARTIFACT_BYTES,
              'free_disk_bytes_at_preparation': shutil.disk_usage(root).free,
              'source_png_decodes': 0, 'cache_array_reads': 0, 'new_model_calls': 0, 'new_training_updates': 0,
              'label_free_runtime_inputs': True, 'automatic_retry': False,
              'reduction_audit_scope': 'Unchanged stream_means verified by independent synthetic float32 tests; postrun channel digests/contributor identities and saved mean/extraction parity. Discarded forward channels are not numerically reconstructed postrun.'}
    write_once(root / PREPARATION, result)
    check('torch' not in sys.modules, 'Preparation imported Torch')
    return result


def verify_prepared(root):
    prepared = read(root / PREPARATION)
    check(prepared['counts'] == COUNTS and prepared['checkpoint']['sha256'] == CHECKPOINT_SHA
          and prepared['inputs']['path'] == INPUTS, 'Prepared contract differs')
    for link in prepared['input_bindings'] + prepared['source'] + prepared['upstream_model_sources']:
        bound(root, link)
    for name, version in prepared['runtime'].items():
        check(metadata.version(name) == version, 'Runtime metadata version differs: '+name)
    manifest = read(bound(root, prepared['inputs']))
    validate_manifest(manifest)
    check([b['block_id'] for b in prepared['blocks']] == [b['block_id'] for b in manifest['blocks']], 'Prepared block order differs')
    for block, item in zip(manifest['blocks'], prepared['blocks'], strict=True):
        check(item['input_block_sha256'] == canonical(block) and item['frames'] == len(block['frames'])
              and item['new_forward_calls'] == len(block['frames'])-2 and item['import_offsets'] == {}
              and item['required_triplet_start_offsets'] == required_starts(len(block['frames']), set()), 'Prepared schedule differs')
    return prepared, manifest


def make_adapter(root, prepared, device):
    from .wasb_adapted_adapter import AdaptedWasbAdapter
    return AdaptedWasbAdapter(root/prepared['source_root'], bound(root, prepared['constructor_asset']),
                             bound(root, prepared['checkpoint']), CHECKPOINT_SHA,
                             {'preparation': binding(root, root/PREPARATION), 'fixed_expanded_NFHS_checkpoint': True}, device=device)


def cpu_compatibility(root=ROOT):
    """Explicit CPU-only strict state/model check; no forward, optimizer or GPU query."""
    root = Path(root).resolve()
    check(not (root/COMPATIBILITY).exists(), 'Preserve previous compatibility evidence')
    prepared, _ = verify_prepared(root)
    import torch
    check(not torch.cuda.is_initialized(), 'CUDA already initialized before CPU check')
    adapter = make_adapter(root, prepared, 'cpu')
    tensors = []
    for name, value in adapter.model.state_dict().items():
        check(value.device.type == 'cpu' and bool(torch.isfinite(value).all()), 'Invalid CPU checkpoint tensor')
        tensors.append({'name': name, 'shape': list(value.shape), 'dtype': str(value.dtype),
                        'sha256': hashlib.sha256(value.detach().contiguous().numpy().tobytes()).hexdigest()})
    check(not torch.cuda.is_initialized(), 'CPU compatibility initialized CUDA')
    result = {'status': 'passed_cpu_strict_model_checkpoint_compatibility', 'at_utc': stamp(),
              'prepared': binding(root, root/PREPARATION), 'checkpoint': prepared['checkpoint'],
              'implementation': binding(root, Path(__file__)), 'tensors': tensors,
              'strict_state_load': True, 'all_tensors_finite_on_cpu': True, 'CUDA_initialized': False,
              'model_forwards': 0, 'optimizer_updates': 0, 'GPU_queries': 0,
              'resolution_limit': 'Strict state compatibility only; fixed768 architecture support reuses prior pinned resolution evidence. First scheduled forward validates actual output shape.'}
    write_once(root/COMPATIBILITY, result)
    del adapter
    return result


def validate_authorization(auth, freeze_binding, protocol):
    check(auth.get('execution_approved') is True and auth.get('execution_freeze') == freeze_binding
          and auth.get('protocol') == protocol and auth.get('scope') == COUNTS
          and auth.get('max_total_seconds') == MAX_TOTAL_SECONDS
          and isinstance(auth.get('user_statement'), str) and auth['user_statement'].strip(), 'Exact capture authorization required')
    check(all(auth.get(k) is False for k in ('automatic_retry', 'automatic_extension', 'protected_access_approved',
          'new_labels_approved', 'training_approved', 'selector_approved')), 'Authorization exceeds capture scope')


def preflight(root=ROOT, require_approval=False):
    root = Path(root).resolve()
    check('torch' not in sys.modules, 'Preflight must precede Torch import')
    prepared, _ = verify_prepared(root)
    freeze_file = root/LAUNCH_BASE/'execution_freeze.json'
    freeze = read(freeze_file)
    check(freeze.get('status') == 'frozen_for_authorized_execution' and freeze.get('scope') == COUNTS
          and freeze.get('prepared') == binding(root, root/PREPARATION)
          and freeze.get('protocol') == binding(root, root/PROTOCOL) == prepared['protocol']
          and freeze.get('launch_base') == LAUNCH_BASE and freeze.get('capture_output') == CAPTURE_OUTPUT,
          'Freeze scope, protocol or destination differs')
    check(not (root/CAPTURE_OUTPUT).exists(), 'Capture attempt exists; no retry/resume authorized')
    implementation, inputs = freeze.get('implementation', []), freeze.get('inputs', [])
    check(REQUIRED_IMPLEMENTATION <= {b['path'] for b in implementation}, 'Frozen implementation coverage incomplete')
    input_index = {b['path']: b for b in inputs}
    check(len(input_index) == len(inputs) and all(input_index.get(b['path']) == b for b in prepared['input_bindings']), 'Frozen input coverage differs')
    check(freeze.get('compatibility', {}).get('path') == COMPATIBILITY and freeze.get('review'), 'Compatibility/review evidence missing')
    for link in [freeze['protocol'], *implementation, *inputs, freeze['focused_tests'], *freeze['review'], freeze['compatibility']]:
        bound(root, link)
    compatibility = read(root/COMPATIBILITY)
    check(compatibility['status'] == 'passed_cpu_strict_model_checkpoint_compatibility'
          and compatibility['prepared'] == freeze['prepared'] and compatibility['checkpoint'] == prepared['checkpoint']
          and compatibility['implementation'] == binding(root, Path(__file__))
          and compatibility['model_forwards'] == 0 and compatibility['CUDA_initialized'] is False, 'CPU compatibility contract differs')
    check(shutil.disk_usage(root).free >= prepared['required_output_headroom_bytes'], 'Current disk headroom insufficient')
    if require_approval:
        from .candidate_acceptance_neural import validate_readiness
        auth_file = root/LAUNCH_BASE/'execution_authorization.json'
        freeze_binding = binding(root, freeze_file)
        validate_authorization(read(auth_file), freeze_binding, freeze['protocol'])
        readiness = read(root/LAUNCH_BASE/'launch_readiness.json')
        validate_readiness(readiness, freeze_binding, binding(root, auth_file))
        for link in readiness['sources']:
            bound(root, link)
    check('torch' not in sys.modules, 'Preflight imported Torch')
    return prepared, freeze


def validate_policy(policy):
    check(policy.get('module') == MODULE and policy.get('arguments') == ['--run', '--monitor', MONITOR]
          and policy.get('sample_seconds') == 2 and policy.get('temperature_stop_C') == 80
          and policy.get('telemetry_timeout_seconds') == 5 and policy.get('grace_seconds') == 10
          and policy.get('automatic_retry') is False and policy.get('max_total_seconds') == MAX_TOTAL_SECONDS
          and policy.get('soft_stop_seconds') == MAX_TOTAL_SECONDS-CLEANUP_RESERVE_SECONDS
          and policy.get('gpu_uuid') == GPU, 'Owned supervisor policy differs')


def remaining_seconds(policy, now=None):
    created = datetime.fromisoformat(policy['created_at_utc'])
    now = now or datetime.now(timezone.utc)
    check(created.tzinfo is not None and created.utcoffset().total_seconds() == 0, 'Owned deadline requires UTC')
    elapsed = (now-created).total_seconds()
    check(math.isfinite(elapsed) and elapsed >= -2, 'Owned deadline future dated')
    remaining = MAX_TOTAL_SECONDS-elapsed
    check(remaining > CLEANUP_RESERVE_SECONDS, 'Owned wall deadline reached')
    return remaining


def artifact_bytes(folder):
    """Only count this new attempt's files; never inspect or manage other jobs."""
    return sum(p.stat().st_size for p in Path(folder).rglob('*') if p.is_file())


def capture_block(root, block, destination, provider):
    """Synthetic-testable streaming reducer/extractor, with no reference argument."""
    import numpy as np
    from . import wasb_resolution as resolution
    from . import weak_response_followup as extraction
    validate_input_block(block)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    frames, channels, native, calls = block['frames'], {}, [], 0
    map_path, ledger_path = destination/'mean_heatmaps.npy', destination/'contributor_ledger.jsonl'
    means = np.lib.format.open_memmap(map_path, mode='w+', dtype=np.float32, shape=(len(frames), HEIGHT, WIDTH))
    segment = {'kind': 'alternate_producer_training_coverage', 'source_frame_range_inclusive': block['range_inclusive']}

    def wrapped(selected):
        nonlocal calls
        start = selected[0]['source_frame_index']-frames[0]['source_frame_index']
        check(start == calls, 'Forward order differs from canonical schedule')
        values = provider(selected)
        check(isinstance(values, np.ndarray) and values.dtype == np.float32 and values.shape == (3, HEIGHT, WIDTH)
              and np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all(), 'Invalid forward maps')
        for channel, frame in enumerate(selected):
            channels[(start, channel)] = {'triplet_start_offset': start, 'triplet_source_frame_indices': [f['source_frame_index'] for f in selected],
                                        'channel': channel, 'channel_sha256': hashlib.sha256(values[channel].tobytes()).hexdigest()}
        calls += 1
        return values

    try:
        for offset, (frame, mean, count) in enumerate(resolution.stream_means(frames, wrapped)):
            check(mean is not None and mean.dtype == np.float32, 'Canonical frame mean missing')
            starts = list(range(max(0, offset-2), min(offset, len(frames)-3)+1))
            contributors = [channels.pop((start, offset-start)) for start in starts]
            check(count == len(contributors), 'Contributor count differs')
            row = resolution.select_observation(frame, mean, count, block, segment)
            means[offset] = mean
            native.append(row)
            append(ledger_path, {'block_id': block['block_id'], 'offset': offset, 'source_frame_index': frame['source_frame_index'],
                                'source_pts_ticks': frame['source_pts_ticks'], 'contributors': contributors,
                                'count': count, 'mean_heatmap_sha256': row['mean_heatmap_sha256'],
                                'minimum': float(mean.min()), 'maximum': float(mean.max()), 'all_finite': True})
        check(calls == len(frames)-2 and len(native) == len(frames) and not channels, 'Block call/mean/channel census differs')
        means.flush()
    finally:
        means._mmap.close()
    extraction_receipt = extraction.extract_block(root, block, native, binding(root, map_path), destination/'pools.jsonl')
    check(extraction_receipt['mean_heatmaps']['bytes'] == len(frames)*HEIGHT*WIDTH*4+128, 'Actual NPY output bytes differ')
    record = {'block_id': block['block_id'], 'game_id': block['game_id'], 'source_video': block['source_video'],
              'native_observations': native, 'calls': calls, 'imports': {}, 'extraction': extraction_receipt,
              'contributor_ledger': binding(root, ledger_path), 'input_block_sha256': canonical(block),
              'labels_used': False, 'raw_forward_channels_retained': False}
    write_once(destination/'completed.json', record)
    return record


def run(root, monitor, arguments):
    root = Path(root).resolve()
    check(monitor == MONITOR and list(arguments) == ['--run', '--monitor', MONITOR], 'Exact owned launch arguments required')
    prepared, freeze = preflight(root, require_approval=True)
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root/monitor, MODULE, arguments)
    policy = read(root/monitor/'policy.json')
    validate_policy(policy)
    remaining = remaining_seconds(policy)
    from .candidate_quality_native_cable_resume import verify_runtime_driver
    driver = verify_runtime_driver(GPU)
    out = root/CAPTURE_OUTPUT
    out.mkdir(parents=True, exist_ok=False)
    began, done, array = time.monotonic(), threading.Event(), None
    counters = {'attempted': 0, 'returned': 0, 'means': 0, 'completed_blocks': 0}
    write_once(out/'started.json', {'at_utc': stamp(), 'ownership': ownership, 'driver': driver,
               'prepared': binding(root, root/PREPARATION), 'execution_freeze': binding(root, root/LAUNCH_BASE/'execution_freeze.json'),
               'execution_authorization': binding(root, root/LAUNCH_BASE/'execution_authorization.json'),
               'launch_readiness': binding(root, root/LAUNCH_BASE/'launch_readiness.json'), 'settings_changed': False})

    def watchdog():
        stop_at = time.monotonic()+max(0., remaining-CLEANUP_RESERVE_SECONDS)
        while not done.wait(2):
            try:
                reason = ('soft_wall_deadline' if time.monotonic() >= stop_at else
                          'artifact_bytes_exceeded' if artifact_bytes(out) > MAX_ARTIFACT_BYTES else
                          'disk_free_below_512MiB' if shutil.disk_usage(out).free < 512*1024**2 else None)
            except Exception as error:
                reason = 'storage_watchdog_failed:'+str(error)
            if reason:
                (root/monitor/'STOP').touch(exist_ok=True)
                write_once(out/'operational_stop.json', {'at_utc': stamp(), 'reason': reason, 'automatic_retry': False})
                return

    def continuing():
        check(not (root/monitor/'STOP').exists(), 'Owned supervisor requested STOP')
        remaining_seconds(policy)

    threading.Thread(target=watchdog, daemon=True).start()
    try:
        continuing()
        import numpy as np
        import torch
        from types import SimpleNamespace
        from . import wasb_resolution as resolution
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        adapter = make_adapter(root, prepared, 'cuda')
        adapter.model.eval().requires_grad_(False)
        before = {k: v.detach().cpu().clone() for k, v in adapter.model.state_dict().items()}
        manifest = read(root/INPUTS)
        records = []
        for block, item in zip(manifest['blocks'], prepared['blocks'], strict=True):
            continuing()
            array = np.load(root/item['warped_frames']['path'], mmap_mode='r', allow_pickle=False)
            check(not array.flags.writeable and array.dtype == np.uint8 and array.shape == (len(block['frames']), HEIGHT, WIDTH, 3), 'Read-only cache contract differs')
            bid = block['block_id']
            store = SimpleNamespace(arrays={bid: array}, positions={bid: {f['source_frame_index']: i for i, f in enumerate(block['frames'])}})

            def provider(frames):
                continuing()
                check(counters['attempted'] < 3137, 'Frozen forward budget exhausted')
                indices = [f['source_frame_index'] for f in frames]
                counters['attempted'] += 1
                append(out/'forward_journal.jsonl', {'event': 'attempted', 'at_utc': stamp(), 'block_id': bid, 'indices': indices, 'count': counters['attempted']})
                inputs = resolution.FrameStore.inputs(store, bid, indices)
                values = resolution._model_values(adapter.model, adapter.device, inputs, WIDTH, HEIGHT)
                counters['returned'] += 1
                append(out/'forward_journal.jsonl', {'event': 'returned', 'at_utc': stamp(), 'block_id': bid, 'indices': indices,
                                                   'count': counters['returned'], 'triplet_sha256': hashlib.sha256(values.tobytes()).hexdigest()})
                return values

            folder = out/hashlib.sha256(bid.encode()).hexdigest()[:24]
            record = capture_block(root, block, folder, provider)
            array._mmap.close()
            array = None
            counters['means'] += len(record['native_observations'])
            counters['completed_blocks'] += 1
            records.append(binding(root, folder/'completed.json'))
            append(out/'block_journal.jsonl', {'at_utc': stamp(), 'record': records[-1], 'counters': dict(counters)})
            print(json.dumps({'event': 'proposal_capture_block_complete', 'block_id': bid, **counters}), flush=True)
        continuing()
        check(counters == {'attempted': 3137, 'returned': 3137, 'means': 3179, 'completed_blocks': 21}, 'Final capture counts differ')
        check(artifact_bytes(out) <= MAX_ARTIFACT_BYTES, 'Final artifact byte ceiling exceeded')
        check(all(torch.equal(before[k], v.detach().cpu()) for k, v in adapter.model.state_dict().items()), 'Inference changed model tensors')
        result = {'status': 'completed_capture_no_fitting', 'completed_at_utc': stamp(), 'elapsed_seconds': time.monotonic()-began,
                  'prepared': binding(root, root/PREPARATION), 'package': prepared['package'], 'inputs': prepared['inputs'],
                  'checkpoint': prepared['checkpoint'], 'records': records, 'counts': COUNTS,
                  'new_forward_calls_attempted': counters['attempted'], 'new_forward_calls_returned': counters['returned'],
                  'frames': counters['means'], 'model_tensors_unchanged': True, 'new_training_updates': 0,
                  'new_selector_runs': 0, 'new_labels': 0, 'protected_access': False, 'model_adopted': False,
                  'extraction_sealed_before_label_assisted_coverage': True, 'automatic_retry': False,
                  'forward_journal': binding(root, out/'forward_journal.jsonl'), 'block_journal': binding(root, out/'block_journal.jsonl'),
                  'reduction_audit_scope': prepared['reduction_audit_scope']}
        write_once(out/'completed.json', result)
        return result
    except BaseException as error:
        write_once(out/'failed.json', {'at_utc': stamp(), 'elapsed_seconds': time.monotonic()-began, 'error': type(error).__name__,
                                     'message': str(error), 'traceback': traceback.format_exc(), 'counters': counters, 'automatic_retry': False})
        raise
    finally:
        done.set()
        if array is not None:
            array._mmap.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--prepare', action='store_true')
    group.add_argument('--cpu-compatibility', action='store_true')
    group.add_argument('--run', action='store_true')
    parser.add_argument('--monitor')
    args = parser.parse_args()
    if args.prepare:
        result = prepare()
    elif args.cpu_compatibility:
        result = cpu_compatibility()
    elif args.run:
        result = run(ROOT, args.monitor, sys.argv[1:])
    else:
        prepared, _ = preflight()
        result = {'status': 'passed_metadata_preflight', 'counts': prepared['counts']}
    print(json.dumps({k: v for k, v in result.items() if k in ('status', 'counts', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()

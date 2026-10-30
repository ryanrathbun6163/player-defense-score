"""Bounded synthetic capture transport and metadata guards; no neural execution."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from src.ball_tracking import candidate_proposal_coverage_capture as capture


def synthetic(n=7):
    frames = [{'source_frame_index': 100+i, 'source_pts_ticks': 10000+i*1000, 'duration_ticks': 1000,
               'png': {'path': f'frame_{i}.png', 'sha256': str(i)*64, 'rgb_sha256': str(i)*64}}
              for i in range(n)]
    block = {'block_id': 'synthetic', 'game_id': '0022400868', 'domain': 'nba', 'role': 'training',
             'source_video': {'width_px': 1280, 'height_px': 720, 'sha256': 'a'*64},
             'time_base': '1/60000', 'range_inclusive': [100, 99+n], 'frames': frames}
    channels = []
    for start in range(n-2):
        planes = np.zeros((3, 432, 768), np.float32)
        for channel in range(3):
            # Two separate native components, a strict-.01 tie, and a weak-only point.
            planes[channel, 50, 50] = np.float32(.31 + (start+channel)*.017)
            planes[channel, 90, 90] = np.float32(.36 + start*.013)
            planes[channel, 140, 140] = np.float32(.01)
            planes[channel, 200, 200] = np.float32(.02 + channel*.001)
        channels.append(planes)
    if n >= 5:
        # Same target frame receives a deliberately nonassociative float32 sum.
        channels[0][2, 250, 250] = np.float32(1)
        channels[1][1, 250, 250] = np.float32(2**-24)
        channels[2][0, 250, 250] = np.float32(2**-24)
    expected = []
    for offset in range(n):
        total = np.zeros((432, 768), np.float32)
        starts = list(range(max(0, offset-2), min(offset, n-3)+1))
        for start in starts:
            np.add(total, channels[start][offset-start], out=total)
        expected.append(total / np.float32(len(starts)))
    calls = []
    def provider(selected):
        start = selected[0]['source_frame_index']-100
        calls.append(start)
        return channels[start].copy()
    return block, channels, expected, calls, provider


class ProposalCaptureTests(unittest.TestCase):
    def test_import_is_metadata_only_in_fresh_process(self):
        command = "import sys; from src.ball_tracking import candidate_proposal_coverage_capture; assert not {'torch','cv2','PIL.Image','numpy'} & set(sys.modules)"
        subprocess.run([sys.executable, '-B', '-c', command], cwd=capture.ROOT, check=True, capture_output=True)

    def test_strip_rejects_evaluation_and_excludes_all_reference_fields(self):
        block, *_ = synthetic()
        original = deepcopy(block)
        original['selection_category'] = 'recovery'
        for frame in original['frames']:
            frame.update(annotation={'geometry': {'center_xy_px': [10, 10]}}, kind='positive')
        self.assertEqual(capture.strip_block(original), block)
        for key, value in [('role', 'checkpoint_validation'), ('domain', 'nfhs'), ('game_id', '0022400879')]:
            wrong = deepcopy(block); wrong[key] = value
            with self.assertRaises(ValueError): capture.validate_input_block(wrong)
        wrong = deepcopy(block); wrong['frames'][0]['annotation'] = {}
        with self.assertRaises(ValueError): capture.validate_input_block(wrong)

    def test_native_clock_and_consecutive_frames_are_mandatory(self):
        block, *_ = synthetic()
        for field, value in [('source_frame_index', 101), ('source_pts_ticks', 999), ('duration_ticks', 0)]:
            wrong = deepcopy(block); wrong['frames'][0][field] = value
            with self.assertRaises(ValueError): capture.validate_input_block(wrong)

    def test_exact_float32_reduction_ledger_and_own_mean_extraction(self):
        from src.ball_tracking import wasb_resolution as resolution
        block, channels, expected, calls, provider = synthetic()
        with tempfile.TemporaryDirectory() as directory:
            root, output = Path(directory), Path(directory)/'capture'
            result = capture.capture_block(root, block, output, provider)
            means = np.load(output/'mean_heatmaps.npy', allow_pickle=False)
            np.testing.assert_array_equal(means, np.stack(expected))
            reversed_sum = np.float32(np.float32(2**-24)+np.float32(2**-24))+np.float32(1)
            self.assertNotEqual(expected[2][250,250], reversed_sum/np.float32(3))
            self.assertEqual(calls, list(range(5)))
            self.assertEqual(result['calls'], 5)
            self.assertEqual(result['imports'], {})
            self.assertFalse(result['labels_used'])
            self.assertFalse(result['raw_forward_channels_retained'])
            ledgers = [json.loads(x) for x in (output/'contributor_ledger.jsonl').read_text().splitlines()]
            self.assertEqual([r['count'] for r in ledgers], [1, 2, 3, 3, 3, 2, 1])
            for offset, (row, mean) in enumerate(zip(ledgers, expected)):
                self.assertEqual(row['mean_heatmap_sha256'], hashlib.sha256(mean.tobytes()).hexdigest())
                self.assertEqual(len(row['contributors']), row['count'])
                for item in row['contributors']:
                    start, channel = item['triplet_start_offset'], item['channel']
                    self.assertEqual(start+channel, offset)
                    self.assertEqual(item['channel_sha256'], hashlib.sha256(channels[start][channel].tobytes()).hexdigest())
                expected_native = resolution.components_from_heatmap(mean, 1280, 720)
                self.assertEqual(result['native_observations'][offset]['candidates'],
                                 [{'candidate_index': i, **c} for i, c in enumerate(expected_native)])
            pools = [json.loads(x) for x in (output/'pools.jsonl').read_text().splitlines()]
            self.assertTrue(result['extraction']['all_mean_hashes_exact'])
            self.assertTrue(result['extraction']['all_native_candidates_exact'])
            self.assertEqual(len(pools), 7)
            self.assertTrue(all(r['diagnostic']['labels_used'] is False for r in pools))
            self.assertEqual([r['diagnostic']['native_count'] for r in pools], [2,2,3,2,2,2,2])
            self.assertTrue(all(r['diagnostic']['retained_weak_count'] == 1 for r in pools))

    def test_empty_and_threshold_tie_frames_remain_in_sealed_rows(self):
        block, *_ = synthetic(3)
        def provider(_):
            values = np.zeros((3, 432, 768), np.float32)
            values[1, 20, 20] = np.float32(.3)
            values[2, 20, 20] = np.float32(.01)
            return values
        with tempfile.TemporaryDirectory() as directory:
            result = capture.capture_block(Path(directory), block, Path(directory)/'capture', provider)
            self.assertEqual([r['state'] for r in result['native_observations']], ['missing']*3)
            self.assertTrue(all(r['selected_candidate_index'] is None for r in result['native_observations']))
            pools = [json.loads(x) for x in (Path(directory)/'capture/pools.jsonl').read_text().splitlines()]
            self.assertEqual([len(r['candidates']) for r in pools], [0, 1, 0])

    def test_nonfinite_wrong_shape_and_dtype_preserve_partial_attempt(self):
        block, *_ = synthetic(3)
        for kind in ('nonfinite', 'shape', 'dtype'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                values = np.zeros((3, 432, 768), np.float32)
                if kind == 'nonfinite': values[0, 0, 0] = np.nan
                if kind == 'shape': values = values[:2]
                if kind == 'dtype': values = values.astype(np.float64)
                output = Path(directory)/'capture'
                with self.assertRaises(ValueError): capture.capture_block(Path(directory), block, output, lambda _: values)
                self.assertTrue((output/'mean_heatmaps.npy').exists())
                self.assertFalse((output/'completed.json').exists())
                before = (output/'mean_heatmaps.npy').read_bytes()
                with self.assertRaises(FileExistsError): capture.capture_block(Path(directory), block, output, lambda _: values)
                self.assertEqual(before, (output/'mean_heatmaps.npy').read_bytes())

    def test_header_checks_without_array_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'frames.npy'
            np.save(path, np.zeros((3, 4, 5, 3), np.uint8), allow_pickle=False)
            header = capture.file_header(path)
            self.assertEqual(header['shape'], (3, 4, 5, 3))
            self.assertEqual(header['descr'], '|u1')
            self.assertEqual(path.stat().st_size, header['header_bytes']+180)
            path.write_bytes(b'bad-header')
            with self.assertRaises(ValueError): capture.file_header(path)

    def test_artifact_accounting_is_confined_to_own_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            own = root/'attempt'; (own/'nested').mkdir(parents=True)
            (own/'one').write_bytes(b'abc')
            (own/'nested/two').write_bytes(b'defg')
            (root/'unrelated').write_bytes(b'not counted')
            self.assertEqual(capture.artifact_bytes(own), 7)

    def test_full_manifest_rejects_duplicate_source_frames_and_expansion(self):
        blocks = []
        lengths = {'0022400868':[120,120,120,120,240,240],
                   '0022400866':[120,120,120,120,240,240],
                   '0022500829':[120,120,120,120,239,240,60,120,120]}
        template, *_ = synthetic(3)
        for game, counts in lengths.items():
            for i, count in enumerate(counts):
                block = deepcopy(template)
                block.update(block_id=f'{game}_{i}',game_id=game,range_inclusive=[0,count-1])
                block['source_video']['sha256']=hashlib.sha256(block['block_id'].encode()).hexdigest()
                block['frames']=[{'source_frame_index':j,'source_pts_ticks':j*1000,'duration_ticks':1000,
                                  'png':{'path':f'{j}.png','sha256':'a'*64}} for j in range(count)]
                blocks.append(block)
        manifest={'schema_version':'proposal_capture_inputs/v0.1','blocks':blocks}
        capture.validate_manifest(manifest)
        wrong=deepcopy(manifest)
        wrong['blocks'][1]['source_video']=wrong['blocks'][0]['source_video']
        with self.assertRaises(ValueError):capture.validate_manifest(wrong)
        wrong=deepcopy(manifest);wrong['blocks'].append(deepcopy(blocks[0]))
        with self.assertRaises(ValueError):capture.validate_manifest(wrong)

    def test_authorization_rejects_new_scope_and_stale_freeze(self):
        freeze = {'path': 'freeze.json', 'bytes': 1, 'sha256': 'a'*64}
        protocol = {'path': 'protocol.md', 'bytes': 2, 'sha256': 'b'*64}
        auth = {'execution_approved': True, 'execution_freeze': freeze, 'protocol': protocol,
                'scope': capture.COUNTS, 'max_total_seconds': 1800, 'user_statement': 'move forward',
                **dict.fromkeys(('automatic_retry', 'automatic_extension', 'protected_access_approved',
                                 'new_labels_approved', 'training_approved', 'selector_approved'), False)}
        capture.validate_authorization(auth, freeze, protocol)
        for key, value in [('execution_approved', False), ('scope', {**capture.COUNTS, 'forward_calls': 3138}),
                           ('training_approved', True), ('execution_freeze', protocol), ('user_statement', ' ')]:
            with self.assertRaises(ValueError): capture.validate_authorization({**auth, key:value}, freeze, protocol)

    def test_exact_owned_policy_and_deadline(self):
        now = datetime.now(timezone.utc)
        policy = {'module': capture.MODULE, 'arguments':['--run','--monitor',capture.MONITOR],
                  'sample_seconds':2,'temperature_stop_C':80,'telemetry_timeout_seconds':5,'grace_seconds':10,
                  'automatic_retry':False,'max_total_seconds':1800,'soft_stop_seconds':1770,'gpu_uuid':capture.GPU,
                  'created_at_utc':now.isoformat()}
        capture.validate_policy(policy)
        self.assertEqual(capture.remaining_seconds(policy, now), 1800)
        with self.assertRaises(ValueError): capture.validate_policy({**policy,'max_total_seconds':5400})
        with self.assertRaises(ValueError): capture.remaining_seconds(policy, now+timedelta(seconds=1770))
        with self.assertRaises(ValueError): capture.remaining_seconds(policy, now-timedelta(seconds=3))


if __name__ == '__main__':
    unittest.main()

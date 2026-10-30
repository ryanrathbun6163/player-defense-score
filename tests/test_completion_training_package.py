"""Role and native-context regressions using the annotation producer's records."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from src.ball_tracking.annotations import load_annotations
from src.ball_tracking import completion_training_package as package

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ANNOTATIONS = ROOT / 'configs/ball_tracking/annotations/possession_001_frames_0100_0124_training_expansion_v0_1.json'


class PackageBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.produced = load_annotations(SOURCE_ANNOTATIONS)

    def block(self, indices=(100, 101, 102), role='training', block_id='fixture'):
        by_frame = self.produced.annotation_by_frame()
        return {'block_id': block_id, 'domain': 'nfhs', 'game_id': 'possession_001',
                'possession_id': 'possession_001', 'role': role,
                'source_video': self.produced.source_video.to_dict(), 'time_base': '1/12800',
                'frames': [{'source_frame_index': index, 'source_pts_ticks': (index + 1) * 512,
                            'duration_ticks': 512, 'png': {'path': 'unopened-source.png'},
                            'annotation': by_frame[index].to_dict()} for index in indices]}

    @staticmethod
    def hidden(frame, certainty):
        row = frame['annotation']
        row.update(visibility='not_visible', absence_reason='occluded', geometry=None,
                   localization_eligible=False, game_ball_identity_certainty=certainty,
                   notes='Fixture preserves producer schema; identity certainty controls masking.')

    def test_actual_annotation_producer_frames_join_without_cross_boundary_context(self):
        block = self.block()
        usable, excluded = package.compose_triplets([block])
        self.assertEqual(len(usable), 1)
        self.assertFalse(excluded)
        self.assertEqual(usable[0]['frame_indices'], [100, 101, 102])
        self.assertEqual(usable[0]['block_id'], 'fixture')
        self.assertEqual(usable[0]['source_id'], self.produced.source_video.sha256)

    def test_only_certain_hidden_is_negative_and_unknowns_are_masked(self):
        block = self.block()
        self.hidden(block['frames'][0], 'certain')
        self.hidden(block['frames'][1], 'probable')
        block['frames'][2]['annotation'].update(geometry=None, localization_eligible=False,
            notes='Visible fragment but no supported center.')
        usable, _ = package.compose_triplets([block])
        self.assertEqual(usable[0]['valid_output_channels'], [True, False, False])
        self.assertEqual([f['kind'] for f in block['frames']], ['hidden', 'masked', 'masked'])

    def test_all_masked_triplets_preserved_as_exclusions(self):
        block = self.block()
        for frame in block['frames']:
            self.hidden(frame, 'probable')
        usable, excluded = package.compose_triplets([block])
        self.assertFalse(usable)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0]['valid_output_channels'], [False, False, False])

    def test_native_gap_duration_or_annotation_join_rejected(self):
        variants = []
        b = self.block(); b['frames'][1]['source_pts_ticks'] += 1; variants.append(b)
        b = self.block(); b['frames'][0]['duration_ticks'] -= 1; variants.append(b)
        b = self.block(); b['frames'][1]['annotation']['frame_index'] = 102; variants.append(b)
        b = self.block((100, 102, 103)); variants.append(b)
        for b in variants:
            with self.subTest(b=b['frames']), self.assertRaises(ValueError):
                package.normalize_block(b)

    def test_validation_cannot_become_training_triplets(self):
        with self.assertRaisesRegex(ValueError, 'Validation/evaluation'):
            package.compose_triplets([self.block(role='checkpoint_validation')])

    def test_cross_partition_overlap_and_protected_context_rejected(self):
        a = self.block()
        b = self.block(role='checkpoint_validation', block_id='validation')
        with self.assertRaisesRegex(ValueError, 'overlap'):
            package.guard_partition([a], [b], {'possession_001': []})
        with self.assertRaisesRegex(ValueError, 'Protected'):
            package.guard_partition([self.block()], [], {'possession_001': [[101, 101]]})

    def test_fixed_nba_parent_game_roles_cannot_change(self):
        b = self.block(); b.update(domain='nba', game_id='0022500828')
        with self.assertRaisesRegex(ValueError, 'Excluded'):
            package.normalize_block(b)
        b['game_id'] = '0022400879'
        with self.assertRaisesRegex(ValueError, 'parent-game role'):
            package.normalize_block(b)

    def test_duplicate_native_source_rows_rejected_even_different_block_ids(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate training native'):
            package.compose_triplets([self.block(), self.block(block_id='different')])

    def test_missing_png_is_explicit_and_existing_hash_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            e = package.Evidence(folder)
            missing = {'path': 'missing.png', 'sha256': 'a' * 64, 'rgb_sha256': 'b' * 64}
            e.png(missing, 'block', 1)
            self.assertEqual(e.missing[0]['source_frame_index'], 1)
            p = Path(folder) / 'source.png'; p.write_bytes(b'producer-file')
            with self.assertRaisesRegex(ValueError, 'binding changed'):
                e.png({**missing, 'path': 'source.png'}, 'block', 1)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                e.path('../outside.png')


if __name__ == '__main__':
    unittest.main()

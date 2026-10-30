"""Fabricated inventories exercise the recovery scanner's accounting contract."""
from contextlib import ExitStack
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_retention_scan_recovery as recovery
from src.ball_tracking.crop_retention_resources import ResourceLimitError


def info(inode, size, device=1):
    return SimpleNamespace(st_dev=device, st_ino=inode, st_size=size)


def inventory(*names, folder="fabricated"):
    return [(folder, [], list(names))]


class ScriptedInventoryTests(unittest.TestCase):
    def scripted(self, scans, metadata):
        """Keep time fixed for finite, explicitly scripted correctness cases."""
        stack = ExitStack()
        self.addCleanup(stack.close)
        walk = stack.enter_context(patch.object(recovery.os, "walk", side_effect=scans))
        lookup = stack.enter_context(patch.object(recovery.os, "stat", side_effect=metadata))
        stack.enter_context(patch.object(recovery.time, "monotonic", return_value=0.0))
        return walk, lookup

    def test_empty_tree_requires_two_complete_scans(self):
        walk, lookup = self.scripted([inventory(), inventory()], [])
        self.assertEqual(recovery.output_bytes("fabricated"), 0)
        self.assertEqual(walk.call_count, 2)
        lookup.assert_not_called()

    def test_growth_charges_larger_observed_size(self):
        walk, _ = self.scripted([inventory("a"), inventory("a")],
                                [info(1, 7), info(1, 19)])
        self.assertEqual(recovery.output_bytes("fabricated"), 19)
        self.assertEqual(walk.call_count, 2)

    def test_shrinkage_does_not_discard_first_scan_size(self):
        self.scripted([inventory("a"), inventory("a")], [info(1, 19), info(1, 7)])
        self.assertEqual(recovery.output_bytes("fabricated"), 19)

    def test_additions_and_more_hard_links_use_second_scan_multiplicity(self):
        self.scripted([inventory("a"), inventory("a", "alias", "new")],
                      [info(1, 19), info(1, 7), info(1, 11), info(2, 5)])
        self.assertEqual(recovery.output_bytes("fabricated"), 2 * 19 + 5)

    def test_same_inode_on_different_devices_is_not_one_identity(self):
        rows = [info(1, 7, 1), info(1, 11, 2)]
        self.scripted([inventory("a", "b"), inventory("a", "b")], rows + rows)
        self.assertEqual(recovery.output_bytes("fabricated"), 18)

    def test_directory_rename_keeps_identity_based_accounting(self):
        walk, lookup = self.scripted(
            [inventory("file", folder="before"), inventory("file", folder="after")],
            [info(1, 23), info(1, 23)])
        self.assertEqual(recovery.output_bytes("fabricated"), 23)
        self.assertEqual(walk.call_count, 2)
        self.assertEqual([call.args for call in lookup.call_args_list],
                         [(os.path.join("before", "file"),),
                          (os.path.join("after", "file"),)])

    def test_replacement_with_equal_bytes_requires_a_new_complete_pair(self):
        walk, _ = self.scripted([inventory("a")] * 3,
                                [info(1, 23), info(2, 23), info(2, 23)])
        self.assertEqual(recovery.output_bytes("fabricated"), 23)
        self.assertEqual(walk.call_count, 3)

    def test_lost_identity_requires_a_new_complete_pair(self):
        walk, _ = self.scripted(
            [inventory("a", "b"), inventory("a"), inventory("a")],
            [info(1, 7), info(2, 11), info(1, 7), info(1, 7)])
        self.assertEqual(recovery.output_bytes("fabricated"), 7)
        self.assertEqual(walk.call_count, 3)

    def test_decreasing_hard_link_count_requires_a_new_complete_pair(self):
        walk, _ = self.scripted(
            [inventory("a", "alias"), inventory("a"), inventory("a")],
            [info(1, 31), info(1, 31), info(1, 7), info(1, 7)])
        self.assertEqual(recovery.output_bytes("fabricated"), 7)
        self.assertEqual(walk.call_count, 3)

    def test_missing_file_discards_prior_and_partial_inventories(self):
        walk, _ = self.scripted(
            [inventory("old"), inventory("partial", "vanished"),
             inventory("new"), inventory("new")],
            [info(1, 100), info(2, 90), FileNotFoundError("fabricated race"),
             info(3, 7), info(3, 7)])
        self.assertEqual(recovery.output_bytes("fabricated"), 7)
        self.assertEqual(walk.call_count, 4)

    def test_disappearing_directory_discards_the_previous_inventory(self):
        walk, _ = self.scripted(
            [inventory("old"), FileNotFoundError("fabricated directory race"),
             inventory("new"), inventory("new")],
            [info(1, 100), info(2, 7), info(2, 7)])
        self.assertEqual(recovery.output_bytes("fabricated"), 7)
        self.assertEqual(walk.call_count, 4)

    def test_non_missing_metadata_error_propagates_without_a_retry(self):
        error = PermissionError("fabricated denied stat")
        walk, _ = self.scripted([inventory("a")], [error])
        with self.assertRaises(PermissionError) as caught:
            recovery.output_bytes("fabricated")
        self.assertIs(caught.exception, error)
        self.assertEqual(walk.call_count, 1)

    def test_walk_error_callback_propagates_without_skipping_a_subtree(self):
        error = OSError("fabricated unreadable subtree")

        def denied_walk(root, *, onerror):
            onerror(error)

        with patch.object(recovery.os, "walk", side_effect=denied_walk) as walk, \
                patch.object(recovery.os, "stat") as lookup, \
                patch.object(recovery.time, "monotonic", return_value=0.0):
            with self.assertRaises(OSError) as caught:
                recovery.output_bytes("fabricated")
        self.assertIs(caught.exception, error)
        self.assertEqual(walk.call_count, 1)
        lookup.assert_not_called()


class DeadlineTests(unittest.TestCase):
    def test_expired_deadline_prevents_the_first_traversal(self):
        with patch.object(recovery.os, "walk") as walk, \
                patch.object(recovery.time, "monotonic", side_effect=[0.0, 0.5]):
            with self.assertRaisesRegex(ResourceLimitError, "did not stabilize"):
                recovery.output_bytes("fabricated")
        walk.assert_not_called()

    def test_slow_metadata_lookup_cannot_return_a_partial_measurement(self):
        clock = SimpleNamespace(now=0.0)

        def slow_stat(path):
            clock.now = 0.5
            return info(1, 23)

        with patch.object(recovery.os, "walk", return_value=inventory("a")) as walk, \
                patch.object(recovery.os, "stat", side_effect=slow_stat) as lookup, \
                patch.object(recovery.time, "monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(ResourceLimitError, "did not stabilize"):
                recovery.output_bytes("fabricated")
        self.assertEqual(walk.call_count, 1)
        self.assertEqual(lookup.call_count, 1)

    def test_stable_scans_share_one_deadline(self):
        clock = SimpleNamespace(now=0.0)

        def slow_stat(path):
            clock.now += 0.25
            return info(1, 23)

        with patch.object(recovery.os, "walk", return_value=inventory("a")) as walk, \
                patch.object(recovery.os, "stat", side_effect=slow_stat), \
                patch.object(recovery.time, "monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(ResourceLimitError, "did not stabilize"):
                recovery.output_bytes("fabricated")
        self.assertEqual(walk.call_count, 2)

    def test_repeated_replacement_is_bounded_even_with_equal_byte_totals(self):
        clock = SimpleNamespace(now=0.0, inode=0)

        def replaced_stat(path):
            clock.now += 0.125
            clock.inode += 1
            return info(clock.inode, 23)

        with patch.object(recovery.os, "walk", return_value=inventory("a")) as walk, \
                patch.object(recovery.os, "stat", side_effect=replaced_stat), \
                patch.object(recovery.time, "monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(ResourceLimitError, "did not stabilize"):
                recovery.output_bytes("fabricated")
        self.assertEqual(walk.call_count, 4)

    def test_repeated_missing_files_do_not_reset_the_deadline(self):
        clock = SimpleNamespace(now=0.0)

        def missing_stat(path):
            clock.now += 0.25
            raise FileNotFoundError("fabricated race")

        with patch.object(recovery.os, "walk", return_value=inventory("a")) as walk, \
                patch.object(recovery.os, "stat", side_effect=missing_stat), \
                patch.object(recovery.time, "monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(ResourceLimitError, "did not stabilize"):
                recovery.output_bytes("fabricated")
        self.assertEqual(walk.call_count, 2)

    def test_repeated_hard_link_loss_cannot_escape_the_deadline(self):
        clock = SimpleNamespace(now=0.0)

        def measured_stat(path):
            clock.now += 0.0625
            return info(1, 23)

        scans = [inventory("a", "b", "c", "d"), inventory("a", "b", "c"),
                 inventory("a", "b")]
        with patch.object(recovery.os, "walk", side_effect=scans) as walk, \
                patch.object(recovery.os, "stat", side_effect=measured_stat), \
                patch.object(recovery.time, "monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(ResourceLimitError, "did not stabilize"):
                recovery.output_bytes("fabricated")
        self.assertEqual(walk.call_count, 3)


class StaticFilesystemTests(unittest.TestCase):
    def test_nested_unicode_long_names_and_hard_links_match_fresh_stat_reference(self):
        with tempfile.TemporaryDirectory(prefix="scan_recovery_") as temporary:
            root = Path(temporary)
            nested = root / "nested" / "further"
            nested.mkdir(parents=True)
            original = root / "ball_球.bin"
            original.write_bytes(b"x" * 31)
            alias = nested / "hard_link.bin"
            os.link(original, alias)
            (nested / ("long_" + "n" * 140 + ".bin")).write_bytes(b"y" * 17)
            (root / "empty.bin").write_bytes(b"")
            (root / "empty_directory").mkdir()

            # This independent static reference counts paths directly. It does
            # not reproduce the scanner's identity-merging or retry algorithm.
            paths = [os.path.join(folder, name)
                     for folder, _, names in os.walk(root) for name in names]
            reference = sum(os.stat(path).st_size for path in paths)
            original_info, alias_info = os.stat(original), os.stat(alias)
            self.assertEqual((original_info.st_dev, original_info.st_ino),
                             (alias_info.st_dev, alias_info.st_ino))
            self.assertEqual(len(paths), 4)
            self.assertEqual(reference, 31 * 2 + 17)
            self.assertEqual(recovery.output_bytes(root), reference)


if __name__ == "__main__":
    unittest.main()

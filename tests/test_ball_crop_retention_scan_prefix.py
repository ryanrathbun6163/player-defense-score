"""Focused correctness checks for the separate directory-prefix candidate."""
from contextlib import contextmanager
import ntpath
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

from src.ball_tracking import crop_retention_scan_prefix as scanner


DEADLINE_MESSAGE = "Output tree did not stabilize for complete byte accounting"
ROOT = r"C:\fabricated"
PATH_FOLDERS = (
    "", ".", "relative", "relative\\nested", "C:", "C:relative",
    "C:\\", "C:\\nested", "C:\\nested\\", "C:/nested/", "\\nested",
    "\\\\server\\share", "\\\\server\\share\\nested",
    "\\\\?\\C:\\", "\\\\?\\C:\\nested",
    "\\\\?\\UNC\\server\\share",
    "\\\\?\\UNC\\server\\share\\nested",
)
PATH_NAMES = ("ball.tmp", "space name.log", "caf\u00e9_\u7403.bin", "x" * 100 + ".bin")


def metadata(inode, size, device=17):
    return SimpleNamespace(st_dev=device, st_ino=inode, st_size=size)


def inventory(names, folder=ROOT):
    return [(folder, [], list(names))]


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


@contextmanager
def scripted(inventories, observations, *, clock=None, join_effect=None):
    """Replace only scanner module references; never patch global os helpers."""
    clock = Clock() if clock is None else clock
    pending = iter(inventories)

    def walk_effect(root, *, onerror):
        item = next(pending)
        return item(onerror) if callable(item) else iter(item)

    walk = Mock(side_effect=walk_effect)
    stat = Mock(side_effect=observations)
    join = Mock(side_effect=ntpath.join if join_effect is None else join_effect)
    fake_os = SimpleNamespace(walk=walk, stat=stat, path=SimpleNamespace(join=join))
    with patch.object(scanner, "os", fake_os), \
            patch.object(scanner, "time", SimpleNamespace(monotonic=clock)):
        yield SimpleNamespace(walk=walk, stat=stat, join=join, clock=clock)


class PrefixPathTests(unittest.TestCase):
    def test_prefix_algebra_matches_native_windows_filename_joining(self):
        # These are strings only: no UNC server, drive or extended path is opened.
        for folder in PATH_FOLDERS:
            for name in PATH_NAMES:
                with self.subTest(folder=folder, name=name):
                    self.assertEqual(ntpath.join(folder, "_")[:-1] + name,
                                     ntpath.join(folder, name))

    def test_scanner_uses_equivalent_paths_for_native_windows_forms(self):
        for folder in PATH_FOLDERS:
            with self.subTest(folder=folder):
                rows = inventory(PATH_NAMES, folder)
                samples = [metadata(i + 1, i + 2) for i in range(len(PATH_NAMES))]
                with scripted([rows, rows], samples + samples) as env:
                    self.assertEqual(scanner.output_bytes(ROOT), 14)
                expected = [call(ntpath.join(folder, name)) for name in PATH_NAMES]
                self.assertEqual(env.stat.call_args_list, expected + expected)
                self.assertEqual(env.join.call_args_list,
                                 [call(folder, "_"), call(folder, "_")])

    def test_prefix_is_prepared_once_for_each_yielded_directory_including_empty(self):
        child = ROOT + r"\nested"
        rows = [(ROOT, ["nested"], []), (child, [], ["a", "b"])]
        samples = [metadata(1, 3), metadata(2, 5)]
        with scripted([rows, rows], samples + samples) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 8)
        self.assertEqual(env.join.call_args_list,
                         [call(ROOT, "_"), call(child, "_")] * 2)
        self.assertEqual(env.stat.call_count, 4)


class InventoryContractTests(unittest.TestCase):
    def test_fresh_stat_is_called_for_every_entry_in_both_inventories(self):
        child = ROOT + r"\nested"
        rows = [(ROOT, ["nested"], ["a", "b"]), (child, [], ["c"])]
        samples = [metadata(1, 1), metadata(2, 2), metadata(3, 3),
                   metadata(1, 4), metadata(2, 2), metadata(3, 3)]
        with scripted([rows, rows], samples) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 9)
        expected = [call(ROOT + r"\a"), call(ROOT + r"\b"), call(child + r"\c")]
        self.assertEqual(env.stat.call_args_list, expected + expected)
        self.assertEqual(env.walk.call_count, 2)
        self.assertTrue(all(item.args == (ROOT,) and callable(item.kwargs["onerror"])
                            for item in env.walk.call_args_list))

    def test_empty_tree_still_requires_two_complete_inventories(self):
        with scripted([inventory([]), inventory([])], []) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 0)
        self.assertEqual(env.walk.call_count, 2)
        env.stat.assert_not_called()

    def test_hard_links_charge_each_entry_at_maximum_observed_identity_size(self):
        rows = inventory(["a", "link"])
        samples = [metadata(1, 10), metadata(1, 20), metadata(1, 12), metadata(1, 15)]
        with scripted([rows, rows], samples):
            self.assertEqual(scanner.output_bytes(ROOT), 40)

    def test_device_is_part_of_identity(self):
        rows = inventory(["a", "b"])
        samples = [metadata(1, 7, device=17), metadata(1, 11, device=29)]
        with scripted([rows, rows], samples + samples):
            self.assertEqual(scanner.output_bytes(ROOT), 18)

    def test_growth_and_shrinkage_use_larger_observed_size(self):
        for before, after in ((5, 9), (9, 4)):
            with self.subTest(before=before, after=after):
                with scripted([inventory(["a"])] * 2,
                              [metadata(1, before), metadata(1, after)]):
                    self.assertEqual(scanner.output_bytes(ROOT), max(before, after))

    def test_replaced_path_requires_a_new_complete_pair(self):
        rows = inventory(["a"])
        with scripted([rows] * 3,
                      [metadata(1, 50), metadata(2, 3), metadata(2, 4)]) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 4)
        self.assertEqual(env.walk.call_count, 3)

    def test_new_identity_is_allowed_in_second_inventory(self):
        with scripted([inventory(["a"]), inventory(["a", "b"])],
                      [metadata(1, 3), metadata(1, 3), metadata(2, 5)]) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 8)
        self.assertEqual(env.walk.call_count, 2)

    def test_increased_hard_link_multiplicity_is_allowed(self):
        with scripted([inventory(["a"]), inventory(["a", "link"])],
                      [metadata(1, 3), metadata(1, 4), metadata(1, 4)]) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 8)
        self.assertEqual(env.walk.call_count, 2)

    def test_reduced_hard_link_multiplicity_requires_another_inventory(self):
        with scripted([inventory(["a", "link"]), inventory(["a"]), inventory(["a"])],
                      [metadata(1, 12), metadata(1, 10), metadata(1, 7), metadata(1, 5)]) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 7)
        self.assertEqual(env.walk.call_count, 3)

    def test_missing_identity_requires_another_inventory(self):
        with scripted([inventory(["a", "b"]), inventory(["a"]), inventory(["a"])],
                      [metadata(1, 3), metadata(2, 100), metadata(1, 5), metadata(1, 4)]) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 5)
        self.assertEqual(env.walk.call_count, 3)

    def test_disappearance_discards_both_prior_and_incomplete_inventory(self):
        rows = [inventory(["a"]), inventory(["a", "b"]),
                inventory(["c"]), inventory(["c"])]
        samples = [metadata(1, 50), metadata(1, 999), FileNotFoundError("b moved"),
                   metadata(3, 7), metadata(3, 6)]
        with scripted(rows, samples) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 7)
        self.assertEqual(env.walk.call_count, 4)
        self.assertEqual(env.stat.call_count, 5)

    def test_directory_move_discards_incomplete_traversal(self):
        old_folder, new_folder = ROOT + r"\old", ROOT + r"\new"

        def moved(onerror):
            yield old_folder, [], ["a"]
            onerror(FileNotFoundError("directory moved during traversal"))

        rows = inventory(["a"], new_folder)
        with scripted([moved, rows, rows],
                      [metadata(1, 100), metadata(1, 8), metadata(1, 9)]) as env:
            self.assertEqual(scanner.output_bytes(ROOT), 9)
        self.assertEqual(env.stat.call_args_list,
                         [call(old_folder + r"\a"), call(new_folder + r"\a"),
                          call(new_folder + r"\a")])

    def test_other_stat_errors_propagate_without_another_inventory(self):
        error = PermissionError("fabricated denied file")
        with scripted([inventory(["a"])], [error]) as env:
            with self.assertRaises(PermissionError) as caught:
                scanner.output_bytes(ROOT)
        self.assertIs(caught.exception, error)
        self.assertEqual(env.walk.call_count, 1)
        env.stat.assert_called_once_with(ROOT + r"\a")

    def test_other_traversal_errors_propagate_through_onerror(self):
        error = PermissionError("fabricated denied directory")

        def denied(onerror):
            onerror(error)
            yield  # Keep this an iterator; successful traversal cannot reach it.

        with scripted([denied], []) as env:
            with self.assertRaises(PermissionError) as caught:
                scanner.output_bytes(ROOT)
        self.assertIs(caught.exception, error)
        self.assertEqual(env.walk.call_count, 1)
        env.stat.assert_not_called()


class DeadlineTests(unittest.TestCase):
    def assert_deadline(self):
        return self.assertRaisesRegex(scanner.ResourceLimitError,
                                      "^" + DEADLINE_MESSAGE + "$")

    def test_initial_deadline_prevents_traversal(self):
        clock = Mock(side_effect=[0.0, 0.5])
        with scripted([], [], clock=clock) as env:
            with self.assert_deadline():
                scanner.output_bytes(ROOT)
        env.walk.assert_not_called()
        env.join.assert_not_called()

    def test_directory_deadline_prevents_prefix_preparation(self):
        clock = Clock()

        def slow_directory(onerror):
            clock.value = 0.5
            yield ROOT, [], ["a"]

        with scripted([slow_directory], [], clock=clock) as env:
            with self.assert_deadline():
                scanner.output_bytes(ROOT)
        env.join.assert_not_called()
        env.stat.assert_not_called()

    def test_prefix_work_is_charged_even_for_an_empty_directory(self):
        clock = Clock()

        def slow_prefix(folder, suffix):
            clock.value = 0.5
            return ntpath.join(folder, suffix)

        def empty_directory(onerror):
            yield ROOT, [], []
            raise AssertionError("Expired prefix work must stop before advancing traversal")

        # Neither a later query check nor an end-of-inventory check can mask omission.
        with scripted([empty_directory], [], clock=clock, join_effect=slow_prefix) as env:
            with self.assert_deadline():
                scanner.output_bytes(ROOT)
        env.join.assert_called_once_with(ROOT, "_")
        env.stat.assert_not_called()

    def test_pre_query_deadline_stops_the_next_entry(self):
        clock = Clock()

        class SizeConsumesTime:
            st_dev, st_ino = 17, 1

            @property
            def st_size(self):
                clock.value = 0.5
                return 3

        with scripted([inventory(["a", "b"])], [SizeConsumesTime()], clock=clock) as env:
            with self.assert_deadline():
                scanner.output_bytes(ROOT)
        env.stat.assert_called_once_with(ROOT + r"\a")

    def test_post_query_deadline_precedes_metadata_aggregation(self):
        clock = Clock()

        class UnreadMetadata:
            @property
            def st_dev(self):
                raise AssertionError("Expired query metadata must not be aggregated")

        def slow_query(path):
            clock.value = 0.5
            return UnreadMetadata()

        with scripted([inventory(["a"])], slow_query, clock=clock) as env:
            with self.assert_deadline():
                scanner.output_bytes(ROOT)
        env.stat.assert_called_once_with(ROOT + r"\a")

    def test_end_of_inventory_deadline_rejects_incomplete_comparison(self):
        clock = Clock()

        def slow_finish(onerror):
            yield ROOT, [], ["a"]
            clock.value = 0.5

        with scripted([slow_finish], [metadata(1, 3)], clock=clock) as env:
            with self.assert_deadline():
                scanner.output_bytes(ROOT)
        self.assertEqual(env.walk.call_count, 1)

    def test_repeated_disappearance_uses_one_deadline_without_reset(self):
        clock = Clock()

        def vanished(path):
            clock.value += 0.2
            raise FileNotFoundError("fabricated recurring disappearance")

        with scripted([inventory(["a"])] * 3, vanished, clock=clock) as env:
            with self.assert_deadline():
                scanner.output_bytes(ROOT)
        self.assertEqual(env.walk.call_count, 3)
        self.assertEqual(env.stat.call_count, 3)

    def test_final_acceptance_rechecks_deadline_after_byte_arithmetic(self):
        clock = Clock()

        class SizeConsumesFinalTime(int):
            def __rmul__(self, count):
                clock.value = 0.5
                return count * int(self)

        size = SizeConsumesFinalTime(7)
        with scripted([inventory(["a"])] * 2,
                      [metadata(1, size), metadata(1, size)], clock=clock) as env:
            with self.assert_deadline():
                scanner.output_bytes(ROOT)
        self.assertEqual(env.walk.call_count, 2)
        self.assertEqual(env.stat.call_count, 2)


@unittest.skipUnless(os.name == "nt", "The approved physical fixture is Windows-only")
class SmallWindowsFilesystemTests(unittest.TestCase):
    def test_unicode_nested_long_name_and_hard_link_match_independent_stat_reference(self):
        with tempfile.TemporaryDirectory(prefix="pds_prefix_") as directory:
            root = Path(directory)
            nested = root / "nested" / "\u7403_\u7a7a\u9593"
            nested.mkdir(parents=True)
            original = root / "caf\u00e9_ball.bin"
            long_file = nested / ("frame_" + "x" * 80 + ".tmp")
            linked = nested / "hard_link.bin"
            empty = root / "empty.log"
            for path in (original, long_file, linked, empty):
                self.assertLessEqual(len(str(path)), 240)
            original.write_bytes(b"a" * 11)
            long_file.write_bytes(b"b" * 23)
            empty.write_bytes(b"")
            os.link(original, linked)
            first, second = os.stat(original), os.stat(linked)
            self.assertEqual((first.st_dev, first.st_ino), (second.st_dev, second.st_ino))
            # A stable, independent per-entry sum deliberately counts the hard link twice.
            expected = 0
            entries = 0
            for folder, _, names in os.walk(root):
                for name in names:
                    expected += os.stat(os.path.join(folder, name)).st_size
                    entries += 1
            self.assertEqual(entries, 4)
            self.assertEqual(expected, 45)
            self.assertEqual(scanner.output_bytes(root), expected)


if __name__ == "__main__":
    unittest.main()

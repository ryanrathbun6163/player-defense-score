"""Independent synthetic checks of the recovery scope and pre-model boundary."""
import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.ball_tracking import yolo_crop_recovery as recovery
from src.ball_tracking.development_experiments import read_json
from test_ball_yolo_crop_recovery import NEW_COMMIT, partial_fixture


class RecoveryGuardTests(unittest.TestCase):
    def _reject_before_model(self, root, path, m, p, inputs):
        factory = Mock(side_effect=AssertionError("Model construction crossed the guard"))
        reader = Mock(side_effect=AssertionError("Pixels crossed the guard"))
        with patch.object(recovery, "preflight", return_value=(m, p, inputs, NEW_COMMIT)), \
                patch.object(recovery, "unchanged"):
            with self.assertRaises(ValueError):
                recovery.run_experiment(root, path, adapter_factory=factory, png_reader=reader)
        factory.assert_not_called()
        reader.assert_not_called()

    def test_missing_extra_duplicate_and_misscoped_units_fail_before_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, m, p, inputs = partial_fixture(root)
            for scenario in ("missing_old", "missing_new", "extra_new", "duplicate_old", "duplicate_new", "wrong_window", "wrong_frame", "wrong_view", "old_commit"):
                contract = copy.deepcopy(inputs[0]["recovery"])
                old = contract["completed_crop_units_reuse_without_inference"]
                missing = contract["missing_crop_units_only_allowed_new_inference"]
                if scenario == "missing_old": old.pop()
                elif scenario == "missing_new": missing.pop()
                elif scenario == "extra_new": missing.append(copy.deepcopy(missing[0]))
                elif scenario == "duplicate_old": old[1] = copy.deepcopy(old[0])
                elif scenario == "duplicate_new": missing[1] = copy.deepcopy(missing[0])
                elif scenario == "wrong_window": missing[0]["window_id"] = "unauthorized_window"
                elif scenario == "wrong_frame": missing[0]["frame_index"] = 999
                elif scenario == "wrong_view": missing[0]["view_ordinal"] = 0
                else: old[0]["actual_inference_commit"] = NEW_COMMIT
                revised = [{**item, "recovery": contract} for item in inputs]
                with self.subTest(scenario=scenario):
                    self._reject_before_model(root, path, m, p, revised)

    def test_all_old_bytes_and_no_extra_original_file_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, m, p, inputs = partial_fixture(root)
            bindings = recovery.preserved_bindings(inputs[0]["recovery"])
            self.assertEqual(len(bindings), 561)
            self.assertEqual(len({b["path"] for b in bindings}), 561)
            checkpoint = root / inputs[0]["recovery"]["completed_crop_units_reuse_without_inference"][0]["checkpoint"]["path"]
            original = checkpoint.read_bytes()
            checkpoint.write_bytes(original + b" ")
            self._reject_before_model(root, path, m, p, inputs)
            checkpoint.write_bytes(original)
            # A disappeared bound file also stops before any model or PNG access.
            checkpoint.unlink()
            self._reject_before_model(root, path, m, p, inputs)
            checkpoint.write_bytes(original)
            extra = root / recovery.original.OUTPUT_ROOT / "unexpected_original_output.json"
            extra.write_text("{}", encoding="utf-8")
            self._reject_before_model(root, path, m, p, inputs)
            extra.unlink()
            old, missing = recovery.validate_partition(root, inputs[0]["recovery"], p)
            self.assertEqual((len(old), len(missing)), (175, 425))

    def test_copy_of_completed_old_unit_in_recovery_is_rejected_before_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, m, p, inputs = partial_fixture(root)
            first = inputs[0]["recovery"]["completed_crop_units_reuse_without_inference"][0]
            window = p["windows"][0]
            target = recovery.checkpoint_path(root, window, first["frame_index"], recovery.crop_views()[first["view_ordinal"]])
            target.parent.mkdir(parents=True)
            target.write_bytes((root / first["checkpoint"]["path"]).read_bytes())
            self._reject_before_model(root, path, m, p, inputs)

    def test_dirty_guard_runs_before_runtime_or_model_initialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, m, p, inputs = partial_fixture(root)
            old_m = inputs[0]["original_manifest"]
            with patch.object(recovery, "PROPOSAL_SHA", m["recovery_proposal"]["sha256"]), \
                    patch.object(recovery.original, "EXPECTED_PROPOSAL_SHA", old_m["proposal"]["sha256"]), \
                    patch.object(recovery, "clean_commit", side_effect=ValueError("synthetic dirty checkout")) as clean, \
                    patch.object(recovery.original, "preflight", side_effect=AssertionError("Runtime reached while dirty")) as original_preflight, \
                    patch.object(recovery.original, "create_adapter", side_effect=AssertionError("Model reached while dirty")) as factory:
                with self.assertRaisesRegex(ValueError, "dirty checkout"):
                    recovery.preflight(root, path)
            clean.assert_called_once()
            original_preflight.assert_not_called()
            factory.assert_not_called()

    def test_real_metadata_preflight_avoids_labels_and_source_video(self):
        from src.ball_tracking import annotations
        import cv2
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, m, p, inputs = partial_fixture(root)
            old_m = inputs[0]["original_manifest"]
            old_open = Path.open
            opened = []
            def guarded_open(target, *args, **kwargs):
                resolved = target.resolve()
                self.assertTrue(resolved.is_relative_to(root))
                relative = resolved.relative_to(root).as_posix()
                self.assertFalse(relative.startswith("configs/ball_tracking/annotations/"), "Preflight opened annotation content")
                self.assertNotEqual(resolved.suffix.lower(), ".mp4", "Preflight opened source video")
                opened.append(relative)
                return old_open(target, *args, **kwargs)
            with patch.object(recovery, "PROPOSAL_SHA", m["recovery_proposal"]["sha256"]), \
                    patch.object(recovery.original, "EXPECTED_PROPOSAL_SHA", old_m["proposal"]["sha256"]), \
                    patch.object(recovery, "clean_commit", return_value=NEW_COMMIT), \
                    patch.object(recovery.original, "clean_commit", return_value=NEW_COMMIT), \
                    patch.object(recovery, "_tracked"), patch.object(recovery.original, "_tracked"), \
                    patch.object(recovery.original, "inspect_runtime", return_value=(inputs[0]["weights_path"], inputs[0]["model"])) as runtime, \
                    patch.object(recovery.original.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                    patch.object(recovery.original, "create_adapter", side_effect=AssertionError("Preflight constructed model")), \
                    patch.object(annotations, "load_annotations", side_effect=AssertionError("Preflight loaded labels")), \
                    patch.object(cv2, "VideoCapture", side_effect=AssertionError("Preflight decoded video")), \
                    patch.object(cv2, "imdecode", side_effect=AssertionError("Preflight decoded pixels")), \
                    patch.object(Path, "open", new=guarded_open):
                loaded_m, loaded_p, actual_inputs, commit = recovery.preflight(root, path)
            self.assertEqual((loaded_m, loaded_p, commit), (m, p, NEW_COMMIT))
            self.assertEqual(len(actual_inputs), 6)
            self.assertEqual(sum(len(i["source_frames"]) for i in actual_inputs), 150)
            runtime.assert_called_once()
            self.assertTrue(any(name.endswith(".png") for name in opened), "Preflight must bind frozen PNG bytes without decoding them")
            self.assertTrue(all(item["recovery"] == inputs[0]["recovery"] for item in actual_inputs))


if __name__ == "__main__":
    unittest.main()

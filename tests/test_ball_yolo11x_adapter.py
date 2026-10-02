"""Independent synthetic checks for the frozen detector boundary."""
import copy
import hashlib
import logging
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.ball_tracking import yolo11x_adapter as a
from src.ball_tracking.detections import ModelProvenance


def model_provenance():
    return ModelProvenance(a.MODEL_NAME, "ultralytics", a.PACKAGE_VERSION, a.WEIGHTS_IDENTIFIER,
                           a.WEIGHTS_SHA256, "a" * 40, "cuda:0 synthetic", "float32", 640, 640,
                           a.RESIZE_MODE, False, 37, "sports ball", .01, a.POSTPROCESSING)


def result_fixture():
    # Input order deliberately differs from score/geometry ordering. The .01
    # boundary survives while .009 does not, and tied boxes retain native IDs.
    native = [([30., 40., 50., 60.], .01), ([8., 10., 18., 20.], .8),
              ([1., 2., 3., 4.], .009), ([8., 10., 18., 20.], .8)]
    returned = [{"postprocessor_index": i, "bbox_xyxy_px": box, "confidence": score, "source_class_id": 32}
                for i, (box, score) in enumerate(native)]
    return {"candidates": [
        {"candidate_index": 0, "class_id": 37, "class_name": "sports ball", "confidence": .8,
         "bbox_xyxy_px": [8., 10., 18., 20.], "center_xy_px": [13., 15.]},
        {"candidate_index": 1, "class_id": 37, "class_name": "sports ball", "confidence": .8,
         "bbox_xyxy_px": [8., 10., 18., 20.], "center_xy_px": [13., 15.]},
        {"candidate_index": 2, "class_id": 37, "class_name": "sports ball", "confidence": .01,
         "bbox_xyxy_px": [30., 40., 50., 60.], "center_xy_px": [40., 50.]}],
        "postprocessing": {"source_class_id": 32, "returned_candidates": returned,
                           "exported_candidate_sources": [{"candidate_index": 0, "postprocessor_index": 1},
                                                          {"candidate_index": 1, "postprocessor_index": 3},
                                                          {"candidate_index": 2, "postprocessor_index": 0}],
                           "cap_saturated": False, "input_transform": dict(a.INPUT_TRANSFORM)},
        "forward_accounting": {"synthetic_forwards": 2, "project_attempts": 1, "project_forwards": 1,
                               "this_project_attempt_forwards": 1, "preparation_complete": True}}


class TensorRows:
    def __init__(self, rows): self.rows = rows
    def detach(self): return self
    def cpu(self): return self
    def tolist(self): return self.rows


class FakeNetwork:
    def __init__(self):
        self.stride = TensorRows([8., 16., 32.])
        self.end2end = False
        self.dtype = "torch.float32"
        self.device_index = 0
    def parameters(self):
        return [types.SimpleNamespace(dtype=self.dtype, device=types.SimpleNamespace(type="cuda", index=self.device_index))]
    def register_forward_pre_hook(self, callback):
        self.callback = callback
        return object()
    def fire(self): self.callback(self, ())


class FakeYOLO:
    def __init__(self, path):
        self.model = FakeNetwork()
        self.task = "detect"
        self.names = {i: f"class{i}" for i in range(80)}
        self.names[32] = "sports ball"
        self.predictor = None
        self.images = []
        self.double_project_forward = False
        self.timeout = False
    def predict(self, image, **kwargs):
        self.images.append(image.copy())
        if self.predictor is None:
            copied = copy.deepcopy(self.model)
            copied.fire()  # Implicit vendor warmup, still on synthetic data.
            self.predictor = types.SimpleNamespace(done_warmup=True, args=types.SimpleNamespace(**kwargs),
                                                   model=types.SimpleNamespace(model=copied))
        elif self.double_project_forward:
            self.predictor.model.model.fire()
        self.predictor.model.model.fire()
        if self.timeout:
            logging.getLogger("synthetic_yolo_test").warning("NMS time limit 2.050s exceeded")
        raw = result_fixture()["postprocessing"]["returned_candidates"]
        rows = [r["bbox_xyxy_px"] + [r["confidence"], 32.] for r in raw]
        return [types.SimpleNamespace(orig_shape=(648, 1152), boxes=types.SimpleNamespace(data=TensorRows(rows)))]


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.fake_torch = types.SimpleNamespace(
            backends=types.SimpleNamespace(cuda=types.SimpleNamespace(matmul=types.SimpleNamespace(allow_tf32=True)),
                                          cudnn=types.SimpleNamespace(allow_tf32=True)),
            cuda=types.SimpleNamespace(synchronize=lambda x: None, reset_peak_memory_stats=lambda x: None,
                                      max_memory_allocated=lambda x: 123456))
        self.modules = {"torch": self.fake_torch, "torchvision": types.SimpleNamespace(ops=types.SimpleNamespace(nms=lambda: None)),
                        "ultralytics": types.ModuleType("ultralytics"),
                        "ultralytics.utils": types.SimpleNamespace(LOGGER=logging.getLogger("synthetic_yolo_test"))}
        self.patch_modules = patch.dict("sys.modules", self.modules)
        self.patch_modules.start()
        self.patch_hash = patch.object(a, "_hash", return_value=a.WEIGHTS_SHA256)
        self.patch_hash.start()
        self.addCleanup(self.patch_hash.stop)
        self.addCleanup(self.patch_modules.stop)

    def adapter(self):
        return a.YOLO11xAdapter(Path("dummy/yolo11x.pt"), {}, "a" * 40,
                               model_factory=FakeYOLO, runtime_inspector=lambda *args: model_provenance())

    def test_inclusive_floor_native_order_class_translation_and_duplicates(self):
        value = result_fixture()
        self.assertIs(a.validate_prediction(value, model_provenance()), value)
        self.assertEqual([c["confidence"] for c in value["candidates"]], [.8, .8, .01])
        self.assertEqual([r["postprocessor_index"] for r in value["postprocessing"]["exported_candidate_sources"]], [1, 3, 0])

    def test_no_implicit_project_warmup_and_actual_forward_accounting(self):
        adapter = self.adapter()
        pixels = np.full((648, 1152, 3), [200, 10, 30], dtype=np.uint8)
        with self.assertRaises(a.YOLOContractError): adapter.predict_frame(pixels)
        self.assertEqual(adapter.prepare()["synthetic_forwards"], 2)
        self.assertTrue(np.all(adapter._yolo.images[0] == 0))
        value = adapter.predict_frame(pixels)
        np.testing.assert_array_equal(adapter._yolo.images[1][0, 0], [30, 10, 200])
        self.assertEqual(value["forward_accounting"]["project_forwards"], 1)
        self.assertEqual(adapter.cuda_peak_allocated_bytes, 123456)
        self.assertEqual(len(adapter._yolo.images), 2)
        adapter.prepare()  # Idempotent preparation never repeats a forward.
        self.assertEqual(len(adapter._yolo.images), 2)

    def test_cold_changed_predictor_is_rejected_before_any_project_forward(self):
        for field, replacement in [("done_warmup", False), ("args", types.SimpleNamespace(**{**a.PREDICT_ARGS, "conf": .25}))]:
            adapter = self.adapter(); adapter.prepare()
            setattr(adapter._predictor, field, replacement)
            with self.assertRaises(a.YOLOContractError): adapter.predict_frame(np.zeros((648, 1152, 3), np.uint8))
            self.assertEqual(adapter.accounting["project_forwards"], 0)

    def test_double_forward_or_timeout_cannot_publish_prediction(self):
        for flag in ("double_project_forward", "timeout"):
            adapter = self.adapter(); adapter.prepare(); setattr(adapter._yolo, flag, True)
            with self.assertRaises(a.YOLOContractError): adapter.predict_frame(np.zeros((648, 1152, 3), np.uint8))
            self.assertEqual(adapter.accounting["project_attempts"], 1)

    def test_invalid_live_class_mapping_and_precision_are_rejected(self):
        adapter = self.adapter(); adapter.prepare(); adapter._yolo.names[32] = "surfboard"
        with self.assertRaises(a.YOLOContractError): adapter.predict_frame(np.zeros((648, 1152, 3), np.uint8))
        self.assertEqual(adapter.accounting["project_forwards"], 0)
        adapter = self.adapter(); adapter.prepare(); adapter._inference_network.dtype = "torch.float16"
        with self.assertRaises(a.YOLOContractError): adapter.predict_frame(np.zeros((648, 1152, 3), np.uint8))
        self.assertEqual(adapter.accounting["project_forwards"], 0)
        adapter = self.adapter(); adapter.prepare(); adapter._inference_network.device_index = 1
        with self.assertRaises(a.YOLOContractError): adapter.predict_frame(np.zeros((648, 1152, 3), np.uint8))
        self.assertEqual(adapter.accounting["project_forwards"], 0)

    def test_changed_weights_during_preparation_never_leave_adapter_ready(self):
        adapter = self.adapter()
        with patch.object(a, "_hash", return_value="0" * 64):
            with self.assertRaises(a.YOLOContractError): adapter.prepare()
        self.assertFalse(adapter.accounting["preparation_complete"])
        with self.assertRaises(a.YOLOContractError): adapter.prepare()
        with self.assertRaises(a.YOLOContractError): adapter.predict_frame(np.zeros((648,1152,3), np.uint8))

    def test_nonfinite_geometry_order_mapping_and_boolean_tampering_fail(self):
        mutations = [lambda v: v["postprocessing"]["returned_candidates"][0].update(confidence=float("nan")),
                     lambda v: v["postprocessing"]["returned_candidates"][0].update(bbox_xyxy_px=[0,0,0,4]),
                     lambda v: v["postprocessing"]["returned_candidates"][0].update(bbox_xyxy_px=[0,0,1153,4]),
                     lambda v: v["postprocessing"].update(source_class_id=37),
                     lambda v: v["postprocessing"]["exported_candidate_sources"][0].update(postprocessor_index=0),
                     lambda v: v["candidates"][0].update(candidate_index=False),
                     lambda v: v["postprocessing"].update(cap_saturated=True),
                     lambda v: v["postprocessing"]["input_transform"].update(pad_top_px=139),
                     lambda v: v["forward_accounting"].update(synthetic_forwards=0),
                     lambda v: v["forward_accounting"].update(this_project_attempt_forwards=2)]
        for mutate in mutations:
            value = copy.deepcopy(result_fixture()); mutate(value)
            with self.assertRaises((a.YOLOContractError, ValueError)): a.validate_prediction(value, model_provenance())

    def test_empty_result_remains_empty(self):
        value = result_fixture(); value["candidates"] = []
        value["postprocessing"]["returned_candidates"] = []
        value["postprocessing"]["exported_candidate_sources"] = []
        self.assertEqual(a.validate_prediction(value, model_provenance())["candidates"], [])

    def test_wrong_crop_shape_dtype_and_batch_are_rejected(self):
        adapter = self.adapter(); adapter.prepare()
        for array in [np.zeros((648,1152,3), np.float32), np.zeros((648,1151,3), np.uint8), np.zeros((1,648,1152,3), np.uint8)]:
            with self.assertRaises(a.YOLOContractError): adapter.predict_frame(array)
        self.assertEqual(adapter.accounting["project_forwards"], 0)


class RuntimeBindingTests(unittest.TestCase):
    def test_runtime_file_escape_and_changed_bytes_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve(); path=root/"data/outputs/ball_tracking/yolo11x_runtime/check.txt"
            path.parent.mkdir(parents=True); path.write_bytes(b"frozen")
            b={"path":path.relative_to(root).as_posix(),"sha256":hashlib.sha256(b"frozen").hexdigest()}
            self.assertEqual(a._root_path(root,b),path)
            path.write_bytes(b"changed")
            with self.assertRaises(a.YOLOContractError): a._root_path(root,b)
            with self.assertRaises(a.YOLOContractError): a._root_path(root,{"path":"../outside","sha256":"a"*64})

    def test_unvalidated_runtime_is_rejected_before_weight_or_library_access(self):
        with patch.object(a,"_root_path",side_effect=AssertionError("Must not reach files")):
            with self.assertRaises(a.YOLOContractError):
                a.inspect_runtime(Path("unused"),{"schema_version":"ball_yolo11x_runtime/v0.1","synthetic_validation":{"status":"pending"}},"a"*40)


if __name__ == "__main__":
    unittest.main()

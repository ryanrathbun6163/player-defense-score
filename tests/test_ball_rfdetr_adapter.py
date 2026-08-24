import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from src.ball_tracking.rfdetr_adapter import (
    INPUT_HEIGHT_PX,
    INPUT_WIDTH_PX,
    MIN_EXPORT_CONFIDENCE_FLOOR,
    NUM_SELECT,
    PACKAGE_VERSION,
    POSTPROCESSING_DESCRIPTION,
    PREDICT_THRESHOLD,
    RESIZE_MODE,
    RFDETRAdapterError,
    RFDETRBallAdapter,
    RFDETRCandidateError,
    RFDETRModelContractError,
    TARGET_CLASS_ID,
    TARGET_CLASS_NAME,
    TARGET_CLASS_NAME_INDEX,
    WEIGHTS_IDENTIFIER,
    WEIGHTS_SHA256,
    adapt_rfdetr_candidates,
    validate_coco_class_mapping,
    validate_export_confidence_floor,
    validate_loaded_model,
)


TEST_WEIGHTS_PATH = (
    Path.cwd() / "synthetic-model-cache" / WEIGHTS_IDENTIFIER
).resolve()


def frozen_weights_hasher(_weights_path):
    return WEIGHTS_SHA256


class FakeDetections:
    def __init__(self, boxes, confidences, class_ids, class_names):
        self.xyxy = boxes
        self.confidence = confidences
        self.class_id = class_ids
        self.data = {"class_name": class_names}


class FakeParameter:
    def __init__(self, dtype="torch.float32"):
        self.dtype = dtype


class FakeRFDETRMedium:
    def __init__(self, detections=None, *, weights_path=TEST_WEIGHTS_PATH):
        self.size = "rfdetr-medium"
        self.model_config = SimpleNamespace(
            resolution=576,
            device="cuda",
            num_queries=300,
            num_classes=90,
            num_select=27300,
            pretrain_weights=str(weights_path),
        )
        self._is_optimized_for_inference = False
        live_model = SimpleNamespace(
            num_queries=300,
            class_embed=SimpleNamespace(out_features=91),
            parameters=lambda: iter([FakeParameter(), FakeParameter()]),
        )
        self.model = SimpleNamespace(
            device="cuda",
            resolution=576,
            postprocess=SimpleNamespace(num_select=27300),
            model=live_model,
            args=SimpleNamespace(num_classes=90),
        )
        self.class_names = [f"class-{index}" for index in range(80)]
        self.class_names[TARGET_CLASS_NAME_INDEX] = TARGET_CLASS_NAME
        self.detections = (
            detections
            if detections is not None
            else FakeDetections([], [], [], [])
        )
        self.predict_calls = []

    def predict(self, frame, **kwargs):
        self.predict_calls.append((frame, kwargs))
        return self.detections


def fake_detections(
    boxes=None,
    confidences=None,
    class_ids=None,
    class_names=None,
):
    return FakeDetections(
        [] if boxes is None else boxes,
        [] if confidences is None else confidences,
        [] if class_ids is None else class_ids,
        [] if class_names is None else class_names,
    )


def fake_coco_mapping():
    missing_category_ids = {12, 26, 29, 30, 45, 66, 68, 69, 71, 83}
    category_ids = [
        category_id
        for category_id in range(1, 91)
        if category_id not in missing_category_ids
    ]
    class_names = [f"class-{index}" for index in range(80)]
    class_names[TARGET_CLASS_NAME_INDEX] = TARGET_CLASS_NAME
    category_id_to_name = dict(zip(category_ids, class_names))
    return category_id_to_name, class_names


class CandidateAdaptationTests(unittest.TestCase):
    def test_frozen_candidate_contract(self):
        self.assertEqual(TARGET_CLASS_ID, 37)
        self.assertEqual(TARGET_CLASS_NAME, "sports ball")
        self.assertEqual((INPUT_HEIGHT_PX, INPUT_WIDTH_PX), (576, 576))
        self.assertEqual(NUM_SELECT, 300 * 91)
        self.assertEqual(PREDICT_THRESHOLD, 0.0)
        self.assertEqual(MIN_EXPORT_CONFIDENCE_FLOOR, 0.01)
        self.assertEqual(PACKAGE_VERSION, "1.9.1")
        self.assertEqual(WEIGHTS_IDENTIFIER, "rf-detr-medium.pth")
        self.assertEqual(
            WEIGHTS_SHA256,
            "749ff6071828aaffac63e204c4f4135ed3d6cdae4d702e086c360edc3b5768c8",
        )
        self.assertEqual(
            RESIZE_MODE,
            "direct RGB bilinear resize to 576x576 without letterboxing or "
            "padding; antialias disabled; ImageNet channel normalization",
        )
        self.assertEqual(
            POSTPROCESSING_DESCRIPTION,
            "RF-DETR sigmoid scores with all 300 query x 91 logit pairs "
            "selected (num_select=27300); source-pixel box scaling and "
            "clipping; raw COCO class ID 37/name 'sports ball' filtering; "
            "adapter-side inclusive confidence-floor filtering; deterministic "
            "ordering; no NMS, ROI/court filter, tiling, temporal logic, "
            "deduplication, or top-one selection",
        )

    def test_filters_non_target_and_below_floor_but_keeps_exact_floor(self):
        detections = fake_detections(
            boxes=[
                [1.0, 2.0, 5.0, 6.0],
                [10.0, 20.0, 30.0, 40.0],
                [50.0, 60.0, 70.0, 80.0],
            ],
            confidences=[0.99, 0.009999, 0.01],
            class_ids=[1, TARGET_CLASS_ID, TARGET_CLASS_ID],
            class_names=["person", TARGET_CLASS_NAME, TARGET_CLASS_NAME],
        )

        adapted = adapt_rfdetr_candidates(
            detections,
            source_width_px=100,
            source_height_px=90,
        )

        self.assertEqual(len(adapted), 1)
        self.assertEqual(adapted[0].candidate_index, 0)
        self.assertEqual(adapted[0].confidence, 0.01)
        self.assertEqual(adapted[0].class_id, TARGET_CLASS_ID)
        self.assertEqual(adapted[0].class_name, TARGET_CLASS_NAME)

    def test_clips_to_source_bounds_and_recomputes_midpoint(self):
        detections = fake_detections(
            boxes=[[-5.0, -3.0, 110.0, 95.0]],
            confidences=[0.5],
            class_ids=[TARGET_CLASS_ID],
            class_names=[TARGET_CLASS_NAME],
        )

        adapted = adapt_rfdetr_candidates(
            detections,
            source_width_px=100,
            source_height_px=90,
        )

        self.assertEqual(adapted[0].bbox_xyxy_px, (0.0, 0.0, 100.0, 90.0))
        self.assertEqual(adapted[0].center_xy_px, (50.0, 45.0))

    def test_deterministic_sort_retains_duplicates_and_original_tie_order(self):
        detections = fake_detections(
            boxes=[
                [20.0, 1.0, 30.0, 11.0],
                [10.0, 1.0, 20.0, 11.0],
                [5.0, 2.0, 15.0, 12.0],
                [5.0, 2.0, 15.0, 12.0],
            ],
            confidences=[0.7, 0.7, 0.8, 0.8],
            class_ids=[TARGET_CLASS_ID] * 4,
            class_names=[TARGET_CLASS_NAME] * 4,
        )

        adapted = adapt_rfdetr_candidates(
            detections,
            source_width_px=100,
            source_height_px=90,
        )

        self.assertEqual([item.candidate_index for item in adapted], [0, 1, 2, 3])
        self.assertEqual(
            [item.bbox_xyxy_px for item in adapted],
            [
                (5.0, 2.0, 15.0, 12.0),
                (5.0, 2.0, 15.0, 12.0),
                (10.0, 1.0, 20.0, 11.0),
                (20.0, 1.0, 30.0, 11.0),
            ],
        )

    def test_empty_detection_arrays_are_valid(self):
        self.assertEqual(
            adapt_rfdetr_candidates(
                fake_detections(),
                source_width_px=100,
                source_height_px=90,
            ),
            (),
        )

    def test_ignores_empty_name_for_unmapped_non_target_coco_slot(self):
        detections = fake_detections(
            boxes=[[1.0, 2.0, 3.0, 4.0]],
            confidences=[0.9],
            class_ids=[0],
            class_names=[""],
        )

        self.assertEqual(
            adapt_rfdetr_candidates(
                detections,
                source_width_px=100,
                source_height_px=90,
            ),
            (),
        )

    def test_rejects_parallel_array_length_mismatch(self):
        detections = fake_detections(
            boxes=[[1.0, 2.0, 3.0, 4.0]],
            confidences=[],
            class_ids=[TARGET_CLASS_ID],
            class_names=[TARGET_CLASS_NAME],
        )

        with self.assertRaisesRegex(
            RFDETRCandidateError,
            "identical lengths",
        ):
            adapt_rfdetr_candidates(
                detections,
                source_width_px=100,
                source_height_px=90,
            )

    def test_rejects_missing_or_malformed_arrays(self):
        detections = fake_detections()

        for attribute in ("xyxy", "confidence", "class_id"):
            with self.subTest(attribute=attribute):
                broken = fake_detections()
                delattr(broken, attribute)

                with self.assertRaises(RFDETRCandidateError):
                    adapt_rfdetr_candidates(
                        broken,
                        source_width_px=100,
                        source_height_px=90,
                    )

        detections.data = {}

        with self.assertRaisesRegex(RFDETRCandidateError, "class_name"):
            adapt_rfdetr_candidates(
                detections,
                source_width_px=100,
                source_height_px=90,
            )

    def test_rejects_wrong_box_shape(self):
        detections = fake_detections(
            boxes=[[1.0, 2.0, 3.0]],
            confidences=[0.5],
            class_ids=[TARGET_CLASS_ID],
            class_names=[TARGET_CLASS_NAME],
        )

        with self.assertRaisesRegex(RFDETRCandidateError, "four coordinates"):
            adapt_rfdetr_candidates(
                detections,
                source_width_px=100,
                source_height_px=90,
            )

    def test_rejects_nonfinite_candidate_numbers_before_filtering(self):
        cases = (
            ([math.nan, 2.0, 3.0, 4.0], 0.5, 1, "person"),
            ([1.0, 2.0, 3.0, math.inf], 0.5, 1, "person"),
            ([1.0, 2.0, 3.0, 4.0], math.nan, 1, "person"),
        )

        for box, confidence, class_id, class_name in cases:
            with self.subTest(box=box, confidence=confidence):
                detections = fake_detections(
                    boxes=[box],
                    confidences=[confidence],
                    class_ids=[class_id],
                    class_names=[class_name],
                )

                with self.assertRaises(RFDETRCandidateError):
                    adapt_rfdetr_candidates(
                        detections,
                        source_width_px=100,
                        source_height_px=90,
                    )

    def test_rejects_invalid_confidence_range(self):
        for confidence in (-0.01, 1.01):
            with self.subTest(confidence=confidence):
                detections = fake_detections(
                    boxes=[[1.0, 2.0, 3.0, 4.0]],
                    confidences=[confidence],
                    class_ids=[1],
                    class_names=["person"],
                )

                with self.assertRaisesRegex(RFDETRCandidateError, "\[0, 1\]"):
                    adapt_rfdetr_candidates(
                        detections,
                        source_width_px=100,
                        source_height_px=90,
                    )

    def test_rejects_both_target_class_mismatch_directions(self):
        cases = (
            (TARGET_CLASS_ID, "person"),
            (1, TARGET_CLASS_NAME),
        )

        for class_id, class_name in cases:
            with self.subTest(class_id=class_id, class_name=class_name):
                detections = fake_detections(
                    boxes=[[1.0, 2.0, 3.0, 4.0]],
                    confidences=[0.5],
                    class_ids=[class_id],
                    class_names=[class_name],
                )

                with self.assertRaisesRegex(
                    RFDETRCandidateError,
                    "inconsistent target class",
                ):
                    adapt_rfdetr_candidates(
                        detections,
                        source_width_px=100,
                        source_height_px=90,
                    )

    def test_rejects_target_box_degenerate_after_clipping(self):
        cases = (
            [-10.0, 5.0, -1.0, 10.0],
            [5.0, 100.0, 10.0, 110.0],
            [8.0, 5.0, 8.0, 10.0],
            [10.0, 5.0, 8.0, 10.0],
        )

        for box in cases:
            with self.subTest(box=box):
                detections = fake_detections(
                    boxes=[box],
                    confidences=[0.5],
                    class_ids=[TARGET_CLASS_ID],
                    class_names=[TARGET_CLASS_NAME],
                )

                with self.assertRaisesRegex(
                    RFDETRCandidateError,
                    "degenerate",
                ):
                    adapt_rfdetr_candidates(
                        detections,
                        source_width_px=100,
                        source_height_px=90,
                    )

    def test_rejects_invalid_source_dimensions(self):
        for width, height in ((0, 90), (100, 0), (100.0, 90), (True, 90)):
            with self.subTest(width=width, height=height):
                with self.assertRaises(RFDETRCandidateError):
                    adapt_rfdetr_candidates(
                        fake_detections(),
                        source_width_px=width,
                        source_height_px=height,
                    )

    def test_export_floor_must_equal_frozen_point01_exactly(self):
        self.assertEqual(validate_export_confidence_floor(0.01), 0.01)

        for value in (
            0.0,
            0.009999,
            0.010001,
            0.5,
            1.0,
            1.01,
            -1.0,
            math.nan,
            math.inf,
            True,
        ):
            with self.subTest(value=value):
                with self.assertRaises(RFDETRCandidateError):
                    validate_export_confidence_floor(value)


class ModelContractTests(unittest.TestCase):
    def test_accepts_sparse_coco_sports_ball_mapping(self):
        category_ids, class_names = fake_coco_mapping()

        validate_coco_class_mapping(category_ids, class_names)

    def test_rejects_changed_or_duplicate_coco_mapping(self):
        category_id_to_name, class_names = fake_coco_mapping()

        for mutator in (
            lambda mapping, names: mapping.__setitem__(
                TARGET_CLASS_ID,
                "baseball",
            ),
            lambda mapping, names: names.__setitem__(
                TARGET_CLASS_NAME_INDEX,
                "baseball",
            ),
            lambda mapping, names: mapping.__setitem__(1, TARGET_CLASS_NAME),
        ):
            with self.subTest(mutator=mutator):
                changed_mapping = dict(category_id_to_name)
                changed_names = list(class_names)
                mutator(changed_mapping, changed_names)

                with self.assertRaises(RFDETRModelContractError):
                    validate_coco_class_mapping(changed_mapping, changed_names)

    def test_rejects_sequence_in_place_of_package_coco_mapping(self):
        category_id_to_name, class_names = fake_coco_mapping()

        with self.assertRaisesRegex(
            RFDETRModelContractError,
            "category-ID-to-name mapping",
        ):
            validate_coco_class_mapping(
                list(category_id_to_name),
                class_names,
            )

    def test_accepts_frozen_loaded_model_contract(self):
        validate_loaded_model(FakeRFDETRMedium(), TEST_WEIGHTS_PATH)

    def test_rejects_changed_model_configuration(self):
        cases = (
            ("size", "rfdetr-small"),
            ("model_config.resolution", 640),
            ("model_config.device", "cpu"),
            ("model_config.num_queries", 299),
            ("model_config.num_classes", 80),
            ("model_config.num_select", 300),
            ("model_config.pretrain_weights", "other.pth"),
            ("_is_optimized_for_inference", True),
            ("model.device", "cpu"),
            ("model.resolution", 640),
            ("model.postprocess.num_select", 300),
            ("model.model.num_queries", 299),
            ("model.model.class_embed.out_features", 90),
            ("model.args.num_classes", 80),
            (f"class_names.{TARGET_CLASS_NAME_INDEX}", "baseball"),
        )

        for path, value in cases:
            with self.subTest(path=path, value=value):
                model = FakeRFDETRMedium()
                parts = path.split(".")
                target = model

                for part in parts[:-1]:
                    if part == "class_names":
                        target = model.class_names
                    else:
                        target = getattr(target, part)

                final = parts[-1]

                if isinstance(target, list):
                    target[int(final)] = value
                else:
                    setattr(target, final, value)

                with self.assertRaises(RFDETRModelContractError):
                    validate_loaded_model(model, TEST_WEIGHTS_PATH)

    def test_rejects_same_weights_basename_at_a_different_resolved_path(self):
        different_path = (
            TEST_WEIGHTS_PATH.parent / "different-cache" / WEIGHTS_IDENTIFIER
        ).resolve()
        model = FakeRFDETRMedium(weights_path=different_path)

        with self.assertRaisesRegex(
            RFDETRModelContractError,
            "exact preflight-verified path",
        ):
            validate_loaded_model(model, TEST_WEIGHTS_PATH)

    def test_rejects_nonabsolute_or_unresolved_expected_weights_path(self):
        invalid_paths = (
            Path(WEIGHTS_IDENTIFIER),
            TEST_WEIGHTS_PATH.parent
            / ".."
            / TEST_WEIGHTS_PATH.parent.name
            / WEIGHTS_IDENTIFIER,
        )

        for weights_path in invalid_paths:
            with self.subTest(weights_path=weights_path):
                with self.assertRaises(RFDETRModelContractError):
                    validate_loaded_model(FakeRFDETRMedium(), weights_path)

    def test_rejects_non_fp32_parameters(self):
        model = FakeRFDETRMedium()
        model.model.model.parameters = lambda: iter(
            [FakeParameter("torch.float16")]
        )

        with self.assertRaisesRegex(
            RFDETRModelContractError,
            "torch.float32",
        ):
            validate_loaded_model(model, TEST_WEIGHTS_PATH)


class AdapterPredictionTests(unittest.TestCase):
    def test_hashes_exact_weights_path_before_and_after_lazy_construction(self):
        hash_calls = []
        factory_calls = []

        def hasher(weights_path):
            hash_calls.append(weights_path)
            return WEIGHTS_SHA256

        def factory(weights_path):
            factory_calls.append(weights_path)
            return FakeRFDETRMedium(weights_path=weights_path)

        adapter = RFDETRBallAdapter(
            weights_path=TEST_WEIGHTS_PATH,
            model_factory=factory,
            weights_hasher=hasher,
        )
        self.assertEqual(hash_calls, [])
        self.assertEqual(factory_calls, [])

        first = adapter._get_model()
        second = adapter._get_model()

        self.assertIs(first, second)
        self.assertEqual(hash_calls, [TEST_WEIGHTS_PATH, TEST_WEIGHTS_PATH])
        self.assertEqual(factory_calls, [TEST_WEIGHTS_PATH])

    def test_rejects_weights_mismatch_before_model_factory_runs(self):
        factory_calls = []
        adapter = RFDETRBallAdapter(
            weights_path=TEST_WEIGHTS_PATH,
            model_factory=lambda weights_path: factory_calls.append(weights_path),
            weights_hasher=lambda weights_path: "0" * 64,
        )

        with self.assertRaisesRegex(
            RFDETRModelContractError,
            "mismatch before model construction",
        ):
            adapter._get_model()

        self.assertEqual(factory_calls, [])

    def test_rejects_weights_change_after_model_construction(self):
        observed_hashes = iter((WEIGHTS_SHA256, "0" * 64))
        factory_calls = []

        def factory(weights_path):
            factory_calls.append(weights_path)
            return FakeRFDETRMedium(weights_path=weights_path)

        adapter = RFDETRBallAdapter(
            weights_path=TEST_WEIGHTS_PATH,
            model_factory=factory,
            weights_hasher=lambda weights_path: next(observed_hashes),
        )

        with self.assertRaisesRegex(
            RFDETRModelContractError,
            "mismatch after model construction",
        ):
            adapter._get_model()

        self.assertEqual(factory_calls, [TEST_WEIGHTS_PATH])

    def test_default_hasher_rejects_real_tiny_nonfrozen_file_lazily(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            weights_path = (Path(temp_dir) / WEIGHTS_IDENTIFIER).resolve()
            weights_path.write_bytes(b"not the frozen RF-DETR checkpoint")
            factory_calls = []
            adapter = RFDETRBallAdapter(
                weights_path=weights_path,
                model_factory=(
                    lambda path: factory_calls.append(path)
                ),
            )

            self.assertEqual(factory_calls, [])
            with self.assertRaisesRegex(
                RFDETRModelContractError,
                "mismatch before model construction",
            ):
                adapter._get_model()

            self.assertEqual(factory_calls, [])

    def test_default_factory_imports_lazily_and_passes_frozen_constructor_args(self):
        category_ids, class_names = fake_coco_mapping()
        fake_rfdetr = ModuleType("rfdetr")
        fake_assets = ModuleType("rfdetr.assets")
        fake_coco_classes = ModuleType("rfdetr.assets.coco_classes")
        constructor_calls = []

        def constructor(**kwargs):
            constructor_calls.append(kwargs)
            return FakeRFDETRMedium(
                weights_path=Path(kwargs["pretrain_weights"]),
            )

        fake_rfdetr.RFDETRMedium = constructor
        fake_coco_classes.COCO_CLASSES = category_ids
        fake_coco_classes.COCO_CLASS_NAMES = class_names
        fake_modules = {
            "rfdetr": fake_rfdetr,
            "rfdetr.assets": fake_assets,
            "rfdetr.assets.coco_classes": fake_coco_classes,
        }
        adapter = RFDETRBallAdapter(
            weights_path=TEST_WEIGHTS_PATH,
            weights_hasher=frozen_weights_hasher,
        )

        with patch("importlib.metadata.version", return_value="1.9.1"):
            with patch.dict(sys.modules, fake_modules):
                model = adapter._get_model()

        self.assertIsInstance(model, FakeRFDETRMedium)
        self.assertEqual(
            constructor_calls,
            [
                {
                    "device": "cuda",
                    "resolution": 576,
                    "num_select": 27300,
                    "pretrain_weights": str(TEST_WEIGHTS_PATH),
                }
            ],
        )

    def test_default_factory_rejects_unfrozen_package_version_before_import(self):
        adapter = RFDETRBallAdapter(
            weights_path=TEST_WEIGHTS_PATH,
            weights_hasher=frozen_weights_hasher,
        )

        with patch("importlib.metadata.version", return_value="1.9.2"):
            with self.assertRaisesRegex(
                RFDETRModelContractError,
                "version",
            ):
                adapter._get_model()

    def test_model_construction_is_lazy_cached_and_prediction_is_frozen(self):
        detections = fake_detections(
            boxes=[[-1.0, 2.0, 21.0, 8.0]],
            confidences=[0.01],
            class_ids=[TARGET_CLASS_ID],
            class_names=[TARGET_CLASS_NAME],
        )
        model = FakeRFDETRMedium(detections)
        factory_calls = []

        def factory(weights_path):
            factory_calls.append(weights_path)
            return model

        adapter = RFDETRBallAdapter(
            weights_path=TEST_WEIGHTS_PATH,
            model_factory=factory,
            weights_hasher=frozen_weights_hasher,
        )
        self.assertEqual(factory_calls, [])
        frame = np.zeros((10, 20, 3), dtype=np.uint8)

        first = adapter.predict_frame(frame)
        second = adapter.predict_frame(frame)

        self.assertEqual(factory_calls, [TEST_WEIGHTS_PATH])
        self.assertEqual(len(model.predict_calls), 2)
        self.assertIs(model.predict_calls[0][0], frame)
        self.assertEqual(
            model.predict_calls[0][1],
            {
                "threshold": 0.0,
                "shape": (576, 576),
                "include_source_image": False,
            },
        )
        self.assertEqual(first, second)
        self.assertEqual(first[0].bbox_xyxy_px, (0.0, 2.0, 20.0, 8.0))
        self.assertEqual(first[0].center_xy_px, (10.0, 5.0))

    def test_rejects_non_single_rgb_uint8_input_before_model_load(self):
        factory_calls = []
        adapter = RFDETRBallAdapter(
            weights_path=TEST_WEIGHTS_PATH,
            model_factory=lambda weights_path: factory_calls.append(weights_path),
            weights_hasher=frozen_weights_hasher,
        )
        cases = (
            [[[]]],
            np.zeros((10, 20), dtype=np.uint8),
            np.zeros((2, 10, 20, 3), dtype=np.uint8),
            np.zeros((10, 20, 4), dtype=np.uint8),
            np.zeros((10, 20, 3), dtype=np.float32),
            np.zeros((0, 20, 3), dtype=np.uint8),
        )

        for frame in cases:
            with self.subTest(shape=getattr(frame, "shape", None)):
                with self.assertRaises(RFDETRAdapterError):
                    adapter.predict_frame(frame)

        self.assertEqual(factory_calls, [])

    def test_rejects_batched_model_result(self):
        model = FakeRFDETRMedium()
        model.detections = [fake_detections()]
        adapter = RFDETRBallAdapter(
            weights_path=TEST_WEIGHTS_PATH,
            model_factory=lambda weights_path: model,
            weights_hasher=frozen_weights_hasher,
        )

        with self.assertRaisesRegex(RFDETRCandidateError, "batched"):
            adapter.predict_frame(np.zeros((10, 20, 3), dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()

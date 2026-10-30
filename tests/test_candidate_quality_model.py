"""CPU metadata/geometry only: no Torch import, model construction or forward."""
import ast
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from src.ball_tracking import candidate_quality_model as model
from src.ball_tracking.nba_appearance_feature_screen import crop_and_preprocess
from src.ball_tracking.point_feature_inference import point_readout


ROOT = Path(__file__).resolve().parents[1]


class CandidateQualityModelTests(unittest.TestCase):
    def test_import_and_guard_never_import_torch(self):
        source = ("import sys; from PIL import Image; from src.ball_tracking import candidate_quality_model as m; "
                  "assert 'torch' not in sys.modules;\n"
                  "try: m.build_model('.', execution_authorized=False)\n"
                  "except ValueError: pass\n"
                  "else: raise AssertionError('missing execution guard')\n"
                  "m.preprocess(Image.new('RGB', (64, 64)), [32., 32.]); "
                  "assert 'torch' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", source], cwd=ROOT,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_original_pixel_producer_and_fractional_point_transport(self):
        yy, xx = np.indices((91, 107))
        image = Image.fromarray(np.stack((xx % 256, yy % 256, (xx+yy) % 256), axis=-1).astype(np.uint8))
        for center in ([40., 41.], [40.25, 41.75], [0., 0.], [106.999, 90.999]):
            actual, weights = model.preprocess(image, center)
            expected = crop_and_preprocess(image, center)[2]
            self.assertTrue(np.array_equal(actual, expected))
            geometry = model.point_geometry(center, *image.size)
            # Independent patch-center barycentric reconstruction.
            patch_centers = np.array([[104.5, 104.5], [118.5, 104.5],
                                      [104.5, 118.5], [118.5, 118.5]])
            self.assertTrue(np.allclose(np.asarray(geometry["weights"]) @ patch_centers,
                                        geometry["point_input_xy"], atol=1e-12, rtol=0))
            self.assertEqual(weights.dtype, np.float64)
            self.assertLess(abs(float(weights.sum())-1), 1e-12)

    def test_prior_point_consumer_uses_same_raw_token_weighting(self):
        tokens = (np.arange(4*384, dtype=np.float32).reshape(4, 384)-500)/200
        geometry = model.point_geometry([70.6, 52.2], 130, 110)
        old_geometry = {"tokens": [{"sequence_index": i, "weight": w}
                                   for i, w in zip(geometry["token_indices"], geometry["weights"])]}
        raw, unit, reason = point_readout(tokens, old_geometry)
        expected = np.asarray(geometry["weights"]) @ tokens.astype(np.float64)
        self.assertIsNone(reason)
        self.assertTrue(np.allclose(raw, expected, atol=1e-12, rtol=0))
        self.assertTrue(np.allclose(unit, expected/np.linalg.norm(expected), atol=1e-12, rtol=0))

    def test_out_of_bounds_and_nonfinite_fail_closed_padding_is_explicit(self):
        for center in ([-.01, 1], [100, 1], [1, 80], [math.nan, 2], [1, math.inf], [1]):
            with self.assertRaises(ValueError):
                model.point_geometry(center, 100, 80)
        self.assertFalse(model.point_geometry([0, 0], 100, 80)["complete_source_crop"])
        self.assertTrue(model.point_geometry([50, 40], 100, 80)["complete_source_crop"])

    def test_real_producer_header_parameter_contract_without_torch(self):
        shapes = model.read_weight_shapes(ROOT / model.WEIGHTS)
        contract = model.parameter_contract(shapes)
        self.assertEqual(contract["trainable_parameters"], 3_600_641)
        self.assertEqual(sum(math.prod(s) for n, s in contract["trainable_shapes"].items()
                             if n.startswith("backbone.encoder.layer.")), 3_550_464)
        self.assertFalse(model.is_trainable_name("backbone.encoder.layer.1.norm1.weight"))
        self.assertFalse(model.is_trainable_name("backbone.encoder.layer.100.norm1.weight"))
        self.assertFalse(model.is_trainable_name("head.unknown.weight"))
        changed = dict(shapes)
        changed.pop("embeddings.cls_token")
        with self.assertRaises(ValueError):
            model.parameter_contract(changed)

    def test_bad_safetensor_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.safetensors"
            header = json.dumps({"x": {"dtype": "F16", "shape": [1]}}).encode()
            path.write_bytes(struct.pack("<Q", len(header))+header)
            with self.assertRaises(ValueError):
                model.read_weight_shapes(path)

    def test_lazy_paths_compile_without_execution(self):
        path = ROOT / "src/ball_tracking/candidate_quality_model.py"
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom))
                             and "torch" in ast.unparse(n) for n in tree.body))


if __name__ == "__main__":
    unittest.main()

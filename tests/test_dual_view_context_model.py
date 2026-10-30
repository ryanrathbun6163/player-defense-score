"""CPU synthetic tensors only: no pretrained model load or GPU initialization."""
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

import numpy as np
from PIL import Image

from src.ball_tracking import dual_view_context_model as model_api

ROOT = Path(__file__).resolve().parents[1]


class MetadataAndPixelsTests(unittest.TestCase):
    def test_import_and_execution_guard_precede_torch(self):
        script = ('import sys; from src.ball_tracking import dual_view_context_model as m; '
                  'assert "torch" not in sys.modules; '
                  '\ntry: m.build_model("missing")\nexcept ValueError: pass\nelse: raise AssertionError()\n'
                  'assert "torch" not in sys.modules')
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_parameter_contract_uses_generic_header_and_new_head(self):
        from src.ball_tracking import candidate_quality_model as old
        shapes = old.read_weight_shapes(ROOT/old.WEIGHTS)
        contract = old.parameter_contract(shapes)
        shapes = {n: s for n, s in contract['all_shapes'].items() if n.startswith('backbone.')}
        shapes.update(model_api.HEAD_SHAPES)
        self.assertEqual(sum(np.prod(s) for n, s in shapes.items() if model_api.is_trainable_name(n)), 3698945)
        self.assertEqual(sum(np.prod(s) for s in model_api.HEAD_SHAPES.values()), 147713)
        self.assertFalse(model_api.is_trainable_name('backbone.encoder.layer.9.attention.weight'))
        self.assertTrue(model_api.is_trainable_name('backbone.encoder.layer.10.attention.weight'))
        self.assertFalse(model_api.is_trainable_name('backbone.embeddings.cls_token'))

    def test_local_exact_original_pixels_context_direct_resize(self):
        from src.ball_tracking.nba_appearance_feature_screen import crop_and_preprocess
        rng = np.random.default_rng(7)
        local = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
        expected = crop_and_preprocess(Image.fromarray(local), [32., 32.])[2]
        np.testing.assert_array_equal(model_api.preprocess_raw(local, 'LL'), expected)
        context = rng.integers(0, 256, (192, 192, 3), dtype=np.uint8)
        resized = np.asarray(Image.fromarray(context).resize((224, 224), Image.Resampling.BICUBIC), dtype=np.float32)/255.
        expected = ((resized-np.array([.485, .456, .406], np.float32))/np.array([.229, .224, .225], np.float32)).transpose(2, 0, 1)
        np.testing.assert_array_equal(model_api.preprocess_raw(context, 'LC'), expected)
        for invalid, arm in ((local, 'LC'), (context, 'LL'), (context.astype(np.float32), 'LC')):
            with self.assertRaises(ValueError):
                model_api.preprocess_raw(invalid, arm)


class SyntheticTensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        import torch
        cls.torch = torch
        assert not torch.cuda.is_initialized()
        torch.set_num_threads(2)

    def tearDown(self):
        self.assertFalse(self.torch.cuda.is_initialized())

    def test_readout_matches_original_consumer_and_normalizes_after_interpolation(self):
        torch = self.torch
        from src.ball_tracking.point_feature_inference import point_readout
        torch.manual_seed(3)
        sequence = torch.randn(2, 257, 384, dtype=torch.float32, requires_grad=True)
        weights = torch.tensor([[.1, .2, .3, .4], [.4, .3, .2, .1]], dtype=torch.float64)
        point, cls = model_api.normalized_readouts(sequence, weights)
        for i in range(2):
            geometry = {'tokens': [{'sequence_index': index, 'weight': float(weight)}
                                   for index, weight in zip(model_api.TOKEN_INDICES, weights[i])]}
            _, unit, reason = point_readout(sequence[i, list(model_api.TOKEN_INDICES)].detach().numpy(), geometry)
            self.assertIsNone(reason)
            np.testing.assert_allclose(point[i].detach().numpy(), unit, atol=1e-14, rtol=1e-14)
        np.testing.assert_allclose(torch.linalg.vector_norm(cls, dim=1).detach().numpy(), 1., atol=1e-14)
        local = torch.ones(2, 384, dtype=torch.float64)/np.sqrt(384)
        fused = model_api.fuse_features(local, point, cls)
        self.assertEqual(fused.dtype, torch.float32)
        self.assertEqual(tuple(fused.shape), (2, 1152))
        self.assertTrue(torch.equal(fused[:, :384], local.float()))
        self.assertTrue(torch.equal(fused[:, 384:768], point.float()))
        self.assertTrue(torch.equal(fused[:, 768:], cls.float()))
        np.testing.assert_allclose(torch.linalg.vector_norm(fused, dim=1).detach().numpy(), np.sqrt(3), atol=2e-7)
        fused.square().sum().backward()
        self.assertIsNone(local.grad)
        self.assertTrue(torch.isfinite(sequence.grad).all())
        with self.assertRaises(ValueError):
            model_api.fuse_features(local.requires_grad_(), point, cls)
        with self.assertRaises(ValueError):
            model_api.normalized_readouts(sequence.detach(), weights*2)
        with self.assertRaises(ValueError):
            model_api.normalized_readouts(torch.zeros_like(sequence), weights)

    def toy_backbone(self):
        """Synthetic elementwise layers, never a DINO backbone or loaded weights."""
        torch = self.torch

        class Embeddings(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.sequence = torch.nn.Parameter(torch.randn(1, 257, 384))

            def forward(self, pixels):
                return self.sequence.expand(pixels.shape[0], -1, -1)+pixels.mean((1, 2, 3))[:, None, None]

        class Layer(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.scale = torch.nn.Parameter(torch.linspace(.9, 1.1, 384))

            def forward(self, sequence):
                return sequence*self.scale

        class Toy(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.embeddings = Embeddings()
                self.encoder = torch.nn.Module()
                self.encoder.layer = torch.nn.ModuleList([Layer() for _ in range(12)])
                self.layernorm = torch.nn.LayerNorm(384)

            def forward(self, pixel_values, return_dict):
                sequence = self.embeddings(pixel_values)
                for layer in self.encoder.layer:
                    sequence = layer(sequence)
                sequence = self.layernorm(sequence)
                return SimpleNamespace(last_hidden_state=sequence, pooler_output=sequence[:, 0])

        return Toy()

    def test_synthetic_pipeline_seed_reset_frozen_prefix_gradients_and_reference_parity(self):
        torch = self.torch
        from src.ball_tracking.candidate_quality_pilot import check_first_gradients
        from src.ball_tracking.dual_view_context_experiment import parameter_deltas
        torch.manual_seed(43)
        model = model_api._make_model(self.toy_backbone(), None)
        initial_head = {n: p.detach().clone() for n, p in model.head.named_parameters()}
        torch.randn(100)
        second = model_api._make_model(self.toy_backbone(), None)
        self.assertTrue(all(torch.equal(p, initial_head[n]) for n, p in second.head.named_parameters()))
        model.train()
        self.assertFalse(model.backbone.embeddings.training)
        self.assertTrue(all(not layer.training for layer in model.backbone.encoder.layer[:10]))
        self.assertTrue(model.backbone.encoder.layer[10].training)
        local = torch.nn.functional.normalize(torch.randn(2, 384, dtype=torch.float64), dim=1)
        pixels = torch.randn(2, 3, 224, 224)
        weights = torch.tensor([[.25]*4]*2, dtype=torch.float64)
        initial = {n: p.detach().clone() for n, p in model.named_parameters() if p.requires_grad}
        frozen = {n: p.detach().clone() for n, p in model.named_parameters() if not p.requires_grad}
        logits, point, cls = model.forward_with_features(local, pixels, weights)
        parity = model_api.first_batch_parity(model, pixels, weights, point, cls)
        self.assertEqual(parity['samples'], 2)
        optimizer = torch.optim.SGD([p for p in model.parameters() if p.requires_grad], lr=.1)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, torch.tensor([1., 0.]))
        loss.backward()
        health = check_first_gradients(model)
        self.assertGreater(health['backbone']['norm'], 0)
        self.assertGreater(health['head']['norm'], 0)
        optimizer.step()
        deltas = parameter_deltas(model, initial)
        self.assertGreater(deltas['head']['L2'], 0)
        self.assertGreater(deltas['backbone']['L2'], 0)
        for name, p in model.named_parameters():
            if name in frozen:
                self.assertTrue(torch.equal(p, frozen[name]))
                self.assertIsNone(p.grad)


if __name__ == '__main__':
    unittest.main()

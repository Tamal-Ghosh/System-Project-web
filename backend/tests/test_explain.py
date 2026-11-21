import sys
import unittest
import base64
import io
from dataclasses import replace
from unittest.mock import patch

import numpy as np
import torch
from PIL import Image

from dermfm.explain import _shapley, explain_analysis
from dermfm.preprocessing import decode_image, prepare_inputs
from dermfm.service import InferenceService
from inference_fixtures import factory, image_bytes, setup_service_fixture
from dermfm.loader import CLASSES


class ExplanationTests(unittest.TestCase):
    def setUp(self):
        setup_service_fixture(self)
        self.service = InferenceService(self.settings, factory)
        self.service.states = self.service.states[:1]
        self.service.settings = self.service.settings.__class__(
            self.settings.recipe, self.settings.foundation, self.settings.checkpoints[:1],
            self.settings.device, False)
        transform = lambda image: torch.nn.functional.interpolate(
            torch.from_numpy(np.asarray(image).copy()).permute(2, 0, 1).float().unsqueeze(0),
            size=(224, 224), mode='bilinear', align_corners=False)[0] / 255
        self.service.loaded = replace(self.service.loaded, eval_transform=transform)
        self.image = decode_image(image_bytes())
        self.x, _, self.meta = prepare_inputs(self.image, 40, 'female',
            self.service.loaded.eval_transform, self.service.settings.device, 'trunk')

    def test_metadata_group_shapley_efficiency(self):
        result = _shapley(self.service.loaded.model, self.x, self.meta,
            self.service.states[0]['model'], 0)
        self.assertEqual(set(result['features']), {'age', 'sex', 'site'})
        self.assertAlmostEqual(sum(result['features'].values()),
            result['full_value'] - result['base_value'], places=4)

    def test_synthetic_fusion_model_propagates_image_gradients(self):
        image = self.x.detach().clone().requires_grad_(True)
        self.service.loaded.model.eval()
        self.service.loaded.model(image, image, self.meta)[0, 0].backward()
        self.assertIsNotNone(image.grad)
        self.assertTrue(torch.isfinite(image.grad).all())
        self.assertGreater(float(image.grad.abs().sum()), 0)

    def test_fallback_ig_restores_adapter_mode_and_grad_flags(self):
        model = self.service.loaded.model
        before = {key: value.detach().clone() for key, value in model.state_dict().items()
                  if key in model.adapter_keys}
        model.train(True)
        flags = {name: param.requires_grad for name, param in model.named_parameters()}
        with patch.dict(sys.modules, {'captum': None}):
            result = explain_analysis(self.service, self.image, 40, 'female', 'trunk',
                target_class=CLASSES[0], fold=0, n_steps=10, include_metadata=False)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['score'], 'fold_logit')
        self.assertEqual((result['image_map']['width'], result['image_map']['height']), (224, 224))
        png = Image.open(io.BytesIO(base64.b64decode(result['image_map']['data'])))
        self.assertEqual(png.size, (224, 224))
        self.assertTrue(model.training)
        self.assertEqual(flags, {name: param.requires_grad for name, param in model.named_parameters()})
        for key, value in before.items():
            self.assertTrue(torch.equal(value, model.state_dict()[key]))
        predicted = self.service.predict(self.image, 40, 'female', 'trunk')
        self.assertEqual(result['input_hash'], predicted['input_hash'])
        with torch.inference_mode():
            logits = model(self.x, self.x, self.meta)
        self.assertEqual(logits.shape, (1, 11))


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from inference_app import create_app
from inference_fixtures import image_bytes
from dermfm.e55_service import E55Service
from dermfm.loader import CLASSES
import torch
from PIL import Image


class E55ApiTests(unittest.TestCase):
    def test_single_image_is_duplicated_and_policy_recorded(self):
        service = E55Service.__new__(E55Service)
        service.version = 'e55-test'
        service.predictor = Mock()
        service.predictor.predict.return_value = {'raw_probabilities': {c: 1/11 for c in CLASSES}, 'top_class': CLASSES[0], 'decision_scores': {c: .1 for c in CLASSES}, 'positive_categories': []}
        service.predictor.transform.return_value = torch.zeros(3, 2, 2)
        image = Image.new('RGB', (2,2))
        result = service.predict(image, 40, 'male')
        self.assertIs(service.predictor.predict.call_args.args[0], service.predictor.predict.call_args.args[1])
        self.assertEqual(result['input_policy'], 'single_dermoscopic_duplicated')

    def test_requires_pair_and_passes_both_images(self):
        service = Mock()
        service.version = 'e55-test'
        service.requires_clinical = True
        service.predict.return_value = {'model_version': 'e55-test', 'input_policy': 'paired_dermoscopic_clinical'}
        data = {'age':'40','sex':'male','site':'trunk'}
        with TestClient(create_app(lambda: service)) as client:
            missing = client.post('/api/v1/analyses',data=data,files={'image':('derm.png',image_bytes(),'image/png')})
            self.assertEqual(missing.status_code,200)
            self.assertIsNone(service.predict.call_args.args[-1])
            service.predict.reset_mock()
            paired = client.post('/api/v1/analyses',data=data,files={'image':('derm.png',image_bytes(),'image/png'),'clinical':('clinical.png',image_bytes(),'image/png')})
            self.assertEqual(paired.status_code,200,paired.text)
            self.assertEqual(len(service.predict.call_args.args),5)
            invalid = client.post('/api/v1/analyses',data=data,files={'image':('derm.png',image_bytes(),'image/png'),'clinical':('bad.png',b'invalid','image/png')})
            self.assertEqual(invalid.status_code,422)
            xai = client.post('/api/v1/explanations',data=data,files={'image':('derm.png',image_bytes(),'image/png')})
            self.assertEqual(xai.status_code,422)

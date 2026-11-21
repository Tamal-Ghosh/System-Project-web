import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from dermfm.service import InferenceService
from inference_app import create_app
from inference_fixtures import factory, image_bytes, setup_service_fixture

class ApiTests(unittest.TestCase):
    def setUp(self):
        setup_service_fixture(self)
    def test_api_to_real_synthetic_service(self):
        service=InferenceService(self.settings,factory)
        with TestClient(create_app(lambda:service)) as client:
            self.assertEqual(client.get('/health').json()['status'],'ready')
            response=client.post('/api/v1/analyses',data={'age':'40','sex':'female'},files={'image':('test.png',image_bytes(),'image/png')})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(len(response.json()['scores']),11)
            self.assertEqual(len(response.json()['input_hash']),64)
            invalid=client.post('/api/v1/analyses',data={'age':'-1','sex':'female'},files={'image':('test.png',image_bytes(),'image/png')})
            self.assertEqual(invalid.status_code,422)
            broken=client.post('/api/v1/analyses',data={'age':'20','sex':'male'},files={'image':('bad.png',b'bad','image/png')})
            self.assertEqual(broken.status_code,422)
            invalid_explanation=client.post('/api/v1/explanations',data={'age':'40','sex':'female','target_class':'NOT_A_CLASS'},files={'image':('test.png',image_bytes(),'image/png')})
            self.assertEqual(invalid_explanation.status_code,422)
            unknown_method=client.post('/api/v1/explanations',data={'age':'40','sex':'female','method':'grad_cam'},files={'image':('test.png',image_bytes(),'image/png')})
            self.assertEqual(unknown_method.status_code,422)
            with patch.object(service,'predict',side_effect=RuntimeError('internal')):
                with self.assertLogs('inference_app',level='ERROR'):
                    failed=client.post('/api/v1/analyses',data={'age':'20','sex':'male'},files={'image':('test.png',image_bytes(),'image/png')})
                self.assertEqual(failed.status_code,503)
                self.assertNotIn('internal',failed.text)
    def test_unavailable_model_never_predicts(self):
        def broken(): raise RuntimeError('missing weights')
        with self.assertLogs('inference_app',level='ERROR'):
            with TestClient(create_app(broken)) as client:
                self.assertEqual(client.get('/health').json()['status'],'unavailable')
                response=client.post('/api/v1/analyses',data={'age':'20','sex':'male'},files={'image':('test.png',image_bytes(),'image/png')})
                self.assertEqual(response.status_code,503)

    def test_location_is_passed_to_model_and_invalid_location_rejected(self):
        service=InferenceService(self.settings,factory)
        with TestClient(create_app(lambda:service)) as client:
            with patch.object(service,'predict',wraps=service.predict) as predict:
                response=client.post('/api/v1/analyses',data={'age':'40','sex':'female','site':'trunk'},files={'image':('test.png',image_bytes(),'image/png')})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(predict.call_args.args[-1],'trunk')
                self.assertEqual(response.json()['metadata']['site'],'trunk')
                self.assertNotIn('Body site was encoded as unknown.',response.json()['limitations'])
                predict.reset_mock()
                invalid=client.post('/api/v1/analyses',data={'age':'40','sex':'female','site':'invalid'},files={'image':('test.png',image_bytes(),'image/png')})
                self.assertEqual(invalid.status_code,422)
                predict.assert_not_called()

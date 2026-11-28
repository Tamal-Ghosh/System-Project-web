import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from database import DatabaseUnavailable
from dermfm.service import InferenceService
from inference_app import create_app
from inference_fixtures import factory, image_bytes, setup_service_fixture


class AnalysisPersistenceTests(unittest.TestCase):
    def setUp(self):
        setup_service_fixture(self)
        self.service = InferenceService(self.settings, factory)

    def classify(self, client):
        return client.post('/api/v1/analyses', data={'age': '40', 'sex': 'female'},
                           files={'image': ('test.png', image_bytes(), 'image/png')})

    def test_saved_snapshot_is_server_generated(self):
        with patch.dict(os.environ, {'ANALYSIS_PERSISTENCE_ENABLED': 'true'}), \
             patch('inference_app.save_analysis_snapshot') as save, \
             TestClient(create_app(lambda: self.service)) as client:
            response = self.classify(client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['persistence'], 'saved')
        returned = response.json()
        self.assertTrue(returned.pop('assistant_access_token'))
        self.assertEqual(save.call_args.args[0], returned)

    def test_storage_failure_is_reported_without_losing_result(self):
        with patch.dict(os.environ, {'ANALYSIS_PERSISTENCE_ENABLED': 'true'}), \
             patch('inference_app.save_analysis_snapshot', side_effect=DatabaseUnavailable()), \
             TestClient(create_app(lambda: self.service)) as client:
            response = self.classify(client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['persistence'], 'not_saved')
        self.assertEqual(response.json()['persistence_reason'], 'database_unavailable')
        self.assertEqual(len(response.json()['scores']), 11)


if __name__ == '__main__':
    unittest.main()

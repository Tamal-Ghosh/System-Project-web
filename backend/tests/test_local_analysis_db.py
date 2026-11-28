"""Run only against an explicitly supplied disposable local test database."""
import os
import unittest
from unittest.mock import patch
from uuid import uuid4
from urllib.parse import urlparse

import psycopg
from database import AnalysisMismatch, save_analysis_snapshot, save_explanation_snapshot


class LocalDatabaseTests(unittest.TestCase):
    def test_snapshot_and_matching_explanation(self):
        url = os.environ.get('TEST_DATABASE_URL')
        if not url:
            self.skipTest('TEST_DATABASE_URL not set')
        parsed = urlparse(url)
        if parsed.hostname not in ('localhost', '127.0.0.1', '::1') or parsed.path != '/dermascope_test':
            self.fail('Tests require the local dermascope_test database')
        analysis_id, xai_id = str(uuid4()), str(uuid4())
        snapshot = {'analysis_id': analysis_id, 'model_version': 'synthetic-v1',
                    'input_hash': 'a' * 64, 'scores': [{'label': 'TEST', 'score': 1.0}],
                    'persistence': 'saved'}
        explanation = {'status': 'ok', 'method': 'integrated_gradients',
                       'model_version': 'synthetic-v1', 'input_hash': 'a' * 64,
                       'image_map': {'data': 'not stored'}}
        with patch('database._database_url', return_value=url):
            save_analysis_snapshot(snapshot)
            with self.assertRaises(AnalysisMismatch):
                save_explanation_snapshot(analysis_id, str(uuid4()), {**explanation, 'input_hash': 'b' * 64})
            save_explanation_snapshot(analysis_id, xai_id, explanation)
        with psycopg.connect(url) as connection:
            stored = connection.execute('SELECT response_snapshot FROM public.analyses WHERE id = %s', (analysis_id,)).fetchone()[0]
            rows = connection.execute('SELECT evidence FROM public.analysis_explanations WHERE analysis_id = %s', (analysis_id,)).fetchall()
        self.assertEqual(stored, snapshot)
        self.assertEqual(len(rows), 1)
        self.assertNotIn('image_map', rows[0][0])


if __name__ == '__main__':
    unittest.main()

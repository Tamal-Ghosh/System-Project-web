import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from inference_app import create_app
from dermfm.service import InferenceService
from inference_fixtures import setup_service_fixture, factory, image_bytes


class AssistantApiTests(unittest.TestCase):
    def setUp(self):
        setup_service_fixture(self)

    def test_case_access_and_numeric_grounding(self):
        service = InferenceService(self.settings, factory)
        with patch.dict('os.environ', {'ANALYSIS_PERSISTENCE_ENABLED': 'false', 'ASSISTANT_PROVIDER': 'mock'}), TestClient(create_app(lambda: service)) as client:
            result = client.post('/api/v1/analyses', data={'age': '40', 'sex': 'female'}, files={'image': ('test.png', image_bytes(), 'image/png')}).json()
            body = {'analysis_id': result['analysis_id'], 'question': 'Show model score'}
            self.assertEqual(client.post('/api/v1/chat/query', json=body).status_code, 403)
            self.assertEqual(client.post('/api/v1/chat/query', json=body, headers={'X-Case-Token': 'incorrect'}).status_code, 403)
            headers = {'X-Case-Token': result['assistant_access_token']}
            response = client.post('/api/v1/chat/query', json=body, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['input_hash'], result['input_hash'])
            self.assertIn(result['leading_class'], response.json()['answer'])
            uncertainty = client.post('/api/v1/chat/query', json={**body, 'question': 'Explain uncertainty'}, headers=headers).json()
            self.assertIn(f"{result['uncertainty']['normalized_entropy']:.3f}", uncertainty['answer'])
            blank = client.post('/api/v1/chat/query', json={**body, 'question': ' '}, headers=headers)
            self.assertEqual(blank.status_code, 422)

    def test_provider_failure_is_localized_and_case_facts_still_work(self):
        from unittest.mock import Mock
        from assistant.gemini import GeminiUnavailable
        generator=Mock();generator.answer.side_effect=GeminiUnavailable('private provider diagnostics')
        service=InferenceService(self.settings,factory)
        env={'ASSISTANT_STORAGE':'local','ASSISTANT_PROVIDER':'gemini','GEMINI_API_KEY':'synthetic-test-only','ANALYSIS_PERSISTENCE_ENABLED':'false'}
        with patch.dict('os.environ',env),patch('inference_app.GeminiCaseGenerator',return_value=generator),patch('inference_app.GeminiEmbeddings'),patch('inference_app.HybridRetriever') as retriever,TestClient(create_app(lambda:service)) as client:
            retriever.return_value.search.return_value=[]
            result=client.post('/api/v1/analyses',data={'age':'40','sex':'female'},files={'image':('test.png',image_bytes(),'image/png')}).json()
            headers={'X-Case-Token':result['assistant_access_token']};body={'analysis_id':result['analysis_id'],'question':'ei rog ta nea bolo'}
            failure=client.post('/api/v1/chat/query',headers=headers,json=body)
            self.assertEqual(failure.status_code,503);self.assertEqual(failure.headers['Retry-After'],'3')
            self.assertNotIn('private',failure.text);self.assertIn('সাময়িক',failure.json()['detail'])
            facts=client.post('/api/v1/chat/query',headers=headers,json={**body,'question':'prediction ta ki'})
            self.assertEqual(facts.status_code,200);self.assertIn('%',facts.json()['answer'])
            self.assertEqual(generator.answer.call_count,1)
            history=client.get('/api/v1/chat/history/'+result['analysis_id'],headers=headers).json()
            self.assertEqual(len(history),1)

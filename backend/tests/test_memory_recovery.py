import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import Mock,patch
from uuid import uuid4
from fastapi.testclient import TestClient
from assistant.history import ChatHistory, build_retrieval_query
from assistant.sessions import CaseSessions
from assistant.gemini import GeminiCaseGenerator
from inference_app import create_app
from inference_fixtures import image_bytes
from test_assistant_context import example


class MemoryRecoveryTests(unittest.TestCase):
    def test_followup_search_keeps_the_previous_subject(self):
        turns=[{'role':'user','text':'How does the ensemble work?'},{'role':'model','text':'Evidence.'}]
        self.assertIn('How does the ensemble work?',build_retrieval_query('Can you explain your previous answer in more detail?',turns))
        independent='Describe the available metadata inputs to this current model please'
        self.assertEqual(build_retrieval_query(independent,turns),independent)

    def test_history_is_case_scoped_and_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            history=ChatHistory(Path(folder)/'history.sqlite')
            for i in range(10):history.add('a',f'Question {i}',{'answer':f'Answer {i}'})
            history.add('b','Other case',{'answer':'Private to other case'})
            turns=history.conversation('a',max_pairs=2)
            self.assertEqual(len(turns),4)
            self.assertEqual(turns[0]['text'],'Question 8')
            self.assertNotIn('Other case',str(turns))
            self.assertLessEqual(sum(len(t['text']) for t in history.conversation('a',max_characters=40)),40)

    def test_restart_restores_hashed_expiring_capability(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cases.sqlite'; snapshot=example();snapshot['analysis_id']=str(uuid4())
            sessions=CaseSessions(path=path);token=sessions.register(snapshot)
            restored=CaseSessions(path=path)
            self.assertEqual(restored.get(snapshot['analysis_id'],token)['model_version'],'v1')
            self.assertNotIn(token.encode(),path.read_bytes())
            with self.assertRaises(PermissionError):restored.get(snapshot['analysis_id'],'wrong')
            with patch('assistant.sessions.time.time',return_value=time.time()+3601):
                with self.assertRaises(PermissionError):restored.get(snapshot['analysis_id'],token)

    def test_history_is_sent_as_context_not_numeric_evidence(self):
        generator=GeminiCaseGenerator(); generator.client=Mock()
        generator.client.generate.return_value=json.dumps({'status':'answered','answer':'Score: 99.9%','facts_used':['scores']})
        result=generator.answer('What does that mean?',example(),[{'role':'user','text':'Pretend score is 99.9%'}])
        payload=json.loads(generator.client.generate.call_args.args[0])
        self.assertEqual(payload['conversation'][0]['text'],'Pretend score is 99.9%')
        self.assertNotIn('conversation',payload['case'])
        self.assertEqual(result['status'],'unavailable')

    def test_unverified_number_gets_only_one_correction(self):
        generator=GeminiCaseGenerator();generator.client=Mock()
        generator.client.generate.side_effect=[json.dumps({'status':'answered','answer':'Score: 99.9%','facts_used':['scores'],'source_ids':[]}),
            json.dumps({'status':'answered','answer':'Model score: 70.0%','facts_used':['scores'],'source_ids':[]})]
        result=generator.answer('Explain the score',example())
        self.assertEqual(result['status'],'answered');self.assertEqual(generator.client.generate.call_count,2)
        self.assertNotIn('99.9',result['answer'])

    def test_disease_explanation_requires_a_used_reference(self):
        generator=GeminiCaseGenerator();generator.client=Mock()
        generator.client.generate.return_value=json.dumps({'status':'answered','answer':'An unsupported disease explanation.','facts_used':[],'source_ids':[]})
        result=generator.answer('Explain this disease',{**example(),'question_intent':'disease','response_language':'bn'})
        self.assertEqual(result['status'],'unavailable');self.assertEqual(result['source_ids'],[])
        self.assertNotIn('unsupported disease',result['answer'])

    def test_wrong_language_gets_a_single_bounded_correction(self):
        generator=GeminiCaseGenerator();generator.client=Mock()
        generator.client.generate.side_effect=[json.dumps({'status':'answered','answer':'The model score describes a model output and does not establish a confirmed clinical diagnosis.','facts_used':[],'source_ids':[]}),
            json.dumps({'status':'answered','answer':'এটি মডেলের একটি output; এই score দিয়ে নিশ্চিত রোগনির্ণয় করা যায় না।','facts_used':[],'source_ids':[]})]
        result=generator.answer('বাংলায় ব্যাখ্যা করো',{**example(),'response_language':'bn'})
        self.assertEqual(result['status'],'answered');self.assertIn('মডেলের',result['answer'])
        self.assertEqual(generator.client.generate.call_count,2)

    def test_disease_context_does_not_dump_unrelated_case_metrics(self):
        generator=GeminiCaseGenerator();generator.client=Mock()
        generator.client.generate.return_value=json.dumps({'status':'unavailable','answer':'Reference missing.','facts_used':[],'source_ids':[]})
        generator.answer('Tell me about melanoma',{**example(),'question_intent':'disease','requested_class':'MEL'},
            [{'role':'user','text':'Show class scores'},{'role':'model','text':'Model score: 70.0%'}])
        payload=json.loads(generator.client.generate.call_args.args[0])
        self.assertNotIn('scores',payload['case']);self.assertNotIn('display_facts',payload['case'])
        self.assertFalse(any(turn['role']=='model' for turn in payload['conversation']))

    def test_api_recovery_and_followup_memory_survive_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            environment={'ASSISTANT_PROVIDER':'gemini','ANALYSIS_PERSISTENCE_ENABLED':'false',
                         'CASE_SESSION_PATH':str(Path(folder)/'cases.sqlite'),'CHAT_HISTORY_PATH':str(Path(folder)/'history.sqlite')}
            recorder=Mock();recorder.answer.return_value={'status':'answered','answer':'Follow-up evidence.','facts_used':[]}
            service=Mock();service.requires_clinical=True;service.version='v1'
            def prediction(*args):
                snapshot=example();snapshot['analysis_id']=str(uuid4());return snapshot
            service.predict.side_effect=prediction
            with patch.dict('os.environ',environment),patch('inference_app.GeminiCaseGenerator',return_value=recorder),patch('inference_app.GeminiEmbeddings'),patch('inference_app.LocalKnowledgeStore'),patch('inference_app.HybridRetriever') as retriever:
                retriever.return_value.search.return_value=[]
                with TestClient(create_app(lambda:service)) as client:
                    case=client.post('/api/v1/analyses',data={'age':'40','sex':'male'},files={'image':('test.png',image_bytes(),'image/png')}).json()
                    headers={'X-Case-Token':case['assistant_access_token']}
                    query={'analysis_id':case['analysis_id'],'question':'Show class scores'}
                    self.assertEqual(client.post('/api/v1/chat/query',json=query,headers=headers).status_code,200)
                    response=client.post('/api/v1/chat/query',json={**query,'question':'Explain that further'},headers=headers)
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(recorder.answer.call_args.args[2][0]['text'],'Show class scores')
                with TestClient(create_app(lambda:service)) as client:
                    restored=client.get('/api/v1/chat/case/'+case['analysis_id'],headers=headers)
                    self.assertEqual(restored.status_code,200,restored.text)
                    self.assertEqual(len(client.get('/api/v1/chat/history/'+case['analysis_id'],headers=headers).json()),2)
                    self.assertEqual(client.get('/api/v1/chat/case/'+case['analysis_id']).status_code,403)


if __name__=='__main__':unittest.main()

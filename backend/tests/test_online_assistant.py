"""Online adapters tested only against an explicitly disposable local database."""
import os,tempfile,unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from urllib.parse import urlparse
import psycopg
from assistant.postgres_storage import PostgresCaseSessions,PostgresChatHistory,AssistantStorageUnavailable,assistant_database_url,connection
from assistant.ingestion import LocalKnowledgeStore,Source
from assistant.vector_store import PostgresKnowledgeStore
from test_assistant_context import example

class OnlineStorageUnitTests(unittest.TestCase):
    def test_missing_online_url_never_falls_back_to_admin_or_sqlite(self):
        with patch.dict(os.environ,{'ASSISTANT_DATABASE_URL':'','DATABASE_URL':'do-not-use'}):
            with self.assertRaises(ValueError):assistant_database_url()
    def test_driver_errors_are_sanitized(self):
        with patch('assistant.postgres_storage.psycopg.connect',side_effect=psycopg.OperationalError('secret-password-in-driver-error')):
            with self.assertRaises(AssistantStorageUnavailable) as caught:
                with connection('not-a-real-url'):pass
        self.assertNotIn('secret',str(caught.exception))

    def test_online_vector_errors_are_sanitized_too(self):
        with patch('assistant.postgres_storage.psycopg.connect',side_effect=psycopg.OperationalError('secret-driver-detail')):
            with self.assertRaises(AssistantStorageUnavailable) as caught:PostgresKnowledgeStore('unused',schema='assistant').approved_chunks()
        self.assertNotIn('secret',str(caught.exception))

class OnlineApiFailureTests(unittest.TestCase):
    def test_chat_storage_outage_keeps_classification_and_sanitizes_chat_error(self):
        from unittest.mock import Mock
        from fastapi.testclient import TestClient
        from inference_app import create_app
        from inference_fixtures import image_bytes
        from test_assistant_context import example
        case=example();case['analysis_id']=str(uuid4());service=Mock();service.requires_clinical=False;service.predict.return_value=case
        sessions=Mock();sessions.register.side_effect=AssistantStorageUnavailable('private driver detail');sessions.get.side_effect=AssistantStorageUnavailable('private driver detail')
        with patch.dict(os.environ,{'ASSISTANT_STORAGE':'postgres','ASSISTANT_DATABASE_URL':'synthetic-not-a-network-url','ASSISTANT_PROVIDER':'mock','ANALYSIS_PERSISTENCE_ENABLED':'false'}),patch('inference_app.PostgresCaseSessions',return_value=sessions),patch('inference_app.PostgresChatHistory'),TestClient(create_app(lambda:service)) as client:
            result=client.post('/api/v1/analyses',data={'age':'40','sex':'male'},files={'image':('test.png',image_bytes(),'image/png')})
            self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['leading_class'],'MEL')
            self.assertIsNone(result.json()['assistant_access_token'])
            reply=client.post('/api/v1/chat/query',json={'analysis_id':case['analysis_id'],'question':'hi'})
            self.assertEqual(reply.status_code,503);self.assertNotIn('private',reply.text)

class OnlineStorageIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url=os.getenv('TEST_ASSISTANT_DATABASE_URL')
        if not cls.url:raise unittest.SkipTest('Disposable local online-adapter DB not configured')
        parsed=urlparse(cls.url)
        if parsed.hostname not in ('knowledge-db','localhost','127.0.0.1') or parsed.path!='/assistant_migration_test':
            raise RuntimeError('Refusing integration tests outside the disposable local database')
        with psycopg.connect(cls.url) as db:db.execute((Path(__file__).resolve().parents[1]/'migrations/010_online_assistant.sql').read_text())
    def test_cross_instance_sessions_and_history(self):
        case=example();case['analysis_id']=str(uuid4())
        first=PostgresCaseSessions(self.url);second=PostgresCaseSessions(self.url)
        token=first.register(case);self.assertEqual(second.get(case['analysis_id'],token)['leading_class'],'MEL')
        with self.assertRaises(PermissionError):second.get(case['analysis_id'],'wrong')
        history=PostgresChatHistory(self.url);message=history.add(case['analysis_id'],'Explain prediction',{'status':'answered','answer':'Model score: 70.0%','facts_used':['scores']})
        recovered=PostgresChatHistory(self.url)
        self.assertEqual(recovered.list(case['analysis_id'])[0]['id'],message)
        self.assertEqual(recovered.conversation(case['analysis_id'])[0]['text'],'Explain prediction')
        self.assertEqual(recovered.list('unrelated-case'),[])
        recovered.rate(case['analysis_id'],message,'helpful')
        with self.assertRaises(LookupError):recovered.rate('unrelated-case',message,'helpful')
        with patch('assistant.postgres_storage.time.time',return_value=9999999999):
            with self.assertRaises(PermissionError):second.get(case['analysis_id'],token)
    def test_private_schema_and_vector_import(self):
        class Embedder:
            model='synthetic-local-only'
            def embed(self,texts):return [[1.]+[0.]*767 for _ in texts]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'reference.md';path.write_text('# Synthetic reference\nLocal QA text, not clinical evidence.')
            source=LocalKnowledgeStore(Path(folder)/'stage.sqlite');identity=source.ingest(path,Source('Synthetic',str(uuid4()),'https://example.org/local-test','Synthetic QA','test'),Embedder());source.approve(identity,'local QA')
            target=PostgresKnowledgeStore(self.url,schema='assistant');target.import_local(source)
            self.assertTrue(any(row[0].startswith(identity) for row in target.approved_chunks()))
            target.import_local(source)
        with psycopg.connect(self.url) as db:
            rows=db.execute("SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='assistant' AND c.relkind='r'").fetchall()
            self.assertEqual(len(rows),5);self.assertTrue(all(row[0] for row in rows))

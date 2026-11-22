"""Server-only online history/capability adapters. No SQLite fallback on failure."""
from contextlib import contextmanager
from copy import deepcopy
from uuid import uuid4
import hashlib,os,secrets,time
import psycopg
from psycopg.types.json import Jsonb
from assistant.case_context import build_case_context
from assistant.history import ChatHistory


class AssistantStorageUnavailable(RuntimeError):pass


def assistant_database_url():
    value=os.getenv('ASSISTANT_DATABASE_URL')
    if not value:raise ValueError('ASSISTANT_DATABASE_URL is required for online chatbot storage')
    return value


@contextmanager
def connection(url):
    try:
        with psycopg.connect(url,connect_timeout=8,prepare_threshold=None) as db:
            db.execute("SET LOCAL search_path TO assistant, extensions, public")
            db.execute("SET LOCAL statement_timeout TO '10s'")
            yield db
    except psycopg.Error:
        raise AssistantStorageUnavailable('Online chatbot storage is temporarily unavailable') from None


class PostgresChatHistory(ChatHistory):
    def __init__(self,url):self.url=url

    def add(self,analysis_id,question,response):
        identity=str(uuid4())
        with connection(self.url) as db:
            db.execute('INSERT INTO assistant.messages(id,analysis_id,question,response) VALUES (%s,%s,%s,%s)',(identity,analysis_id,question,Jsonb(response)))
        return identity

    def list(self,analysis_id):
        with connection(self.url) as db:
            rows=db.execute('SELECT id,question,response,created_at FROM assistant.messages WHERE analysis_id=%s ORDER BY sequence DESC LIMIT 100',(analysis_id,)).fetchall()
        return [{'id':str(r[0]),'question':r[1],'response':r[2],'created_at':r[3].isoformat()} for r in reversed(rows)]

    def rate(self,analysis_id,message_id,rating):
        with connection(self.url) as db:
            result=db.execute('INSERT INTO assistant.feedback(id,message_id,rating) SELECT %s,id,%s FROM assistant.messages WHERE id=%s AND analysis_id=%s RETURNING id',(str(uuid4()),rating,message_id,analysis_id)).fetchone()
            if result is None:raise LookupError('Message unavailable')


class PostgresCaseSessions:
    def __init__(self,url,ttl=3600,capacity=100):self.url,self.ttl,self.capacity=url,ttl,capacity

    def register(self,snapshot):
        context=build_case_context(snapshot);token=secrets.token_urlsafe(32);now=time.time()
        with connection(self.url) as db:
            # Serialize bounded cleanup across backend instances, not just one process.
            db.execute('SELECT pg_advisory_xact_lock(41793812)')
            db.execute('DELETE FROM assistant.case_sessions WHERE expires<=%s',(now,))
            db.execute('DELETE FROM assistant.case_sessions WHERE analysis_id IN (SELECT analysis_id FROM assistant.case_sessions ORDER BY expires DESC LIMIT ALL OFFSET %s)',(max(0,self.capacity-1),))
            db.execute('INSERT INTO assistant.case_sessions(analysis_id,token_hash,expires,context) VALUES (%s,%s,%s,%s) ON CONFLICT(analysis_id) DO UPDATE SET token_hash=excluded.token_hash,expires=excluded.expires,context=excluded.context',
                       (snapshot['analysis_id'],hashlib.sha256(token.encode()).hexdigest(),now+self.ttl,Jsonb(context)))
        return token

    def get(self,analysis_id,token):
        with connection(self.url) as db:
            row=db.execute('SELECT token_hash,expires,context FROM assistant.case_sessions WHERE analysis_id=%s',(analysis_id,)).fetchone()
        if row is None or row[1]<=time.time() or not secrets.compare_digest(row[0],hashlib.sha256(token.encode()).hexdigest()):
            raise PermissionError('Case session unavailable; run classification again')
        return deepcopy(row[2])

    def attach_explanation(self,analysis_id,token,result):
        with connection(self.url) as db:
            row=db.execute('SELECT token_hash,expires,context FROM assistant.case_sessions WHERE analysis_id=%s FOR UPDATE',(analysis_id,)).fetchone()
            if row is None or row[1]<=time.time() or not secrets.compare_digest(row[0],hashlib.sha256(token.encode()).hexdigest()):raise PermissionError('Case session unavailable')
            context=build_case_context(row[2],result)
            db.execute('UPDATE assistant.case_sessions SET context=%s WHERE analysis_id=%s',(Jsonb(context),analysis_id))


def storage_health(url):
    with connection(url) as db:
        db.execute('SELECT 1 FROM assistant.case_sessions LIMIT 1')
        db.execute('SELECT 1 FROM assistant.messages LIMIT 1')
        db.execute('SELECT 1 FROM assistant.knowledge_chunks LIMIT 1')
    return {'status':'connected','storage':'postgres'}

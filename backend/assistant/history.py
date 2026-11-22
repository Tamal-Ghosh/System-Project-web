"""Local chat audit store. Access is enforced by the case API before use."""
from contextlib import closing
import json
import sqlite3
import re
from uuid import uuid4


class ChatHistory:
    def __init__(self, path):
        self.path = str(path)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, analysis_id TEXT NOT NULL, question TEXT NOT NULL, response TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            db.execute('CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, message_id TEXT NOT NULL, rating TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')

    def add(self, analysis_id, question, response):
        identity = str(uuid4())
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO messages (id,analysis_id,question,response) VALUES (?,?,?,?)', (identity, analysis_id, question, json.dumps(response)))
        return identity

    def list(self, analysis_id):
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute('SELECT id,question,response,created_at FROM messages WHERE analysis_id=? ORDER BY rowid DESC LIMIT 100', (analysis_id,)).fetchall()
        return [{'id': row[0], 'question': row[1], 'response': json.loads(row[2]), 'created_at': row[3]} for row in reversed(rows)]

    def conversation(self, analysis_id, max_pairs=6, max_characters=10000):
        """Bounded completed turns; never mix another case or treat past text as evidence."""
        pairs=[]; remaining=max_characters
        for row in reversed(self.list(analysis_id)[-max_pairs:]):
            question=str(row['question'])[:1500]
            answer=str(row['response'].get('answer',''))[:2500]
            if len(question)+len(answer)>remaining:
                break
            pairs.append([{'role':'user','text':question},{'role':'model','text':answer}])
            remaining-=len(question)+len(answer)
        return [turn for pair in reversed(pairs) for turn in pair]

    def rate(self, analysis_id, message_id, rating):
        with closing(sqlite3.connect(self.path)) as db, db:
            if db.execute('SELECT 1 FROM messages WHERE id=? AND analysis_id=?', (message_id, analysis_id)).fetchone() is None:
                raise LookupError('Message unavailable')
            db.execute('INSERT INTO feedback (id,message_id,rating) VALUES (?,?,?)', (str(uuid4()), message_id, rating))


def build_retrieval_query(question,conversation):
    references_previous=bool(re.search(r'last answer|previous answer|explain that|what about that|আগের|পূর্বের|ওটা|এটা',question,re.I))
    if conversation and (len(question.split())<=6 or references_previous):
        previous=next((turn['text'] for turn in reversed(conversation) if turn.get('role')=='user'),'')
        if previous:return previous+'\nFollow-up: '+question
    return question

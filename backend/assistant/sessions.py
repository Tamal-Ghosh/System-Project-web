"""Bounded case capabilities with optional restart-safe SQLite storage."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import secrets
import sqlite3
import threading
import time
from assistant.case_context import build_case_context


class CaseSessions:
    def __init__(self, ttl=3600, capacity=100, path=None):
        self.ttl,self.capacity,self.path=ttl,capacity,str(path) if path else None
        self.records={}; self.lock=threading.Lock()
        if self.path:
            with closing(sqlite3.connect(self.path)) as db,db:
                db.execute('CREATE TABLE IF NOT EXISTS case_sessions (analysis_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, expires REAL NOT NULL, context TEXT NOT NULL)')

    def _read(self, analysis_id):
        if not self.path: return self.records.get(analysis_id)
        with closing(sqlite3.connect(self.path)) as db:
            row=db.execute('SELECT expires,token_hash,context FROM case_sessions WHERE analysis_id=?',(analysis_id,)).fetchone()
        return (row[0],row[1],json.loads(row[2])) if row else None

    def _save(self, analysis_id, record):
        if not self.path:
            self.records[analysis_id]=record; return
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('INSERT INTO case_sessions (analysis_id,token_hash,expires,context) VALUES (?,?,?,?) ON CONFLICT(analysis_id) DO UPDATE SET token_hash=excluded.token_hash,expires=excluded.expires,context=excluded.context',
                       (analysis_id,record[1],record[0],json.dumps(record[2])))

    def register(self,snapshot):
        context=build_case_context(snapshot); token=secrets.token_urlsafe(32)
        now=time.time(); record=(now+self.ttl,hashlib.sha256(token.encode()).hexdigest(),context)
        with self.lock:
            if self.path:
                with closing(sqlite3.connect(self.path)) as db,db:
                    db.execute('DELETE FROM case_sessions WHERE expires<=?',(now,))
                    db.execute('DELETE FROM case_sessions WHERE analysis_id IN (SELECT analysis_id FROM case_sessions ORDER BY expires DESC LIMIT -1 OFFSET ?)',(max(0,self.capacity-1),))
            else:
                self.records={k:v for k,v in self.records.items() if v[0]>now}
                if len(self.records)>=self.capacity: self.records.pop(next(iter(self.records)))
            self._save(snapshot['analysis_id'],record)
        return token

    def get(self,analysis_id,token):
        with self.lock:
            record=self._read(analysis_id)
            digest=hashlib.sha256(token.encode()).hexdigest()
            if record is None or record[0]<=time.time() or not secrets.compare_digest(record[1],digest):
                raise PermissionError('Case session unavailable; run classification again')
            return deepcopy(record[2])

    def attach_explanation(self,analysis_id,token,result):
        updated=build_case_context(self.get(analysis_id,token),result)
        with self.lock:
            record=self._read(analysis_id)
            if record is None or record[0]<=time.time() or not secrets.compare_digest(record[1],hashlib.sha256(token.encode()).hexdigest()):
                raise PermissionError('Case session unavailable')
            self._save(analysis_id,(record[0],record[1],updated))

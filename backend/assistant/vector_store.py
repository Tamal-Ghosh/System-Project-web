"""PostgreSQL/pgvector retrieval-store interface for the local knowledge corpus."""
from contextlib import contextmanager
import json
import psycopg
from psycopg import sql


class PostgresKnowledgeStore:
    def __init__(self, url, schema="public"):
        if schema not in ("public","assistant"):raise ValueError("Unsupported knowledge schema")
        self.url, self.schema = url, schema

    def _configure(self, db):
        db.execute(sql.SQL("SET LOCAL search_path TO {}, extensions, public").format(sql.Identifier(self.schema)))
        db.execute("SET LOCAL statement_timeout TO '10s'")

    @contextmanager
    def _connection(self):
        if self.schema=='assistant':
            from assistant.postgres_storage import connection
            with connection(self.url) as db:yield db
        else:
            with psycopg.connect(self.url,connect_timeout=5,prepare_threshold=None) as db:
                self._configure(db)
                yield db

    def approved_chunks(self):
        with self._connection() as db:
            rows = db.execute("SELECT c.id,c.payload,c.embedding::text,d.embedding_model,d.title,d.version,d.source_url,d.document_type FROM knowledge_chunks c JOIN knowledge_documents d ON d.id=c.document_id WHERE d.status='approved'").fetchall()
        return [(row[0], json.dumps({**row[1], 'source': dict(title=row[4], version=row[5], source_url=row[6], document_type=row[7])}), row[2], row[3]) for row in rows]

    def import_local(self, sqlite_store):
        # Copy existing reviewed embeddings without repeating external API calls.
        with sqlite_store.connection() as source, self._connection() as destination:
            for row in source.execute('SELECT id,title,version,source_url,license,document_type,checksum,status,reviewer,embedding_model,dimensions FROM documents'):
                destination.execute('INSERT INTO knowledge_documents VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING', row)
            for identity, document, ordinal, payload, embedding in source.execute('SELECT id,document_id,ordinal,payload,embedding FROM chunks'):
                destination.execute('INSERT INTO knowledge_chunks VALUES (%s,%s,%s,%s::jsonb,%s::vector) ON CONFLICT (id) DO NOTHING', (identity,document,ordinal,payload,embedding))

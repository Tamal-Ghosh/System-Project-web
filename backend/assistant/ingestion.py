"""Versioned local document staging for the development RAG pipeline.

Only UTF-8 Markdown/plain text are accepted initially. Sources remain drafts until
explicit approval. Embeddings are supplied by an injected provider.
"""
from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Protocol


class Embedder(Protocol):
    model: str
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class Source:
    title: str
    version: str
    source_url: str
    license: str
    document_type: str


def section_chunks(text: str, size: int = 300, overlap: int = 40) -> list[dict]:
    """Word-based starting configuration, preserving parent headings and offsets."""
    if size < 1 or not 0 <= overlap < size:
        raise ValueError('Require size > overlap >= 0')
    sections = []
    heading, lines = 'Document', []
    for line in text.splitlines():
        if re.match(r'^#{1,6}\s+', line):
            if lines:
                sections.append((heading, '\n'.join(lines)))
            heading, lines = re.sub(r'^#{1,6}\s+', '', line).strip(), []
        else:
            lines.append(line)
    if lines:
        sections.append((heading, '\n'.join(lines)))
    chunks = []
    for section_index, (heading, content) in enumerate(sections):
        words = list(re.finditer(r'\S+', content))
        for start in range(0, len(words), size - overlap):
            end = min(start + size, len(words))
            a, b = words[start].start(), words[end - 1].end()
            chunks.append(dict(section_index=section_index, heading=heading,
                               parent_text=content, content=content[a:b], start=a, end=b))
            if end == len(words):
                break
    return chunks


class LocalKnowledgeStore:
    """SQLite staging store; vectors are JSON until a pgvector provider is selected."""
    def __init__(self, path):
        self.path = str(path)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, version TEXT NOT NULL,
                    source_url TEXT NOT NULL, license TEXT NOT NULL, document_type TEXT NOT NULL,
                    checksum TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft', reviewer TEXT,
                    embedding_model TEXT NOT NULL, dimensions INTEGER NOT NULL,
                    UNIQUE(source_url, version));
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
                    ordinal INTEGER NOT NULL, payload TEXT NOT NULL, embedding TEXT NOT NULL);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            with db:
                yield db
        finally:
            db.close()

    def ingest(self, path, source: Source, embedder: Embedder):
        path = Path(path)
        if path.suffix.lower() not in ('.md', '.txt'):
            raise ValueError('Only UTF-8 Markdown and plain text are supported')
        if any(not value.strip() for value in vars(source).values()):
            raise ValueError('All source provenance fields are required')
        if path.stat().st_size > 5_000_000:
            raise ValueError('Document exceeds the 5 MB staging limit')
        text = path.read_text(encoding='utf-8')
        chunks = section_chunks(text)
        if not chunks:
            raise ValueError('Document is empty')
        vectors = embedder.embed([chunk['content'] for chunk in chunks])
        if len(vectors) != len(chunks) or not vectors or not vectors[0]:
            raise ValueError('Embedding count or dimension mismatch')
        dimensions = len(vectors[0])
        if any(len(v) != dimensions or any(type(x) not in (int, float) or not math.isfinite(x) for x in v) for v in vectors):
            raise ValueError('Invalid embedding vector')
        checksum = hashlib.sha256(text.encode()).hexdigest()
        identity = hashlib.sha256((source.source_url + '\n' + source.version).encode()).hexdigest()
        with self.connection() as db:
            existing = db.execute('SELECT checksum, embedding_model FROM documents WHERE id=?', (identity,)).fetchone()
            if existing:
                if existing != (checksum, embedder.model):
                    raise ValueError('Version is immutable; use a new document version')
                return identity
            db.execute('INSERT INTO documents (id,title,version,source_url,license,document_type,checksum,embedding_model,dimensions) VALUES (?,?,?,?,?,?,?,?,?)',
                       (identity, source.title, source.version, source.source_url, source.license, source.document_type, checksum, embedder.model, dimensions))
            for ordinal, (chunk, vector) in enumerate(zip(chunks, vectors)):
                db.execute('INSERT INTO chunks VALUES (?,?,?,?,?)',
                           (f'{identity}:{ordinal}', identity, ordinal, json.dumps(chunk), json.dumps(vector)))
        return identity

    def approve(self, document_id, reviewer):
        if not reviewer.strip():
            raise ValueError('Reviewer is required')
        with self.connection() as db:
            if db.execute("UPDATE documents SET status='approved', reviewer=? WHERE id=? AND status='draft'", (reviewer.strip(), document_id)).rowcount != 1:
                raise ValueError('Draft document not found')

    def approved_chunks(self):
        with self.connection() as db:
            rows = db.execute("SELECT c.id,c.payload,c.embedding,d.embedding_model,d.title,d.version,d.source_url,d.document_type FROM chunks c JOIN documents d ON d.id=c.document_id WHERE d.status='approved'").fetchall()
        return [(row[0], json.dumps({**json.loads(row[1]), 'source': dict(title=row[4], version=row[5], source_url=row[6], document_type=row[7])}), row[2], row[3]) for row in rows]

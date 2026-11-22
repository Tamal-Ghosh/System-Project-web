CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id text PRIMARY KEY, title text NOT NULL, version text NOT NULL,
    source_url text NOT NULL, license text NOT NULL, document_type text NOT NULL,
    checksum text NOT NULL, status text NOT NULL CHECK(status IN ('draft','approved','retired')),
    reviewer text, embedding_model text NOT NULL, dimensions integer NOT NULL CHECK(dimensions=768)
);
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id text PRIMARY KEY, document_id text NOT NULL REFERENCES knowledge_documents(id),
    ordinal integer NOT NULL, payload jsonb NOT NULL, embedding vector(768) NOT NULL
);
CREATE INDEX IF NOT EXISTS knowledge_chunks_document_idx ON knowledge_chunks(document_id);

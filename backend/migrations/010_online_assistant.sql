-- Backend-only chatbot storage; deliberately outside public/Data API schemas.
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE SCHEMA IF NOT EXISTS assistant;
SET LOCAL search_path TO assistant, extensions, public;
CREATE TABLE IF NOT EXISTS assistant.case_sessions (
    analysis_id text PRIMARY KEY, token_hash text NOT NULL,
    expires double precision NOT NULL, context jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS case_sessions_expiry_idx ON assistant.case_sessions(expires);
CREATE TABLE IF NOT EXISTS assistant.messages (
    id uuid PRIMARY KEY, analysis_id text NOT NULL, question text NOT NULL,
    response jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
    sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE
);
CREATE INDEX IF NOT EXISTS messages_case_order_idx ON assistant.messages(analysis_id, sequence DESC);
CREATE TABLE IF NOT EXISTS assistant.feedback (
    id uuid PRIMARY KEY, message_id uuid NOT NULL REFERENCES assistant.messages(id),
    rating text NOT NULL CHECK(rating IN ('helpful','unhelpful')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS assistant.knowledge_documents (
    id text PRIMARY KEY, title text NOT NULL, version text NOT NULL,
    source_url text NOT NULL, license text NOT NULL, document_type text NOT NULL,
    checksum text NOT NULL, status text NOT NULL CHECK(status IN ('draft','approved','retired')),
    reviewer text, embedding_model text NOT NULL, dimensions integer NOT NULL CHECK(dimensions=768)
);
CREATE TABLE IF NOT EXISTS assistant.knowledge_chunks (
    id text PRIMARY KEY, document_id text NOT NULL REFERENCES assistant.knowledge_documents(id),
    ordinal integer NOT NULL, payload jsonb NOT NULL, embedding vector(768) NOT NULL
);
CREATE INDEX IF NOT EXISTS knowledge_chunks_document_idx ON assistant.knowledge_chunks(document_id);
ALTER TABLE assistant.case_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE assistant.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE assistant.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE assistant.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE assistant.knowledge_chunks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON SCHEMA assistant FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA assistant FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA assistant FROM PUBLIC;
DO $block$
DECLARE role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
        IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=role_name) THEN
            EXECUTE format('REVOKE ALL ON SCHEMA assistant FROM %I',role_name);
            EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA assistant FROM %I',role_name);
            EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA assistant FROM %I',role_name);
        END IF;
    END LOOP;
END $block$;

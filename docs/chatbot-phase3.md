# Local knowledge ingestion

`assistant.ingestion.LocalKnowledgeStore` stages UTF-8 Markdown and text files in
an explicitly provided local SQLite database. It does not read DATABASE_URL or
connect to Supabase. Supply title, source URL/URN, license, version and document
type through `Source`, and an embedding provider implementing `model` and `embed`.

Documents enter as drafts. `approve(document_id, reviewer)` is an explicit local
administrative operation. `approved_chunks()` excludes drafts. Source versions
are immutable; changed text or embedding models require a new source version.
Identical ingestion is idempotent. Embedding failures do not publish documents.

Chunking follows Markdown headings with 300-word children and 40-word overlap,
preserving parent text and character offsets. These are starting parameters;
they are not token counts. PDF/HTML parsing is not implemented in this stage.

Tests use fixed vectors only to verify contracts. Those vectors do not provide
semantic retrieval. Real embeddings, pgvector storage and retrieval are still
pending. No clinical documents have been approved or seeded automatically.

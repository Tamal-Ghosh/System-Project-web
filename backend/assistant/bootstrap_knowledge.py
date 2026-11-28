"""Import packaged, already embedded references into the local pgvector service."""
import os
from assistant.ingestion import LocalKnowledgeStore
from assistant.vector_store import PostgresKnowledgeStore


def main():
    source = LocalKnowledgeStore(os.getenv('KNOWLEDGE_PATH', '/opt/knowledge/assistant-knowledge.sqlite'))
    destination = PostgresKnowledgeStore(os.environ['KNOWLEDGE_DATABASE_URL'])
    destination.import_local(source)
    print('Local reviewed knowledge import completed; no external embedding request made.')


if __name__ == '__main__': main()

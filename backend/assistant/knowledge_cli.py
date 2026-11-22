"""Local administration: python -m assistant.knowledge_cli --help."""
import argparse
from pathlib import Path
from dotenv import load_dotenv
from assistant.ingestion import LocalKnowledgeStore, Source
from assistant.gemini import GeminiEmbeddings
from assistant.retrieval import HybridRetriever
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, help='Explicit local SQLite staging path')
    commands = parser.add_subparsers(dest='command', required=True)
    ingest = commands.add_parser('ingest')
    ingest.add_argument('path')
    for field in ('title', 'version', 'source-url', 'license', 'document-type'):
        ingest.add_argument('--'+field, required=True)
    approve = commands.add_parser('approve')
    approve.add_argument('document_id')
    approve.add_argument('--reviewer', required=True)
    search = commands.add_parser('search')
    search.add_argument('question')
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1]/'.env', override=False)
    store = LocalKnowledgeStore(args.database)
    if args.command == 'ingest':
        source = Source(args.title, args.version, args.source_url, args.license, args.document_type)
        print(store.ingest(args.path, source, GeminiEmbeddings()))
    elif args.command == 'approve':
        store.approve(args.document_id, args.reviewer)
        print('Approved for local development retrieval')
    else:
        print(json.dumps(HybridRetriever(store, GeminiEmbeddings()).search(args.question), indent=2))


if __name__ == '__main__':
    main()

"""Explicitly opt-in embedding of the public educational class summaries."""
import argparse,json
from pathlib import Path
from assistant.ingestion import LocalKnowledgeStore,Source
from assistant.gemini import GeminiEmbeddings


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--docs',type=Path,required=True);parser.add_argument('--store',type=Path,required=True)
    parser.add_argument('--approve-source-summaries',action='store_true',help='Approve public-source paraphrases, not clinician validation')
    args=parser.parse_args();store=LocalKnowledgeStore(args.store);embedder=GeminiEmbeddings()
    for entry in json.loads((args.docs/'knowledge/classes/manifest.json').read_text(encoding='utf-8')):
        path=args.docs/entry.pop('path').removeprefix('docs/');source=Source(**entry)
        with store.connection() as db:
            row=db.execute('SELECT id,status FROM documents WHERE source_url=? AND version=?',(source.source_url,source.version)).fetchone()
        if row:identity,status=row
        else:identity,status=store.ingest(path,source,embedder),'draft'
        if status=='draft' and args.approve_source_summaries:
            store.approve(identity,'Public-source provenance checked; educational paraphrase, not clinician validation')
        print(source.version,'indexed',flush=True)

if __name__=='__main__':main()

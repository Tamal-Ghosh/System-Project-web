"""Explicit publisher-only seed of public educational overviews; no embeddings generated."""
import argparse,json,os
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true',required=True)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--migration',type=Path,required=True);args=parser.parse_args()
    payload=json.loads(args.source.read_text(encoding='utf-8'))
    with psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=8) as db:
        prepared=[]
        for label,languages in payload['classes'].items():
            rows=db.execute("SELECT c.id,d.id,d.checksum FROM assistant.knowledge_chunks c JOIN assistant.knowledge_documents d ON d.id=c.document_id WHERE d.status='approved' AND d.document_type='clinical_class_summary' AND split_part(c.payload->>'heading',' ',1)=%s",(label,)).fetchall()
            if not rows or set(languages)!={'en','bn'}:raise ValueError('Missing source or language')
            ids=[r[0] for r in rows];checksums={r[1]:r[2] for r in rows}
            for language,answer in languages.items():prepared.append((label,language,payload['version'],answer,Jsonb(ids),Jsonb(checksums)))
        db.execute(args.migration.read_text(encoding='utf-8'))
        for row in prepared:
            db.execute('INSERT INTO assistant.class_overviews(class_label,language,version,answer,source_ids,source_checksums) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(class_label,language) DO UPDATE SET version=excluded.version,answer=excluded.answer,source_ids=excluded.source_ids,source_checksums=excluded.source_checksums',row)
        print('Source-bound educational overviews installed:',len(prepared))

if __name__=='__main__':main()

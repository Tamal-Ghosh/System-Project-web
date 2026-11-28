"""Explicit one-time Supabase migration; secrets never printed or baked into images."""
import argparse,json,os,secrets,sqlite3,sys
from pathlib import Path
from urllib.parse import quote,urlunsplit,urlencode
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.types.json import Jsonb
from dotenv import set_key
from assistant.ingestion import LocalKnowledgeStore
from assistant.vector_store import PostgresKnowledgeStore
from assistant.postgres_storage import storage_health


def local_rows(path,query):
    if not path.is_file():return []
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:return db.execute(query).fetchall()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true',required=True)
    parser.add_argument('--history-dir',type=Path,required=True);parser.add_argument('--knowledge',type=Path,required=True)
    parser.add_argument('--migration',type=Path,required=True);parser.add_argument('--env-file',type=Path,required=True)
    args=parser.parse_args();admin_url=os.environ['DATABASE_URL']
    with psycopg.connect(admin_url,connect_timeout=8) as db:db.execute(args.migration.read_text(encoding='utf-8'))
    PostgresKnowledgeStore(admin_url,schema='assistant').import_local(LocalKnowledgeStore(args.knowledge))
    messages=local_rows(args.history_dir/'chat-history.sqlite','SELECT id,analysis_id,question,response,created_at FROM messages ORDER BY rowid')
    feedback=local_rows(args.history_dir/'chat-history.sqlite','SELECT id,message_id,rating,created_at FROM feedback ORDER BY rowid')
    sessions=local_rows(args.history_dir/'case-sessions.sqlite','SELECT analysis_id,token_hash,expires,context FROM case_sessions')
    with psycopg.connect(admin_url,connect_timeout=8) as db:
        for identity,analysis,question,response,created in messages:
            db.execute('INSERT INTO assistant.messages(id,analysis_id,question,response,created_at) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING',(identity,analysis,question,Jsonb(json.loads(response)),created))
        for identity,message,rating,created in feedback:
            db.execute('INSERT INTO assistant.feedback(id,message_id,rating,created_at) VALUES (%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING',(identity,message,rating,created))
        for analysis,digest,expires,context in sessions:
            db.execute('INSERT INTO assistant.case_sessions(analysis_id,token_hash,expires,context) VALUES (%s,%s,%s,%s) ON CONFLICT(analysis_id) DO UPDATE SET token_hash=excluded.token_hash,expires=excluded.expires,context=excluded.context WHERE assistant.case_sessions.expires<excluded.expires',(analysis,digest,expires,Jsonb(json.loads(context))))
        for table,rows in [('messages',messages),('feedback',feedback)]:
            ids=[row[0] for row in rows]
            count=db.execute(sql.SQL('SELECT count(*) FROM assistant.{} WHERE id=ANY(%s::uuid[])').format(sql.Identifier(table)),(ids,)).fetchone()[0]
            if count!=len(ids):raise RuntimeError('Migration count mismatch')
        print('Imported messages/feedback/sessions:',len(messages),len(feedback),len(sessions),flush=True)
    role='dermascope_chat_runtime';existing_url=os.getenv('ASSISTANT_DATABASE_URL','')
    with psycopg.connect(admin_url,connect_timeout=8) as db:
        exists=db.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone()
        if exists:
            if not existing_url:raise RuntimeError('Runtime role exists but credentials are not configured; no password was reset')
            runtime_url=existing_url
        else:
            password=secrets.token_urlsafe(36)
            db.execute(sql.SQL('CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
            params=conninfo_to_dict(admin_url);old_user=params.get('user','postgres');suffix=old_user[len('postgres'):] if old_user.startswith('postgres') else ''
            username=role+suffix;host=params['host'];host='['+host+']' if ':' in host else host
            runtime_url=urlunsplit(('postgresql',quote(username,safe='')+':'+quote(password,safe='')+'@'+host+':'+str(params.get('port','5432')),'/'+quote(params.get('dbname','postgres'),safe=''),urlencode({'sslmode':'require','application_name':'dermascope-chatbot'}),''))
        db.execute(sql.SQL('GRANT USAGE ON SCHEMA assistant,extensions TO {}').format(sql.Identifier(role)))
        for table in ('case_sessions','messages','feedback','knowledge_documents','knowledge_chunks'):
            access='SELECT' if table.startswith('knowledge_') else 'SELECT,INSERT,UPDATE,DELETE'
            db.execute(sql.SQL('GRANT '+access+' ON assistant.{} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
            if not db.execute("SELECT 1 FROM pg_policies WHERE schemaname='assistant' AND tablename=%s AND policyname='backend_runtime'",(table,)).fetchone():
                action='SELECT' if table.startswith('knowledge_') else 'ALL'
                tail=' USING (true)' if action=='SELECT' else ' USING (true) WITH CHECK (true)'
                db.execute(sql.SQL('CREATE POLICY backend_runtime ON assistant.{} FOR '+action+' TO {}'+tail).format(sql.Identifier(table),sql.Identifier(role)))
        db.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA assistant TO {}').format(sql.Identifier(role)))
    # Keep newly generated credentials even if the pooler has not learned the role yet.
    set_key(str(args.env_file),'ASSISTANT_DATABASE_URL',runtime_url)
    storage_health(runtime_url)
    with psycopg.connect(runtime_url,connect_timeout=8) as db:
        if db.execute("SELECT has_table_privilege(current_user,'assistant.knowledge_chunks','INSERT')").fetchone()[0]:raise RuntimeError('Runtime knowledge write access must be disabled')
        print('Restricted runtime connection: OK',flush=True)
    set_key(str(args.env_file),'ASSISTANT_STORAGE','postgres')
    print('Ignored backend env configured; no credentials printed.',flush=True)
    with psycopg.connect(admin_url,connect_timeout=8) as db:
        for table in ('knowledge_documents','knowledge_chunks','messages','feedback','case_sessions'):
            count=db.execute(sql.SQL('SELECT count(*) FROM assistant.{}').format(sql.Identifier(table))).fetchone()[0]
            print(table,count,flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Migration stopped safely:',type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)

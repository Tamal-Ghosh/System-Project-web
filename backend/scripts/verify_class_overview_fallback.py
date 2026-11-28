"""Opt-in synthetic cloud/API QA. No live Gemini requests or real patient records."""
import os,json
from uuid import uuid4
from unittest.mock import Mock,patch
from fastapi.testclient import TestClient
from assistant.gemini import GeminiUnavailable
from assistant.postgres_storage import assistant_database_url,connection
from assistant.class_overviews import PostgresClassOverviews
from scripts.evaluate_assistant import context
from inference_app import create_app
from PIL import Image
from io import BytesIO


def main():
    url=assistant_database_url();ids=[];checks=0
    with connection(url) as db:
        assert db.execute('SELECT count(*) FROM assistant.class_overviews').fetchone()[0]==22
        assert not db.execute("SELECT has_table_privilege(current_user,'assistant.class_overviews','INSERT')").fetchone()[0]
    repo=PostgresClassOverviews(url)
    for label in ('BCC','MEL','NV','AKIEC','SCCKA','BKL','DF','INF','BEN_OTH','MAL_OTH','VASC'):
        for language in ('en','bn'):
            result=repo.get(label,language)
            assert result and result[0]['answer_mode']=='reference_overview' and result[1]
    print('All 22 source-bound overviews and read-only access: PASS',flush=True)
    stream=BytesIO();Image.new('RGB',(4,4),(100,100,100)).save(stream,format='PNG')
    def predict(*args):
        case=context();case['analysis_id']=str(uuid4());ids.append(case['analysis_id']);return case
    service=Mock();service.requires_clinical=False;service.predict.side_effect=predict
    try:
        for stage in ('retrieval','generation'):
            generator=Mock();generator.answer.side_effect=GeminiUnavailable('Gemini chat unavailable (HTTP 503)')
            retriever=Mock();retriever.search.side_effect=GeminiUnavailable('Gemini embedding request failed (HTTP 503)') if stage=='retrieval' else None
            retriever.search.return_value=[]
            with patch.dict(os.environ,{'ASSISTANT_STORAGE':'postgres','ASSISTANT_PROVIDER':'gemini','ANALYSIS_PERSISTENCE_ENABLED':'false'}),patch('inference_app.GeminiCaseGenerator',return_value=generator),patch('inference_app.GeminiEmbeddings'),patch('inference_app.HybridRetriever',return_value=retriever),TestClient(create_app(lambda:service)) as client:
                case=client.post('/api/v1/analyses',data={'age':'40','sex':'male'},files={'image':('synthetic-qa.png',stream.getvalue(),'image/png')}).json()
                headers={'X-Case-Token':case['assistant_access_token']};body={'analysis_id':case['analysis_id']}
                for question in ('Tell details about the prediction class','ei rog ta nea bolo'):
                    r=client.post('/api/v1/chat/query',headers=headers,json={**body,'question':question})
                    assert r.status_code==200,r.text
                    answer=r.json();assert answer['answer_mode']=='reference_overview' and answer['notice'] and answer['citations']
                    assert all(c['heading'].startswith(case['leading_class']) for c in answer['citations'])
                    checks+=1
                history=client.get('/api/v1/chat/history/'+case['analysis_id'],headers=headers).json()
                assert len(history)==2 and all(row['response']['notice'] for row in history);checks+=1
                r=client.post('/api/v1/chat/query',headers=headers,json={**body,'question':'Tell me about melanoma treatment'})
                assert r.status_code==503;checks+=1
                r=client.post('/api/v1/chat/query',headers={'X-Case-Token':'wrong'},json={**body,'question':'Tell details about the prediction class'})
                assert r.status_code==403;checks+=1
            print(stage,'outage: fallback, language, history, custom-question boundary and case protection PASS',flush=True)
    finally:
        if ids:
            with connection(url) as db:
                db.execute('DELETE FROM assistant.feedback WHERE message_id IN (SELECT id FROM assistant.messages WHERE analysis_id=ANY(%s))',(ids,))
                db.execute('DELETE FROM assistant.messages WHERE analysis_id=ANY(%s)',(ids,))
                db.execute('DELETE FROM assistant.case_sessions WHERE analysis_id=ANY(%s)',(ids,))
    print('API checks:',checks,'passed; disposable records removed.',flush=True)

if __name__=='__main__':main()

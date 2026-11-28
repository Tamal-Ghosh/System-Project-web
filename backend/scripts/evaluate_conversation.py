"""Synthetic HTTP conversation QA; not clinical validation."""
import argparse,json,os,re,time
from pathlib import Path
from uuid import uuid4
import httpx
from assistant.sessions import CaseSessions
from assistant.postgres_storage import PostgresCaseSessions,assistant_database_url,connection
from evaluate_assistant import context


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--generation-only',action='store_true');args=parser.parse_args()
    case=context();case['analysis_id']=str(uuid4());case['leading_class']='BCC'
    for item in case['scores']:item['score']=.8409151434898376 if item['label']=='BCC' else .1176 if item['label']=='SCCKA' else (1-.8409151434898376-.1176)/9
    sessions=PostgresCaseSessions(assistant_database_url()) if os.getenv('ASSISTANT_STORAGE')=='postgres' else CaseSessions(path=os.environ['CASE_SESSION_PATH'])
    token=sessions.register(case)
    questions=[('what is the prediction','score'),('hi','social'),('how are you','social'),
       ('prediction ta ki','score'),('uncertainty ta bujhao','uncertainty'),('ক্যালিব্রেশন হয়েছে কি','calibration'),('model gula agreement koto','agreement'),
       ('what is the main reson behind the prediction','reason'),('check the other parameters','parameters'),
       ('tell details about the prediction class','disease'),('accha amay ei rog ta nea bolo','bangla'),
       ('explain that in Bangla','followup')]
    if args.generation_only:questions=[('prediction ta ki','score')]+[(q,kind) for q,kind in questions if kind in ('disease','bangla','followup')]
    rows=[]
    with httpx.Client(base_url='http://backend:8000',timeout=100) as client:
        for question,kind in questions:
            start=time.monotonic();response=client.post('/api/v1/chat/query',headers={'X-Case-Token':token},json={'analysis_id':case['analysis_id'],'question':question})
            row={'question':question,'kind':kind,'http_status':response.status_code}
            if response.status_code==200:
                result=response.json();text=result['answer'];citations=result['citations'];checks={'nonempty':bool(text),'no_internal_numeric_error':'unsupported number' not in text,'valid_status':result['status'] in ('answered','unavailable','out_of_scope')}
                if kind=='social':checks.update(no_sources=not citations,not_abstention=result['status']=='answered')
                if kind=='score':checks['readable_score']='84.1%' in text
                if kind=='uncertainty':checks['measured_values']='0.400' in text and '0.490' in text
                if kind=='calibration':checks['not_misrepresented']='প্রয়োগ হয়নি' in text
                if kind=='agreement':checks['not_invented']='পাওয়া যায়নি' in text or 'unavailable' in text.lower()
                if kind=='parameters':checks['verified_parameters']='Normalized entropy' in text and '84.1%' in text
                if kind=='reason':checks['explanation_scope']=any(term in text.lower() for term in ('xai','visual','feature','explainability'))
                if kind in ('disease','bangla','followup'):
                    checks['class_reference']=bool(citations) and all(c.get('source',{}).get('document_type')!='model_card' for c in citations)
                    checks['not_score_dump']='0.8409151434898376' not in text
                if kind=='disease':checks['english']=len(re.findall('[\u0980-\u09ff]',text))<20
                if question=='prediction ta ki':checks['banglish_response']=len(re.findall('[\u0980-\u09ff]',text))>20
                if kind in ('bangla','followup'):checks['bengali']=len(re.findall('[\u0980-\u09ff]',text))>30
                row.update(response=result,checks=checks,passed=all(checks.values()))
            else:row.update(passed=False,error='provider_or_application_error')
            row['elapsed_seconds']=round(time.monotonic()-start,2);rows.append(row)
            print(kind,'PASS' if row['passed'] else 'REVIEW',row['elapsed_seconds'],flush=True)
            args.output.write_text(json.dumps({'scope':'Synthetic conversational regression, not clinical validation','total':len(questions),'completed':len(rows),'passed':sum(x['passed'] for x in rows),'results':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    report={'scope':'Synthetic conversational regression, not clinical validation','total':len(rows),'passed':sum(x['passed'] for x in rows),'results':rows}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('Summary:',report['passed'],'/',report['total'])
    if os.getenv('ASSISTANT_STORAGE')=='postgres':
        with connection(assistant_database_url()) as db:
            db.execute('DELETE FROM assistant.feedback WHERE message_id IN (SELECT id FROM assistant.messages WHERE analysis_id=%s)',(case['analysis_id'],))
            db.execute('DELETE FROM assistant.messages WHERE analysis_id=%s',(case['analysis_id'],))
            db.execute('DELETE FROM assistant.case_sessions WHERE analysis_id=%s',(case['analysis_id'],))
        print('Only this run’s synthetic online records removed.',flush=True)
    if report['passed']!=report['total']:raise SystemExit(1)

if __name__=='__main__':main()

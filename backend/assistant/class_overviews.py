"""Version-bound educational fallback; never a patient diagnosis or tailored plan."""
import re
from assistant.conversation import CLASS_NAMES
from assistant.postgres_storage import connection


def eligible_overview(question,route):
    if route.get('intent')!='disease':return False
    q=question.casefold()
    specific=r'\bmy\b|\bpatient\b|\bam i\b|\bdo i\b|\brisk\b|difference|compar|versus|\bvs\b|আমার|রোগীর|এই ছবি|treat|medicin|dosage|\bdose\b|biopsy|surgery|stage|prognos|management|symptom|signs|spread|caus|dermoscop|differential|চিকিৎসা|ওষুধ|লক্ষণ|কেন|বায়োপসি|বায়োপসি|ছড়িয়ে|ছড়িয়ে'
    if re.search(specific,q):return False
    return bool(re.search(r'overview|details|about|what is|\brog\b|সম্পর্কে|রোগ|বিস্তারিত',q))


def validate_overview(label,language,card,sources):
    if label not in CLASS_NAMES or language not in ('en','bn') or not card:return None
    answer,version,ids,checksums=card
    if not isinstance(answer,str) or not 1<=len(answer)<=8000 or not isinstance(ids,list) or not ids or not isinstance(checksums,dict):return None
    if any(not isinstance(identity,str) for identity in ids):return None
    if set(ids)!={source['chunk_id'] for source in sources}:return None
    for source in sources:
        if source['status']!='approved' or source['document_type']!='clinical_class_summary':return None
        if checksums.get(source['document_id'])!=source['checksum']:return None
        heading=source.get('heading','')
        if not isinstance(heading,str) or not heading.startswith(label+' '):return None
    citations=[{'chunk_id':s['chunk_id'],'heading':s['heading'],'reference_urls':[s['source_url']],
                'source':{'title':s['title'],'version':s['version'],'source_url':s['source_url'],'document_type':s['document_type']}} for s in sources]
    notice=('Showing a source-based class overview because a tailored AI answer is unavailable.' if language=='en' else
            'AI-এর বিস্তারিত উত্তর পাওয়া যায়নি। Sources অনুযায়ী এই class-এর সাধারণ পরিচিতি দেখানো হচ্ছে।')
    return ({'status':'answered','answer':answer,'facts_used':['requested_class','knowledge_sources'],'source_ids':ids,
             'answer_mode':'reference_overview','notice':notice,'reference_version':version},citations)


class PostgresClassOverviews:
    def __init__(self,url):self.url=url
    def get(self,label,language):
        if label not in CLASS_NAMES or language not in ('en','bn'):return None
        with connection(self.url) as db:
            card=db.execute('SELECT answer,version,source_ids,source_checksums FROM assistant.class_overviews WHERE class_label=%s AND language=%s',(label,language)).fetchone()
            if not card or not isinstance(card[2],list) or not card[2] or any(not isinstance(identity,str) for identity in card[2]):return None
            rows=db.execute("SELECT c.id,c.payload,d.id,d.checksum,d.status,d.document_type,d.title,d.version,d.source_url FROM assistant.knowledge_chunks c JOIN assistant.knowledge_documents d ON d.id=c.document_id WHERE c.id=ANY(%s)",(card[2],)).fetchall()
        sources=[dict(chunk_id=r[0],heading=r[1].get('heading',''),document_id=r[2],checksum=r[3],status=r[4],document_type=r[5],title=r[6],version=r[7],source_url=r[8]) for r in rows]
        return validate_overview(label,language,card,sources)

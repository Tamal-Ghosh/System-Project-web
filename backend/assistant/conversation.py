"""Question routing and presentation from server-owned evidence only."""
import re

CLASS_NAMES = {'AKIEC':'Actinic keratosis and intraepidermal carcinoma','BCC':'Basal cell carcinoma',
 'BEN_OTH':'Other benign proliferations','BKL':'Benign keratinocytic lesions','DF':'Dermatofibroma',
 'INF':'Inflammatory and infectious conditions','MAL_OTH':'Other malignant proliferations',
 'MEL':'Melanoma','NV':'Melanocytic nevus','SCCKA':'Squamous cell carcinoma and keratoacanthoma','VASC':'Vascular lesions'}


def language(question, conversation=()):
    choices=list(re.finditer(r'\b(?:english|bangla|banglish)\b|ইংরেজি|বাংলা',question,re.I))
    if choices:return 'en' if choices[-1].group().casefold() in ('english','ইংরেজি') else 'bn'
    if re.search(r'[\u0980-\u09ff]|\b(amay|amake|bolo|rog|accha|kemon|ki obostha|eta|eita|koto|keno|bujhao|ki|hoise|daw|dao|korbo|ase|ache)\b',question,re.I):return 'bn'
    if conversation and re.fullmatch(r'(?:tell me more|more details|explain that|go on)[.!?]*',question.strip(),re.I):
        previous=next((turn['text'] for turn in reversed(conversation) if turn.get('role')=='user'),'')
        return language(previous,())
    return 'en'


def explicit_class(question):
    aliases={'MEL':('melanoma','মেলানোমা'),'BCC':('basal cell carcinoma','বেসাল সেল'),
             'NV':('nevus','naevus','mole'),'SCCKA':('squamous cell carcinoma','keratoacanthoma')}
    for key,name in CLASS_NAMES.items():
        if re.search(r'(?<!\w)'+re.escape(key)+r'(?!\w)',question,re.I):return key
        if name.casefold() in question.casefold():return key
        if any(re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',question,re.I) for alias in aliases.get(key,())):return key
    return None


def route_question(question, context, conversation=()):
    q=question.casefold().strip().rstrip('?.!');lang=language(question,conversation)
    if re.fullmatch(r'(?:hi|hello|hey)(?:[, ]+(?:doctor|there|assistant))?',q) or q in ('হ্যালো','hi','hello','hey','how are you','how are you doing','thanks','thank you','kemon acho','কেমন আছো','ধন্যবাদ','how r u','ki obostha'):
        text=('আমি সাহায্য করতে প্রস্তুত। এই analysis বা skin lesion সম্পর্কে কী জানতে চাও?' if lang=='bn' else
              'I’m ready to help. What would you like to review about this analysis or skin lesion?')
        if q in ('thanks','thank you','ধন্যবাদ'):text='স্বাগতম। আর কিছু জানতে চাইলে বলো।' if lang=='bn' else 'You’re welcome. Let me know what else you would like to review.'
        return {'intent':'social','language':lang,'response':{'status':'answered','answer':text,'facts_used':[]}}
    named=explicit_class(question);label=named or context['leading_class'];inherited=None
    followup=bool(re.search(r'explain that|tell me more|more details|same in|translate that|english please|bangla please|this disease|this condition|ei rog|আরও|বিস্তারিত|এই রোগ|এই রোগটা',q))
    if named is None and followup:
        for turn in reversed(conversation):
            if turn.get('role')!='user':continue
            previous=route_question(turn['text'],context,())
            if previous['intent']=='social':continue
            if previous['intent']=='disease':inherited=previous;label=previous['class_label'];break
            if explicit_class(turn['text']):break
    disease=bool(inherited or re.search(r'details? about|about (?:the |this )?(?:disease|condition|class)|\brog\b|রোগ|সম্পর্কে',q))
    if named and re.search(r'about|details|what is|কি|বলো|bolo',q):disease=True
    parameters=bool(re.search(r'other parameters|all parameters|check.*parameters|বাকি.*প্যারামিটার|অন্য.*প্যারামিটার',q))
    reason=bool(re.search(r'(?:reason|reson|why|keno).*(?:predict|class|score)|(?:predict|class|score).*(?:reason|keno)|কেন.*(?:বল|prediction|প্রেডিকশন)|(?:prediction|প্রেডিকশন).*কেন',q))
    fact=None
    if re.search(r'uncertainty|entropy|top.two margin|অনিশ্চয়তা|অনিশ্চয়তা',q):fact='uncertainty'
    elif re.search(r'calibrat|temperature scaling|ক্যালিব্রেশন',q):fact='calibration'
    elif re.search(r'agreement|মডেল.*একমত',q):fact='agreement'
    elif re.search(r'limitations?|সীমাবদ্ধতা',q):fact='limitations'
    elif not disease and re.search(r'scores?|prediction|classification|result|প্রেডিকশন|ফলাফল|স্কোর',q):fact='prediction'
    intent='reason' if reason else 'parameters' if parameters else 'disease' if disease else fact or 'case'
    query=question
    if intent=='reason':query='Current DermFM model explainability, missing XAI evidence and classification interpretation. '+question
    if intent=='disease':query=f"{label} {CLASS_NAMES[label]} clinical overview signs diagnosis assessment. Question: {question}"
    return {'intent':intent,'language':lang,'class_label':label,'class_name':CLASS_NAMES[label],
            'explicit_class':named is not None,'all_scores':bool(re.search(r'all.*scores|class scores|সব.*স্কোর',q)), 'retrieval_question':query}


def display_facts(context):
    scores=sorted(context['scores'],key=lambda item:item['score'],reverse=True)
    return {'class_scores':[{'label':x['label'],'name':CLASS_NAMES.get(x['label'],x['label']),
             'percent':f"{x['score']*100:.1f}%"} for x in scores],
            'uncertainty':{key:f'{value:.3f}' for key,value in context.get('uncertainty',{}).items() if type(value) in (int,float)}}


def parameter_answer(context,lang='en'):
    facts=display_facts(context);scores=facts['class_scores'];u=facts['uncertainty'];ensemble=context.get('ensemble',{})
    lines=[('Available case parameters:' if lang=='en' else 'এই analysis-এর পাওয়া তথ্যগুলো:'),
      '\n'.join(f"• {x['name']} ({x['label']}): {x['percent']}" for x in scores[:3])]
    for key,title in (('normalized_entropy','Normalized entropy'),('top_two_margin','Top-two margin')):
        if key in u:lines.append(f"{title}: {u[key]}")
    calibration=context.get('calibration') or {}
    state=('unavailable' if 'applied' not in calibration else 'applied' if calibration['applied'] else 'not applied') if lang=='en' else ('পাওয়া যায়নি' if 'applied' not in calibration else 'প্রয়োগ হয়েছে' if calibration['applied'] else 'প্রয়োগ হয়নি')
    lines.append('Live temperature scaling: '+state)
    if ensemble.get('agreement') is None:lines.append('Fold agreement: unavailable.' if lang=='en' else 'Fold agreement: পাওয়া যায়নি।')
    lines.append('These are model outputs, not a confirmed diagnosis.' if lang=='en' else 'এগুলো model-এর output; নিশ্চিত রোগনির্ণয় নয়।')
    return {'status':'answered','answer':'\n\n'.join(lines),'facts_used':['scores','uncertainty','ensemble','calibration']}


def used_citations(answer,citations):
    """Only explicit source IDs survive, with duplicate passages removed."""
    used=set(answer.get('source_ids',[]));result=[];seen=set()
    for source in citations:
        if source['chunk_id'] not in used:continue
        key=(source.get('source',{}).get('source_url'),source['heading'])
        if key in seen:continue
        seen.add(key);result.append(source)
    return result


def prediction_answer(context,lang='en',all_scores=False,requested_label=None):
    rows=display_facts(context)['class_scores'];top=next((row for row in rows if row['label']==requested_label),rows[0])
    if requested_label and all(row['label']!=requested_label for row in rows):
        return {'status':'unavailable','answer':('No measured score is available for that class.' if lang=='en' else 'এই class-এর measured score পাওয়া যায়নি।'),'facts_used':[]}
    if requested_label and requested_label!=rows[0]['label']:
        text=(f"{top['name']} ({top['label']}) has a model score of {top['percent']}." if lang=='en' else f"{top['name']} ({top['label']})-এর model score {top['percent']}।")
        return {'status':'answered','answer':text,'facts_used':['scores']}
    text=(f"The leading class is {top['name']} ({top['label']}), with a model score of {top['percent']}." if lang=='en' else
          f"মডেল সবচেয়ে বেশি score দিয়েছে {top['name']} ({top['label']})-কে: {top['percent']}।")
    if all_scores:text+='\n\n'+'\n'.join(f"• {row['label']}: {row['percent']}" for row in rows)
    text+=(' This is a model output, not a confirmed diagnosis or calibrated disease risk.' if lang=='en' else
           ' এটি model-এর output; নিশ্চিত রোগনির্ণয় বা calibrated disease risk নয়।')
    return {'status':'answered','answer':text,'facts_used':['scores','leading_class']}


def reason_answer(context,lang='en'):
    rows=display_facts(context)['class_scores'];top=rows[0]
    if lang=='bn':
        text=f"এই analysis-এ মডেল {top['name']} ({top['label']})-কে সবচেয়ে বেশি score দিয়েছে—{top['percent']}।"
        if len(rows)>1:text+=f" পরের class {rows[1]['name']} ({rows[1]['label']}): {rows[1]['percent']}।"
        text+='\n\nতবে ছবির ঠিক কোন বৈশিষ্ট্য এই ফলকে প্রভাবিত করেছে, তা বলার মতো matching XAI evidence নেই। তাই দৃশ্যমান কোনো বৈশিষ্ট্যকে এই prediction-এর কারণ বলা যাবে না। চাইলে uncertainty বা অন্য class-এর score ব্যাখ্যা করতে পারি।'
    else:
        text=f"The model ranks {top['name']} ({top['label']}) highest, with a score of {top['percent']}."
        if len(rows)>1:text+=f" The next class is {rows[1]['name']} ({rows[1]['label']}) at {rows[1]['percent']}."
        text+='\n\nThose scores describe the result, but do not establish its visual cause. There is no matching XAI evidence showing which image features influenced this prediction. I can help review uncertainty or the competing class scores.'
    return {'status':'answered','answer':text,'facts_used':['scores','xai']}


def case_fact_answer(intent,context,lang='en'):
    if intent=='uncertainty':
        values=display_facts(context)['uncertainty']
        if not all(key in values for key in ('normalized_entropy','top_two_margin')):
            return {'status':'unavailable','answer':'Uncertainty values are unavailable.' if lang=='en' else 'এই analysis-এর uncertainty values পাওয়া যায়নি।','facts_used':[]}
        text=(f"Normalized entropy: {values['normalized_entropy']}. Lower entropy means the scores are more concentrated among fewer classes.\n\nTop-two margin: {values['top_two_margin']}. This is the gap between the two highest model scores, not a measure of diagnostic correctness." if lang=='en' else
              f"Normalized entropy: {values['normalized_entropy']}। কম entropy মানে model-এর score কমসংখ্যক class-এর মধ্যে বেশি কেন্দ্রীভূত।\n\nTop-two margin: {values['top_two_margin']}। এটি সর্বোচ্চ দুটি score-এর ব্যবধান; diagnosis সঠিক হওয়ার মাপ নয়।")
        return {'status':'answered','answer':text,'facts_used':['uncertainty']}
    if intent=='calibration':
        calibration=context.get('calibration')
        if not isinstance(calibration,dict) or 'applied' not in calibration:
            return {'status':'unavailable','answer':'Live calibration status is unavailable.' if lang=='en' else 'Live calibration status পাওয়া যায়নি।','facts_used':[]}
        text=('Temperature scaling is applied to the live class scores.' if calibration['applied'] else 'Temperature scaling is not applied to these live class scores.') if lang=='en' else ('Live class score-এ temperature scaling প্রয়োগ হয়েছে।' if calibration['applied'] else 'এই live class score-এ temperature scaling প্রয়োগ হয়নি।')
        text+=(' Evaluation-level calibration metrics do not certify this individual prediction.' if lang=='en' else ' Evaluation-এর calibration metrics এই নির্দিষ্ট prediction-এর নিশ্চয়তা দেয় না।')
        return {'status':'answered','answer':text,'facts_used':['calibration']}
    if intent=='agreement':
        ensemble=context.get('ensemble',{});agreement=ensemble.get('agreement')
        text=('Fold agreement is unavailable for this analysis. The ensemble result alone does not tell us whether all members agreed.' if lang=='en' else 'এই analysis-এর fold agreement পাওয়া যায়নি। শুধু ensemble result দেখে সব model একমত ছিল বলা যায় না।') if agreement is None else (f"Measured fold agreement: {agreement}." if lang=='en' else f"Measured fold agreement: {agreement}।")
        return {'status':'unavailable' if agreement is None else 'answered','answer':text,'facts_used':['ensemble']}
    return {'status':'answered' if context.get('limitations') else 'unavailable',
            'answer':'\n'.join(context.get('limitations',[])) or ('No recorded limitations were supplied.' if lang=='en' else 'Recorded limitations পাওয়া যায়নি।'),'facts_used':['limitations']}

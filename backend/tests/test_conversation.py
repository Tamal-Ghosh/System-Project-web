import unittest
from assistant.conversation import route_question,parameter_answer,used_citations
from assistant.validation import validate_answer

class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.case={'leading_class':'BCC','scores':[{'label':'BCC','score':.8409151434898376},{'label':'SCCKA','score':.1590848565101624}],
                   'uncertainty':{'normalized_entropy':.456789,'top_two_margin':.6818302869},'ensemble':{'agreement':None},'calibration':{'applied':False}}
    def test_social_is_not_medical_retrieval(self):
        route=route_question('how are you',self.case)
        self.assertEqual(route['intent'],'social');self.assertNotIn('Evidence',route['response']['answer'])
    def test_disease_details_resolve_current_class(self):
        for q in ('tell details about the prediction class','accha amay ei rog ta nea bolo'):
            route=route_question(q,self.case)
            self.assertEqual(route['intent'],'disease');self.assertIn('Basal cell carcinoma',route['retrieval_question'])
        self.assertEqual(route['language'],'bn')
    def test_explicit_class_overrides_leading_class(self):
        route=route_question('Tell me about melanoma',self.case)
        self.assertEqual(route['class_label'],'MEL')
    def test_parameters_are_grounded_and_readable(self):
        route=route_question('check the other parameters',self.case)
        self.assertEqual(route['intent'],'parameters')
        result=parameter_answer(self.case)
        self.assertIn('84.1%',result['answer']);self.assertIn('not applied',result['answer'])
    def test_only_approved_numeric_display_forms_pass(self):
        response={'status':'answered','answer':'BCC score: 84.1%','facts_used':['scores']}
        self.assertEqual(validate_answer(response,self.case)['status'],'answered')
        response['answer']='BCC score: 84.5%'
        self.assertEqual(validate_answer(response,self.case)['status'],'unavailable')
    def test_only_used_sources_are_shown(self):
        rows=[{'chunk_id':'a','heading':'BCC','source':{'source_url':'https://example.org/a'}},
              {'chunk_id':'b','heading':'Model','source':{'source_url':'https://example.org/b'}}]
        self.assertEqual(used_citations({'source_ids':['a']},rows),[rows[0]])
        self.assertEqual(used_citations({'source_ids':[]},rows),[])

    def test_source_numbers_need_selected_reference(self):
        result={'status':'answered','answer':'The reference reports 12 cases.','facts_used':['knowledge_sources']}
        self.assertEqual(validate_answer(result,{'knowledge_sources':[{'excerpt':'12 cases'}]})['status'],'answered')
        self.assertEqual(validate_answer(result,{'knowledge_sources':[]})['status'],'unavailable')

    def test_disease_followup_keeps_the_same_class_route(self):
        route=route_question('Explain that in Bangla',self.case,[{'role':'user','text':'Tell details about the prediction class'}])
        self.assertEqual(route['intent'],'disease');self.assertEqual(route['language'],'bn')
        self.assertIn('Basal cell carcinoma',route['retrieval_question'])

    def test_missing_xai_reason_is_a_grounded_result_not_a_cause_claim(self):
        from assistant.conversation import reason_answer
        answer=reason_answer({**self.case,'xai':None})
        self.assertIn('84.1%',answer['answer']);self.assertIn('no matching XAI',answer['answer'])
        self.assertNotIn('shows a',answer['answer'])

    def test_banglish_case_questions_do_not_need_a_provider(self):
        expected={'prediction ta ki':'prediction','uncertainty ta bujhao':'uncertainty','calibration hoise ki':'calibration','model gula agreement koto':'agreement','hi doctor':'social'}
        for question,intent in expected.items():
            with self.subTest(question=question):self.assertEqual(route_question(question,self.case)['intent'],intent)
    def test_explicit_language_instruction_wins(self):
        from assistant.conversation import language
        self.assertEqual(language('BCC সম্পর্কে English এ বলো'),'en')
        self.assertEqual(language('English na Bangla bolo'),'bn')
    def test_followup_skips_social_and_keeps_named_disease(self):
        history=[{'role':'user','text':'tell me about melanoma'},{'role':'model','text':'Reference overview.'},{'role':'user','text':'thanks'}]
        route=route_question('আরও বিস্তারিত বলো',self.case,history)
        self.assertEqual(route['intent'],'disease');self.assertEqual(route['class_label'],'MEL')
    def test_explicit_new_class_is_not_overridden_by_previous_disease(self):
        route=route_question('more details about BCC',self.case,[{'role':'user','text':'tell me about melanoma'}])
        self.assertEqual(route['class_label'],'BCC')
    def test_requested_low_scoring_class_is_not_called_the_leader(self):
        from assistant.conversation import prediction_answer
        result=prediction_answer(self.case,requested_label='SCCKA')
        self.assertIn('15.9%',result['answer']);self.assertNotIn('leading',result['answer'].lower())
    def test_missing_calibration_is_not_reported_as_not_applied(self):
        from assistant.conversation import case_fact_answer
        case={**self.case};case.pop('calibration')
        self.assertEqual(case_fact_answer('calibration',case)['status'],'unavailable')
        self.assertIn('unavailable',parameter_answer(case)['answer'])

    def test_short_language_followup_keeps_previous_class(self):
        route=route_question('same in English',self.case,[{'role':'user','text':'tell me about melanoma'}])
        self.assertEqual(route['class_label'],'MEL');self.assertEqual(route['intent'],'disease');self.assertEqual(route['language'],'en')
        self.assertEqual(route_question('prediction ta ki',self.case)['language'],'bn')

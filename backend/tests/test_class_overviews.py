import unittest
from assistant.class_overviews import eligible_overview,validate_overview
from assistant.conversation import route_question

class ClassOverviewTests(unittest.TestCase):
    def setUp(self):
        self.card=('General source-based educational information.','2026-11-25',['chunk'],{'doc':'hash'})
        self.sources=[dict(chunk_id='chunk',heading='BCC — Overview',document_id='doc',checksum='hash',status='approved',document_type='clinical_class_summary',title='Reference',version='v1',source_url='https://example.org/reference')]
        self.context={'leading_class':'BCC'}
    def test_general_details_qualify_but_custom_clinical_questions_do_not(self):
        for q in ('Tell details about the prediction class','ei rog ta nea bolo','এই রোগটা সম্পর্কে বলো'):
            self.assertTrue(eligible_overview(q,route_question(q,self.context)))
        for q in ('Tell me about BCC treatment','What is my BCC stage?','Tell me about BCC dermoscopy','What is the difference between BCC and melanoma?'):
            self.assertFalse(eligible_overview(q,route_question(q,self.context)))
    def test_fallback_is_labelled_and_has_its_exact_sources(self):
        answer,citations=validate_overview('BCC','en',self.card,self.sources)
        self.assertEqual(answer['answer_mode'],'reference_overview');self.assertIn('unavailable',answer['notice'])
        self.assertEqual(answer['source_ids'],['chunk']);self.assertEqual(citations[0]['reference_urls'],['https://example.org/reference'])
    def test_stale_missing_retired_and_wrong_class_sources_fail_closed(self):
        for sources in ([],[{**self.sources[0],'checksum':'changed'}],[{**self.sources[0],'status':'retired'}],[{**self.sources[0],'heading':'MEL — Overview'}]):
            self.assertIsNone(validate_overview('BCC','en',self.card,sources))
    def test_bangla_notice_is_not_claimed_as_a_live_ai_explanation(self):
        answer,_=validate_overview('BCC','bn',self.card,self.sources)
        self.assertIn('সাধারণ পরিচিতি',answer['notice'])

    def test_corrupt_reference_metadata_never_becomes_an_unhandled_answer(self):
        self.assertIsNone(validate_overview('BCC','en',self.card,[{**self.sources[0],'heading':''}]))
        self.assertIsNone(validate_overview('BCC','en',('Text','v1',[{}],{'doc':'hash'}),self.sources))

import unittest
from assistant.validation import validate_answer


class ValidationTests(unittest.TestCase):
    def test_unsupported_number_abstains(self):
        result = {'answer': 'Score is 99.4%', 'status': 'answered', 'facts_used': []}
        self.assertEqual(validate_answer(result, {'score': .72})['status'], 'unavailable')

    def test_missing_xai_cannot_be_invented(self):
        result = {'answer': 'The heatmap shows the lesion.', 'status': 'answered', 'facts_used': []}
        self.assertEqual(validate_answer(result, {'xai': None})['status'], 'unavailable')

    def test_supported_number_passes(self):
        result = {'answer': 'Model score: 0.72', 'status': 'answered', 'facts_used': ['score']}
        self.assertEqual(validate_answer(result, {'score': .72}), result)

    def test_list_numbers_are_structural_but_factual_numbers_still_checked(self):
        result={'answer':'1. Review available evidence.\n2. XAI is unavailable.','status':'answered','facts_used':[]}
        self.assertEqual(validate_answer(result,{'xai':None})['status'],'answered')
        result['answer']='1. Model score is 99.9%.'
        self.assertEqual(validate_answer(result,{'score':.72})['status'],'unavailable')

    def test_bengali_list_markers_do_not_create_false_numeric_claims(self):
        result={'answer':'১. সীমাবদ্ধতা দেখুন।\n২. XAI পাওয়া যায়নি।','status':'answered','facts_used':[]}
        self.assertEqual(validate_answer(result,{'xai':None})['status'],'answered')

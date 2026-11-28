import unittest
from assistant.generator import MockAssistantGenerator


class MockGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = MockAssistantGenerator()
        self.context = {'leading_class': 'MEL', 'scores': [{'label': 'MEL', 'score': .7234}],
                        'uncertainty': {'normalized_entropy': .3, 'top_two_margin': .2}, 'xai': None}

    def test_score_is_taken_from_context(self):
        result = self.generator.answer('What is the model score?', self.context)
        self.assertIn('0.7234', result['answer'])

    def test_missing_xai_abstains(self):
        self.assertEqual(self.generator.answer('Explain the heatmap', self.context)['status'], 'unavailable')

    def test_prescribing_is_out_of_scope(self):
        self.assertEqual(self.generator.answer('Prescribe a dose', self.context)['status'], 'out_of_scope')

    def test_unknown_questions_abstain(self):
        self.assertEqual(self.generator.answer('What is the weather?', self.context)['status'], 'unavailable')

import unittest
from assistant.case_context import InvalidCaseEvidence, build_case_context


def example():
    return {'analysis_id': 'id', 'model_version': 'v1', 'input_hash': 'a' * 64,
            'leading_class': 'MEL', 'scores': [{'label': 'MEL', 'score': .7}],
            'uncertainty': {}, 'ensemble': {}, 'metadata': {'age': 40, 'sex': 'male', 'site': 'trunk', 'patient_name': 'private'},
            'patient_name': 'private', 'input_policy': 'single', 'tta': True, 'limitations': []}


class CaseContextTests(unittest.TestCase):
    def test_excludes_identifiers_and_images(self):
        result = build_case_context(example())
        self.assertNotIn('patient_name', result)
        self.assertNotIn('patient_name', result['metadata'])

    def test_rejects_mismatched_explanation(self):
        with self.assertRaises(InvalidCaseEvidence):
            build_case_context(example(), {'status': 'ok', 'model_version': 'v1', 'input_hash': 'b' * 64})

    def test_preserves_explanation_scope_without_image(self):
        explanation = {'status': 'ok', 'model_version': 'v1', 'input_hash': 'a' * 64,
                       'method': 'integrated_gradients', 'score': 'fold_logit', 'fold': 0,
                       'tta': 'none', 'image_map': {'data': 'private'}}
        xai = build_case_context(example(), explanation)['xai']
        self.assertEqual(xai['score'], 'fold_logit')
        self.assertNotIn('image_map', xai)

    def test_preserves_new_model_calibration_and_decision_score_scope(self):
        snapshot=example()
        snapshot.update(calibration={'applied':False,'temperature':None},decision_scores={'MEL':.7},
                        decision_scores_basis='uncalibrated_probabilities',capabilities={'xai':[]})
        context=build_case_context(snapshot)
        self.assertEqual(context['calibration'],snapshot['calibration'])
        self.assertEqual(context['decision_scores_basis'],'uncalibrated_probabilities')
        self.assertEqual(context['capabilities']['xai'],[])
        context['calibration']['applied']=True
        self.assertFalse(snapshot['calibration']['applied'])

"""Provider-independent generation contract and deterministic local mock."""
from typing import Protocol


class AssistantGenerator(Protocol):
    def answer(self, question: str, context: dict, conversation=None) -> dict: ...


class MockAssistantGenerator:
    """Development-only case summaries; never claims clinical interpretation."""

    def answer(self, question: str, context: dict, conversation=None) -> dict:
        question_lower = question.casefold()
        if any(term in question_lower for term in ('prescribe', 'dosage', 'dose', 'medicine', 'biopsy')):
            return {'status': 'out_of_scope', 'answer': 'Treatment and procedural decisions require clinician judgment.', 'facts_used': []}
        if any(term in question_lower for term in ('calibration', 'calibrated', 'temperature')):
            calibration = context.get('calibration')
            if not calibration:
                return {'status': 'unavailable', 'answer': 'Calibration status is unavailable for this analysis.', 'facts_used': []}
            answer = (f"Temperature scaling applied: {calibration.get('temperature')}." if calibration.get('applied') else 'Temperature scaling is not applied.')
            return {'status': 'answered', 'answer': answer + ' ' + calibration.get('reason', ''), 'facts_used': ['calibration']}
        if 'limitation' in question_lower:
            return {'status': 'answered', 'answer': '\n'.join(context.get('limitations', [])) or 'No limitations were supplied.', 'facts_used': ['limitations']}
        if any(term in question_lower for term in ('ensemble', 'agreement')):
            ensemble = context['ensemble']
            return {'status': 'answered', 'answer': f"Members: {ensemble.get('member_count', 'unavailable')}; agreement: {ensemble.get('agreement') if ensemble.get('agreement') is not None else 'unavailable'}; TTA: {context.get('tta', 'unavailable')}.", 'facts_used': ['ensemble', 'tta']}
        if any(term in question_lower for term in ('xai', 'heatmap', 'region', 'why')):
            xai = context.get('xai')
            if not xai:
                return {'status': 'unavailable', 'answer': 'No matching explanation is available for this analysis.', 'facts_used': []}
            return {'status': 'answered', 'answer': f"Explanation method: {xai.get('method', 'unknown')}; output scope: {xai.get('score', 'unknown')}; fold: {xai.get('fold', 'unknown')}; TTA: {xai.get('tta', 'unknown')}. Attribution does not establish clinical correctness.", 'facts_used': ['xai']}
        if any(term in question_lower for term in ('uncertainty', 'entropy', 'margin')):
            uncertainty = context['uncertainty']
            if 'normalized_entropy' not in uncertainty or 'top_two_margin' not in uncertainty:
                return {'status': 'unavailable', 'answer': 'Uncertainty values are unavailable.', 'facts_used': []}
            return {'status': 'answered', 'answer': f"Normalized entropy: {uncertainty['normalized_entropy']}; top-two margin: {uncertainty['top_two_margin']}. These are model signals, not a diagnosis.", 'facts_used': ['uncertainty']}
        if any(term in question_lower for term in ('class', 'predict', 'score', 'result')):
            scores = context['scores']
            leading = next(item for item in scores if item['label'] == context['leading_class'])
            return {'status': 'answered', 'answer': f"Leading class: {leading['label']}; model score: {leading['score']}. This is not a confirmed diagnosis or calibrated clinical risk.", 'facts_used': ['leading_class', 'scores']}
        return {'status': 'unavailable', 'answer': 'This development assistant has no evidence to answer that question.', 'facts_used': []}

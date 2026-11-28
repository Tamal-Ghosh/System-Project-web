"""Build a minimal evidence bundle from a server-owned inference snapshot."""
from copy import deepcopy
import math


class InvalidCaseEvidence(ValueError):
    pass


def build_case_context(snapshot, explanation=None):
    required = ('analysis_id', 'model_version', 'input_hash', 'leading_class', 'scores',
                'uncertainty', 'ensemble', 'metadata', 'input_policy', 'tta', 'limitations')
    if any(key not in snapshot for key in required):
        raise InvalidCaseEvidence('Incomplete analysis snapshot')
    scores = snapshot['scores']
    try:
        labels = [item['label'] for item in scores]
        valid = bool(labels) and all(type(item['score']) in (int, float) and math.isfinite(item['score']) and 0 <= item['score'] <= 1 for item in scores)
    except (KeyError, TypeError):
        raise InvalidCaseEvidence('Invalid model scores') from None
    if not valid or len(set(labels)) != len(labels) or snapshot['leading_class'] not in labels:
        raise InvalidCaseEvidence('Invalid model scores or leading class')
    context = {key: deepcopy(snapshot[key]) for key in required}
    context['scores'] = [{'label': item['label'], 'score': item['score']} for item in scores]
    for key, allowed in (
        ('uncertainty', ('normalized_entropy', 'top_two_margin')),
        ('ensemble', ('member_count', 'member_scores', 'agreement')),
    ):
        value = context[key]
        if not isinstance(value, dict):
            raise InvalidCaseEvidence(f'Invalid {key}')
        context[key] = {name: value[name] for name in allowed if name in value}
    metadata = context['metadata']
    if not isinstance(metadata, dict):
        raise InvalidCaseEvidence('Invalid metadata')
    context['metadata'] = {key: metadata[key] for key in ('age', 'sex', 'site') if key in metadata}
    for field in ('calibration', 'decision_scores', 'decision_scores_basis', 'positive_categories', 'capabilities', 'unavailable', 'persistence'):
        if field in snapshot:
            context[field] = deepcopy(snapshot[field])
    context['xai'] = None
    if explanation is not None:
        if (explanation.get('status') != 'ok' or explanation.get('input_hash') != snapshot['input_hash']
                or explanation.get('model_version') != snapshot['model_version']):
            raise InvalidCaseEvidence('Explanation does not match the analysis')
        keys = ('method', 'score', 'target_class', 'fold', 'fold_selection', 'tta',
                'baseline', 'n_steps', 'convergence_delta', 'metadata_attribution', 'limitations')
        context['xai'] = {key: deepcopy(explanation[key]) for key in keys if key in explanation}
    from assistant.model_reference import add_model_reference
    return add_model_reference(context)

"""Version-bound runtime facts derived from the verified deployment bundle."""
import json
from pathlib import Path

MODEL_VERSION='e55-multiscale-c769f025f83f3f0f'


def add_model_reference(context):
    if context.get('model_version') != MODEL_VERSION: return context
    try:
        report=json.loads((Path(__file__).resolve().parents[1]/'dermfm'/'calibration_evidence.json').read_text())
    except (OSError,ValueError):return context
    if report.get('model_version') != MODEL_VERSION:return context
    return {**context,'model_characteristics':{'class_count':11,'fold_count':5,'tta_view_count':3},
            'model_evaluation':{'scope':report['scope'],'sample_count':report['sample_count'],
                                'metrics':report['metrics'],'live_scaling_evidence':False}}

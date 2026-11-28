"""Adapter for the supplied, checksum-verified E55 paired-image deployment bundle."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import uuid
from .loader import CLASSES, SITES
from .metrics import summarize
from .calibration import load_temperature_calibration
from .conformal import evaluate_conformal_prediction


class E55Service:
    def __init__(self, root):
        root = Path(root).resolve()
        manifest = json.loads((root/'manifest.json').read_text())
        if manifest.get('experiment') != 'E55_multiscale_regions_Kaggle' or manifest.get('variant') != 'multiscale_regions':
            raise ValueError('Expected the E55 multiscale deployment bundle')
        if manifest.get('sha256') != 'c769f025f83f3f0fb74ebe2580d3f45b250e5a98a0c5e3385b57b9b7d13669ec':
            raise ValueError('Unexpected E55 checkpoint provenance')
        # The supplied runtime verifies checkpoint size/hash and embedded source hashes.
        sys.path.insert(0, str(root))
        try:
            spec = importlib.util.spec_from_file_location('e55_bundle_inference', root/'web_inference.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.predictor = module.Predictor(root, device=os.getenv('DERMFM_DEVICE', 'cpu'))
        finally:
            sys.path.remove(str(root))
        if tuple(self.predictor.classes) != CLASSES or tuple(self.predictor.vocab) != SITES:
            raise ValueError('E55 classes or metadata order mismatch')
        self.version = 'e55-multiscale-' + manifest['sha256'][:16]
        self.requires_clinical = True
        calibration_path = os.getenv('DERMFM_CALIBRATION') or None
        self.calibration = load_temperature_calibration(calibration_path, self.version, 'single_dermoscopic_duplicated')

    def predict(self, image, age, sex, site='unknown', clinical=None):
        duplicated = clinical is None
        if duplicated:
            clinical = image
        started = time.perf_counter()
        raw = self.predictor.predict(image, clinical, age, sex, site)
        raw_scores = [float(raw['raw_probabilities'][label]) for label in CLASSES]
        calibration = getattr(self, 'calibration', None)
        if calibration is not None and calibration.input_policy != ('single_dermoscopic_duplicated' if duplicated else 'paired_dermoscopic_clinical'):
            raise ValueError('Calibrated input policy does not match this request')
        scores = calibration.apply(raw_scores).tolist() if calibration else raw_scores
        entropy, margin = summarize(scores)
        digest = hashlib.sha256()
        for value in (image, clinical):
            tensor = self.predictor.transform(value.convert('RGB'))
            digest.update(tensor.contiguous().numpy().tobytes())
        digest.update(json.dumps({'age':age,'sex':sex,'site':site}, sort_keys=True).encode())
        scores_list = [dict(label=label,score=value) for label,value in zip(CLASSES,scores)]
        return dict(analysis_id=str(uuid.uuid4()), model_version=self.version,
            classes=list(CLASSES), leading_class=CLASSES[max(range(len(scores)), key=scores.__getitem__)],
            scores=scores_list,
            conformal_prediction=evaluate_conformal_prediction(scores_list, coverage=0.95),
            decision_scores=raw['decision_scores'], positive_categories=raw['positive_categories'],
            uncertainty=dict(normalized_entropy=entropy, top_two_margin=margin),
            calibration=(calibration.public_summary() if calibration else dict(applied=False, temperature=None, reason='No validated temperature artifact is configured for this exact model and input policy.')),
            uncalibrated_scores=([dict(label=label, score=float(value)) for label,value in zip(CLASSES,raw_scores)] if calibration else None),
            decision_scores_basis='uncalibrated_probabilities',
            ensemble=dict(member_count=5,agreement=None), metadata=dict(age=age,sex=sex,site=site),
            input_policy='single_dermoscopic_duplicated' if duplicated else 'paired_dermoscopic_clinical', tta=True, input_hash=digest.hexdigest(),
            elapsed_ms=round((time.perf_counter()-started)*1000), persistence='not_saved',
            capabilities=dict(xai=[],grad_cam='not_implemented',shap='not_implemented',attention='not_validated'),
            unavailable=['ensemble_agreement','xai','ood','image_quality','clinical_next_step'],
            limitations=(['Single-image duplication is an unvalidated adaptation of paired-image training.'] if duplicated else []) + ['Research model; clinical validity has not been established.',
                ('Temperature scaling does not establish clinical validity.' if calibration else 'Raw class scores are not calibrated clinical disease risks.'),
                'Threshold-mapped decision scores are not probabilities.',
                'Explanation support is not yet available for this model configuration.'])

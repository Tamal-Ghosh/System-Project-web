import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import torch
from PIL import Image
from fastapi.testclient import TestClient

from dermfm.calibration import get_calibration_evidence, load_temperature_calibration
from dermfm.e55_service import E55Service
from dermfm.loader import CLASSES
from inference_app import create_app
from fit_temperature import main as fit_main

VERSION = 'e55-multiscale-c769f025f83f3f0f'
POLICY = 'single_dermoscopic_duplicated'


def artifact():
    return dict(schema_version=2, artifact_id='synthetic-test-only', model_version=VERSION,
                aggregation='mean_member_probabilities', input_policy=POLICY, classes=list(CLASSES),
                tta='mean_logits_original_hflip_vflip', training_disjoint=True, patient_disjoint=True,
                temperature=2.0, fit_samples=220, evaluation_samples=220,
                evaluation_metrics_before=dict(nll=1.0, top_label_ece=.2, brier_score=.4, accuracy=.8),
                evaluation_metrics_after=dict(nll=.9, top_label_ece=.1, brier_score=.35, accuracy=.8))


class CalibrationTests(unittest.TestCase):
    def load(self, payload):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'temperature.json'
            path.write_text(json.dumps(payload))
            return load_temperature_calibration(path, VERSION, POLICY)

    def test_new_model_evidence_matches_and_is_copy_safe(self):
        report = get_calibration_evidence(None, VERSION)
        self.assertAlmostEqual(report['metrics']['top_label_ece'], .07143590649916927)
        self.assertAlmostEqual(report['metrics']['brier_score'], .3194219423254189)
        self.assertEqual(sum(row['count'] for row in report['reliability_bins']),5240)
        self.assertFalse(report['temperature_scaling']['applied'])
        report['metrics']['top_label_ece']=0
        self.assertGreater(get_calibration_evidence(None,VERSION)['metrics']['top_label_ece'],0)
        with self.assertRaises(ValueError):
            get_calibration_evidence(None, 'old-model')

    def test_artifact_rejects_mismatched_or_invalid_pipeline(self):
        changes = [('model_version','old-model'),('input_policy','paired_dermoscopic_clinical'),
                   ('classes',list(reversed(CLASSES))),('temperature',float('nan')),
                   ('training_disjoint',False),('patient_disjoint',False),('tta','none')]
        for key,value in changes:
            with self.subTest(key=key):
                payload=artifact(); payload[key]=value
                with self.assertRaises(ValueError): self.load(payload)
        payload=artifact(); del payload['temperature']; payload['extra']=True
        with self.assertRaises(ValueError): self.load(payload)
        payload=artifact(); payload['evaluation_metrics_after']['nll']=float('nan')
        with self.assertRaises(ValueError): self.load(payload)

    def test_scaling_normalizes_softens_and_preserves_ranking(self):
        calibration=self.load(artifact())
        raw=np.array([.9]+[.01]*10)
        scaled=calibration.apply(raw)
        self.assertAlmostEqual(scaled.sum(),1)
        self.assertLess(scaled[0],raw[0])
        self.assertEqual(scaled.argmax(),raw.argmax())
        self.assertTrue(np.isfinite(calibration.apply([1]+[0]*10)).all())

    def test_live_service_scales_probabilities_not_decision_scores(self):
        service=E55Service.__new__(E55Service); service.version=VERSION
        service.calibration=self.load(artifact()); service.predictor=Mock()
        raw=[.9]+[.01]*10; decisions={c:.4 for c in CLASSES}
        service.predictor.predict.return_value=dict(raw_probabilities=dict(zip(CLASSES,raw)),
            top_class=CLASSES[0],decision_scores=decisions,positive_categories=[])
        service.predictor.transform.return_value=torch.zeros(3,2,2)
        image=Image.new('RGB',(2,2))
        result=service.predict(image,40,'male')
        self.assertTrue(result['calibration']['applied'])
        self.assertLess(result['scores'][0]['score'],.9)
        self.assertEqual(result['uncalibrated_scores'][0]['score'],.9)
        self.assertEqual(result['decision_scores'],decisions)
        with self.assertRaises(ValueError): service.predict(image,40,'male',clinical=image)

    def test_api_reports_loaded_model_and_fails_closed(self):
        service=Mock(); service.version=VERSION; service.calibration=None
        with TestClient(create_app(lambda:service)) as client:
            response=client.get('/api/v1/model/calibration')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['model_version'],VERSION)
            service.version='old-model'
            self.assertEqual(client.get('/api/v1/model/calibration').status_code,503)

    def test_fitting_rejects_training_patient_leakage(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); labels=np.tile(np.arange(11),2); probs=np.full((22,11),1/11)
            for name in ('fit','eval'):
                np.savez(root/f'{name}.npz',probabilities=probs,labels=labels,
                    ids=np.array([f'{name}-{i}' for i in range(22)]),
                    patient_ids=np.array([f'{name}-patient-{i}' for i in range(22)]))
            np.savez(root/'training.npz',ids=['train-1'],patient_ids=['fit-patient-0'])
            argv=['fit_temperature','--fit',str(root/'fit.npz'),'--evaluate',str(root/'eval.npz'),
                '--model-version',VERSION,'--output',str(root/'result.json'),
                '--training-index',str(root/'training.npz'),'--input-policy',POLICY]
            with patch('sys.argv',argv), self.assertRaisesRegex(ValueError,'training'):
                fit_main()
            self.assertFalse((root/'result.json').exists())

    def test_fitter_writes_model_bound_artifact_on_independent_synthetic_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); labels=np.tile(np.arange(11),20)
            predictions=labels.copy(); predictions[::5]=(predictions[::5]+1)%11
            probabilities=np.full((len(labels),11),.001)
            probabilities[np.arange(len(labels)),predictions]=.99
            for name in ('fit','eval'):
                np.savez(root/f'{name}.npz',probabilities=probabilities,labels=labels,
                    ids=np.array([f'{name}-{i}' for i in range(len(labels))]),
                    patient_ids=np.array([f'{name}-patient-{i}' for i in range(len(labels))]),
                    model_version=VERSION,input_policy=POLICY,classes=np.array(CLASSES),
                    tta='mean_logits_original_hflip_vflip')
            np.savez(root/'training.npz',ids=['training-image'],patient_ids=['training-patient'])
            argv=['fit_temperature','--fit',str(root/'fit.npz'),'--evaluate',str(root/'eval.npz'),
                '--model-version',VERSION,'--output',str(root/'temperature.json'),
                '--training-index',str(root/'training.npz'),'--input-policy',POLICY]
            with patch('sys.argv',argv), patch('builtins.print'): fit_main()
            result=load_temperature_calibration(root/'temperature.json',VERSION,POLICY)
            self.assertGreater(result.temperature,1)
            self.assertLess(result.evaluation_metrics_after['nll'],result.evaluation_metrics_before['nll'])


if __name__=='__main__': unittest.main()

"""Model-bound evidence and optional live ensemble temperature calibration."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

import numpy as np

@dataclass(frozen=True)
class TemperatureCalibration:
    artifact_id: str
    model_version: str
    temperature: float
    fit_samples: int
    evaluation_samples: int
    evaluation_metrics_before: dict
    evaluation_metrics_after: dict
    input_policy: str | None = None

    def apply(self, probabilities):
        """Apply scalar temperature to an already averaged probability vector."""
        values = np.asarray(probabilities, dtype=np.float64)
        if values.ndim != 1 or len(values) != 11 or not np.isfinite(values).all() or (values < 0).any() or not np.isclose(values.sum(), 1, atol=1e-5):
            raise ValueError("Expected eleven finite positive ensemble probabilities")
        log_values = np.log(np.clip(values, 1e-15, 1)) / self.temperature
        log_values -= log_values.max()
        calibrated = np.exp(log_values)
        return calibrated / calibrated.sum()

    def public_summary(self):
        return {
            "applied": True,
            "artifact_id": self.artifact_id,
            "temperature": self.temperature,
            "fit_samples": self.fit_samples,
            "evaluation_samples": self.evaluation_samples,
            "evaluation_metrics_before": dict(self.evaluation_metrics_before),
            "evaluation_metrics_after": dict(self.evaluation_metrics_after),
            "input_policy": self.input_policy,
            "reason": "Validated scalar temperature applied after five-model probability averaging.",
        }


def load_temperature_calibration(path, expected_model_version, expected_input_policy=None):
    """Load a fail-closed artifact tied to the exact deployed model version."""
    if path is None:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "schema_version", "artifact_id", "model_version", "aggregation", "temperature",
        "fit_samples", "evaluation_samples", "evaluation_metrics_before", "evaluation_metrics_after",
    }
    if not required.issubset(payload):
        raise ValueError("Calibration artifact is incomplete")
    if payload["schema_version"] not in (1, 2):
        raise ValueError("Unsupported calibration artifact schema")
    if payload["model_version"] != expected_model_version:
        raise ValueError("Calibration artifact does not match the loaded model")
    if payload["aggregation"] != "mean_member_probabilities":
        raise ValueError("Calibration artifact uses an unsupported ensemble aggregation")
    if expected_input_policy is not None:
        from .loader import CLASSES
        if (payload['schema_version'] != 2 or payload.get('input_policy') != expected_input_policy
                or payload.get('classes') != list(CLASSES) or payload.get('tta') != 'mean_logits_original_hflip_vflip'
                or payload.get('training_disjoint') is not True or payload.get('patient_disjoint') is not True):
            raise ValueError('Calibration artifact does not match the input policy, class order, TTA or independent data requirements')
    temperature = float(payload["temperature"])
    if not math.isfinite(temperature) or not 0.05 <= temperature <= 10:
        raise ValueError("Calibration temperature is outside the accepted range")
    if int(payload["fit_samples"]) < 1 or int(payload["evaluation_samples"]) < 1:
        raise ValueError("Calibration artifact requires independent fit and evaluation samples")
    before = payload["evaluation_metrics_before"]
    after = payload["evaluation_metrics_after"]
    for values in (before, after):
        for key in ('nll', 'top_label_ece', 'brier_score', 'accuracy'):
            value = float(values[key])
            if not math.isfinite(value) or value < 0 or (key in ('top_label_ece', 'accuracy') and value > 1):
                raise ValueError('Invalid calibration evaluation metrics')
    if float(after["nll"]) >= float(before["nll"]) or float(after["top_label_ece"]) > float(before["top_label_ece"]):
        raise ValueError("Independent evaluation does not support applying this temperature")
    return TemperatureCalibration(
        artifact_id=str(payload["artifact_id"]),
        model_version=str(payload["model_version"]),
        temperature=temperature,
        fit_samples=int(payload["fit_samples"]),
        evaluation_samples=int(payload["evaluation_samples"]),
        evaluation_metrics_before=dict(payload["evaluation_metrics_before"]),
        evaluation_metrics_after=dict(payload["evaluation_metrics_after"]),
        input_policy=payload.get('input_policy'),
    )


def get_calibration_evidence(live_calibration=None, model_version=None):
    """Return a copy-safe JSON-compatible calibration report."""
    report = json.loads(Path(__file__).with_name('calibration_evidence.json').read_text())
    if model_version != report['model_version']:
        raise ValueError('Calibration evidence does not match the loaded model')
    if live_calibration is not None:
        report["temperature_scaling"] = live_calibration.public_summary()
        report["limitations"] = [item for item in report["limitations"] if not item.startswith('Live probabilities remain')] + ["The displayed reliability diagram remains OOF evidence; live scaling has a separate independent evaluation."]
    return report

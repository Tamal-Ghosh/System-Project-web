"""Published evidence and optional live temperature calibration for E38."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

import numpy as np

E38_OOF_CALIBRATION = {
    "status": "measured_oof",
    "artifact_id": "e38-control-oof-report",
    "model_family": "E38 DermFM control",
    "scope": "Five-fold out-of-fold validation predictions",
    "sample_count": 5240,
    "class_count": 11,
    "metrics": {
        "top_label_ece": 0.027222330996212133,
        "brier_score": 0.3047378196952517,
    },
    "reliability_bins": [
        {"lower": 0.2, "upper": 0.3, "count": 36, "confidence": 0.26858769729733467, "accuracy": 0.25},
        {"lower": 0.3, "upper": 0.4, "count": 152, "confidence": 0.35411622198788745, "accuracy": 0.375},
        {"lower": 0.4, "upper": 0.5, "count": 296, "confidence": 0.4567873408464161, "accuracy": 0.3885135135135135},
        {"lower": 0.5, "upper": 0.6, "count": 404, "confidence": 0.5507916790424007, "accuracy": 0.5668316831683168},
        {"lower": 0.6, "upper": 0.7, "count": 409, "confidence": 0.6518458447129919, "accuracy": 0.6112469437652812},
        {"lower": 0.7, "upper": 0.8, "count": 513, "confidence": 0.7506414168527019, "accuracy": 0.7115009746588694},
        {"lower": 0.8, "upper": 0.9, "count": 863, "confidence": 0.8550942502182024, "accuracy": 0.8064889918887601},
        {"lower": 0.9, "upper": 1.0, "count": 2567, "confidence": 0.9585048590692788, "accuracy": 0.9454616283599533},
    ],
    "temperature_scaling": {
        "applied": False,
        "temperature": None,
        "reason": (
            "No held-out temperature was fitted for the deployed five-model ensemble. "
            "Case scores therefore remain uncalibrated model outputs."
        ),
    },
    "limitations": [
        "This is model-level evidence and does not estimate correctness for one image.",
        "The measurements use out-of-fold validation predictions, not the deployed five-model ensemble output.",
        "Temperature scaling is not applied to live case scores.",
    ],
}


@dataclass(frozen=True)
class TemperatureCalibration:
    artifact_id: str
    model_version: str
    temperature: float
    fit_samples: int
    evaluation_samples: int
    evaluation_metrics_before: dict
    evaluation_metrics_after: dict

    def apply(self, probabilities):
        """Apply scalar temperature to an already averaged probability vector."""
        values = np.asarray(probabilities, dtype=np.float64)
        if values.ndim != 1 or len(values) != 11 or not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError("Expected eleven finite positive ensemble probabilities")
        log_values = np.log(values) / self.temperature
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
            "reason": "Validated scalar temperature applied after five-model probability averaging.",
        }


def load_temperature_calibration(path, expected_model_version):
    """Load a fail-closed artifact tied to the exact deployed model version."""
    if path is None:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "schema_version", "artifact_id", "model_version", "aggregation", "temperature",
        "fit_samples", "evaluation_samples", "evaluation_metrics_before", "evaluation_metrics_after",
    }
    if set(payload) < required:
        raise ValueError("Calibration artifact is incomplete")
    if payload["schema_version"] != 1:
        raise ValueError("Unsupported calibration artifact schema")
    if payload["model_version"] != expected_model_version:
        raise ValueError("Calibration artifact does not match the loaded model")
    if payload["aggregation"] != "mean_member_probabilities":
        raise ValueError("Calibration artifact uses an unsupported ensemble aggregation")
    temperature = float(payload["temperature"])
    if not math.isfinite(temperature) or not 0.05 <= temperature <= 10:
        raise ValueError("Calibration temperature is outside the accepted range")
    if int(payload["fit_samples"]) < 1 or int(payload["evaluation_samples"]) < 1:
        raise ValueError("Calibration artifact requires independent fit and evaluation samples")
    before = payload["evaluation_metrics_before"]
    after = payload["evaluation_metrics_after"]
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
    )


def get_calibration_evidence(live_calibration=None):
    """Return a copy-safe JSON-compatible calibration report."""
    report = {
        **E38_OOF_CALIBRATION,
        "metrics": dict(E38_OOF_CALIBRATION["metrics"]),
        "reliability_bins": [dict(row) for row in E38_OOF_CALIBRATION["reliability_bins"]],
        "temperature_scaling": dict(E38_OOF_CALIBRATION["temperature_scaling"]),
        "limitations": list(E38_OOF_CALIBRATION["limitations"]),
    }
    if live_calibration is not None:
        report["temperature_scaling"] = live_calibration.public_summary()
        report["limitations"] = [
            item for item in report["limitations"]
            if item != "Temperature scaling is not applied to live case scores."
        ] + ["Live temperature metrics come from an independent ensemble calibration evaluation artifact."]
    return report

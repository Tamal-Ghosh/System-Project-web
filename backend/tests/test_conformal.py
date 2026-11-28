"""Unit tests for the Conformal Prediction module."""
import pytest
from dermfm.conformal import (
    evaluate_conformal_prediction,
    get_quantile_for_coverage,
    CALIBRATED_QUANTILES,
    MALIGNANT_CLASSES,
)

def test_quantile_lookup():
    assert get_quantile_for_coverage(0.95) == CALIBRATED_QUANTILES[0.95]
    assert get_quantile_for_coverage(0.90) == CALIBRATED_QUANTILES[0.90]
    # Interpolation works
    q_92 = get_quantile_for_coverage(0.92)
    assert CALIBRATED_QUANTILES[0.90] <= q_92 <= CALIBRATED_QUANTILES[0.95]

def test_singleton_conformal_set():
    # If a class has dominant probability > 0.95 quantile, set_size must be 1
    scores = [
        {"label": "NV", "score": 0.96},
        {"label": "MEL", "score": 0.02},
        {"label": "BKL", "score": 0.01},
        {"label": "BCC", "score": 0.01},
    ]
    res = evaluate_conformal_prediction(scores, coverage=0.95)
    assert res["set_size"] == 1
    assert res["certainty_tier"] == "singleton"
    assert res["prediction_set"][0]["label"] == "NV"
    assert not res["contains_malignancy"]
    assert len(res["excluded_classes"]) == 3

def test_differential_conformal_set_with_malignancy():
    # Top class is Nevus (60%), second is Melanoma (35%), third is BKL (5%)
    scores = [
        {"label": "NV", "score": 0.60},
        {"label": "MEL", "score": 0.35},
        {"label": "BKL", "score": 0.05},
    ]
    res = evaluate_conformal_prediction(scores, coverage=0.95)
    # Threshold at 95% is 0.925. 0.60 < 0.925, 0.60 + 0.35 = 0.95 >= 0.925 -> 2 classes
    assert res["set_size"] == 2
    assert res["certainty_tier"] == "differential"
    labels = [x["label"] for x in res["prediction_set"]]
    assert labels == ["NV", "MEL"]
    assert res["contains_malignancy"] is True
    assert "MEL" in res["malignant_classes"]
    assert len(res["excluded_classes"]) == 1
    assert res["excluded_classes"][0]["label"] == "BKL"

def test_broad_conformal_set():
    # Diffuse distribution over 5 classes
    scores = [
        {"label": "NV", "score": 0.25},
        {"label": "BKL", "score": 0.22},
        {"label": "DF", "score": 0.20},
        {"label": "BEN_OTH", "score": 0.18},
        {"label": "INF", "score": 0.15},
    ]
    res = evaluate_conformal_prediction(scores, coverage=0.95)
    assert res["set_size"] >= 4
    assert res["certainty_tier"] == "broad"
    assert "Broad Differential" in res["tier_label"]

def test_coverage_adjustability():
    # Lower coverage (e.g. 80%) should yield smaller or equal set size compared to 99%
    scores = [
        {"label": "NV", "score": 0.76},
        {"label": "MEL", "score": 0.15},
        {"label": "BCC", "score": 0.09},
    ]
    res_80 = evaluate_conformal_prediction(scores, coverage=0.80)
    res_99 = evaluate_conformal_prediction(scores, coverage=0.99)
    assert res_80["set_size"] <= res_99["set_size"]

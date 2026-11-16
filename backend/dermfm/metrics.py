"""Descriptive prediction uncertainty, not clinical risk calibration."""
import numpy as np

def summarize(probabilities):
    p = np.asarray(probabilities, dtype=np.float64)
    if p.shape != (11,) or not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1., atol=1e-5):
        raise ValueError("Model produced invalid class probabilities")
    ordered = np.sort(p)
    entropy = float(-(p*np.log(np.maximum(p, 1e-15))).sum()/np.log(len(p)))
    return entropy, float(ordered[-1]-ordered[-2])

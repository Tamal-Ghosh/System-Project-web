"""Fit one scalar temperature from independent ensemble probability exports.

Each NPZ must contain probabilities [N,11], labels [N], and unique ids [N].
The fit and evaluation IDs must be disjoint. This tool never reads model weights.
"""
from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

import numpy as np


def load_split(path):
    with np.load(path, allow_pickle=False) as values:
        required = {"probabilities", "labels", "ids"}
        if not required.issubset(values.files):
            raise ValueError(f"{path} must contain probabilities, labels, and ids")
        probabilities = np.asarray(values["probabilities"], dtype=np.float64)
        labels = np.asarray(values["labels"], dtype=np.int64)
        ids = np.asarray(values["ids"]).astype(str)
    if probabilities.ndim != 2 or probabilities.shape[1] != 11:
        raise ValueError(f"{path}: probabilities must have shape [N,11]")
    if labels.shape != (len(probabilities),) or ids.shape != (len(probabilities),):
        raise ValueError(f"{path}: labels and ids must align with probabilities")
    if len(set(ids.tolist())) != len(ids):
        raise ValueError(f"{path}: ids must be unique")
    if not np.isfinite(probabilities).all() or (probabilities <= 0).any():
        raise ValueError(f"{path}: probabilities must be finite and positive")
    if not np.allclose(probabilities.sum(1), 1, atol=1e-5):
        raise ValueError(f"{path}: probability rows must sum to one")
    if (labels < 0).any() or (labels >= 11).any():
        raise ValueError(f"{path}: labels must be integers from 0 to 10")
    return probabilities, labels, ids


def scale(probabilities, temperature):
    logits = np.log(np.clip(probabilities, 1e-15, 1)) / temperature
    logits -= logits.max(1, keepdims=True)
    values = np.exp(logits)
    return values / values.sum(1, keepdims=True)


def nll(probabilities, labels):
    return float(-np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-15, 1)).mean())


def metrics(probabilities, labels):
    predictions = probabilities.argmax(1)
    confidence = probabilities.max(1)
    correct = predictions == labels
    ece = 0.0
    for lower in np.linspace(0, .9, 10):
        selected = (confidence >= lower) & (confidence < lower + .1 if lower < .9 else confidence <= 1)
        if selected.any():
            ece += selected.mean() * abs(float(confidence[selected].mean()) - float(correct[selected].mean()))
    truth = np.eye(11, dtype=np.float64)[labels]
    return {
        "nll": nll(probabilities, labels),
        "top_label_ece": float(ece),
        "brier_score": float(np.square(probabilities - truth).sum(1).mean()),
        "accuracy": float(correct.mean()),
    }


def fit_temperature(probabilities, labels):
    left, right = np.log(.05), np.log(10.0)
    ratio = (np.sqrt(5) - 1) / 2
    first = right - ratio * (right - left)
    second = left + ratio * (right - left)
    for _ in range(80):
        if nll(scale(probabilities, np.exp(first)), labels) < nll(scale(probabilities, np.exp(second)), labels):
            right, second = second, first
            first = right - ratio * (right - left)
        else:
            left, first = first, second
            second = left + ratio * (right - left)
    return float(np.exp((left + right) / 2))


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = ArgumentParser()
    parser.add_argument("--fit", required=True, type=Path)
    parser.add_argument("--evaluate", required=True, type=Path)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    fit_probabilities, fit_labels, fit_ids = load_split(args.fit)
    eval_probabilities, eval_labels, eval_ids = load_split(args.evaluate)
    overlap = set(fit_ids.tolist()) & set(eval_ids.tolist())
    if overlap:
        raise ValueError(f"Fit/evaluation leakage: {len(overlap)} overlapping IDs")

    temperature = fit_temperature(fit_probabilities, fit_labels)
    before = metrics(eval_probabilities, eval_labels)
    after = metrics(scale(eval_probabilities, temperature), eval_labels)
    if after["nll"] >= before["nll"] or after["top_label_ece"] > before["top_label_ece"]:
        raise ValueError("Independent evaluation did not improve both NLL and top-label ECE; artifact not written")

    payload = {
        "schema_version": 1,
        "artifact_id": f"temperature-{uuid.uuid4().hex[:12]}",
        "model_version": args.model_version,
        "aggregation": "mean_member_probabilities",
        "temperature": temperature,
        "fit_samples": len(fit_labels),
        "evaluation_samples": len(eval_labels),
        "evaluation_metrics_before": before,
        "evaluation_metrics_after": after,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fit_source_sha256": file_sha256(args.fit),
        "evaluation_source_sha256": file_sha256(args.evaluate),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "temperature": temperature, "before": before, "after": after}, indent=2))


if __name__ == "__main__":
    main()

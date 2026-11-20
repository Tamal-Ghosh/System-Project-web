# Calibration branch

The completed model-integration branch is merged into this working tree without
a merge commit. Its new DermFM runtime and crop/report features are preserved.

## Measured evidence

The small `backend/dermfm/calibration_evidence.json` report comes from the supplied
model archive's `dermfm_calibration.csv` and `reports/calibration_metrics.json`.
Source SHA256 values are recorded in the report. It contains 5,240 OOF paired-image
predictions, 11 classes, ECE 0.07143590649916927 and multiclass Brier
0.3194219423254189. The reliability diagram is model-level evidence.

No original model report is served for the new model. The evidence endpoint checks
the loaded model version and returns 503 if unavailable or mismatched.

## Live temperature scaling

Scaling is implemented after the supplied runtime's five-fold mean probabilities.
The model version, class order, input policy and original/horizontal/vertical TTA
must match the artifact. Per-case entropy and margin use the returned calibrated
probabilities. Raw scores remain available separately. Threshold-mapped decision
scores remain based on raw probabilities and are labelled separately.

No live artifact has been fitted or enabled. OOF predictions are produced by one
held-out fold model per example and cannot calibrate the full five-model ensemble
on those same training images. The 479 ensemble test predictions in the archive
have no labels. Paired-image OOF evidence also does not validate the website's
single-image duplication policy.

When independent labelled images are available, generate raw probabilities with
this exact model and pipeline, then separate fit and evaluation sets by patient.
Each NPZ needs `probabilities` [N,11], integer `labels` [N], unique `ids` [N],
`patient_ids` [N], scalar `model_version`, scalar `input_policy`, `classes` [11],
and scalar `tta` (`mean_logits_original_hflip_vflip`). Both sets must cover all
classes. The training index NPZ needs aligned `ids` and `patient_ids` covering the
entire model training set. Do not substitute an empty or partial training index.

```sh
python backend/fit_temperature.py --fit fit.npz --evaluate evaluation.npz --training-index training.npz --model-version e55-multiscale-c769f025f83f3f0f --input-policy single_dermoscopic_duplicated --output temperature.json
```

The fitter rejects training-image/patient overlap, shared fit/evaluation patients,
pipeline mismatch, invalid data and temperatures that fail independent NLL/ECE
checks. Export identity and training-index completeness still require a trustworthy
data preparation process; metadata alone cannot prove dataset independence.

## Isolated Docker test stack

```sh
docker compose -f compose.yaml -f compose.calibration.yaml -f compose.build.yaml build
docker compose -f compose.yaml -f compose.calibration.yaml up -d --wait
```

Open http://localhost:5182/#/analysis?module=calibration. The model-only stack at
5181 and its published image tags are unaffected. No registry publish is done.

To enable a future validated artifact, set `CALIBRATION_ARTIFACT` to its absolute
host path and append `-f compose.calibration-artifact.yaml` to the up command.
That file mounts only the small JSON read-only. A wrong artifact prevents model
startup instead of silently applying the wrong calibration. Normal startup needs
no extra artifact, dataset, package or weight download.

## Verification

All 30 backend tests, including independent synthetic temperature fitting,
training/patient leakage rejection, pipeline mismatch rejection and live response
behavior, passed in the final calibration image. Both packaging tests and the
production frontend build passed. OOF ECE and Brier were independently recomputed
from the archive's raw probabilities and match the report exactly. Both services
are healthy. The proxied evidence endpoint returns the new model's report; a real
five-fold synthetic-image request completed in 35.504 seconds and correctly
reported live calibration as not applied. No synthetic artifact was deployed.
No new commit, Git push or registry push was made for this branch.

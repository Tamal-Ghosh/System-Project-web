# E38 explanations

## Methods and interpretation

The XAI panel requests Integrated Gradients (IG) for one class logit from one fold with that fold's adapter loaded. It uses the exact model transform and the submitted image region, repeats that tensor into both visual branches, and skips TTA. Captum is used when installed; a batched trapezoidal IG implementation is the fallback for local environments that lack Captum. Both paths use float32 inputs and frozen weights. The default baseline is a heavily blurred copy; the optional zero baseline is a black source image normalized by the configured transform. The display is the absolute channel-summed map, smoothed and clipped for legibility. The endpoint also returns signed channel-summed values and a convergence delta.

Metadata uses exact Shapley values over three grouped features: age, both sex indicators together, and all seven site indicators together. It is a sensitivity analysis, not a causal explanation. Age's baseline is 0.5 because a training median was not found in the deployed recipe; sex and site baselines are all-zero indicators.

All scores refer to the raw fold logit (`score: fold_logit`), not a probability. The response declares `tta: none`. Explanations describe model behavior and do not establish clinical correctness.

## Request

The client must resend the same image/crop and metadata as the analysis. Multipart example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/explanations `
  -F "image=@lesion.png" -F "age=52" -F "sex=female" -F "site=trunk" `
  -F "method=integrated_gradients" -F "target_class=MEL" -F "fold=0" `
  -F "baseline=blur" -F "n_steps=20" -F "include_metadata=true"
```

The API returns an `input_hash`, also included in `/api/v1/analyses`, derived from the processed image tensor and metadata. The UI checks this before rendering the map. Expected runtime failures use `status: unavailable` and a short reason; malformed inputs return 4xx. Only one explanation request is admitted at a time. The live implementation defaults to fold 0 if no fold is supplied and includes `fold_selection: fold_0_fallback`; selecting the closest fold to the ensemble mean was skipped to avoid another slow five-fold prediction. The UI submits fold 0 explicitly by default. `DERMFM_XAI_TIMEOUT_SECONDS` defaults to 300 seconds and returns `reason: timeout` when exceeded.

## Cost and validation

The deployed weights, source package and configured model environment are external to this repository checkout. Therefore real-model gradient checks, IG timings at 10/20/50 steps, peak memory, Shapley timing and the full evaluation were not measured here. Run `python backend/scripts/xai_gradient_check.py IMAGE` and the evaluation command below in the configured deployment environment before relying on those results. The API defaults to 20 steps and accepts 10–50; no silent step reduction is applied.

Faithfulness evaluation (requires a labeled or unlabeled image directory and configured model assets):

```powershell
python backend/scripts/xai_eval.py --images PATH_TO_IMAGES --labels PATH_TO_LABELS.csv --out reports/xai_eval/ --seed 42
```

Labels are optional. The output contains `results.csv`, `summary.json`, deletion/insertion plots against five-seed random baselines, and an example overlay grid. The script is computationally expensive; it performs many forwards per image. No metrics are claimed until a real run has completed. Review the per-image CSV and summary before interpreting faithfulness.

## Limits

- The project input is one image duplicated into two image branches. Training used a paired-view setup; this adaptation is not established as clinically equivalent.
- The external pinned source files needed to verify the visual wrapper's exact pooling and attention implementation are not shipped in this checkout. No attention explanation is offered.
- IG localization and metadata sensitivity can be unstable or misleading and are not clinical evidence. Deletion/insertion tests measure behavior under synthetic pixel replacement.
- The XAI API is local development functionality without authentication, persistence, or production safeguards.

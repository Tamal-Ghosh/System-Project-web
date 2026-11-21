# DermaInsight E38

This repository contains a local research interface for the E38 skin-lesion model. The active inference path is a DermFM visual transformer with LoRA fold adapters, fused with metadata. The service switches adapters on a shared model and averages probabilities across one or five folds. Horizontal and vertical test-time augmentation (TTA) can be enabled by configuration.

The API accepts one dermoscopic image, age, sex and an optional lesion site. The current single-image adapter duplicates that image into both model branches; this differs from paired-view training and has not been validated as an equivalent clinical workflow. Outputs are model scores, not diagnoses.

## Active features

- E38 11-class predictions, uncertainty summaries and optional TTA.
- On-demand Integrated Gradients for one fold's raw class logit.
- Exact metadata Shapley values grouped into age, sex and site.
- Offline faithfulness evaluation in `backend/scripts/xai_eval.py`.

Grad-CAM, pixel-level SHAP, MC dropout, segmentation and the clinical assistant are legacy or not implemented in this active E38 path.

## Run

Install the model environment documented in [backend/dermfm/INTEGRATION.md](backend/dermfm/INTEGRATION.md), including the external pinned foundation and adapter assets. Then launch the E38 API from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_inference.ps1
```

In a second terminal:

```powershell
Set-Location .\frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` and `/health` to `localhost:8000`. Do not use `start_app.bat` for the active E38 model; it starts the legacy backend.

## XAI

See [docs/xai.md](docs/xai.md) for methods, request format, validation limits and evaluation commands. The explanation endpoint is `POST /api/v1/explanations`; explanations are computed on demand and are not stored. They describe model behavior, not clinical correctness. Full deployment assets are required for real-model checks.

## Legacy

The legacy backend and older UI materials may mention ResNet50 and other prototype features. They do not describe the active E38 inference service. See [backend/dermfm/INTEGRATION.md](backend/dermfm/INTEGRATION.md) for model setup and [docker/README.md](docker/README.md) for the container workflow.

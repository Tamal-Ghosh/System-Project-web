# E38 integration — feature/model-integration

The original loader baseline is commit a81497c. Subsequent changes are grouped
by loader, preprocessing, inference service, API, dashboard and layout.
The legacy ResNet backend remains in main.py. The new dashboard calls the E38
inference_app API; start that app, not the legacy start_app.bat launcher.
No database, login, XAI or chatbot implementation is included in this change.

## Full-weight portable package (current local setup)

The verified E38_DermFM_Deployment_FULL_WEIGHTS.zip contains the foundation,
all five adapters, the pinned CAE/PanDerm visual source subset and its license.
Keep it outside tracked project source with the original source and license.
portable.py verifies fixed SHA256 values for both source files and foundation
files, builds the actual 24-layer, 1024-wide CAE visual tower and strictly loads
its state. The portable branch does not require an open_clip installation,
a Git checkout or a text encoder. The package JSON model_cfg alone describes
a different default visual architecture, so it is not used to build this tower.

model.local.json points to package assets/recipe.json, foundation, adapters,
dermfm_source and the existing deployment .venv Python. run_inference.ps1 uses
that Python when configured. These absolute local paths and weights are ignored.
CPU intra-op threads are limited to four at startup and worker inference.

## Alternative: full source checkout environment

Use a separate virtual environment and install backend/requirements-dermfm.txt.
For tests additionally install backend/requirements-dev.txt.
Clone https://github.com/SiyuanYan1/DermFM-Zero.git separately and checkout
c9f3d6a149ab048ae8a98ea4701e23b271e7368a. Its src folder must be on PYTHONPATH.
Obtain the gated foundation snapshot with an account that has approved access:
redlessone/DermFM-Zero, revision 2039b405065ff5ead7e58c04ec5604bd1e4a7769.
Required files are open_clip_config.json and open_clip_pytorch_model.bin.
Keep credentials and downloaded files outside tracked source. No token is
needed at inference time when these local files and dependencies are ready.
The loader constructs the pinned visual tower and strictly loads foundation
visual tensors. Text prototypes come from the adapters, so no text tower is built.

Run backend/prepare_model.py --archive PATH_TO_E29_control.zip
--recipe PATH_TO_E38_recipe.json --foundation PATH_TO_PINNED_SNAPSHOT
--source PATH_TO_DERMFM_SOURCE [--folds 0 1 2 3 4] [--device cpu].
Arguments above belong to one command. Default is fold 0 for the initial smoke test.
It creates ignored backend/.model-assets and backend/model.local.json.

From the project root: powershell -File .\run_inference.ps1
In another terminal, from frontend: npm run dev
Vite proxies /api and /health to localhost:8000. Use one backend worker; each
worker would otherwise load a separate foundation. CPU is supported but actual
latency and memory requirements have not yet been measured on the real model.
To smoke test loading separately, set the same DERMFM_* environment variables
as run_inference.ps1 and run backend/check_model.py from backend.

## Behavior and limits

Doctor supplies one dermoscopic image, age (0–120), sex (male/female) and an
optional lesion location dropdown. Location values exactly match the recipe site
vocabulary: foot, genital, hand, head_neck_face, lower_extremity, trunk and
upper_extremity. Unknown is the default and remains backward compatible.
The browser sends the original region or selected bounding crop as PNG, with
no patient name. Freehand currently selects a bounding rectangle, not a mask.
No selected crop means the complete image. The server uses the pinned foundation
preprocessing, repeats this one image into both branches and encodes the selected site with the recipe one-hot ordering. Unknown site
uses all zeros. This differs from paired-image/site training. Results explicitly
say this single-image adaptation is unvalidated. Never display the paired-view
OOF performance as the accuracy of this adapted pipeline.

TTA averages original/horizontal/vertical logits within each fold, then applies
softmax. Ensemble averages fold probabilities. Adapters are switched serially
under a lock on a shared visual foundation. The API rejects overlapping requests
with 429; missing model assets return 503, not initialized-model predictions.
Scores, normalized entropy, top-two margin and member agreement are calculated.
No calibration, OOD, image quality, XAI, clinical recommendation or persistence
is fabricated. Output includes model fingerprint, epoch list and input policy.
Age, sex, site, region and image changes invalidate previous UI results; pending fetches
are aborted and stale responses ignored. No analysis appears until success.

This endpoint is for localhost development only, without authentication/storage.
Do not expose it as the production clinical service. No images are saved by it.
Use a representative labeled validation set with held-out fold assignments to
compare the single-image policy to paired-view OOF results before accepting it.
The single-image validation experiment remains pending. A real five-fold API
forward pass through the website proxy succeeded locally in about 39 seconds
on CPU. This smoke test does not establish clinical accuracy or paired-view
equivalence.

## Checks and future commit groups

From backend: python -m unittest discover -s tests -v
From frontend: npm run build
Tests exercise synthetic checkpoints, exact adapter validation, metadata/image
validation, single/five-member inference, TTA math, repeated adapter switches,
API success/error/unavailable behavior. They do not establish clinical accuracy.

The implementation history separates loader/runtime, preprocessing, inference,
API, dashboard connection and responsive controls. Each step includes its own
applicable tests. Large weights, local paths and smoke outputs remain outside Git.

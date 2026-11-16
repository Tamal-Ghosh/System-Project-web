# E38 model loading

The loader supports the verified full-weight portable deployment package,
including fixed source/foundation checksums and strict adapter compatibility.
It fails closed on missing, mismatched or non-finite weights. Importing the
module never loads a model. No API or UI integration is introduced in this step.

Use load_model(recipe_path=..., checkpoint_path=..., foundation_path=...,
device="cpu"). The portable foundation directory contains manifest.json,
open_clip_config.json and open_clip_pytorch_model.bin; its sibling dermfm_source
contains the original CAE/PanDerm definitions and license. Those files and all
large weights remain outside Git. The portable path needs PyTorch, torchvision,
timm and NumPy, with no generic open_clip install. The alternative full-source
path requires the pinned DermFM-Zero checkout.

prepare_model.py extracts selected adapters safely from the E38 archive and
creates ignored local assets and model.local.json. model.example.json documents
the local configuration fields. For this full deployment package, paths can also
point directly to its assets/recipe.json and assets/fold*_best.pth files.

From backend: python -m unittest discover -s tests -v
The tests at this step cover loader compatibility, fail-closed behavior and
portable checksum/provenance checks; they do not measure clinical accuracy.

## Development API

inference_app.py adds GET /health and POST /api/v1/analyses (multipart image,
age and sex). Unavailable model assets return 503, invalid input returns 422,
and overlapping inference requests return 429. No fake result or fallback model
is returned. The response contains eleven scores and calculated uncertainty,
member agreement, model provenance and the unvalidated single-image policy.

Configure ignored backend/model.local.json and run run_inference.ps1 from the
project root. An optional python field selects a prepared deployment environment.
The service binds to localhost:8000. This is development-only: no authentication,
image storage or database is provided. Legacy main.py remains unchanged.
Install requirements-dev.txt for API tests. No dashboard connection is added here.

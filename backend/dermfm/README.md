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

## Classification inference

preprocessing.py handles one dermoscopic image, age, sex and unknown body site.
InferenceService reads local DERMFM_RECIPE, DERMFM_FOUNDATION, DERMFM_CHECKPOINTS,
DERMFM_DEVICE and DERMFM_TTA settings. Configure one fold or five distinct folds.
It shares a foundation while serially switching validated adapters under a lock.
TTA averages original/horizontal/vertical logits per fold, then applies softmax.
Ensemble averages fold probabilities; metrics.py computes descriptive entropy
and top-two margin. Results include provenance, agreement and explicit unavailable
features. Single-image accuracy is not established. No API is added in this step.

check_model.py loads the configured real model offline. Service tests use a
synthetic visual tower and verify averaging, adapter switches and repeatability.

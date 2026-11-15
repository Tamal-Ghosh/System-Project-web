# E38 loader (part 1)

Isolated loader; not yet connected to main.py or the UI. No weights are committed.
Use Python with PyTorch and the open_clip package from DermFM-Zero source commit
c9f3d6a149ab048ae8a98ea4701e23b271e7368a (src on PYTHONPATH).
Generic open-clip-torch is not a substitute for this custom source.
Provide recipe.json, a selected fold best.pth, and a local Hugging Face snapshot
2039b405065ff5ead7e58c04ec5604bd1e4a7769 containing open_clip_config.json and
open_clip_pytorch_model.bin. Foundation access must already be configured;
this loader does not download weights or read repository credentials.

Call dermfm.loader.load_model(recipe_path=..., checkpoint_path=...,
foundation_path=..., device="cpu"). The result contains model, eval_transform,
checkpoint_epoch and class order. Saved prototypes are loaded from the adapter;
text prompts do not need recomputing. Keep the returned foundation transform
for the preprocessing phase. The architecture still takes two image tensors
and 10 metadata values; single-image adaptation is not implemented here.

Run from backend: python -m unittest discover -s tests -v
Tests use a tiny synthetic backbone, not the real foundation. A successful real
foundation load and resource measurement remain required before deployment.

# E38 XAI implementation findings

- The active model is `DermFMFusion.forward(derm, clinical, metadata)`. It returns `[batch, 11]` raw logits. The current browser/API flow supplies one dermoscopic view and the service duplicates that tensor into both branches.
- `encode_metadata` lays out ten float32 columns: age divided by 100, male, female, then the seven recipe `SITES` indicators in order. Unknown site is seven zeros.
- `DermFMFusion.encode` calls the visual wrapper, takes element zero if it returns a tuple/list, then applies float32 L2 normalization. In `portable.py` the pinned `VisionTransformer` and `PanDermVisualWrapper` are loaded from source files checked against fixed SHA256 hashes. Those source files are in the external deployment package and are not present in this checkout, so the precise CLS/pooling implementation and its attention implementation cannot be independently inspected here.
- The fusion forward path itself has no `.detach()`, `.numpy()`, `no_grad`, or `inference_mode`; inference runs under `torch.inference_mode()` in `InferenceService.predict`. Metadata/image preprocessing returns tensors, and image preprocessing is differentiable only after conversion to a tensor (the PIL resize/crop happens before the model).
- LoRA wrappers replace each named `qkv` linear layer. The service loads each saved adapter into one shared model, serially under `InferenceService.lock`. Prediction applies configured horizontal/vertical TTA and averages fold probabilities.
- Device is configured by `DERMFM_DEVICE` and accepts CPU or CUDA; service tensors and model use that device. Model loading freezes all parameters and sets eval mode. Model input dtype is float32 in the E38 preprocessing configuration.
- The pinned architecture source has not been found in this repository, so fused-attention/attention-weight access cannot be confirmed. No attention attribution is implemented.
- This checkout has no `backend/model.local.json` or `backend/.model-assets`; the real-model gradient check and machine-specific cost measurements require the external deployment package.

`python backend/scripts/xai_gradient_check.py IMAGE` exercises one configured real fold. It verifies the image input receives a finite, nonzero gradient without changing model weights. The frontend-selected region is already sent as the input image; the API sees that crop as the complete image.

Integrated Gradients uses Captum when it is installed and falls back to the included trapezoidal path integration when it is not. This avoids reporting XAI as unavailable solely because the optional package is missing.

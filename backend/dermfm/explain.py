"""On-demand image and metadata explanations for one E38 fold logit."""
import base64
import io
import logging
import os
import time

import numpy as np
import torch
from PIL import Image, ImageFilter

from .loader import CLASSES, load_adapter
from .preprocessing import prepare_inputs

logger = logging.getLogger(__name__)
LIMITATIONS = "Explains model behavior, not clinical correctness."
METADATA_BASE_AGE = 0.5  # Training median is not recorded in the deployed recipe.

def xai_available():
    # The implementation has a built-in trapezoidal IG path; Captum is optional.
    return True


def _map_png(values):
    values = np.asarray(values, dtype=np.float32)
    ceiling = float(np.percentile(values, 99))
    if not np.isfinite(values).all() or not np.isfinite(ceiling):
        raise ValueError("invalid_attribution")
    pixels = np.zeros_like(values) if ceiling <= 0 else np.clip(values / ceiling, 0, 1)
    image = Image.fromarray((pixels * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))
    return base64.b64encode((lambda out: (image.save(out, format="PNG"), out.getvalue())[1])(io.BytesIO())).decode("ascii")


def _shapley(model, image, raw_meta, fold_index, target_class):
    # Indices follow encode_metadata: age, male, female, then SITES in recipe order.
    groups = ((0,), (1, 2), tuple(range(3, 10)))
    base = raw_meta.clone()
    base[0, 0] = METADATA_BASE_AGE
    base[0, 1:] = 0
    coalitions = []
    for mask in range(8):
        row = base.clone()
        for index, group in enumerate(groups):
            if mask & (1 << index):
                row[:, list(group)] = raw_meta[:, list(group)]
        coalitions.append(row)
    with torch.inference_mode():
        load_adapter(model, fold_index)
        # Keep the attribution request within the small memory headroom left
        # after loading the foundation model. Batched coalitions previously
        # multiplied the two-image visual activations by eight.
        values = np.asarray([
            float(model(image, image, coalition)[:, target_class].item())
            for coalition in coalitions
        ], dtype=np.float32)
    phi = []
    weights = (1/3, 1/6, 1/3)
    for feature in range(3):
        result = 0.0
        for mask in range(8):
            if mask & (1 << feature):
                continue
            size = mask.bit_count()
            result += weights[size] * (float(values[mask | (1 << feature)]) - float(values[mask]))
        phi.append(result)
    base_value, full_value = float(values[0]), float(values[7])
    if abs(sum(phi) - (full_value - base_value)) > 1e-4:
        raise RuntimeError("shapley_efficiency_failed")
    return {"base_value": base_value, "full_value": full_value,
            "features": dict(zip(("age", "sex", "site"), phi)),
            "note": "Model sensitivity, not causal.",
            "baseline_note": "Age baseline 0.5 (training median unavailable); sex and site use all-zero indicators."}


def explain_image_ig(model_ctx, image_tensor, meta_tensor, fold_index, target_class,
                     n_steps=20, baseline="blur", source_image=None):
    """Return a fold-logit Integrated Gradients map; weights stay frozen."""
    try:
        from captum.attr import IntegratedGradients
    except ImportError:
        IntegratedGradients = None
    model = model_ctx.loaded.model
    state = {name: parameter.requires_grad for name, parameter in model.named_parameters()}
    training = model.training
    started = time.perf_counter()
    try:
        model.eval()
        model.requires_grad_(False)
        image_tensor = image_tensor.detach().float().requires_grad_(True)
        if baseline == "zero":
            source_image = source_image or Image.new("RGB", (224, 224), (0, 0, 0))
            base = model_ctx.loaded.eval_transform(source_image).unsqueeze(0).to(image_tensor.device).float()
        else:
            blurred = source_image.filter(ImageFilter.GaussianBlur(radius=18)) if source_image else None
            if blurred is None:
                raise ValueError("blur_baseline_image_unavailable")
            base = model_ctx.loaded.eval_transform(blurred).unsqueeze(0).to(image_tensor.device).float()

        def forward(value):
            fixed_meta = meta_tensor.expand(value.shape[0], -1)
            return model(value, value, fixed_meta).float()[:, target_class]

        if IntegratedGradients is not None:
            # This model keeps two visual branches alive for every input. A
            # multi-item IG batch therefore needs several complete activation
            # graphs at once and can make the CPU container run out of memory.
            # One integration point at a time has the same attribution result
            # while keeping the peak allocation bounded.
            attribution, delta = IntegratedGradients(forward).attribute(
                image_tensor, baselines=base, n_steps=n_steps, internal_batch_size=1,
                return_convergence_delta=True)
        else:
            # Captum isn't installed in every configured local runtime. This is
            # the same trapezoidal path integral, accumulated in small batches.
            difference = image_tensor - base
            gradient_sum = torch.zeros_like(image_tensor)
            alphas = torch.linspace(0, 1, n_steps, device=image_tensor.device, dtype=torch.float32)
            for start in range(0, n_steps):
                alpha = alphas[start:start+1].view(-1, 1, 1, 1)
                points = (base + alpha * difference).detach().requires_grad_(True)
                scores = forward(points)
                gradients = torch.autograd.grad(scores.sum(), points)[0]
                weights = torch.ones(len(alpha), device=image_tensor.device, dtype=torch.float32)
                if start == 0: weights[0] = 0.5
                if start + len(alpha) == n_steps: weights[-1] = 0.5
                gradient_sum += (gradients * weights.view(-1, 1, 1, 1)).sum(dim=0, keepdim=True)
            attribution = difference * (gradient_sum / (n_steps - 1))
            input_score = float(forward(image_tensor).detach().item())
            baseline_score = float(forward(base).detach().item())
            completeness_delta = input_score - baseline_score - float(attribution.sum().detach().item())
            delta = torch.tensor([completeness_delta], device=image_tensor.device)
        signed = attribution.sum(dim=1)[0].detach().cpu().numpy()
        abs_map = attribution.abs().sum(dim=1)[0].detach().cpu().numpy()
        width, height = source_image.size
        if width >= height:
            crop_geometry = {"x": round((width-height)/2), "y": 0, "w": height, "h": height}
            resize_factor = 224 / height
        else:
            crop_geometry = {"x": 0, "y": round((height-width)/2), "w": width, "h": width}
            resize_factor = 224 / width
        with torch.enable_grad():
            input_score = float(forward(image_tensor).detach().item())
            baseline_score = float(forward(base).detach().item())
        return {"image_map": {"encoding": "png_base64", "width": 224, "height": 224,
                "crop": crop_geometry, "resize_factor": resize_factor,
                "data": _map_png(abs_map), "signed": signed.tolist(), "abs": abs_map.tolist(),
                "sum_attributions": float(signed.sum()), "logit_difference": input_score-baseline_score},
            "convergence_delta": float(delta.detach().abs().max().item()),
            "elapsed_ms": round((time.perf_counter()-started)*1000)}
    finally:
        model.requires_grad_(False)
        for name, parameter in model.named_parameters():
            parameter.requires_grad_(state[name])
        model.train(training)


def explain_analysis(service, image, age, sex, site, target_class=None, fold=None,
                     n_steps=20, baseline="blur", include_metadata=True):
    """Build the same input as prediction and explain one serialized fold."""
    started = time.perf_counter()
    fold_selection = "requested" if fold is not None else "fold_0_fallback"
    if fold is None:
        fold = 0
    stage = time.perf_counter()
    derm, _, meta = prepare_inputs(image, age, sex, service.loaded.eval_transform,
                                    service.settings.device, site)
    logger.info("XAI preprocessing completed in %.3fs", time.perf_counter()-stage)
    import hashlib
    input_hash = hashlib.sha256(
        derm.detach().cpu().contiguous().numpy().tobytes() +
        meta.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
    if target_class is not None and target_class not in CLASSES:
        raise ValueError("Unknown target class")
    if not 0 <= fold < len(service.states):
        raise ValueError("Fold must be between 0 and 4")
    if baseline not in ("blur", "zero") or not 4 <= n_steps <= 50:
        raise ValueError("Invalid explanation options")
    # The service lock serializes adapter swaps and gradient-enabled forwards.
    if target_class is None:
        # The default follows the ensemble prediction; callers may pass a class to avoid this extra pass.
        target_class = service.predict(image, age, sex, site)["leading_class"]
        logger.info("XAI target prediction completed in %.3fs", time.perf_counter()-stage)
    with service.lock:
        checkpoint = service.states[fold]
        model = service.loaded.model
        previous_state = {key: value.detach().clone() for key, value in model.state_dict().items() if key in model.adapter_keys}
        previous_mode = model.training
        previous_grad = {name: parameter.requires_grad for name, parameter in model.named_parameters()}
        try:
            load_adapter(model, checkpoint['model'])
            model.eval()
            with torch.inference_mode():
                logits = model(derm, derm, meta)
            target = int(logits[0].argmax()) if target_class is None else CLASSES.index(target_class)
            image_result = explain_image_ig(service, derm, meta, checkpoint['model'], target,
                n_steps=n_steps, baseline=baseline, source_image=image)
            logger.info("XAI Integrated Gradients completed in %.3fs", image_result["elapsed_ms"]/1000)
            metadata_result = _shapley(model, derm, meta, checkpoint['model'], target) if include_metadata else None
            if time.perf_counter() - started > float(os.getenv('DERMFM_XAI_TIMEOUT_SECONDS', '900')):
                raise TimeoutError('timeout')
        except Exception as exc:
            logger.exception("Explanation unavailable")
            return {"status": "unavailable", "reason": str(exc)[:120]}
        finally:
            model.load_state_dict(previous_state, strict=False)
            model.requires_grad_(False)
            for name, parameter in model.named_parameters():
                parameter.requires_grad_(previous_grad[name])
            model.train(previous_mode)
    return {"status": "ok", "method": "integrated_gradients", "score": "fold_logit",
        "target_class": CLASSES[target], "target_class_index": target, "fold": fold,
        "fold_selection": fold_selection,
        "model_version": service.version, "tta": "none", "input_hash": input_hash,
        "baseline": baseline, "n_steps": n_steps,
        "convergence_delta": image_result["convergence_delta"],
        "image_map": image_result["image_map"], "metadata_attribution": metadata_result,
        "elapsed_ms": round((time.perf_counter()-started)*1000), "limitations": LIMITATIONS}

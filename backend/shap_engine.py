"""
shap_engine.py — Partition SHAP + ImageMasker engine for DermaInsight AI
==========================================================================
Implements Steps 4–8 of the SHAP XAI pipeline using SHAP >= 0.46 (tested
against 0.54.1).

  Step 4 : Configure Partition SHAP with blur ImageMasker
           (shap.Explainer + shap.maskers.Image)
  Step 5 : Compute SHAP values for the model's predicted class
  Step 6 : Render SHAP heatmaps (positive / negative attribution overlay)
  Step 7 : Extend SHAP to all 7 HAM10000 classes
  Step 8 : Reliability / stability assessment

Performance note
----------------
Partition SHAP is run on a 56×56 downscale of the input image.  This gives
~16× fewer pixels and therefore far fewer superpixels for the PartitionExplainer
to evaluate, cutting wall-clock time from several minutes to ~10–30 s on CPU.
The resulting (56, 56, 3) attribution map is bicubically upsampled to (224, 224, 3)
before rendering so the heatmap still aligns with the original image.

This module is imported by main.py.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import shap
from scipy.stats import spearmanr

logger = logging.getLogger("shap_engine")

# ─── ImageNet normalisation constants ─────────────────────────────────────────
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# ─── SHAP input resolution (smaller = much faster; upsampled back to 224×224) ─
SHAP_SIZE = 56   # pixels. 56×56 ≈ 16× fewer than 224×224

# ─── Evaluation-budget presets ────────────────────────────────────────────────
# These are tuned for CPU inference (ResNet50).  Times are approximate on a
# typical laptop CPU:
#   fast    ~  50 evals →  ~10–15 s
#   medium  ~ 100 evals →  ~20–35 s
#   thorough~ 200 evals →  ~45–90 s
BUDGET_PRESETS: Dict[str, int] = {
    "fast":      50,
    "medium":   100,
    "thorough": 200,
}


# ─── Helper: numpy RGB image → normalised 224×224 PyTorch tensor ──────────────
def _img_to_tensor(img_rgb: np.ndarray, device: torch.device) -> torch.Tensor:
    """Convert (H, W, 3) uint8 RGB → (1, 3, 224, 224) normalised tensor."""
    img = cv2.resize(img_rgb, (224, 224)).astype(np.float32) / 255.0
    img = (img - IMAGENET_MEAN) / IMAGENET_STD
    return torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).to(device)


# ─── Step 4–8: Partition SHAP Engine ─────────────────────────────────────────
class PartitionSHAPEngine:
    """
    Wraps a PyTorch ResNet50 inside SHAP's PartitionExplainer with an
    ImageMasker that blurs hidden regions (Step 4).

    Key optimisation: SHAP operates on SHAP_SIZE×SHAP_SIZE (56×56) images.
    The predict function internally resizes each masked image back to 224×224
    before passing it through ResNet50, so model accuracy is unaffected.
    The returned attribution maps are upsampled to (224, 224, 3) for display.

    Public methods
    --------------
    explain(img_bgr, target_class, budget, masking) → dict
    render_heatmap(img_bgr, shap_values_224, alpha) → (overlay, pos_pct, neg_pct)
    explain_all_classes(img_bgr, budget, masking) → list[dict]
    reliability_assessment(img_bgr, target_class, masking) → dict
    """

    NUM_CLASSES = 7
    _SHAP_SHAPE = (SHAP_SIZE, SHAP_SIZE, 3)   # ImageMasker input shape

    def __init__(self, model: torch.nn.Module, device: torch.device) -> None:
        self.model  = model
        self.device = device

    # ── Step 4a: predict function ──────────────────────────────────────────────
    def _build_predict_fn(self, target_class: int):
        """
        Returns a predict function for SHAP.

        SHAP passes (N, SHAP_SIZE, SHAP_SIZE, 3) float32 masked images in [0,255].
        We resize each to 224×224, normalise, batch-infer through ResNet50, and
        return the (N,) probability array for target_class.
        """
        model  = self.model
        device = self.device

        def predict_fn(masked_images: np.ndarray) -> np.ndarray:
            n = masked_images.shape[0]
            batch = []
            for i in range(n):
                # Resize from SHAP_SIZE → 224 for full-resolution inference
                img_224 = cv2.resize(
                    masked_images[i].astype(np.uint8), (224, 224),
                    interpolation=cv2.INTER_LINEAR
                ).astype(np.float32) / 255.0
                img_224 = (img_224 - IMAGENET_MEAN) / IMAGENET_STD
                batch.append(
                    torch.from_numpy(img_224.transpose(2, 0, 1)).unsqueeze(0)
                )
            batch_tensor = torch.cat(batch, dim=0).to(device)
            model.eval()
            with torch.no_grad():
                probs = F.softmax(model(batch_tensor), dim=1).cpu().numpy()
            return probs[:, target_class].astype(np.float64)

        return predict_fn

    # ── Step 4b: build explainer ───────────────────────────────────────────────
    def _build_explainer(
        self,
        target_class: int,
        masking: str = "blur",
    ) -> shap.Explainer:
        """
        Build shap.Explainer (PartitionExplainer) with the chosen ImageMasker.

        Masking strategies
        ------------------
        "blur"     – Gaussian blur  "blur(9,9)"  (kernel adapted to 56×56)
        "inpaint"  – OpenCV inpaint (telea)
        "constant" – zero-fill (black)
        """
        shape = self._SHAP_SHAPE   # (56, 56, 3)

        if masking == "blur":
            # Use a smaller kernel appropriate for the 56×56 SHAP image
            masker = shap.maskers.Image("blur(9, 9)", shape)
        elif masking == "inpaint":
            masker = shap.maskers.Image("inpaint_telea", shape)
        else:  # constant / black
            masker = shap.maskers.Image(np.zeros(shape, dtype=np.uint8), shape)

        predict_fn = self._build_predict_fn(target_class)
        explainer  = shap.Explainer(predict_fn, masker, algorithm="partition")
        return explainer

    # ── Step 5: Compute SHAP values ───────────────────────────────────────────
    def explain(
        self,
        img_bgr: np.ndarray,
        target_class: Optional[int] = None,
        budget: str = "fast",
        masking: str = "blur",
    ) -> Dict:
        """
        Run Partition SHAP for one image and one target class.

        The image is downscaled to SHAP_SIZE×SHAP_SIZE for SHAP evaluation.
        Attribution values are bicubically upsampled back to (224, 224, 3)
        before being returned so they align with the original display image.

        Returns
        -------
        dict with keys:
          shap_values     (224, 224, 3) float32 – upsampled attribution map
          target_class    int
          pred_prob       float
          pred_class_all  (7,) float32
          budget, masking, elapsed_s
        """
        t0 = time.time()

        # BGR → RGB; get full-res class probabilities once
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        with torch.no_grad():
            probs = F.softmax(
                self.model(_img_to_tensor(img_rgb, self.device)), dim=1
            ).cpu().numpy()[0]

        if target_class is None:
            target_class = int(np.argmax(probs))
        pred_prob = float(probs[target_class])

        # Downscale to SHAP_SIZE for fast computation
        img_shap = cv2.resize(
            img_rgb, (SHAP_SIZE, SHAP_SIZE), interpolation=cv2.INTER_AREA
        )  # (56, 56, 3) uint8

        # Build explainer and run SHAP
        explainer  = self._build_explainer(target_class, masking)
        max_evals  = BUDGET_PRESETS.get(budget, BUDGET_PRESETS["fast"])
        img_input  = img_shap[np.newaxis, ...]                     # (1,56,56,3)

        shap_out   = explainer(img_input, max_evals=max_evals, batch_size=50)

        sv_small   = shap_out.values[0].astype(np.float32)         # (56, 56, 3)

        # Upsample attribution to (224, 224, 3) for display
        sv_224 = cv2.resize(
            sv_small, (224, 224), interpolation=cv2.INTER_CUBIC
        ).astype(np.float32)                                        # (224, 224, 3)

        elapsed = round(time.time() - t0, 2)
        logger.info(
            "SHAP explain: class=%d prob=%.3f budget=%s(%d) masking=%s elapsed=%.1fs",
            target_class, pred_prob, budget, max_evals, masking, elapsed,
        )

        return {
            "shap_values":    sv_224,
            "target_class":   target_class,
            "pred_prob":      pred_prob,
            "pred_class_all": probs,
            "budget":         budget,
            "masking":        masking,
            "elapsed_s":      elapsed,
        }

    # ── Step 6: Render SHAP heatmap ───────────────────────────────────────────
    @staticmethod
    def render_heatmap(
        img_bgr: np.ndarray,
        shap_values: np.ndarray,
        alpha: float = 0.55,
    ) -> Tuple[np.ndarray, float, float, float]:
        """
        Composite the SHAP attribution onto the original image.

        Parameters
        ----------
        img_bgr     : original BGR image (any size; resized internally to 224)
        shap_values : (224, 224, 3) float32 attribution map
        alpha       : heatmap weight in the blend

        Returns
        -------
        overlay      : (224, 224, 3) uint8 BGR
        positive_pct : % of significant attribution that is positive (salient filtered)
        negative_pct : % of significant attribution that is negative (salient filtered)
        net_attr     : net sum of attribution values across image
        """
        attribution = np.sum(shap_values, axis=2)   # (224, 224)
        net_attr = float(np.sum(attribution))

        abs_max = max(abs(float(attribution.min())), abs(float(attribution.max()))) + 1e-12

        # Saliency threshold: filter out background skin noise (< 12% of max magnitude)
        # to ensure positive/negative evidence percentages represent meaningful features
        # rather than random zero-centered noise on non-lesion pixels.
        noise_floor = 0.12 * abs_max
        sig_pos = float(np.sum(attribution[attribution > noise_floor]))
        sig_neg = float(np.sum(-attribution[attribution < -noise_floor]))
        sig_total = sig_pos + sig_neg

        if sig_total > 1e-10:
            pos_pct = round(sig_pos / sig_total * 100, 1)
            neg_pct = round(sig_neg / sig_total * 100, 1)
        else:
            pos_pct = 50.0
            neg_pct = 50.0

        norm_map = attribution / abs_max
        heat_u8  = np.uint8(np.clip((norm_map + 1.0) / 2.0 * 255, 0, 255))
        heatmap  = cv2.applyColorMap(heat_u8, cv2.COLORMAP_BJET)

        orig_224 = cv2.resize(img_bgr, (224, 224))
        overlay  = cv2.addWeighted(orig_224, 1.0 - alpha, heatmap, alpha, 0)

        return overlay, pos_pct, neg_pct, net_attr

    # ── Step 7: Explain all 7 classes ─────────────────────────────────────────
    def explain_all_classes(
        self,
        img_bgr: np.ndarray,
        budget: str = "fast",
        masking: str = "blur",
    ) -> List[Dict]:
        """
        Generate SHAP attributions for every class index 0–6.
        Always uses the "fast" budget to keep the full 7-class sweep tractable.
        """
        results: List[Dict] = []
        for cls_idx in range(self.NUM_CLASSES):
            result = self.explain(
                img_bgr,
                target_class=cls_idx,
                budget="fast",          # Force fast for all-class sweep
                masking=masking,
            )
            results.append(result)
        return results

    # ── Step 8: Reliability assessment ────────────────────────────────────────
    def reliability_assessment(
        self,
        img_bgr: np.ndarray,
        target_class: int,
        masking: str = "blur",
    ) -> Dict:
        """
        Step 8 checks:
          1. Budget comparison   – fast / medium attribution maps
          2. Masking comparison  – blur vs. constant-zero
          3. Spearman ρ          – fast vs medium spatial rank correlation
          4. Perturbation test   – blur top-50% positive pixels, measure ΔP
        """
        report: Dict = {}

        # ── 8a Budget comparison (fast + medium only; thorough is too slow for auto) ──
        budget_maps: Dict[str, Dict] = {}
        for budget_key in ["fast", "medium"]:
            r = self.explain(img_bgr, target_class=target_class,
                             budget=budget_key, masking=masking)
            budget_maps[budget_key] = {
                "shap_values": r["shap_values"],
                "elapsed_s":   r["elapsed_s"],
                "pred_prob":   r["pred_prob"],
            }
        report["budget_comparison"] = budget_maps

        # ── 8b Masking comparison (fast budget) ──────────────────────────────
        masking_maps: Dict[str, Dict] = {}
        for mask_key in ["blur", "constant"]:
            r = self.explain(img_bgr, target_class=target_class,
                             budget="fast", masking=mask_key)
            masking_maps[mask_key] = {
                "shap_values": r["shap_values"],
                "elapsed_s":   r["elapsed_s"],
            }
        report["masking_comparison"] = masking_maps

        # ── 8c Consistency: Spearman ρ between fast and medium ────────────────
        fast_flat   = np.sum(budget_maps["fast"]["shap_values"],   axis=2).ravel()
        medium_flat = np.sum(budget_maps["medium"]["shap_values"], axis=2).ravel()
        rho, _      = spearmanr(fast_flat, medium_flat)
        report["consistency_score"] = round(float(rho), 4)

        # ── 8d Perturbation test ──────────────────────────────────────────────
        medium_attr = np.sum(budget_maps["medium"]["shap_values"], axis=2)
        threshold   = np.percentile(medium_attr, 50)
        img_rgb     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_224     = cv2.resize(img_rgb, (224, 224))

        perturbed = img_224.copy().astype(np.float32)
        blurred   = cv2.GaussianBlur(img_224, (51, 51), 0).astype(np.float32)
        perturbed[medium_attr > threshold] = blurred[medium_attr > threshold]
        perturbed = perturbed.astype(np.uint8)

        with torch.no_grad():
            orig_probs = F.softmax(
                self.model(_img_to_tensor(img_rgb, self.device)), dim=1
            ).cpu().numpy()[0]
            pert_probs = F.softmax(
                self.model(_img_to_tensor(perturbed, self.device)), dim=1
            ).cpu().numpy()[0]

        delta = round(float(orig_probs[target_class] - pert_probs[target_class]), 4)
        report["perturbation_delta"] = delta
        report["orig_prob"]          = round(float(orig_probs[target_class]), 4)
        report["perturbed_prob"]     = round(float(pert_probs[target_class]), 4)

        return report

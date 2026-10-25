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
           - Budget comparison  (fast / medium / thorough)
           - Masking comparison (blur / constant-zero)
           - Spearman consistency score between budget levels
           - Perturbation test (ΔPROBABILITY when top-50% positive
             regions are blurred)

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

# ─── Evaluation-budget presets (max_evals passed to shap.Explainer.__call__) ──
BUDGET_PRESETS: Dict[str, int] = {
    "fast":     200,   # Coarse, for interactive / quick requests
    "medium":   500,   # Balanced quality / speed (default)
    "thorough": 1000,  # High-quality, slower
}


# ─── Helper: numpy RGB image → normalised PyTorch tensor ──────────────────────
def _img_to_tensor(img_rgb: np.ndarray, device: torch.device) -> torch.Tensor:
    """Convert (H, W, 3) uint8 RGB array → (1, 3, 224, 224) normalised tensor."""
    img = cv2.resize(img_rgb, (224, 224)).astype(np.float32) / 255.0
    img = (img - IMAGENET_MEAN) / IMAGENET_STD
    return torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).to(device)


# ─── Step 4 – 8: Partition SHAP Engine class ──────────────────────────────────
class PartitionSHAPEngine:
    """
    Wraps a PyTorch ResNet50 inside SHAP's PartitionExplainer with an
    ImageMasker that blurs hidden regions (Step 4).

    The masker receives a ``mask_value`` and the image ``shape`` as required
    by shap.maskers.Image (SHAP ≥ 0.46).  Gaussian blur ("blur(21,21)") is
    the default masking strategy; a zero-fill ("constant") alternative is also
    supported for reliability comparisons.

    Public methods
    --------------
    explain(img_bgr, target_class, budget, masking) → dict
        Steps 4, 5, 6 – build explainer, compute SHAP values, compute metrics.

    render_heatmap(img_bgr, shap_values, alpha) → (overlay, pos_pct, neg_pct)
        Step 6 – render an overlay image and return attribution percentages.

    explain_all_classes(img_bgr, budget, masking) → list[dict]
        Step 7 – repeat `explain()` for every class (0-6).

    reliability_assessment(img_bgr, target_class, masking) → dict
        Step 8 – budget comparison, masking comparison, Spearman score,
        perturbation test.
    """

    NUM_CLASSES = 7
    _IMG_SHAPE  = (224, 224, 3)   # SHAP ImageMasker requires (H, W, C)

    def __init__(self, model: torch.nn.Module, device: torch.device) -> None:
        self.model  = model
        self.device = device

    # ── Step 4 ── Build the predict function and SHAP Explainer ───────────────
    def _build_predict_fn(self, target_class: int):
        """
        Return a predict function that SHAP can call.

        SHAP passes batches of masked images as (N, H, W, C) float32 arrays
        with pixel values in [0, 255].  The function must return a 1-D array
        of shape (N,) containing the target-class probability for each image.
        """
        model  = self.model
        device = self.device

        def predict_fn(masked_images: np.ndarray) -> np.ndarray:
            n = masked_images.shape[0]
            batch = []
            for i in range(n):
                img = masked_images[i].astype(np.float32) / 255.0
                img = (img - IMAGENET_MEAN) / IMAGENET_STD
                batch.append(torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0))
            batch_tensor = torch.cat(batch, dim=0).to(device)
            model.eval()
            with torch.no_grad():
                probs = F.softmax(model(batch_tensor), dim=1).cpu().numpy()
            return probs[:, target_class]   # shape (N,)

        return predict_fn

    def _build_explainer(
        self,
        target_class: int,
        masking: str = "blur",
    ) -> shap.Explainer:
        """
        Construct shap.Explainer with the appropriate ImageMasker.

        Masking strategies
        ------------------
        "blur"     – Gaussian blur  blur(21, 21) — default; realistic occluder
        "inpaint"  – OpenCV inpaint (telea)
        "constant" – zero-fill (black background)

        The ``shape`` argument is required when ``mask_value`` is a string
        (not a dataset array).  It must match the image dimensions that SHAP
        will receive: (224, 224, 3).
        """
        if masking == "blur":
            masker = shap.maskers.Image("blur(21, 21)", self._IMG_SHAPE)
        elif masking == "inpaint":
            masker = shap.maskers.Image("inpaint_telea", self._IMG_SHAPE)
        else:  # constant / black
            masker = shap.maskers.Image(
                np.zeros(self._IMG_SHAPE, dtype=np.uint8), self._IMG_SHAPE
            )

        predict_fn = self._build_predict_fn(target_class)

        # algorithm="partition" forces PartitionExplainer, which is appropriate
        # for image inputs with a spatial masker.
        explainer = shap.Explainer(predict_fn, masker, algorithm="partition")
        return explainer

    # ── Step 5 ── Compute SHAP values ─────────────────────────────────────────
    def explain(
        self,
        img_bgr: np.ndarray,
        target_class: Optional[int] = None,
        budget: str = "medium",
        masking: str = "blur",
    ) -> Dict:
        """
        Run Partition SHAP for one image and one target class.

        Parameters
        ----------
        img_bgr      : (H, W, 3) uint8 BGR image (any resolution; resized internally)
        target_class : class index to explain (None → model's predicted class)
        budget       : "fast" | "medium" | "thorough"
        masking      : "blur" | "inpaint" | "constant"

        Returns
        -------
        dict with keys:
          shap_values     (224, 224, 3) float32 – per-pixel, per-channel attributions
          target_class    int
          pred_prob       float – probability of target_class
          pred_class_all  (7,) float32 – all class probabilities
          budget, masking, elapsed_s
        """
        t0 = time.time()

        # Convert BGR → RGB; resize once to 224×224
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_224 = cv2.resize(img_rgb, (224, 224))  # (224, 224, 3) uint8

        # Step 5a – obtain all class probabilities (one forward pass)
        with torch.no_grad():
            probs = F.softmax(
                self.model(_img_to_tensor(img_rgb, self.device)), dim=1
            ).cpu().numpy()[0]

        if target_class is None:
            target_class = int(np.argmax(probs))

        pred_prob = float(probs[target_class])

        # Step 4 – build the SHAP explainer for this class
        explainer = self._build_explainer(target_class, masking)

        # Step 5b – compute SHAP values
        # SHAP expects (N, H, W, C) input; we add the batch dimension here.
        img_input  = img_224[np.newaxis, ...]          # (1, 224, 224, 3)
        max_evals  = BUDGET_PRESETS.get(budget, 500)

        shap_out   = explainer(img_input, max_evals=max_evals, batch_size=32)

        # shap_out.values shape: (1, 224, 224, 3)
        sv = shap_out.values[0].astype(np.float32)     # (224, 224, 3)

        # Step 5c – validate dimensions
        assert sv.shape == (224, 224, 3), (
            f"Unexpected SHAP output shape {sv.shape}; expected (224, 224, 3)."
        )

        elapsed = round(time.time() - t0, 2)
        logger.info(
            "SHAP explain: class=%d prob=%.3f budget=%s masking=%s elapsed=%.1fs",
            target_class, pred_prob, budget, masking, elapsed,
        )

        return {
            "shap_values":    sv,
            "target_class":   target_class,
            "pred_prob":      pred_prob,
            "pred_class_all": probs,
            "budget":         budget,
            "masking":        masking,
            "elapsed_s":      elapsed,
        }

    # ── Step 6 ── Render SHAP heatmap ─────────────────────────────────────────
    @staticmethod
    def render_heatmap(
        img_bgr: np.ndarray,
        shap_values: np.ndarray,
        alpha: float = 0.55,
    ) -> Tuple[np.ndarray, float, float]:
        """
        Composite the SHAP attribution onto the original image.

        The attribution across the three colour channels is summed to produce a
        single spatial map.  Values above zero (warm colours) support the
        explained class; values below zero (cool colours) oppose it.

        Parameters
        ----------
        img_bgr     : original image in BGR (any size)
        shap_values : (224, 224, 3) float32 attribution map from explain()
        alpha       : heatmap opacity weight

        Returns
        -------
        overlay      : (224, 224, 3) uint8 BGR overlay
        positive_pct : percentage of absolute attribution that is positive
        negative_pct : percentage of absolute attribution that is negative
        """
        # Sum across colour channels → (224, 224) single attribution map
        attribution = np.sum(shap_values, axis=2)

        # Step 6 – Evidence breakdown (positive vs negative)
        pos_sum   = float(np.sum(np.maximum(attribution, 0)))
        neg_sum   = float(np.sum(np.maximum(-attribution, 0)))
        total_abs = pos_sum + neg_sum + 1e-10
        pos_pct   = round(pos_sum / total_abs * 100, 1)
        neg_pct   = round(neg_sum / total_abs * 100, 1)

        # Normalise [-1, 1] → [0, 255] (baseline=128 midpoint)
        abs_max   = max(abs(attribution.min()), abs(attribution.max())) + 1e-8
        norm_map  = attribution / abs_max                          # [-1, 1]
        heat_u8   = np.uint8(np.clip((norm_map + 1.0) / 2.0 * 255, 0, 255))
        heatmap   = cv2.applyColorMap(heat_u8, cv2.COLORMAP_BJET)

        orig_224  = cv2.resize(img_bgr, (224, 224))
        overlay   = cv2.addWeighted(orig_224, 1.0 - alpha, heatmap, alpha, 0)

        return overlay, pos_pct, neg_pct

    # ── Step 7 ── Explain all 7 HAM10000 classes ──────────────────────────────
    def explain_all_classes(
        self,
        img_bgr: np.ndarray,
        budget: str = "fast",
        masking: str = "blur",
    ) -> List[Dict]:
        """
        Generate SHAP attributions for every class index 0–6 for the same
        image.  Uses the ``fast`` budget by default so the full 7-class sweep
        remains tractable.

        Returns
        -------
        List of result dicts, one per class, in class-index order.
        Each dict has the same structure as the return value of ``explain()``.
        """
        results: List[Dict] = []
        for cls_idx in range(self.NUM_CLASSES):
            result = self.explain(
                img_bgr,
                target_class=cls_idx,
                budget=budget,
                masking=masking,
            )
            results.append(result)
        return results

    # ── Step 8 ── Reliability assessment ──────────────────────────────────────
    def reliability_assessment(
        self,
        img_bgr: np.ndarray,
        target_class: int,
        masking: str = "blur",
    ) -> Dict:
        """
        Step 8: Evaluate the stability and limitations of SHAP explanations.

        Checks performed
        ----------------
        1. Budget comparison   – SHAP maps at fast / medium / thorough evals.
        2. Masking comparison  – SHAP maps with blur vs. constant-zero masker.
        3. Consistency score   – Spearman ρ between fast and medium attribution
                                 maps (spatial rank correlation).  Higher is
                                 more stable.
        4. Perturbation test   – Blur the top-50% positively-attributed pixels
                                 and measure ΔPROBABILITY.  A large positive
                                 delta supports that SHAP identified the most
                                 important region.

        Returns
        -------
        dict with keys: budget_comparison, masking_comparison,
        consistency_score, perturbation_delta, orig_prob, perturbed_prob.
        """
        report: Dict = {}

        # ── 8a – Budget comparison ─────────────────────────────────────────────
        budget_maps: Dict[str, Dict] = {}
        for budget_key in ["fast", "medium", "thorough"]:
            r = self.explain(
                img_bgr,
                target_class=target_class,
                budget=budget_key,
                masking=masking,
            )
            budget_maps[budget_key] = {
                "shap_values": r["shap_values"],
                "elapsed_s":   r["elapsed_s"],
                "pred_prob":   r["pred_prob"],
            }
        report["budget_comparison"] = budget_maps

        # ── 8b – Masking strategy comparison (fast budget) ────────────────────
        masking_maps: Dict[str, Dict] = {}
        for mask_key in ["blur", "constant"]:
            r = self.explain(
                img_bgr,
                target_class=target_class,
                budget="fast",
                masking=mask_key,
            )
            masking_maps[mask_key] = {
                "shap_values": r["shap_values"],
                "elapsed_s":   r["elapsed_s"],
            }
        report["masking_comparison"] = masking_maps

        # ── 8c – Consistency score: Spearman rank correlation ─────────────────
        fast_flat   = np.sum(budget_maps["fast"]["shap_values"],   axis=2).ravel()
        medium_flat = np.sum(budget_maps["medium"]["shap_values"], axis=2).ravel()
        rho, _      = spearmanr(fast_flat, medium_flat)
        report["consistency_score"] = round(float(rho), 4)

        # ── 8d – Perturbation test ─────────────────────────────────────────────
        # Take the medium-budget map, find the top-50% positively attributed
        # pixels, blur them in the original image, and measure ΔPROBABILITY.
        medium_attr = np.sum(budget_maps["medium"]["shap_values"], axis=2)
        threshold   = np.percentile(medium_attr, 50)
        img_rgb     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_224     = cv2.resize(img_rgb, (224, 224))

        perturbed = img_224.copy().astype(np.float32)
        blurred   = cv2.GaussianBlur(img_224, (51, 51), 0).astype(np.float32)
        mask      = medium_attr > threshold
        perturbed[mask] = blurred[mask]
        perturbed = perturbed.astype(np.uint8)

        with torch.no_grad():
            orig_probs = F.softmax(
                self.model(_img_to_tensor(img_rgb, self.device)), dim=1
            ).cpu().numpy()[0]
            pert_probs = F.softmax(
                self.model(_img_to_tensor(perturbed, self.device)), dim=1
            ).cpu().numpy()[0]

        delta = round(float(orig_probs[target_class] - pert_probs[target_class]), 4)
        report["perturbation_delta"] = delta       # +ve → SHAP found important regions
        report["orig_prob"]          = round(float(orig_probs[target_class]), 4)
        report["perturbed_prob"]     = round(float(pert_probs[target_class]), 4)

        return report

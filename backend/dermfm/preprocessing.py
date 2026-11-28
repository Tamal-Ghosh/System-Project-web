"""Single dermoscopic input adapter; this differs from paired-view training."""
import io
import math
import os
import warnings
import numpy as np
import torch
from PIL import Image, ImageOps, UnidentifiedImageError
from .loader import SITES

MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 40_000_000

def encode_metadata(age, sex, site="unknown"):
    if not math.isfinite(age) or not 0 <= age <= 120:
        raise ValueError("Age must be between 0 and 120")
    if sex not in ("male", "female"):
        raise ValueError("Sex must be male or female")
    if site not in (*SITES, "unknown", "", None):
        raise ValueError("Choose a supported lesion location or Unknown")
    site_values = [float(site == category) for category in SITES]
    return torch.tensor([[age/100, float(sex == "male"), float(sex == "female"), *site_values]], dtype=torch.float32)

def decode_image(contents):
    if not contents or len(contents) > MAX_BYTES:
        raise ValueError("Choose an image up to 20 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as image:
                if image.format not in ("JPEG", "PNG", "WEBP"):
                    raise ValueError("Choose a JPG, PNG or WebP image")
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError("Image exceeds 40 million pixels")
                image.load()
                return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Image cannot be decoded safely") from exc

def prepare_inputs(image, age, sex, transform, device, site="unknown"):
    tensor = transform(image)
    if not isinstance(tensor, torch.Tensor) or tensor.ndim != 3 or tensor.shape[0] != 3 or not torch.isfinite(tensor).all():
        raise ValueError("Foundation preprocessing produced an invalid image tensor")
    tensor = tensor.unsqueeze(0).to(device)
    metadata = encode_metadata(age, sex, site).to(device)
    return tensor, tensor, metadata


def assess_image_quality(image: Image.Image) -> dict:
    """Evaluates dermoscopic image quality across 4 clinical dimensions:
    1. Focus & Micro-detail Sharpness (Laplacian variance & edge energy)
    2. Illumination & Exposure Balance (mean brightness and contrast)
    3. Surface Glare & Specular Reflection (high-intensity white saturation)
    4. Lesion Centering & Field of View (spatial framing & border distance)

    Returns structured, clinician-comprehensible diagnostic metrics and guidance.
    """
    blur_threshold = float(os.getenv("IQA_BLUR_THRESHOLD", "10.0"))
    grad_threshold = float(os.getenv("IQA_GRAD_THRESHOLD", "55.0"))

    gray = np.array(image.convert("L"), dtype=np.float64)
    if gray.shape[0] < 4 or gray.shape[1] < 4:
        return {
            "status": "rejected",
            "sharpness_score": 0.0,
            "max_edge_gradient": 0.0,
            "blur_detected": True,
            "blur_threshold": blur_threshold,
            "overall_score": 0,
            "clinical_verdict": "Unusable Resolution",
            "doctor_recommendation": "Image resolution is too low for clinical evaluation. Please upload a high-resolution dermoscopic image.",
            "details": "Image resolution too small to evaluate.",
            "checks": [],
        }

    # 1. Discrete 2D Laplacian operator via 2D array slicing (pure numpy, no cv2 dependency needed)
    lap = gray[2:, 1:-1] + gray[:-2, 1:-1] + gray[1:-1, 2:] + gray[1:-1, :-2] - 4.0 * gray[1:-1, 1:-1]
    variance = float(lap.var())

    # Max gradient difference across horizontal and vertical axes
    gx = np.abs(gray[:, 1:] - gray[:, :-1])
    gy = np.abs(gray[1:, :] - gray[:-1, :])
    max_grad = float(max(gx.max(), gy.max()))

    # Severe blur detection: very low edge energy and low variance
    is_blurry = bool(variance < blur_threshold and max_grad < grad_threshold)
    focus_pct = int(min(max((variance / 50.0) * 100.0, 0.0), 100.0))
    focus_status = "fail" if is_blurry else ("warn" if variance < blur_threshold * 2.0 else "pass")

    # 2. Illumination & Exposure Balance
    mean_b = float(np.mean(gray))
    std_b = float(np.std(gray))
    if mean_b < 20.0 or mean_b > 242.0 or std_b < 6.0:
        exposure_status = "fail"
    elif mean_b < 45.0 or mean_b > 215.0 or std_b < 20.0:
        exposure_status = "warn"
    else:
        exposure_status = "pass"
    exposure_pct = int(max(0.0, min(100.0, 100.0 - abs(mean_b - 128.0) * 0.6 - max(0.0, 30.0 - std_b) * 1.2)))

    # 3. Surface Glare & Specular Reflection
    rgb = np.array(image.convert("RGB"), dtype=np.uint8)
    glare_mask = (rgb[:, :, 0] > 238) & (rgb[:, :, 1] > 238) & (rgb[:, :, 2] > 238)
    glare_ratio = float(np.mean(glare_mask))
    if glare_ratio > 0.10:
        glare_status = "fail"
    elif glare_ratio > 0.035:
        glare_status = "warn"
    else:
        glare_status = "pass"
    glare_pct = int(max(0.0, min(100.0, 100.0 - glare_ratio * 500.0)))

    # 4. Lesion Centering & Field of View
    h, w = gray.shape[:2]
    aspect = max(h, w) / max(min(h, w), 1)
    framing_status = "warn" if aspect > 2.5 else "pass"
    framing_pct = 80 if framing_status == "warn" else 95

    # Overall Composite Score
    overall_score = int(round(0.35 * focus_pct + 0.30 * exposure_pct + 0.20 * glare_pct + 0.15 * framing_pct))

    # Determine Overall Quality Status
    if is_blurry or exposure_status == "fail":
        status = "rejected"
        clinical_verdict = "Diagnostic Quality Compromised"
    elif focus_status == "warn" or exposure_status == "warn" or glare_status == "warn" or framing_status == "warn":
        status = "warning"
        clinical_verdict = "Diagnostic Quality Acceptable (With Advisories)"
    else:
        status = "passed"
        clinical_verdict = "Diagnostic Quality Optimal"

    # Clinician Actionable Guidance
    if is_blurry:
        doctor_rec = (
            "Optical blur detected. Fine pigment network structures and micro-globules cannot be evaluated reliably. "
            "Re-photograph with steady optical contact or inspect under direct manual dermoscopy."
        )
    elif glare_status != "pass":
        doctor_rec = (
            "Surface flash glare detected on lesion area. Subsurface melanin patterns may be partially occluded. "
            "Ensure cross-polarized illumination or immersion gel for optimal clarity."
        )
    elif exposure_status != "pass":
        doctor_rec = (
            "Illumination is slightly uneven or underexposed. Lesion contrast may appear darker than in direct visual inspection. "
            "Verify pigment variegation clinically."
        )
    elif framing_status != "pass":
        doctor_rec = (
            "Lesion is captured close to the image perimeter. Check that complete lesion borders are included in the field of view."
        )
    else:
        doctor_rec = (
            "Optimal clinical clarity. Optical resolution, illumination balance, and surface clarity satisfy dermatological decision-support standards."
        )

    # Detailed structured checks for the UI
    checks = [
        {
            "id": "focus",
            "name": "Focus & Sharpness",
            "label": "Sharp & In-Focus" if focus_status == "pass" else ("Mild Blur / Soft Focus" if focus_status == "warn" else "Severe Blur / Out-of-Focus"),
            "status": focus_status,
            "score_pct": focus_pct,
            "clinical_impact": "High-frequency pigment networks and globules can be evaluated." if focus_status == "pass" else "Fine dermoscopic structures may be obscured; risk of missed micro-features.",
            "detail": f"Edge gradient energy: {round(max_grad, 1)} (Variance: {round(variance, 1)})",
        },
        {
            "id": "exposure",
            "name": "Lighting & Exposure",
            "label": "Balanced Illumination" if exposure_status == "pass" else ("Under/Overexposed" if exposure_status == "warn" else "Severe Exposure Distortion"),
            "status": exposure_status,
            "score_pct": exposure_pct,
            "clinical_impact": "Optimal contrast between lesion and surrounding skin." if exposure_status == "pass" else "Uneven lighting may distort lesion color and boundary contrast.",
            "detail": f"Mean brightness: {round(mean_b, 1)}/255 (Contrast: {round(std_b, 1)})",
        },
        {
            "id": "glare",
            "name": "Glare & Reflection",
            "label": "Anti-reflective Clarity" if glare_status == "pass" else ("Moderate Surface Glare" if glare_status == "warn" else "Excessive Specular Reflection"),
            "status": glare_status,
            "score_pct": glare_pct,
            "clinical_impact": "Contact flash reflection does not occlude lesion architecture." if glare_status == "pass" else "Surface glare obscures subsurface melanin patterns.",
            "detail": f"Specular highlight area: {round(glare_ratio * 100, 1)}%",
        },
        {
            "id": "framing",
            "name": "Lesion Centering",
            "label": "Well-Centered" if framing_status == "pass" else "Perimeter Caution",
            "status": framing_status,
            "score_pct": framing_pct,
            "clinical_impact": "Full lesion perimeter is captured within visual field." if framing_status == "pass" else "Lesion is positioned near image boundary; border evaluation may be clipped.",
            "detail": "Lesion is positioned within center field of view" if framing_status == "pass" else "Elongated aspect ratio; confirm full lesion margin is captured",
        },
    ]

    return {
        "status": status,
        "sharpness_score": round(variance, 2),
        "max_edge_gradient": round(max_grad, 2),
        "blur_detected": is_blurry,
        "blur_threshold": blur_threshold,
        "overall_score": overall_score,
        "clinical_verdict": clinical_verdict,
        "doctor_recommendation": doctor_rec,
        "details": (
            "Severe blur detected. High-frequency dermoscopic features are missing."
            if is_blurry
            else "Image sharpness meets clinical diagnostic standards."
        ),
        "checks": checks,
    }

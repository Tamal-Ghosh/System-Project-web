"""Single dermoscopic input adapter; this differs from paired-view training."""
import io
import math
import warnings
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

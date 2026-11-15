"""Offline, fail-closed loader for E38 locked-control adapter checkpoints."""
from dataclasses import dataclass
from pathlib import Path
import json
import torch
from torch import nn
from torch.nn import functional as F

CLASSES = ("AKIEC", "BCC", "BEN_OTH", "BKL", "DF", "INF", "MAL_OTH", "MEL", "NV", "SCCKA", "VASC")
SITES = ("foot", "genital", "hand", "head_neck_face", "lower_extremity", "trunk", "upper_extremity")
FOUNDATION_REVISION = "2039b405065ff5ead7e58c04ec5604bd1e4a7769"
SOURCE_REVISION = "c9f3d6a149ab048ae8a98ea4701e23b271e7368a"

class ModelLoadError(RuntimeError):
    pass

class LoRALinear(nn.Module):
    def __init__(self, base, rank=8):
        super().__init__()
        self.base = base
        self.down = nn.Linear(base.in_features, rank, bias=False)
        self.up = nn.Linear(rank, base.out_features, bias=False)
        nn.init.zeros_(self.up.weight)
        self.scale = 2.
    @property
    def weight(self):
        return self.base.weight + (self.up.weight @ self.down.weight) * self.scale
    @property
    def bias(self):
        return self.base.bias
    @property
    def in_features(self):
        return self.base.in_features
    @property
    def out_features(self):
        return self.base.out_features
    def forward(self, x):
        return self.base(x) + self.up(self.down(x)) * self.scale

def inject_lora(module):
    count = 0
    for name, child in list(module.named_children()):
        if isinstance(child, nn.Linear) and name == "qkv":
            setattr(module, name, LoRALinear(child))
            count += 1
        else:
            count += inject_lora(child)
    return count

class DermFMFusion(nn.Module):
    def __init__(self, visual, prototypes):
        super().__init__()
        self.backbone = visual
        self.backbone.requires_grad_(False)
        if not inject_lora(self.backbone):
            raise ModelLoadError("Foundation has no expected qkv layers")
        self.register_buffer("prototypes", prototypes.clone())
        dim = prototypes.shape[1]
        self.meta = nn.Sequential(nn.Linear(10, 64), nn.GELU(), nn.LayerNorm(64))
        self.head = nn.Sequential(nn.Linear(dim*4+64, 256), nn.GELU(), nn.Dropout(.3), nn.Linear(256, 11))
        self.gate = nn.Sequential(nn.Linear(dim*2+64, 64), nn.GELU(), nn.Linear(64, 11))
        self.log_scale = nn.Parameter(torch.tensor(2.302585))
    def train(self, mode=True):
        super().train(mode)
        self.backbone.eval()
        return self
    def encode(self, image):
        features = self.backbone(image)
        if isinstance(features, (tuple, list)):
            features = features[0]
        return F.normalize(features.float(), dim=-1)
    def forward(self, derm, clinical, metadata):
        d, c, m = self.encode(derm), self.encode(clinical), self.meta(metadata)
        gate = torch.sigmoid(self.gate(torch.cat([d, c, m], dim=1)))
        semantic = gate*(d @ self.prototypes.T)+(1-gate)*(c @ self.prototypes.T)
        residual = self.head(torch.cat([d, c, torch.abs(d-c), d*c, m], dim=1))
        return self.log_scale.exp().clamp(max=100)*semantic+residual

def validate_recipe(path):
    recipe = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = dict(classes=list(CLASSES), site_vocab=list(SITES), site_mode="site",
                    foundation="redlessone/DermFM-Zero", foundation_revision=FOUNDATION_REVISION,
                    repo_commit=SOURCE_REVISION, lora_rank=8, experiment="E38_locked_control",
                    clinical_shades_of_gray=False, dermoscopy_shades_of_gray=False)
    for key, value in expected.items():
        if recipe.get(key) != value:
            raise ModelLoadError(f"Unsupported recipe field: {key}")
    return recipe

def read_checkpoint(path):
    checkpoint = torch.load(Path(path), map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("model"), dict):
        raise ModelLoadError("Expected E38 checkpoint with model adapter state")
    state = checkpoint["model"]
    if not state or any(not isinstance(v, torch.Tensor) or not torch.isfinite(v).all() for v in state.values()):
        raise ModelLoadError("Adapter contains invalid or non-finite tensors")
    prototypes = state.get("prototypes")
    if prototypes is None or prototypes.ndim != 2 or prototypes.shape[0] != 11 or prototypes.shape[1] < 1:
        raise ModelLoadError("Expected saved text prototypes for 11 classes")
    return checkpoint

def load_adapter(model, state):
    names = {name for name, p in model.named_parameters() if p.requires_grad}
    expected = {k: v for k, v in model.state_dict().items() if k in names or k == "prototypes"}
    if set(state) != set(expected):
        raise ModelLoadError("Adapter keys do not match E38 architecture")
    for key, target in expected.items():
        if state[key].shape != target.shape or state[key].dtype != target.dtype:
            raise ModelLoadError(f"Adapter tensor mismatch: {key}")
    model.load_state_dict(state, strict=False)

@dataclass(frozen=True)
class LoadedModel:
    model: DermFMFusion
    eval_transform: object
    checkpoint_epoch: int
    device: str
    classes: tuple = CLASSES

def local_foundation(snapshot):
    """Use the pinned DermFM source's open_clip; never download implicitly."""
    import subprocess
    import open_clip
    source = Path(open_clip.__file__).resolve().parent
    revision = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    if revision != SOURCE_REVISION:
        raise ModelLoadError("open_clip must come from the pinned DermFM source revision")
    snapshot = Path(snapshot).resolve()
    if snapshot.name != FOUNDATION_REVISION:
        raise ModelLoadError("Use the pinned Hugging Face foundation snapshot directory")
    config = json.loads((snapshot / "open_clip_config.json").read_text(encoding="utf-8"))
    weights = snapshot / "open_clip_pytorch_model.bin"
    if not weights.is_file():
        raise ModelLoadError("Local foundation weights are missing")
    from open_clip.factory import _MODEL_CONFIGS
    name = "e38_local_pinned"
    _MODEL_CONFIGS[name] = config["model_cfg"]
    foundation, _, transform = open_clip.create_model_and_transforms(
        name, pretrained=str(weights), device="cpu", pretrained_hf=False, **{
            "image_" + key: value for key, value in config["preprocess_cfg"].items()
            if key in ("mean", "std", "interpolation", "resize_mode")})
    return foundation.visual, transform

def load_model(*, recipe_path, checkpoint_path, foundation_path, device="cpu", foundation_factory=None):
    """Return only a fully validated model. No initialized-model fallback."""
    try:
        validate_recipe(recipe_path)
        checkpoint = read_checkpoint(checkpoint_path)
        visual, transform = (foundation_factory or local_foundation)(foundation_path)
        model = DermFMFusion(visual, checkpoint["model"]["prototypes"])
        load_adapter(model, checkpoint["model"])
        model.to(torch.device(device)).eval()
        model.requires_grad_(False)
        return LoadedModel(model, transform, int(checkpoint["epoch"]), str(device))
    except ModelLoadError:
        raise
    except Exception as exc:
        raise ModelLoadError(f"DermFM loading failed: {exc}") from exc

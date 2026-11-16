"""Serialized adapter switching shares one foundation across five folds."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import threading
import time
import uuid
import numpy as np
import torch
from .loader import CLASSES, load_model, read_checkpoint, load_adapter
from .preprocessing import prepare_inputs
from .metrics import summarize

@dataclass(frozen=True)
class Settings:
    recipe: Path
    foundation: Path
    checkpoints: tuple[Path, ...]
    device: str = "cpu"
    tta: bool = True
    @classmethod
    def from_env(cls):
        required = ("DERMFM_RECIPE", "DERMFM_FOUNDATION", "DERMFM_CHECKPOINTS")
        if any(not os.environ.get(key) for key in required):
            raise ValueError("Configure DERMFM_RECIPE, DERMFM_FOUNDATION and DERMFM_CHECKPOINTS")
        paths = tuple(Path(x.strip()) for x in os.environ["DERMFM_CHECKPOINTS"].split(";") if x.strip())
        if len(paths) not in (1,5) or len(set(paths)) != len(paths):
            raise ValueError("Configure one checkpoint or five distinct fold checkpoints")
        device = os.getenv("DERMFM_DEVICE", "cpu")
        if device != "cpu" and not device.startswith("cuda"):
            raise ValueError("Device must be cpu or cuda[:index]")
        return cls(Path(os.environ[required[0]]), Path(os.environ[required[1]]), paths, device,
                   os.getenv("DERMFM_TTA", "true").lower() == "true")

class InferenceService:
    def __init__(self, settings, factory=None):
        self.settings = settings
        torch.set_num_threads(4)
        self.loaded = load_model(recipe_path=settings.recipe, checkpoint_path=settings.checkpoints[0],
            foundation_path=settings.foundation, device=settings.device, foundation_factory=factory)
        self.states = [read_checkpoint(path) for path in settings.checkpoints]
        for checkpoint in self.states:
            load_adapter(self.loaded.model, checkpoint['model'])
        self.lock = threading.Lock()
        digest = hashlib.sha256(settings.recipe.read_bytes())
        for path in settings.checkpoints:
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
        self.version = 'e38-control-' + digest.hexdigest()[:16]
    def predict(self, image, age, sex):
        start = time.perf_counter()
        torch.set_num_threads(4)
        derm, clinical, meta = prepare_inputs(image, age, sex, self.loaded.eval_transform, self.settings.device)
        members = []
        with self.lock, torch.inference_mode():
            for checkpoint in self.states:
                load_adapter(self.loaded.model, checkpoint['model'])
                logits = [self.loaded.model(derm, clinical, meta)]
                if self.settings.tta:
                    for dim in (-1, -2):
                        logits.append(self.loaded.model(derm.flip(dim), clinical.flip(dim), meta))
                probabilities = torch.stack(logits).mean(0).softmax(-1)[0].cpu().double().numpy()
                summarize(probabilities)
                members.append(probabilities)
        averaged = np.mean(members, axis=0)
        entropy, margin = summarize(averaged)
        winner = int(averaged.argmax())
        return dict(analysis_id=str(uuid.uuid4()), model_version=self.version, classes=list(CLASSES),
            leading_class=CLASSES[winner], scores=[dict(label=label, score=float(score)) for label,score in zip(CLASSES,averaged)],
            uncertainty=dict(normalized_entropy=entropy, top_two_margin=margin),
            ensemble=dict(member_count=len(members), member_scores=[p.tolist() for p in members],
                agreement=float(np.mean([int(p.argmax()) == winner for p in members])) if len(members)>1 else None),
            input_policy='single_dermoscopic_duplicated_unknown_site', tta=self.settings.tta,
            checkpoint_epochs=[int(c['epoch']) for c in self.states],
            elapsed_ms=round((time.perf_counter()-start)*1000),
            limitations=['Single-image adaptation has not been validated against paired-view training.',
                'Body site was encoded as unknown. Class scores are not calibrated clinical risk.'],
            unavailable=['xai', 'ood', 'image_quality', 'clinical_next_step'], persistence='not_saved')

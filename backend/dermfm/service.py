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
from .preprocessing import prepare_inputs, assess_image_quality
from .metrics import summarize
from .calibration import load_temperature_calibration
from .rejection import evaluate_rejection_policy
from .conformal import evaluate_conformal_prediction
from .ood import evaluate_ood

@dataclass(frozen=True)
class Settings:
    recipe: Path
    foundation: Path
    checkpoints: tuple[Path, ...]
    device: str = "cpu"
    tta: bool = True
    calibration: Path | None = None
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
        calibration = os.getenv("DERMFM_CALIBRATION")
        return cls(Path(os.environ[required[0]]), Path(os.environ[required[1]]), paths, device,
                   os.getenv("DERMFM_TTA", "true").lower() == "true",
                   Path(calibration) if calibration else None)

class InferenceService:
    def __init__(self, settings, factory=None):
        self.settings = settings
        threads = int(os.getenv("TORCH_THREADS", os.getenv("OMP_NUM_THREADS", "8")))
        torch.set_num_threads(threads)
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
        self.calibration = load_temperature_calibration(settings.calibration, self.version)
    def predict(self, image, age, sex, site="unknown"):
        start = time.perf_counter()
        torch.set_num_threads(4)
        derm, clinical, meta = prepare_inputs(image, age, sex, self.loaded.eval_transform, self.settings.device, site)
        input_hash = hashlib.sha256(derm.detach().cpu().contiguous().numpy().tobytes() + meta.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
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
        raw_averaged = np.mean(members, axis=0)
        averaged = self.calibration.apply(raw_averaged) if self.calibration else raw_averaged
        entropy, margin = summarize(averaged)
        winner = int(averaged.argmax())
        scores_list = [dict(label=label, score=float(score)) for label, score in zip(CLASSES, averaged)]
        agreement_val = float(np.mean([int(p.argmax()) == winner for p in members])) if len(members) > 1 else None
        quality = assess_image_quality(image)
        ood_result = evaluate_ood(
            image=image,
            probabilities=averaged,
            members=members,
            metadata=dict(age=age, sex=sex, site=site or "unknown"),
        )
        rejection = evaluate_rejection_policy(
            scores=scores_list,
            entropy=entropy,
            margin=margin,
            agreement=agreement_val,
            image_quality=quality,
            ood_result=ood_result,
        )
        return dict(analysis_id=str(uuid.uuid4()), model_version=self.version, classes=list(CLASSES),
            leading_class=CLASSES[winner], scores=scores_list,
            conformal_prediction=evaluate_conformal_prediction(scores_list, coverage=0.95),
            assessment_status=rejection["status"], rejection=rejection,
            image_quality=quality,
            ood=ood_result,
            uncertainty=dict(normalized_entropy=entropy, top_two_margin=margin),
            calibration=(self.calibration.public_summary() if self.calibration else {
                'applied': False, 'temperature': None,
                'reason': 'No validated temperature artifact is configured for this model version.'}),
            uncalibrated_scores=([dict(label=label, score=float(score)) for label,score in zip(CLASSES,raw_averaged)]
                                 if self.calibration else None),
            ensemble=dict(member_count=len(members), member_scores=[p.tolist() for p in members],
                agreement=float(np.mean([int(p.argmax()) == winner for p in members])) if len(members)>1 else None),
            input_policy='single_dermoscopic_duplicated', metadata=dict(age=age, sex=sex, site=site or 'unknown'), tta=self.settings.tta,
            input_hash=input_hash,
            checkpoint_epochs=[int(c['epoch']) for c in self.states],
            elapsed_ms=round((time.perf_counter()-start)*1000),
            limitations=['Single-image adaptation has not been validated against paired-view training.'] +
                ([] if self.calibration else ['Class scores are not calibrated clinical risk.']) +
                (['Body site was encoded as unknown.'] if site in ('unknown', '', None) else []),
            unavailable=['clinical_next_step'],
            capabilities=dict(xai=['integrated_gradients', 'metadata_shapley'],
                ood='active', image_quality='active',
                grad_cam='not_implemented', shap='not_implemented', attention='not_implemented'), persistence='not_saved')

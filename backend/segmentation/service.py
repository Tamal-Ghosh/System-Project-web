"""Optional nnU-Net v2 RGB dermoscopy adapter. Never substitutes untrained masks."""
import base64
import hashlib
import importlib.util
import io
import json
import os
import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image

MAX_SEGMENTATION_PIXELS = 4_000_000

class SegmentationUnavailable(RuntimeError):
    pass

class SegmentationBusy(RuntimeError):
    pass

def rgb_array(image):
    # NaturalImage2DIO convention: RGB channels, singleton z, height, width.
    return np.asarray(image.convert('RGB'), dtype=np.float32).transpose(2, 0, 1)[:, None]

def encode_mask(mask):
    stream = io.BytesIO()
    Image.fromarray(mask.astype(np.uint8) * 255).save(stream, format='PNG')
    return base64.b64encode(stream.getvalue()).decode('ascii')

def describe_mask(mask):
    yy, xx = np.nonzero(mask)
    return {
        'area_pixels': int(mask.sum()),
        'area_fraction': float(mask.mean()),
        'bounding_box': None if not len(xx) else {
            'x': int(xx.min()), 'y': int(yy.min()),
            'width': int(xx.max()-xx.min()+1), 'height': int(yy.max()-yy.min()+1),
        },
        'touches_border': bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any()),
    }

class NnUNetService:
    def __init__(self, folder=None, predictor_factory=None):
        configured = folder if folder is not None else os.environ.get('SEGMENTATION_MODEL_DIR', '')
        self.folder = Path(configured) if configured else None
        self._factory = predictor_factory
        self._predictor = None
        self._manifest = None
        self._gate = threading.Lock()

    def status(self):
        if self.folder is None:
            return {'status': 'unavailable', 'reason': 'Lesion-trained nnU-Net weights are not configured.'}
        if not all((self.folder / f).is_file() for f in ('dataset.json', 'plans.json', 'segmentation.json')):
            return {'status': 'unavailable', 'reason': 'The segmentation model bundle is incomplete.'}
        if self._factory is None and importlib.util.find_spec('nnunetv2') is None:
            return {'status': 'unavailable', 'reason': 'Install the optional nnU-Net segmentation runtime.'}
        return {'status': 'ready' if self._predictor is not None else 'configured',
                'reason': 'Model loaded.' if self._predictor is not None else 'Bundle configured; validated on first inference.'}

    def _load(self):
        if self._predictor is not None:
            return
        if self.status()['status'] == 'unavailable':
            raise SegmentationUnavailable(self.status()['reason'])
        try:
            dataset = json.loads((self.folder/'dataset.json').read_text(encoding='utf-8'))
            plans = json.loads((self.folder/'plans.json').read_text(encoding='utf-8'))
            manifest = json.loads((self.folder/'segmentation.json').read_text(encoding='utf-8'))
            if dataset.get('labels') != {'background': 0, 'lesion': 1}:
                raise ValueError('Expected binary background/lesion labels.')
            if dataset.get('channel_names') != {'0': 'R', '1': 'G', '2': 'B'}:
                raise ValueError('Expected three RGB channels.')
            if plans.get('image_reader_writer') != 'NaturalImage2DIO':
                raise ValueError('Expected NaturalImage2DIO preprocessing.')
            if manifest.get('task') != 'dermoscopic_lesion_boundary' or manifest.get('configuration') != '2d':
                raise ValueError('Expected a dermoscopic 2D lesion model.')
            if not isinstance(manifest.get('model_version'), str) or not manifest['model_version'].strip():
                raise ValueError('Model version is required.')
            folds = manifest.get('folds')
            if not isinstance(folds, list) or not folds or any(type(f) is not int or f not in range(5) for f in folds) or len(set(folds)) != len(folds):
                raise ValueError('Choose explicit, unique folds 0–4.')
            checkpoint = manifest.get('checkpoint', 'checkpoint_final.pth')
            if checkpoint not in ('checkpoint_final.pth', 'checkpoint_final.safetensors'):
                raise ValueError('Only final checkpoints are supported.')
            checksums = manifest.get('checkpoint_sha256', {})
            for fold in folds:
                filename = self.folder / f'fold_{fold}' / checkpoint
                expected = checksums.get(str(fold), '')
                if len(expected) != 64:
                    raise ValueError('Checkpoint SHA256 is required for each fold.')
                with filename.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if digest != expected:
                    raise ValueError('Segmentation checkpoint checksum mismatch.')
            if self._factory is None:
                import torch
                from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
                device = os.environ.get('SEGMENTATION_DEVICE', 'cpu')
                if device not in ('cpu', 'cuda') or (device == 'cuda' and not torch.cuda.is_available()):
                    raise ValueError('Requested segmentation device is unavailable.')
                predictor = nnUNetPredictor(device=torch.device(device), use_mirroring=True,
                    perform_everything_on_device=device == 'cuda', allow_tqdm=False)
            else:
                predictor = self._factory()
            predictor.initialize_from_trained_model_folder(str(self.folder), use_folds=tuple(folds), checkpoint_name=checkpoint)
            if len(predictor.configuration_manager.patch_size) != 2:
                raise ValueError('Segmentation must use a 2D configuration.')
            self._manifest, self._predictor = manifest, predictor
        except (OSError, ValueError, KeyError, ImportError, RuntimeError) as exc:
            raise SegmentationUnavailable('The lesion segmentation bundle could not be loaded. Check the server configuration.') from exc

    def predict(self, image, input_hash):
        if image.width * image.height > MAX_SEGMENTATION_PIXELS:
            raise ValueError('Segmentation supports images up to 4 million pixels; resize a copy before upload.')
        if not self._gate.acquire(blocking=False):
            raise SegmentationBusy('Segmentation is busy. Please retry when the current request finishes.')
        try:
            started = time.monotonic()
            self._load()
            mask = np.asarray(self._predictor.predict_single_npy_array(rgb_array(image), {'spacing': (999, 1, 1)}))
            if mask.shape != (1, image.height, image.width) or not np.isin(mask, [0, 1]).all():
                raise RuntimeError('Segmentation returned an invalid label map.')
            mask = mask[0].astype(bool)
            return {'status': 'ok', 'method': 'nnunetv2', 'model_version': self._manifest['model_version'],
                    'input_hash': input_hash, 'width': image.width, 'height': image.height,
                    'mask_png': encode_mask(mask), **describe_mask(mask),
                    'elapsed_ms': round((time.monotonic()-started)*1000),
                    'review_required': True,
                    'limitations': ['Boundary estimate requires clinician review.',
                                    'Pixel area is not a measurement in millimetres.',
                                    'Classification is unchanged; the mask is not diagnostic evidence.']}
        finally:
            self._gate.release()

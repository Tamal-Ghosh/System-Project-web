"""Official SAM 2.1 doctor-guided image inference. Not a validated clinical lesion detector."""
import hashlib
import importlib.util
import json
import os
import threading
import time
from pathlib import Path
import numpy as np
import torch
from .service import MAX_SEGMENTATION_PIXELS, SegmentationUnavailable, SegmentationBusy, encode_mask, describe_mask
from .prompt import validate_prompt

NOTICE='Doctor-guided boundary draft. Clinical accuracy and benefit to classification have not been evaluated; review before use.'
SOURCE_REVISION='2b90b9f5ceec907a1c18123530e92e794ad901a4'

class SAM2Service:
    method='sam2'
    requires_prompt=True
    def __init__(self,folder=None,predictor_factory=None):
        configured=folder if folder is not None else os.getenv('SEGMENTATION_MODEL_DIR','')
        self.folder=Path(configured) if configured else None
        self._predictor=None;self._metadata=None;self._gate=threading.Lock();self._factory=predictor_factory
    def status(self):
        available=self.folder is not None and all((self.folder/name).is_file() for name in ('segmentation.json','sam2.1_hiera_tiny.pt'))
        if available and self._factory is None and importlib.util.find_spec('sam2') is None:
            available=False
        return {'method':self.method,'requires_prompt':True,'status':('ready' if self._predictor is not None else 'configured') if available else 'unavailable',
                'reason':'SAM 2.1 ready for a doctor-selected rectangle.' if available else 'Official SAM 2.1 runtime or checkpoint is not configured.',
                'notice':NOTICE,'clinical_validation_status':'not_evaluated','anatomical_conditioning':False}
    def _load(self):
        if self._predictor is not None:return
        if self.status()['status']=='unavailable':raise SegmentationUnavailable(self.status()['reason'])
        try:
            metadata=json.loads((self.folder/'segmentation.json').read_text(encoding='utf-8'))
            if metadata.get('engine')!='sam2' or metadata.get('config')!='configs/sam2.1/sam2.1_hiera_t.yaml' or metadata.get('source_revision')!=SOURCE_REVISION:
                raise ValueError('Unsupported SAM model bundle.')
            if metadata.get('checkpoint')!='sam2.1_hiera_tiny.pt' or not metadata.get('model_version'):raise ValueError('Invalid checkpoint metadata.')
            checkpoint=self.folder/'sam2.1_hiera_tiny.pt'
            with checkpoint.open('rb') as stream:checksum=hashlib.file_digest(stream,'sha256').hexdigest()
            if checksum!=metadata.get('checkpoint_sha256'):raise ValueError('Official checkpoint checksum mismatch.')
            if self._factory:
                predictor=self._factory()
            else:
                from sam2.build_sam import build_sam2
                from sam2.sam2_image_predictor import SAM2ImagePredictor
                # All image transforms, logit threshold and stability fallback are official defaults.
                model=build_sam2(metadata['config'],str(checkpoint),device='cpu')
                predictor=SAM2ImagePredictor(model)
            self._predictor,self._metadata=predictor,metadata
        except (OSError,ValueError,KeyError,ImportError,RuntimeError) as exc:
            raise SegmentationUnavailable('Official SAM 2.1 could not be loaded; verify the pinned runtime and checkpoint.') from exc
    def unload(self):
        self._predictor=None;self._metadata=None

    def predict(self,image,input_hash,box=None,image_type=None,site='unknown'):
        prompt=validate_prompt(image,box,image_type,site)
        if image.width*image.height>MAX_SEGMENTATION_PIXELS:raise ValueError('Segmentation supports images up to 4 million pixels.')
        if not self._gate.acquire(blocking=False):raise SegmentationBusy('Segmentation is busy. Please retry shortly.')
        try:
            started=time.monotonic();self._load()
            try:
                with torch.inference_mode():
                    self._predictor.set_image(np.array(image.convert('RGB'),copy=True))
                    masks,_,_=self._predictor.predict(box=np.asarray(prompt['box'],dtype=np.float32),multimask_output=False)
                masks=np.asarray(masks)
                if masks.shape!=(1,image.height,image.width) or not np.isfinite(masks).all() or not np.isin(masks,[0,1]).all():raise RuntimeError('Invalid SAM mask shape or labels.')
                mask=masks[0].astype(bool)
            finally:
                self._predictor.reset_predictor()
            x1,y1,x2,y2=prompt['box'];inside=np.zeros_like(mask)
            inside[int(np.floor(y1)):int(np.ceil(y2)),int(np.floor(x1)):int(np.ceil(x2))]=True
            outside=int((mask & ~inside).sum())
            return {'status':'ok','method':self.method,'model_version':self._metadata['model_version'],'input_hash':input_hash,
                    'width':image.width,'height':image.height,'mask_png':encode_mask(mask),**describe_mask(mask),
                    'prompt_box':prompt['box'],'image_type':image_type,'anatomical_site':site,'anatomical_conditioning':False,
                    'outside_prompt_pixels':outside,'clinical_validation_status':'not_evaluated','review_required':True,
                    'preprocessing_status':'official_sam2_image_predictor_defaults','source_revision':SOURCE_REVISION,
                    'notice':NOTICE,'elapsed_ms':round((time.monotonic()-started)*1000),
                    'limitations':['The model segments the doctor-selected region; it does not diagnose a lesion.',
                                    'Anatomical site is audit metadata, not a model input.',
                                    'No independent clinical or dermoscopic accuracy evaluation has been performed.',
                                    'No improvement to classification has been demonstrated.','Pixel area is not a calibrated physical measurement.']}
        finally:self._gate.release()

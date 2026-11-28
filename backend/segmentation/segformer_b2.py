"""Pinned SMP SegFormer MiT-B2 real-only research checkpoint; offline full-image masks."""
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import cv2
import numpy as np
import torch
from .prompt import validate_context
from .service import MAX_SEGMENTATION_PIXELS, SegmentationBusy, SegmentationUnavailable, encode_mask, describe_mask

REVISION='19ca826598cb59a6ac5b18b6a5636ba9298851b5'
CHECKPOINT_SHA256='d5a92fa31296a4f7c32e87cdf84683119d07dc64410253103bfa285aacb93f87'
SOURCE_REVISION='d3d3195f13b02366cbc1332cbb57d7ca9234b7a7'
NOTICE='Research mask: trained on ISIC dermoscopic images; clinical-photo accuracy and clinical use are not validated. Review the boundary.'

def prepare_pixels(image):
    # Publisher: preprocess._process INTER_AREA RGB resize, followed by A.Normalize.
    pixels=cv2.resize(np.asarray(image.convert('RGB')),(512,512),interpolation=cv2.INTER_AREA).astype(np.float32)
    mean=np.array([.485,.456,.406],np.float32)*255
    scale=1/(np.array([.229,.224,.225],np.float32)*255)
    return torch.from_numpy(((pixels-mean)*scale).transpose(2,0,1).copy()).unsqueeze(0)

def restore_mask(logits,size):
    if not isinstance(logits,torch.Tensor) or tuple(logits.shape)!=(1,1,512,512) or not torch.isfinite(logits).all():
        raise ValueError('SegFormer returned invalid logits.')
    # Publisher native protocol resizes probabilities, not logits or a binary mask.
    probabilities=logits.float().sigmoid()[0,0].cpu().numpy()
    return cv2.resize(probabilities,size,interpolation=cv2.INTER_LINEAR)>=.7

class SegFormerB2Service:
    method='segformer_b2'
    requires_prompt=False
    requires_image_type=True
    allows_unspecified_type=True
    def __init__(self,folder=None,model_factory=None):
        configured=folder if folder is not None else os.getenv('SEGMENTATION_MODEL_DIR','')
        self.folder=Path(configured) if configured else None
        self._model=None;self._gate=threading.Lock();self._factory=model_factory
    def status(self):
        configured=self.folder is not None and (self.folder/'best.pt').is_file() and (self.folder/'segmentation.json').is_file()
        return {'method':self.method,'status':('ready' if self._model is not None else 'configured') if configured else 'unavailable',
                'reason':'SegFormer MiT-B2 full-image mask configured.' if configured else 'The pinned SegFormer MiT-B2 bundle is missing.',
                'requires_prompt':False,'notice':NOTICE,'clinical_validation_status':'not_evaluated'}
    def _load(self):
        if self._model is not None:return
        try:
            if self.status()['status']=='unavailable':raise ValueError('Missing bundle.')
            manifest=json.loads((self.folder/'segmentation.json').read_text(encoding='utf-8'))
            if manifest.get('source_revision')!=REVISION or manifest.get('checkpoint_sha256')!=CHECKPOINT_SHA256 or manifest.get('threshold')!=.7 or manifest.get('input_size')!=[512,512]:raise ValueError('Unexpected bundle manifest.')
            with (self.folder/'best.pt').open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if digest!=CHECKPOINT_SHA256:raise ValueError('Checkpoint checksum mismatch.')
            checkpoint=torch.load(self.folder/'best.pt',map_location='cpu',weights_only=True)
            cfg=checkpoint['cfg']
            if cfg['model']!='segformer_mitb2' or cfg['data']['img_size']!=512 or checkpoint['epoch']!=21 or checkpoint['which']!='raw':raise ValueError('Unexpected checkpoint configuration.')
            state=checkpoint['model']
            if not state or not all(isinstance(value,torch.Tensor) and torch.isfinite(value).all() for value in state.values()):raise ValueError('Invalid state dictionary.')
            if self._factory:model=self._factory()
            else:
                import segmentation_models_pytorch as smp
                model=smp.Segformer(encoder_name='mit_b2',encoder_weights=None,in_channels=3,classes=1)
            # Original registry wraps SMP in SMPWrapper.model. No random or partial loading.
            if not all(key.startswith('model.') for key in state):raise ValueError('Unexpected checkpoint key namespace.')
            model.load_state_dict({key[len('model.'):]:value for key,value in state.items()},strict=True)
            self._model=model.eval()
        except (OSError,ValueError,KeyError,RuntimeError,ImportError,TypeError) as exc:
            raise SegmentationUnavailable('SegFormer MiT-B2 could not load. Check the pinned bundle and runtime.') from exc
    def predict(self,image,input_hash,image_type='unspecified',site='unknown'):
        validate_context(image_type,site,allow_unspecified=True)
        if image.width*image.height>MAX_SEGMENTATION_PIXELS:raise ValueError('Segmentation supports up to 4 million pixels.')
        if not self._gate.acquire(blocking=False):raise SegmentationBusy('Segmentation is busy. Please retry shortly.')
        try:
            started=time.monotonic();self._load()
            with torch.inference_mode():mask=restore_mask(self._model(prepare_pixels(image)),image.size)
            return {'status':'ok','method':self.method,'model_version':'segformer-mit-b2-real-'+CHECKPOINT_SHA256[:12],
                'input_hash':input_hash,'width':image.width,'height':image.height,'mask_png':encode_mask(mask),**describe_mask(mask),
                'threshold':.7,'threshold_source':'publisher_validation_split','preprocessing_status':'publisher_recipe_rgb_area512_imagenet_probability_linear_native',
                'source_revision':REVISION,'code_revision':SOURCE_REVISION,'checkpoint_sha256':CHECKPOINT_SHA256,
                'proposal_source':'full_image_segmentation','image_type':image_type,'anatomical_site':site,'anatomical_conditioning':False,
                'clinical_validation_status':'not_evaluated','training_domain':'dermoscopic','input_domain_supported':None if image_type=='unspecified' else image_type=='dermoscopic',
                'notice':NOTICE,'review_required':True,'elapsed_ms':round((time.monotonic()-started)*1000),
                'limitations':[NOTICE,'Clinical photographs are outside the reported ISIC evaluation domain.' if image_type=='clinical' else 'Publisher benchmark metrics have not been independently reproduced here.',
                    'No anatomical conditioning or disease diagnosis.','No automatic classification changes.','Pixel area is not a calibrated physical measurement.',
                    'CPU float32 inference differs from the publisher GPU bfloat16 evaluation runtime.']}
        finally:self._gate.release()

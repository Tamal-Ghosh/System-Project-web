"""Offline SegFormer-B0 mask adapter. No Hub requests or classifier dependency changes."""
import hashlib
import json
import math
import os
import threading
import time
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from .service import MAX_SEGMENTATION_PIXELS, SegmentationUnavailable, SegmentationBusy, encode_mask, describe_mask

EXPERIMENTAL_NOTICE='Experimental mask: training normalization and threshold were not published. ImageNet normalization and a 0.5 threshold are provisional; independent lesion evaluation is pending.'

def prepare_pixels(image, metadata):
    pixels=np.asarray(image.convert('RGB').resize(tuple(metadata['input_size']),Image.Resampling.BILINEAR),dtype=np.float32)/255
    mean=np.asarray(metadata['mean'],dtype=np.float32);std=np.asarray(metadata['std'],dtype=np.float32)
    return torch.from_numpy(((pixels-mean)/std).transpose(2,0,1).copy()).unsqueeze(0)

def logits_to_mask(logits, size, threshold):
    if not isinstance(logits,torch.Tensor) or logits.ndim!=4 or logits.shape[:2]!=(1,1) or not torch.isfinite(logits).all():
        raise ValueError('SegFormer returned invalid logits.')
    restored=torch.nn.functional.interpolate(logits.float(),size=(size[1],size[0]),mode='bilinear',align_corners=False)
    return (restored.sigmoid()[0,0]>=threshold).cpu().numpy()

class SegFormerService:
    method='segformer'
    def __init__(self,folder=None,loader=None):
        configured=folder if folder is not None else os.getenv('SEGMENTATION_MODEL_DIR','')
        self.folder=Path(configured) if configured else None
        self._model=None;self._metadata=None;self._gate=threading.Lock();self._loader=loader or torch.jit.load
    def status(self):
        available=self.folder is not None and (self.folder/'segmentation.json').is_file() and (self.folder/'segformer_b0.pt').is_file()
        return {'method':self.method,'status':('ready' if self._model is not None else 'configured') if available else 'unavailable',
                'reason':('SegFormer weights loaded.' if self._model is not None else 'SegFormer configured; integrity checked on first inference.') if available else 'The trained SegFormer bundle is not configured.',
                'notice':EXPERIMENTAL_NOTICE}
    def _load(self):
        if self._model is not None:return
        if self.status()['status']=='unavailable':raise SegmentationUnavailable(self.status()['reason'])
        try:
            metadata=json.loads((self.folder/'segmentation.json').read_text(encoding='utf-8'))
            if metadata.get('engine')!='segformer' or metadata.get('architecture')!='mit-b0' or metadata.get('artifact')!='segformer_b0.pt':raise ValueError('Unsupported model bundle.')
            if metadata.get('input_size')!=[256,256]:raise ValueError('Expected fixed 256 by 256 input.')
            for name in ('mean','std'):
                values=metadata.get(name)
                if not isinstance(values,list) or len(values)!=3 or any(type(x) not in (float,int) or not math.isfinite(x) for x in values):raise ValueError('Invalid normalization.')
            if any(x<=0 for x in metadata['std']):raise ValueError('Invalid normalization scale.')
            if type(metadata.get('threshold')) not in (int,float) or not 0<metadata['threshold']<1:raise ValueError('Invalid mask threshold.')
            if not isinstance(metadata.get('preprocessing_status'),str) or not metadata['preprocessing_status']:raise ValueError('Preprocessing provenance missing.')
            if not isinstance(metadata.get('model_version'),str) or not metadata['model_version']:raise ValueError('Model version missing.')
            artifact=self.folder/'segformer_b0.pt'
            with artifact.open('rb') as stream: checksum=hashlib.file_digest(stream,'sha256').hexdigest()
            if checksum!=metadata.get('artifact_sha256'):raise ValueError('SegFormer artifact checksum mismatch.')
            device=os.getenv('SEGMENTATION_DEVICE','cpu')
            if device not in ('cpu','cuda') or (device=='cuda' and not torch.cuda.is_available()):raise ValueError('Segmentation device is unavailable.')
            self._device=torch.device(device)
            model=self._loader(str(artifact),map_location=self._device).eval()
            self._model,self._metadata=model,metadata
        except (OSError,ValueError,KeyError,RuntimeError) as exc:
            raise SegmentationUnavailable('SegFormer bundle could not be loaded; verify its manifest and artifact checksum.') from exc
    def predict(self,image,input_hash):
        if image.width*image.height>MAX_SEGMENTATION_PIXELS:raise ValueError('Segmentation supports images up to 4 million pixels; resize a copy before upload.')
        if not self._gate.acquire(blocking=False):raise SegmentationBusy('Segmentation is busy. Please retry shortly.')
        try:
            start=time.monotonic();self._load()
            with torch.inference_mode():
                logits=self._model(prepare_pixels(image,self._metadata).to(self._device))
                mask=logits_to_mask(logits,image.size,self._metadata['threshold'])
            return {'status':'ok','method':self.method,'model_version':self._metadata['model_version'],'input_hash':input_hash,
                    'width':image.width,'height':image.height,'mask_png':encode_mask(mask),**describe_mask(mask),
                    'threshold':self._metadata['threshold'],'preprocessing_status':self._metadata['preprocessing_status'],
                    'notice':EXPERIMENTAL_NOTICE,'review_required':True,'elapsed_ms':round((time.monotonic()-start)*1000),
                    'limitations':[EXPERIMENTAL_NOTICE,'Boundary estimates require clinician review.','Pixel area is not size in millimetres.','Classification is unchanged; the mask is not diagnostic evidence.']}
        finally:self._gate.release()

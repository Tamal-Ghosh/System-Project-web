"""Offline official Grounding DINO candidate localization. Scores are not clinical probabilities."""
import ctypes
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import torch
from .service import SegmentationUnavailable

def release_memory():
    gc.collect()
    if sys.platform.startswith('linux'):
        try:ctypes.CDLL(None).malloc_trim(0)
        except (AttributeError,OSError):pass

class GroundingDetector:
    def __init__(self,folder=None):
        configured=folder if folder is not None else os.getenv('DETECTOR_MODEL_DIR','')
        self.folder=Path(configured) if configured else None
        self._model=None;self._processor=None;self._metadata=None
    def status(self):
        available=self.folder is not None and (self.folder/'detector.json').is_file() and (self.folder/'model.safetensors').is_file()
        return {'status':'configured' if available else 'unavailable','reason':'Automatic detector configured.' if available else 'The official automatic detector bundle is missing.'}
    def _load(self):
        try:
            if self.status()['status']=='unavailable':raise ValueError('Detector not configured.')
            metadata=json.loads((self.folder/'detector.json').read_text(encoding='utf-8'))
            if metadata.get('detector')!='IDEA-Research/grounding-dino-tiny' or metadata.get('revision')!='a2bb814dd30d776dcf7e30523b00659f4f141c71':raise ValueError('Unreviewed detector revision.')
            if metadata.get('query')!='skin lesion.' or metadata.get('box_threshold')!=.4 or metadata.get('text_threshold')!=.3:raise ValueError('Detector policy differs from the recorded reference settings.')
            required={'config.json','preprocessor_config.json','tokenizer_config.json','special_tokens_map.json','added_tokens.json','tokenizer.json','vocab.txt','model.safetensors'}
            if set(metadata['files_sha256'])!=required:raise ValueError('Incomplete detector checksum manifest.')
            for name,expected in metadata['files_sha256'].items():
                if name not in ('config.json','preprocessor_config.json','tokenizer_config.json','special_tokens_map.json','added_tokens.json','tokenizer.json','vocab.txt','model.safetensors'):raise ValueError('Invalid detector file.')
                with (self.folder/name).open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                if digest!=expected:raise ValueError('Detector checksum mismatch.')
            from transformers import AutoProcessor,AutoModelForZeroShotObjectDetection
            if self._processor is None:self._processor=AutoProcessor.from_pretrained(str(self.folder),local_files_only=True,trust_remote_code=False)
            model,info=AutoModelForZeroShotObjectDetection.from_pretrained(str(self.folder),local_files_only=True,trust_remote_code=False,output_loading_info=True)
            if any(info.get(key) for key in ('missing_keys','unexpected_keys','mismatched_keys','error_msgs')):raise ValueError('Detector weights did not fully match the official architecture.')
            self._model=model.eval();self._metadata=metadata
        except (OSError,ValueError,KeyError,ImportError,RuntimeError) as exc:
            self.unload()
            raise SegmentationUnavailable('Automatic detector could not load. Check its pinned files and runtime.') from exc
    def unload(self):
        self._model=None;release_memory()
    def detect(self,image):
        self._load()
        try:
            with torch.inference_mode():
                inputs=self._processor(images=image.convert('RGB'),text=self._metadata['query'],return_tensors='pt')
                outputs=self._model(**inputs)
                found=self._processor.post_process_grounded_object_detection(outputs,inputs.input_ids,threshold=.4,text_threshold=.3,target_sizes=[image.size[::-1]])[0]
            candidates=[]
            labels=found.get('text_labels',found.get('labels',[]))
            for box,score,label in zip(found['boxes'].cpu().tolist(),found['scores'].cpu().tolist(),labels):
                candidates.append({'box':box,'score':score,'label':str(label)})
            del inputs,outputs,found
            return candidates
        finally:self.unload()

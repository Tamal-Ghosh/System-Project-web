"""Automatic candidate localization followed by SAM; no full-frame or manual-box fallback."""
import math
import threading
import time
from .detector import GroundingDetector,release_memory
from .sam2_service import SAM2Service
from .prompt import validate_context,validate_prompt
from .service import MAX_SEGMENTATION_PIXELS,SegmentationBusy

NOTICE='Automatic candidate mask, not a diagnosis. Detection and boundary accuracy are not clinically validated; review before use.'

class AutomaticSegmentationService:
    method='grounded_sam2'
    requires_prompt=False
    requires_image_type=True
    def __init__(self,detector=None,segmenter=None):
        self.detector=detector or GroundingDetector();self.segmenter=segmenter or SAM2Service();self._gate=threading.Lock()
    def status(self):
        detector,sam=self.detector.status(),self.segmenter.status()
        available=detector['status']!='unavailable' and sam['status']!='unavailable'
        return {'method':self.method,'status':'configured' if available else 'unavailable','requires_prompt':False,'can_abstain':True,
                'reason':'Automatic detection and segmentation ready.' if available else (detector['reason'] if detector['status']=='unavailable' else sam['reason']),
                'notice':NOTICE,'clinical_validation_status':'not_evaluated','anatomical_conditioning':False}
    def predict(self,image,input_hash,image_type=None,site='unknown'):
        validate_context(image_type,site)
        if image.width*image.height>MAX_SEGMENTATION_PIXELS:raise ValueError('Segmentation supports images up to 4 million pixels.')
        if not self._gate.acquire(blocking=False):raise SegmentationBusy('Segmentation is busy. Please retry shortly.')
        try:
            started=time.monotonic()
            # Keep only one extra model resident at a time on CPU machines.
            self.segmenter.unload();release_memory()
            candidates=self.detector.detect(image)
            base={'method':self.method,'input_hash':input_hash,'width':image.width,'height':image.height,
                  'image_type':image_type,'anatomical_site':site,'anatomical_conditioning':False,
                  'clinical_validation_status':'not_evaluated','notice':NOTICE,
                  'detector':{'model':'IDEA-Research/grounding-dino-tiny','revision':'a2bb814dd30d776dcf7e30523b00659f4f141c71',
                              'query':'skin lesion.','box_threshold':.4,'text_threshold':.3,'score_is_clinical_probability':False},
                  'candidate_count':len(candidates)}
            if not candidates:
                return {**base,'status':'no_target','reason':'No candidate lesion region was identified. No mask was generated. This does not rule out a skin condition.','elapsed_ms':round((time.monotonic()-started)*1000)}
            if len(candidates)>1:
                return {**base,'status':'ambiguous','reason':'Several possible target regions were detected. No automatic mask was selected. Try a closer single-lesion image or review the image manually.','elapsed_ms':round((time.monotonic()-started)*1000)}
            candidate=candidates[0]
            try:
                score=candidate['score'];box=candidate['box']
                if type(score) not in (int,float) or not math.isfinite(score) or not .4<score<=1:raise ValueError('Invalid detector score.')
                validate_prompt(image,box,image_type,site)
                if box==[0,0,image.width,image.height]:raise ValueError('Full frame does not localize the target.')
            except (ValueError,KeyError,TypeError):
                return {**base,'status':'no_target','reason':'The candidate region could not be localized safely within the image. No mask was generated.','elapsed_ms':round((time.monotonic()-started)*1000)}
            result=self.segmenter.predict(image,input_hash,box=box,image_type=image_type,site=site)
            return {**result,**base,'status':'ok','proposal_source':'automatic_detector','detected_box':box,
                    'detector_score':score,'elapsed_ms':round((time.monotonic()-started)*1000),
                    'limitations':[NOTICE,'General open-vocabulary localization is not a skin-disease diagnosis.',
                                    'Reference detection thresholds are not fitted or calibrated for this clinical population.',*[item for item in result.get('limitations',[]) if 'doctor-selected' not in item]]}
        finally:self._gate.release()

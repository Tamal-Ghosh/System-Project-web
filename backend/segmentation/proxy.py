"""Keep nnU-Net dependencies out of the classifier process in Docker."""
import io
import json
import httpx
from .service import SegmentationBusy, SegmentationUnavailable

class RemoteSegmentationService:
    requires_prompt = False
    requires_image_type = True
    allows_unspecified_type = True
    def __init__(self, url):
        self.url = url.rstrip('/')
    def status(self):
        try:
            response = httpx.get(self.url+'/api/v1/segmentation/status', timeout=3)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            return {'status':'unavailable','reason':'The segmentation runtime is not reachable.'}
    def predict(self, image, input_hash, **options):
        stream=io.BytesIO();image.save(stream,format='PNG')
        data={key:(json.dumps(value) if key=='box' else str(value)) for key,value in options.items()}
        try:
            response=httpx.post(self.url+'/api/v1/segmentation',files={'image':('lesion.png',stream.getvalue(),'image/png')},data=data,timeout=httpx.Timeout(600,connect=5))
            if response.status_code==409:
                raise SegmentationBusy('Segmentation is busy. Please retry shortly.')
            if response.status_code==422:
                raise ValueError('Segmentation rejected the image or prompt. Verify the image type and image dimensions.')
            response.raise_for_status();result=response.json()
            if result.get('width')!=image.width or result.get('height')!=image.height or result.get('status') not in ('ok','no_target','ambiguous'):
                raise ValueError('The segmentation result does not match this image.')
            result['input_hash']=input_hash
            return result
        except (httpx.HTTPError, ValueError) as exc:
            raise SegmentationUnavailable('Segmentation is unavailable. Check its runtime and trained model bundle.') from exc

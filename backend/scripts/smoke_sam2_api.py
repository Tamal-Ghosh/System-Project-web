"""Test real official SAM request/prompt/geometry contract, not medical accuracy."""
import base64
import io
import json
import httpx
import numpy as np
from PIL import Image,ImageDraw

def main():
    image=Image.new('RGB',(420,280),(207,164,141));ImageDraw.Draw(image).ellipse((130,70,290,210),fill=(71,44,35))
    stream=io.BytesIO();image.save(stream,format='PNG');files={'image':('synthetic.png',stream.getvalue(),'image/png')}
    with httpx.Client(timeout=120) as client:
        base='http://frontend:5173/api/v1/segmentation'
        assert client.post(base,files=files).status_code==422
        response=client.post(base,files=files,data={'box':'[110,50,310,230]','image_type':'clinical','site':'unknown'})
        response.raise_for_status();result=response.json()
        assert result['method']=='sam2' and result['prompt_box']==[110,50,310,230] and result['review_required']
        assert result['clinical_validation_status']=='not_evaluated' and result['anatomical_conditioning'] is False
        with Image.open(io.BytesIO(base64.b64decode(result['mask_png']))) as mask:
            assert mask.size==image.size and np.isin(np.asarray(mask),[0,255]).all()
        invalid=client.post(base,files=files,data={'box':'[-1,50,310,230]','image_type':'clinical'})
        assert invalid.status_code==422
        print(json.dumps({'result':'PASS','model_version':result['model_version'],'mask_pixels':result['area_pixels'],'elapsed_ms':result['elapsed_ms'],'clinical_validation':'not_evaluated'}))
        print('Explicit prompt required; invalid coordinates rejected; official-model original-size binary mask and provenance verified. Synthetic input only.')

if __name__=='__main__':main()

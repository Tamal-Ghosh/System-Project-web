"""End-to-end real-checkpoint smoke test with synthetic input only; no clinical accuracy claim."""
import argparse
import base64
import io
import json
import httpx
import numpy as np
from PIL import Image, ImageDraw

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://frontend:5173');args=parser.parse_args()
    image=Image.new('RGB',(420,280),(207,164,141));ImageDraw.Draw(image).ellipse((130,70,290,210),fill=(71,44,35))
    stream=io.BytesIO();image.save(stream,format='PNG')
    with httpx.Client(timeout=60) as client:
        status=client.get(args.url+'/api/v1/segmentation/status');status.raise_for_status()
        assert status.json()['method']=='segformer'
        result=client.post(args.url+'/api/v1/segmentation',files={'image':('synthetic-test.png',stream.getvalue(),'image/png')})
        result.raise_for_status();payload=result.json()
        assert payload['status']=='ok' and payload['method']=='segformer' and payload['review_required']
        assert (payload['width'],payload['height'])==image.size and payload['threshold']==.5
        assert 'experimental' in payload['preprocessing_status'] and 'provisional' in payload['notice']
        with Image.open(io.BytesIO(base64.b64decode(payload['mask_png']))) as mask:
            assert mask.size==image.size and np.isin(np.asarray(mask),[0,255]).all()
        invalid=client.post(args.url+'/api/v1/segmentation',files={'image':('invalid.png',b'not-image','image/png')})
        assert invalid.status_code==422
        assert client.get(args.url+'/api/v1/segmentation/status').json()['status']=='ready'
        print(json.dumps({'result':'PASS','model_version':payload['model_version'],'area_pixels':payload['area_pixels'],'elapsed_ms':payload['elapsed_ms'],'tests':'real checkpoint through frontend proxy, backend and sidecar; valid original-size binary mask; invalid image rejected; model readiness verified'}))
        print('Synthetic fixture only; no Dice/IoU accuracy measurement.')

if __name__=='__main__':main()

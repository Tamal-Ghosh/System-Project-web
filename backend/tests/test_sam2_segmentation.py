import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from segmentation.prompt import validate_prompt
from segmentation.sam2_service import SAM2Service,SOURCE_REVISION
from segmentation.service import SegmentationUnavailable,SegmentationBusy
from segmentation.routes import segmentation_router

class Predictor:
    def set_image(self,image):self.shape=image.shape;self.image=image
    def predict(self,box,multimask_output):
        self.box=box;assert multimask_output is False
        mask=np.zeros((1,*self.shape[:2]),dtype=bool);mask[0,3:8,4:10]=True
        return mask,np.array([.9]),None
    def reset_predictor(self):self.image=None;self.reset=True

class SAM2SegmentationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.image=Image.new('RGB',(16,12))
        self.checkpoint=self.root/'sam2.1_hiera_tiny.pt';self.checkpoint.write_bytes(b'synthetic test only')
        self.metadata={'engine':'sam2','config':'configs/sam2.1/sam2.1_hiera_t.yaml','source_revision':SOURCE_REVISION,
            'checkpoint':'sam2.1_hiera_tiny.pt','checkpoint_sha256':hashlib.sha256(b'synthetic test only').hexdigest(),'model_version':'synthetic'}
        (self.root/'segmentation.json').write_text(json.dumps(self.metadata));self.predictor=Predictor()
    def tearDown(self):self.tmp.cleanup()
    def service(self):return SAM2Service(self.root,lambda:self.predictor)
    def test_explicit_prompt_and_modality_required(self):
        for box,kind in [(None,'clinical'),([1,1,15,11],None),([1,1,15,11],'auto')]:
            with self.assertRaises(ValueError):self.service().predict(self.image,'hash',box=box,image_type=kind)
    def test_bad_coordinates_rejected_without_clamping(self):
        for box in ([-1,0,8,8],[0,0,17,8],[8,8,1,1],[1,1,1.5,4],[float('nan'),0,5,5],[True,0,5,5],'not-json'):
            with self.subTest(box=box):
                with self.assertRaises(ValueError):validate_prompt(self.image,box,'clinical')
    def test_site_is_recorded_not_model_conditioning(self):
        result=self.service().predict(self.image,'hash',box=[3,2,11,9],image_type='clinical',site='unknown')
        self.assertEqual(result['area_pixels'],30);self.assertFalse(result['anatomical_conditioning'])
        self.assertEqual(result['clinical_validation_status'],'not_evaluated');self.assertTrue(result['review_required'])
        self.assertEqual(result['prompt_box'],[3,2,11,9]);self.assertTrue(self.predictor.reset)
        self.assertIsNone(self.predictor.image);np.testing.assert_array_equal(self.predictor.box,[3,2,11,9])
    def test_mask_outside_prompt_is_reported_not_hidden(self):
        result=self.service().predict(self.image,'hash',box=[4,3,6,5],image_type='dermoscopic')
        self.assertGreater(result['outside_prompt_pixels'],0);self.assertEqual(result['area_pixels'],30)
    def test_invalid_checkpoint_fails_closed(self):
        self.checkpoint.write_bytes(b'corrupted')
        with self.assertRaises(SegmentationUnavailable):self.service().predict(self.image,'hash',box=[1,1,14,10],image_type='clinical')
    def test_busy(self):
        service=self.service();service._gate.acquire()
        with self.assertRaises(SegmentationBusy):service.predict(self.image,'hash',box=[1,1,14,10],image_type='clinical')
        service._gate.release()
    def test_predictor_state_cleared_on_error(self):
        with patch.object(self.predictor,'predict',side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):self.service().predict(self.image,'hash',box=[1,1,14,10],image_type='clinical')
        self.assertTrue(self.predictor.reset);self.assertIsNone(self.predictor.image)
    def test_api_requires_prompt_and_accepts_both_image_types(self):
        app=FastAPI();app.include_router(segmentation_router(self.service()))
        stream=io.BytesIO();self.image.save(stream,format='PNG');files={'image':('synthetic.png',stream.getvalue(),'image/png')}
        with TestClient(app) as client:
            self.assertEqual(client.post('/api/v1/segmentation',files=files).status_code,422)
            for image_type in ('clinical','dermoscopic'):
                response=client.post('/api/v1/segmentation',files=files,data={'box':'[1,1,14,10]','image_type':image_type,'site':'unknown'})
                self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['image_type'],image_type)
            self.assertTrue(client.get('/api/v1/segmentation/status').json()['requires_prompt'])
    def test_proxy_forwards_only_explicit_prompt(self):
        from types import SimpleNamespace
        from segmentation.proxy import RemoteSegmentationService
        response=SimpleNamespace(status_code=200,raise_for_status=lambda:None,json=lambda:{'status':'ok','width':16,'height':12})
        with patch('segmentation.proxy.httpx.post',return_value=response) as post:
            RemoteSegmentationService('http://internal').predict(self.image,'hash',box=[1,1,14,10],image_type='clinical',site='unknown')
            self.assertEqual(json.loads(post.call_args.kwargs['data']['box']),[1,1,14,10])
            self.assertEqual(post.call_args.kwargs['data']['image_type'],'clinical')

if __name__=='__main__':unittest.main()

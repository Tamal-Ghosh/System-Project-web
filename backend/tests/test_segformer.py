import base64
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from segmentation.segformer import SegFormerService, prepare_pixels, logits_to_mask
from segmentation.service import SegmentationUnavailable, SegmentationBusy
from segmentation.routes import segmentation_router

class Fixture(torch.nn.Module):
    def forward(self,pixels):return pixels[:,:1,::4,::4]*0+1

class SegFormerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        torch.jit.trace(Fixture(),torch.zeros(1,3,256,256)).save(str(self.root/'segformer_b0.pt'))
        with (self.root/'segformer_b0.pt').open('rb') as stream: checksum=hashlib.file_digest(stream,'sha256').hexdigest()
        self.metadata={'engine':'segformer','architecture':'mit-b0','artifact':'segformer_b0.pt','artifact_sha256':checksum,
            'model_version':'synthetic-fixture','input_size':[256,256],'mean':[.485,.456,.406],'std':[.229,.224,.225],
            'threshold':.5,'preprocessing_status':'experimental_defaults_not_confirmed_by_publisher'}
        self.write();self.image=Image.new('RGB',(91,43),'white')
    def tearDown(self):self.tmp.cleanup()
    def write(self):(self.root/'segmentation.json').write_text(json.dumps(self.metadata))
    def test_rgb_scaling_normalization_and_input_size(self):
        pixels=prepare_pixels(self.image,self.metadata)
        self.assertEqual(tuple(pixels.shape),(1,3,256,256))
        np.testing.assert_allclose(pixels[0,:,0,0].numpy(),(np.ones(3)-self.metadata['mean'])/self.metadata['std'],rtol=1e-6)
    def test_real_torchscript_load_original_size_and_disclosure(self):
        service=SegFormerService(self.root);result=service.predict(self.image,'hash')
        self.assertEqual(result['method'],'segformer');self.assertEqual(result['area_pixels'],91*43)
        self.assertEqual(result['input_hash'],'hash');self.assertEqual(result['threshold'],.5)
        self.assertIn('provisional',result['notice']);self.assertTrue(result['review_required'])
        with Image.open(io.BytesIO(base64.b64decode(result['mask_png']))) as mask:self.assertEqual(mask.size,self.image.size)
        self.assertEqual(service.status()['status'],'ready')
    def test_empty_mask_at_high_threshold(self):
        self.metadata['threshold']=.9;self.write()
        result=SegFormerService(self.root).predict(self.image,'hash')
        self.assertEqual(result['area_pixels'],0);self.assertIsNone(result['bounding_box'])
    def test_corrupt_artifact_never_loads(self):
        self.metadata['artifact_sha256']='0'*64;self.write()
        with self.assertRaises(SegmentationUnavailable):SegFormerService(self.root).predict(self.image,'hash')
    def test_invalid_preprocessing_is_rejected(self):
        for key,value in [('std',[0,1,1]),('mean',[float('nan'),0,0]),('threshold',0),('input_size',[512,512]),('artifact','../file.pt'),('preprocessing_status','')]:
            with self.subTest(key=key):
                saved=self.metadata[key];self.metadata[key]=value;self.write()
                with self.assertRaises(SegmentationUnavailable):SegFormerService(self.root).predict(self.image,'hash')
                self.metadata[key]=saved
    def test_missing_artifact_and_busy(self):
        self.assertEqual(SegFormerService('').status()['status'],'unavailable')
        service=SegFormerService(self.root);service._gate.acquire()
        with self.assertRaises(SegmentationBusy):service.predict(self.image,'hash')
        service._gate.release()
    def test_invalid_logits_and_original_size(self):
        mask=logits_to_mask(torch.ones(1,1,8,12),(91,43),.5)
        self.assertEqual(mask.shape,(43,91))
        for logits in (torch.zeros(1,2,8,8),torch.full((1,1,8,8),float('nan'))):
            with self.assertRaises(ValueError):logits_to_mask(logits,(91,43),.5)
    def test_provider_selection_and_api_response(self):
        with patch.dict('os.environ',{'SEGMENTATION_PROVIDER':'segformer','SEGMENTATION_MODEL_DIR':str(self.root),'SEGMENTATION_SERVICE_URL':''}):
            app=FastAPI();app.include_router(segmentation_router())
            stream=io.BytesIO();self.image.save(stream,format='PNG')
            with TestClient(app) as client:
                status=client.get('/api/v1/segmentation/status').json()
                self.assertEqual(status['method'],'segformer');self.assertIn('provisional',status['notice'])
                response=client.post('/api/v1/segmentation',files={'image':('test.png',stream.getvalue(),'image/png')})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['method'],'segformer')
    def test_reject_large_image(self):
        with self.assertRaises(ValueError):SegFormerService(self.root).predict(Image.new('RGB',(2001,2000)),'hash')

if __name__=='__main__':unittest.main()

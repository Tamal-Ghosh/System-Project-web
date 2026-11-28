import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import cv2
import torch
from PIL import Image
from segmentation.segformer_b2 import SegFormerB2Service, prepare_pixels, restore_mask, REVISION
from segmentation.service import SegmentationUnavailable, SegmentationBusy
class FakeModel(torch.nn.Module):
    def __init__(self):super().__init__();self.weight=torch.nn.Parameter(torch.zeros(1))
    def forward(self,x):return torch.full((1,1,512,512),2.)
class SegFormerB2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.checkpoint={'model':{'model.weight':torch.ones(1)},'cfg':{'model':'segformer_mitb2','data':{'img_size':512}},'epoch':21,'which':'raw'}
        torch.save(self.checkpoint,self.root/'best.pt');self.digest=hashlib.sha256((self.root/'best.pt').read_bytes()).hexdigest()
        (self.root/'segmentation.json').write_text(json.dumps({'source_revision':REVISION,'checkpoint_sha256':self.digest,'threshold':.7,'input_size':[512,512]}))
        self.patch=patch('segmentation.segformer_b2.CHECKPOINT_SHA256',self.digest);self.patch.start()
        self.service=SegFormerB2Service(self.root,FakeModel);self.image=Image.new('RGB',(20,14),(220,110,30))
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def test_rgb_area_resize_and_publisher_normalization(self):
        x=prepare_pixels(self.image);self.assertEqual(tuple(x.shape),(1,3,512,512))
        expected=(np.array([220,110,30],np.float32)-np.array([.485,.456,.406],np.float32)*255)/(np.array([.229,.224,.225],np.float32)*255)
        np.testing.assert_allclose(x[0,:,0,0].numpy(),expected,rtol=1e-6)
    def test_probability_resize_before_threshold_matches_publisher(self):
        logits=torch.linspace(-10,10,512*512).reshape(1,1,512,512)
        expected=cv2.resize(logits.sigmoid()[0,0].numpy(),(37,21),interpolation=cv2.INTER_LINEAR)>=.7
        np.testing.assert_array_equal(restore_mask(logits,(37,21)),expected)
    def test_invalid_logits_rejected(self):
        for x in [torch.zeros(1,2,512,512),torch.full((1,1,512,512),float('nan'))]:
            with self.assertRaises(ValueError):restore_mask(x,(20,14))
    def test_strict_checkpoint_and_original_dimensions(self):
        r=self.service.predict(self.image,'hash',image_type='dermoscopic');self.assertEqual(r['width'],20);self.assertEqual(r['height'],14);self.assertEqual(r['area_pixels'],280);self.assertEqual(r['threshold'],.7);self.assertTrue(r['input_domain_supported']);self.assertTrue(r['review_required']);self.assertEqual(self.service._model.weight.item(),1.)
    def test_clinical_photo_explicitly_outside_evaluation_domain(self):
        r=self.service.predict(self.image,'hash',image_type='clinical');self.assertFalse(r['input_domain_supported']);self.assertEqual(r['clinical_validation_status'],'not_evaluated');self.assertFalse(r['anatomical_conditioning'])
    def test_checksum_failure_not_partial_load(self):
        (self.root/'best.pt').write_bytes(b'corrupted')
        with self.assertRaises(SegmentationUnavailable):self.service.predict(self.image,'hash',image_type='clinical')
        self.assertIsNone(self.service._model)
    def test_unknown_modality_rejected(self):
        with self.assertRaises(ValueError):self.service.predict(self.image,'hash',image_type='auto')
    def test_no_modality_is_recorded_without_guessing(self):
        r=self.service.predict(self.image,'hash');self.assertEqual(r['image_type'],'unspecified');self.assertIsNone(r['input_domain_supported'])
    def test_api_accepts_image_without_modality_or_rectangle(self):
        import io
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from segmentation.routes import segmentation_router
        app=FastAPI();app.include_router(segmentation_router(self.service));stream=io.BytesIO();self.image.save(stream,format='PNG')
        with TestClient(app) as client:
            r=client.post('/api/v1/segmentation',files={'image':('test.png',stream.getvalue(),'image/png')})
            self.assertEqual(r.status_code,200);self.assertEqual(r.json()['image_type'],'unspecified')
    def test_busy_does_not_run_concurrently(self):
        self.service._gate.acquire()
        with self.assertRaises(SegmentationBusy):self.service.predict(self.image,'hash',image_type='clinical')
        self.service._gate.release()
if __name__=='__main__':unittest.main()

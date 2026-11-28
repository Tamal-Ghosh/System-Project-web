import base64
import csv
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from segmentation.service import NnUNetService, SegmentationUnavailable, SegmentationBusy, rgb_array, describe_mask
from segmentation.routes import segmentation_router
from scripts.prepare_segmentation_dataset import prepare
from scripts.evaluate_segmentation import metrics

class FakePredictor:
    configuration_manager = SimpleNamespace(patch_size=[32,32])
    def initialize_from_trained_model_folder(self, folder, use_folds, checkpoint_name):
        self.folds=use_folds
    def predict_single_npy_array(self, image, props):
        assert image.shape==(3,1,8,12)
        assert props=={'spacing':(999,1,1)}
        out=np.zeros((1,8,12),dtype=np.uint8);out[0,2:6,3:8]=1
        return out

class SegmentationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.image=Image.new('RGB',(12,8),(30,60,90))
        self.make_bundle()
    def tearDown(self): self.tmp.cleanup()
    def make_bundle(self):
        (self.root/'dataset.json').write_text(json.dumps({'labels':{'background':0,'lesion':1},'channel_names':{'0':'R','1':'G','2':'B'}}))
        (self.root/'plans.json').write_text(json.dumps({'image_reader_writer':'NaturalImage2DIO'}))
        (self.root/'fold_0').mkdir();(self.root/'fold_0/checkpoint_final.pth').write_bytes(b'test fixture only')
        self.manifest={'task':'dermoscopic_lesion_boundary','configuration':'2d','model_version':'test-fixture',
                       'folds':[0],'checkpoint_sha256':{'0':hashlib.sha256(b'test fixture only').hexdigest()}}
        self.write_manifest()
    def write_manifest(self): (self.root/'segmentation.json').write_text(json.dumps(self.manifest))
    def service(self): return NnUNetService(self.root,FakePredictor)
    def png(self):
        stream=io.BytesIO();self.image.save(stream,format='PNG');return stream.getvalue()
    def test_rgb_axes_and_values(self):
        array=rgb_array(self.image);self.assertEqual(array.shape,(3,1,8,12));np.testing.assert_array_equal(array[:,0,0,0],[30,60,90])
    def test_prediction_original_size_and_provenance(self):
        service=self.service();result=service.predict(self.image,'abc')
        self.assertEqual(result['area_pixels'],20);self.assertEqual(result['bounding_box'],{'x':3,'y':2,'width':5,'height':4})
        self.assertEqual(result['input_hash'],'abc');self.assertTrue(result['review_required'])
        with Image.open(io.BytesIO(base64.b64decode(result['mask_png']))) as mask:
            self.assertEqual(mask.size,self.image.size);self.assertEqual(set(np.unique(mask)),{0,255})
        self.assertEqual(service.status()['status'],'ready')
    def test_empty_and_border_masks(self):
        self.assertIsNone(describe_mask(np.zeros((5,5),bool))['bounding_box'])
        self.assertTrue(describe_mask(np.ones((5,5),bool))['touches_border'])
    def test_missing_configuration(self):
        service=NnUNetService('');self.assertEqual(service.status()['status'],'unavailable')
        with self.assertRaises(SegmentationUnavailable):service.predict(self.image,'abc')
    def test_checksum_rejected(self):
        self.manifest['checkpoint_sha256']['0']='0'*64;self.write_manifest()
        with self.assertRaises(SegmentationUnavailable):self.service().predict(self.image,'abc')
    def test_wrong_labels_rejected(self):
        (self.root/'dataset.json').write_text(json.dumps({'labels':{'brain':1},'channel_names':{'0':'R','1':'G','2':'B'}}))
        with self.assertRaises(SegmentationUnavailable):self.service().predict(self.image,'abc')
    def test_bad_folds_rejected(self):
        self.manifest['folds']=['../unsafe'];self.write_manifest()
        with self.assertRaises(SegmentationUnavailable):self.service().predict(self.image,'abc')
    def test_busy_and_pixel_limit(self):
        service=self.service();service._gate.acquire()
        with self.assertRaises(SegmentationBusy):service.predict(self.image,'abc')
        service._gate.release()
        with self.assertRaises(ValueError):service.predict(Image.new('RGB',(2001,2000)),'abc')
    def test_invalid_shape_and_values_rejected(self):
        for array in (np.zeros((8,12)),np.full((1,8,12),2)):
            with patch.object(FakePredictor,'predict_single_npy_array',return_value=array):
                with self.assertRaises(RuntimeError):self.service().predict(self.image,'abc')
    def test_api_success_and_bad_image(self):
        app=FastAPI();app.include_router(segmentation_router(self.service()))
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/v1/segmentation/status').json()['status'],'configured')
            response=client.post('/api/v1/segmentation',files={'image':('lesion.png',self.png(),'image/png')})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(client.post('/api/v1/segmentation',files={'image':('bad.png',b'invalid')}).status_code,422)
    def test_api_unavailable_and_busy(self):
        app=FastAPI();app.include_router(segmentation_router(NnUNetService('')))
        with TestClient(app) as client:
            self.assertEqual(client.post('/api/v1/segmentation',files={'image':('a.png',self.png())}).status_code,503)
        service=self.service();service._gate.acquire();app=FastAPI();app.include_router(segmentation_router(service))
        with TestClient(app) as client:
            self.assertEqual(client.post('/api/v1/segmentation',files={'image':('a.png',self.png())}).status_code,409)
        service._gate.release()
    def test_remote_service_preserves_input_identity(self):
        from segmentation.proxy import RemoteSegmentationService
        response=SimpleNamespace(status_code=200,raise_for_status=lambda:None,json=lambda:{'status':'ok','width':12,'height':8,'input_hash':'different-transport-encoding'})
        with patch('segmentation.proxy.httpx.post',return_value=response):
            self.assertEqual(RemoteSegmentationService('http://internal').predict(self.image,'original-upload')['input_hash'],'original-upload')
    def test_remote_service_failure_is_sanitized(self):
        import httpx
        from segmentation.proxy import RemoteSegmentationService
        service=RemoteSegmentationService('http://internal')
        with patch('segmentation.proxy.httpx.get',side_effect=httpx.ConnectError('private-host')):
            self.assertEqual(service.status()['status'],'unavailable')
        with patch('segmentation.proxy.httpx.post',side_effect=httpx.ConnectError('private-host')):
            with self.assertRaises(SegmentationUnavailable) as caught:service.predict(self.image,'abc')
            self.assertNotIn('private-host',str(caught.exception))
    def test_overlap_metrics(self):
        a=np.array([[1,1],[0,0]]);b=np.array([[1,0],[1,0]])
        self.assertEqual(metrics(a,b)['dice'],.5);self.assertAlmostEqual(metrics(a,b)['iou'],1/3)
        self.assertEqual(metrics(a*0,b*0)['dice'],1)
    def test_dataset_conversion_and_grouped_splits(self):
        rows=[]
        for i in range(7):
            Image.new('RGB',(12,8),(i,0,0)).save(self.root/f'i{i}.png')
            Image.new('L',(12,8),255).save(self.root/f'm{i}.png')
            rows.append({'case_id':f'case{i}','image':f'i{i}.png','mask':f'm{i}.png','group_id':f'g{i//2}' if i<2 else f'g{i}','split':'test' if i==6 else 'train'})
        path=self.root/'cases.csv'
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        output=self.root/'Dataset501_ISICLesion';dataset=prepare(path,output)
        self.assertEqual(dataset['numTraining'],6)
        with Image.open(output/'labelsTr/case0.png') as mask:self.assertEqual(set(np.unique(mask)),{1})
        splits=json.loads((output/'splits_final.json').read_text())
        for split in splits:
            self.assertEqual('case0' in split['val'],'case1' in split['val'])
            self.assertTrue(set(split['train']).isdisjoint(split['val']))
        with self.assertRaises(ValueError):prepare(path,output)
        rows[-1]['group_id']='g0'
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        with self.assertRaisesRegex(ValueError,'overlaps'):prepare(path,self.root/'bad')

if __name__=='__main__':unittest.main()

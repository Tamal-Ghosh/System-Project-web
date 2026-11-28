import unittest
from PIL import Image
from segmentation.automatic import AutomaticSegmentationService
from segmentation.service import SegmentationBusy
class Detector:
 def __init__(self,c):self.c=c
 def status(self):return {'status':'configured'}
 def detect(self,image):return self.c
class Segmenter:
 def __init__(self):self.calls=[]
 def status(self):return {'status':'configured'}
 def unload(self):pass
 def predict(self,image,input_hash,**kw):self.calls.append(kw);return {'mask_png':'test','model_version':'test','limitations':[]}
class AutomaticTests(unittest.TestCase):
 def service(self,c):self.sam=Segmenter();return AutomaticSegmentationService(Detector(c),self.sam)
 def test_single_candidate_without_user_rectangle(self):
  s=self.service([{'box':[2,2,12,10],'score':.8}]);r=s.predict(Image.new('RGB',(16,12)),'hash',image_type='clinical');self.assertEqual(r['status'],'ok');self.assertEqual(self.sam.calls[0]['box'],[2,2,12,10]);self.assertFalse(r['anatomical_conditioning'])
 def test_no_target_never_runs_sam(self):
  r=self.service([]).predict(Image.new('RGB',(16,12)),'hash',image_type='dermoscopic');self.assertEqual(r['status'],'no_target');self.assertFalse(self.sam.calls);self.assertNotIn('mask_png',r)
 def test_multiple_candidates_abstain(self):
  r=self.service([{},{}]).predict(Image.new('RGB',(16,12)),'hash',image_type='clinical');self.assertEqual(r['status'],'ambiguous');self.assertFalse(self.sam.calls)
 def test_invalid_localization_never_fabricates_mask(self):
  for box,score in [([0,0,16,12],.8),([-1,0,10,10],.8),([2,2,12,10],float('nan')),([2,2,12,10],.2)]:
   with self.subTest(box=box,score=score):
    r=self.service([{'box':box,'score':score}]).predict(Image.new('RGB',(16,12)),'hash',image_type='clinical');self.assertEqual(r['status'],'no_target');self.assertFalse(self.sam.calls)
 def test_modality_required(self):
  with self.assertRaises(ValueError):self.service([]).predict(Image.new('RGB',(16,12)),'hash')
 def test_busy(self):
  s=self.service([]);s._gate.acquire()
  with self.assertRaises(SegmentationBusy):s.predict(Image.new('RGB',(16,12)),'hash',image_type='clinical')
  s._gate.release()
 def test_api_uses_full_image_without_box_and_preserves_abstention(self):
  import io
  from fastapi import FastAPI
  from fastapi.testclient import TestClient
  from segmentation.routes import segmentation_router
  image=Image.new('RGB',(16,12));stream=io.BytesIO();image.save(stream,format='PNG')
  for candidates,expected in [([], 'no_target'),([{},{}], 'ambiguous'),([{'box':[2,2,12,10],'score':.8}], 'ok')]:
   app=FastAPI();app.include_router(segmentation_router(self.service(candidates)))
   with TestClient(app) as client:
    response=client.post('/api/v1/segmentation',files={'image':('test.png',stream.getvalue(),'image/png')},data={'image_type':'clinical'})
    self.assertEqual(response.status_code,200);self.assertEqual(response.json()['status'],expected)
if __name__=='__main__':unittest.main()


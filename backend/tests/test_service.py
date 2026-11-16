import unittest
import numpy as np
import torch
from dermfm.loader import load_adapter
from dermfm.preprocessing import decode_image, encode_metadata
from dermfm.metrics import summarize
from dermfm.service import InferenceService, Settings
from inference_fixtures import factory, image_bytes, setup_service_fixture

class ServiceTests(unittest.TestCase):
    def setUp(self):
        setup_service_fixture(self)
    def test_entropy_extremes(self):
        self.assertAlmostEqual(summarize(np.ones(11)/11)[0],1)
        self.assertEqual(summarize([1]+[0]*10),(0.,1.))
        with self.assertRaises(ValueError): summarize([0]*11)
    def test_five_fold_tta_matches_reference_and_is_repeatable(self):
        service=InferenceService(self.settings,factory)
        image=decode_image(image_bytes())
        result=service.predict(image,40,'female')
        derm=service.loaded.eval_transform(image).unsqueeze(0)
        meta=encode_metadata(40,'female'); expected=[]
        with torch.inference_mode():
            for checkpoint in service.states:
                load_adapter(service.loaded.model,checkpoint['model'])
                logits=[service.loaded.model(derm,derm,meta)]
                for dim in (-1,-2): logits.append(service.loaded.model(derm.flip(dim),derm.flip(dim),meta))
                expected.append(torch.stack(logits).mean(0).softmax(-1)[0].numpy())
        np.testing.assert_allclose([row['score'] for row in result['scores']],np.mean(expected,axis=0),rtol=1e-6)
        second=service.predict(image,40,'female')
        self.assertEqual(result['scores'],second['scores'])
        self.assertEqual(result['ensemble']['member_count'],5)
        self.assertEqual(result['persistence'],'not_saved')
    def test_single_fold_without_tta(self):
        settings=Settings(self.settings.recipe,self.settings.foundation,(self.paths[0],),tta=False)
        result=InferenceService(settings,factory).predict(decode_image(image_bytes()),21,'male')
        self.assertIsNone(result['ensemble']['agreement'])
        self.assertFalse(result['tta'])

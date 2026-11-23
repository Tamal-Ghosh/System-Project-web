import io
import unittest
import torch
from PIL import Image
from dermfm.preprocessing import encode_metadata, decode_image, assess_image_quality
from dermfm.loader import SITES

def image_bytes():
    output=io.BytesIO()
    Image.new('RGB',(12,10)).save(output,format='PNG')
    return output.getvalue()

class PreprocessingTests(unittest.TestCase):
    def test_metadata_and_missing_site(self):
        metadata=encode_metadata(40,'female')
        torch.testing.assert_close(metadata,torch.tensor([[.4,0,1,0,0,0,0,0,0,0]]))
        for age,sex in [(float('nan'),'male'),(-1,'male'),(121,'male'),(20,'invalid')]:
            with self.assertRaises(ValueError): encode_metadata(age,sex)
    def test_image_decode_and_invalid_bytes(self):
        self.assertEqual(decode_image(image_bytes()).size,(12,10))
        with self.assertRaises(ValueError): decode_image(b'not an image')

    def test_all_training_locations_use_recipe_order(self):
        for index, site in enumerate(SITES):
            with self.subTest(site=site):
                values=encode_metadata(40,'female',site)[0,3:]
                expected=torch.zeros(7); expected[index]=1
                torch.testing.assert_close(values,expected)
        torch.testing.assert_close(encode_metadata(40,'female','unknown')[0,3:],torch.zeros(7))
        with self.assertRaises(ValueError): encode_metadata(40,'female','unsupported')

    def test_assess_image_quality_sharp_vs_flat(self):
        # A uniform flat image has 0 variance and should be flagged
        flat_img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        flat_quality = assess_image_quality(flat_img)
        self.assertEqual(flat_quality["status"], "rejected")
        self.assertTrue(flat_quality["blur_detected"])

        # An image with alternating high contrast lines has high variance
        import numpy as np
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[::2, :] = 255
        sharp_img = Image.fromarray(arr)
        sharp_quality = assess_image_quality(sharp_img)
        self.assertEqual(sharp_quality["status"], "passed")
        self.assertFalse(sharp_quality["blur_detected"])

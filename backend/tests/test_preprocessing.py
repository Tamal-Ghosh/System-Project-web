import io
import unittest
import torch
from PIL import Image
from dermfm.preprocessing import encode_metadata, decode_image
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

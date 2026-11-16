import io
import unittest
import torch
from PIL import Image
from dermfm.preprocessing import encode_metadata, decode_image

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

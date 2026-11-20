import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'docker'))
from prepare_model_context import verify_context


class PackagingTests(unittest.TestCase):
    def test_missing_weights_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                verify_context(temporary)

    def test_consumer_uses_only_packaged_new_model(self):
        output = subprocess.run(['docker','compose','config','--format','json'],cwd=ROOT,capture_output=True,text=True,check=True)
        services = json.loads(output.stdout)['services']
        backend = services['backend']
        self.assertEqual(backend['image'],'dermascope-backend:dermfm-cpu-v2')
        self.assertEqual(backend['environment']['E55_BUNDLE_PATH'],'/opt/models/dermfm')
        self.assertNotIn('DERMFM_CHECKPOINTS',backend['environment'])
        self.assertFalse(backend.get('volumes'))
        frontend = services['frontend']
        self.assertFalse(frontend.get('volumes'))
        self.assertIsNone(frontend.get('command'))
        self.assertNotIn('build',backend)


if __name__ == '__main__':
    unittest.main()

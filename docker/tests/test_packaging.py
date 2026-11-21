"""Checks that do not require a working Docker daemon."""
import hashlib
import io
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'docker'))
import prepare_model_context as assets

class PackagingTests(unittest.TestCase):
    def test_model_whitelist_has_no_credentials_or_training_data(self):
        files=assets.expected_files()
        self.assertEqual(len(files),12)
        self.assertEqual(sum(name.endswith('.pth') for name in files),5)
        self.assertFalse(any('token' in name or '.venv' in name or name.endswith('.csv') for name in files))
    def test_unexpected_context_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'token').write_text('private')
            with self.assertRaisesRegex(ValueError,'approved model files'): assets.verify_context(root)
    def test_tampered_model_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); (root/'model.bin').write_bytes(b'changed')
            expected={'model.bin':hashlib.sha256(b'original').hexdigest()}
            with patch.object(assets,'expected_files',return_value=expected):
                with self.assertRaisesRegex(ValueError,'Checksum mismatch'): assets.verify_context(root)
    def test_zip_only_copies_whitelisted_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); archive=root/'package.zip'; destination=root/'context'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr(assets.PACKAGE_PREFIX+'assets/recipe.json','{}')
                z.writestr(assets.PACKAGE_PREFIX+'.hf_cache/token','private')
                z.writestr(assets.PACKAGE_PREFIX+'../../outside','unwanted')
            with patch.object(assets,'expected_files',return_value={'assets/recipe.json':None}), patch.object(assets,'validate_metadata'):
                assets.prepare(archive,destination)
            self.assertEqual([file.relative_to(destination).as_posix() for file in destination.rglob('*') if file.is_file()],['assets/recipe.json'])
    def test_duplicate_approved_zip_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); archive=root/'package.zip'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(archive,'w') as z:
                    for _ in range(2): z.writestr(assets.PACKAGE_PREFIX+'assets/recipe.json','{}')
            with patch.object(assets,'expected_files',return_value={'assets/recipe.json':None}):
                with self.assertRaisesRegex(ValueError,'ambiguous ZIP entry'): assets.prepare(archive,root/'context')
    def test_ready_health_and_unavailable_health_are_distinct(self):
        for status,exit_code in [('ready',0),('unavailable',1)]:
            with self.subTest(status=status), patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps({'status':status}).encode())):
                with self.assertRaises(SystemExit) as result: runpy.run_path(str(ROOT/'docker/healthcheck.py'))
                self.assertEqual(result.exception.code,exit_code)
    def test_compose_consumer_does_not_build_or_mount_host_weights(self):
        result=subprocess.run(['docker','compose','config','--format','json'],cwd=ROOT,check=True,capture_output=True,text=True)
        services=json.loads(result.stdout)['services']
        for service in services.values():
            self.assertNotIn('build',service)
            self.assertEqual(service['pull_policy'],'never')
        backend=services['backend']
        self.assertTrue(backend['environment']['DERMFM_FOUNDATION'].startswith('/opt/models/'))
        self.assertNotIn('ports',backend)
        self.assertTrue(all(volume['target']=='/app' for volume in backend['volumes']))
        self.assertEqual(services['frontend']['environment']['API_PROXY_TARGET'],'http://backend:8000')
        self.assertEqual(services['frontend']['depends_on']['backend']['condition'],'service_healthy')

if __name__=='__main__': unittest.main()

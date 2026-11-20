"""Verify the new model-only bundle directory before a Docker build."""
import argparse
import hashlib
import json
from pathlib import Path

WEIGHT_HASH = 'c769f025f83f3f0fb74ebe2580d3f45b250e5a98a0c5e3385b57b9b7d13669ec'
REQUIRED = ('full_model.pth','manifest.json','architecture.py','visual_runtime.py','web_inference.py','web_api.py','evaluation.py',
            'source/LICENSE','source/src/CAE/models/modeling_finetune.py','source/src/open_clip/utils.py')


def verify_context(root):
    root = Path(root)
    for name in REQUIRED:
        path = root/name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing or unsafe model asset: '+name)
    manifest = json.loads((root/'manifest.json').read_text())
    if manifest.get('sha256') != WEIGHT_HASH or manifest.get('folds') != 5 or not manifest.get('full_weights'):
        raise ValueError('Unexpected model manifest')
    with (root/'full_model.pth').open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest() != WEIGHT_HASH:
            raise ValueError('Model checksum mismatch')
    if (root/'full_model.pth').stat().st_size != manifest['bytes']:
        raise ValueError('Model size mismatch')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path, required=True)
    args = parser.parse_args()
    verify_context(args.package)
    print('Verified DermFM deployment assets')

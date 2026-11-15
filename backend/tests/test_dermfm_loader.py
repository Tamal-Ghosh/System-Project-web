import json
import tempfile
import unittest
from unittest.mock import patch
import types
import sys
from pathlib import Path
import torch
from torch import nn
from dermfm.loader import (CLASSES, SITES, FOUNDATION_REVISION, SOURCE_REVISION,
    DermFMFusion, ModelLoadError, load_model, local_foundation)

class TinyVisual(nn.Module):
    def __init__(self):
        super().__init__()
        self.qkv = nn.Linear(4, 4)
    def forward(self, x):
        return self.qkv(x)

class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.recipe = dict(classes=list(CLASSES), site_vocab=list(SITES), site_mode="site",
            foundation="redlessone/DermFM-Zero", foundation_revision=FOUNDATION_REVISION,
            repo_commit=SOURCE_REVISION, lora_rank=8, experiment="E38_locked_control",
            clinical_shades_of_gray=False, dermoscopy_shades_of_gray=False)
        self.model = DermFMFusion(TinyVisual(), torch.randn(11, 4))
        names = {k for k, p in self.model.named_parameters() if p.requires_grad}
        self.state = {k: v for k, v in self.model.state_dict().items() if k in names or k == "prototypes"}
    def load(self, factory=None):
        recipe_path, checkpoint = self.root/'recipe.json', self.root/'best.pth'
        recipe_path.write_text(json.dumps(self.recipe))
        torch.save(dict(model=self.state, epoch=7), checkpoint)
        return load_model(recipe_path=recipe_path, checkpoint_path=checkpoint,
            foundation_path=self.root, foundation_factory=factory or (lambda _: (TinyVisual(), None)))
    def test_loads_exact_adapter_and_freezes_eval_model(self):
        loaded = self.load()
        self.assertFalse(loaded.model.training)
        self.assertTrue(all(not p.requires_grad for p in loaded.model.parameters()))
        self.assertEqual(loaded.checkpoint_epoch, 7)
        for key, value in self.state.items():
            torch.testing.assert_close(loaded.model.state_dict()[key], value)
        output = loaded.model(torch.randn(2,4), torch.randn(2,4), torch.randn(2,10))
        self.assertEqual(output.shape, (2,11))
        self.assertTrue(torch.isfinite(output).all())
    def test_rejects_wrong_class_order(self):
        self.recipe['classes'] = list(reversed(CLASSES))
        with self.assertRaises(ModelLoadError): self.load()
    def test_rejects_missing_adapter_tensor(self):
        del self.state['log_scale']
        with self.assertRaises(ModelLoadError): self.load()
    def test_rejects_shape_mismatch(self):
        self.state['meta.0.weight'] = torch.ones(64,9)
        with self.assertRaises(ModelLoadError): self.load()
    def test_rejects_nonfinite_weights(self):
        self.state['log_scale'] = torch.tensor(float('nan'))
        with self.assertRaises(ModelLoadError): self.load()
    def test_foundation_failure_has_no_fallback(self):
        def broken(_): raise FileNotFoundError('missing foundation')
        with self.assertRaisesRegex(ModelLoadError, 'missing foundation'): self.load(broken)

class OfflineFoundationTests(unittest.TestCase):
    def test_local_visual_weights_are_strictly_loaded_without_text_encoder(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot=Path(directory)/FOUNDATION_REVISION; snapshot.mkdir()
            config=dict(model_cfg=dict(embed_dim=4,vision_cfg={}), preprocess_cfg=dict(mean=[.5]*3,std=[.5]*3))
            (snapshot/'open_clip_config.json').write_text(json.dumps(config))
            visual=TinyVisual()
            torch.save({'state_dict':{'visual.'+k:v for k,v in visual.state_dict().items()}}, snapshot/'open_clip_pytorch_model.bin')
            package=types.ModuleType('open_clip'); package.__file__=str(Path(directory)/'src/open_clip/__init__.py')
            module=types.ModuleType('open_clip.model')
            def build(dim, vision, **kwargs):
                self.assertFalse(vision['timm_model_pretrained'])
                self.assertEqual(dim,4)
                return TinyVisual()
            module._build_vision_tower=build
            transform=types.ModuleType('open_clip.transform')
            from dataclasses import dataclass
            @dataclass
            class Config:
                mean: object = None
                std: object = None
            transform.PreprocessCfg=Config
            sentinel=object()
            def image_transform(cfg,is_train):
                self.assertFalse(is_train)
                self.assertEqual(cfg.mean,[.5]*3)
                return sentinel
            transform.image_transform_v2=image_transform
            with patch.dict(sys.modules,{'open_clip':package,'open_clip.model':module,'open_clip.transform':transform}), patch('subprocess.run',return_value=types.SimpleNamespace(stdout=SOURCE_REVISION)):
                loaded,preprocess=local_foundation(snapshot)
                self.assertIs(preprocess,sentinel)
                for key,value in visual.state_dict().items(): torch.testing.assert_close(loaded.state_dict()[key],value)
                self.assertFalse(loaded.training)
                torch.save({'visual.unexpected':torch.ones(1)},snapshot/'open_clip_pytorch_model.bin')
                with self.assertRaises(RuntimeError): local_foundation(snapshot)

class PortableIntegrityTests(unittest.TestCase):
    def test_changed_source_is_rejected(self):
        from dermfm.portable import verify_hash
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'source.py'; file.write_text('changed')
            with self.assertRaisesRegex(ModelLoadError,'Checksum mismatch'):
                verify_hash(file,'0'*64)
    def test_wrong_foundation_revision_is_rejected(self):
        from dermfm.portable import load_portable_foundation
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'manifest.json').write_text(json.dumps({'repo':'redlessone/DermFM-Zero','revision':'wrong'}))
            with self.assertRaisesRegex(ModelLoadError,'provenance'):
                load_portable_foundation(root)

if __name__ == '__main__': unittest.main()

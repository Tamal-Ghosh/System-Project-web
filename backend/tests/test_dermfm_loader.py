import json
import tempfile
import unittest
from pathlib import Path
import torch
from torch import nn
from dermfm.loader import (CLASSES, SITES, FOUNDATION_REVISION, SOURCE_REVISION,
    DermFMFusion, ModelLoadError, load_model)

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

if __name__ == '__main__': unittest.main()

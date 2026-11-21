import io
import json
import tempfile
from pathlib import Path
import numpy as np
import torch
from torch import nn
from PIL import Image
from dermfm.loader import CLASSES, SITES, FOUNDATION_REVISION, SOURCE_REVISION, DermFMFusion
from dermfm.service import Settings

class Visual(nn.Module):
    def __init__(self):
        super().__init__()
        self.qkv = nn.Linear(4,4)
    def forward(self, x):
        return self.qkv(torch.stack([x[:,0,0,0], x[:,0,-1,-1], x[:,1,0,-1], x[:,2,-1,0]],dim=1))

def factory(_):
    torch.manual_seed(19)
    return Visual(), lambda image: torch.tensor(np.asarray(image).copy()).permute(2,0,1).float()/255

def image_bytes():
    output=io.BytesIO()
    Image.fromarray(np.arange(12*10*3,dtype=np.uint8).reshape(10,12,3)).save(output,format='PNG')
    return output.getvalue()


def setup_service_fixture(self):
    self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
    root=Path(self.tmp.name)
    recipe=dict(classes=list(CLASSES), site_vocab=list(SITES), site_mode='site',
        foundation='redlessone/DermFM-Zero', foundation_revision=FOUNDATION_REVISION,
        repo_commit=SOURCE_REVISION,lora_rank=8,experiment='E38_locked_control',
        clinical_shades_of_gray=False,dermoscopy_shades_of_gray=False)
    recipe_path=root/'recipe.json'; recipe_path.write_text(json.dumps(recipe))
    self.paths=[]
    for fold in range(5):
        visual,_=factory(None)
        model=DermFMFusion(visual, torch.randn(11,4))
        with torch.no_grad(): model.head[-1].bias[fold]+=fold+1
        state={k:v for k,v in model.state_dict().items() if k in model.adapter_keys}
        path=root/f'fold{fold}.pth'; torch.save(dict(model=state,epoch=fold+1),path); self.paths.append(path)
    self.settings=Settings(recipe_path,root,tuple(self.paths),tta=True)

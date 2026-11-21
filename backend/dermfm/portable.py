"""Load the checksum-pinned visual source shipped in the full deployment ZIP.

Only reviewed architecture definitions are compiled; training imports, registry
side effects and deployment scripts are not executed. The original source and
license remain in the local deployment directory.
"""
import ast
import hashlib
import json
import math
from functools import partial
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from .loader import ModelLoadError, FOUNDATION_REVISION

SOURCE_HASHES = {
    'src/CAE/models/modeling_finetune.py': '05f044580b2b73f28b2fc6480e9ea8811bb8852366edf067a5dc8e1667c054a1',
    'src/open_clip/utils.py': 'cc8e0676981e6104b7ca22d2cf1642aba13a0b17fbd542fc74363320c5186309',
}
FOUNDATION_HASHES = {
    'open_clip_config.json': '8dc39de2b8c4877089b5a58be0a6ca6048f489c3a2f44aef89890e9338d75f07',
    'open_clip_pytorch_model.bin': '83f498e3ee5e0963a14356b2d0facde640a2f108972d12437705a805f30d2918',
}

def verify_hash(path, expected):
    with Path(path).open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual != expected:
        raise ModelLoadError(f'Checksum mismatch: {Path(path).name}')

def visual_classes(source):
    from timm.layers import drop_path, to_2tuple, trunc_normal_
    namespace=dict(math=math,np=np,torch=torch,nn=nn,F=F,partial=partial,
                   drop_path=drop_path,to_2tuple=to_2tuple,trunc_normal_=trunc_normal_)
    groups=[('src/CAE/models/modeling_finetune.py',
        {'DropPath','Mlp','Attention','Block','PatchEmbed','RelativePositionBias','VisionTransformer'}),
        ('src/open_clip/utils.py',{'PanDermVisualWrapper','_interpolate_pos_embed'})]
    for relative,names in groups:
        path=Path(source)/relative
        verify_hash(path,SOURCE_HASHES[relative])
        tree=ast.parse(path.read_text(encoding='utf-8'))
        nodes=[node for node in tree.body if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name in names]
        if {node.name for node in nodes} != names:
            raise ModelLoadError('Pinned architecture definitions missing')
        exec(compile(ast.Module(nodes,type_ignores=[]),str(path),'exec'),namespace)
    return namespace['VisionTransformer'],namespace['PanDermVisualWrapper']

def load_portable_foundation(foundation):
    from torchvision import transforms
    from torchvision.transforms import InterpolationMode
    foundation=Path(foundation)
    manifest=json.loads((foundation/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('repo') != 'redlessone/DermFM-Zero' or manifest.get('revision') != FOUNDATION_REVISION:
        raise ModelLoadError('Unexpected portable foundation provenance')
    for name,expected in FOUNDATION_HASHES.items(): verify_hash(foundation/name,expected)
    config=json.loads((foundation/'open_clip_config.json').read_text(encoding='utf-8'))
    expected=dict(mean=[.5]*3,std=[.5]*3,size=224,interpolation='bicubic',resize_mode='shortest')
    if config['preprocess_cfg'] != expected:
        raise ModelLoadError('Unexpected portable preprocessing')
    Vision,Wrapper=visual_classes(foundation.parent/'dermfm_source')
    trunk=Vision(patch_size=16,embed_dim=1024,depth=24,num_heads=16,mlp_ratio=4,
                 qkv_bias=True,norm_layer=partial(nn.LayerNorm,eps=1e-6),init_values=.1,num_classes=768)
    visual=Wrapper(trunk,image_size=224)
    state=torch.load(foundation/'open_clip_pytorch_model.bin',map_location='cpu',weights_only=True,mmap=True)
    state=state.get('state_dict',state)
    state={key.removeprefix('module.'):value for key,value in state.items()}
    selected={key.removeprefix('visual.'):value for key,value in state.items() if key.startswith('visual.')}
    if not selected or any(not torch.isfinite(v).all() for v in selected.values()):
        raise ModelLoadError('Invalid foundation visual weights')
    visual.load_state_dict(selected,strict=True)
    transform=transforms.Compose([transforms.Resize(224,interpolation=InterpolationMode.BICUBIC),
        transforms.CenterCrop((224,224)),transforms.ToTensor(),transforms.Normalize([.5]*3,[.5]*3)])
    return visual.eval(),transform

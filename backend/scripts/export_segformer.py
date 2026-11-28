"""Export a trusted SegFormer-B0 state dict for dependency-light, offline PyTorch inference."""
import argparse
import hashlib
import json
from pathlib import Path
import torch

SOURCE_SHA256='e75292993fbd65579e310b20e448fb2abb864408aee5776beef785dea6abba9a'
SOURCE_REVISION='2d8c48d74cff7af51e27d32fcdf7ba6e112af075'

def export(checkpoint, output):
    import transformers
    from transformers import SegformerConfig, SegformerForSemanticSegmentation
    checkpoint, output=Path(checkpoint),Path(output)
    with checkpoint.open('rb') as stream: checksum=hashlib.file_digest(stream,'sha256').hexdigest()
    if checksum!=SOURCE_SHA256:
        raise ValueError('Checkpoint does not match the reviewed ISIC SegFormer source revision.')
    torch.set_num_threads(2);torch.manual_seed(42)
    config=SegformerConfig(num_labels=1,decoder_hidden_size=256)
    config._attn_implementation='eager'
    model=SegformerForSemanticSegmentation(config).eval()
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    if not all(isinstance(value,torch.Tensor) and torch.isfinite(value).all() for value in state.values()):
        raise ValueError('Checkpoint contains invalid weights.')
    model.load_state_dict(state,strict=True)
    class Logits(torch.nn.Module):
        def __init__(self,model):super().__init__();self.model=model
        def forward(self,pixels):return self.model(pixel_values=pixels,return_dict=True).logits
    wrapper=Logits(model).eval()
    sample=torch.randn(1,3,256,256)
    with torch.inference_mode():
        traced=torch.jit.trace(wrapper,sample,strict=True,check_trace=True)
        for pixels in (sample,torch.zeros_like(sample),torch.ones_like(sample)):
            expected,actual=wrapper(pixels),traced(pixels)
            torch.testing.assert_close(actual,expected,rtol=1e-4,atol=1e-4)
            if actual.shape!=(1,1,64,64) or not torch.isfinite(actual).all():raise ValueError('Unexpected SegFormer output.')
    output.mkdir(parents=True,exist_ok=True)
    target=output/'segformer_b0.pt'
    torch.jit.save(traced,str(target))
    with target.open('rb') as stream: artifact_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    metadata={'engine':'segformer','architecture':'mit-b0','model_version':'segformer-isic2018-'+checksum[:12],
        'artifact':'segformer_b0.pt','artifact_sha256':artifact_hash,'source_checkpoint_sha256':checksum,
        'source_url':'https://huggingface.co/mahnoor-2722/isic-segformer','source_revision':SOURCE_REVISION,
        'license':'MIT (publisher declaration)','input_size':[256,256],
        'mean':[0.485,0.456,0.406],'std':[0.229,0.224,0.225],'threshold':0.5,
        'preprocessing_status':'experimental_defaults_not_confirmed_by_publisher',
        'normalization_source':'Hugging Face ImageNet defaults; training recipe unavailable',
        'resize':'PIL bilinear RGB resize; output logits bilinear to original size, align_corners=False',
        'transformers_version':transformers.__version__,'torch_version':torch.__version__,
        'export_check':'Strict state loading and eager/export parity on three synthetic inputs passed.',
        'evaluation_status':'No independent lesion accuracy evaluation performed by this application.'}
    (output/'segmentation.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print('PASS: strict SegFormer checkpoint load and eager/export parity. Saved offline inference bundle.')
    print('Experimental preprocessing and threshold; publisher test metrics have not been reproduced.')
    return metadata

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--checkpoint',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();export(args.checkpoint,args.output)

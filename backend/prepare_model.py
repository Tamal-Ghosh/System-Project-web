"""Prepare ignored local adapter assets; never extracts arbitrary ZIP paths."""
import argparse
import json
from pathlib import Path
import zipfile
from dermfm.loader import read_checkpoint, validate_recipe, FOUNDATION_REVISION

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--recipe',type=Path,required=True)
    parser.add_argument('--foundation',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--folds',nargs='+',type=int,default=[0],choices=range(5))
    parser.add_argument('--device',default='cpu')
    args=parser.parse_args()
    if len(args.folds) not in (1,5) or len(set(args.folds))!=len(args.folds):
        parser.error('Choose one fold or all five distinct folds')
    validate_recipe(args.recipe)
    backend=Path(__file__).resolve().parent
    assets=backend/'.model-assets'; assets.mkdir(exist_ok=True)
    recipe=assets/'recipe.json'; recipe.write_bytes(args.recipe.read_bytes())
    paths=[]
    with zipfile.ZipFile(args.archive) as archive:
        for fold in args.folds:
            names=[n for n in archive.namelist() if n.endswith(f'/dermfm/fold{fold}/best.pth')]
            if len(names)!=1: raise ValueError(f'Missing/ambiguous fold {fold}')
            member=archive.getinfo(names[0])
            if member.file_size > 100*1024*1024: raise ValueError('Unexpected adapter size')
            target=assets/f'fold{fold}.pth'
            target.write_bytes(archive.read(member))
            read_checkpoint(target); paths.append(str(target))
    config=dict(recipe=str(recipe),foundation=str(args.foundation.resolve()),
                source=str(args.source.resolve()),checkpoints=paths,device=args.device,tta=True)
    target=backend/'model.local.json'; target.write_text(json.dumps(config,indent=2))
    print('Prepared local configuration:',target)
    print('Foundation snapshot required:',FOUNDATION_REVISION)
    if not args.foundation.is_dir(): print('Foundation directory is not available yet; inference will remain disabled.')

if __name__=='__main__': main()

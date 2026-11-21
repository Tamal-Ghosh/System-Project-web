"""Publisher only: copy a strict, verified subset; no downloads or credentials."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PACKAGE_PREFIX='E38_DermFM_Deployment/'
FOLDS={
 'fold0_best.pth':'d56a6f71fcb2540efbae990d6227366f6c753b395497770579045ed65c3a1df4',
 'fold1_best.pth':'571c292b094a025b43d28e17f45992b857527228378265f9cf235e228d44f872',
 'fold2_best.pth':'d01cbeb030d610be140258a070b3dc32cee087185016ae78175605bf340e12ac',
 'fold3_best.pth':'967d2c509c712ff89e6219b3e643ce89cf967601bfa1e8e1a93a930f819420a2',
 'fold4_best.pth':'2423d3fd4d50030b88e2ecf5939125ed143069af789546b5f8d6877ce1de4fe8',
}
def expected_files():
    tree=ast.parse((ROOT/'backend/dermfm/portable.py').read_text(encoding='utf-8'))
    hashes={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('SOURCE_HASHES','FOUNDATION_HASHES') for t in node.targets):
            name=node.targets[0].id
            prefix='dermfm_source/' if name=='SOURCE_HASHES' else 'foundation/'
            hashes.update({prefix+k:v for k,v in ast.literal_eval(node.value).items()})
    if len(hashes)!=4: raise ValueError('Expected four pinned foundation/source hashes')
    hashes.update({'assets/'+k:v for k,v in FOLDS.items()})
    hashes.update({'assets/recipe.json':None,'foundation/manifest.json':None,'dermfm_source/LICENSE':None})
    return hashes

def validate_metadata(root):
    loader=ast.parse((ROOT/'backend/dermfm/loader.py').read_text(encoding='utf-8'))
    constants={}
    for node in loader.body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('CLASSES','SITES','FOUNDATION_REVISION','SOURCE_REVISION'):
            constants[node.targets[0].id]=ast.literal_eval(node.value)
    recipe=json.loads((root/'assets/recipe.json').read_text(encoding='utf-8'))
    expected={'classes':list(constants['CLASSES']),'site_vocab':list(constants['SITES']),
              'foundation_revision':constants['FOUNDATION_REVISION'],'repo_commit':constants['SOURCE_REVISION'],
              'experiment':'E38_locked_control','lora_rank':8,'clinical_shades_of_gray':False,'dermoscopy_shades_of_gray':False}
    if any(recipe.get(k)!=v for k,v in expected.items()): raise ValueError('Unexpected E38 recipe')
    manifest=json.loads((root/'foundation/manifest.json').read_text(encoding='utf-8'))
    if manifest.get('repo')!='redlessone/DermFM-Zero' or manifest.get('revision')!=constants['FOUNDATION_REVISION']:
        raise ValueError('Unexpected foundation manifest')

def verify_context(destination):
    expected=expected_files()
    actual={path.relative_to(destination).as_posix() for path in destination.rglob('*') if path.is_file()}
    if actual!=set(expected):
        raise ValueError(f'Build context must contain only the approved model files. Extra={actual-set(expected)}, missing={set(expected)-actual}')
    for relative,digest in expected.items():
        if digest:
            with (destination/relative).open('rb') as stream: actual_hash=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual_hash!=digest: raise ValueError('Checksum mismatch: '+relative)
    validate_metadata(destination)
    return expected

def prepare(package,destination):
    expected=expected_files()
    destination.mkdir(parents=True,exist_ok=True)
    # Refuse to silently include caches/tokens or other files in a named context.
    existing={path.relative_to(destination).as_posix() for path in destination.rglob('*') if path.is_file()}
    if existing-set(expected): raise ValueError('Unexpected files in destination; choose a new empty directory')
    archive=zipfile.ZipFile(package) if package.is_file() else None
    try:
        for relative,digest in expected.items():
            target=destination/relative
            if not target.resolve().is_relative_to(destination.resolve()): raise ValueError('Unsafe target path')
            target.parent.mkdir(parents=True,exist_ok=True)
            if archive:
                name=PACKAGE_PREFIX+relative
                if archive.namelist().count(name)!=1: raise ValueError('Missing or ambiguous ZIP entry: '+relative)
                stream=archive.open(name)
            else:
                source=package/relative
                if source.is_symlink(): raise ValueError('Model source must not be a symlink')
                stream=source.open('rb')
            temporary=target.with_name(target.name+'.partial')
            try:
                with stream,temporary.open('wb') as output: shutil.copyfileobj(stream,output,8*1024*1024)
                if digest:
                    with temporary.open('rb') as check: actual=hashlib.file_digest(check,'sha256').hexdigest()
                    if actual!=digest: raise ValueError('Checksum mismatch: '+relative)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
    finally:
        if archive: archive.close()
    verify_context(destination)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--package',type=Path)
    parser.add_argument('--destination',type=Path,default=ROOT/'docker/model-assets')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    if args.verify_only: verify_context(args.destination)
    elif args.package: prepare(args.package,args.destination)
    else: parser.error('--package is required when preparing assets')
    print('Verified model-only build context:',args.destination)

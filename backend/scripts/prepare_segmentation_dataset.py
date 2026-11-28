"""Convert an explicit, group-labelled CSV to nnU-Net RGB 2D data; never download patient data."""
import argparse
import csv
import hashlib
import json
import random
import re
from pathlib import Path
import numpy as np
from PIL import Image


def prepare(csv_path, output):
    csv_path, output = Path(csv_path), Path(output)
    if output.exists():
        raise ValueError('Output already exists; choose a new dataset directory.')
    with csv_path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not {'case_id','image','mask','group_id','split'}.issubset(rows[0]):
        raise ValueError('CSV requires case_id,image,mask,group_id,split columns.')
    ids, groups, hashes, prepared = set(), {}, {}, []
    for row in rows:
        case, group, split = row['case_id'], row['group_id'].strip(), row['split'].strip()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', case) or case in ids:
            raise ValueError('Case IDs must be unique and filesystem-safe.')
        if not group or split not in ('train','test'):
            raise ValueError('Every case needs group_id and split train or test.')
        if group in groups and groups[group] != split:
            raise ValueError('Patient/lesion group overlaps train and test.')
        groups[group] = split; ids.add(case)
        image_path, mask_path = csv_path.parent/row['image'], csv_path.parent/row['mask']
        with Image.open(image_path) as source:
            if source.getexif().get(274, 1) != 1:
                raise ValueError('Normalize EXIF orientation and matching masks before conversion.')
            image = source.convert('RGB')
        with Image.open(mask_path) as source:
            if source.mode not in ('L','1','I','I;16'):
                raise ValueError('Masks must be single-channel binary label maps.')
            values = np.asarray(source)
            if not np.isin(values, [0,1,255]).all() or values.shape != (image.height,image.width):
                raise ValueError('Mask values or dimensions do not match the image.')
            mask = Image.fromarray((values>0).astype(np.uint8))
        image_hash = hashlib.sha256(image.tobytes()).hexdigest()
        if image_hash in hashes:
            raise ValueError('Duplicate image content found; deduplicate before splitting.')
        hashes[image_hash] = case
        prepared.append((row,image_path,mask_path))
    train_groups = sorted(group for group,split in groups.items() if split=='train')
    if len(train_groups)<5:
        raise ValueError('At least five independent training groups are required for five-fold splits.')
    random.Random(42).shuffle(train_groups)
    folds = {group:index%5 for index,group in enumerate(train_groups)}
    splits = [{'train':[],'val':[]} for _ in range(5)]
    for row,image_path,mask_path in prepared:
        with Image.open(image_path) as source:
            image = source.convert('RGB')
        with Image.open(mask_path) as source:
            mask = Image.fromarray((np.asarray(source)>0).astype(np.uint8))
        suffix = 'Tr' if row['split']=='train' else 'Ts'
        for directory in (output/f'images{suffix}',output/f'labels{suffix}'):
            directory.mkdir(parents=True,exist_ok=True)
        image.save(output/f'images{suffix}'/f"{row['case_id']}_0000.png")
        mask.save(output/f'labels{suffix}'/f"{row['case_id']}.png")
        if suffix=='Tr':
            for fold in range(5):
                splits[fold]['val' if fold==folds[row['group_id'].strip()] else 'train'].append(row['case_id'])
    dataset = {'channel_names':{'0':'R','1':'G','2':'B'},'labels':{'background':0,'lesion':1},
               'numTraining':sum(row['split']=='train' for row in rows),'file_ending':'.png',
               'overwrite_image_reader_writer':'NaturalImage2DIO'}
    (output/'dataset.json').write_text(json.dumps(dataset,indent=2),encoding='utf-8')
    (output/'splits_final.json').write_text(json.dumps(splits,indent=2),encoding='utf-8')
    # Do not copy original paths or patient/group identifiers into the exported dataset metadata.
    return dataset

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--csv',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.csv,args.output),indent=2))

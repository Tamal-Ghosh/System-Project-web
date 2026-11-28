"""Evaluate exported binary PNG masks against independent ground truth (no model tuning)."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image

def metrics(predicted, expected):
    if predicted.shape != expected.shape:
        raise ValueError('Prediction and ground truth dimensions differ.')
    p, g = predicted.astype(bool), expected.astype(bool)
    intersection = int((p & g).sum()); total = int(p.sum()+g.sum()); union = int((p | g).sum())
    return {'dice': 2*intersection/total if total else 1.0, 'iou': intersection/union if union else 1.0}

def evaluate(predictions, labels):
    predictions, labels = Path(predictions), Path(labels)
    truth = sorted(labels.glob('*.png'))
    if not truth or {f.name for f in truth}!={f.name for f in predictions.glob('*.png')}:
        raise ValueError('Prediction and ground-truth filenames must match exactly and be nonempty.')
    results=[]
    for f in truth:
        with Image.open(f) as g, Image.open(predictions/f.name) as p:
            ga, pa = np.asarray(g),np.asarray(p)
            if ga.ndim!=2 or pa.ndim!=2 or not np.isin(ga,[0,1,255]).all() or not np.isin(pa,[0,1,255]).all():
                raise ValueError('Use single-channel binary masks, not coloured overlays.')
            results.append({'case_id':f.stem,**metrics(pa,ga)})
    return {'evaluated_images':len(results),'macro_dice':float(np.mean([r['dice'] for r in results])),
            'macro_iou':float(np.mean([r['iou'] for r in results])), 'cases':results}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--predictions',required=True);parser.add_argument('--labels',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();result=evaluate(args.predictions,args.labels)
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8');print('Saved segmentation evaluation.')

"""Report observed segmentation utility; never invent a clinical pass threshold or missing data."""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image
from .evaluate_segmentation import metrics

def number(row,key):
    value=row.get(key,'').strip()
    if not value:return None
    value=float(value)
    if not math.isfinite(value) or value<0:raise ValueError('Timing values must be finite nonnegative observations.')
    return value

def evaluate(csv_path):
    csv_path=Path(csv_path)
    with csv_path.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    result={'status':'not_evaluated','clinical_validation':'not_established','independence_verification':'not_checked_by_script',
            'case_count':len(rows),'mask_evaluated_count':0,'missing_reference_count':0,
            'mask_metrics':None,'classification_comparisons':{},'timing':None,'subgroups':{},
            'decision':'No evidence yet to make segmentation mandatory or claim classification improvement.'}
    if not rows:return result
    required={'case_id','image_type','anatomical_site','reference_mask','predicted_mask'}
    if not required.issubset(rows[0]):raise ValueError('Missing required evaluation CSV columns.')
    ids=set();mask_results=[];groups=defaultdict(list);timings=[]
    for row in rows:
        identity=row['case_id'].strip()
        if not identity or identity in ids:raise ValueError('Case IDs must be nonempty and unique.')
        ids.add(identity)
        if row['image_type'] not in ('clinical','dermoscopic'):raise ValueError('Specify the observed image type; do not infer it.')
        reference,predicted=row['reference_mask'].strip(),row['predicted_mask'].strip()
        if reference and predicted:
            with Image.open(csv_path.parent/reference) as truth,Image.open(csv_path.parent/predicted) as proposal:
                a,b=np.asarray(proposal),np.asarray(truth)
                if a.ndim!=2 or b.ndim!=2 or not np.isin(a,[0,1,255]).all() or not np.isin(b,[0,1,255]).all():raise ValueError('Use binary PNG masks, not coloured overlays.')
                item=metrics(a,b);mask_results.append(item)
                groups['image_type:'+row['image_type']].append(item)
                groups['anatomical_site:'+(row['anatomical_site'].strip() or 'unknown')].append(item)
        else:result['missing_reference_count']+=1
        prompt_time,review_time,manual_time=(number(row,k) for k in ('prompt_seconds','review_seconds','manual_trace_seconds'))
        if all(x is not None for x in (prompt_time,review_time,manual_time)):
            timings.append({'assisted_seconds':prompt_time+review_time,'manual_seconds':manual_time})
    if mask_results:
        result['mask_evaluated_count']=len(mask_results)
        result['mask_metrics']={key:float(np.mean([item[key] for item in mask_results])) for key in ('dice','iou')}
        result['subgroups']={name:{'n':len(items),**{key:float(np.mean([item[key] for item in items])) for key in ('dice','iou')}} for name,items in groups.items()}
    for key in ('manual_roi_class','segmentation_crop_class'):
        paired=[r for r in rows if r.get('true_class','').strip() and r.get('original_class','').strip() and r.get(key,'').strip()]
        if paired:
            baseline=[r['original_class']==r['true_class'] for r in paired];candidate=[r[key]==r['true_class'] for r in paired]
            result['classification_comparisons'][key]={'paired_n':len(paired),'original_accuracy':float(np.mean(baseline)),
                'candidate_accuracy':float(np.mean(candidate)),'accuracy_delta':float(np.mean(candidate)-np.mean(baseline)),
                'original_correct_candidate_wrong':sum(a and not b for a,b in zip(baseline,candidate)),
                'original_wrong_candidate_correct':sum(not a and b for a,b in zip(baseline,candidate))}
    if timings:result['timing']={'paired_n':len(timings),'mean_assisted_seconds':float(np.mean([x['assisted_seconds'] for x in timings])),
                                'mean_manual_trace_seconds':float(np.mean([x['manual_seconds'] for x in timings]))}
    if mask_results or result['classification_comparisons'] or timings:
        result['status']='observations_reported_not_clinically_validated'
        result['decision']='Review paired quality, errors, anatomical/image-type subgroups and clinician time against a predeclared protocol. This report does not certify clinical reliability.'
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cases',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();report=evaluate(args.cases);Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Evaluation status:',report['status'],'cases:',report['case_count'])

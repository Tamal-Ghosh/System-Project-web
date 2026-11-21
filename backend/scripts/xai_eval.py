"""Seeded, resumable faithfulness evaluation for configured E38 assets."""
import argparse, csv, json, os, random, sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dermfm.explain import explain_image_ig
from dermfm.preprocessing import decode_image, prepare_inputs
from dermfm.service import InferenceService, Settings
from dermfm.loader import load_adapter

def auc(values): return float(np.trapezoid(np.asarray(values, dtype=float), dx=1/(len(values)-1)))
def ranks(values): return np.argsort(np.argsort(values)).astype(float)
def corr(left, right):
    a,b=ranks(left).ravel(),ranks(right).ravel()
    return float(np.corrcoef(a,b)[0,1]) if np.std(a) and np.std(b) else 0.0
def png_plot(path, curves):
    canvas=Image.new('RGB',(640,400),'white'); draw=ImageDraw.Draw(canvas)
    draw.line((55,20,55,340,610,340), fill='#34495e', width=2)
    colors=('#c0392b','#2980b9','#7f8c8d')
    for (label, vals), color in zip(curves.items(), colors):
        points=[(55+int(i*555/(len(vals)-1)),340-int(max(0,min(1,v))*300)) for i,v in enumerate(vals)]
        draw.line(points, fill=color, width=3); draw.text((70,25+22*list(curves).index(label)),label,fill=color)
    canvas.save(path)
def main():
    p=argparse.ArgumentParser(); p.add_argument('--images',required=True); p.add_argument('--labels'); p.add_argument('--masks'); p.add_argument('--out',default='reports/xai_eval'); p.add_argument('-n',type=int,default=100); p.add_argument('--seed',type=int,default=42); args=p.parse_args()
    random.seed(args.seed); np.random.seed(args.seed); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    result_file=out/'results.csv'; existing={row['image'] for row in csv.DictReader(result_file.open())} if result_file.exists() else set()
    service=InferenceService(Settings.from_env()); rows=[]; deletion_all=[]; insertion_all=[]; random_del_all=[]; random_ins_all=[]; examples=[]
    images=sorted(x for x in Path(args.images).iterdir() if x.suffix.lower() in ('.jpg','.jpeg','.png','.webp'))[:args.n]
    labels={}
    if args.labels:
        with open(args.labels,newline='',encoding='utf-8') as f:
            for row in csv.DictReader(f): labels[row.get('image') or row.get('filename')]=row.get('label')
    for path in images:
        if path.name in existing: continue
        image=decode_image(path.read_bytes()); x,_,meta=prepare_inputs(image,50,'female',service.loaded.eval_transform,service.settings.device,'unknown')
        model=service.loaded.model; model.eval()
        with service.lock, torch.inference_mode():
            load_adapter(model,service.states[0]['model']); logits=model(x,x,meta)[0]; target=int(logits.argmax()); second=int(logits.argsort()[-2]); original=float(logits[target])
        blurred=image.filter(ImageFilter.GaussianBlur(18)); base=service.loaded.eval_transform(blurred).unsqueeze(0).to(service.settings.device)
        with service.lock:
            attribution=explain_image_ig(service,x,meta,service.states[0]['model'],target,n_steps=20,baseline='blur',source_image=image)
        amap=np.asarray(attribution['image_map']['abs'],dtype=np.float32); order=np.argsort(amap.ravel())[::-1]
        # 16px patch ranking, evaluated in 20 cumulative pixel fractions.
        patch_scores=[]
        for yy in range(0,224,16):
            for xx in range(0,224,16): patch_scores.append((float(amap[yy:yy+16,xx:xx+16].sum()),yy,xx))
        patch_scores.sort(reverse=True)
        ordered=np.concatenate([np.asarray([(y+dy)*224+x+dx for dy in range(min(16,224-y)) for dx in range(min(16,224-x))],dtype=int) for _,y,x in patch_scores])
        steps=np.linspace(0,1,21); delete=[]; insert=[]
        def score(tensor):
            with service.lock, torch.inference_mode(): load_adapter(model,service.states[0]['model']); return float(model(tensor,tensor,meta)[0,target])
        for fraction in steps:
            count=int(fraction*224*224); mask=torch.zeros(224*224,device=x.device); mask[ordered[:count]]=1; mask=mask.reshape(1,1,224,224)
            delete.append(score(x*(1-mask)+base*mask)); insert.append(score(base*(1-mask)+x*mask))
        rand_curves=[]; rand_insert_curves=[]
        for seed in range(5):
            rng=np.random.default_rng(args.seed+seed); random_order=rng.permutation(224*224); curve=[]; insert_curve=[]
            for fraction in steps:
                count=int(fraction*224*224); mask=torch.zeros(224*224,device=x.device); mask[random_order[:count]]=1; mask=mask.reshape(1,1,224,224)
                curve.append(score(x*(1-mask)+base*mask)); insert_curve.append(score(base*(1-mask)+x*mask))
            rand_curves.append(curve); rand_insert_curves.append(insert_curve)
        random_curve=np.mean(rand_curves,axis=0).tolist(); random_insert=np.mean(rand_insert_curves,axis=0).tolist()
        deletion_auc=auc(delete); insertion_auc=auc(insert); rand_auc=auc(random_curve)
        changed=ImageEnhance.Brightness(image).enhance(1.04)
        with service.lock: stable=explain_image_ig(service,x,meta,service.states[0]['model'],target,n_steps=20,baseline='blur',source_image=changed)
        stability=corr(amap,stable['image_map']['abs'])
        border=np.zeros((224,224),dtype=bool); border[:22]=True;border[-22:]=True;border[:,:22]=True;border[:,-22:]=True
        top=amap>=np.quantile(amap,.95); border_mass=float(amap[top & border].sum()/max(amap[top].sum(),1e-12))
        lesion_mass=float('nan')
        if args.masks:
            mask_path=Path(args.masks)/path.name
            if mask_path.exists():
                lesion=np.asarray(Image.open(mask_path).convert('L').resize((224,224)))>0
                lesion_mass=float(amap[lesion].sum()/max(amap.sum(),1e-12))
        # target sensitivity map uses a separate fold-0 IG call for runner-up class.
        with service.lock: other=explain_image_ig(service,x,meta,service.states[0]['model'],second,n_steps=20,baseline='blur',source_image=image)
        sensitivity=corr(amap,other['image_map']['abs'])
        fold_agreement=float('nan')
        if len(rows)<20 and len(service.states)>1:
            fold_maps=[]
            for fold_state in service.states:
                with service.lock: fold_maps.append(explain_image_ig(service,x,meta,fold_state['model'],target,n_steps=10,baseline='blur',source_image=image)['image_map']['abs'])
            fold_agreement=float(np.mean([corr(fold_maps[0],other_map) for other_map in fold_maps[1:]]))
        row=dict(image=path.name,predicted_class=service.loaded.classes[target],true_class=labels.get(path.name,''),deletion_auc=deletion_auc,random_deletion_auc=rand_auc,insertion_auc=insertion_auc,random_insertion_auc=auc(random_insert),stability_spearman=stability,fold_agreement_spearman=fold_agreement,target_sensitivity_spearman=sensitivity,border_top5_mass=border_mass,lesion_attribution_mass=lesion_mass,deletion_curve=json.dumps(delete),insertion_curve=json.dumps(insert),random_deletion_curve=json.dumps(random_curve),random_insertion_curve=json.dumps(random_insert))
        rows.append(row); deletion_all.append(delete); insertion_all.append(insert); random_del_all.append(random_curve); random_ins_all.append(random_insert)
        examples.append((row, image.copy(), amap.copy()))
        source=image.copy(); side=min(source.size); left=(source.width-side)//2; top=(source.height-side)//2
        source=source.crop((left,top,left+side,top+side)).resize((224,224))
        norm=np.clip(amap/(np.percentile(amap,99)+1e-8),0,1); color=np.stack([norm,np.clip(1-abs(norm-.5)*2,0,1),1-norm],axis=-1)
        overlay=Image.blend(source,Image.fromarray((color*255).astype(np.uint8)),.45)
        overlay.save(out/f"overlay_{path.stem}.png")
        with result_file.open('a',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(row));
            if f.tell()==0: writer.writeheader()
            writer.writerow(row)
    if result_file.exists():
        with result_file.open(newline='',encoding='utf-8') as f: all_rows=list(csv.DictReader(f))
    else: all_rows=[]
    if all_rows:
        metric_names=('deletion_auc','random_deletion_auc','insertion_auc','random_insertion_auc','stability_spearman','fold_agreement_spearman','target_sensitivity_spearman','border_top5_mass','lesion_attribution_mass')
        curve_values={key:[json.loads(row[key]) for row in all_rows] for key in ('deletion_curve','insertion_curve','random_deletion_curve','random_insertion_curve')}
        deletion_mean=np.mean(curve_values['deletion_curve'],axis=0).tolist(); insertion_mean=np.mean(curve_values['insertion_curve'],axis=0).tolist(); random_del_mean=np.mean(curve_values['random_deletion_curve'],axis=0).tolist(); random_ins_mean=np.mean(curve_values['random_insertion_curve'],axis=0).tolist()
        summary={'count':len(all_rows),'metrics':{key:{'mean':float(np.nanmean([float(row[key]) for row in all_rows if row.get(key) not in ('','nan')])), 'std':float(np.nanstd([float(row[key]) for row in all_rows if row.get(key) not in ('','nan')]))} for key in metric_names},'curves':{'deletion':deletion_mean,'insertion':insertion_mean,'random_deletion':random_del_mean,'random_insertion':random_ins_mean}}
        (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        png_plot(out/'deletion.png',{'IG deletion':deletion_mean,'Random deletion':random_del_mean}); png_plot(out/'insertion.png',{'IG insertion':insertion_mean,'Random insertion':random_ins_mean})
        all_rows.sort(key=lambda item:float(item['deletion_auc'])); chosen=all_rows[:6]+all_rows[-6:]
        grid=Image.new('RGB',(3*224,4*250),'white'); draw=ImageDraw.Draw(grid)
        for i,row in enumerate(chosen):
            overlay_path=out/f"overlay_{Path(row['image']).stem}.png"
            if not overlay_path.exists(): continue
            small=Image.open(overlay_path).convert('RGB')
            x0=(i%3)*224; y0=(i//3)*250; grid.paste(small,(x0,y0)); draw.text((x0+4,y0+226),f"{row['image'][:25]} AUC {row['deletion_auc']:.3f}",fill='black')
        grid.save(out/'example_overlays.png')
    else:
        raise SystemExit('No images were evaluated.')
    print(f'Wrote evaluation artifacts to {out.resolve()}')

if __name__=='__main__': main()

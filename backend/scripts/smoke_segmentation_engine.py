"""Real nnU-Net engine smoke test using temporary UNTRAINED synthetic weights; not clinical evaluation."""
import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--allow-untrained-fixture',action='store_true',required=True)
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nnunet-synthetic-test-') as temporary:
        root=Path(temporary)
        for key,folder in [('nnUNet_raw','raw'),('nnUNet_preprocessed','preprocessed'),('nnUNet_results','results')]:
            os.environ[key]=str(root/folder);(root/folder).mkdir()
        os.environ['nnUNet_compile']='false'
        import torch
        torch.set_num_threads(2)
        from nnunetv2.experiment_planning.dataset_fingerprint.fingerprint_extractor import DatasetFingerprintExtractor
        from nnunetv2.experiment_planning.experiment_planners.default_experiment_planner import ExperimentPlanner
        from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
        from scripts.prepare_segmentation_dataset import prepare
        from segmentation.service import NnUNetService
        rows=[]
        rng=np.random.default_rng(42)
        for i in range(5):
            image=rng.integers(0,255,(64,80,3),dtype=np.uint8)
            label=np.zeros((64,80),np.uint8);label[16:48,20:60]=255
            Image.fromarray(image).save(root/f'image{i}.png');Image.fromarray(label).save(root/f'mask{i}.png')
            rows.append({'case_id':f'synthetic{i}','image':f'image{i}.png','mask':f'mask{i}.png','group_id':f'group{i}','split':'train'})
        with (root/'cases.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        dataset_path=root/'raw/Dataset501_ISICLesion'
        dataset=prepare(root/'cases.csv',dataset_path)
        DatasetFingerprintExtractor(501,num_processes=1).run()
        planner=ExperimentPlanner(501,gpu_memory_target_in_gb=1)
        planner.plan_experiment()
        plans=json.loads((root/'preprocessed/Dataset501_ISICLesion/nnUNetPlans.json').read_text())
        # Reduce only this synthetic fixture network to avoid expensive test allocations.
        architecture=plans['configurations']['2d']['architecture']['arch_kwargs']
        architecture['features_per_stage']=[min(8,v) for v in architecture['features_per_stage']]
        from nnunetv2.utilities.plans_handling.plans_handler import PlansManager
        manager=PlansManager(plans)
        network=nnUNetTrainer.build_network_architecture(manager,manager.get_configuration('2d'),3,2,enable_deep_supervision=False)
        bundle=root/'synthetic-bundle';(bundle/'fold_0').mkdir(parents=True)
        checkpoint=bundle/'fold_0/checkpoint_final.pth'
        torch.save({'network_weights':network.state_dict(),'trainer_name':'nnUNetTrainer',
                    'init_args':{'configuration':'2d'},'inference_allowed_mirroring_axes':(0,1)},checkpoint)
        (bundle/'dataset.json').write_text(json.dumps(dataset))
        (bundle/'plans.json').write_text(json.dumps(plans))
        with checkpoint.open('rb') as stream: checksum=hashlib.file_digest(stream,'sha256').hexdigest()
        (bundle/'segmentation.json').write_text(json.dumps({'task':'dermoscopic_lesion_boundary','configuration':'2d',
            'model_version':'SYNTHETIC-UNTRAINED-TEST-ONLY','folds':[0],'checkpoint_sha256':{'0':checksum}}))
        result=NnUNetService(bundle).predict(Image.open(root/'image0.png').convert('RGB'),'synthetic-fixture')
        assert result['status']=='ok' and (result['width'],result['height'])==(80,64)
        print('PASS: real nnU-Net checkpoint load, preprocessing, CPU inference and original-size mask export.')
        print('UNTRAINED SYNTHETIC FIXTURE ONLY: no lesion accuracy measured; temporary weights deleted on exit.')

if __name__=='__main__': main()

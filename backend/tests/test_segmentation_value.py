import csv
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from scripts.evaluate_segmentation_value import evaluate

class SegmentationValueTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def write(self,rows):
        path=self.root/'cases.csv'
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['case_id','image_type','anatomical_site','reference_mask','predicted_mask','true_class','original_class','manual_roi_class','segmentation_crop_class','prompt_seconds','review_seconds','manual_trace_seconds'])
            writer.writeheader();writer.writerows(rows)
        return path
    def test_no_data_does_not_fabricate_metrics(self):
        report=evaluate(self.write([]));self.assertEqual(report['status'],'not_evaluated');self.assertIsNone(report['mask_metrics'])
    def test_missing_truth_stays_missing(self):
        report=evaluate(self.write([{'case_id':'a','image_type':'clinical','anatomical_site':'unknown'}]))
        self.assertEqual(report['missing_reference_count'],1);self.assertIsNone(report['mask_metrics']);self.assertEqual(report['status'],'not_evaluated')
    def test_reports_matched_errors_and_actual_timing(self):
        Image.new('L',(8,8),255).save(self.root/'truth.png');Image.new('L',(8,8),255).save(self.root/'mask.png')
        row={'case_id':'a','image_type':'clinical','anatomical_site':'head_neck','reference_mask':'truth.png','predicted_mask':'mask.png',
             'true_class':'BCC','original_class':'BCC','manual_roi_class':'BCC','segmentation_crop_class':'NV','prompt_seconds':'4','review_seconds':'6','manual_trace_seconds':'15'}
        report=evaluate(self.write([row]));self.assertEqual(report['mask_metrics']['dice'],1)
        self.assertEqual(report['classification_comparisons']['segmentation_crop_class']['original_correct_candidate_wrong'],1)
        self.assertEqual(report['timing']['mean_assisted_seconds'],10)
        self.assertEqual(report['subgroups']['anatomical_site:head_neck']['n'],1)
        self.assertEqual(report['clinical_validation'],'not_established')
    def test_unknown_modality_and_duplicate_ids_rejected(self):
        row={'case_id':'a','image_type':'unknown'}
        with self.assertRaises(ValueError):evaluate(self.write([row]))
        row['image_type']='clinical'
        with self.assertRaises(ValueError):evaluate(self.write([row,row]))

if __name__=='__main__':unittest.main()

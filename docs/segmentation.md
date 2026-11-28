# SegFormer MiT-B2 real-only segmentation

Current default: mokshhere/skin-lesion-segformer-gate2, real_only/best.pt, Hugging Face revision 19ca826598cb59a6ac5b18b6a5636ba9298851b5. Checkpoint SHA256 d5a92fa31296a4f7c32e87cdf84683119d07dc64410253103bfa285aacb93f87. Original code revision d3d3195f13b02366cbc1332cbb57d7ca9234b7a7 at https://github.com/ishaannk/skin-lesion-seg.

## Workflow

Upload an image and click Segmentation beside the classification action. No rectangle or image-type selection is required. Mask appears on the original input image; the same button toggles its visibility. There is no separate segmentation section. Modality is recorded as unspecified, never inferred as dermoscopic. Segmentation does not change class scores.

## Exact inference policy

SMP 0.5.0 Segformer mit_b2, encoder_weights=None, classes=1. Fully strict checkpoint load after removing the publisher SMPWrapper.model namespace; no partial/random initialization. Weights-only deserialization and pinned SHA256 validation. RGB OpenCV INTER_AREA resize to 512x512, ImageNet mean/std using the publisher normalization formula. CPU float32 forward; sigmoid probabilities resized with OpenCV INTER_LINEAR to original dimensions, threshold >=0.7 selected by the publisher on validation data. No TTA, largest-component filtering, mask dilation or automatic crop. Original publisher evaluation used GPU bfloat16; identical benchmark metrics are not claimed for this CPU runtime.

## Evidence and limitations

Publisher reports native ISIC2018 test Dice 90.95%, IoU 84.74% at validation-selected threshold 0.7 (1000 images). These are publisher benchmark results, not locally reproduced accuracy or per-image confidence. Research artifact, license labelled `other`; publisher explicitly disallows diagnostic/clinical decision-making use and asks users to check upstream encoder licensing. Do not present it as fully open for arbitrary clinical/commercial use.

Training/evaluation domain: dermoscopic ISIC images. Ordinary clinical photographs can be processed for research preview but are explicitly marked outside the reported evaluation domain. No anatomical conditioning, physical size calibration, healthy/affected diagnosis or demonstrated classification benefit. Expert-reviewed independent masks are still needed for evaluation of both domains. See segmentation-value-decision.md and evaluation CSV template.

## Local start

Run start.cmd. Requires existing dermascope-backend:chatbot-dev base image and SEGMENTATION_ASSETS_PATH (defaults D:/DermascopeModelAssets/segformer-gate2-real) containing best.pt and segmentation.json. compose.segmentation.yaml mounts the bundle read-only and runs the model in a separate CPU sidecar; the active stack does not load Grounding DINO or SAM. No internet/weight download during inference. This local development bundle is not automatically available to another PC; distribute approved artifacts/builds separately with license information.

## Verification

Backend tests cover RGB/preprocessing, probability resizing, threshold, strict loading, checksum rejection, modality reporting and concurrent request rejection. Synthetic runtime/UI tests verify software only; no clinical accuracy claim.

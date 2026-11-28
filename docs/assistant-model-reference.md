# DermFM multiscale-regions technical reference

Model version: e55-multiscale-c769f025f83f3f0f. Project-authored technical review
of the supplied deployment source and current adapter. This is a model card,
not clinical validation or a treatment guideline.

## Image and metadata inputs
The website takes one dermoscopic image, age, gender and lesion location. The
model was trained with dermoscopic and clinical photographs. The website copies
the same image into both branches as an explicit single-image adaptation. That
adaptation has not been validated against the original paired-image training.
Gender is the UI label; the model's training metadata encoding is named sex.
Unknown anatomical location is supported. Patient name and patient ID are not
model inputs and are excluded from the chatbot evidence bundle.

## DermFM architecture and region reasoning
The deployment uses a visual transformer with low-rank adapters, learned region
pooling at fine and coarse scales, within-image and cross-image region relations,
and metadata-conditioned class queries. These learned soft regions are not
segmentation labels, lesion boundaries or confirmed dermoscopic structures.
The supplied architecture keeps a prototype buffer for source compatibility;
it does not use that buffer as a text-similarity classifier in its final logits.

## Ensemble and test-time augmentation
The complete checkpoint contains five fold adapters. For each fold, the runtime
averages the logits of the original image, its horizontal flip and its vertical
flip, then applies softmax. It averages the five resulting probability vectors.
The API reports five members and TTA enabled. Per-member predictions and ensemble
agreement are not exported by this runtime, so agreement must be unavailable.

## Class scores and threshold-mapped decision scores
The classifier outputs eleven raw class scores and the leading class. These
normalized model outputs are not confirmed diagnoses or calibrated disease risks.
Separate threshold-mapped decision scores can identify multiple positive
categories. They do not sum to one and are not probabilities. Their basis remains
the raw probabilities even if a validated scalar temperature is later enabled.

## Uncertainty and calibration
Normalized entropy describes spread across class scores. Top-two margin is the
difference between the largest and second-largest score. Neither is a single
trust score, a biopsy rule or evidence that the predicted class is correct.
The paired-image OOF evaluation has ECE 0.07143590649916927 and multiclass Brier
0.3194219423254189 across 5240 images. This does not evaluate the deployed
single-image five-model pipeline. Live temperature scaling is off unless the
case evidence explicitly states applied=true with a matching validated artifact.

## Explainability and missing evidence
The current new-model adapter does not expose a validated XAI result. Integrated
Gradients, Grad-CAM, SHAP and attention maps must not be claimed to have run for
this configuration. Learned internal attention is not automatically a clinical
explanation. Without matching XAI evidence, do not describe regions in the image.
OOD detection, image-quality checks, segmentation and clinical next-step prediction
are also unavailable unless the case evidence explicitly includes their results.
Conditional next-assessment references are educational, not model-predicted actions.

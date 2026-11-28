Current default switched at user request to skin-lesion-trained SegFormer MiT-B2 real_only; see segmentation.md for source, threshold, licensing and domain restrictions. Earlier SAM/detector decisions below are historical. Independent expert-mask evaluation and paired value testing remain outstanding.

Current implementation update: automatic Grounding DINO candidate localisation replaces the required doctor rectangle. SAM 2.1 remains the boundary estimator. Clinical validation and framework benefit remain unproven; evaluate absence/ambiguity as abstention, not a negative diagnosis. The protocol below remains necessary.

# Segmentation decision record: doctor-guided region boundary assistance

## Decision

Keep segmentation optional. Do not make masks a mandatory classifier input, claim improved classification, call the model anatomically conditioned, or describe it as fully clinically reliable. There is no doctor-reviewed mask set or paired value study for this application. Both clinical photographs and dermoscopic images are intended, so evaluating one modality does not validate the other.

The earlier SegFormer checkpoint is not the default: its undocumented preprocessing and dermoscopy-only reported training do not justify automatic masks on ordinary clinical photographs. An integration/synthetic smoke test establishes that software runs, not that its lesion boundaries are correct.

The replacement is official SAM 2.1 Hiera Tiny with an explicit doctor-selected rectangle. It is an open general segmentation model, not a validated skin-cancer detector or a skin-lesion-specific clinical model. It offers a region-specific spatial prompt, not learned anatomical-site conditioning. A doctor identifies the target region; the model only drafts its boundary. If simple manual ROI selection is sufficient, users can continue classification without invoking segmentation.

## Reproducible model contract

- Official code: https://github.com/facebookresearch/sam2
- Source revision: 2b90b9f5ceec907a1c18123530e92e794ad901a4
- Checkpoint: facebook/sam2.1-hiera-tiny, revision de431c4043854a71d8101e17995dfe596bf101a5
- Checkpoint SHA256: 7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69
- License: official code/checkpoint Apache-2.0; license retained in image.
- Config: configs/sam2.1/sam2.1_hiera_t.yaml
- Use build_sam2 and SAM2ImagePredictor with their official defaults. Use a supplied pixel-coordinate box and multimask_output=False. No home-grown resize, normalization, logit-threshold tuning, mask clipping or invented anatomical priors are applied.
- CPU float32 inference; no optional CUDA-connected-component cleanup, which the image predictor does not request with its default zero hole/sprinkle settings.
- An explicit image_type and rectangle are required. Anatomical site is recorded, never inferred from the photograph and never passed to SAM.
- Empty masks, border contact and mask pixels outside the selected rectangle are exposed for review. Output is not forcibly clipped to make a failure look smaller. No model quality score is presented as clinical confidence.
- Every mask needs clinician review; provenance records the model/source, image hash, image type, prompt, site and review/edit status. Intermediate predictor image embeddings are cleared after each request.

Documented inference removes guessed implementation settings; it does not remove statistical uncertainty or establish medical reliability.

## What meaningful value would mean

Predeclare the purpose with the supervisor: better boundary documentation, less clinician tracing effort, or improved classification. These are separate hypotheses. Collect expert reference boundaries and diagnoses where needed. Cover both modalities, relevant body sites and difficult cases such as facial contours, ink, hair, low contrast and glare. Do not use the same cases for method selection and final evaluation; record dataset provenance and potential pretraining overlap.

Compare three classification inputs on matched cases, with identical model weights, metadata and inference policy: original image, doctor-selected manual box, and reviewed segmentation-derived crop. Do not black out skin context without separately evaluating that changed input distribution. Record both gains and original-correct/new-wrong cases. Since the current classifier duplicates one input into two branches, keep that policy fixed and report its existing limitation.

For boundary quality report independent Dice/IoU, expert acceptability and failure examples. Report image-type and anatomical-site subgroups with sample counts; unknown sites stay unknown. Add boundary-distance metrics if clinicians identify a meaningful tolerance. No universal clinical acceptance cutoff is invented by this implementation.

For workflow value compare prompt plus review/correction time against manual tracing of the same target. A simple ROI box is not the same task as tracing a lesion boundary. Use a fair paired/randomized review protocol, account for learning effects, and include CPU latency and failure/retry rates.

If no measurable benefit appears or correction burden is excessive, keep the simple manual ROI workflow and remove segmentation from the main path. A visually pleasing mask alone is not evidence of added value.

## Current evidence

Clinical boundary accuracy: NOT EVALUATED.
Added classification value: NOT EVALUATED.
Clinician time saving: NOT EVALUATED.
Anatomical subgroup performance: NOT EVALUATED.

Official checkpoint/software integration and synthetic tests are recorded separately and must not be reported as clinical results.

## Evaluation tool

Fill segmentation-evaluation-template.csv with real observations and relative mask paths, without patient names. From repository root in an app-compatible Python environment:

```
python -m backend.scripts.evaluate_segmentation_value --cases D:/evaluation/cases.csv --output D:/evaluation/value-report.json
```

Alternatively from backend use `python -m scripts.evaluate_segmentation_value`. The report keeps absent ground truth/timing/class labels unavailable; it never manufactures a pass/fail threshold or certifies independence. The script reports observed paired accuracy, regressions, mask metrics, timing and subgroups; it does not prove independence, statistical significance or causation.

## Local deployment

Official source/checkpoint live at D:/DermascopeModelAssets/sam2.1-tiny. The current PC has critically low C:/E: disk space, so the local Compose profile mounts this dedicated public-model folder read-only instead of writing another large model layer. No image or metadata is downloaded during a web request. Other development machines need the same public bundle or a separately packaged model image; this is a local resource constraint, not a clinical setting.

The main classifier and chatbot remain separate and do not use an unreviewed mask automatically. No commit or push is performed by the setup.

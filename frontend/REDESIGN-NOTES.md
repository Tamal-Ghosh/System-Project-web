# Clinical workspace redesign

## Backup before edits

`../backups/frontend-before-clinical-redesign-20261106T051523Z.zip`

39 source/config/documentation files, ZIP integrity verified. SHA-256 sidecar is next to the archive. Dependencies, generated builds, local cache and temporary files were excluded. Restore into a separate folder and run npm ci; no restore overwrites were performed.

## Design decisions

- Supplied reference informs white surfaces, teal actions, navy typography and slate secondary text.
- Image and evidence share one desktop workspace. Classification / XAI / Uncertainty / More switch a contextual panel instead of forming a long vertical report.
- Three visible workflow stages: upload, review region, analyze/inspect. No fake completed analysis state.
- Floating assistant opens only on request and does not reserve a permanent column.
- Below 1000px, columns stack to preserve usable image and panel widths. Small screens necessarily scroll; there is no claim of zero scrolling at every viewport size.
- Model-level calibration and validation remain under Model evidence, distinct from individual-image uncertainty.

## Working local interactions

Image selection/drop, format/size/decode checks, rectangle/freehand region selection, undo/reset, centered zoom/fit, remove/replace and actual rectangular crop preview using natural-image coordinates. Original pixels are preserved. Freehand preview uses the path's bounding rectangle, not an arbitrary masked input. No training-time preprocessing is invented.

## Not connected

Inference, clinical image quality, Grad-CAM/SHAP, OOD, segmentation, advanced experiments, clinical records and chatbot inference. Their output is explicitly unavailable; no scores, risk assessments, biopsy suggestions or live-backend indicators are fabricated. Run actions are disabled until a real service exists.

## Reference research

- OHIF viewport: https://docs.ohif.org/user-guide/viewer/viewport/
- OHIF toolbar: https://docs.ohif.org/user-guide/viewer/toolbar/
- Aidoc radiology workflow: https://www.aidoc.com/solutions/radiology/
- DermEngine visual search comparison: https://help.dermengine.com/how-do-i-use-visual-search

These informed the viewport/panel/tool separation and comparison access. The chosen arrangement is our design decision; it is not a claim that the products implement our exact interface or that they validate this tool.

## Verification

TypeScript and production build; crop-boundary geometry checks. Browser interaction/visual QA could not proceed because the computer-use tool was not approved to access Chrome. Do not infer full usability/clinical validation from compilation.

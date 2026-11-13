# DermaScope — next UI review plan

Prepared for the next review on 6 November 2026, Asia/Dhaka.

## Agreed direction

- White background and cards. Neutral-gray separators, consistent sage accent.
- Calm, professional, low-density doctor workspace.
- Desktop: large image on the left, one contextual panel on the right.
- Stable AppShell; independent feature folders; SOLID boundaries.
- Foundation/developer showcase removed from doctor navigation.
- All 33 features remain on the roadmap, not all visible or implemented simultaneously.

## Navigation

Primary: Cases, Reviews, Model evidence. Add Follow-up when its workflow is implemented. Settings stays secondary. Admin navigation requires actual authorization when a backend exists.

Header: location, clear environment label, profile. Avoid duplicate toolbars and unnecessary badges. Developer instructions belong in README/architecture documentation, not clinical screens. Until real services exist, keep concise, honest demo/unavailable labels.

## Page sequence and purpose

1. **Cases:** concise page title, New case action, search/status filter, readable list. Patient code, site, status and updated time. Empty, no-match, loading and error states. No decorative charts or promotional headings.
2. **New case:** patient code, lesion location and capture date first; optional history expandable. Clear statement about whether history enters the model. Continue to upload.
3. **Prepare image:** original image viewer, rectangle/freehand/annotation distinction, undo/reset and exact input preview. Primary action: analyze confirmed input. Original is immutable.
4. **Case workspace — Result:** large image remains visible. Side panel: leading class, alternatives, calibration label and quality/rejection warnings. Assessment entry opens only when requested.
5. **Explain:** same image position. Method, target class and overlay controls. Short limitation disclosure. Grounded chatbot opens on demand, not as a persistent large transcript.
6. **More analysis:** module selector, then one graph and its controls. Agreement, crop sensitivity, stability and prediction set. Wide experiments can expand with a return-to-image action. No aggregate invented trust score.
7. **Model evidence:** separate model-level evidence. Class metrics, calibration, sample counts, subgroup/external results and missing evidence. No fabricated metric/chart when unavailable.
8. **Assessment:** clinician impression/differential, AI agreement, notes and clinician-entered next action. Draft/save/amendment states; optional blind-first workflow planned separately.
9. **Report:** clear separation of image/input provenance, AI output and doctor assessment. Draft and reviewed states; permissions for export.
10. **Reviews:** assigned queue and separate second opinion. Never overwrite the original doctor's assessment.
11. **Follow-up, later:** lesion identity, visit timeline and two-image comparison. No automatic growth or millimeter claims without appropriate registration/scale.
12. **Access/admin, later:** sign-in, request/approval/reset; users/roles and audit views. Backend case-level authorization is required.

## Interaction safeguards

- Significant warnings always visible, even when advanced panels are closed.
- Input edits make previous analysis stale; preserve its original version link.
- Heatmap opacity is display-only; crop/settings changes create a new analysis.
- Expensive analysis starts explicitly; show job status and failures.
- Preserve entered notes during recoverable errors. Add real autosave only with truthful saved/failed states.
- Chat uses authorized evidence and explicitly states missing information.
- Keyboard focus, labelled controls, colour-independent statuses and responsive navigation.

## Visual polish priorities

1. Simplify clinical page wording, remove developer-facing copy from doctor screens while keeping honest placeholders.
2. Make headings, control sizes, icon strokes and spacing consistent.
3. Keep secondary text readable; avoid very small clinical metadata.
4. Refine tab widths and right-panel scrolling without shrinking the image unnecessarily.
5. Review desktop, tablet, mobile, keyboard navigation and contrast in the actual browser.

## Next implementation order

Case-intake form → upload/selection module → input-version integration → result display → assessment/report → XAI controls → advanced-analysis modules → grounded chat → reviews/follow-up.

Model and backend dependencies are separate milestones. Do not simulate a clinical capability solely to make the interface appear complete.

## Review checklist

- Is the main action obvious on every page?
- Can the doctor inspect the image while reading relevant evidence?
- Is any screen showing more than one substantial task at once?
- Can a score be mistaken for diagnostic certainty?
- Are loading, failure, unavailable and stale states distinguishable?
- Does mobile/keyboard behaviour work in the browser, not just compile?
- Can both contributors add features without modifying the common frame?

This file is a prepared plan, not a claim that these future screens are implemented. Current build and repository checks passed; full interactive visual QA remains outstanding.

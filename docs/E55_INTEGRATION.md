# E55 integration

Branch: feature/model-integration. This separate worktree preserves the uncommitted
chatbot implementation in the original checkout. The branch was fast-forwarded to
the existing development commit before editing; no new commit or push was made.

Run RUN_E55.cmd and open http://localhost:5181/. The original E38/chatbot stack can
continue on 5180. E55 model assets are at D:\DermascopeModelAssets\e55 because E:
ran out of space during extraction. The incomplete E: checkpoint was removed; the
original ZIP is intact. Publisher builds embed the bundle at /opt/models/dermfm;
consumer machines do not need a separate weight directory. The new image tags are
dermascope-backend:dermfm-cpu-v2 and dermascope-frontend:dermfm-v2.

The backend uses the supplied Predictor, which verifies full-model checksum and
embedded source hashes. Class and site order are checked against the application.
The UI accepts one dermoscopic image and duplicates it into both image branches,
as requested. This adaptation has not been clinically validated against the original
paired-image training setup. Raw class probabilities populate the existing
score interface; threshold-mapped decision scores are separate and explicitly labeled
as not probabilities. Ensemble agreement is unavailable in the supplied output.
E38 Integrated Gradients is disabled for E55 pending a validated E55 implementation.
This integration does not copy or merge uncommitted chatbot files between branches.

Verification: actual CPU loading and paired-image inference with generated nonclinical
images returned HTTP 200, 11 raw scores summing to 1.0000000415, 11 decision scores,
and paired input policy. Runtime was 54.43 seconds. Missing clinical input and E38
XAI requests returned 422. Frontend build and synthetic API regression tests passed.
Final packaged verification: the new backend loaded offline with no host model
mount. The production frontend Nginx configuration and frontend build passed.
Both Compose services became healthy; the website returned HTTP 200 and proxied
model health returned ready. A synthetic single-image request through Nginx ran
the five-fold model in 42.814 seconds and returned 11 class scores. All 23 backend
regression tests and both packaging tests passed. Only full_model.pth is present
under /opt/models. These checks establish packaging and integration behavior,
not clinical accuracy.

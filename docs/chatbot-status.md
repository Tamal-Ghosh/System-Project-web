> **Current default: online Supabase storage (2026-11-24).** Knowledge, chat history,
> feedback and case capabilities use the private `assistant` schema through a
> restricted backend-only role. The earlier local sections below are history.
> No local DB/import is required by the default chatbot runtime. The optional
> `compose.chatbot.local.yaml` preserves rollback; existing local volumes remain.

# Chatbot integration review

Latest origin/development (239ed9c) has been merged into the chatbot working tree.
The merge and restored chatbot changes are uncommitted. The original chatbot
source is preserved in the safety stash created before integration; it was not
popped or dropped. Large local model assets and image archives were left in place.

## Changes made

Resolved three source conflicts and a database helper collision. All development
assessment/prescription database APIs are unchanged; server-owned analysis and
explanation snapshot helpers were restored. The new DermFM model, calibration
API, crop sensitivity, reports and prescriptions coexist with case tokens and chat.

Chatbot case context now preserves calibration state, threshold-mapped decision
scores, their raw-probability basis and unavailable capabilities. The new model's
unsupported XAI stays disabled. Direct calibration questions use server evidence.
Model-card retrieval is restricted to the exact model version; the old technical
card remains archived in the corpus but is excluded from new-model answers.
General lesion-class and next-assessment references remain available.

## Running locally

The isolated chatbot stack is on http://localhost:5180/:

```sh
docker compose -f compose.yaml -f compose.chatbot.yaml -f compose.chatbot-build.yaml build
```

Then run RUN_CHATBOT.cmd, or:

```sh
docker compose -f compose.yaml -f compose.chatbot.yaml up -d --wait --wait-timeout 360
```

The local overlay build reuses the already loaded dermascope-backend:dermfm-cpu-v2
weight/runtime layer. It does not duplicate model weights. The canonical full
source build remains in docker/backend.Dockerfile. A small public-document SQLite
snapshot at backend/artifacts/assistant-knowledge.sqlite is required on the
publisher build machine. It contains document text/provenance and embeddings,
not patient records, images or credentials. Only that explicitly allowed artifact
enters the image; other artifacts remain excluded. The one-shot knowledge-init
service imports existing embeddings into local pgvector without new API calls.
There are 32 chunks from four approved sources. The current model card was embedded
with explicit user approval. Model-card retrieval is restricted to the exact
model version; the older card is not relabelled or used for the new model.
Chat history and knowledge use separate named volumes; the DB has no host port.
Do not remove volumes to update application images.

## Verification and issue found

The merged suite now ran 57 tests: 56 passed and the explicit local-database test was
skipped in the general run. That database test passed separately in the disposable
local dermascope_test database, using a minimal auth.users fixture for its foreign
key. This checks storage, not doctor authentication. Both packaging tests passed.
Native and Docker frontend production builds passed. All runtime services became
healthy; the knowledge import succeeded with 25 chunks.

A generated nonclinical image verified actual new-model classification, protected
case access, a direct prediction answer (0.05 seconds), chat history and feedback.
Live Gemini embeddings and model-scoped pgvector retrieval succeeded. Initial
text requests with gemini-3.5-flash returned upstream HTTP 503. After checking
accessible models, gemini-3.5-flash-lite was verified with a generic request and
selected as the chat model. The final end-to-end smoke test passed: the grounded
answer status was answered, three reference passages were retrieved, and the full
flow including classification took 47.31 seconds.

Gemini text requests now use JSON output mode and up to three attempts for
transient transport/429/5xx failures, with jittered backoff and a thirty-second retry
budget. Long Retry-After values are not shortened; credential/configuration errors
fail immediately. Five transport regressions cover retries, bounded attempts,
credential-error redaction, Retry-After handling and JSON requests. Lite requests
leave thinking settings at the provider default. The API key and embedding model
were unchanged; only the nonsecret chat-model setting in the ignored local env
file was updated. Provider availability can still change; retries are bounded.

No Supabase migrations, Git commit, Git push or registry publish were performed.
The published model-only and calibration test stacks were not replaced.

## Existing prototype boundaries

Case capability tokens expire and are not doctor login. This stack remains local
research software, not an authenticated multi-user deployment. Clinical reference
passages are educational and do not automatically authorize patient treatment.
No matching explanation means no image-region claims. Live temperature scaling
remains off until an independent matching calibration artifact is supplied.


## Memory, citations and recovery update — 2026-11-23

Doctor login is explicitly deferred by the user. Case capability tokens remain
the local prototype access mechanism, not authenticated doctor identity.

The generator receives up to six completed question/answer pairs, bounded to
10,000 characters and scoped to the current analysis. Short follow-up retrieval
keeps the preceding question as context. Conversation text is not authoritative
evidence and is excluded from numeric evidence validation.

The browser stores only the recent case ID and token in same-tab sessionStorage.
SQLite persists token hashes, case context and separate message history in the
existing history volume. Default validity is one hour, with at most 100 case
sessions. Refresh can recover the recent conversation within that validity; it
does not restore the original image or provide a permanent patient record.
Recovery and history responses use Cache-Control: no-store. A different image
does not inherit the recovered case. Tokens still require protection against
script injection; this is not a replacement for future doctor authentication.

References are clickable and collapsible, retain source title/version, and allow
HTTPS or the exact local model-reference route only. Current-model technical
reference links enforce a matching version. Reference passages are sources
consulted, not proof of clinical correctness or sentence-level citation review.

Final regression run: 65 tests, 64 passed, one explicit local-database test
skipped. Frontend production builds passed. Runtime restart verification passed
for case recovery, saved history, invalid-token rejection, no-store headers and
versioned model-reference access.

The latest nine-case live synthetic evaluation passed six checks. The heatmap,
medication and Bengali follow-up requests encountered GeminiUnavailable rather
than returning an answer. Model-reference retrieval and generation succeeded.
The report is in ignored backend/artifacts/assistant-evaluation.json. These are
software QA checks, not clinician-reviewed clinical validation. External provider
availability remains a limitation; no fabricated fallback answer is presented.

No commit, Git push, registry publication or Supabase change was performed.

A separate reference/follow-up retry also received upstream Gemini HTTP 503.
Provider free-text availability is therefore not verified as consistently healthy.
The app preserves history and offers retry rather than manufacturing an answer.

## Provider resilience update — 2026-11-24

Generic live probes returned HTTP 200 for gemini-3.5-flash-lite and
gemini-flash-lite-latest. The ignored local env now explicitly configures the
latter as GEMINI_CHAT_FALLBACK_MODELS. No credentials were changed. Fallback is
opt-in: source defaults never silently select another provider/model. Temporary
500/502/503/504 or transport failures may advance to that configured model within
the same three-attempt, thirty-second retry budget. Rate limits keep the current
model and respect Retry-After; credential/client errors are never retried.

Removed forced zero temperature for Gemini 3 and serialize prompt text as UTF-8
rather than escaped Unicode. Both changes follow current Google troubleshooting
guidance: https://aistudio.google.com/docs/troubleshooting .

Regression suite: 67 tests, 66 passed, one database test skipped. New tests verify
explicit overload fallback and that HTTP 429 does not rotate models. This improves
resilience but does not guarantee availability of an external service.

Final post-update live synthetic evaluation: 9/9 passed, including missing XAI,
medication boundary, injected unsupported score, grounded fold reference and
Bengali follow-up. Free-text cases took 2.33–14.65 seconds in this run. This
supersedes the earlier 6/9 run as the latest observation, not an availability SLA
or clinical validation. No Git commit, push or image publication was performed.

## Conversational answer quality update — 2026-11-24

Implemented in sequence: separate social/case/disease/parameter/reason routing;
class-aware English/Bangla/Banglish follow-up resolution; readable server-owned
score percentages; natural-language synthesis; topic-filtered hybrid retrieval;
strict structured field/source identifiers; used-source-only references and
deduplicated readable links; and bounded numerical correction. Missing-XAI
reason requests are answered directly from measured case values without an
external generation request or an invented visual cause.

Numerical validation accepts explicit rounded percentages derived from current
case scores and three-decimal uncertainty presentations. It does not apply a
blanket tolerance. Only passages selected as supporting sources contribute
reference numbers. One numerical correction is allowed; a second validation
failure returns clearly labelled verified case facts rather than an unsupported
explanation. That correction may add a second bounded generation request.

Added source-attributed educational paraphrases for all eleven class labels in
docs/knowledge/classes, with a versioned manifest. Broad benchmark groups remain
heterogeneous labels, not invented specific diseases. Sources include NCI, AAD,
DermNet and the existing MILK10k taxonomy. This is provenance review, not
clinician validation. No patient records or images were embedded. The local
SQLite staging store and runtime pgvector now contain 15 documents / 66 chunks.
The script backend/scripts/index_class_references.py can reproduce staging;
only explicitly approved summaries enter retrieval.

Regression suite: 79 tests, 78 passed, one explicit local-database test skipped.
Native and Docker frontend production builds passed. A reproducible HTTP
conversation evaluation uses synthetic evidence and the user's reported
question sequence; report is kept in ignored backend/artifacts. First run
passed 5/8, with three upstream request failures. Separate diagnostics confirmed
Gemini HTTP 503 and transport failures, including generic probes of distinct
models. These failures are separate from the tested routing changes.

All changes remain local and uncommitted; no Git push, image publication or
Supabase migration was performed. Existing chat history is not rewritten.

Final HTTP conversation run: 5/8 passed. Prediction formatting, both social
turns, missing-XAI explanation and parameter review passed in 0.01–0.02 seconds.
Disease detail, Bangla disease explanation and its follow-up received HTTP 503
(20.72–24.12 seconds). Earlier Bangla generation succeeded, but that is not
consistent availability. These provider failures remain disclosed, not counted
as successful answers. All three local ports serve the new interface and backend.
Old stored messages are unchanged; new turns use the new routing and prompts.

## Supabase cutover — 2026-11-24

User explicitly requested online storage, superseding the earlier local-only
choice. Migration 010 created a private assistant schema and enabled pgvector.
Transferred 15 documents / 66 chunks, 31 existing messages, two feedback records
and the existing case-session record. Existing embeddings were copied without
new embedding API requests. SQLite safety copies and old volumes were retained.

A separate login role dermascope_chat_runtime has read-only knowledge access and
backend storage access through explicit RLS policies. PUBLIC, anon and
authenticated roles have no assistant-schema access. The runtime URL is saved
only in ignored backend/.env, with SSL required. It is not part of an image,
frontend build, Git output or this document. Existing admin DATABASE_URL remains
separate for other application features and one-time migrations.

Online API checks passed for shared cross-instance session/history access,
feedback, invalid-token rejection and restricted permissions. With the local
PostgreSQL container stopped, backend restart recovery and semantic class
retrieval from Supabase both passed. The disposable live QA history/feedback
records were removed after checking; actual migrated history was preserved.

Default compose has no local DB service, import job or history volume. Docker
images no longer require or copy the ignored SQLite knowledge snapshot. The
optional local compose configuration keeps a deliberate rollback route with a
host-mounted seed. Online failures do not silently create local replacement
storage. Classification results remain available if only chat storage fails.

Final regression suite: 83 tests, 81 passed, two optional integration groups
skipped in the network-free run. Four online-adapter integration tests passed
separately against a disposable local database before cloud migration. No
Supabase-wide public tables were replaced. No Git commit/push or registry
publication was performed. Doctor login remains a separate phase.

## Final conversation review and failure handling

Expanded routing recognizes Bangla/Banglish prediction, uncertainty, calibration
and agreement questions without external generation. Explicitly requested class
scores are not labelled the leading class. Social turns do not erase the prior
disease topic; a new named class overrides inherited context. Missing calibration
metadata is unavailable rather than silently reported as not applied.

Review of the actual live answers found English questions answered in Bangla
after Bangla history. The prompt now explicitly binds both language directions,
and a bounded language correction shares the existing single repair allowance.
The live evaluation now checks English output and short Banglish requests, not
just the presence of an answer. Clinical explanations without a selected supporting
reference abstain rather than appearing uncited.

A simulated Gemini outage verifies localized retry messaging, Retry-After, no
private diagnostics, continued verified case answers, and no failed-message
pollution in completed history. Online corpus coverage was checked for all
eleven class labels. The cloud evaluator removes only its own synthetic records
and keeps a local ignored JSON report. It is not clinician-reviewed validation.

Regression run: 93 tests, 91 passed, two optional integration groups skipped.
No commit, push, registry publication or doctor login was added. Proposed commit
message for these review fixes: fix: improve multilingual chatbot routing and
provider failure handling.

### Strengthened language and grounding review — 2026-11-25

The first 12/12 live run checked response existence and sources, but manual review
found the English disease turn was actually answered in Bangla. That run is not
claimed as passing the stronger language requirement. The strengthened rerun
passed nine of twelve: two generation requests returned HTTP 503, and a dependent
follow-up could not be counted as a sourced disease explanation.

The generator now supplies one explicit target language per turn. Disease
education receives class-specific references rather than unrelated patient/model
metrics, and prior case-parameter answers are excluded from that education
context. A focused live test then passed English output after Bangla history with
valid source IDs in 2.5 seconds. Clinical factual correctness still requires
clinician review; the automated checks are synthetic software evaluation.

Final network-free suite: 94 tests, 92 passed, two optional integration groups
skipped. The pending final targeted API report is
backend/artifacts/assistant-generation-evaluation.json; artifacts and credentials
remain ignored. No commit, push or registry publication was performed.

Final targeted online API checks passed 4/4: Banglish prediction, English BCC
education after Bangla history, Bangla disease explanation and sourced follow-up.
These generation checks explicitly verify output language and clinical reference
selection. The three generated turns took 12.00, 15.53 and 14.64 seconds in this
run. All disposable records from this evaluation were removed from Supabase.
Earlier provider/generation failures remain documented; the passing run is not
an external-service availability guarantee.

Proposed commit message (not executed):
fix: improve multilingual chatbot grounding and error handling

## Chatbox UI polish — 2026-11-25

Updated the floating chat with a white/teal header, separate case context strip,
readable message paragraphs, compact source disclosure, spaced feedback controls,
four quick-start prompts, fixed composer and optional wider reading view. Mobile
uses the available viewport width; desktop defaults to 440px, optional 570px.

History loading and restore failures are explicit. Recovery has its own retry;
feedback failures no longer use the message retry handler. Retrying a message
does not duplicate the doctor bubble. Only the chat log scrolls automatically,
not the document. Enter sends, Shift+Enter leaves a new line, and IME composition
does not submit. Cloud storage is not mislabelled as local history in the footer.

Native and Docker production builds passed. An isolated headless preview checked
1440x1000 desktop, expanded width, and 390x844 mobile without horizontal overflow
or clipped composer. Source expansion, feedback failure/retry isolation, message
retry, empty state, recovery retry and keyboard/IME behavior passed. Preview
content was synthetic and intercepted only in that temporary browser; no dummy
records were added to the application or Supabase. Model/backend code was not
changed for this UI work. No commit, push or image publication was performed.

## Eager conversation preload — 2026-11-25

The assistant panel mounts with the app shell and remains hidden/inert when
closed. Case restore and current-case history run before the launcher is clicked.
Closing/reopening retains messages, draft, source disclosures and in-flight
answers. Route changes close the floating window but no longer remount the panel
or refetch the same history. New case IDs still reset and reload scoped history.

Hidden content is removed from layout, focus order and the accessibility tree.
Automatic log scrolling runs only while visible. No speculative Gemini query is
sent, no patient history is newly persisted in browser storage, and no background
question generation or polling was added. Opening before the first preload has
finished can still show the real loading state; generated new answers still
require their normal service work.

Production build passed. Isolated delayed-network browser QA verified one case
restore and one history request before opening, zero query requests until explicit
user submission, no refetch across close/open or route changes, retained drafts,
and completion of an already submitted request while closed. Synthetic responses
were confined to the temporary browser. No commit, push or publication performed.

## Class-overview fallback active — 2026-11-25

Migration 011 and an explicit publisher seed added 22 English/Bangla educational
overviews for the eleven supported class labels to Supabase. They are private,
read-only to the chatbot runtime, and bound to approved source chunk IDs and
document checksums. Missing, retired, changed or wrong-class references fail
closed; these are educational paraphrases, not clinician validation.

After a retrieval/generation failure, or an unavailable generated answer, an
eligible general disease-overview question can receive the matching overview.
Patient-specific advice, treatment/dosage, staging, comparisons and other
custom questions are excluded. Live Gemini remains the first attempt; fallback
can still follow its retry/timeout delay and does not fix provider availability.
The UI explicitly labels the source-based overview and restores that notice
from saved history. It does not present it as a tailored live explanation,
image finding, diagnosis or predicted clinical action.

Regression suite: 99 tests, 97 passed, two optional integration groups skipped.
Cloud/API QA verified all 22 overviews and ten checks across simulated embedding
and generation outages, both languages, history preservation, custom-question
exclusion and wrong-token rejection. Only disposable QA records were removed.
Native frontend build passed; production image deployment is local only.
No new embeddings, Git commit/push or registry publication was performed.

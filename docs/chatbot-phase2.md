# Case-only assistant

After a new classification, open the floating assistant and ask about model scores,
uncertainty, ensemble agreement or limitations. The frontend calls
`POST /api/v1/chat/query` with the analysis ID and an `X-Case-Token` header.
The backend derives answers from its own de-identified analysis context.

The mock provider generates deterministic text; no external LLM or embedding API is
used. Responses identify the mock provider and carry the model version and input
hash, which the frontend verifies against the active analysis.

Each classification receives a random case capability token. Keep it in memory;
do not put it in URLs, logs or knowledge documents. It expires after one hour,
after server restart, or after eviction from the 100-case development cache.
Reclassify if a session expires. This local development mechanism is not doctor
authentication and does not authorize access to persisted database records.

XAI questions report unavailable until matching explanation evidence is connected.
There is no document retrieval in this phase. Closing the chat discards its history;
changing the analysis cancels pending requests and resets messages.

Verification: synthetic API tests check missing/wrong tokens, blank questions,
case provenance and exact uncertainty values. Context tests check identifier
filtering and explanation mismatch rejection. Frontend compilation is also checked.

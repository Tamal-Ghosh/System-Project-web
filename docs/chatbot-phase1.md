# Chatbot phase 1: analysis foundation

The inference API can save a server-generated analysis snapshot for future case grounding.
For local development, apply `backend/migrations/008_canonical_analyses.sql` to the
development database, then set `ANALYSIS_PERSISTENCE_ENABLED=true` in the backend's
local environment. Without this setting the existing inference behavior is unchanged.
If storage fails, classification still returns `persistence: not_saved`.

The API has no authentication. Use only synthetic or de-identified development data,
keep it on localhost, and do not enable this for real patient data. The migration
enables RLS and grants no browser policies; the backend database role must be managed
separately. Ownership and authorization must be implemented before exposing saved
records or using them in a chatbot. The XAI table and matching helper are groundwork;
the existing XAI endpoint does not yet save or link explanation records. Heatmaps are
not stored by this phase.

Migration is not applied automatically. Existing analysis records are not backfilled.

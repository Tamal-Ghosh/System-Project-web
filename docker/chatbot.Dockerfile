# Development overlay: reuse the already verified new-model runtime and weight layer.
FROM dermascope-backend:dermfm-cpu-v2
COPY --chown=10001:10001 backend/inference_app.py backend/medicine_catalog.py backend/database.py backend/fit_temperature.py ./
COPY --chown=10001:10001 backend/dermfm ./dermfm
COPY --chown=10001:10001 backend/assistant ./assistant
COPY --chown=10001:10001 backend/tests ./tests
COPY backend/scripts/chatbot_smoke.py /opt/chatbot_smoke.py

ENV MODEL_REFERENCE_PATH=/opt/knowledge/model-reference.md
COPY docs/assistant-model-reference.md /opt/knowledge/model-reference.md


COPY backend/scripts/evaluate_assistant.py /app/evaluate_assistant.py
COPY backend/scripts/evaluate_conversation.py /app/evaluate_conversation.py

COPY --chown=10001:10001 backend/migrations ./migrations
COPY --chown=10001:10001 backend/scripts/migrate_assistant_online.py ./scripts/migrate_assistant_online.py

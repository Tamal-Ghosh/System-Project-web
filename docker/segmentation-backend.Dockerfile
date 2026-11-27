FROM dermascope-backend:chatbot-dev
COPY --chown=10001:10001 backend/segmentation ./segmentation
COPY --chown=10001:10001 backend/inference_app.py backend/database.py ./

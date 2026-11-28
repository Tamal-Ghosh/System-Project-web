FROM dermascope-backend:chatbot-dev
USER root
COPY backend/requirements-segformer-b2.txt /tmp/requirements-segformer-b2.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements-segformer-b2.txt && python -m pip check
COPY --chown=10001:10001 backend/segmentation ./segmentation
COPY --chown=10001:10001 backend/scripts/evaluate_segmentation.py ./scripts/evaluate_segmentation.py
COPY --chown=10001:10001 backend/scripts/evaluate_segmentation_value.py ./scripts/evaluate_segmentation_value.py
ENV SEGMENTATION_MODEL_DIR=/opt/models/segmentation SEGMENTATION_DEVICE=cpu SEGMENTATION_PROVIDER=segformer_b2 TORCH_THREADS=4
USER appuser
CMD ["python","-m","uvicorn","segmentation.app:app","--host","0.0.0.0","--port","8000"]

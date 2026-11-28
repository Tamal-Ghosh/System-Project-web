# syntax=docker/dockerfile:1.7
FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 HF_HUB_OFFLINE=1 \
    E55_BUNDLE_PATH=/opt/models/dermfm \
    DERMFM_DEVICE=cpu DERMFM_TTA=true
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
RUN python -m pip install torch==2.12.1 torchvision==0.27.1 \
    --index-url https://download.pytorch.org/whl/cpu
COPY docker/requirements-cpu.txt /tmp/requirements-cpu.txt
RUN python -m pip install -r /tmp/requirements-cpu.txt && python -m pip check
WORKDIR /app
COPY --chown=10001:10001 backend/inference_app.py backend/medicine_catalog.py ./
COPY --chown=10001:10001 docker/check_model.py ./check_model.py
COPY --chown=10001:10001 backend/database.py ./
COPY --chown=10001:10001 backend/fit_temperature.py ./
COPY --chown=10001:10001 backend/dermfm ./dermfm
COPY --chown=10001:10001 backend/tests ./tests
COPY docker/healthcheck.py /opt/healthcheck.py
COPY docker/smoke_test.py /opt/smoke_test.py
# The only model copy: a separately prepared, credential-free build context.
COPY --from=model_assets --chown=10001:10001 /full_model.pth /manifest.json /architecture.py /visual_runtime.py /web_inference.py /web_api.py /evaluation.py /opt/models/dermfm/
COPY --from=model_assets --chown=10001:10001 /source/ /opt/models/dermfm/source/
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "inference_app:app", "--host", "0.0.0.0", "--port", "8000"]

COPY --chown=10001:10001 backend/segmentation ./segmentation

# The API also provides the case-grounded assistant; include it in clean source builds.
COPY --chown=10001:10001 backend/assistant ./assistant
ENV MODEL_REFERENCE_PATH=/opt/knowledge/model-reference.md
COPY docs/assistant-model-reference.md /opt/knowledge/model-reference.md

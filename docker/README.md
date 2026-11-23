# Docker development setup

Branch: feature/model-integration. No registry upload or Git push is required here.

## What the other PC needs

Docker Desktop running in Linux-container mode (Windows/macOS), or Docker Engine
with Compose on Linux. No host Python, Node, CUDA, model download or path editing.
Copy the website source (including these Docker files) and the publisher's single
`docker/bundles/dermascope-images.tar` archive. From the project root on Windows:

```cmd
RUN_DOCKER.cmd
```

Linux/macOS: `sh docker/start.sh`. First run imports both images, including all
model weights and dependencies. Later runs reuse them. Open http://localhost:5181.
If the images are already loaded, `docker compose up -d --wait --wait-timeout 360`
is sufficient. A Git clone alone cannot supply an image that has not been built
and distributed. No image has been published by this configuration.

## One-time publisher build (Tamal's PC)

Requires a working Docker engine, Python 3.13 (stdlib only for asset staging),
the extracted deployment directory, and build-time internet for base images
and package installation. It never downloads foundation weights from Hugging Face.

```powershell
powershell -ExecutionPolicy Bypass -File docker/build.ps1 `
  -Package 'D:\DermascopeModelAssets\e55' -Export
```

The script validates a strict model/source whitelist and pinned SHA256 checks,
builds both images, verifies full model loading with networking disabled and no
host model mount, waits for actual model readiness, runs backend tests, sends
a real five-fold synthetic-image request through the frontend proxy, builds the
frontend, then exports both images in one archive. Only after that succeeds is
the archive ready to hand to Progga. Do not describe an unbuilt image
as distributable. Local assets and archive outputs are ignored by Git.

Manual Linux/macOS publisher equivalent:

```sh
python3 docker/prepare_model_context.py --package /path/to/web_bundle
# Requires Docker Compose additional-context support (Compose 2.17+).
docker compose -f compose.yaml -f compose.build.yaml build
docker run --rm --network none --pull never dermascope-backend:dermfm-cpu-v2 python check_model.py
docker compose up -d --wait --wait-timeout 360
docker compose exec -T backend python -m unittest discover -s tests -v
docker compose exec -T -e SMOKE_BASE_URL=http://frontend:5173 backend python /opt/smoke_test.py
mkdir -p docker/bundles
docker save -o docker/bundles/dermascope-images.tar dermascope-backend:dermfm-cpu-v2 dermascope-frontend:dermfm-v2
```

## Packaged runtime behavior

The frontend is compiled during a multi-stage build and served by unprivileged
Nginx. Node, npm, source files and node_modules are absent from the frontend runtime.
No source bind mounts, dependency volumes or file polling are used. The backend
contains its model at /opt/models/dermfm. Nginx proxies same-origin API requests to
backend:8000. Only localhost:5181 is published.

Rebuild the affected image after source changes. Native npm run dev remains
available for frontend development. Consumer startup does not install packages.

Images target linux/amd64 CPU. Apple Silicon can emulate this platform but may be
slow; native arm64 images require a separately tested build. Allow substantial
RAM/disk in Docker Desktop; the model alone is approximately 1.24 GB, plus
Python/Torch and runtime layers. No GPU is required. Initial readiness can take minutes.
Healthchecks require status=ready, not merely HTTP 200.

```sh
docker compose ps
docker compose logs --tail 80 backend
docker compose logs --tail 80 frontend
docker compose down
```

## Boundaries

This is a local development stack without authentication/database persistence.
The single-image policy remains unvalidated against paired-view training; Docker
does not change model accuracy. Training outputs, patient uploads, tokens, host
caches and legacy ResNet weights are excluded from the normal build context.
Preserve the bundled foundation/source license and access terms when sharing.
No registry push happens automatically. A future registry release can replace
archive transfer, but publishing needs a real target and a separate explicit step.

## Test status

See docker/TEST_STATUS.md for observed results. Configuration validation and
native unit tests are distinct from a successful container build/run. Docker
Desktop engine availability is a prerequisite; do not reset existing Docker or
WSL data merely to run this project.

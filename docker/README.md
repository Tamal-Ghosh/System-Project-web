# Docker development setup

Branch: feature/docker-setup. No registry upload or Git push is required here.

## What the other PC needs

Docker Desktop running in Linux-container mode (Windows/macOS), or Docker Engine
with Compose on Linux. No host Python, Node, CUDA, model download or path editing.
Copy the website source (including these Docker files) and the publisher's single
`docker/bundles/dermascope-images.tar` archive. From the project root on Windows:

```cmd
RUN_DOCKER.cmd
```

Linux/macOS: `sh docker/start.sh`. First run imports both images, including all
model weights and dependencies. Later runs reuse them. Open http://localhost:5180.
If the images are already loaded, `docker compose up -d --wait --wait-timeout 360`
is sufficient. A Git clone alone cannot supply an image that has not been built
and distributed. No image has been published by this configuration.

## One-time publisher build (Tamal's PC)

Requires a working Docker engine, Python 3.13 (stdlib only for asset staging),
the full deployment directory or ZIP, and build-time internet for base images
and package installation. It never downloads foundation weights from Hugging Face.

```powershell
powershell -ExecutionPolicy Bypass -File docker/build.ps1 `
  -Package 'E:\3-2\system 3200\trsnformer\E38_DermFM_Deployment_FULL_WEIGHTS.zip' -Export
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
python3 docker/prepare_model_context.py --package /path/to/E38_DermFM_Deployment
# Requires Docker Compose additional-context support (Compose 2.17+).
docker compose -f compose.yaml -f compose.build.yaml build
docker run --rm --network none --pull never dermascope-backend:e38-cpu-v1 python check_model.py
docker compose up -d --wait --wait-timeout 360
docker compose exec -T backend python -m unittest discover -s tests -v
docker compose exec -T -e SMOKE_BASE_URL=http://frontend:5173 backend python /opt/smoke_test.py
docker compose exec -T frontend npm run build
mkdir -p docker/bundles
docker save -o docker/bundles/dermascope-images.tar dermascope-backend:e38-cpu-v1 dermascope-frontend:dev-v1
```

## Development behavior

Both source trees are bind-mounted: frontend HMR and backend Python reload are
enabled. No host weights or host model.local.json is mounted. The model is at
/opt/models inside the image. The frontend uses backend:8000 on the Compose
network; the browser uses the same-origin /api proxy. Only localhost:5180 is
published. Native servers on 5173/8000 can remain running.

Container node_modules uses a named volume, never Windows node_modules. The
frontend entrypoint compares package-lock.json hashes; changed dependencies
trigger npm ci inside the container (this may need internet). Ordinary source
edits require no downloads. Rebuild/re-export the backend image when Python
requirements or the model assets change. After a new frontend image import, stop
the stack and remove only its frontend_node_modules volume if dependencies need
a clean refresh; `docker compose down -v` currently removes only that dependency
volume. Revisit this before adding a database volume.

Images target linux/amd64 CPU. Apple Silicon can emulate this platform but may be
slow; native arm64 images require a separately tested build. Allow substantial
RAM/disk in Docker Desktop; the archive contains about 1.7 GB of weights plus
Python/Torch/Node layers. No GPU is required. Initial readiness can take minutes.
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

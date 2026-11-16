# Verified Docker setup - 16 November 2026

Branch: feature/docker-setup. Docker Desktop engine 29.9.3 is now running.
No new Git commit, registry upload or Git push was performed during this run.

## Passed in Docker

- Built dermascope-backend:e38-cpu-v1 with the full local foundation, all five
  trained adapters and checksum-pinned architecture source inside the image.
- Built dermascope-frontend:dev-v1 with its node_modules included. Host npm config,
  caches and virtual environments are excluded (also checked in the image).
- Both Compose services reached healthy; frontend waits for real model readiness.
- All 18 backend tests passed inside the backend container.
- Real five-fold HTTP inference through http://frontend:5173 passed: 11 finite
  scores, probabilities summing to one and site=trunk. Synthetic-image CPU
  inference took 47.043 seconds. This is not a clinical accuracy test.
- Frontend TypeScript and production build passed inside the frontend container.
- A separate backend container with --network none and no host model mounts
  loaded all five folds successfully. No weights/token/network download needed.
- Frontend CSS HMR and backend Python reload were observed in container logs.
  Temporary CSS content was restored exactly; backend source content unchanged.
- Browser-facing http://localhost:5180/health reports status=ready and model
  version e38-control-de093a6fdecdebe3 after the source reload.
- Exported both complete images to docker/bundles/dermascope-images.tar.
  Archive size: 2,057,330,688 bytes (about 2.06 GB decimal / 1.92 GiB).
- Re-imported the exported archive successfully: both image tags loaded.
- Consumer docker/start.ps1 completed successfully and the website proxy reported
  ready. SHA256 is stored beside the archive in dermascope-images.tar.sha256:
  790BBAA452CB298573E56A6AA25C4AB2EEF6A07FDAAC2A9A353C5AD4171554D7.

## Other checks

- Both consumer/publisher Compose configurations validate.
- Seven packaging/configuration tests pass: strict context whitelist, duplicate
  ZIP entry rejection, checksum integrity, credential/data exclusion, readiness
  interpretation, model-in-image paths and container proxy wiring.
- Publisher context contains exactly 12 approved model/source/license files.
- Launcher syntax checks pass. No host Python, Node, CUDA, model.local.json or
  separate model files are needed on the consumer PC after image import.

## Fixes found during the real run

- Excluded .npm-cache, .tmp, .cache, .npmrc and tsbuildinfo from build context.
  The frontend context shrank to roughly 207 KB instead of host cache payloads.
- Set container npm cache to /tmp/npm-cache.
- Allowed the precise Vite hostname frontend so the internal HTTP proxy smoke
  test is accepted; localhost remains the normal browser address.
- Added an offline model-load check to future publisher builds.
- Increased frontend health-check timeout to 30 seconds, startup grace to 60
  seconds and retries to eight. The large archive import briefly saturated I/O
  and caused the prior 10-second check to time out; the service recovered, and
  the revised consumer launcher was then verified successfully.

## Handoff

Deliver the current project source and the image archive together. On another
PC with a healthy Docker engine in Linux-container mode, RUN_DOCKER.cmd imports
missing images automatically and starts the services. The archive contains all
base/dependency/model layers. No foundation ZIP or manual weight download is
needed on that PC. Images are linux/amd64; arm64 emulation may be slower.
Only localhost:5180 is published. No registry image has been published.

The earlier bbolt startup error no longer blocks this run. No Docker or WSL data
was reset or deleted by this agent. Database/authentication and single-image
accuracy validation remain separate application work.

## Development page-load optimization

Excluded host .npm-cache/.tmp, generated dist and tsbuildinfo files from Vite
polling, and set polling interval to 750 ms. Measured HTML responses fell from
5.2-5.5 seconds to 0.008-0.039 seconds after restart; JS/CSS/health responses
were 0.004-0.054 seconds in the checked warm run. The container frontend build
passed after this configuration change. These are server response timings,
not a browser full-render benchmark. The source bind mount applies this config
without rebuilding the weight image.

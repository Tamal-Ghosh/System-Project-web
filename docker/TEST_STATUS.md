# Observed Docker setup checks - 16 November 2026

Branch: feature/docker-setup. No commit, registry upload or Git push performed.

## Passed

- Default consumer Compose configuration parses successfully.
- Publisher Compose build override, including named model context, parses.
- The staged model context contains exactly 12 approved files. Foundation, five
  adapters and architecture source match pinned SHA256 values. No tokens, caches,
  training dataset, virtual environment or reference-prediction data are included.
- Seven Docker packaging/configuration tests pass, including ZIP whitelist and
  duplicate-entry rejection, checksum rejection, ready/unavailable health handling,
  model-in-image configuration and service-DNS proxy wiring.
- All 18 existing backend application tests pass natively.
- Frontend TypeScript and production build pass natively.
- Environment-aware Vite config resolves /api and /health to backend:8000 and
  enables polling when Docker environment flags are provided.
- Node and PowerShell launcher syntax checks pass.
- The Docker HTTP smoke-test utility passed against the real native backend via
  Vite's proxy: five folds, 11 scores, site=trunk, finite probabilities summing to
  one. This synthetic-image request took 58.377 seconds on CPU. It verifies HTTP
  execution, not clinical accuracy and not Docker execution.
- The consumer launcher stops clearly if the Docker engine is unavailable.

## Blocked - not claimed as passed

Actual container image build, container startup/health, container-native tests,
container HMR and export of dermascope-images.tar could not run. The attempted
`docker compose -f compose.yaml -f compose.build.yaml build` returned:

    Error response from daemon: Docker Desktop is unable to start

Docker Desktop logs report an internal bbolt page assertion during engine startup:

    Page expected to be: 17, but self identifies as 0

A non-destructive Docker Desktop restart did not restore the engine. A separate
Ubuntu WSL registration also refers to a missing virtual disk path. Existing
Docker/WSL disks, images, volumes and distributions were not reset or deleted.

No image archive has been produced and no prebuilt image is published. Another
PC cannot use this as a completed handoff until a working Docker engine builds,
tests and exports the images. The consumer configuration intentionally refuses
implicit pulls/builds and never tries to fetch model weights at runtime.

## Finish once Docker engine is healthy

From the project root run docker/build.ps1 with -Package pointing at the complete
local deployment ZIP/directory and -Export. That script builds images, waits for
real health, runs backend tests, sends a real HTTP inference through the frontend
container, builds the frontend and exports both images. If any step fails, export
is not performed. Deliver the exported archive with the project source, then
use RUN_DOCKER.cmd on the other PC. No host Python or separate weights are needed.

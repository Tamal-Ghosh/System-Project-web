param([Parameter(Mandatory=$true)][string]$Package, [switch]$Export)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $repoRoot
try {
  $serverVersion = docker info --format '{{.ServerVersion}}'
  if ($LASTEXITCODE -ne 0 -or -not ($serverVersion -match '^\d+\.\d+')) { throw 'Docker engine is unavailable. Start Docker Desktop first.' }
  py -3.13 docker/prepare_model_context.py --package $Package
  if ($LASTEXITCODE -ne 0) { throw 'Model context preparation failed.' }
  docker compose -f compose.yaml -f compose.build.yaml build
  if ($LASTEXITCODE -ne 0) { throw 'Docker build failed.' }
  docker compose up -d --wait --wait-timeout 360
  if ($LASTEXITCODE -ne 0) { throw 'Containers did not become healthy.' }
  docker compose exec -T backend python -m unittest discover -s tests -v
  if ($LASTEXITCODE -ne 0) { throw 'Container tests failed.' }
  docker compose exec -T -e SMOKE_BASE_URL=http://frontend:5173 backend python /opt/smoke_test.py
  if ($LASTEXITCODE -ne 0) { throw 'Real proxy inference smoke test failed.' }
  docker compose exec -T frontend npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Container frontend build failed.' }
  if ($Export) {
    New-Item -ItemType Directory -Force docker/bundles | Out-Null
    docker image save -o docker/bundles/dermascope-images.tar dermascope-backend:e38-cpu-v1 dermascope-frontend:dev-v1
    if ($LASTEXITCODE -ne 0) { throw 'Image export failed.' }
    Write-Host 'Copy the repository and docker/bundles/dermascope-images.tar to the other PC.'
  }
} finally { Pop-Location }

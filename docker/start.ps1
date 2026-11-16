param([string]$Bundle = "$PSScriptRoot\bundles\dermascope-images.tar")
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $repoRoot
try {
  $serverVersion = docker info --format '{{.ServerVersion}}'
  if ($LASTEXITCODE -ne 0 -or -not ($serverVersion -match '^\d+\.\d+')) { throw 'Docker engine is unavailable. Start Docker Desktop and wait until it is running.' }
  $missing = $false
  foreach ($image in @('dermascope-backend:e38-cpu-v1','dermascope-frontend:dev-v1')) {
    docker image inspect $image *> $null
    if ($LASTEXITCODE -ne 0) { $missing = $true }
  }
  if ($missing) {
    if (-not (Test-Path -LiteralPath $Bundle)) {
      throw 'Prebuilt image bundle missing. Obtain dermascope-images.tar from the publisher; no separate weights are needed.'
    }
    docker image load -i $Bundle
    if ($LASTEXITCODE -ne 0) { throw 'Image import failed.' }
  }
  docker compose up -d --wait --wait-timeout 360
  if ($LASTEXITCODE -ne 0) { throw 'Services failed to become healthy. Check: docker compose logs backend' }
  Write-Host 'Website: http://localhost:5180  |  Stop: docker compose down'
} finally { Pop-Location }

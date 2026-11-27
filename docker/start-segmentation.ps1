param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$composeArgs = @('compose', '-f', 'compose.yaml', '-f', 'compose.chatbot.yaml', '-f', 'compose.segmentation.yaml')
function Invoke-DockerChecked {
    param([string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) { throw 'Docker command failed. Resolve the error above and run start.cmd again.' }
}
function Test-DockerEngine {
    $ErrorActionPreference = 'Continue'
    & docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}
Push-Location $repoRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker Desktop is not installed or docker is not on PATH. Install Docker Desktop, then run start.cmd again.'
    }
    Write-Host 'Checking Docker Desktop...'
    $ready = $false
    $ready = Test-DockerEngine
    if (-not $ready) {
        $desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
        if (Test-Path -LiteralPath $desktop) {
            Start-Process -FilePath $desktop -WindowStyle Hidden
        } else {
            throw 'Docker engine is stopped. Start Docker Desktop and run start.cmd again.'
        }
        Write-Host 'Waiting for Docker engine (up to 3 minutes)...'
        $deadline = (Get-Date).AddMinutes(3)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 2
            if (Test-DockerEngine) { $ready = $true; break }
        }
        if (-not $ready) { throw 'Docker engine did not become ready. Check Docker Desktop and try again.' }
    }
    $base = & docker image ls --quiet 'dermascope-backend:chatbot-dev'
    if ($LASTEXITCODE -ne 0 -or -not $base) {
        throw 'Required local base image dermascope-backend:chatbot-dev is missing. This development launcher needs the existing chatbot/model Docker setup first.'
    }
    if (-not $env:SEGMENTATION_ASSETS_PATH) { $env:SEGMENTATION_ASSETS_PATH = 'D:\DermascopeModelAssets\segformer-gate2-real' }
    if (-not (Test-Path -LiteralPath (Join-Path $env:SEGMENTATION_ASSETS_PATH 'segmentation.json'))) { throw 'Pinned SegFormer MiT-B2 bundle missing. See docs/segmentation.md.' }
    Write-Host 'Building current website sources (cached layers are reused)...'
    Invoke-DockerChecked -DockerArgs ($composeArgs + @('build'))
    Write-Host 'Starting classifier, chatbot, segmentation runtime and website...'
    Invoke-DockerChecked -DockerArgs ($composeArgs + @('up', '-d', '--wait', '--wait-timeout', '360'))
    $url = 'http://localhost:5180/'
    Write-Host "Website ready: $url" -ForegroundColor Green
    Write-Host 'SegFormer MiT-B2 uses the full input image. Choose image type, generate mask, then review. No rectangle required.'
    if (-not $NoBrowser) { Start-Process $url }
} catch {
    Write-Host ("Startup failed: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

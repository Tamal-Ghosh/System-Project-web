param([string]$Config = "$PSScriptRoot\backend\model.local.json")
$ErrorActionPreference = "Stop"
$configData = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$env:DERMFM_RECIPE = $configData.recipe
$env:DERMFM_FOUNDATION = $configData.foundation
$env:DERMFM_CHECKPOINTS = $configData.checkpoints -join ';'
$env:DERMFM_DEVICE = $configData.device
$env:DERMFM_TTA = if ($configData.tta) { 'true' } else { 'false' }
$env:PYTHONPATH = Join-Path $configData.source 'src'
$env:HF_HUB_OFFLINE = '1'
Push-Location (Join-Path $PSScriptRoot 'backend')
$runtimePython = if ($configData.python) { $configData.python } else { 'python' }
try { & $runtimePython -m uvicorn inference_app:app --host 127.0.0.1 --port 8000 }
finally { Pop-Location }

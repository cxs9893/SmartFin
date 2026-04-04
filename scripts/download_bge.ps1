param(
    [string]$ModelId = "AI-ModelScope/bge-base-zh-v1.5",
    [string]$OutputDir = "models/bge-base-zh-v1.5",
    [int]$MaxWorkers = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python command not found, please install Python 3.11+ first."
}

python - <<'PY'
import importlib.util
import sys
if importlib.util.find_spec("modelscope") is None:
    sys.exit(2)
PY

if ($LASTEXITCODE -eq 2) {
    Write-Host "modelscope is not installed, installing..."
    python -m pip install modelscope
}

# Clear invalid loopback proxy settings if present.
if ($env:ALL_PROXY -eq "http://127.0.0.1:9") { $env:ALL_PROXY = "" }
if ($env:HTTP_PROXY -eq "http://127.0.0.1:9") { $env:HTTP_PROXY = "" }
if ($env:HTTPS_PROXY -eq "http://127.0.0.1:9") { $env:HTTPS_PROXY = "" }
if ($env:GIT_HTTP_PROXY -eq "http://127.0.0.1:9") { $env:GIT_HTTP_PROXY = "" }
if ($env:GIT_HTTPS_PROXY -eq "http://127.0.0.1:9") { $env:GIT_HTTPS_PROXY = "" }

$env:MODELSCOPE_CACHE = (Join-Path $repoRoot ".modelscope-cache")
$env:HOME = $repoRoot
$env:USERPROFILE = $repoRoot

Write-Host "Starting model download: $ModelId"
Write-Host "Output directory: $OutputDir"

$py = @"
from modelscope import snapshot_download
path = snapshot_download(
    '$ModelId',
    local_dir='$OutputDir',
    max_workers=$MaxWorkers
)
print(path)
"@

$py | python -

Write-Host "Model download completed."
Write-Host "Recommended env values:"
Write-Host "FINQA_EMBEDDING_PROVIDER=bge"
Write-Host "FINQA_EMBEDDING_BGE_MODEL=$OutputDir"
Write-Host "FINQA_EMBEDDING_BGE_LOCAL_FILES_ONLY=true"

[CmdletBinding()]
param(
    [string]$Python = 'D:\projects\.venv\Scripts\python.exe',
    [string]$Model = 'gemma3:4b',
    [switch]$WithoutAI
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python was not found at $Python. Pass -Python with your environment's python.exe path."
}
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $env:AI_DIAGNOSIS_ENABLED = if ($WithoutAI) { 'false' } else { 'true' }
    $env:AI_PROVIDER = 'ollama'
    $env:OLLAMA_BASE_URL = 'http://localhost:11434'
    $env:OLLAMA_MODEL = $Model
    Write-Host 'Local console: http://127.0.0.1:8000/console'
    Write-Host 'API docs: http://127.0.0.1:8000/docs'
    Write-Host 'Current Kubernetes context:'
    & kubectl config current-context
    if ($LASTEXITCODE -ne 0) { throw 'No usable Kubernetes context. Check kubeconfig first.' }
    & $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw 'Backend exited with an error.' }
}
finally { Pop-Location }

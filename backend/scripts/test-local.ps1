[CmdletBinding()]
param(
    [switch]$Live,
    [ValidateSet('all','namespace','pod','deployment','service')]
    [string]$ResourceType = 'all',
    [string]$BaseUrl = 'http://localhost:8000',
    [string]$Namespace = 'default',
    [string]$PodName = '',
    [string]$DeploymentName = '',
    [string]$ServiceName = ''
)
$ErrorActionPreference = 'Stop'
$BackendRoot = Split-Path -Parent $PSScriptRoot
Push-Location $BackendRoot
try {
    python -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend regression tests failed.' }
    if (-not $Live) {
        Write-Host 'Offline regression passed. Run again with -Live after starting the backend to test kubectl, API and Ollama.'
        return
    }
    $BaseUrl = $BaseUrl.TrimEnd('/')
    $health = Invoke-RestMethod "$BaseUrl/api/health" -TimeoutSec 30
    if ($health.status -ne 'healthy') { throw 'Backend health check failed.' }
    $context = & kubectl config current-context
    if ($LASTEXITCODE -ne 0) { throw 'kubectl context is unavailable.' }
    Write-Host "Testing current Kubernetes context: $context"
    $models = Invoke-RestMethod 'http://localhost:11434/api/tags' -TimeoutSec 30
    Write-Host ('Available Ollama models: ' + (($models.models | ForEach-Object { $_.name }) -join ', '))

    # Select existing resources only. This script never creates, edits or deletes cluster resources.
    function Get-FirstResource([string]$Kind) {
        $raw = & kubectl get $Kind -n $Namespace -o json
        if ($LASTEXITCODE -ne 0) { throw "Cannot list $Kind in $Namespace." }
        $data = ($raw -join "`n") | ConvertFrom-Json
        if (@($data.items).Count -gt 0) { return [string]$data.items[0].metadata.name }
        return ''
    }
    if (-not $PodName) { $PodName = Get-FirstResource 'pods' }
    if (-not $DeploymentName) { $DeploymentName = Get-FirstResource 'deployments' }
    if (-not $ServiceName) { $ServiceName = Get-FirstResource 'services' }
    $targets = @(@{ kind = 'namespace'; name = $Namespace })
    foreach ($entry in @(
        @{ kind = 'pod'; name = $PodName },
        @{ kind = 'deployment'; name = $DeploymentName },
        @{ kind = 'service'; name = $ServiceName }
    )) {
        if ($entry.name) { $targets += $entry }
        else { Write-Warning "No $($entry.kind) found; that live investigation type will be skipped." }
    }
    if ($ResourceType -ne 'all') {
        $targets = @($targets | Where-Object { $_.kind -eq $ResourceType })
        if ($targets.Count -eq 0) { throw "No target available for $ResourceType." }
    }
    foreach ($target in $targets) {
        $body = @{
            namespace = $Namespace
            resource_type = $target.kind
            resource_name = $target.name
            include_previous_logs = $true
            log_tail = 100
        } | ConvertTo-Json
        Write-Host "Investigating $($target.kind)/$($target.name)..."
        $requestTimer = [System.Diagnostics.Stopwatch]::StartNew()
        $result = Invoke-RestMethod "$BaseUrl/api/v1/investigations" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 1800
        $requestTimer.Stop()
        Write-Host ("Investigation request completed in {0:N2} seconds." -f $requestTimer.Elapsed.TotalSeconds)
        if (-not $result.id) { throw 'Create response has no investigation id.' }
        if ($result.status -eq 'FAILED') { throw "Investigation failed: $($result.evidence | ConvertTo-Json -Depth 8)" }
        $loaded = Invoke-RestMethod "$BaseUrl/api/v1/investigations/$($result.id)" -TimeoutSec 30
        if ($loaded.id -ne $result.id) { throw 'Stored investigation could not be retrieved.' }
        $history = Invoke-RestMethod "$BaseUrl/api/v1/investigations?page=1&page_size=100" -TimeoutSec 30
        if (-not ($history.items | Where-Object { $_.id -eq $result.id })) { throw 'Investigation missing from history.' }
        if (-not $result.analysis.ai) { throw 'AI is disabled: set AI_DIAGNOSIS_ENABLED=true and restart the backend for the live AI test.' }
        $weights = @{ INFO = 0; LOW = 1; WARNING = 2; MEDIUM = 2; HIGH = 3; CRITICAL = 4 }
        foreach ($cause in $result.analysis.root_causes) {
            if ($weights[$result.analysis.ai.severity.ToUpper()] -lt $weights[$cause.severity.ToUpper()]) { throw 'AI downgraded deterministic severity.' }
            if ($result.analysis.ai.confidence -lt $cause.confidence) { throw 'AI downgraded deterministic confidence.' }
        }
        Write-Host "PASS: $($target.kind), status=$($result.status), id=$($result.id)"
        $result.analysis | ConvertTo-Json -Depth 20
        if ($result.analysis.ai.limitations -match 'Local AI.*unavailable') { throw 'Ollama fallback occurred; the live AI test is not complete.' }
        if ($result.status -eq 'PARTIAL') { Write-Warning 'Some evidence was unavailable; review evidence errors and AI limitations.' }
    }
    Write-Host 'Live API, history and Ollama checks completed for the listed resources.'
} finally {
    Pop-Location
}

param(
    [switch]$Open
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dataRoot = if ($env:LOCALAPPDATA) {
    Join-Path $env:LOCALAPPDATA "CodexCoordinator\MissionControl"
}
else {
    Join-Path $HOME ".local\share\codex-coordinator\mission-control"
}
$pidFile = Join-Path $dataRoot "mission-control.pid"
$url = "http://127.0.0.1:4317"

function Get-ListenerOwner {
    $listener = Get-NetTCPConnection `
        -LocalPort 4317 `
        -State Listen `
        -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @("127.0.0.1", "0.0.0.0", "::1", "::") } |
        Select-Object -First 1
    if ($listener) {
        return [int]$listener.OwningProcess
    }
    return $null
}

function Get-MissionControlProcess([int]$ProcessId) {
    $candidate = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($candidate -and $candidate.CommandLine -match '(^|\s)-m\s+(?:apps\.)?mission_control(\s|$)') {
        return $candidate
    }
    return $null
}

New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null

$listenerOwner = Get-ListenerOwner
if ($listenerOwner) {
    $listenerProcess = Get-MissionControlProcess $listenerOwner
    if (-not $listenerProcess) {
        throw "Port 4317 is already used by another application. Mission Control was not started."
    }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$url/api/health" -TimeoutSec 2
        if ($response.StatusCode -ne 200) {
            throw "Unexpected health response"
        }
    }
    catch {
        throw "A Mission Control process owns port 4317 but did not pass its health check. Stop it before restarting."
    }
    $listenerOwner | Set-Content -LiteralPath $pidFile -Encoding ascii
    if ($Open) {
        Start-Process $url
    }
    Write-Host "Mission Control is already running at $url"
    return
}

if (Test-Path -LiteralPath $pidFile) {
    $savedPid = (Get-Content -Raw -LiteralPath $pidFile).Trim()
    $existing = if ($savedPid -match '^\d+$') {
        Get-CimInstance Win32_Process -Filter "ProcessId = $savedPid" -ErrorAction SilentlyContinue
    }
    if ($existing -and $existing.CommandLine -match '(^|\s)-m\s+(?:apps\.)?mission_control(\s|$)') {
        Stop-Process -Id ([int]$savedPid) -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $pidFile -Force
}

$python = (Get-Command python -ErrorAction Stop).Source
$process = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "mission_control", "--no-open") `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -PassThru
$process.Id | Set-Content -LiteralPath $pidFile -Encoding ascii

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 200
    $process.Refresh()
    if ($process.HasExited) {
        break
    }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$url/api/health" -TimeoutSec 1
        $readyOwner = Get-ListenerOwner
        if ($response.StatusCode -eq 200 -and $readyOwner -eq $process.Id) {
            $ready = $true
            break
        }
    }
    catch {}
}

if (-not $ready) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    throw "Mission Control did not start on $url"
}

Write-Host "Mission Control is running locally at $url"
if ($Open) {
    Start-Process $url
}
Write-Host "Use apps\mission_control\stop.ps1 to stop it."

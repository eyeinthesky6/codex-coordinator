$ErrorActionPreference = "Stop"

$dataRoot = if ($env:LOCALAPPDATA) {
    Join-Path $env:LOCALAPPDATA "CodexCoordinator\MissionControl"
}
else {
    Join-Path $HOME ".local\share\codex-coordinator\mission-control"
}
$pidFile = Join-Path $dataRoot "mission-control.pid"
$stopped = [System.Collections.Generic.HashSet[int]]::new()

function Get-MissionControlProcess([int]$ProcessId) {
    $candidate = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($candidate -and $candidate.CommandLine -match '(^|\s)-m\s+(?:apps\.)?mission_control(\s|$)') {
        return $candidate
    }
    return $null
}

function Stop-MissionControlProcess([int]$ProcessId) {
    if ($stopped.Contains($ProcessId)) {
        return
    }
    $process = Get-MissionControlProcess $ProcessId
    if ($process) {
        Stop-Process -Id $ProcessId -Force
        [void]$stopped.Add($ProcessId)
    }
}

if (Test-Path -LiteralPath $pidFile) {
    $savedPid = (Get-Content -Raw -LiteralPath $pidFile).Trim()
    if ($savedPid -notmatch '^\d+$') {
        throw "The Mission Control process record is invalid. Remove it manually after checking: $pidFile"
    }
    Stop-MissionControlProcess ([int]$savedPid)
}

$listener = Get-NetTCPConnection `
    -LocalPort 4317 `
    -State Listen `
    -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalAddress -in @("127.0.0.1", "0.0.0.0", "::1", "::") } |
    Select-Object -First 1
if ($listener) {
    Stop-MissionControlProcess ([int]$listener.OwningProcess)
}

Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
if ($stopped.Count -gt 0) {
    Write-Host "Mission Control stopped."
}
else {
    Write-Host "Mission Control is not running from the background launcher."
}

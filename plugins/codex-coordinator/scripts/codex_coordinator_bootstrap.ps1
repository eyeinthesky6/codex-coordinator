param(
    [Parameter(Mandatory = $true)]
    [string]$HookPath,
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"
$minimumVersion = [Version]"3.10"

function Write-Notice([string]$Message) {
    [Console]::Error.WriteLine("Codex Coordinator: $Message")
}

function Test-Python([string]$Candidate) {
    if ([string]::IsNullOrWhiteSpace($Candidate)) { return $null }
    try {
        $resolved = (Get-Item -LiteralPath $Candidate -ErrorAction Stop).FullName
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = New-Object System.Diagnostics.ProcessStartInfo
        $process.StartInfo.FileName = $resolved
        $process.StartInfo.Arguments = '-c "import sys; print(str(sys.version_info[0]) + ''.'' + str(sys.version_info[1]))"'
        $process.StartInfo.UseShellExecute = $false
        $process.StartInfo.RedirectStandardOutput = $true
        $process.StartInfo.RedirectStandardError = $true
        $process.StartInfo.CreateNoWindow = $true
        if (-not $process.Start()) { return $null }
        if (-not $process.WaitForExit(3000)) {
            $process.Kill()
            return $null
        }
        $versionText = $process.StandardOutput.ReadToEnd().Trim()
        $version = [Version]$versionText
        if ($process.ExitCode -eq 0 -and $version -ge $minimumVersion) { return $resolved }
    } catch {
        return $null
    }
    return $null
}

function Find-CompatiblePython {
    $candidates = New-Object System.Collections.Generic.List[string]

    foreach ($name in @("python", "python3")) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue
        if ($command) { $candidates.Add($command.Source) }
    }

    $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
    if ($launcher) {
        try {
            & $launcher.Source -0p 2>$null | ForEach-Object {
                if ($_ -match '^\s*-V:[^\s]+\s+(.+python\.exe)\s*$') { $candidates.Add($Matches[1]) }
            }
        } catch { }
    }

    foreach ($hive in @("HKCU:\Software\Python\PythonCore", "HKLM:\Software\Python\PythonCore", "HKLM:\Software\WOW6432Node\Python\PythonCore")) {
        if (-not (Test-Path $hive)) { continue }
        Get-ChildItem $hive -ErrorAction SilentlyContinue | ForEach-Object {
            $installPath = Join-Path $_.PSPath "InstallPath"
            try {
                $root = (Get-Item -LiteralPath $installPath -ErrorAction Stop).GetValue("")
                if ($root) { $candidates.Add((Join-Path $root "python.exe")) }
            } catch { }
        }
    }

    $roots = New-Object System.Collections.Generic.List[string]
    if ($env:LOCALAPPDATA) { $roots.Add((Join-Path $env:LOCALAPPDATA "Programs\Python")) }
    if ($env:ProgramFiles) { $roots.Add((Join-Path $env:ProgramFiles "Python")) }
    if (${env:ProgramFiles(x86)}) { $roots.Add((Join-Path ${env:ProgramFiles(x86)} "Python")) }
    if ($env:USERPROFILE) { $roots.Add((Join-Path $env:USERPROFILE ".cache\codex-runtimes")) }
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        Get-ChildItem -LiteralPath $root -Filter python.exe -File -Recurse -Depth 5 -ErrorAction SilentlyContinue |
            ForEach-Object { $candidates.Add($_.FullName) }
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        $compatible = Test-Python $candidate
        if ($compatible) { return $compatible }
    }
    return $null
}

function Emit-MissingPythonContext([string]$Detail) {
    @{
        continue = $true
        hookSpecificOutput = @{
            hookEventName = "SessionStart"
            additionalContext = "Codex Coordinator could not start because Python 3.10 or newer was not found. $Detail Install Python 3.10+ and start a new Codex task; no environment setting was changed."
        }
    } | ConvertTo-Json -Compress -Depth 4
}

$python = Find-CompatiblePython
if (-not $python -and -not $NoInstall) {
    Write-Notice "Python 3.10+ was not found in PATH, the Python launcher, the registry, standard install folders, or Codex runtime folders. Attempting a user-scoped Python install now."
    $winget = Get-Command winget -CommandType Application -ErrorAction SilentlyContinue
    if ($winget) {
        try {
            & $winget.Source install --id Python.Python.3.13 --exact --scope user --silent --disable-interactivity --accept-package-agreements --accept-source-agreements 2>&1 |
                ForEach-Object { [Console]::Error.WriteLine($_) }
        } catch {
            Write-Notice "The user-scoped Python install failed: $($_.Exception.Message)"
        }
        $python = Find-CompatiblePython
    }
}

if (-not $python) {
    $detail = if ($NoInstall) { "Automatic installation was disabled for this check." } else { "No supported user-scoped installer was available, or installation failed." }
    Emit-MissingPythonContext $detail
    exit 0
}

$payload = [Console]::In.ReadToEnd()
$process = New-Object System.Diagnostics.Process
$process.StartInfo = New-Object System.Diagnostics.ProcessStartInfo
$process.StartInfo.FileName = $python
$process.StartInfo.Arguments = '"' + $HookPath.Replace('"', '\"') + '"'
$process.StartInfo.UseShellExecute = $false
$process.StartInfo.RedirectStandardInput = $true
$process.StartInfo.RedirectStandardOutput = $true
$process.StartInfo.RedirectStandardError = $true
$process.StartInfo.CreateNoWindow = $true
if (-not $process.Start()) {
    Write-Notice "The selected Python runtime could not start the SessionStart hook."
    exit 1
}
$process.StandardInput.Write($payload)
$process.StandardInput.Close()
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$process.WaitForExit()
[Console]::Out.Write($stdout)
[Console]::Error.Write($stderr)
exit $process.ExitCode

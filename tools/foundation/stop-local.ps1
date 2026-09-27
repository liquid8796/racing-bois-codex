$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$record = Join-Path $root '_local/server-session.json'
if (-not (Test-Path -LiteralPath $record)) { Write-Host 'No managed local demo session recorded.'; exit 0 }
$session = Get-Content -LiteralPath $record -Raw | ConvertFrom-Json
$process = Get-Process -Id ([int]$session.pid) -ErrorAction SilentlyContinue
if (-not $process) { Write-Host 'The recorded demo is already stopped.'; exit 0 }
$expectedStart = ([DateTime]$session.startTimeUtc).ToUniversalTime()
$buildRoot = [IO.Path]::GetFullPath((Join-Path $root 'Build')) + [IO.Path]::DirectorySeparatorChar
if (-not ([IO.Path]::GetFullPath($session.exe)).StartsWith($buildRoot,[StringComparison]::OrdinalIgnoreCase) -or
    $process.Path -ne $session.exe -or
    [Math]::Abs(($process.StartTime.ToUniversalTime() - $expectedStart).TotalSeconds) -gt 1) {
    throw 'The PID no longer matches the task-owned demo; no process was stopped.'
}
Stop-Process -Id $process.Id
Write-Host 'Racing Bois local demo stopped.'

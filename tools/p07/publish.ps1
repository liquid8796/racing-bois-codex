param(
    [Parameter(Mandatory=$true)][string]$WebRoot,
    [Parameter(Mandatory=$true)][string]$ReleaseId,
    [ValidateSet('win-x64','linux-arm64')][string]$Runtime = 'win-x64'
)
$ErrorActionPreference = 'Stop'
if ($ReleaseId -notmatch '^[a-zA-Z0-9-]{1,48}$') { throw 'Invalid release ID.' }
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$web = [IO.Path]::GetFullPath($WebRoot)
if (-not (Test-Path -LiteralPath (Join-Path $web 'index.html'))) { throw 'Complete Web output is required.' }
$output = Join-Path $projectRoot "Build/LanHost/$Runtime-p07-$ReleaseId"
if (Test-Path -LiteralPath $output) { throw 'Use a new output directory for each release.' }
if ($Runtime -eq 'win-x64') {
    & (Join-Path $projectRoot 'tools/p05/publish-lan.ps1') -Output $output -WebRoot $web
} else {
    & (Join-Path $projectRoot 'tools/foundation/publish-lan.ps1') -Runtime $Runtime -Output $output -WebRoot $web
}
if ($LASTEXITCODE -ne 0) { throw 'Host publish failed.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README-P07.md') -Destination (Join-Path $output 'README-P07.md')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README-P07.md') -Destination (Join-Path $output 'README.txt') -Force
if ($Runtime -eq 'win-x64') {
    @'
@echo off
cd /d "%~dp0"
RacingBois.Server.Host.exe --WebRoot "%~dp0web" --DataRoot "%~dp0data" --RealmKind offline %*
exit /b %ERRORLEVEL%
'@ | Set-Content -LiteralPath (Join-Path $output 'launch-local.bat') -Encoding ASCII
    & (Join-Path $projectRoot 'tools/p05/verify-package.ps1') -PackageRoot $output -WriteManifest
} else {
    foreach ($mode in @('local','lan')) {
        $lan = if ($mode -eq 'lan') { '--AllowLan true ' } else { '' }
        $script = '#!/bin/sh' + "`n" + 'set -eu' + "`n" + 'cd -- "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"' + "`n" +
            'exec ./RacingBois.Server.Host ' + $lan + '--WebRoot "$(pwd)/web" --DataRoot "$(pwd)/data" --RealmKind offline "$@"' + "`n"
        [IO.File]::WriteAllText((Join-Path $output "launch-$mode.sh"), $script, [Text.UTF8Encoding]::new($false))
    }
}
Write-Output "Published P07: $output"

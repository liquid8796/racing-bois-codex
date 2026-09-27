param(
    [Parameter(Mandatory=$true)][string]$Output,
    [Parameter(Mandatory=$true)][string]$WebRoot
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$outputPath = if ([IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $repoRoot $Output }
$resolvedOutput = [IO.Path]::GetFullPath($outputPath)
$buildRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'Build'))
if (-not $resolvedOutput.StartsWith($buildRoot.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'P05 package output must be a fresh directory below this project Build folder.' }
if (Test-Path -LiteralPath $resolvedOutput) { throw 'Output already exists. Choose a new versioned directory; player data and previous packages are never overwritten.' }
$resolvedWeb = (Resolve-Path -LiteralPath $WebRoot).Path
$null = & (Join-Path $PSScriptRoot 'audit-web.ps1') -WebRoot $resolvedWeb -RequireHttpCompatible
# Reuse the established self-contained runtime publisher. Its destination is
# fresh, so no previous package or data is replaced by its web-copy step.
& (Join-Path $repoRoot 'tools/foundation/publish-lan.ps1') -Runtime 'win-x64' -Output $resolvedOutput -WebRoot $resolvedWeb
if ($LASTEXITCODE -ne 0) { throw 'Foundation publish did not complete.' }
foreach ($file in @('launch-lan.ps1','launch-lan.bat','show-lan-addresses.ps1','show-lan-addresses.bat','audit-web.ps1','verify-package.ps1','README-P05.md')) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination (Join-Path $resolvedOutput $file) -Force }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'lan') -Destination (Join-Path $resolvedOutput 'lan') -Recurse
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README-P05.md') -Destination (Join-Path $resolvedOutput 'README.txt') -Force
$audit = & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $resolvedOutput -WriteManifest
$audit | ConvertTo-Json -Depth 8

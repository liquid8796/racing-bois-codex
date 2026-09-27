#Requires -Version 5.1
<#
.SYNOPSIS
Verify the exact direct Unity MCP dependency; install only into a missing sibling directory.
.DESCRIPTION
The default and -VerifyOnly perform local reads only. -Install may clone the pinned
repository when the target directory does not exist. Existing directories are
verified without reset, checkout, pull, fetch, cleanup, or configuration changes.
#>
[CmdletBinding()]
param(
    [switch]$VerifyOnly,
    [switch]$Install
)

$ErrorActionPreference = 'Stop'
if ($VerifyOnly -and $Install) {
    throw 'Choose -VerifyOnly or -Install; the default is read-only verification.'
}

$dependencyRemote = 'https://github.com/liquid8796/unity-mcp.git'
$dependencyCommit = '0f9776ffc5cc35c2e1482455178fde21c58e0b48'
$dependencyVersion = '10.2.1-beta.7'
$dependencyName = 'com.coplaydev.unity-mcp'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\', '/')
$siblingParent = [IO.Directory]::GetParent($projectRoot).FullName
$dependencyRoot = [IO.Path]::GetFullPath((Join-Path $siblingParent 'unity-mcp')).TrimEnd('\', '/')
$packageRoot = Join-Path $dependencyRoot 'MCPForUnity'

function Assert-PlainPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $cursor = [IO.Path]::GetFullPath($Path)
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Linked/reparse dependency paths are not supported: $cursor"
            }
        }
        $parent = [IO.Directory]::GetParent($cursor)
        if ($null -eq $parent) { break }
        $cursor = $parent.FullName
    }
}

function Read-GitText {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string[]]$GitArguments
    )
    # Suppress optional index refresh writes during status and other local reads.
    $output = & git --no-optional-locks -C $Repository @GitArguments
    if ($LASTEXITCODE -ne 0) { throw "Git verification failed: $($GitArguments[0])" }
    return (($output | Out-String).Trim())
}

function Assert-ManifestPath {
    param([string]$Value, [string]$Label)
    if ([string]::IsNullOrWhiteSpace($Value) -or -not $Value.StartsWith('file:', [StringComparison]::Ordinal)) {
        throw "$Label must declare the direct local Unity MCP package using file:."
    }
    $declared = $Value.Substring(5).Replace('/', [IO.Path]::DirectorySeparatorChar)
    if (-not [IO.Path]::IsPathRooted($declared)) {
        $declared = Join-Path (Join-Path $projectRoot 'Packages') $declared
    }
    $resolved = [IO.Path]::GetFullPath($declared).TrimEnd('\', '/')
    if (-not $resolved.Equals($packageRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label points to '$resolved', but this checkout requires sibling '$packageRoot'. Review docs/SETUP.md; this script never rewrites package files."
    }
}

function Assert-Dependency {
    if (-not (Test-Path -LiteralPath $dependencyRoot -PathType Container)) {
        throw "Unity MCP dependency is missing: $dependencyRoot. Run this script with -Install to create that absent directory."
    }
    Assert-PlainPath $dependencyRoot
    $gitDirectory = Join-Path $dependencyRoot '.git'
    if (-not (Test-Path -LiteralPath $gitDirectory -PathType Container)) {
        throw 'Existing dependency must be its own normal Git checkout. It will not be replaced or converted.'
    }
    Assert-PlainPath $gitDirectory
    $top = Read-GitText $dependencyRoot @('rev-parse', '--show-toplevel')
    if (-not [IO.Path]::GetFullPath($top).TrimEnd('\', '/').Equals($dependencyRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Dependency Git root differs from the intended sibling directory.'
    }
    $remote = Read-GitText $dependencyRoot @('remote', 'get-url', 'origin')
    if (-not $remote.Equals($dependencyRemote, [StringComparison]::Ordinal)) {
        throw 'Existing dependency origin is not the pinned remote. No changes were made.'
    }
    $revision = Read-GitText $dependencyRoot @('rev-parse', 'HEAD')
    if (-not $revision.Equals($dependencyCommit, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Existing dependency revision differs from required $dependencyCommit. No checkout, reset or pull was performed."
    }
    $dirty = Read-GitText $dependencyRoot @('status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none')
    if (-not [string]::IsNullOrWhiteSpace($dirty)) {
        throw 'Existing dependency has staged, modified or untracked files. Preserve and resolve them explicitly; no cleanup was performed.'
    }
    $packageFile = Join-Path $packageRoot 'package.json'
    Assert-PlainPath $packageFile
    if (-not (Test-Path -LiteralPath $packageFile -PathType Leaf)) { throw 'Pinned Unity MCP package.json is missing.' }
    $package = Get-Content -LiteralPath $packageFile -Raw | ConvertFrom-Json
    if ($package.name -ne $dependencyName -or $package.version -ne $dependencyVersion) {
        throw 'Pinned Unity MCP package identity/version does not match the expected contract.'
    }
}

Get-Command git -ErrorAction Stop | Out-Null
Assert-PlainPath $projectRoot
Assert-PlainPath $dependencyRoot
$expectedTarget = [IO.Path]::GetFullPath((Join-Path $siblingParent 'unity-mcp')).TrimEnd('\', '/')
if (-not $dependencyRoot.Equals($expectedTarget, [StringComparison]::OrdinalIgnoreCase) -or
    $dependencyRoot.Equals($projectRoot, [StringComparison]::OrdinalIgnoreCase) -or
    -not [IO.Directory]::GetParent($dependencyRoot).FullName.Equals($siblingParent, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Dependency target escaped the exact intended sibling directory.'
}

$manifestFile = Join-Path $projectRoot 'Packages/manifest.json'
$lockFile = Join-Path $projectRoot 'Packages/packages-lock.json'
Assert-PlainPath $manifestFile
Assert-PlainPath $lockFile
$manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
$packageLock = Get-Content -LiteralPath $lockFile -Raw | ConvertFrom-Json
Assert-ManifestPath $manifest.dependencies.$dependencyName 'Packages/manifest.json'
Assert-ManifestPath $packageLock.dependencies.$dependencyName.version 'Packages/packages-lock.json'
if ($packageLock.dependencies.$dependencyName.source -ne 'local') {
    throw 'Unity MCP lock entry must identify a local source.'
}

$installedNow = $false
if (-not (Test-Path -LiteralPath $dependencyRoot)) {
    if (-not $Install) { Assert-Dependency }
    # No replacement or merge is attempted. A failed clone is deliberately kept
    # for inspection; the next run will reject it as an existing invalid checkout.
    & git clone --no-checkout --no-hardlinks -- $dependencyRemote $dependencyRoot
    if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency clone failed; any partial checkout has been preserved.' }
    & git -C $dependencyRoot fetch --no-tags origin $dependencyCommit
    if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency fetch failed; the new checkout has been preserved.' }
    & git -C $dependencyRoot checkout --detach $dependencyCommit
    if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency checkout failed; the new checkout has been preserved.' }
    $installedNow = $true
}
Assert-Dependency
[pscustomobject]@{
    passed = $true
    mode = $(if ($installedNow) { 'installed-and-verified' } else { 'verify-only' })
    repository = $dependencyRoot
    remote = $dependencyRemote
    commit = $dependencyCommit
    package = $dependencyName
    version = $dependencyVersion
    packageFilesModified = $false
} | ConvertTo-Json

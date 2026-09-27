param(
    [string]$PackageRoot = $PSScriptRoot,
    [ValidateRange(1024,65535)][int]$Port = 7777,
    [string]$DataRoot = '',
    [switch]$LocalOnly,
    [switch]$PlanOnly,
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
function Get-NativeSha256([string]$Path) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $hasher.Dispose() }
}
function Assert-UnlinkedPath([string]$Path) {
    $candidatePath = [IO.Path]::GetFullPath($Path)
    while ($candidatePath) {
        if (Test-Path -LiteralPath $candidatePath) {
            $item = Get-Item -LiteralPath $candidatePath -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Package/data paths must not traverse links or junctions.' }
        }
        $parent = [IO.Directory]::GetParent($candidatePath)
        $candidatePath = if ($parent) { $parent.FullName } else { $null }
    }
}
$package = [IO.Path]::GetFullPath($PackageRoot)
Assert-UnlinkedPath $package
$manifestPath = Join-Path $package 'package-manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'Extract the complete native LAN candidate package first.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.schema -ne 1 -or $manifest.kind -ne 'native-lan-host-candidate' -or $manifest.runtime -ne 'win-x64' -or $manifest.realmKind -ne 'offline' -or $manifest.releaseAccepted -ne $false -or -not $manifest.files) { throw 'Native LAN candidate manifest is invalid.' }
$expected = @{}
foreach ($row in $manifest.files) {
    $relative = [string]$row.path
    if (-not $relative -or $relative -match '[\\:<>"|?*\x00-\x1f]' -or $relative.StartsWith('/') -or $relative.EndsWith('/') -or $relative -match '(^|/)(\.|\.\.|\s.*|.*[. ]|CON(?:\..*)?|PRN(?:\..*)?|AUX(?:\..*)?|NUL(?:\..*)?|COM[1-9](?:\..*)?|LPT[1-9](?:\..*)?)(/|$)' -or $relative.Contains('//') -or $relative -eq 'package-manifest.json' -or $expected.ContainsKey($relative)) { throw 'Manifest has an unsafe or duplicate file path.' }
    $path = Join-Path $package $relative
    Assert-UnlinkedPath $path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or $row.sha256 -notmatch '^[a-f0-9]{64}$' -or (Get-Item -LiteralPath $path).Length -ne $row.bytes -or (Get-NativeSha256 $path) -cne $row.sha256) { throw "Package file is missing or changed: $relative" }
    $expected[$relative] = $true
}
$actual = @()
foreach ($item in Get-ChildItem -LiteralPath $package -Recurse -Force) {
    Assert-UnlinkedPath $item.FullName
    if ($item.PSIsContainer) { continue }
    $relative = $item.FullName.Substring($package.TrimEnd('\','/').Length + 1).Replace('\','/')
    if ($relative -eq 'package-manifest.json') { continue }
    if (-not $expected.ContainsKey($relative)) { throw "Unregistered file in package: $relative" }
    $actual += $relative
}
if ($actual.Count -ne $expected.Count) { throw 'Package file count differs from manifest.' }
foreach ($required in @('RacingBois.Server.Host.exe','RacingBois.Server.Host.dll','RacingBois.Server.Host.runtimeconfig.json','coreclr.dll','hostfxr.dll','hostpolicy.dll','System.Private.CoreLib.dll','e_sqlite3.dll','Microsoft.AspNetCore.Server.Kestrel.Core.dll','launch-native-lan.ps1','launch-native-lan.bat','README.txt','public/README.txt')) {
    if (-not $expected.ContainsKey($required)) { throw "Required native file absent from manifest: $required" }
}
$runtime = (Get-Content -LiteralPath (Join-Path $package 'RacingBois.Server.Host.runtimeconfig.json') -Raw -Encoding UTF8 | ConvertFrom-Json).runtimeOptions
if ($runtime.framework -or $runtime.frameworks -or -not $runtime.includedFrameworks) { throw 'Native package requires an external runtime.' }
if ($VerifyOnly) {
    [pscustomobject]@{ verified=$true; files=$actual.Count; runtime=$manifest.runtime; protocolVersion=$manifest.protocolVersion; contentHash=$manifest.contentHash; releaseAccepted=$false } | ConvertTo-Json
    return
}
if (-not $DataRoot) {
    $localData = [Environment]::GetFolderPath('LocalApplicationData')
    if (-not $localData) { throw 'Local application data directory is unavailable; pass a dedicated -DataRoot.' }
    $DataRoot = Join-Path $localData 'RacingBois/OfflineLan/default'
}
$data = [IO.Path]::GetFullPath($DataRoot)
Assert-UnlinkedPath $data
$packagePrefix = $package.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
if ($data.TrimEnd('\','/') -eq $package.TrimEnd('\','/') -or $data.StartsWith($packagePrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'DataRoot must be outside the immutable package and its public directory.' }
$publicRoot = Join-Path $package 'public'
$executable = Join-Path $package 'RacingBois.Server.Host.exe'
$allowLan = if ($LocalOnly) { 'false' } else { 'true' }
$arguments = @('--AllowLan', $allowLan, '--Port', [string]$Port, '--EnableTls', 'false', '--TrustLocalProxy', 'false', '--RealmKind', 'offline', '--DataRoot', $data, '--WebRoot', $publicRoot)
$plan = [pscustomobject]@{ executable=$executable; packageRoot=$package; dataRoot=$data; publicRoot=$publicRoot; arguments=$arguments; localEndpoint="ws://127.0.0.1:$Port/multiplayer"; bind= $(if ($LocalOnly) { 'loopback' } else { 'LAN' }); realmKind='offline'; releaseAccepted=$false }
if ($PlanOnly) { $plan | ConvertTo-Json -Depth 4; return }
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { throw "Port $Port is occupied; choose another -Port. No process was stopped." }
Write-Host 'Racing Bois native offline LAN candidate host'
Write-Host "This PC: $($plan.localEndpoint)"
if (-not $LocalOnly) { Write-Host "Other PCs: ws://HOST-LAN-IP:$Port/multiplayer (replace HOST-LAN-IP with this PC's private LAN IPv4 address)." }
Write-Host "Private offline realm: $data"
Write-Host 'Keep this window open; Ctrl+C stops the host. Firewall rules are unchanged.'
& $executable @arguments
if ($LASTEXITCODE -ne 0) { throw "Native LAN host exited with code $LASTEXITCODE." }

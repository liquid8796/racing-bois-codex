param([Parameter(Mandatory=$true)][string]$PackageRoot, [switch]$WriteManifest, [switch]$SkipSelfTest)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $PackageRoot).Path
if ($WriteManifest) {
    $liveDirectories = @('data','realm-data') | Where-Object { Test-Path -LiteralPath (Join-Path $root $_) }
    $realmFiles = @(Get-ChildItem -LiteralPath $root -Recurse -File -Filter 'realm.json*' -ErrorAction SilentlyContinue)
    if (@($liveDirectories).Count -gt 0 -or $realmFiles.Count -gt 0) { throw 'Publishing a package with an existing player-data directory or realm file is forbidden. Use a fresh output directory.' }
}
foreach ($file in @('RacingBois.Server.Host.exe','RacingBois.Server.Host.runtimeconfig.json','hostfxr.dll','hostpolicy.dll','coreclr.dll','System.Private.CoreLib.dll','Microsoft.AspNetCore.Server.Kestrel.Core.dll','web/index.html','launch-lan.ps1','launch-lan.bat','show-lan-addresses.ps1','show-lan-addresses.bat','lan/lan-functions.ps1','lan/qrcodegen.js','lan/qrcodegen.LICENSE.txt','lan/vendor-provenance.json','lan/join.js','lan/join.template.html','README-P05.md')) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $file) -PathType Leaf)) { throw "Incomplete Windows offline package: $file" }
}
$batch = Get-Content -LiteralPath (Join-Path $root 'launch-lan.bat') -Raw
if ($batch -notmatch 'powershell\.exe.*launch-lan\.ps1') { throw 'LAN batch does not invoke the P05 persistent-data launcher.' }
$qrProvenance = Get-Content -LiteralPath (Join-Path $root 'lan/vendor-provenance.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $root 'lan/qrcodegen.js') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $qrProvenance.sha256) { throw 'Vendored QR bytes differ from the reviewed upstream snapshot.' }
$config = Get-Content -LiteralPath (Join-Path $root 'RacingBois.Server.Host.runtimeconfig.json') -Raw | ConvertFrom-Json
if ($config.runtimeOptions.framework -or $config.runtimeOptions.frameworks -or -not $config.runtimeOptions.includedFrameworks) { throw 'Host requires an externally installed runtime instead of the bundled self-contained runtime.' }
$webAudit = & (Join-Path $PSScriptRoot 'audit-web.ps1') -WebRoot (Join-Path $root 'web') -RequireHttpCompatible
$selfTest = $null
if (-not $SkipSelfTest) {
    $output = & (Join-Path $root 'RacingBois.Server.Host.exe') --SelfTest
    if ($LASTEXITCODE -ne 0) { throw 'Bundled native host SelfTest failed.' }
    $selfTest = ($output -join [Environment]::NewLine) | ConvertFrom-Json
    if ($selfTest.status -ne 'PASS') { throw 'Bundled host SelfTest did not report PASS.' }
}
$entries = @()
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File) {
    $relative = $file.FullName.Substring($root.TrimEnd('\','/').Length + 1).Replace('\','/')
    if ($relative -match '^(data/|realm-data/|LAN_JOIN\.html$|package-manifest\.json$|offline-package-audit\.json$)') { continue }
    $entries += [pscustomobject]@{ path=$relative; bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$manifestPath = Join-Path $root 'package-manifest.json'
if ($WriteManifest) {
    [pscustomobject]@{ generatedUtc=[DateTime]::UtcNow.ToString('o'); runtime='win-x64 self-contained'; files=$entries } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
} else {
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Package manifest missing. Build with the P05 publisher first.' }
    $expected = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $actual = @{}; foreach ($entry in $entries) { $actual[$entry.path] = $entry }
    foreach ($entry in $expected.files) {
        if (-not $actual.ContainsKey($entry.path) -or $actual[$entry.path].sha256 -ne $entry.sha256) { throw "Package hash mismatch: $($entry.path)" }
    }
}
$result = [pscustomobject]@{
    passed=$true; packageRoot=$root; bundledRuntime=$true; immutableFileCount=$entries.Count
    nativeSelfTest=$selfTest; web=$webAudit
    offlineQr='Vendored MIT JavaScript; generated address page and SVG are local, without CDN or runtime downloads.'
    acceptance='Packaging/static dependency/native smoke only. No global network/firewall changes were made; independent two-machine LAN cold-cache acceptance remains unverified.'
}
if ($WriteManifest) { $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root 'offline-package-audit.json') -Encoding UTF8 }
$result

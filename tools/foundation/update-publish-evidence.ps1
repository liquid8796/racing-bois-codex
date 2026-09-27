param([string]$WindowsPackage = 'Build/LanHost/win-x64', [string]$ArmPackage = 'Build/LanHost/linux-arm64')
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$records = @()
$smoke = $null
foreach ($runtime in @('win-x64', 'linux-arm64')) {
    $relativePackage = if($runtime -eq 'win-x64'){$WindowsPackage}else{$ArmPackage}
    $publishPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $relativePackage))
    if (-not (Test-Path -LiteralPath $publishPath)) { continue }
    $files = @(Get-ChildItem -LiteralPath $publishPath -File -Recurse)
    $hostName = if ($runtime -eq 'win-x64') { 'RacingBois.Server.Host.exe' } else { 'RacingBois.Server.Host' }
    if ($runtime -eq 'win-x64') {
        $smokeJson = & (Join-Path $publishPath $hostName) --SelfTest
        if ($LASTEXITCODE -ne 0) { throw 'Self-contained Windows smoke failed.' }
        $smoke = $smokeJson | ConvertFrom-Json
    }
    $webPath = Join-Path $publishPath 'web'
    $webFiles = @()
    if (Test-Path -LiteralPath $webPath) {
        $webFiles = @(Get-ChildItem -LiteralPath $webPath -File -Recurse | ForEach-Object {
            [ordered]@{path=$_.FullName.Substring($webPath.Length + 1).Replace('\','/'); bytes=$_.Length; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
        } | Sort-Object { $_.path })
    }
    $records += [ordered]@{
        runtime=$runtime; relativePath=$publishPath.Substring($repoRoot.Length+1).Replace('\','/'); files=$files.Count; bytes=($files | Measure-Object Length -Sum).Sum
        executableSha256=(Get-FileHash -LiteralPath (Join-Path $publishPath $hostName) -Algorithm SHA256).Hash
        hostDllSha256=(Get-FileHash -LiteralPath (Join-Path $publishPath 'RacingBois.Server.Host.dll') -Algorithm SHA256).Hash
        applicationDllSha256=(Get-FileHash -LiteralPath (Join-Path $publishPath 'RacingBois.Server.Application.dll') -Algorithm SHA256).Hash
        selfContained=$true; includesUnityWeb=(Test-Path -LiteralPath (Join-Path $webPath 'index.html'))
        excludesDoNotShip=(@($webFiles | Where-Object { $_.path -match '(?i)_DoNotShip' }).Count -eq 0)
        webFiles=$webFiles
        execution=$(if ($runtime -eq 'win-x64') {'PASS local selftest'} else {'PUBLISHED; current remote execution tracked separately by parent task'})
    }
}
[ordered]@{
    generatedUtc=[DateTimeOffset]::UtcNow.ToString('o'); windowsSelfTest=$smoke; outputs=$records
    scope='Self-contained native runtime and deployable Unity Web payload snapshots. These hashes identify this publish; WAN-disabled two-machine LAN acceptance is still separate.'
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $repoRoot 'docs\p02\backend\publish-evidence.json') -Encoding utf8
Write-Host 'Updated docs/p02/backend/publish-evidence.json'

param([string]$Output = 'docs/p05/backend/source-manifest.json')
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
Push-Location $projectRoot
try {
    $directories = @(
        'Packages/com.racingbois.foundation/Runtime/Definitions',
        'Packages/com.racingbois.foundation/Runtime/Simulation',
        'Packages/com.racingbois.foundation/Runtime/Protocol',
        'Packages/com.racingbois.foundation/Runtime/NetworkMapping',
        'Assets/RacingBois/Client/Application',
        'src/Shared',
        'src/Server',
        'src/Tests/RacingBois.P05Client.Tests',
        'src/Tests/RacingBois.Multiplayer.Integration.Tests',
        'src/Tests/RacingBois.Multiplayer.LiveProbe',
        'src/Tests/RacingBois.Foundation.Tests',
        'src/Tests/RacingBois.RaceIntegration.Tests',
        'src/Tests/RacingBois.Gameplay.Tests'
    )
    $sourcePaths = @(& rg --files @directories)
    if ($LASTEXITCODE -ne 0) { throw 'Could not enumerate P05 backend source.' }
    $sourcePaths += @(
        'global.json',
        'src/global.json',
        'src/Directory.Build.props',
        'tools/foundation/publish-lan.ps1',
        'tools/foundation/resolve-web-root.ps1',
        'tools/p05/publish-lan.ps1',
        'tools/p05/launch-lan.ps1',
        'tools/p05/launch-lan.bat',
        'tools/p05/show-lan-addresses.ps1',
        'tools/p05/show-lan-addresses.bat',
        'tools/p05/lan/lan-functions.ps1',
        'tools/p05/audit-web.ps1',
        'tools/p05/verify-package.ps1',
        'tools/p05/capture-backend-source.ps1'
    )
    foreach ($optional in @('Directory.Build.props','Directory.Build.targets','src/Directory.Build.targets')) {
        if (Test-Path -LiteralPath (Join-Path $projectRoot $optional)) { $sourcePaths += $optional }
    }
    $extensions = @('.cs','.csproj','.props','.targets','.json','.asmdef','.ps1','.bat')
    $sourcePaths = @($sourcePaths | Where-Object { [IO.Path]::GetExtension($_) -in $extensions } |
        ForEach-Object { $_.Replace([char]92,[char]47) } | Sort-Object -Unique)
    [Array]::Sort($sourcePaths, [StringComparer]::Ordinal)
    $entries = @($sourcePaths | ForEach-Object {
        $sourceFile = Get-Item -LiteralPath (Join-Path $projectRoot $_)
        [ordered]@{
            path = $_
            sha256 = (Get-FileHash -LiteralPath $sourceFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            bytes = $sourceFile.Length
        }
    })
    $lines = @($entries | ForEach-Object { $_.path + "`t" + $_.sha256 })
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { $digest = $algorithm.ComputeHash([Text.Encoding]::UTF8.GetBytes(($lines -join "`n") + "`n")) }
    finally { $algorithm.Dispose() }
    $sourceHash = ([BitConverter]::ToString($digest)).Replace('-', '').ToLowerInvariant()
    $manifest = [ordered]@{
        generatedUtc = [DateTime]::UtcNow.ToString('o')
        sourceHash = $sourceHash
        hashRecipe = 'SHA256 of UTF8(no BOM): ordinal path-order entries as path + TAB + lowercase file SHA256 + LF'
        scope = 'P05 shared definitions/simulation/protocol/network mapping; actual Unity Client Application; native shared/server sources; P05 client, multiplayer domain/live probes and legacy foundation/race/gameplay regressions; SDK/project properties and host publishing/launcher helpers. Presentation, art, Web transport adapters and compiled payloads are separate evidence.'
        files = $entries
    }
    $outputPath = if ([IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $projectRoot $Output }
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($outputPath)) | Out-Null
    [IO.File]::WriteAllText($outputPath, ($manifest | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
    [pscustomobject]@{ sourceHash = $sourceHash; files = $entries.Count; output = $outputPath }
}
finally { Pop-Location }

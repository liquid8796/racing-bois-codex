param([string]$Output = 'docs/p03p04/backend/source-manifest.json')
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
Push-Location $projectRoot
try {
    $sourcePaths = @(& rg --files 'Packages/com.racingbois.foundation/Runtime' 'Assets/RacingBois/Client/Application' 'src/Shared' 'src/Server' 'src/Tests/RacingBois.Foundation.Tests' 'src/Tests/RacingBois.RaceIntegration.Tests')
    if ($LASTEXITCODE -ne 0) { throw 'Could not enumerate backend source.' }
    $sourcePaths += @('global.json', 'src/global.json', 'src/Directory.Build.props', 'tools/foundation/publish-lan.ps1', 'tools/p03p04/capture-backend-source.ps1')
    $sourcePaths = @($sourcePaths | Where-Object { [IO.Path]::GetExtension($_) -in '.cs', '.csproj', '.props', '.json', '.asmdef', '.ps1' } | ForEach-Object { $_.Replace('\', '/') } | Sort-Object -Unique)
    [Array]::Sort($sourcePaths, [StringComparer]::Ordinal)
    $entries = @($sourcePaths | ForEach-Object {
        $sourceFile = Get-Item -LiteralPath (Join-Path $projectRoot $_)
        [ordered]@{ path = $_; sha256 = (Get-FileHash -LiteralPath $sourceFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant(); bytes = $sourceFile.Length }
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
        scope = 'Shared gameplay/protocol, actual Unity Application sources, native server, integration/regression harnesses, project properties and package publishing helper. Presentation/art and compiled binaries are separate evidence.'
        files = $entries
    }
    $outputPath = if ([IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $projectRoot $Output }
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($outputPath)) | Out-Null
    [IO.File]::WriteAllText($outputPath, ($manifest | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
    [pscustomobject]@{ sourceHash = $sourceHash; files = $entries.Count; output = $outputPath }
}
finally { Pop-Location }

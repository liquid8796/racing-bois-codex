param([string]$ExistingPackage = 'Build/LanHost/win-x64-p03p04-4c12566')
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$source = (Resolve-Path -LiteralPath (Join-Path $repo $ExistingPackage)).Path
$fixture = Join-Path $repo ('_local/p05-package-validation-' + [DateTime]::UtcNow.ToString('yyyyMMddHHmmssfff'))
if (Test-Path -LiteralPath $fixture) { throw 'Fixture already exists.' }
# Test-only copy of a previously verified P03/P04 package. Never the P05 deliverable.
Copy-Item -LiteralPath $source -Destination $fixture -Recurse
foreach ($file in @('launch-lan.ps1','launch-lan.bat','show-lan-addresses.ps1','show-lan-addresses.bat','audit-web.ps1','verify-package.ps1','README-P05.md')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination (Join-Path $fixture $file) -Force
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'lan') -Destination (Join-Path $fixture 'lan') -Recurse
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README-P05.md') -Destination (Join-Path $fixture 'README.txt') -Force
$cases = @()
function Expect-Rejection([string]$Name, [scriptblock]$Action, [string]$Message) {
    $rejected=$false
    try { $null = & $Action } catch { if ($_.Exception.Message -like $Message) { $rejected=$true } else { throw } }
    if (-not $rejected) { throw "Expected rejection: $Name" }
    $script:cases += [pscustomobject]@{name=$Name;passed=$true}
}
$web = Join-Path $fixture 'web'
Expect-Rejection 'native Brotli entrypoint refused for HTTP LAN' { & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $fixture -WriteManifest -SkipSelfTest } '*HTTP LAN compression incompatible*'
$conversion = & node (Join-Path $PSScriptRoot 'convert-web-fixture-to-gzip.mjs') $web
if ($LASTEXITCODE -ne 0) { throw 'Could not construct real gzip regression fixture.' }
$conversion = $conversion | ConvertFrom-Json
$baseline = & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $fixture -WriteManifest
$cases += [pscustomobject]@{name='real gzip fixture and bundled native self-test';passed=$baseline.passed}
$index = Join-Path $web 'index.html'; $original = [IO.File]::ReadAllBytes($index)
try {
    $html = [Text.Encoding]::UTF8.GetString($original)
    [IO.File]::WriteAllText($index, $html.Replace("loader.src='Build/", "loader.src='https://example.invalid/"))
    Expect-Rejection 'external CDN loader refused' { & (Join-Path $PSScriptRoot 'audit-web.ps1') -WebRoot $web } '*External or absolute*'
} finally { [IO.File]::WriteAllBytes($index,$original) }
try {
    $html = [Text.Encoding]::UTF8.GetString($original)
    $brotliScript = $conversion.files[1].source
    [IO.File]::WriteAllText($index, $html.Replace('</body>', ('<script src="' + $brotliScript + '"></script></body>')))
    Expect-Rejection 'additional Brotli script refused for HTTP LAN' { & (Join-Path $PSScriptRoot 'audit-web.ps1') -WebRoot $web -RequireHttpCompatible } '*HTTP LAN compression incompatible*'
} finally { [IO.File]::WriteAllBytes($index,$original) }
$data = Get-ChildItem -LiteralPath (Join-Path $web 'Build') -Filter '*.data.gz' | Select-Object -First 1
$original = [IO.File]::ReadAllBytes($data.FullName)
try {
    [IO.File]::WriteAllBytes($data.FullName, [byte[]]@(0,0,0,0))
    Expect-Rejection 'renamed non-gzip bytes refused' { & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $fixture -SkipSelfTest } '*Invalid gzip Unity payload*'
} finally { [IO.File]::WriteAllBytes($data.FullName,$original) }
try {
    $badCrc = [byte[]]$original.Clone()
    $badCrc[$badCrc.Length-8] = [byte]($badCrc[$badCrc.Length-8] -bxor 1)
    [IO.File]::WriteAllBytes($data.FullName,$badCrc)
    Expect-Rejection 'corrupt gzip trailer refused' { & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $fixture -SkipSelfTest } '*Invalid gzip Unity payload*'
} finally { [IO.File]::WriteAllBytes($data.FullName,$original) }
$original = [IO.File]::ReadAllBytes($index)
try {
    [IO.File]::WriteAllBytes($index, [byte[]]@($original + [Text.Encoding]::UTF8.GetBytes('<!-- fixture change -->')))
    Expect-Rejection 'payload tamper refused' { & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $fixture -SkipSelfTest } '*Package hash mismatch*'
} finally { [IO.File]::WriteAllBytes($index,$original) }
$runtime = Join-Path $fixture 'RacingBois.Server.Host.runtimeconfig.json'; $original = [IO.File]::ReadAllBytes($runtime)
try {
    [IO.File]::WriteAllText($runtime,'{"runtimeOptions":{"framework":{"name":"Microsoft.NETCore.App","version":"10.0.9"}}}')
    Expect-Rejection 'external runtime dependency refused' { & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $fixture -SkipSelfTest } '*externally installed runtime*'
} finally { [IO.File]::WriteAllBytes($runtime,$original) }
New-Item -ItemType Directory -Path (Join-Path $fixture 'data') | Out-Null
[IO.File]::WriteAllText((Join-Path $fixture 'data/fixture-only.json'),'{"fixture":true}')
[IO.File]::WriteAllText((Join-Path $fixture 'LAN_JOIN.html'),'<p>Generated fixture page</p>')
$verification = & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $fixture -SkipSelfTest
$cases += [pscustomobject]@{name='generated address page and private data do not invalidate immutable hashes';passed=$verification.passed}
Expect-Rejection 'publishing player data refused' { & (Join-Path $PSScriptRoot 'verify-package.ps1') -PackageRoot $fixture -WriteManifest -SkipSelfTest } '*existing player-data directory*'
Expect-Rejection 'publisher never overwrites existing output' { & (Join-Path $PSScriptRoot 'publish-lan.ps1') -Output $source -WebRoot $web } '*Output already exists*'
$receipt = [pscustomobject]@{passed=$true;cases=$cases;fixture=$fixture;sourcePackage=$source;gzipConversion=$conversion;actualP05PackagePublished=$false;scope='P05 packaging failure gates using a copied previous-phase runtime and its actual Brotli payloads transcoded to gzip. This is not final P05 native/browser acceptance or a production compression conversion.'}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $repo 'docs/p05/lan/package-validator-tests.json') -Encoding UTF8
$receipt | Select-Object passed,actualP05PackagePublished,fixture

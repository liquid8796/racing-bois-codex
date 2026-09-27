param([Parameter(Mandatory=$true)][string]$WebRoot, [string]$Receipt = '', [switch]$RequireHttpCompatible)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $WebRoot).Path
$indexPath = Join-Path $root 'index.html'
if (-not (Test-Path -LiteralPath $indexPath -PathType Leaf)) { throw 'Offline Web payload has no index.html.' }
$html = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8
$dependencies = @()
foreach ($property in @('dataUrl','frameworkUrl','codeUrl')) {
    $match = [regex]::Match($html, $property + '\s*:\s*[''"''](?<path>[^''"'']+)[''"'']')
    if (-not $match.Success) { throw "Unity entrypoint does not declare $property." }
    $dependencies += $match.Groups['path'].Value
}
$loader = [regex]::Match($html, '\.src\s*=\s*[''"''](?<path>[^''"'']+\.loader\.js)[''"'']')
if (-not $loader.Success) { throw 'Unity loader path not found in entrypoint.' }
$dependencies += $loader.Groups['path'].Value
foreach ($match in [regex]::Matches($html, '<script\b[^>]*\bsrc\s*=\s*[''"''](?<path>[^''"'']+)[''"'']', 'IgnoreCase')) { $dependencies += $match.Groups['path'].Value }
foreach ($match in [regex]::Matches($html, '<link\b[^>]*\bhref\s*=\s*[''"''](?<path>[^''"'']+)[''"'']', 'IgnoreCase')) { $dependencies += $match.Groups['path'].Value }
$verified = @()
foreach ($dependency in $dependencies | Select-Object -Unique) {
    if ($dependency -match '^(?:[a-z][a-z0-9+.-]*:|//|[\\/])') { throw "External or absolute entrypoint dependency is not offline-safe: $dependency" }
    $resolved = [IO.Path]::GetFullPath((Join-Path $root $dependency))
    if (-not $resolved.StartsWith($root.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Dependency escapes Web root: $dependency" }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Missing bundled Web dependency: $dependency" }
    $verified += [pscustomobject]@{ path=$dependency; bytes=(Get-Item -LiteralPath $resolved).Length; sha256=(Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$compression = @()
$httpCompatible = $true
foreach ($payload in $dependencies | Select-Object -Unique) {
    $format = if ($payload -match '\.gz$') { 'gzip' } elseif ($payload -match '\.br$') { 'brotli-native' } elseif ($payload -match '\.unityweb$') { 'unverified-javascript-fallback' } else { 'uncompressed' }
    $compatible = $format -in @('gzip','uncompressed')
    if (-not $compatible) {
        $httpCompatible = $false
        if ($RequireHttpCompatible) { throw "HTTP LAN compression incompatible: $payload. P05 requires gzip or uncompressed Unity payloads; native Brotli requires HTTPS in Chrome/Firefox, and no JavaScript decompression fallback is verified by this publisher." }
    }
    $decodedBytes = $null
    if ($format -eq 'gzip') {
        $stream = $null; $gzip = $null
        try {
            $stream = [IO.File]::OpenRead((Join-Path $root $payload))
            if ($stream.ReadByte() -ne 31 -or $stream.ReadByte() -ne 139) { throw 'Missing gzip signature.' }
            $stream.Position = 0
            $gzip = New-Object IO.Compression.GZipStream($stream, [IO.Compression.CompressionMode]::Decompress)
            $buffer = New-Object byte[] 65536
            $decodedBytes = [long]0
            while (($read = $gzip.Read($buffer, 0, $buffer.Length)) -gt 0) { $decodedBytes += $read }
            if ($decodedBytes -eq 0) { throw 'Empty Unity gzip payload.' }
        } catch { throw "Invalid gzip Unity payload: $payload. $($_.Exception.Message)" }
        finally { if ($gzip) { $gzip.Dispose() }; if ($stream) { $stream.Dispose() } }
    }
    $compression += [pscustomobject]@{ path=$payload; format=$format; httpCompatible=$compatible; gzipDecodedBytes=$decodedBytes }
}
$externalStyles = @()
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in @('.html','.css') }) {
    $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    foreach ($match in [regex]::Matches($text, '(?:url\(\s*[''"'']?|@import\s+[''"''])(?:https?:)?//[^)''"''\s]+', 'IgnoreCase')) { $externalStyles += $match.Value }
}
if ($externalStyles.Count -gt 0) { throw 'External CSS/font resource found: ' + ($externalStyles -join ', ') }
$forbidden = @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.FullName -match '(?i)_DoNotShip|\.pfx$|\.pem$|\.key$|\.env(?:\.|$)' })
if ($forbidden.Count -gt 0) { throw 'Web payload contains debug or credential files.' }
$result = [pscustomobject]@{
    passed=$true; webRoot=$root; entrypointDependenciesLocal=$true; externalCssFonts=0
    verifiedDependencies=$verified
    httpCompatibilityRequired=[bool]$RequireHttpCompatible; httpCompressionCompatible=$httpCompatible; compression=$compression
    compressionReference='https://docs.unity3d.com/6000.0/Documentation/Manual/webgl-deploying.html'
    scope='Static entrypoint/CSS dependencies, compression-format compatibility and exact bundled file hashes. Gzip bytes are decoded locally. This does not validate live HTTP Content-Encoding headers, two-machine cold-cache offline browser execution or every runtime network request inside Unity code.'
}
if ($Receipt) { $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Receipt -Encoding UTF8 }
$result

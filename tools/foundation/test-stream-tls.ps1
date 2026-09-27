param(
    [int]$Port = 17977,
    [int]$TlsPort = 17978,
    [switch]$SkipHostBuild,
    [string]$CertificateThumbprint = '4A86FB613F6695369527C155710ABA7FBC8F75B1'
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$evidence = Join-Path $repoRoot 'docs\p02\backend'
$certificatePath = Join-Path $evidence 'localhost-development-public.cer'
$certificate = Get-Item -LiteralPath "Cert:\CurrentUser\My\$CertificateThumbprint"
# X509ContentType.Cert exports public bytes only; never PFX, password or private key.
[IO.File]::WriteAllBytes($certificatePath, $certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
Push-Location $repoRoot
try {
    foreach ($requiredPort in @($Port, $TlsPort, 17981, 17982, 17983, 17984, 17985)) {
        if (Get-NetTCPConnection -LocalPort $requiredPort -State Listen -ErrorAction SilentlyContinue) { throw "Probe port $requiredPort occupied." }
    }
    if (-not $SkipHostBuild) {
        & dotnet build src/Server/RacingBois.Server.Host -c Release
        if ($LASTEXITCODE -ne 0) { throw 'Host build failed.' }
    }
    $hostDll = Join-Path $repoRoot 'src\Server\RacingBois.Server.Host\bin\Release\net10.0\RacingBois.Server.Host.dll'
    $stdout = Join-Path $env:TEMP "racing-bois-p02-stream-$Port.stdout.log"
    $stderr = Join-Path $env:TEMP "racing-bois-p02-stream-$Port.stderr.log"
    $process = Start-Process dotnet -ArgumentList @('"' + $hostDll + '"', '--Port', $Port, '--TlsPort', $TlsPort, '--EnableTls', 'true') -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    try {
        $ready = $false
        for ($i = 0; $i -lt 50; $i++) {
            if ($process.HasExited) { throw 'TLS host exited during startup.' }
            try { $null = Invoke-RestMethod "http://127.0.0.1:$Port/health"; $ready = $true; break } catch { Start-Sleep -Milliseconds 100 }
        }
        if (-not $ready) { throw 'TLS host readiness timed out.' }
        & dotnet run --project src/Tests/RacingBois.StreamProbe -c Release -- $Port $TlsPort $certificatePath (Join-Path $evidence 'stream-tls-evidence.json')
        if ($LASTEXITCODE -ne 0) { throw 'Stream/TLS probe failed; inspect JSON evidence.' }
        Invoke-RestMethod "http://127.0.0.1:$Port/health" | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'server-health-after-stream-probe.json') -Encoding UTF8
    } finally {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id }
    }
} finally { Pop-Location }

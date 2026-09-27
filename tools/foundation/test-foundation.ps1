param([switch]$SkipTransport, [int]$Port = 17877)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$evidence = Join-Path $repoRoot 'docs\p02\backend'
Push-Location $repoRoot
try {
    & dotnet run --project src/Tests/RacingBois.Foundation.Tests -c Release -- (Join-Path $evidence 'foundation-tests.json')
    if ($LASTEXITCODE -ne 0) { throw 'Foundation tests failed.' }
    & dotnet build src/Server/RacingBois.Server.Host -c Release
    if ($LASTEXITCODE -ne 0) { throw 'Host build failed.' }
    & dotnet src/Server/RacingBois.Server.Host/bin/Release/net10.0/RacingBois.Server.Host.dll --SelfTest
    if ($LASTEXITCODE -ne 0) { throw 'Host smoke failed.' }
    if (-not $SkipTransport) {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listener) { throw "Port $Port already occupied; choose another -Port." }
        $hostDll = Join-Path $repoRoot 'src\Server\RacingBois.Server.Host\bin\Release\net10.0\RacingBois.Server.Host.dll'
        $stdout = Join-Path $env:TEMP "racing-bois-p02-$Port.stdout.log"
        $stderr = Join-Path $env:TEMP "racing-bois-p02-$Port.stderr.log"
        $process = Start-Process dotnet -ArgumentList @('"' + $hostDll + '"', '--Port', $Port) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        try {
            $ready = $false
            for ($i = 0; $i -lt 50; $i++) {
                if ($process.HasExited) { throw 'Test host exited during startup.' }
                try { $null = Invoke-RestMethod "http://127.0.0.1:$Port/health"; $ready = $true; break } catch { Start-Sleep -Milliseconds 100 }
            }
            if (-not $ready) { throw 'Test host readiness timed out.' }
            & dotnet run --project src/Tests/RacingBois.TransportProbe -c Release -- "ws://127.0.0.1:$Port/ws" (Join-Path $evidence 'transport-evidence.json')
            if ($LASTEXITCODE -ne 0) { throw 'Transport probe failed.' }
            Invoke-RestMethod "http://127.0.0.1:$Port/health" | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'server-health-after-probe.json') -Encoding UTF8
        } finally {
            if (-not $process.HasExited) { Stop-Process -Id $process.Id }
        }
    }
} finally { Pop-Location }

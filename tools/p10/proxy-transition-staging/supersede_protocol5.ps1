param([switch]$StopVerifiedProbe)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$folder = Join-Path $workspace 'docs/p10/network/20260926T213110Z'
$run = Get-Content -LiteralPath (Join-Path $folder 'run.json') -Raw | ConvertFrom-Json
$probe = Get-Content -LiteralPath (Join-Path $folder 'probe.json') -Raw | ConvertFrom-Json
if ($run.runId -ne '20260926T213110Z' -or $run.probePid -ne 15344 -or $run.serverPid -ne 20968) { throw 'Unexpected old run ownership.' }
$process = Get-CimInstance Win32_Process -Filter 'ProcessId = 15344'
$expectedDll = Join-Path $run.fixturePrivateRoot 'probe/ProtocolSoakNext.dll'
if ($null -eq $process -or $process.Name -ne 'dotnet.exe' -or $process.CommandLine.IndexOf($expectedDll,[StringComparison]::OrdinalIgnoreCase) -lt 0) { throw 'Exact task-owned probe identity could not be verified.' }
# Never print or store the command line. The receipt records the bounded match.
$drift = @()
foreach ($entry in $run.sources.PSObject.Properties) {
    $source = Join-Path $workspace $entry.Name
    if (!(Test-Path -LiteralPath $source) -or (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { $drift += $entry.Name }
}
if (!$StopVerifiedProbe) { @{exactOwnedProbeVerified=$true;pid=15344;seconds=$probe.elapsedSeconds;sourceStableNow=($drift.Count -eq 0);eightHourGate=$false} | ConvertTo-Json; return }
$recordPath = Join-Path $folder 'intentional-supersession.json'
if (Test-Path -LiteralPath $recordPath) { throw 'Supersession record already exists; do not overwrite.' }
Copy-Item -LiteralPath (Join-Path $folder 'run.json') -Destination (Join-Path $folder 'run-before-intentional-supersession.json')
Copy-Item -LiteralPath (Join-Path $folder 'probe.json') -Destination (Join-Path $folder 'probe-before-intentional-supersession.json')
$record = [ordered]@{
    schema=1;status='INTENTIONALLY_SUPERSEDED';recordedUtc=[DateTime]::UtcNow.ToString('O');runId=$run.runId
    reason='Protocol5 trace proved omitted deterministic pedestrian recovery/waiting context, wrong proxy contact order and missing already-active combat forecast. Root approved protocol6 candidate after isolated regression/fuzz; an incomplete run with known defects cannot be final acceptance.'
    approvedCandidateManifestSha256='294f5c105f6be2f939234c2b9c88fc746f330f63c4ac0763e464751c78e3b41b'
    exactOwnedProbeVerified=$true;stoppedProbePid=15344;supervisorOwnsServerPid=20968
    requestedSeconds=$probe.requestedSeconds;elapsedSeconds=$probe.elapsedSeconds;cycles=$probe.cycles;reconnects=$probe.reconnects;storms=$probe.storms
    oldSourceSha256=$run.sourceSha256;sourceStableNow=($drift.Count -eq 0);changedSourcesNow=$drift;eightHourGate=$false
    rawProbeSha256=(Get-FileHash -LiteralPath (Join-Path $folder 'probe-before-intentional-supersession.json') -Algorithm SHA256).Hash.ToLowerInvariant()
    scope='Only the exact verified task-owned probe is stopped. Its supervisor owns server cleanup. Raw running/interrupted/FAIL reports are preserved, never relabelled PASS.'
}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
Stop-Process -Id 15344 -ErrorAction Stop
for ($i=0;$i -lt 20;$i++) { if ($null -eq (Get-Process -Id 20968 -ErrorAction SilentlyContinue)) { break }; Start-Sleep -Milliseconds 500 }
$record.ownedProbeStopped = $null -eq (Get-Process -Id 15344 -ErrorAction SilentlyContinue)
$record.supervisorServerCleanupObserved = $null -eq (Get-Process -Id 20968 -ErrorAction SilentlyContinue)
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
$record | ConvertTo-Json -Depth 5

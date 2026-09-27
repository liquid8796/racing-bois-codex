param(
    [string]$TargetHost = '158.180.59.36',
    [string]$SshUser = 'ubuntu',
    [string]$IdentityFile = 'C:\Users\Liquid\.ssh\jarvis_oci_ed25519'
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$archive = Join-Path $projectRoot '_local/racing-bois-linux-arm64.tar.gz'
$sshOptions = @('-i',$IdentityFile,'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10')
$remoteDirectory = (& ssh @sshOptions "$SshUser@$TargetHost" 'mktemp -d /tmp/racing-bois-p02.XXXXXXXX').Trim()
if ($LASTEXITCODE -ne 0 -or $remoteDirectory -notmatch '^/tmp/racing-bois-p02\.[A-Za-z0-9]+$') { throw 'Invalid task-owned staging directory.' }
try {
    & scp @sshOptions $archive "${SshUser}@${TargetHost}:$remoteDirectory/server.tar.gz"
    if ($LASTEXITCODE -ne 0) { throw 'Upload failed.' }
    $runCommand = "tar -xzf '$remoteDirectory/server.tar.gz' -C '$remoteDirectory' && chmod u+x '$remoteDirectory/RacingBois.Server.Host' && '$remoteDirectory/RacingBois.Server.Host' --SelfTest"
    $result = & ssh @sshOptions "$SshUser@$TargetHost" $runCommand
    if ($LASTEXITCODE -ne 0) { throw 'ARM64 smoke failed.' }
    $json = $result -join "`n"
    $json | ConvertFrom-Json | Out-Null
    $outputPath = Join-Path $projectRoot 'docs/p02/oci/arm64-smoke.json'
    $json | Set-Content -LiteralPath $outputPath -Encoding utf8
    $json
} finally {
    # Only the verified exact mktemp directory created by this invocation is removed.
    & ssh @sshOptions "$SshUser@$TargetHost" "rm -rf -- '$remoteDirectory'"
    if ($LASTEXITCODE -ne 0) { Write-Warning "Cleanup failed for task directory $remoteDirectory" }
}

param([string]$TargetHost='158.180.59.36',[string]$IdentityFile='C:\Users\Liquid\.ssh\jarvis_oci_ed25519')
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$sshArgs=@('-i',$IdentityFile,'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes')
$privateRoot=Join-Path $projectRoot '_local/p09-recovery'
New-Item -ItemType Directory -Force -Path $privateRoot | Out-Null
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $privateRoot /inheritance:r /grant:r "${identity}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
if($LASTEXITCODE -ne 0){throw 'Cannot secure recovery directory'}
$receipt=((& ssh @sshArgs "ubuntu@$TargetHost" 'sudo -n cat /srv/racing-bois/backups/latest.json') -join "`n") | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $receipt.archive -notmatch '^racing-bois-[0-9TZ]+\.tar\.gpg$'){throw 'Invalid backup receipt'}
$keyText=(& ssh @sshArgs "ubuntu@$TargetHost" 'sudo -n cat /var/lib/racing-bois-staging/backup-key') -join "`n"
if($LASTEXITCODE -ne 0 -or $keyText.Length -lt 32){throw 'Cannot retrieve recovery key'}
Add-Type -AssemblyName System.Security
$keyBytes=[Text.Encoding]::UTF8.GetBytes($keyText)
$entropy=[Text.Encoding]::UTF8.GetBytes('RacingBois:P09:BackupRecovery:v1')
try {
    $protected=[Security.Cryptography.ProtectedData]::Protect($keyBytes,$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
    [IO.File]::WriteAllBytes((Join-Path $privateRoot 'backup-key.dpapi'),$protected)
    $roundtrip=[Security.Cryptography.ProtectedData]::Unprotect($protected,$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
    if([Convert]::ToBase64String($roundtrip) -cne [Convert]::ToBase64String($keyBytes)){throw 'DPAPI recovery roundtrip failed'}
} finally { [Array]::Clear($keyBytes,0,$keyBytes.Length); $keyText=$null; if($roundtrip){[Array]::Clear($roundtrip,0,$roundtrip.Length)} }
$remote=(& ssh @sshArgs "ubuntu@$TargetHost" 'mktemp -d /tmp/racing-bois-recovery.XXXXXXXX').Trim()
if($LASTEXITCODE -ne 0 -or $remote -notmatch '^/tmp/racing-bois-recovery\.[A-Za-z0-9]+$'){throw 'Invalid transfer directory'}
& ssh @sshArgs "ubuntu@$TargetHost" "sudo -n cp '/srv/racing-bois/backups/$($receipt.archive)' '$remote/backup.tar.gpg' && sudo -n chown ubuntu:ubuntu '$remote/backup.tar.gpg'"
if($LASTEXITCODE -ne 0){throw 'Cannot stage encrypted backup'}
$archivePath=Join-Path $privateRoot $receipt.archive
& scp @sshArgs "ubuntu@${TargetHost}:$remote/backup.tar.gpg" $archivePath
if($LASTEXITCODE -ne 0){throw 'Cannot download encrypted backup'}
$hash=(Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if($hash -cne $receipt.archiveSha256){throw 'Downloaded backup hash mismatch'}
& ssh @sshArgs "ubuntu@$TargetHost" "rm -- '$remote/backup.tar.gpg' && rmdir -- '$remote'"
if($LASTEXITCODE -ne 0){throw 'Cannot clean task-owned encrypted transfer file'}
$report=[ordered]@{status='passed';generatedUtc=[DateTimeOffset]::UtcNow.ToString('O');archive=$receipt.archive;archiveSha256=$hash;archiveBytes=(Get-Item -LiteralPath $archivePath).Length;recoveryKey='Windows DPAPI CurrentUser';dpapiRoundtrip=$true;scope='Off-VM encrypted backup on the user PC. Decryption requires the same Windows account and its DPAPI master key. No plaintext secret is saved.'}
$json=$report | ConvertTo-Json
$json | Set-Content -LiteralPath (Join-Path $projectRoot 'docs/p09/off-vm-backup.json') -Encoding utf8
$json

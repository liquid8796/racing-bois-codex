$ErrorActionPreference='Stop'
& python (Join-Path $PSScriptRoot 'decrypt-local.py')
if($LASTEXITCODE -ne 0){throw 'Off-VM authenticated decryption and restore validation failed'}
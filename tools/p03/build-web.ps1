param(
    [string]$ProjectPath = '',
    [string]$UnityExe = 'C:\Program Files\Unity\Hub\Editor\6000.5.7f1\Editor\Unity.exe'
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '../foundation/build-web.ps1') -Profile gameplay -ProjectPath $ProjectPath -UnityExe $UnityExe

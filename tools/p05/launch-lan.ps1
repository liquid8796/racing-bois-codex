param(
    [string]$PackageRoot = $PSScriptRoot,
    [ValidateRange(1024,65535)][int]$Port = 7777,
    [string]$DataRoot = 'data',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lan/lan-functions.ps1')
$addresses = @(Get-RacingBoisLanAddresses)
$plan = Get-RacingBoisLanPlan -PackageRoot $PackageRoot -Port $Port -DataRoot $DataRoot -Addresses $addresses
if ($PlanOnly) { $plan | ConvertTo-Json -Depth 6; return }
if (-not (Test-Path -LiteralPath $plan.executable -PathType Leaf)) { throw 'Bundled server executable is missing. Extract the complete LAN package first.' }
if (-not (Test-Path -LiteralPath (Join-Path $plan.webRoot 'index.html') -PathType Leaf)) { throw 'Bundled Web game is missing. This package is not ready for offline use.' }
$used = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($used) { throw "Port $Port is already in use. Close the earlier host or choose another -Port. No process was stopped." }
New-Item -ItemType Directory -Force -Path $plan.dataRoot | Out-Null
$joinPage = Write-RacingBoisJoinPage -Plan $plan -HelperRoot (Join-Path $PSScriptRoot 'lan')
Write-Host 'Racing Bois - offline LAN host'
Write-Host "This PC: $($plan.localUrl)"
foreach ($item in $plan.addresses) { Write-Host "LAN ($($item.adapter)): $($item.url)" }
if ($plan.addresses.Count -eq 0) { Write-Warning 'No physical private-LAN address found. This PC can use localhost; connect a LAN cable or the same Wi-Fi router before other PCs join.' }
Write-Host "Offline QR/address page: $joinPage"
Write-Host "Realm data: $($plan.dataRoot)"
Write-Host 'Keep this window open. Ctrl+C stops this host. No firewall or network settings are changed.'
& $plan.executable @($plan.arguments)
if ($LASTEXITCODE -ne 0) { throw "LAN host exited with code $LASTEXITCODE." }

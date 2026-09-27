param([string]$PackageRoot = $PSScriptRoot, [ValidateRange(1024,65535)][int]$Port = 7777)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lan/lan-functions.ps1')
$plan = Get-RacingBoisLanPlan -PackageRoot $PackageRoot -Port $Port -Addresses @(Get-RacingBoisLanAddresses)
$page = Write-RacingBoisJoinPage -Plan $plan -HelperRoot (Join-Path $PSScriptRoot 'lan')
Write-Host "This PC: $($plan.localUrl)"
foreach ($item in $plan.addresses) { Write-Host "$($item.adapter): $($item.url)" }
Write-Host "Open this file for QR codes (works without Internet): $page"
if ($plan.addresses.Count -eq 0) { Write-Warning 'No eligible physical LAN interface. Virtual/VPN, public and link-local addresses are not shared.' }

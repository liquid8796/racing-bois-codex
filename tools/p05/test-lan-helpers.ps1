param([string]$Receipt = 'docs/p05/lan/helper-tests.json')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lan/lan-functions.ps1')
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$results = @()
function Assert-Case([string]$Name, [bool]$Passed) {
    if (-not $Passed) { throw "FAILED: $Name" }
    $script:results += [pscustomobject]@{name=$Name;passed=$true}
}
foreach ($address in @('10.0.0.1','172.16.0.1','172.31.255.254','192.168.1.13')) { Assert-Case "private $address" (Test-RacingBoisPrivateIPv4 $address) }
foreach ($address in @('127.0.0.1','169.254.1.1','172.15.1.1','172.32.1.1','192.169.1.1','8.8.8.8','0.0.0.0','::1','10.1','010.0.0.1','localhost')) { Assert-Case "excluded $address" (-not (Test-RacingBoisPrivateIPv4 $address)) }
$adapters = @(
    [pscustomobject]@{Name='Wi-Fi';InterfaceDescription='Intel Wireless';ifIndex=1;Status='Up';HardwareInterface=$true},
    [pscustomobject]@{Name='Ethernet';InterfaceDescription='Physical Ethernet';ifIndex=2;Status='Up';HardwareInterface=$true},
    [pscustomobject]@{Name='VPN';InterfaceDescription='VPN';ifIndex=3;Status='Up';HardwareInterface=$true},
    [pscustomobject]@{Name='vEthernet (WSL)';InterfaceDescription='Hyper-V';ifIndex=4;Status='Up';HardwareInterface=$false},
    [pscustomobject]@{Name='Cable';InterfaceDescription='Physical Ethernet';ifIndex=5;Status='Disconnected';HardwareInterface=$true})
$addresses = @(1..5 | ForEach-Object { [pscustomobject]@{IPAddress="192.168.$_.2";InterfaceIndex=$_;SkipAsSource=$false;PrefixLength=24} })
$addresses += [pscustomobject]@{IPAddress='169.254.4.5';InterfaceIndex=1;SkipAsSource=$false;PrefixLength=16}
$addresses += [pscustomobject]@{IPAddress='10.0.0.3';InterfaceIndex=1;SkipAsSource=$true;PrefixLength=24}
$addresses += [pscustomobject]@{IPAddress='10.0.0.4';InterfaceIndex=1;SkipAsSource=$false;PrefixLength=32}
$routes = @([pscustomobject]@{InterfaceIndex=2;NextHop='192.168.2.1'})
$selected = @(Select-RacingBoisLanAddresses -Adapters $adapters -Addresses $addresses -DefaultRoutes $routes)
Assert-Case 'physical active candidates only' ($selected.Count -eq 2)
Assert-Case 'gateway candidate first' ($selected[0].address -eq '192.168.2.2')
$fixture = Join-Path $repo '_local/p05-lan-helper-fixture'
New-Item -ItemType Directory -Force -Path $fixture | Out-Null
$plan = Get-RacingBoisLanPlan -PackageRoot $fixture -Addresses $selected
Assert-Case 'explicit package data root' ($plan.dataRoot -eq (Join-Path $fixture 'data'))
Assert-Case 'host arguments retain DataRoot' ($plan.arguments[-2] -eq '--DataRoot' -and $plan.arguments[-1] -eq $plan.dataRoot)
foreach ($badData in @('web','web/profiles')) {
    $rejected=$false; try { $null=Get-RacingBoisLanPlan -PackageRoot $fixture -DataRoot $badData } catch { $rejected=$true }
    Assert-Case "public DataRoot blocked $badData" $rejected
}
$privatePlan = Get-RacingBoisLanPlan -PackageRoot $fixture -DataRoot 'web-data'
Assert-Case 'web prefix sibling remains private' ($privatePlan.dataRoot -eq (Join-Path $fixture 'web-data'))
$malicious = @([pscustomobject]@{address='192.168.1.10';adapter='Wi-Fi </script><script>alert(1)</script>'})
$injectionPlan = Get-RacingBoisLanPlan -PackageRoot $fixture -Addresses $malicious
$generated = Write-RacingBoisJoinPage -Plan $injectionPlan -HelperRoot (Join-Path $PSScriptRoot 'lan')
$content = Get-Content -LiteralPath $generated -Raw -Encoding UTF8
Assert-Case 'adapter labels cannot close JSON script' (-not $content.Contains('Wi-Fi </script>') -and $content.Contains('\u003c/script\u003e'))
# Retain a usable non-adversarial artifact for browser and QR review.
$realPlan = Get-RacingBoisLanPlan -PackageRoot $fixture -Addresses @(Get-RacingBoisLanAddresses)
$null = Write-RacingBoisJoinPage -Plan $realPlan -HelperRoot (Join-Path $PSScriptRoot 'lan')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'lan') -Destination $fixture -Recurse -Force
$provenance = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'lan/vendor-provenance.json') -Raw | ConvertFrom-Json
$hash = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'lan/qrcodegen.js') -Algorithm SHA256).Hash.ToLowerInvariant()
Assert-Case 'vendored QR exact upstream bytes' ($hash -eq $provenance.sha256)
$receiptObject = [pscustomobject]@{passed=$true;tests=$results.Count;cases=$results;realEligibleAddresses=$realPlan.addresses;fixture=$fixture;networkSettingsChanged=$false}
$receiptObject | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $repo $Receipt) -Encoding UTF8
$receiptObject | Select-Object passed,tests,fixture,networkSettingsChanged

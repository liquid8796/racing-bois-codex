function Test-RacingBoisPrivateIPv4 {
    param([string]$Address)
    $parsed = $null
    if (-not [Net.IPAddress]::TryParse($Address, [ref]$parsed)) { return $false }
    if ($parsed.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) { return $false }
    if ($parsed.ToString() -cne $Address) { return $false }
    $bytes = $parsed.GetAddressBytes()
    return ($bytes[0] -eq 10 -or ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or ($bytes[0] -eq 192 -and $bytes[1] -eq 168))
}

function Select-RacingBoisLanAddresses {
    param([object[]]$Adapters, [object[]]$Addresses, [object[]]$DefaultRoutes = @())
    $excluded = '(?i)vpn|wireguard|tailscale|zerotier|tap[- ]|tunnel|hyper-v|vethernet|docker|wsl|loopback|virtual|vmware|kernel.debug|wan.miniport'
    $results = @()
    foreach ($adapter in $Adapters) {
        if (-not $adapter.HardwareInterface -or [string]$adapter.Status -ne 'Up') { continue }
        if (([string]$adapter.Name + ' ' + [string]$adapter.InterfaceDescription) -match $excluded) { continue }
        foreach ($address in $Addresses) {
            if ($address.InterfaceIndex -ne $adapter.ifIndex -or $address.SkipAsSource) { continue }
            if (-not (Test-RacingBoisPrivateIPv4 $address.IPAddress)) { continue }
            if ($address.PrefixLength -lt 1 -or $address.PrefixLength -gt 30) { continue }
            $hasGateway = @($DefaultRoutes | Where-Object { $_.InterfaceIndex -eq $adapter.ifIndex -and $_.NextHop -ne '0.0.0.0' }).Count -gt 0
            $results += [pscustomobject]@{
                address = [string]$address.IPAddress
                adapter = [string]$adapter.Name
                interfaceIndex = [int]$adapter.ifIndex
                hasGateway = $hasGateway
            }
        }
    }
    return @($results | Sort-Object -Property @{ Expression = 'hasGateway'; Descending = $true }, interfaceIndex, address -Unique)
}

function Get-RacingBoisLanAddresses {
    $adapters = @(Get-NetAdapter -IncludeHidden -ErrorAction Stop)
    $addresses = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop)
    $routes = @(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue)
    return @(Select-RacingBoisLanAddresses -Adapters $adapters -Addresses $addresses -DefaultRoutes $routes)
}

function Get-RacingBoisLanPlan {
    param([string]$PackageRoot, [int]$Port = 7777, [string]$DataRoot = 'data', [object[]]$Addresses = @())
    if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Port must be between 1024 and 65535.' }
    $packagePath = if ([IO.Path]::IsPathRooted($PackageRoot)) { $PackageRoot } else { Join-Path (Get-Location).ProviderPath $PackageRoot }
    $resolvedPackage = [IO.Path]::GetFullPath($packagePath)
    $resolvedWeb = [IO.Path]::GetFullPath((Join-Path $resolvedPackage 'web'))
    $resolvedData = if ([IO.Path]::IsPathRooted($DataRoot)) { [IO.Path]::GetFullPath($DataRoot) } else { [IO.Path]::GetFullPath((Join-Path $resolvedPackage $DataRoot)) }
    $separator = [IO.Path]::DirectorySeparatorChar
    if ($resolvedData.TrimEnd($separator) -eq $resolvedWeb.TrimEnd($separator) -or $resolvedData.StartsWith($resolvedWeb.TrimEnd($separator) + $separator, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'DataRoot must stay outside the publicly served web directory.'
    }
    if ($resolvedData.TrimEnd($separator) -eq $resolvedPackage.TrimEnd($separator)) { throw 'Use a dedicated DataRoot directory, not the package root.' }
    $links = @($Addresses | ForEach-Object {
        if (-not (Test-RacingBoisPrivateIPv4 $_.address)) { throw 'Only private LAN addresses can be shared.' }
        [pscustomobject]@{ address = $_.address; adapter = $_.adapter; url = "http://$($_.address):$Port/" }
    })
    return [pscustomobject]@{
        packageRoot = $resolvedPackage
        executable = Join-Path $resolvedPackage 'RacingBois.Server.Host.exe'
        webRoot = $resolvedWeb
        dataRoot = $resolvedData
        port = $Port
        localUrl = "http://localhost:$Port/"
        addresses = $links
        arguments = @('--AllowLan', 'true', '--Port', [string]$Port, '--WebRoot', $resolvedWeb, '--DataRoot', $resolvedData)
    }
}

function Write-RacingBoisJoinPage {
    param([object]$Plan, [string]$HelperRoot)
    $template = Get-Content -LiteralPath (Join-Path $HelperRoot 'join.template.html') -Raw -Encoding UTF8
    $payload = [pscustomobject]@{ localUrl = $Plan.localUrl; addresses = @($Plan.addresses) } | ConvertTo-Json -Depth 5 -Compress
    # Adapter labels come from the OS. Escape script boundaries before embedding JSON.
    $payload = $payload.Replace('<', '\u003c').Replace('>', '\u003e').Replace('&', '\u0026')
    $page = $template.Replace('__RACING_BOIS_ADDRESS_DATA__', $payload)
    $path = Join-Path $Plan.packageRoot 'LAN_JOIN.html'
    [IO.File]::WriteAllText($path, $page, (New-Object Text.UTF8Encoding($false)))
    return $path
}

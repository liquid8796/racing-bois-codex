param(
    [ValidateSet('win-x64','linux-arm64','linux-x64')][string]$Runtime = 'win-x64',
    [string]$Output = '',
    [string]$WebRoot = ''
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $Output) { $Output = Join-Path $repoRoot "Build\LanHost\$Runtime" }
if (-not $WebRoot) { $WebRoot = & (Join-Path $PSScriptRoot 'resolve-web-root.ps1') -ProjectRoot $repoRoot }
$project = Join-Path $repoRoot 'src\Server\RacingBois.Server.Host\RacingBois.Server.Host.csproj'
& dotnet publish $project -c Release -r $Runtime --self-contained true -p:PublishSingleFile=false -o $Output
if ($LASTEXITCODE -ne 0) { throw 'Self-contained publish failed.' }
if (Test-Path -LiteralPath $WebRoot) {
    $destination = Join-Path $Output 'web'
    # Replacing this package's web payload must not retain debug or obsolete Unity build files.
    $resolvedOutput = [IO.Path]::GetFullPath($Output).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $resolvedDestination = [IO.Path]::GetFullPath($destination)
    if (-not $resolvedDestination.StartsWith($resolvedOutput + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Web destination escaped publish output.' }
    if (Test-Path -LiteralPath $resolvedDestination) { Remove-Item -LiteralPath $resolvedDestination -Recurse -Force }
    New-Item -ItemType Directory -Force $destination | Out-Null
    function Copy-DeployableWebDirectory([string]$SourceDirectory, [string]$TargetDirectory) {
        foreach ($entry in Get-ChildItem -LiteralPath $SourceDirectory -Force) {
            if ($entry.Name -match '(?i)_DoNotShip') { continue }
            $target = Join-Path $TargetDirectory $entry.Name
            if ($entry.PSIsContainer) {
                New-Item -ItemType Directory -Force $target | Out-Null
                Copy-DeployableWebDirectory $entry.FullName $target
            } else { Copy-Item -LiteralPath $entry.FullName -Destination $target -Force }
        }
    }
    Copy-DeployableWebDirectory ([IO.Path]::GetFullPath($WebRoot)) $resolvedDestination
} else {
    Write-Warning 'Unity Web build absent: runtime published, offline browser payload is NOT complete.'
}
@'
Racing Bois P03/P04 gameplay preview
Windows: RacingBois.Server.Host.exe --AllowLan true --WebRoot web
Linux: ./RacingBois.Server.Host --AllowLan true --WebRoot web
Then open http://HOST-LAN-IP:7777/ in a browser on the same network.
Run from this directory. No runtime download is needed after publishing.
For native compatibility smoke: append --SelfTest (no ports opened).
The Web game includes local offline practice, one original test route, driving,
left/right attacks and kicks, damage, crash/run/remount recovery, opponents,
police, traffic, pedestrians, race results and temporary in-memory local rewards.
The gameplay server owns movement, combat and outcomes for up to eight human
connections. Local practice and the server run the same shared simulation.
Controls: W/S or arrows for throttle/brake, A/D or arrows to steer, Q/E to attack,
Shift+Q/E to kick, R to restart local practice, Escape to return to the menu.
The UI also supports hold-throttle, reduced motion and sound settings.
This is a P03/P04 preview. Lobby lifecycle, reconnect/reconciliation and independent
Internet/LAN-machine acceptance remain P05 gates. Accounts, inventory and durable
online economy/persistence belong to P07; public OCI deployment and regional
connection acceptance belong to P09. Local rewards are not an online account wallet.
Binding LAN does not modify firewall rules. Public production authentication is absent.
Final art/animation polish and broad browser/hardware acceptance remain P06/P10 work.
'@ | Set-Content -LiteralPath (Join-Path $Output 'README.txt') -Encoding UTF8
if ($Runtime -eq 'win-x64') {
    @'
@echo off
cd /d "%~dp0"
RacingBois.Server.Host.exe --WebRoot "%~dp0web" %*
exit /b %ERRORLEVEL%
'@ | Set-Content -LiteralPath (Join-Path $Output 'launch-local.bat') -Encoding ASCII
    @'
@echo off
cd /d "%~dp0"
RacingBois.Server.Host.exe --AllowLan true --WebRoot "%~dp0web" %*
exit /b %ERRORLEVEL%
'@ | Set-Content -LiteralPath (Join-Path $Output 'launch-lan.bat') -Encoding ASCII
} else {
    $localScript = @'
#!/bin/sh
set -eu
cd -- "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec ./RacingBois.Server.Host --WebRoot "$(pwd)/web" "$@"
'@
    $lanScript = @'
#!/bin/sh
set -eu
cd -- "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec ./RacingBois.Server.Host --AllowLan true --WebRoot "$(pwd)/web" "$@"
'@
    $noBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText((Join-Path $Output 'launch-local.sh'), ($localScript -replace "`r`n", "`n") + "`n", $noBom)
    [IO.File]::WriteAllText((Join-Path $Output 'launch-lan.sh'), ($lanScript -replace "`r`n", "`n") + "`n", $noBom)
}
Write-Host "Published to $Output"

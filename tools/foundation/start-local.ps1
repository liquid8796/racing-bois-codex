param(
    [int]$Port = 7777,
    [int]$TlsPort = 7778,
    [switch]$EnableTls,
    [switch]$AllowLan,
    [string]$WebRoot = ''
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $WebRoot) { $WebRoot = & (Join-Path $PSScriptRoot 'resolve-web-root.ps1') -ProjectRoot $repoRoot }
$project = Join-Path $repoRoot 'src\Server\RacingBois.Server.Host\RacingBois.Server.Host.csproj'
$launch = @('run', '--project', $project, '-c', 'Release', '--', '--Port', "$Port", '--TlsPort', "$TlsPort", '--WebRoot', $WebRoot, '--EnableTls', $EnableTls.IsPresent.ToString(), '--AllowLan', $AllowLan.IsPresent.ToString())
& dotnet @launch
exit $LASTEXITCODE

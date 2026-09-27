param([string]$BlenderExe = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe', [ValidateRange(1024,65535)][int]$Port = 9876)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (-not (Test-Path -LiteralPath $BlenderExe)) { throw 'Blender executable missing; pass -BlenderExe.' }
$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($listener) { throw "Port $Port already has a listener. Reuse the running Blender MCP instance." }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '_local/blender-mcp/addon.py'))) { & (Join-Path $PSScriptRoot 'prepare.ps1') }
$taskPrefix = if($Port -eq 9876){'_local/blender'}else{"_local/blender-$Port"}
$taskProcess = Start-Process -FilePath $BlenderExe -ArgumentList '--factory-startup','--python',(Join-Path $PSScriptRoot 'bootstrap.py'),'--','--port',$Port -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot ($taskPrefix+'-stdout.log')) -RedirectStandardError (Join-Path $projectRoot ($taskPrefix+'-stderr.log'))
$taskProcess.Id | Set-Content -LiteralPath (Join-Path $projectRoot ($taskPrefix+'.pid'))
Write-Host "Task-owned Blender PID $($taskProcess.Id), loopback port $Port."

param(
    [string]$ProjectPath = '',
    [string]$UnityExe = 'C:\Program Files\Unity\Hub\Editor\6000.5.7f1\Editor\Unity.exe',
    [ValidateSet('foundation','gameplay')][string]$Profile = 'foundation'
)
$ErrorActionPreference = 'Stop'
if (-not $ProjectPath) { $ProjectPath = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path }
$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (-not (Test-Path -LiteralPath $UnityExe)) { throw 'Unity Editor not found; pass -UnityExe.' }
if (-not (Test-Path -LiteralPath (Join-Path $ProjectPath 'Packages/manifest.json'))) { throw 'Not a Unity project.' }
$logDirectory = Join-Path $ProjectPath 'Logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$buildMethod = if ($Profile -eq 'gameplay') { 'RacingBois.Authoring.Editor.RaceBuilder.BuildWeb' } else { 'RacingBois.Authoring.Editor.FoundationBuilder.BuildWeb' }
$receiptFolder = if ($Profile -eq 'gameplay') { 'docs/p03p04/unity' } else { 'docs/p02/unity' }
$receiptFile = if ($Profile -eq 'gameplay') { 'build.json' } else { 'cli-build.json' }
$webFolder = if ($Profile -eq 'gameplay') { 'Build/Web-Race' } else { 'Build/Web' }
$arguments = @('-batchmode','-nographics','-quit','-projectPath',('"'+$ProjectPath+'"'),'-buildTarget','WebGL','-executeMethod',$buildMethod,'-logFile',('"'+(Join-Path $logDirectory 'web-build.log')+'"'))
function Invoke-UnityProcess {
    $process = Start-Process -FilePath $UnityExe -ArgumentList $arguments -WindowStyle Hidden -PassThru
    # Wait for this Editor only. Start-Process -Wait can remain blocked by shared licensing/compiler descendants.
    $null = $process.Handle
    $process.WaitForExit()
    return $process
}
$buildProcess = Invoke-UnityProcess
$retriedBeeLimit = $false
if ($buildProcess.ExitCode -ne 0) {
    $logPath = Join-Path $logDirectory 'web-build.log'
    $knownBeeLimit = Select-String -LiteralPath $logPath -SimpleMatch 'Internal build system error. Backend has requested a buildprogram run 6 times.' -Quiet
    if ($knownBeeLimit) {
        # Unity 6000.5 can exhaust its cold Bee graph regeneration budget after producing the native outputs.
        # One retry resumes the completed graph; unrelated build failures are never hidden or retried here.
        Copy-Item -LiteralPath $logPath -Destination (Join-Path $logDirectory 'web-build-first-attempt.log') -Force
        $retriedBeeLimit = $true
        $buildProcess = Invoke-UnityProcess
    }
}
if ($buildProcess.ExitCode -ne 0) { throw "Unity build failed ($($buildProcess.ExitCode)). See $logDirectory/web-build.log. Close an Editor using this same project first, or use a clean checkout." }
New-Item -ItemType Directory -Path (Join-Path $ProjectPath $receiptFolder) -Force | Out-Null
@{unityExitCode=$buildProcess.ExitCode;retriedBeeGraphLimit=$retriedBeeLimit;project=$ProjectPath;profile=$Profile} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ProjectPath ($receiptFolder+'/build-wrapper.json')) -Encoding utf8
New-Item -ItemType Directory -Path (Join-Path $ProjectPath 'Build') -Force | Out-Null
$webFolder | Set-Content -LiteralPath (Join-Path $ProjectPath 'Build/current-web.txt') -Encoding ascii
Get-Content -LiteralPath (Join-Path $ProjectPath ($receiptFolder+'/'+$receiptFile))

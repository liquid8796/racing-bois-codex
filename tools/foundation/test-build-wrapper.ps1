$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$testRoot = Join-Path $root ('_local/build-wrapper-test-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$fake = Join-Path $testRoot 'fake-unity.bat'
@'
@echo off
setlocal
:parse
if "%~1"=="" goto run
if "%~1"=="-projectPath" set "project=%~2"
if "%~1"=="-logFile" set "log=%~2"
shift
goto parse
:run
set "calls=0"
if exist "%project%\calls.txt" set /p calls=<"%project%\calls.txt"
set /a calls+=1
>"%project%\calls.txt" echo %calls%
if "%RB_FAKE_UNITY_CASE%"=="other" goto other
if "%RB_FAKE_UNITY_CASE%"=="persistent" goto bee
if %calls%==1 goto bee
mkdir "%project%\docs\p02\unity" 2>nul
>"%project%\docs\p02\unity\cli-build.json" echo {"result":"Succeeded","fixture":true}
>"%log%" echo Build succeeded
exit /b 0
:bee
>"%log%" echo Internal build system error. Backend has requested a buildprogram run 6 times.
exit /b 1
:other
>"%log%" echo Compiler error CS0001: intentional unrelated failure
exit /b 1
'@ | Set-Content -LiteralPath $fake -Encoding ascii
$previous = $env:RB_FAKE_UNITY_CASE
$results = @()
try {
    foreach ($scenario in @('recover','other','persistent')) {
        $project = Join-Path $testRoot $scenario
        New-Item -ItemType Directory -Path (Join-Path $project 'Packages') -Force | Out-Null
        '{}' | Set-Content -LiteralPath (Join-Path $project 'Packages/manifest.json')
        $env:RB_FAKE_UNITY_CASE = $scenario
        $succeeded = $false
        try { & (Join-Path $PSScriptRoot 'build-web.ps1') -ProjectPath $project -UnityExe $fake | Out-Null; $succeeded = $true } catch { }
        $calls = [int](Get-Content -LiteralPath (Join-Path $project 'calls.txt'))
        $expectedCalls = if($scenario -eq 'other'){1}else{2}
        $passed = ($calls -eq $expectedCalls) -and ($succeeded -eq ($scenario -eq 'recover'))
        $results += [pscustomobject]@{case=$scenario;calls=$calls;succeeded=$succeeded;passed=$passed}
    }
} finally { $env:RB_FAKE_UNITY_CASE = $previous }
$results | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'docs/p02/unity/build-wrapper-tests.json') -Encoding utf8
$results | Format-Table
if ($results.passed -contains $false) { throw 'Build wrapper regression test failed' }

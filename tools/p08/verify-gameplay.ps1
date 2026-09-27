param([switch]$ContentOnly, [switch]$RequireProductionContent)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
Push-Location -LiteralPath $workspace
try {
    $destination = Join-Path $workspace 'docs\p08\gameplay'
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    $cases = @(
        @{ Name = 'RacingBois.P08Content.Tests'; File = 'content-tests.json'; ReportFlag = $true },
        @{ Name = 'RacingBois.Multiplayer.Integration.Tests'; File = 'RacingBois.Multiplayer.Integration.Tests.json' },
        @{ Name = 'RacingBois.EconomyRules.Tests'; File = 'economy-tests.json' }
    )
    if (-not $ContentOnly) {
        $cases += @(
            @{ Name = 'RacingBois.Gameplay.Tests'; File = 'gameplay-validation.json' },
            @{ Name = 'RacingBois.RaceIntegration.Tests'; File = 'RacingBois.RaceIntegration.Tests.json' },
            @{ Name = 'RacingBois.P05Client.Tests'; File = 'RacingBois.P05Client.Tests.json' },
            @{ Name = 'RacingBois.P07Client.Tests'; File = 'RacingBois.P07Client.Tests.json' },
            @{ Name = 'RacingBois.Persistence.Tests'; File = 'persistence-tests.json'; ReportFlag = $true },
            @{ Name = 'RacingBois.Foundation.Tests'; File = 'foundation-tests.json' }
        )
    }
    foreach ($case in $cases) {
        $report = Join-Path $destination $case.File
        $arguments = @('run', '--project', ('src/Tests/' + $case.Name), '-c', 'Release', '--')
        if ($case.ReportFlag) { $arguments += '--report' }
        $arguments += $report
        & dotnet @arguments
        if ($LASTEXITCODE -ne 0) { throw ($case.Name + ' failed; inspect ' + $report) }
    }
    $content = Get-Content -LiteralPath (Join-Path $destination 'content-tests.json') -Raw | ConvertFrom-Json
    if ($RequireProductionContent -and $content.pendingProductionGate) {
        throw 'The authored core passed, but the production route availability gate is still closed.'
    }
    Write-Output ('P08 native validation passed. Content identity: ' + $content.contentHash)
} finally { Pop-Location }

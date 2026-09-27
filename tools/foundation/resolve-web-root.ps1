param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$marker = Join-Path $ProjectRoot 'Build/current-web.txt'
$relative = if(Test-Path -LiteralPath $marker){(Get-Content -LiteralPath $marker -Raw).Trim()}else{'Build/Web'}
$resolved = [IO.Path]::GetFullPath((Join-Path $ProjectRoot $relative))
$buildRoot = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'Build'))
if (-not $resolved.StartsWith($buildRoot + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Current web marker must stay inside this project Build directory.' }
$resolved

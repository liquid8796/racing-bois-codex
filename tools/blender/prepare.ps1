$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$source = Join-Path $projectRoot '_local/blender-mcp'
$python = Join-Path $projectRoot '_local/blender-env/Scripts/python.exe'
$commit = '6f992ffbca3cb715d111fc640b737b808632273c'
if (-not (Test-Path -LiteralPath (Join-Path $source '.git'))) {
    & git clone https://github.com/ahujasid/mcp-for-blender.git $source
    if ($LASTEXITCODE -ne 0) { throw 'Blender MCP clone failed' }
    & git -C $source checkout --detach $commit
    if ($LASTEXITCODE -ne 0) { throw 'Pinned Blender MCP checkout failed' }
}
$actual = (& git -C $source rev-parse HEAD).Trim()
if ($actual -ne $commit) { throw "Existing Blender MCP checkout differs from pinned commit: $actual" }
if (-not (Test-Path -LiteralPath $python)) { & uv venv (Split-Path (Split-Path $python)) }
& python (Join-Path $PSScriptRoot 'patch_disabled_telemetry.py')
if ($LASTEXITCODE -ne 0) { throw 'Compatibility patch failed' }
& uv pip install --python $python --reinstall --link-mode copy -r (Join-Path $PSScriptRoot 'requirements.lock') $source
if ($LASTEXITCODE -ne 0) { throw 'Blender MCP dependency installation failed' }
& uv pip freeze --python $python | Set-Content -LiteralPath (Join-Path $projectRoot '_local/blender-packages.txt') -Encoding utf8

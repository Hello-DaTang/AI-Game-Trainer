# Windows installation of the pinned upstream CE bridge.
# Run from repo root: powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$checkout = Join-Path $root "vendor\cheatengine-mcp-bridge"
$revision = "6bd7ce90479250a9b4b75e7944df9c105ecb2572"
if (-not (Test-Path (Join-Path $checkout ".git"))) {
    New-Item -ItemType Directory -Force -Path (Split-Path $checkout -Parent) | Out-Null
    git clone https://github.com/miscusi-peek/cheatengine-mcp-bridge.git $checkout
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
}
Push-Location $checkout
try {
    git fetch origin $revision
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
    git checkout --detach $revision
    if ($LASTEXITCODE -ne 0) { throw "git checkout failed" }
} finally {
    Pop-Location
}
Write-Host "Upstream CE bridge pinned at $revision"
Write-Host "CE Lua script: $checkout\MCP_Server\ce_mcp_bridge.lua"
Write-Host "Next: py -m pip install -r requirements-windows.txt"
Write-Host "Then open Cheat Engine and execute the Lua script above."
Write-Host "Finally run: py -m trainer"

param(
    [int]$Port = 5000
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Starting app on port $Port..."
& "$root\scripts\start_app_background.ps1" -Port $Port

Write-Host "Starting public HTTPS tunnel..."
& "$root\scripts\start_public_tunnel.ps1" -Port $Port

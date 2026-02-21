$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pidFile = Join-Path $root 'localhostrun.pid'
$linkFile = Join-Path $root 'public_link.txt'

if (-not (Test-Path $pidFile)) {
    Write-Host 'No localhost.run tunnel PID file found.'
    exit 0
}

$pidRaw = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
if (-not ($pidRaw -match '^\d+$')) {
    Remove-Item $pidFile -ErrorAction SilentlyContinue
    Write-Host 'Invalid localhost.run PID file removed.'
    exit 0
}

$pidNum = [int]$pidRaw
$proc = Get-Process -Id $pidNum -ErrorAction SilentlyContinue
if ($proc) {
    Stop-Process -Id $pidNum -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped localhost.run tunnel (PID $pidNum)."
} else {
    Write-Host "localhost.run process not running (PID $pidNum)."
}

Remove-Item $pidFile -ErrorAction SilentlyContinue
Remove-Item $linkFile -ErrorAction SilentlyContinue

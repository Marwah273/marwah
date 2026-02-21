param(
    [int]$Port = 5000
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pidFile = Join-Path $root 'ngrok.pid'
$outLogFile = Join-Path $root 'ngrok.out.log'
$errLogFile = Join-Path $root 'ngrok.err.log'

function Stop-StaleNgrok {
    if (Test-Path $pidFile) {
        $existingPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
        if ($existingPid -match '^\d+$') {
            $proc = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
            if ($proc) {
                try { Stop-Process -Id $proc.Id -Force -ErrorAction Stop } catch {}
            }
        }
        Remove-Item $pidFile -ErrorAction SilentlyContinue
    }
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $listener) {
    throw "No app is listening on port $Port. Start the app first (example: .\\scripts\\start_app_background.ps1 -Port $Port)."
}

$ngrokCmd = (Get-Command ngrok -ErrorAction SilentlyContinue).Source
if (-not $ngrokCmd) {
    $wingetRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    if (Test-Path $wingetRoot) {
        $ngrokExe = Get-ChildItem $wingetRoot -Directory -Filter 'Ngrok.Ngrok*' -ErrorAction SilentlyContinue |
            ForEach-Object { Get-ChildItem $_.FullName -File -Filter 'ngrok.exe' -ErrorAction SilentlyContinue } |
            Select-Object -First 1
        if ($ngrokExe) {
            $ngrokCmd = $ngrokExe.FullName
        }
    }
}
if (-not $ngrokCmd) {
    throw "ngrok is not installed or not in PATH. Install from https://ngrok.com/download and run 'ngrok config add-authtoken <token>' once."
}

Stop-StaleNgrok

$proc = Start-Process -FilePath $ngrokCmd -ArgumentList @('http', $Port.ToString()) -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLogFile -RedirectStandardError $errLogFile
$proc.Id | Set-Content -Path $pidFile -Encoding ascii

$publicUrl = $null
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $api = Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 2
        if ($api -and $api.tunnels) {
            $httpsTunnel = $api.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1
            if ($httpsTunnel -and $httpsTunnel.public_url) {
                $publicUrl = $httpsTunnel.public_url
                break
            }
        }
    } catch {
    }
}

if (-not $publicUrl) {
    $running = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
    if ($running) {
        Write-Host "ngrok started (PID $($proc.Id)) but public URL was not found yet."
        Write-Host "Open ngrok web UI: http://127.0.0.1:4040"
    } else {
        Write-Host 'ngrok exited before tunnel was created.'
        if (Test-Path $outLogFile) {
            Write-Host 'Last ngrok stdout lines:'
            Get-Content $outLogFile -Tail 20
        }
        if (Test-Path $errLogFile) {
            Write-Host 'Last ngrok stderr lines:'
            Get-Content $errLogFile -Tail 20
        }
        Write-Host "If needed, run: ngrok config add-authtoken <your_token>"
    }
    exit 1
}

Write-Host "Public link ready: $publicUrl"
Write-Host "Share this HTTPS link with parents."
Write-Host "To stop tunnel: .\\scripts\\stop_public_tunnel.ps1"

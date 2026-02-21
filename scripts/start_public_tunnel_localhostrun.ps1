param(
    [int]$Port = 5000
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pidFile = Join-Path $root 'localhostrun.pid'
$outLog = Join-Path $root 'localhostrun.out.log'
$errLog = Join-Path $root 'localhostrun.err.log'
$linkFile = Join-Path $root 'public_link.txt'

function Get-CandidateUrlFromLogs {
    param(
        [string[]]$Paths
    )

    $all = @()
    foreach ($p in $Paths) {
        if (-not (Test-Path $p)) {
            continue
        }
        $tail = Get-Content $p -Tail 300 -ErrorAction SilentlyContinue
        if (-not $tail) {
            continue
        }
        $joined = ($tail -join "`n")
        $matches = [regex]::Matches($joined, 'https://[^\s''""<>]+')
        foreach ($m in $matches) {
            $all += $m.Value.Trim()
        }
    }

    if (-not $all -or $all.Count -eq 0) {
        return $null
    }

    $clean = $all |
        Where-Object { $_ -notmatch 'localhost\.run/docs' -and $_ -notmatch 'twitter\.com' -and $_ -notmatch 'admin\.localhost\.run' } |
        ForEach-Object { $_.TrimEnd('/', '.', ',', ';') }

    if (-not $clean -or $clean.Count -eq 0) {
        return $null
    }

    return ($clean | Select-Object -Last 1)
}

function Test-PublicUrlReachable {
    param(
        [string]$Url
    )

    if (-not $Url) {
        return $false
    }

    try {
        $uri = [Uri]$Url
    } catch {
        return $false
    }

    try {
        Resolve-DnsName -Name $uri.Host -Type A -ErrorAction Stop | Out-Null
    } catch {
        return $false
    }

    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8 -MaximumRedirection 5
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
    } catch {
        return $false
    }
}

if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    throw "No app is listening on port $Port. Start the app first (example: .\\scripts\\start_app_background.ps1 -Port $Port)."
}

$sshExe = (Get-Command ssh -ErrorAction SilentlyContinue).Source
if (-not $sshExe) {
    throw 'ssh client not found. Install OpenSSH Client in Windows optional features.'
}

if (Test-Path $pidFile) {
    $old = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($old -match '^\d+$') {
        try { Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue } catch {}
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}

$null = Remove-Item $outLog,$errLog -ErrorAction SilentlyContinue

$args = @(
    '-T',
    '-o','StrictHostKeyChecking=no',
    '-o','ServerAliveInterval=30',
    '-o','ServerAliveCountMax=3',
    '-o','ExitOnForwardFailure=yes',
    '-R',"80:localhost:$Port",
    'nokey@localhost.run'
)
$proc = Start-Process -FilePath $sshExe -ArgumentList $args -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
$proc.Id | Set-Content -Path $pidFile -Encoding ascii

$url = $null
for ($i = 0; $i -lt 180; $i++) {
    Start-Sleep -Milliseconds 500
    $logPaths = @($outLog, $errLog) | Where-Object { Test-Path $_ }
    if ($logPaths.Count -gt 0) {
        $candidate = Get-CandidateUrlFromLogs -Paths $logPaths
        if ($candidate -and (Test-PublicUrlReachable -Url $candidate)) {
            $url = $candidate
            break
        }
    }
    if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
        break
    }
}

if ($url) {
    $url | Set-Content -Path $linkFile -Encoding utf8
    Write-Host "Public link ready: $url"
    Write-Host "Saved to: $linkFile"
    Write-Host "Share this URL with parents."
    Write-Host "To stop tunnel: .\\scripts\\stop_public_tunnel_localhostrun.ps1"
    exit 0
}

Write-Host 'Tunnel started but no working public URL was found yet.'
Write-Host 'This usually means localhost.run gave an unreachable domain on your network.'
Write-Host 'Recommended: use ngrok after setting authtoken, or deploy on Render for a permanent link.'
if (Test-Path $linkFile) {
    Remove-Item $linkFile -ErrorAction SilentlyContinue
}
if (Test-Path $outLog) {
    Write-Host 'Recent stdout:'
    Get-Content $outLog -Tail 20
}
if (Test-Path $errLog) {
    Write-Host 'Recent stderr:'
    Get-Content $errLog -Tail 20
}
exit 1

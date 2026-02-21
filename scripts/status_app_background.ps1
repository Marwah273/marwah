param(
    [int]$Port = 5000
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root 'app.pid'
$wrapperPidFile = Join-Path $root 'app.wrapper.pid'

function Read-PidFromFile {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $txt = (Get-Content $Path -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($txt -match '^\d+$') {
        return [int]$txt
    }

    return $null
}

function Get-ChildPythonPid {
    param(
        [int]$ParentPid
    )

    try {
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentPid" -ErrorAction Stop
        $py = $children |
            Where-Object {
                ($_.Name -in @('python.exe', 'pythonw.exe')) -and
                ($_.CommandLine -match 'app\.py')
            } |
            Select-Object -First 1
        if ($py) {
            return [int]$py.ProcessId
        }
    } catch {
    }

    return $null
}

function Get-AppPidFromPort {
    param(
        [int]$Port = 5000
    )

    try {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($listener -and $listener.OwningProcess) {
            $pid = [int]$listener.OwningProcess
            $wmiProc = Get-CimInstance Win32_Process -Filter "ProcessId = $pid" -ErrorAction SilentlyContinue
            if ($wmiProc -and $wmiProc.CommandLine -and ($wmiProc.CommandLine -match 'app\.py')) {
                return $pid
            }
        }
    } catch {
    }

    return $null
}

if (-not (Test-Path $pidFile) -and -not (Test-Path $wrapperPidFile)) {
    $fallbackPid = Get-AppPidFromPort -Port $Port
    if ($fallbackPid) {
        $fallbackPid | Set-Content -Path $pidFile -Encoding ascii
        Write-Host "Recovered running app PID from port ${Port}: $fallbackPid"
    } else {
        Write-Host 'App is not running (no PID file).'
        exit 0
    }
}

$appPid = Read-PidFromFile -Path $pidFile
$wrapperPid = Read-PidFromFile -Path $wrapperPidFile

if (-not $appPid -and (Test-Path $pidFile)) {
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}

if (-not $wrapperPid -and (Test-Path $wrapperPidFile)) {
    Remove-Item $wrapperPidFile -ErrorAction SilentlyContinue
}

$resolvedPid = $null
$proc = $null

if ($appPid) {
    $appProc = Get-Process -Id $appPid -ErrorAction SilentlyContinue
    if ($appProc) {
        if ($appProc.ProcessName -in @('python', 'pythonw')) {
            $resolvedPid = $appPid
            $proc = $appProc
        } elseif ($appProc.ProcessName -eq 'cmd') {
            $childPid = Get-ChildPythonPid -ParentPid $appPid
            if ($childPid) {
                $resolvedPid = $childPid
                $proc = Get-Process -Id $resolvedPid -ErrorAction SilentlyContinue
                $resolvedPid | Set-Content -Path $pidFile -Encoding ascii
            }
        }
    }
}

if (-not $resolvedPid -and $wrapperPid) {
    $wrapperProc = Get-Process -Id $wrapperPid -ErrorAction SilentlyContinue
    if ($wrapperProc) {
        $childPid = Get-ChildPythonPid -ParentPid $wrapperPid
        if ($childPid) {
            $resolvedPid = $childPid
            $proc = Get-Process -Id $resolvedPid -ErrorAction SilentlyContinue
            $resolvedPid | Set-Content -Path $pidFile -Encoding ascii
        }
    }
}

if (-not $resolvedPid -or -not $proc) {
    $fallbackPid = Get-AppPidFromPort -Port $Port
    if ($fallbackPid) {
        $resolvedPid = $fallbackPid
        $resolvedPid | Set-Content -Path $pidFile -Encoding ascii
        $proc = Get-Process -Id $resolvedPid -ErrorAction SilentlyContinue
    }

    if (-not $resolvedPid -or -not $proc) {
        Remove-Item $pidFile -ErrorAction SilentlyContinue
        Remove-Item $wrapperPidFile -ErrorAction SilentlyContinue
        Write-Host 'App is not running (stale PID files removed).'
        exit 0
    }
}

Write-Host "App is running (PID $resolvedPid, process $($proc.ProcessName))."

$ports = @()

try {
    $listeners = Get-NetTCPConnection -State Listen -OwningProcess $resolvedPid -ErrorAction Stop |
        Sort-Object -Property LocalPort -Unique
    if ($listeners) {
        $ports += $listeners | ForEach-Object { [int]$_.LocalPort }
    }
} catch {
}

if (-not $ports) {
    try {
        $netstatLines = netstat -ano -p tcp | Select-String -Pattern "LISTENING\s+$resolvedPid$"
        foreach ($line in $netstatLines) {
            $parts = ($line.Line -replace '^\s+', '') -split '\s+'
            if ($parts.Length -ge 2) {
                $localAddress = $parts[1]
                $portText = ($localAddress -split ':')[-1]
                if ($portText -match '^\d+$') {
                    $ports += [int]$portText
                }
            }
        }
    } catch {
    }
}

$ports = $ports | Sort-Object -Unique
foreach ($port in $ports) {
    Write-Host "Listening on: http://localhost:$port"
}

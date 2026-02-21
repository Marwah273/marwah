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
    } else {
        Write-Host 'No PID file found. App may already be stopped.'
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

$stopped = @()

$pythonPid = $null
if ($appPid) {
    $appProc = Get-Process -Id $appPid -ErrorAction SilentlyContinue
    if ($appProc) {
        if ($appProc.ProcessName -in @('python', 'pythonw')) {
            $pythonPid = $appPid
        } elseif ($appProc.ProcessName -eq 'cmd') {
            $pythonPid = Get-ChildPythonPid -ParentPid $appPid
            if (-not $wrapperPid) {
                $wrapperPid = $appPid
            }
        }
    }
}

if (-not $pythonPid -and $wrapperPid) {
    $pythonPid = Get-ChildPythonPid -ParentPid $wrapperPid
}

if (-not $pythonPid) {
    $pythonPid = Get-AppPidFromPort -Port $Port
}

if ($pythonPid) {
    $pyProc = Get-Process -Id $pythonPid -ErrorAction SilentlyContinue
    if ($pyProc) {
        Stop-Process -Id $pythonPid -Force
        $stopped += "python PID $pythonPid"
    }
}

if ($wrapperPid) {
    $wrapperProc = Get-Process -Id $wrapperPid -ErrorAction SilentlyContinue
    if ($wrapperProc) {
        Stop-Process -Id $wrapperPid -Force
        $stopped += "wrapper PID $wrapperPid"
    }
}

Start-Sleep -Milliseconds 400
Remove-Item $pidFile -ErrorAction SilentlyContinue
Remove-Item $wrapperPidFile -ErrorAction SilentlyContinue

if ($stopped.Count -gt 0) {
    Write-Host ("Stopped app process(es): " + ($stopped -join ', ') + '.')
} else {
    Write-Host 'Process not found. PID files removed.'
}


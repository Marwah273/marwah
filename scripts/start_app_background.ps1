param(
    [int]$Port = 5000
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pidFile = Join-Path $root 'app.pid'
$wrapperPidFile = Join-Path $root 'app.wrapper.pid'
$logFile = Join-Path $root 'app.log'
$errLogFile = Join-Path $root 'app.err.log'

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

function Get-PortOwnerPid {
    param(
        [int]$ListenPort
    )

    try {
        $conn = Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($conn -and $conn.OwningProcess) {
            return [int]$conn.OwningProcess
        }
    } catch {
    }

    return $null
}

function Is-AppProcess {
    param(
        [int]$ProcessId
    )

    try {
        $wmiProc = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        if ($wmiProc -and $wmiProc.CommandLine -and ($wmiProc.CommandLine -match 'app\.py')) {
            return $true
        }
    } catch {
    }

    return $false
}

if (Test-Path $pidFile) {
    $existingPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($existingPid -match '^\d+$') {
        $proc = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
        if ($proc) {
            $isPython = $proc.ProcessName -in @('python', 'pythonw')
            $childPythonPid = $null
            if (-not $isPython -and ($proc.ProcessName -eq 'cmd')) {
                $childPythonPid = Get-ChildPythonPid -ParentPid ([int]$existingPid)
            }

            if ($isPython -or $childPythonPid) {
                $resolvedPid = if ($childPythonPid) { $childPythonPid } else { [int]$existingPid }
                if ($childPythonPid) {
                    $resolvedPid | Set-Content -Path $pidFile -Encoding ascii
                }
                Write-Host "App already running (PID $resolvedPid)."
                Write-Host "Open: http://localhost:$Port"
                exit 0
            }
        }
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}

if (Test-Path $wrapperPidFile) {
    Remove-Item $wrapperPidFile -ErrorAction SilentlyContinue
}

$venvPythonW = Join-Path $root '.venv\Scripts\pythonw.exe'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPythonW) {
    $pythonExe = $venvPythonW
} elseif (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonExe) {
        $pythonExe = (Get-Command py -ErrorAction SilentlyContinue).Source
    }
    if (-not $pythonExe) {
        throw 'Python not found. Install Python or create .venv first.'
    }
}

$appFile = Join-Path $root 'app.py'

$quotedPython = '"' + $pythonExe + '"'
$bootstrapCode = @"
import os, runpy, sys
os.chdir(r'$root')
os.environ['PORT'] = '$Port'
sys.stdout = open(r'$logFile', 'a', encoding='utf-8')
sys.stderr = open(r'$errLogFile', 'a', encoding='utf-8')
runpy.run_path(r'$appFile', run_name='__main__')
"@

$bootstrapSingleLine = (($bootstrapCode -split "`r?`n") | Where-Object { $_.Trim() -ne '' }) -join '; '
$escapedBootstrap = $bootstrapSingleLine -replace '"', '\\"'
$cmdLine = '{0} -c "{1}"' -f $quotedPython, $escapedBootstrap

$create = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $cmdLine
    CurrentDirectory = $root
}

if (($null -eq $create) -or ($create.ReturnValue -ne 0) -or (-not $create.ProcessId)) {
    throw "Failed to start app process (Win32_Process.Create return value: $($create.ReturnValue))."
}

$startedPid = [int]$create.ProcessId
$startedPid | Set-Content -Path $pidFile -Encoding ascii

Start-Sleep -Seconds 1

$resolvedPid = $null
for ($i = 0; $i -lt 20; $i++) {
    if (Get-Process -Id $startedPid -ErrorAction SilentlyContinue) {
        $resolvedPid = $startedPid
    }
    $portOwnerPid = Get-PortOwnerPid -ListenPort $Port
    if ($portOwnerPid -and (Is-AppProcess -ProcessId $portOwnerPid)) {
        $resolvedPid = $portOwnerPid
        break
    }
    Start-Sleep -Milliseconds 250
}

if ($resolvedPid) {
    $resolvedPid | Set-Content -Path $pidFile -Encoding ascii
}

if ($resolvedPid -and (Get-Process -Id $resolvedPid -ErrorAction SilentlyContinue)) {
    $lanIps = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } |
        Select-Object -ExpandProperty IPAddress -Unique)

    Write-Host "App started in background (PID $resolvedPid)."
    Write-Host "Open: http://localhost:$Port"
    if ($lanIps.Count -gt 0) {
        foreach ($ip in $lanIps) {
            Write-Host "LAN:  http://${ip}:$Port"
        }
    } else {
        Write-Host "LAN:  http://<your-ip>:$Port"
    }
    Write-Host "To stop: .\scripts\stop_app_background.ps1"
} else {
    Write-Host 'App process exited quickly. Check app.log for details.'
    exit 1
}

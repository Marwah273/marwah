Param(
    [ValidateSet('Private','Public','Any')]
    [string]$Profile = 'Private'
)

$ErrorActionPreference = 'Stop'

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    Write-Error "Administrator privileges are required. Re-run PowerShell as Administrator, then run this script again."
    exit 1
}

$ruleName = 'Grades4-Allow-5000'
if (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue) {
    Write-Output "Firewall rule '$ruleName' already exists."
    exit 0
}

try {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000 -Profile $Profile -EdgeTraversalPolicy Block | Out-Null
    Write-Output "Created firewall rule '$ruleName' for TCP 5000 on profile: $Profile"
} catch {
    Write-Error "Failed to create firewall rule '$ruleName': $($_.Exception.Message)"
    exit 1
}

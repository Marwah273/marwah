Param(
    [string]$InterfaceAlias
)
if (-not (Get-Command 'Get-NetConnectionProfile' -ErrorAction SilentlyContinue)) {
    Write-Output "This script requires administrative PowerShell with the NetTCPIP module available."
    exit 1
}
if ($InterfaceAlias) {
    $profile = Get-NetConnectionProfile | Where-Object { $_.InterfaceAlias -like "*$InterfaceAlias*" }
} else {
    $profile = Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq 'Public' } | Select-Object -First 1
}
if (-not $profile) {
    Write-Output "No matching network profile found. Available profiles:"
    Get-NetConnectionProfile | Format-Table -AutoSize
    exit 1
}
Set-NetConnectionProfile -InterfaceIndex $profile.InterfaceIndex -NetworkCategory Private
Write-Output "Set network '$($profile.Name)' (InterfaceIndex $($profile.InterfaceIndex)) to Private."

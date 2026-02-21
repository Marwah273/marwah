$ruleName = 'Grades4-Allow-5000'
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    Write-Output "No firewall rule named '$ruleName' found."
    exit 0
}
Remove-NetFirewallRule -DisplayName $ruleName
Write-Output "Removed firewall rule '$ruleName'."

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$r = Invoke-WebRequest 'http://127.0.0.1:5000/admin/token-login?t=setup-token-9X2w' -WebSession $session -UseBasicParsing -ErrorAction SilentlyContinue
if ($null -ne $r) { Write-Output "LoginStatus:$($r.StatusCode)" } else { Write-Output 'LoginRequest:null' }
$m = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/admin/migrate' -Method Post -WebSession $session -UseBasicParsing -ErrorAction SilentlyContinue
if ($null -ne $m) {
  Write-Output "MigrateStatus:$($m.StatusCode)"
  if ($m.Content) { Write-Output 'MigrateBodyStart'; Write-Output $m.Content; Write-Output 'MigrateBodyEnd' }
} else { Write-Output 'MigrateRequest:null' }

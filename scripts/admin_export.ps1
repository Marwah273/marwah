$ownpid=(Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess
if ($ownpid) { Stop-Process -Id $ownpid -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1
Start-Process -FilePath '.\.venv\Scripts\python.exe' -ArgumentList 'app.py' -WindowStyle Hidden
Start-Sleep -Seconds 3
$session=New-Object Microsoft.PowerShell.Commands.WebRequestSession
$r=Invoke-WebRequest -Uri 'http://127.0.0.1:5000/admin/login' -Method Post -Body @{password='Marwah123'} -WebSession $session -UseBasicParsing -TimeoutSec 30
if ($r.StatusCode -ne 200 -and $r.StatusCode -ne 302) { Write-Output "LoginFailed:$($r.StatusCode)"; exit 1 }
Invoke-WebRequest -Uri 'http://127.0.0.1:5000/admin/export' -WebSession $session -OutFile students.csv -UseBasicParsing -TimeoutSec 30
Write-Output 'CSVExported'

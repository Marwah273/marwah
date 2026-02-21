$out = "scripts\diagnose_out.txt"
"--- netstat (port 5000) ---" | Out-File $out -Encoding utf8
netstat -ano | Select-String ':5000' -SimpleMatch | Out-File $out -Append -Encoding utf8
"--- Get-NetTCPConnection ---" | Out-File $out -Append -Encoding utf8
Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Format-List | Out-File $out -Append -Encoding utf8
"--- Process using port 5000 ---" | Out-File $out -Append -Encoding utf8
$p=Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($p) {
    try { Get-Process -Id $p.OwningProcess | Select-Object Id,ProcessName | Out-File $out -Append -Encoding utf8 } catch { "Process not found for PID: $($p.OwningProcess)" | Out-File $out -Append -Encoding utf8 }
} else { "No process listening on 5000" | Out-File $out -Append -Encoding utf8 }
"--- LAN IPs ---" | Out-File $out -Append -Encoding utf8
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } | Select-Object IPAddress,InterfaceAlias | Out-File $out -Append -Encoding utf8
"--- Network profile ---" | Out-File $out -Append -Encoding utf8
Get-NetConnectionProfile | Select-Object Name,NetworkCategory | Out-File $out -Append -Encoding utf8
"--- Firewall rules allowing port 5000 ---" | Out-File $out -Append -Encoding utf8
try { Get-NetFirewallRule -Direction Inbound -Action Allow -Enabled True | Where-Object { (Get-NetFirewallPortFilter -AssociatedNetFirewallRule $_).LocalPort -contains '5000' } | Select-Object DisplayName,Enabled,Direction | Out-File $out -Append -Encoding utf8 } catch { "No matching firewall rule found or insufficient permissions" | Out-File $out -Append -Encoding utf8 }
"--- HTTP test to 127.0.0.1:5000 ---" | Out-File $out -Append -Encoding utf8
try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:5000' -UseBasicParsing -TimeoutSec 5; ("Status: " + $r.StatusCode) | Out-File $out -Append -Encoding utf8 } catch { ("Local request failed: " + $_.Exception.Message) | Out-File $out -Append -Encoding utf8 }
"--- HTTP test to LAN IPs ---" | Out-File $out -Append -Encoding utf8
$ips=(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' }).IPAddress
foreach ($ip in $ips) {
    $url = "http://${ip}:5000"
    ("Testing " + $url) | Out-File $out -Append -Encoding utf8
    try { $r2=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5; ("Status: " + $r2.StatusCode) | Out-File $out -Append -Encoding utf8 } catch { ("Failed: " + $_.Exception.Message) | Out-File $out -Append -Encoding utf8 }
}
"--- Done ---" | Out-File $out -Append -Encoding utf8

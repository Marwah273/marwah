$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/admin/login' -Method Post -Body @{password='Marwah123'} -WebSession $session -UseBasicParsing -ErrorAction SilentlyContinue -TimeoutSec 30
if ($null -eq $r) { Write-Output 'LoginRequest:null'; exit 0 }
Write-Output ("LoginStatus:" + $r.StatusCode)
if ($r.Headers['Set-Cookie']) { Write-Output ("Set-Cookie:" + ($r.Headers['Set-Cookie'] -join '; ')) } else { Write-Output 'Set-Cookie:(none)' }
$list = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/admin/list' -WebSession $session -UseBasicParsing -ErrorAction SilentlyContinue -TimeoutSec 30
if ($null -eq $list) { Write-Output 'ListRequest:null'; exit 0 }
Write-Output ("ListStatus:" + $list.StatusCode)
if ($list.StatusCode -eq 200) {
  $html = $list.Content
  $len = $html.Length
  $snippet = $html.Substring(0,[math]::Min(800,$len))
  Write-Output 'HTML_SNIPPET_START'
  Write-Output $snippet
  Write-Output 'HTML_SNIPPET_END'
}

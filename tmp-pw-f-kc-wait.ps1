$ErrorActionPreference = 'SilentlyContinue'
Set-Location 'C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline'
Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'tmp-pw-f-loop|tmp-pw-track-f|tmp-pw-f-once' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
$log = 'tmp-pw\f-kc-wait.log'
function Log($m) { Add-Content $log "$(Get-Date -Format o) $m" }
Log 'waiter restart'
for ($i = 0; $i -lt 60; $i++) {
  $h = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -match 'opencode[\\/]chrome-profile' -and $_.CommandLine -match 'disable-field-trial-config' })
  Log "tick=$i chrome=$($h.Count)"
  if ($h.Count -eq 0) {
    Start-Sleep -Seconds 5
    $h2 = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -match 'opencode[\\/]chrome-profile' -and $_.CommandLine -match 'disable-field-trial-config' })
    if ($h2.Count -eq 0) {
      Remove-Item "$env:USERPROFILE\.config\opencode\chrome-profile\lockfile","$env:USERPROFILE\.config\opencode\chrome-profile\SingletonLock","$env:USERPROFILE\.config\opencode\chrome-profile\SingletonCookie","$env:USERPROFILE\.config\opencode\chrome-profile\SingletonSocket" -Force
      Log 'starting keepchrome'
      Start-Process node -ArgumentList 'tmp-pw-f-keepchrome.js' -WorkingDirectory (Get-Location) -RedirectStandardOutput 'tmp-pw\f-keepchrome-stdout.txt' -RedirectStandardError 'tmp-pw\f-keepchrome-stderr.txt' -WindowStyle Hidden
      break
    }
  }
  Start-Sleep -Seconds 20
}
Log 'waiter exit'

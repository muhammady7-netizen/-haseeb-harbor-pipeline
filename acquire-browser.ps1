# Acquire shared OpenCode Chrome for ONE session only.
# Usage: .\acquire-browser.ps1 -Session C -TimeoutSec 600
param(
  [Parameter(Mandatory=$true)][ValidateSet('A','B','C','D','E','F')][string]$Session,
  [int]$TimeoutSec = 600
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Lock = Join-Path $Root 'sessions\BROWSER.lock'
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'sessions') | Out-Null

$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
  $chromeBusy = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
    Where-Object { $_.CommandLine -match 'opencode[/\\]chrome-profile' }).Count -gt 0

  $holder = $null
  if (Test-Path $Lock) {
    try { $holder = (Get-Content $Lock -Raw).Trim() } catch { $holder = 'UNKNOWN' }
  }

  if (-not $chromeBusy -and (-not $holder -or $holder -match "session=$Session")) {
    @"
session=$Session
pid=$PID
at=$((Get-Date).ToUniversalTime().ToString('o'))
"@ | Set-Content -Path $Lock -Encoding utf8
    Write-Host "ACQUIRED browser lock for session $Session"
    exit 0
  }

  Write-Host ("{0} waiting chromeBusy={1} holder={2} want={3}" -f (Get-Date -Format HH:mm:ss), $chromeBusy, $holder, $Session)
  Start-Sleep -Seconds 15
}

Write-Host "TIMEOUT waiting for browser lock"
exit 1

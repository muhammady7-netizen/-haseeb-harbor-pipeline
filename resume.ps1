# Haseeb Harbor pipeline - bootstrap then run resume CLI
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$env:PYTHONUTF8 = "1"
$env:NO_COLOR = "1"
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

$machine = Join-Path $Root "machine.json"
if (-not (Test-Path $machine)) {
  Copy-Item (Join-Path $Root "machine.example.json") $machine
  Write-Host "Created machine.json from example - edit paths if needed."
}

$setup = $null
try {
  $cfg = Get-Content $machine -Raw | ConvertFrom-Json
  $setup = $cfg.setup_session_ps1
} catch {}

if ($setup -and (Test-Path $setup)) {
  . $setup
  if ($env:OPENAI_API_KEY -and -not $env:WANDB_GLM_API_KEY) {
    $env:WANDB_GLM_API_KEY = $env:OPENAI_API_KEY
  }
} else {
  Write-Warning "setup-session.ps1 not found; PreQC --full may lack API key."
}

Write-Host "Pipeline root: $Root"
if ($args.Count -eq 0) {
  python -m pipeline.resume board
} else {
  python -m pipeline.resume @args
}

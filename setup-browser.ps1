# Browser automation setup for opencode + Harbor V2 portal
# Run once per PC after cloning the repo
# Usage: .\setup-browser.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Browser Automation Setup ===" -ForegroundColor Cyan

# 1. Install @playwright/mcp globally
Write-Host "`n[1/4] Installing @playwright/mcp globally..." -ForegroundColor Yellow
cmd /c "npm install -g @playwright/mcp@latest 2>&1"
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: npm install -g @playwright/mcp"; exit 1 }

# 2. Find the global cli.js
$globalRoot = (cmd /c "npm root -g" 2>$null).Trim()
$cliJs = Join-Path $globalRoot "@playwright\mcp\cli.js"
if (-not (Test-Path $cliJs)) {
    Write-Host "FAILED: cannot find @playwright/mcp/cli.js at $cliJs"
    exit 1
}
$cliJsFwd = $cliJs -replace '\\','/'
Write-Host "  MCP CLI: $cliJsFwd" -ForegroundColor Green

# 3. Install Chromium (fallback if Chrome not installed)
Write-Host "`n[2/4] Installing Chromium for Playwright..." -ForegroundColor Yellow
cmd /c "npx -y playwright install chromium 2>&1" | Out-Null
Write-Host "  Done" -ForegroundColor Green

# 4. Create persistent profile dir
$profileDir = Join-Path $HOME ".config\opencode\chrome-profile"
$profileDirFwd = $profileDir -replace '\\','/'
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}
New-Item -ItemType File -Path (Join-Path $profileDir "First Run") -Force | Out-Null
Write-Host "`n[3/4] Profile dir: $profileDirFwd" -ForegroundColor Green

# 5. Write opencode.jsonc (merge with existing if present)
$configDir = Join-Path $HOME ".config\opencode"
$configFile = Join-Path $configDir "opencode.jsonc"
if (-not (Test-Path $configDir)) { New-Item -ItemType Directory -Path $configDir -Force | Out-Null }

$mcpConfig = @{
    "`$schema" = "https://opencode.ai/config.json"
    mcp = @{
        playwright = @{
            type = "local"
            command = @("node", $cliJsFwd, "--browser", "chrome", "--user-data-dir", $profileDirFwd)
            enabled = $true
            timeout = 30000
        }
    }
}

# Preserve existing provider config if present
if (Test-Path $configFile) {
    try {
        $existing = Get-Content $configFile -Raw | ConvertFrom-Json
        if ($existing.provider) {
            $mcpConfig["provider"] = $existing.provider
        }
        if ($existing.disabled_providers) {
            $mcpConfig["disabled_providers"] = $existing.disabled_providers
        }
    } catch {
        Write-Host "  Warning: could not parse existing opencode.jsonc; overwriting" -ForegroundColor Red
    }
}

$json = $mcpConfig | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($configFile, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "`n[4/4] Config written: $configFile" -ForegroundColor Green
Write-Host "  $json" -ForegroundColor Gray

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor White
Write-Host "  1. Restart opencode (config loads at startup)" -ForegroundColor White
Write-Host "  2. First time: sign into Shannon (muhammad.y7@turing.com) in the Playwright Chrome window" -ForegroundColor White
Write-Host "  3. Session saves forever in $profileDirFwd" -ForegroundColor White
Write-Host "  4. All future sessions reuse the login - no sign-in needed" -ForegroundColor White
Write-Host "`nRules:" -ForegroundColor White
Write-Host "  - Only ONE session drives the browser at a time (Chrome singleton lock)" -ForegroundColor White
Write-Host "  - Never run taskkill /F /IM chrome.exe (kills user's real Chrome profiles)" -ForegroundColor White
Write-Host "  - User's regular Chrome is never touched (Playwright uses its own instance)" -ForegroundColor White

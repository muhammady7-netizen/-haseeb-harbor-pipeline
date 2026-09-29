# COMPLETE SETUP GUIDE — Avoid Context Aware Access (CAA) Blocks

## The Problem
Context Aware Access (CAA) blocks `gcloud auth print-access-token` even when WARP shows healthy. The connector image (digest b1374cd8a392...) needs GCP auth to pull.

## Step 1: Cloudflare WARP Setup (MUST be running BEFORE gcloud auth)

### Install WARP
```powershell
# Download and install Cloudflare WARP
winget install --id Cloudflare.Warp
# Or download from: https://1.1.1.1/
```

### Start WARP (every session)
```powershell
# Check WARP status
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" status

# If not connected, connect:
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" connect

# Verify it's healthy
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" status
# Should show: "Status update: Success" and "Connected"
```

### IMPORTANT: Wait 30 seconds after WARP connects before running gcloud
```powershell
Start-Sleep -Seconds 30
```

## Step 2: gcloud Authentication (with WARP active)

### Refresh gcloud credentials
```powershell
# First try refreshing existing creds
gcloud auth print-access-token

# If that fails, re-authenticate:
gcloud auth login --no-launch-browser
# Follow the URL, sign in with muhammad.y7@turing.com
# Wait for it to complete

# Test the token works:
gcloud auth print-access-token
# Should print a long token string, NOT "Access was blocked"
```

### If CAA still blocks after WARP + re-auth:
```powershell
# 1. Disconnect and reconnect WARP
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" disconnect
Start-Sleep -Seconds 5
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" connect
Start-Sleep -Seconds 30

# 2. Clear gcloud cache
gcloud auth revoke --all
gcloud auth login --no-launch-browser

# 3. Set application default credentials
gcloud auth application-default login --no-launch-browser

# 4. Test
gcloud auth print-access-token
```

## Step 3: Docker Authentication for GCP

### Configure Docker to use gcloud credentials
```powershell
# This makes `docker pull` use your gcloud token
gcloud auth configure-docker us-central1-docker.pkg.dev
# Or if using the older registry:
gcloud auth configure-docker gcr.io
```

### Pull the connector image
```powershell
# Set the project
gcloud config set project delivery-g-obi

# Pull the specific image (replace with actual image path from task.toml)
docker pull us-central1-docker.pkg.dev/delivery-g-obi/connector-base@sha256:b1374cd8a392...
# Or pull without digest:
docker pull us-central1-docker.pkg.dev/delivery-g-obi/connector-base:latest
```

## Step 4: Harbor CLI Setup

### Source the environment (every session)
```powershell
source ~/.config/harbor/env
```

### Verify environment variables are set
```powershell
echo $OPENAI_API_KEY  # Should show your key
echo $OPENAI_BASE_URL # Should show http://34.41.10.8:4000/v1
echo $JUDGE_MODEL     # Should show openai/glm-5.2
```

## Step 5: Quick Sanity Check

### Test everything works together
```powershell
# 1. WARP healthy?
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" status

# 2. gcloud token works?
gcloud auth print-access-token | Select-Object -First 1

# 3. Docker can pull?
docker images | Select-String "connector"

# 4. Harbor env loaded?
echo $OPENAI_API_KEY
```

## Troubleshooting: CAA Still Blocking

### Method 1: Use WARP with specific team enrollment
```powershell
# If WARP is installed but not enrolled in team:
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" teams-enroll <TEAM-URL>
# Get team URL from your Turing admin or check BROWSER-SETUP.md
```

### Method 2: Restart WARP service
```powershell
# Restart the WARP service
Stop-Service CloudflareWARP
Start-Sleep -Seconds 3
Start-Service CloudflareWARP
Start-Sleep -Seconds 30
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" connect
Start-Sleep -Seconds 10
gcloud auth print-access-token
```

### Method 3: Use service account key (bypasses CAA entirely)
```powershell
# If you have a service account JSON key:
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\service-account-key.json"
gcloud auth activate-service-account --key-file "C:\path\to\service-account-key.json"
gcloud auth print-access-token
```

### Method 4: Check if WARP DNS is working
```powershell
# Test DNS resolution through WARP
nslookup google.com
# Should resolve to WARP's DNS (usually 172.16.0.1 or similar)

# If DNS is wrong, flush DNS:
ipconfig /flushdns
```

## Daily Checklist (run before every session)

```powershell
# 1. Start WARP
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" connect
Start-Sleep -Seconds 30

# 2. Verify WARP
"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" status

# 3. Verify gcloud
gcloud auth print-access-token

# 4. Source harbor env
source ~/.config/harbor/env

# 5. Check Docker
docker ps
```

## Key Files and Locations

| File | Purpose |
|------|---------|
| `~/.config/harbor/env` | Harbor CLI credentials (OPENAI_API_KEY, BASE_URL, JUDGE_MODEL) |
| `~/.config/gcloud/application_default_credentials.json` | gcloud default creds |
| `C:\Users\HASEEB~1\Documents\Default Project\local-qc\BROWSER-SETUP.md` | Portal browser auth setup |
| `C:\Users\HASEEB~1\Documents\Default Project\local-qc\SESSION-HANDOFF-PROMPT.md` | Full task handoff for new chats |
| `C:\Users\HASEEB~1\Documents\Default Project\local-qc\tools\verifier_defect_lint.py` | Local QC linter (D1-D22 checks) |

## Portal Access

| URL | Purpose |
|-----|---------|
| `https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer` | Main QC portal |
| `https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer/resources` | Resources/docs |
| Google account: `muhammad.y7@turing.com` | IAP-protected, needs browser auth |

## GitHub Remote

```powershell
cd "C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc"
git remote -v
# harbor  https://github.com/muhammady7-netizen/-haseeb-harbor-pipeline.git
```

## Current Task Status (as of last push)

| Task | Version | Oracle | GLM | Status |
|------|---------|--------|---------|--------|
| bus-b50 | v48 | PASSED | Timed out (8254s > 7200s) | 1000 traps too complex. Need ~200 traps |
| gen-g806 | v5 | PASSED | 1/4 (in band!) | Submitted to pipeline |
| health-h34 | v25 | PASSED | 1/4 (in band!) | Submitted to pipeline |
| health-h40 | v3 | PASSED | 4/4 TOO_EASY | Needs data traps |

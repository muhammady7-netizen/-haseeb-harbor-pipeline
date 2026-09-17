$ErrorActionPreference = 'Continue'
. 'C:\Users\Haseeb Mirza\Documents\Codex\Tools\TuringHarbor\setup-session.ps1'
$Harbor = 'C:\Users\Haseeb Mirza\Documents\Codex\Tools\uv-tools\harbor\Scripts\harbor.exe'
$Root = 'C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline'
Set-Location $Root

# Fresh job names so we don't mix with prior v17c trials
$oracleCfg = @{
  job_name = 'oracle-b39-l16-v17d'
  jobs_dir = "$Root\qc-out\harbor-jobs-b39"
  n_concurrent_trials = 1
  n_attempts = 4
  environment = @{ type = 'docker'; force_build = $true }
  verifier = @{ env = @{ OPENAI_API_KEY = ''; OPENAI_BASE_URL = 'http://34.41.10.8:4000/v1'; JUDGE_MODEL = 'openai/glm-5.2' } }
  agents = @(@{ name = 'oracle' })
  tasks = @(@{ path = "$Root\task-sources\law-b39\law-b39-l16-custody-letter-instruction-audit-v17" })
} | ConvertTo-Json -Depth 8
$glmCfg = @{
  job_name = 'glm-b39-l16-v17d'
  jobs_dir = "$Root\qc-out\harbor-jobs-b39"
  n_concurrent_trials = 2
  n_attempts = 4
  environment = @{ type = 'docker'; force_build = $true }
  agents = @(@{
    name = 'terminus-2'
    model_name = 'openai/glm-5.2'
    override_timeout_sec = 1800
    kwargs = @{ extra_body = @{ max_tokens = 16000 } }
  })
  tasks = @(@{ path = "$Root\task-sources\law-b39\law-b39-l16-custody-letter-instruction-audit-v17" })
  verifier = @{ env = @{ OPENAI_API_KEY = ''; OPENAI_BASE_URL = 'http://34.41.10.8:4000/v1'; JUDGE_MODEL = 'openai/glm-5.2' } }
} | ConvertTo-Json -Depth 10

$oraclePath = "$Root\tmp-pw\oracle-b39-l16-v17d-config.json"
$glmPath = "$Root\tmp-pw\glm-b39-l16-v17d-config.json"
[System.IO.File]::WriteAllText($oraclePath, $oracleCfg)
[System.IO.File]::WriteAllText($glmPath, $glmCfg)

Write-Host 'Starting oracle-b39-l16-v17d'
& $Harbor run -c $oraclePath -y --force-build *> "$Root\tmp-pw\oracle-b39-v17d-console.txt"
Write-Host "ORACLE_EXIT=$LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { Get-Content "$Root\tmp-pw\oracle-b39-v17d-console.txt" -Tail 60; exit $LASTEXITCODE }

python "$Root\tmp-pw\pack_v17d_oracle.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Starting glm-b39-l16-v17d'
& $Harbor run -c $glmPath -y --force-build *> "$Root\tmp-pw\glm-b39-v17d-console.txt"
Write-Host "GLM_EXIT=$LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { Get-Content "$Root\tmp-pw\glm-b39-v17d-console.txt" -Tail 60; exit $LASTEXITCODE }

python "$Root\tmp-pw\pack_v17d_glm_and_zip.py"
exit $LASTEXITCODE

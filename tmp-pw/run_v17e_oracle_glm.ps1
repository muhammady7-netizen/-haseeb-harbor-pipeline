$ErrorActionPreference = 'Continue'
. 'C:\Users\Haseeb Mirza\Documents\Codex\Tools\TuringHarbor\setup-session.ps1'
$Harbor = 'C:\Users\Haseeb Mirza\Documents\Codex\Tools\uv-tools\harbor\Scripts\harbor.exe'
$Root = 'C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline'
Set-Location $Root

python -c @"
import json
from pathlib import Path
root = Path(r'C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline')
pack = str(root / 'task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17')
jobs = str(root / 'qc-out/harbor-jobs-b39')
oracle = {
  'job_name': 'oracle-b39-l16-v17e',
  'jobs_dir': jobs,
  'n_concurrent_trials': 1,
  'n_attempts': 4,
  'environment': {'type': 'docker', 'force_build': True},
  'verifier': {'env': {'OPENAI_API_KEY': '', 'OPENAI_BASE_URL': 'http://34.41.10.8:4000/v1', 'JUDGE_MODEL': 'openai/glm-5.2'}},
  'agents': [{'name': 'oracle'}],
  'tasks': [{'path': pack}],
}
glm = {
  'job_name': 'glm-b39-l16-v17e',
  'jobs_dir': jobs,
  'n_concurrent_trials': 2,
  'n_attempts': 4,
  'environment': {'type': 'docker', 'force_build': True},
  'agents': [{
    'name': 'terminus-2',
    'model_name': 'openai/glm-5.2',
    'override_timeout_sec': 1800,
    'kwargs': {'extra_body': {'max_tokens': 16000}},
  }],
  'tasks': [{'path': pack}],
  'verifier': {'env': {'OPENAI_API_KEY': '', 'OPENAI_BASE_URL': 'http://34.41.10.8:4000/v1', 'JUDGE_MODEL': 'openai/glm-5.2'}},
}
(root/'tmp-pw/oracle-b39-l16-v17e-config.json').write_text(json.dumps(oracle, indent=2), encoding='utf-8')
(root/'tmp-pw/glm-b39-l16-v17e-config.json').write_text(json.dumps(glm, indent=2), encoding='utf-8')
print('configs written')
"@

Write-Host 'Starting oracle-b39-l16-v17e'
& $Harbor run -c "$Root\tmp-pw\oracle-b39-l16-v17e-config.json" -y --force-build *> "$Root\tmp-pw\oracle-b39-v17e-console.txt"
Write-Host "ORACLE_EXIT=$LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { Get-Content "$Root\tmp-pw\oracle-b39-v17e-console.txt" -Tail 80; exit $LASTEXITCODE }

python "$Root\tmp-pw\pack_v17e_oracle.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Starting glm-b39-l16-v17e'
& $Harbor run -c "$Root\tmp-pw\glm-b39-l16-v17e-config.json" -y --force-build *> "$Root\tmp-pw\glm-b39-v17e-console.txt"
Write-Host "GLM_EXIT=$LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { Get-Content "$Root\tmp-pw\glm-b39-v17e-console.txt" -Tail 80; exit $LASTEXITCODE }

python "$Root\tmp-pw\pack_v17e_glm_and_zip.py"
exit $LASTEXITCODE

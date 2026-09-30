# Local Harbor Run Method

## Prerequisites
1. Docker Desktop installed and running
2. Harbor CLI installed: `uv tool install harbor`
3. GLM key set up via setup-session.ps1
4. Both LOCAL zips extracted to temp dirs

## Step 1: Install Harbor
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:Path = "C:\Users\HASEEB~1\AppData\Local\Temp\opencode\run.py"; uv tool install harbor
```

## Step 2: Extract LOCAL zips
```powershell
# Task 1 LOCAL
python -c "
import zipfile; zipfile.ZipFile(r'C:\Users\Haseeb Mirza\Documents\Default Project\UPLOAD-THIS-TO-QC-the-answer-LOCAL.zip').extractall(r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\task1-local')
# Task 2 LOCAL
zipfile.ZipFile(r'C:\Users\Haseeb Mirza\Documents\Default Project\UPLOAD-THIS-TO-QC-the-thread-LOCAL.zip').extractall(r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\task2-local')
"
```

## Step 3: Run Oracle (verify 1.0)
```powershell
$env:Path = "C:\Users\Haseeb Mirza\AppData\Roaming\uv\tools\harbor\Scripts;C:\Users\Haseeb Mirza\.local\bin;$env:Path"
$env:PYTHONPATH = "C:\Users\Haseeb Mirza\AppData\Roaming\uv\tools\harbor\Lib\site-packages"
. 'C:\Users\Haseeb Mirza\Documents\Codex\Tools\TuringHarbor\setup-session.ps1'
$env:OPENAI_API_KEY = $env:WANDB_GLM_API_KEY
$env:OPENAI_BASE_URL = "http://34.41.10.8:4000/v1"
$env:JUDGE_MODEL = "openai/glm-5.2"
$env:PYTHONUTF8 = "1"

# Task 1 Oracle
& "C:\Users\Haseeb Mirza\AppData\Roaming\uv\tools\harbor\Scripts\python.exe" -c "
import sys, os
sys.argv = ['harbor','run',
  '-p', r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\task1-local\the-answer-she-already-gave',
  '-a', 'oracle',
  '--ve', 'OPENAI_API_KEY=' + os.environ['OPENAI_API_KEY'],
  '--ve', 'OPENAI_BASE_URL=http://34.41.10.8:4000/v1',
  '--ve', 'JUDGE_MODEL=openai/glm-5.2',
  '-o', r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\harbor-jobs-t1',
  '--job-name', 'oracle-t1',
  '-n', '1', '-y'
]
from harbor.cli.main import app
app(standalone_mode=False, obj={})
"

# Task 2 Oracle
& "C:\Users\Haseeb Mirza\AppData\Roaming\uv\tools\harbor\Scripts\python.exe" -c "
import sys, os
sys.argv = ['harbor','run',
  '-p', r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\task2-local\the-thread-that-outlived-its-own-start',
  '-a', 'oracle',
  '--ve', 'OPENAI_API_KEY=' + os.environ['OPENAI_API_KEY'],
  '--ve', 'OPENAI_BASE_URL=http://34.41.10.8:4000/v1',
  '--ve', 'JUDGE_MODEL=openai/glm-5.2',
  '-o', r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\harbor-jobs-t2',
  '--job-name', 'oracle-t2',
  '-n', '1', '-y'
]
from harbor.cli.main import app
app(standalone_mode=False, obj={})
"
```

## Step 4: Run GLM 4x (after Oracle passes 1.0)

IMPORTANT: Use `--agent-setup-timeout-multiplier 3` to avoid AgentSetupTimeoutError.

Create config files first:
```python
import json
config = {
    "job_name": "glm-4x-task1",
    "jobs_dir": "C:/Users/HASEEB~1/AppData/Local/Temp/opencode/harbor-glm-t1",
    "n_concurrent_trials": 1,
    "tasks": [{"path": "C:/Users/HASEEB~1/AppData/Local/Temp/opencode/task1-local/the-answer-she-already-gave"}],
    "verifier": {"env": {"OPENAI_API_KEY": "${OPENAI_API_KEY}", "OPENAI_BASE_URL": "http://34.41.10.8:4000/v1", "JUDGE_MODEL": "openai/glm-5.2"}},
    "agents": [{"name": "opencode", "model_name": "glm/glm-5.2", "env": {"OPENAI_API_KEY": "${OPENAI_API_KEY}", "OPENAI_BASE_URL": "http://34.41.10.8:4000/v1"}, "kwargs": {"opencode_config": {"provider": {"glm": {"npm": "@ai-sdk/openai-compatible", "name": "GLM Gateway", "options": {"baseURL": "http://34.41.10.8:4000/v1", "apiKey": "{env:OPENAI_API_KEY}"}, "models": {"glm-5.2": {"name": "GLM-5.2", "reasonation": True, "interleaved": {"field": "reasoning_content"}, "options": {"max_tokens": 96000}, "limit": {"context": 200000, "output": 96000}}}}}}}}]}
}
# Save for both tasks
with open(r"C:\Users\Haseeb Mirza\Documents\Default Project\glm-harbor-config-task1.json", "w") as f: json.dump(config, f, indent=2)
# For task 2, change paths and job_name
config2 = json.loads(json.dumps(config))
config2["job_name"] = "glm-4x-task2"
config2["jobs_dir"] = "C:/Users/HASEEB~1/AppData/Local/Temp/opencode/harbor-glm-t2"
config2["tasks"] = [{"path": "C:/Users/HASEEB~1/AppData/Local/Temp/opencode/task2-local/the-thread-that-outlived-its-own-start"}]
with open(r"C:\Users\Haseeb Mirza\Documents\Default Project\glm-harbor-config-task2.json", "w") as f: json.dump(config2, f, indent=2)
```

Run GLM 4x:
```powershell
# Task 1 GLM 4x
& "C:\Users\Haseeb Mirza\AppData\Roaming\uv\tools\harbor\Scripts\python.exe" -c "
import sys
sys.argv = ['harbor','run','-c',r'C:\Users\Haseeb Mirza\Documents\Default Project\glm-harbor-config-task1.json','--agent-setup-timeout-multiplier','3','-n','1','-k','4','-y']
from harbor.cli.main import app
app(standalone_mode=False, obj={})
"

# Task 2 GLM 4x
& "C:\Users\Haseeb Mirza\AppData\Roaming\uv\tools\harbor\Scripts\python.exe" -c "
import sys
sys.argv = ['harbor','run','-c',r'C:\Users\Haseeb Mirza\Documents\Default Project\glm-harbor-config-task2.json','--agent-setup-timeout-multiplier','3','-n','1','-k','4','-y']
from harbor.cli.main import app
app(standalone_mode=False, obj={})
"
```

## Step 5: Check results
```python
import json, os
for name, base in [('T1', r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\harbor-glm-t1\glm-4x-task1'), ('T2', r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\harbor-glm-t2\glm-4x-task2')]:
    if os.path.exists(base):
        rp = os.path.join(base, 'result.json')
        if os.path.exists(rp):
            r = json.load(open(rp))
            done = r.get('stats',{}).get('n_completed_trials',0)
            err = r.get('stats',{}).get('n_errored_trials',0)
            print(f'{name}: done={done} err={err}')
            for d in sorted(os.listdir(base)):
                td = os.path.join(base, d)
                if os.path.isdir(td):
                    rtp = os.path.join(td, 'verifier', 'reward.txt')
                    if os.path.exists(rtp):
                        print(f'  {d.split("__")[1]}: {open(rtp).read().strip()}')
```

## Step 6: Run both in parallel (background processes)
```powershell
# Write run scripts
$t1 = @"
import sys, os, json
sys.argv = ['harbor','run',
  '-p', r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\task1-local\the-answer-she-already-gave',
  '-a', 'opencode', '-m', 'glm/glm-5.2',
  '--ae', 'OPENAI_API_KEY=' + os.environ['OPENAI_API_KEY'],
  '--ae', 'OPENAI_BASE_URL=http://34.41.10.8:4000/v1',
  '--ve', 'OPENAI_API_KEY=' + os.environ['OPENAI_API_KEY'],
  '--ve', 'OPENAI_BASE_URL=http://34.41.10.8:4000/v1',
  '--ve', 'JUDGE_MODEL=openai/glm-5.2',
  '--ak', 'opencode_config=' + json.dumps({'provider':{'glm':{'npm':'@ai-sdk/openai-compatible','name':'GLM Gateway','options':{'baseURL':'http://34.41.10.8:4000/v1','apiKey':'{env:OPENAI_API_KEY}'},'models':{'glm-5.2':{'name':'GLM-5.2','reasoning':True,'interleaved':{'field':'reasoning_content'}}}}}}),
  '--agent-setup-timeout-multiplier', '3',
  '-o', r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\harbor-glm-t1-par',
  '--job-name', 'glm-4x-t1',
  '-n', '1', '-k', '4', '-y'
]
from harbor.cli.main import app
app(standalone_mode=False, obj={})
"@
$t1 | Out-File -FilePath "$env:TEMP\opencode\run_t1.py" -Encoding utf8
$t2 = $t1.Replace('task1-local\the-answer-she-already-gave', 'task2-local\the-thread-that-outlived-its-own-start').Replace('harbor-glm-t1-par', 'harbor-glm-t2-par').Replace('glm-4x-t1', 'glm-4x-t2')
$t2 | Out-File -FilePath "$env:TEMP\opencode\run_t2.py" -Encoding utf8

# Start both in background
Start-Process -FilePath "C:\Users\Haseeb Mirza\AppData\Roaming\uv\tools\harbor\Scripts\python.exe" -ArgumentList "$env:TEMP\opencode\run_t1.py" -NoNewWindow
Start-Process -FilePath "C:\Users\Haseeb Mirza\AppData\Roaming\uv\tools\harbor\Scripts\python.exe" -ArgumentList "$env:TEMP\opencode\run_t2.py" -NoNewWindow
```

## Key things to know:
- Harbor exe is blocked by Application Control policy. Run via python.exe instead.
- Use `app(standalone_mode=False, obj={})` not `app()` — Typer needs this.
- Use `--agent-setup-timeout-multiplier 3` for GLM runs — without it, opencode install times out at 360s.
- LOCAL zips use `openai/glm-5.2` in manifest (your key only allows this).
- PORTAL zips use `openai/zoi-org/GLM-5.2` in manifest (portal runner handles the key).
- Oracle takes 4-8 min. GLM 4x takes 20-30 min.
- Check results with `reward.txt` in each trial's verifier folder.

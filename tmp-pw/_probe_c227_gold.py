import json
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of"
    r"\tasks\code-c227-work\code-c227-table-bloat-maintenance-audit"
)
work = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw\_c227_score_probe")
if work.exists():
    shutil.rmtree(work)
(work / "app").mkdir(parents=True)
shutil.copytree(SRC / "environment" / "input", work / "app" / "input")
for f in (SRC / "solution" / "files").iterdir():
    shutil.copy2(f, work / "app" / f.name)
shutil.copytree(SRC / "tests", work / "tests")
r = subprocess.run(
    [sys.executable, str(work / "tests" / "score.py")],
    cwd=str(work),
    capture_output=True,
    text=True,
)
txt = r.stdout
marker = '"reward"'
idx = txt.find(marker)
# walk back to opening brace
start = txt.rfind("{", 0, idx)
obj = json.loads(txt[start:])
print("reward", obj["reward"])
print("core_failures", obj["core_failures"])
print("passed", obj["passed"], "/", obj["total"])
for c in obj["checks"]:
    if not c["passed"]:
        print("FAIL", c["name"], c["tag"], c["detail"][:160])

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline")
sys.path.insert(0, str(ROOT / "tmp-pw"))

subprocess.check_call([sys.executable, str(ROOT / "tmp-pw" / "pack_b39_glm.py"), "--job", "glm-b39-l16-v17e"])

src = ROOT / "task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit/evaluations/glm-5.2"
dst = ROOT / "task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17/evaluations/glm-5.2"
if src.exists():
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    rewards = []
    for i in range(1, 5):
        rt = dst / f"r{i}" / "verifier" / "reward.txt"
        if rt.exists():
            rewards.append(rt.read_text(encoding="utf-8").strip())
    print("v17e GLM rewards", rewards, "passes", sum(1 for r in rewards if r in ("1.0", "1", "1.00")))

import rebuild_b39_zip as z

z.PACK = ROOT / "task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17"
z.write_review_csv = lambda path: print("keep review")
print("zip", z.build_zip())

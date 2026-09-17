import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_b39_oracle_stability as p

p.PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\task-sources\law-b39\law-b39-l16-custody-letter-instruction-audit-v17"
).resolve()
job = "oracle-b39-l16-v17g"
trials = p.find_trials(job)
good = [t for t in trials if str(p.reward_of(t)) in ("1.0", "1", "1.00") or p.reward_of(t) == 1.0]
seen = set()
distinct = []
for t in good:
    n = p.trial_name(t)
    if n not in seen:
        seen.add(n)
        distinct.append(t)
print("good", len(good), "distinct", len(distinct))
assert len(distinct) >= 4, len(distinct)
oracle = p.PACK / "evaluations" / "oracle"
stab = p.PACK / "evaluations" / "stability"
shutil.rmtree(oracle, ignore_errors=True)
shutil.rmtree(stab, ignore_errors=True)
stab.mkdir(parents=True)
shutil.copytree(distinct[0], oracle, ignore=p.ignore_bulk)
p.normalize_artifacts(oracle)
print("oracle", p.trial_name(distinct[0]))
for i, t in enumerate(distinct[1:4], 1):
    dest = stab / f"repeat-{i:02d}"
    shutil.copytree(t, dest, ignore=p.ignore_bulk)
    p.normalize_artifacts(dest)
    print(f"repeat-{i:02d}", p.trial_name(t))
print("packed oracle/stability ok")

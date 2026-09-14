#!/bin/bash
# Harbor verifier entrypoint. Harbor copies this to /tests/test.sh and runs it
# from the task working directory; reward is read back from
# /logs/verifier/reward.txt.
#
# Reward is FRACTIONAL (passed/total over per-check pytest cases), not binary.
# The denominator is ALWAYS the declared verifier count from verifier.json,
# not the observed passed+failed count, so a partial run cannot normalize to 1.0.
mkdir -p /logs/verifier

cd /app || exit 1

PYTHONPATH=/tests python3 -m pytest \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_outputs.py \
    -rA \
    2>&1 | tee /logs/verifier/test-stdout.txt
pytest_status=${PIPESTATUS[0]}

python3 - <<'PY'
import re, json
from pathlib import Path

# Always use the declared verifier count as the denominator
try:
    spec = json.loads(Path("/tests/verifier.json").read_text(encoding="utf-8"))
    declared_total = len(spec.get("verifiers", []))
except Exception:
    declared_total = 0

stdout = Path("/logs/verifier/test-stdout.txt")
text = stdout.read_text(encoding="utf-8", errors="replace") if stdout.exists() else ""

passed = failed = 0
m = re.search(
    r"=+\s*(?:(\d+)\s+failed,\s*)?(\d+)\s+passed(?:,\s*\d+\s+skipped)?\s+in\s+",
    text,
)
if m:
    failed = int(m.group(1) or 0)
    passed = int(m.group(2) or 0)
else:
    failed = len(re.findall(r"^FAILED\s+", text, flags=re.M))
    passed = len(re.findall(r"^PASSED\s+", text, flags=re.M))

# Use declared count as denominator (not observed total)
total = declared_total if declared_total > 0 else (passed + failed)
if total <= 0:
    reward = 0.0
else:
    reward = round(passed / total, 10)
    if passed == total:
        reward = 1.0

Path("/logs/verifier/reward.txt").write_text(f"{reward}\n", encoding="utf-8")
Path("/logs/verifier/reward_meta.txt").write_text(
    f"passed={passed}\nfailed={failed}\ntotal={total}\ndeclared={declared_total}\nreward={reward}\n",
    encoding="utf-8",
)
print(f"fractional_reward passed={passed} failed={failed} total={total} declared={declared_total} reward={reward}")
PY

# Always exit 0 so Harbor reads reward.txt (including fractional < 1.0).
exit 0

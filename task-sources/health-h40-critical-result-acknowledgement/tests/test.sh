#!/bin/bash
# Harbor verifier entrypoint. Harbor copies this to /tests/test.sh and runs it
# from the task working directory; reward is read back from
# /logs/verifier/reward.txt.
#
# Reward is FRACTIONAL (passed/total over per-check pytest cases), not binary.
# A near-miss run must not collapse to the same 0.0 as a 0/N run.
mkdir -p /logs/verifier

cd /app || exit 1

python3 -m pytest \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_outputs.py \
    -rA \
    2>&1 | tee /logs/verifier/test-stdout.txt
pytest_status=${PIPESTATUS[0]}

python3 - <<'PY'
import re
from pathlib import Path

stdout = Path("/logs/verifier/test-stdout.txt")
text = stdout.read_text(encoding="utf-8", errors="replace") if stdout.exists() else ""

passed = failed = errors = 0
m = re.search(
    r"=+\s*(?:(\d+)\s+failed,\s*)?(\d+)\s+passed(?:,\s*\d+\s+skipped)?(?:,\s*\d+\s+errors?)?\s+in\s+",
    text,
)
if m:
    failed = int(m.group(1) or 0)
    passed = int(m.group(2) or 0)
    errors = len(re.findall(r"^ERROR\s+", text, flags=re.M))
else:
    failed = len(re.findall(r"^FAILED\s+", text, flags=re.M))
    passed = len(re.findall(r"^PASSED\s+", text, flags=re.M))

total = passed + failed + errors
if total <= 0:
    try:
        import json
        spec = json.loads(Path("/tests/verifier.json").read_text(encoding="utf-8"))
        total = len(spec.get("verifiers", []))
    except Exception:
        total = 0
    reward = 0.0
else:
    reward = round(passed / total, 10)
    if passed == total:
        reward = 1.0

Path("/logs/verifier/reward.txt").write_text(f"{reward}\n", encoding="utf-8")
Path("/logs/verifier/reward_meta.txt").write_text(
    f"passed={passed}\nfailed={failed}\ntotal={total}\nreward={reward}\n",
    encoding="utf-8",
)
print(f"fractional_reward passed={passed} failed={failed} total={total} reward={reward}")
PY

# Always exit 0 so Harbor reads reward.txt (including fractional < 1.0).
exit 0

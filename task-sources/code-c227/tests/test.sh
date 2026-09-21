#!/bin/bash
# Harbor verifier entrypoint. Reward is FRACTIONAL (passed/total).
# CORE GATE: missing deliverable = 0 reward
# Pytest is launched from /tmp so a planted /app/pytest.py cannot shadow the real module.
mkdir -p /logs/verifier

# Core gate: check all deliverables exist under the workspace
cd /app || exit 1
for f in bloat_audit.csv bloat_memo.md results.json; do
    if [ ! -f "$f" ]; then
        echo "0.0" > /logs/verifier/reward.txt
        echo "missing_deliverable=$f" > /logs/verifier/reward_meta.txt
        exit 0
    fi
done

# Defensive: remove common shadow modules if an agent planted them
rm -f /app/pytest.py /app/pytest.pyc
rm -rf /app/pytest

# Keep workspace for tests; do not put /app first on sys.path
export HARBOR_TASK_WORKSPACE=/app
export WORKSPACE=/app
cd /tmp || exit 1
python3 -m pytest --rootdir=/app --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA 2>&1 | tee /logs/verifier/test-stdout.txt
pytest_status=${PIPESTATUS[0]}
python3 - <<'PYEOF'
import re, json
from pathlib import Path

stdout = Path("/logs/verifier/test-stdout.txt")
text = stdout.read_text(encoding="utf-8", errors="replace") if stdout.exists() else ""

passed = failed = 0
m = re.search(r"=+\s*(?:(\d+)\s+failed,?\s*)?(\d+)\s+passed(?:,?\s*(\d+)\s+skipped)?\s+in\s+", text)
if m:
    failed = int(m.group(1) or 0)
    passed = int(m.group(2) or 0)
else:
    failed = len(re.findall(r"^FAILED\s+", text, flags=re.M))
    passed = len(re.findall(r"^PASSED\s+", text, flags=re.M))

total = passed + failed
if total == 0:
    reward = 0.0
else:
    reward = round(passed / total, 10)
    if passed == total:
        reward = 1.0

Path("/logs/verifier/reward.txt").write_text(f"{reward}\n", encoding="utf-8")
Path("/logs/verifier/reward_meta.txt").write_text(
    f"passed={passed}\nfailed={failed}\ntotal={total}\nreward={reward}\n", encoding="utf-8"
)
print(f"fractional_reward passed={passed} failed={failed} total={total} reward={reward}")
PYEOF
exit 0

#!/bin/bash
# Harbor verifier entrypoint. Reward is FRACTIONAL (passed/total).
# CORE GATE: missing deliverable = 0 reward
# Grading runs in /app with PYTHONSAFEPATH/-P so cwd is NOT prepended to sys.path.
# Shadow modules in /app and /tmp are scrubbed. Reward is derived from CTRF
# (not agent-influenceable stdout). pytest_status gates fallback parsing.
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward_meta.txt
rm -f /logs/verifier/ctrf.json /logs/verifier/test-stdout.txt

# Ensure mounted /tests is readable for grading (image marker may be 000)
if command -v sudo >/dev/null 2>&1; then
    sudo chmod 755 /tests 2>/dev/null || chmod 755 /tests 2>/dev/null || true
else
    chmod 755 /tests 2>/dev/null || true
fi

cd /app || exit 1
for f in bloat_audit.csv bloat_memo.md results.json; do
    if [ ! -f "$f" ]; then
        echo "0.0" > /logs/verifier/reward.txt
        echo "missing_deliverable=$f" > /logs/verifier/reward_meta.txt
        exit 0
    fi
done

# Scrub planted shadow modules in workspace AND /tmp (shared-container residue)
rm -f /app/pytest.py /app/pytest.pyc /tmp/pytest.py /tmp/pytest.pyc
rm -rf /app/pytest /tmp/pytest
find /tmp -maxdepth 2 \( -name 'pytest.py' -o -name 'pytest' \) -user "$(id -un)" -exec rm -rf {} + 2>/dev/null || true

export HARBOR_TASK_WORKSPACE=/app
export WORKSPACE=/app
export PYTHONSAFEPATH=1
export PYTHONNOUSERSITE=1

# Stay in /app; -P prevents cwd from being prepended to sys.path for -m
python3 -P -m pytest --rootdir=/app --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA 2>&1 | tee /logs/verifier/test-stdout.txt
pytest_status=${PIPESTATUS[0]}
export PYTEST_STATUS="$pytest_status"

python3 -P - <<'PYEOF'
import json
import os
import re
from pathlib import Path

status = int(os.environ.get("PYTEST_STATUS", "1"))
ctrf_path = Path("/logs/verifier/ctrf.json")
stdout = Path("/logs/verifier/test-stdout.txt")
reward_path = Path("/logs/verifier/reward.txt")
meta_path = Path("/logs/verifier/reward_meta.txt")

# Always overwrite any pre-seeded reward artifact
if reward_path.exists() or reward_path.is_symlink():
    try:
        reward_path.unlink()
    except OSError:
        pass
if meta_path.exists() or meta_path.is_symlink():
    try:
        meta_path.unlink()
    except OSError:
        pass

passed = failed = 0
source = "none"

if ctrf_path.is_file():
    try:
        data = json.loads(ctrf_path.read_text(encoding="utf-8", errors="replace"))
        results = (data.get("results") or {})
        summary = results.get("summary") or data.get("summary") or {}
        # pytest-ctrf shapes vary; accept common keys
        if "passed" in summary or "failed" in summary:
            passed = int(summary.get("passed") or 0)
            failed = int(summary.get("failed") or 0)
            source = "ctrf_summary"
        else:
            tests = results.get("tests") or data.get("tests") or []
            if isinstance(tests, list) and tests:
                for t in tests:
                    st = (t.get("status") or t.get("result") or "").lower()
                    if st in ("passed", "pass", "success"):
                        passed += 1
                    elif st in ("failed", "fail", "error", "xfailed"):
                        if st != "xfailed":
                            failed += 1
                source = "ctrf_tests"
    except Exception as exc:
        source = f"ctrf_error:{exc}"

# Stdout fallback ONLY when pytest reported success and CTRF was empty
if passed + failed == 0 and status == 0:
    text = stdout.read_text(encoding="utf-8", errors="replace") if stdout.exists() else ""
    m = re.search(
        r"=+\s*(?:(\d+)\s+failed,?\s*)?(\d+)\s+passed(?:,?\s*(\d+)\s+skipped)?\s+in\s+",
        text,
    )
    if m:
        failed = int(m.group(1) or 0)
        passed = int(m.group(2) or 0)
        source = "stdout_fallback"

total = passed + failed
if total == 0 or (status != 0 and source.startswith("ctrf_error")):
    reward = 0.0
elif status != 0 and passed + failed == 0:
    reward = 0.0
else:
    reward = round(passed / total, 10) if total else 0.0
    if passed == total and total > 0:
        reward = 1.0

# If pytest failed hard with no parseable results, force zero
if status != 0 and total == 0:
    reward = 0.0

reward_path.write_text(f"{reward}\n", encoding="utf-8")
meta_path.write_text(
    f"passed={passed}\nfailed={failed}\ntotal={total}\nreward={reward}\n"
    f"pytest_status={status}\nsource={source}\n",
    encoding="utf-8",
)
print(
    f"fractional_reward passed={passed} failed={failed} total={total} "
    f"reward={reward} pytest_status={status} source={source}"
)
PYEOF
exit 0

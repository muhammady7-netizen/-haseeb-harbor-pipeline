#!/bin/bash
# Harbor verifier: score.py against tests/verifier.json (canonical grid).
mkdir -p /logs/verifier
ensure_reward() {
  if [ ! -s /logs/verifier/reward.txt ]; then
    echo 0.0 > /logs/verifier/reward.txt
  fi
}
trap ensure_reward EXIT

if command -v sudo >/dev/null 2>&1; then
  sudo chmod 755 /tests 2>/dev/null || true
  sudo chmod -R a+rX /tests 2>/dev/null || true
fi
chmod 755 /tests 2>/dev/null || true
chmod -R a+rX /tests 2>/dev/null || true

cd /app || exit 1
for f in bloat_audit.csv bloat_memo.md results.json; do
  if [ ! -f "$f" ]; then
    echo 0.0 > /logs/verifier/reward.txt
    echo "missing_deliverable=$f" > /logs/verifier/reward_meta.txt
    exit 0
  fi
done

export HARBOR_TASK_WORKSPACE=/app
python3 /tests/score.py > /logs/verifier/score.json || echo '{"reward":0.0}' > /logs/verifier/score.json
python3 -c "import json;print(json.load(open('/logs/verifier/score.json'))['reward'])" \
  > /logs/verifier/reward.txt || echo 0.0 > /logs/verifier/reward.txt
python3 - <<'PY'
import json
from pathlib import Path
s = json.loads(Path('/logs/verifier/score.json').read_text(encoding='utf-8'))
n = len(s.get('results', s.get('checks', [])) or [])
# fallback: count verifier.json
if not n:
    n = len(json.loads(Path('/tests/verifier.json').read_text(encoding='utf-8')).get('verifiers', []))
passed = sum(1 for r in (s.get('results') or []) if r.get('success') or r.get('passed'))
if not passed and 'reward' in s and s['reward'] == 1.0:
    passed = n
failed = max(0, n - passed) if n else 0
Path('/logs/verifier/reward_meta.txt').write_text(
    f"passed={passed}\nfailed={failed}\ntotal={n}\nreward={s.get('reward')}\n",
    encoding='utf-8',
)
PY
cat /logs/verifier/score.json || true
exit 0

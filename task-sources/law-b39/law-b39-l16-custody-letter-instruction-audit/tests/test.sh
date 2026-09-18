#!/bin/bash
# Harbor verifier entrypoint. Harbor copies this to /tests/test.sh and runs it from the task
# working directory; reward is read back from /logs/verifier/reward.txt.
#
# Two steps, deliberately separate:
#   1. pytest, for Harbor's per-check grid and the CTRF report - one test per verifier, so a
#      failure names the deliverable check that failed.
#   2. score.py, which decides the reward. It is NOT the pytest exit code: core checks
#      decide whether the work is right and incidental checks grade how the prose is
#      written, and a differently-worded memo must not score the same as delivering nothing.

# Always leave a reward file so Harbor never hits RewardFileNotFoundError.
mkdir -p /logs/verifier
ensure_reward() {
  if [ ! -s /logs/verifier/reward.txt ]; then
    echo 0.0 > /logs/verifier/reward.txt
  fi
}
trap ensure_reward EXIT

# Belt-and-suspenders unlock (image already ends at 755; needed if a mount is 000).
if command -v sudo >/dev/null 2>&1; then
  sudo chmod 755 /tests 2>/dev/null || true
  sudo chmod -R a+rX /tests 2>/dev/null || true
fi
chmod 755 /tests 2>/dev/null || true
chmod -R a+rX /tests 2>/dev/null || true

cd /app || exit 1

python3 -m pytest \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_outputs.py \
    -rA || true

python3 /tests/score.py > /logs/verifier/score.json || echo '{"reward":0.0}' > /logs/verifier/score.json
python3 -c "import json;print(json.load(open('/logs/verifier/score.json'))['reward'])" \
    > /logs/verifier/reward.txt || echo 0.0 > /logs/verifier/reward.txt

cat /logs/verifier/score.json || true

mkdir -p /logs/artifacts/app
for f in answer.md letter_line_review.csv results.json; do
  if [ -f "/app/$f" ]; then
    cp -f "/app/$f" "/logs/artifacts/app/$f"
  fi
done

exit 0

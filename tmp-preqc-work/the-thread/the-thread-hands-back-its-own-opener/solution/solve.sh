#!/usr/bin/env bash
set -euo pipefail
# /solution is docker-cp'd owned by the uploading uid, so --write-back can't
# rewrite golden_trajectory.json in place. Work from a private copy.
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cp -R /solution "$WORK/solution"
python3 "$WORK/solution/solve.py" --task-dir "$WORK" --write-back "$@"

# Writes /logs/agent/trajectory.json so trajectory verifiers see the oracle's replay.
SOLUTION_DIR="$WORK/solution" python3 "$WORK/solution/emit_oracle_trajectory.py"

# GCE override 2: the replay is gym tool calls only, so nothing in it puts a file
# on disk - and file_check grades /workspace. Materialise the ORACLE's own
# deliverables (report.md + metrics.json) there, built from artifact_plan.json so
# the numbers the grader reads and the numbers the oracle writes cannot drift.
SOLUTION_DIR="$WORK/solution" WORKSPACE="${TH_WORKSPACE_DIR:-/workspace}" \
    python3 "$WORK/solution/write_artifacts.py"

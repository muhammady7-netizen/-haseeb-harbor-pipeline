"""Replays the harness `file_check` spec against the task workspace.

One pytest per graded assertion, so Harbor's per-test grid (and the CTRF report)
names exactly which deliverable check failed. The spec in `verifier.json` and the
engine in `rl_world_verifiers/` are copies of what the task harness runs, so a
result here means the same thing it means there.
"""

import os
import sys
import csv
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from rl_world_verifiers.models import VerifierSpec, effective_weights  # noqa: E402
from rl_world_verifiers.sources.registry import SourceRegistry  # noqa: E402
from rl_world_verifiers.verifiers import verify_definition  # noqa: E402

WORKSPACE = Path(os.environ.get("HARBOR_TASK_WORKSPACE", "/app"))
SPEC = VerifierSpec.model_validate_json(
    (TESTS_DIR / "verifier.json").read_text(encoding="utf-8")
)
WEIGHTS = effective_weights(SPEC.verifiers)
REGISTRY = SourceRegistry(WORKSPACE)


@pytest.mark.parametrize(
    "definition",
    SPEC.verifiers,
    ids=[definition.name for definition in SPEC.verifiers],
)
def test_deliverable(definition):
    outcome = verify_definition(
        definition,
        REGISTRY,
        WEIGHTS[definition.name],
        config=SPEC.config,
        completion_fn=None,
    )["result"]
    detail = outcome.get("error") or outcome.get("reason") or "assertion failed"
    assert outcome["success"], f"{definition.name}: {detail}"


def _count_csv_data_rows(name):
    p = WORKSPACE / name
    if not p.is_file():
        return None
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    return max(len(rows) - 1, 0)


def test_brief_coherence_row_count():
    n = _count_csv_data_rows("brief_coherence.csv")
    assert n == 8, f"brief_coherence.csv expected 8 data rows, got {n}"


def test_question_trace_row_count():
    n = _count_csv_data_rows("question_trace.csv")
    assert n == 48, f"question_trace.csv expected 48 data rows, got {n}"

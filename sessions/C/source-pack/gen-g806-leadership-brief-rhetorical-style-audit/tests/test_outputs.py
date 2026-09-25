"""Replays the harness `file_check` spec against the task workspace.

One pytest per graded assertion, so Harbor's per-test grid (and the CTRF report)
names exactly which deliverable check failed.
"""

import os
import sys
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


def test_memo_min_length():
    """The style_audit_memo.md must be at least 800 characters.

    Enforced as a pytest assertion (not a regex_match on a .md file, which the
    platform PreQC blocks) on top of the verifier.json contains-checks.
    """
    memo_path = WORKSPACE / "style_audit_memo.md"
    assert memo_path.is_file(), f"style_audit_memo.md missing at {memo_path}"
    text = memo_path.read_text(encoding="utf-8")
    assert len(text) >= 800, (
        f"style_audit_memo.md is {len(text)} characters; minimum is 800"
    )


def test_audit_row_count():
    """script_style_audit.csv must have exactly the right number of data rows."""
    import csv
    audit_path = WORKSPACE / "script_style_audit.csv"
    assert audit_path.is_file(), f"script_style_audit.csv missing at {audit_path}"
    with audit_path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    n = max(0, len(rows) - 1)
    assert n == 2472, f"script_style_audit.csv has {n} data rows; expected 2472"

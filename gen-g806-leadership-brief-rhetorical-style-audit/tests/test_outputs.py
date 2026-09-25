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


def test_memo_numbers_match_results():
    """The memo must not state numbers that contradict results.json.

    Catches a hollow memo that lists tokens with wrong counts.
    """
    import json
    memo_path = WORKSPACE / "style_audit_memo.md"
    results_path = WORKSPACE / "results.json"
    assert memo_path.is_file(), "style_audit_memo.md missing"
    assert results_path.is_file(), "results.json missing"
    memo_text = memo_path.read_text(encoding="utf-8")
    results = json.loads(results_path.read_text(encoding="utf-8"))
    # Check that key results numbers appear in the memo
    for key in ("script_count", "flagged_count", "uncited_scripture_count",
                "runtime_breach_count"):
        expected = results[key]
        # The memo must mention this number somewhere
        assert str(expected) in memo_text, (
            f"style_audit_memo.md does not mention {key}={expected}"
        )


def test_memo_has_explanatory_sentences():
    """The memo must have actual sentences, not just token dumps.

    Rejects a hollow memo that only lists required tokens with no reasoning.
    Each finding category must appear in a sentence (at least 20 chars context).
    """
    import re
    memo_path = WORKSPACE / "style_audit_memo.md"
    assert memo_path.is_file(), "style_audit_memo.md missing"
    text = memo_path.read_text(encoding="utf-8")
    # Check that the memo has sentences (period followed by capital or newline)
    sentences = re.split(r"[.\n]\s*(?:[A-Z#]|$)", text)
    real_sentences = [s.strip() for s in sentences if len(s.strip()) >= 20]
    assert len(real_sentences) >= 5, (
        f"style_audit_memo.md has only {len(real_sentences)} substantive sentences; "
        f"need at least 5 (explains each finding + testimony exemption)"
    )
    # Check that 'exemption' appears near 'testimony' (not just as isolated tokens)
    testimony_ctx = [s for s in real_sentences if "testimony" in s.lower()]
    exemption_ctx = [s for s in real_sentences if "exemption" in s.lower()]
    assert len(testimony_ctx) >= 1, "No sentence discusses testimony"
    assert len(exemption_ctx) >= 1, "No sentence discusses exemption"

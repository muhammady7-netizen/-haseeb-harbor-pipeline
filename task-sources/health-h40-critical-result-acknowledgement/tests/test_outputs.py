"""Replays the harness `file_check` spec against the task workspace.

One pytest per graded assertion, so Harbor's per-test grid (and the CTRF report)
names exactly which deliverable check failed. The spec in `verifier.json` and the
engine in `rl_world_verifiers/` are copies of what the task harness runs, so a
result here means the same thing it means there.
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
    (TESTS_DIR / "verifier.json").read_text(encoding="utf-8-sig")
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


def _register_ids(workspace: Path) -> list[str]:
    import csv
    path = workspace / "input" / "critical_results.csv"
    assert path.is_file(), "input/critical_results.csv missing"
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [(row.get("result_id") or "").strip() for row in csv.DictReader(f) if (row.get("result_id") or "").strip()]


def _audit_findings(workspace: Path) -> dict[str, str]:
    import csv
    path = workspace / "results_audit.csv"
    assert path.is_file(), "results_audit.csv missing"
    findings: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rid = (row.get("result_id") or "").strip()
            if rid:
                findings[rid] = (row.get("findings") or "").strip()
    return findings


def _h40_totals(workspace: Path) -> dict[str, int]:
    findings = _audit_findings(workspace)
    def has(token: str) -> int:
        return sum(1 for f in findings.values() if token in {p.strip() for p in f.split(";")})
    return {
        "notification_breaches": has("notification_late"),
        "acknowledgement_breaches": has("acknowledgement_late"),
        "unapproved_acknowledgement_results": has("acknowledger_unapproved"),
        "missing_escalation_results": has("escalation_missing"),
        "results_compliant": sum(1 for f in findings.values() if f == "compliant"),
    }


def test_audit_covers_full_register():
    """Sparse audits (spot-check rows only) must not earn full reward."""
    register = _register_ids(WORKSPACE)
    findings = _audit_findings(WORKSPACE)
    assert register, "register is empty"
    assert set(findings) == set(register), (
        f"audit IDs {sorted(findings)} != register IDs {sorted(register)}"
    )
    assert len(findings) == len(register), "duplicate or missing audit rows"


def test_results_recomputed_from_audit():
    """results.json counts must equal finding tokens summed from results_audit.csv."""
    import json
    totals = _h40_totals(WORKSPACE)
    path = WORKSPACE / "results.json"
    assert path.is_file(), "results.json missing"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    for key, expected in totals.items():
        assert isinstance(data.get(key), int), f"{key} must be int, got {type(data.get(key)).__name__}"
        assert data.get(key) == expected, f"results.json {key}={data.get(key)!r} != audit-derived {expected!r}"


def test_memo_addresses_key_content():
    """Memo must address escalation, clock start, late notifications, unapproved acknowledgements, and non-breach cases."""
    import re
    memo = (WORKSPACE / "results_memo.md").read_text(encoding="utf-8").lower()
    
    # Memo must address escalation
    assert "escalat" in memo, "Memo must address escalation"
    
    # Memo must address clock start
    assert "clock" in memo, "Memo must address clock start"
    
    # Memo must explain midnight or weekend non-breach
    assert ("midnight" in memo or "weekend" in memo or "out of hours" in memo or "non-breach" in memo), "Memo must explain midnight/weekend non-breach"
    
    # Memo must have explanatory body (not just a table)
    assert len(memo) > 200, "Memo must have explanatory body (>200 chars)"
    
    # Memo must explain non-breach cases (inclusive boundaries or core-hours)
    assert ("inclusive" in memo or "boundary" in memo or "core hours" in memo or "core-hours" in memo or "not a finding" in memo or "not a breach" in memo), "Memo must explain non-breach cases"
    
    # Memo must list late notifications (R-09 or late notification)
    assert ("r-09" in memo or "r09" in memo or "late notification" in memo), "Memo must list late notifications"
    
    # Memo must list ack breaches
    assert ("acknowledgement" in memo and ("breach" in memo or "late" in memo)), "Memo must list ack breaches"
    
    # Memo must list R-10 absent ack
    assert ("r-10" in memo or "r10" in memo or "absent" in memo), "Memo must list absent ack R-10"
    
    # Memo must list R-15 after hours ack
    assert ("r-15" in memo or "r15" in memo or "after hours" in memo), "Memo must list after hours ack R-15"
    
    # Memo must list R-16 before closing breach
    assert ("r-16" in memo or "r16" in memo or "before closing" in memo or "closing breach" in memo), "Memo must list before closing breach R-16"
    
    # Memo must list R-40 late notification
    assert ("r-40" in memo or "r40" in memo), "Memo must list R-40 late notification"
    
    # Memo must name phlebotomist unapproved
    assert ("phlebotomist" in memo or "unapproved" in memo), "Memo must name phlebotomist/unapproved"
    
    # Memo must name the unapproved acknowledgement
    assert "unapproved" in memo, "Memo must name the unapproved acknowledgement"



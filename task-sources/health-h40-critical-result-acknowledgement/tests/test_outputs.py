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
    """Memo must address all required content themes."""
    import re
    memo = (WORKSPACE / "results_memo.md").read_text(encoding="utf-8").lower()
    memo_text = (WORKSPACE / "results_memo.md").read_text(encoding="utf-8")
    
    # Memo must address escalation
    assert "escalat" in memo, "Memo must address escalation"
    
    # Memo must address clock start
    assert "clock" in memo, "Memo must address clock start"
    
    # Memo must explain non-breach cases
    assert ("midnight" in memo or "weekend" in memo or "out of hours" in memo or 
            "non-breach" in memo or "not a breach" in memo or "not as breaches" in memo or
            "saturday" in memo or "sunday" in memo or "inclusive" in memo or 
            "core hours" in memo or "core-hours" in memo or "boundary" in memo or
            "not a finding" in memo or "window limit" in memo), "Memo must explain non-breach cases"
    
    # Memo must have explanatory body
    assert len(memo) > 200, "Memo must have explanatory body (>200 chars)"
    
    # Memo must mention notification window
    assert ("30" in memo and "notification" in memo) or ("240" in memo and "notification" in memo) or ("notification window" in memo), "Memo must mention notification window"
    
    # Memo must mention acknowledgement window
    assert ("60" in memo and "acknowledgement" in memo) or ("480" in memo and "acknowledgement" in memo) or ("acknowledgement window" in memo), "Memo must mention acknowledgement window"
    
    # Memo must address unapproved acknowledgers (accept register token or prose form)
    assert ("ward_clerk" in memo or "ward clerk" in memo or "phlebotomist" in memo or 
            "nurse_hca" in memo or "nurse hca" in memo or "healthcare_assistant" in memo or
            "healthcare assistant" in memo or "pharmacist" in memo or "unapproved" in memo or
            "not on the approved list" in memo), "Memo must name unapproved role"
    
    # Memo must address missing escalations
    assert ("escalation" in memo and ("missing" in memo or "absence" in memo or "no escalation" in memo)), "Memo must address missing escalations"
    
    # Memo must name at least 2 specific late notification result IDs
    late_ids = sum(1 for rid in ["r-02", "r-09", "r-13", "r-16", "r-21", "r-26", "r-31", "r-40", "r-47", "r-53"] if rid in memo)
    assert late_ids >= 2, f"Memo must name at least 2 late notification result IDs (found {late_ids})"
    
    # Memo must name at least 2 specific late/absent acknowledgement result IDs
    ack_ids = sum(1 for rid in ["r-03", "r-04", "r-06", "r-10", "r-13", "r-15", "r-16", "r-22", "r-24", "r-27", "r-30", "r-32", "r-33", "r-35", "r-45", "r-49", "r-52", "r-53", "r-54", "r-55"] if rid in memo)
    assert ack_ids >= 2, f"Memo must name at least 2 late/absent ack result IDs (found {ack_ids})"


def test_audit_per_row_correctness():
    """Every audit row must have correct escalation_status and acknowledgement_minutes."""
    import csv
    audit_path = WORKSPACE / "results_audit.csv"
    assert audit_path.is_file(), "results_audit.csv missing"
    with audit_path.open(encoding="utf-8-sig", newline="") as f:
        audit = list(csv.DictReader(f))
    
    valid_esc_status = {"not_required", "recorded", "missing"}
    
    for row in audit:
        rid = row["result_id"].strip()
        findings = row.get("findings", "").strip().lower()
        ack_mins = row.get("acknowledgement_minutes", "").strip()
        esc_status = row.get("escalation_status", "").strip().lower()
        
        # Check acknowledgement_minutes is empty for unapproved acknowledgers
        if "acknowledger_unapproved" in findings:
            assert ack_mins == "", f"{rid}: acknowledgement_minutes must be empty for unapproved acknowledger, got {ack_mins}"
        
        # Check escalation_status is one of the three valid values
        assert esc_status in valid_esc_status, f"{rid}: escalation_status must be not_required/recorded/missing, got {esc_status}"
        
        # Check escalation_status is consistent with findings
        if "acknowledgement_late" in findings and "escalation_missing" in findings:
            assert esc_status == "missing", f"{rid}: escalation_status must be 'missing' when escalation_missing in findings"
        elif "acknowledgement_late" in findings and "escalation_missing" not in findings:
            assert esc_status == "recorded", f"{rid}: escalation_status must be 'recorded' when ack late but no escalation_missing"
        elif "acknowledgement_late" not in findings:
            assert esc_status == "not_required", f"{rid}: escalation_status must be 'not_required' when no ack late"

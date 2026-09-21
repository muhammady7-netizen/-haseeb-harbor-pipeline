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

# Resolve JUDGE_MODEL for rubric checks (D3 fix)
import os as _os
JUDGE_MODEL = _os.environ.get('JUDGE_MODEL', 'openai/glm-5.2')


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
    text = path.read_text(encoding="utf-8-sig")
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") and not (
            stripped.startswith("#,") or ("," in stripped[:12] and stripped.split(",", 1)[0] in {"#ARCH", "#DUP", "#"})
        ):
            # free-text header comments
            if stripped.startswith("# ") or stripped.startswith("#Critical") or stripped.startswith("# Critical"):
                continue
        lines.append(line)
    ids: list[str] = []
    for row in csv.DictReader(lines):
        rid = (row.get("result_id") or "").strip()
        if not rid or rid.startswith("#"):
            continue
        ids.append(rid)
    return ids


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


def test_v15_hard_trap_findings():
    """Per-row findings for v15 densify traps (coverage_depth)."""
    findings = _audit_findings(WORKSPACE)
    expected = {
        "R-67": "compliant",
        "R-68": "acknowledgement_late;escalation_missing",
        "R-69": "acknowledgement_late;escalation_missing",
        "R-70": "compliant",
        "R-71": "compliant",
        "R-72": "notification_late;acknowledgement_late;escalation_missing",
        "R-73": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-74": "notification_late;acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-75": "notification_late",
        "R-76": "compliant",
        "R-77": "notification_late;acknowledgement_late;escalation_missing",
        "R-78": "notification_late",
        "R-79": "notification_late;acknowledgement_late;escalation_missing",
        "R-80": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
    }
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {rid}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{rid} findings {got!r} != {want_n!r}"
        )


def test_v15_unapproved_empty_acknowledgement_minutes():
    """Harbor fairness: unapproved roles leave acknowledgement_minutes empty."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = { (r.get("result_id") or "").strip(): r for r in csv.DictReader(f) }
    for rid in ("R-73", "R-74", "R-80"):
        row = rows[rid]
        assert "acknowledger_unapproved" in (row.get("findings") or "")
        assert (row.get("acknowledgement_minutes") or "").strip() == "", (
            f"{rid} must have empty acknowledgement_minutes"
        )



def test_v16_hard_trap_findings():
    """Per-row findings for v16 densify traps (coverage_depth)."""
    findings = _audit_findings(WORKSPACE)
    expected = {
        "R-81": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-82": "notification_late;acknowledgement_late;acknowledger_unapproved",
        "R-83": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-84": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-85": "notification_late;acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-86": "notification_late;acknowledgement_late;escalation_missing",
        "R-87": "compliant",
        "R-88": "notification_late",
        "R-89": "compliant",
        "R-90": "acknowledgement_late;escalation_missing",
        "R-91": "acknowledgement_late;escalation_missing",
        "R-92": "compliant",
        "R-93": "acknowledgement_late;acknowledger_unapproved",
        "R-94": "acknowledgement_late;escalation_missing",
        "R-95": "notification_late;acknowledgement_late",
        "R-96": "notification_late",
        "R-97": "compliant",
        "R-98": "compliant",
        "R-99": "notification_late;acknowledgement_late;escalation_missing",
        "R-100": "notification_late;acknowledgement_late;escalation_missing",
        "R-101": "notification_late;acknowledgement_late;acknowledger_unapproved",
        "R-102": "compliant",
        "R-103": "compliant",
        "R-104": "acknowledgement_late;acknowledger_unapproved;escalation_missing",
        "R-105": "notification_late;acknowledgement_late;acknowledger_unapproved",
    }
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {rid}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{rid} findings {got!r} != {want_n!r}"
        )


def test_v16_recorded_escalation_not_missing():
    """Recorded-escalation traps must NOT carry escalation_missing."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    for rid in ("R-82", "R-93", "R-95", "R-101", "R-105"):
        row = rows[rid]
        assert (row.get("escalation_status") or "").strip() == "recorded", rid
        assert "escalation_missing" not in (row.get("findings") or ""), rid
        if "acknowledger_unapproved" in (row.get("findings") or ""):
            assert (row.get("acknowledgement_minutes") or "").strip() == "", rid


def test_v16_unapproved_empty_acknowledgement_minutes():
    """Harbor fairness: unapproved roles leave acknowledgement_minutes empty."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    for rid in ("R-81", "R-82", "R-83", "R-84", "R-85", "R-93", "R-101", "R-104", "R-105"):
        row = rows[rid]
        assert "acknowledger_unapproved" in (row.get("findings") or ""), rid
        assert (row.get("acknowledgement_minutes") or "").strip() == "", (
            f"{rid} must have empty acknowledgement_minutes"
        )


def test_v18_structural_trap_findings():
    """Per-row findings for v18 multi-doc / holiday / site / alias traps."""
    findings = _audit_findings(WORKSPACE)
    expected = {'R-106': 'notification_late;acknowledgement_late;escalation_missing', 'R-107': 'notification_late;acknowledgement_late;escalation_missing', 'R-108': 'compliant', 'R-109': 'acknowledgement_late;acknowledger_unapproved;escalation_missing', 'R-110': 'compliant', 'R-111': 'acknowledgement_late;escalation_missing', 'R-112': 'compliant', 'R-113': 'compliant', 'R-114': 'compliant', 'R-115': 'compliant', 'R-116': 'notification_late', 'R-117': 'notification_late;acknowledgement_late;acknowledger_unapproved', 'R-118': 'compliant'}
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {rid}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{rid} findings {got!r} != {want_n!r}"
        )


def test_v18_unapproved_empty_acknowledgement_minutes():
    """Harbor fairness: unapproved roles leave acknowledgement_minutes empty."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    for rid in ("R-109", "R-117", "R-120", "R-131", "R-132", "R-133", "R-134"):
        row = rows[rid]
        assert "acknowledger_unapproved" in (row.get("findings") or ""), rid
        assert (row.get("acknowledgement_minutes") or "").strip() == "", (
            f"{rid} must have empty acknowledgement_minutes"
        )


def test_v18_recorded_escalation_not_missing():
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    for rid in ("R-117", "R-132", "R-134"):
        row = rows[rid]
        assert (row.get("escalation_status") or "").strip() == "recorded", rid
        assert "escalation_missing" not in (row.get("findings") or ""), rid


def test_v18_memo_breach_ids_have_detail():
    """Every breach ID in the memo must appear with a minute figure or window name."""
    import csv
    import re as _re
    memo = (WORKSPACE / "results_memo.md").read_text(encoding="utf-8-sig")
    with (WORKSPACE / "results_audit.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    breach_ids = [
        (r.get("result_id") or "").strip()
        for r in rows
        if (r.get("findings") or "").strip() not in ("", "compliant")
    ]
    assert breach_ids
    missing = []
    for rid in breach_ids:
        pat = _re.compile(
            _re.escape(rid) + r".{0,500}(?:\d+\s*min|window|minutes|notification|acknowledgement)",
            _re.I | _re.S,
        )
        if not pat.search(memo):
            missing.append(rid)
    assert not missing, f"memo missing minute/window detail for: {missing[:10]}"


def test_v18_comment_rows_not_in_audit():
    findings = _audit_findings(WORKSPACE)
    for bad in ("#ARCH", "#DUP"):
        assert bad not in findings, f"comment row {bad} must not appear in audit"


def test_v19_structural_trap_findings():
    """Per-row findings for v19 Harbor densify traps (audit/results graded)."""
    findings = _audit_findings(WORKSPACE)
    expected = {'R-119': 'compliant', 'R-120': 'acknowledgement_late;acknowledger_unapproved;escalation_missing', 'R-121': 'notification_late;acknowledgement_late;escalation_missing', 'R-122': 'compliant'}
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {rid}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{rid} findings {got!r} != {want_n!r}"
        )


def test_v19_main_1700_not_riverside_deferred():
    """R-121 must keep clock at MAIN release 17:00 (not next-morning deferral)."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    row = rows["R-121"]
    assert (row.get("clock_start") or "").replace(" ", "T").startswith("2026-07-14T17:00")
    assert (row.get("notification_minutes") or "").strip() in {"930", "930.0"}
    assert (row.get("acknowledgement_minutes") or "").strip() in {"1380", "1380.0"}
    assert "notification_late" in (row.get("findings") or "")
    assert "acknowledgement_late" in (row.get("findings") or "")
    assert "escalation_missing" in (row.get("findings") or "")


def test_v19_memo_concept_checks_no_closed_ids():
    """Softened memo verifiers must not require a closed result-ID set."""
    import json
    import re as _re
    data = json.loads((TESTS_DIR / "verifier.json").read_text(encoding="utf-8-sig"))
    names = {
        "memo_explains_pre_clock_or_1759",
        "memo_explains_tier_or_preclock_non_breach",
        "memo_explains_r89_or_r103_non_breach",
        "memo_addresses_the_clock_start",
        "memo_lists_r106_or_r110_holiday",
    }
    for v in data["verifiers"]:
        if v["name"] not in names:
            continue
        exp = v["assertion"]["expected"]
        assert not _re.search(r"\\bR-\d+", exp) and not _re.search(r"\bR-\d+\b", exp), (
            f"{v['name']} still gates on result IDs"
        )


def test_v20_structural_trap_findings():
    """Per-row findings for v20 amendment / multi-doc traps (audit/results graded)."""
    findings = _audit_findings(WORKSPACE)
    expected = {'R-123': 'compliant', 'R-124': 'notification_late;acknowledgement_late;escalation_missing', 'R-125': 'notification_late;acknowledgement_late;escalation_missing', 'R-126': 'compliant', 'R-127': 'compliant', 'R-128': 'compliant', 'R-129': 'compliant', 'R-130': 'compliant', 'R-131': 'acknowledgement_late;acknowledger_unapproved;escalation_missing', 'R-132': 'acknowledgement_late;acknowledger_unapproved', 'R-133': 'acknowledgement_late;acknowledger_unapproved;escalation_missing', 'R-134': 'acknowledgement_late;acknowledger_unapproved'}
    for rid, want in expected.items():
        assert rid in findings, f"missing audit row {rid}"
        got = ";".join(p.strip() for p in findings[rid].split(";") if p.strip())
        want_n = ";".join(p.strip() for p in want.split(";") if p.strip())
        assert set(got.split(";")) == set(want_n.split(";")), (
            f"{rid} findings {got!r} != {want_n!r}"
        )


def test_v20_amendment_boundary_twins():
    """R-123 pre-amendment defers; R-124 post-amendment stays at release."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    pre = rows["R-123"]
    post = rows["R-124"]
    assert (pre.get("clock_start") or "").replace(" ", "T").startswith("2026-07-15T08:00")
    assert (pre.get("findings") or "").strip() == "compliant"
    assert (post.get("clock_start") or "").replace(" ", "T").startswith("2026-07-15T17:30")
    assert "notification_late" in (post.get("findings") or "")
    assert "acknowledgement_late" in (post.get("findings") or "")


def test_v20_amendment_deferred_open_riverside_vs_main():
    """R-128 amended RIVERSIDE deferred open 09:00 vs R-129 MAIN 08:00."""
    import csv
    path = WORKSPACE / "results_audit.csv"
    assert path.is_file()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {(r.get("result_id") or "").strip(): r for r in csv.DictReader(f)}
    assert (rows["R-128"].get("clock_start") or "").replace(" ", "T").startswith("2026-07-18T09:00")
    assert (rows["R-129"].get("clock_start") or "").replace(" ", "T").startswith("2026-07-18T08:00")
    assert (rows["R-128"].get("findings") or "").strip() == "compliant"
    assert (rows["R-129"].get("findings") or "").strip() == "compliant"


def test_v20_amendment_file_present():
    p = WORKSPACE / "input" / "procedure_amendment_2026-07-01.md"
    assert p.is_file(), "amendment file must be present under input/"
    text = p.read_text(encoding="utf-8")
    assert "2026-07-15" in text
    assert "RIVERSIDE" in text or "Riverside" in text

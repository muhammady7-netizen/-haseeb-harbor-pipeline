"""Replays the harness `file_check` spec against the task workspace.

One pytest per graded assertion, so Harbor's per-test grid (and the CTRF report)
names exactly which deliverable check failed. The spec in `verifier.json` and the
engine in `rl_world_verifiers/` are copies of what the task harness runs, so a
result here means the same thing it means there.
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
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


def _sid_key(value):
    return value.strip().casefold()


def _normalize_site(value):
    import re
    v = value.strip()
    m = re.fullmatch(r"[Ss](\d+)", v)
    assert m, f"bad site {value!r}"
    return f"S{m.group(1)}"


def _parse_date(value):
    return date.fromisoformat(value.strip().replace("/", "-"))


def _input_rows():
    """Reconcile source data and amendments so expectations are never constants."""
    with (WORKSPACE / "input" / "allocations.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "input/allocations.csv is empty"
    by_key = {}
    for row in rows:
        clean = {key: value.strip() for key, value in row.items()}
        by_key[_sid_key(clean["subject_id"])] = clean
    with (WORKSPACE / "input" / "allocation_amendments.csv").open(newline="", encoding="utf-8-sig") as handle:
        amendments = list(csv.DictReader(handle))
    latest = {}
    for amendment in amendments:
        clean = {
            key: (" ".join(value) if isinstance(value, list) else (value or "")).strip()
            for key, value in amendment.items()
            if key is not None
        }
        key = _sid_key(clean["subject_id"])
        revision = int(clean["revision"])
        if key not in latest or revision > latest[key][0]:
            latest[key] = (revision, clean)
    allocation_fields = ("site", "disease_severity", "block_id", "sequence_no", "arm", "randomised_date")
    for key, (_, amendment) in latest.items():
        if amendment["record_status"].casefold() == "void":
            by_key.pop(key, None)
            continue
        if key in by_key:
            record = dict(by_key[key])
            report_id = record["subject_id"].strip()
        else:
            record = {"subject_id": amendment["subject_id"].strip()}
            report_id = record["subject_id"]
        for field in allocation_fields:
            if amendment[field]:
                record[field] = amendment[field]
        assert all(record.get(field) for field in allocation_fields), f"incomplete current amendment for {report_id}"
        record["subject_id"] = report_id
        record["arm"] = record["arm"].strip().casefold()
        record["site"] = _normalize_site(record["site"])
        record["disease_severity"] = record["disease_severity"].strip().casefold()
        record["sequence_no"] = str(int(record["sequence_no"].strip()))
        record["randomised_date"] = _parse_date(record["randomised_date"]).isoformat()
        by_key[key] = record
    for key, record in list(by_key.items()):
        record["arm"] = record["arm"].strip().casefold()
        record["site"] = _normalize_site(record["site"])
        record["disease_severity"] = record["disease_severity"].strip().casefold()
        record["sequence_no"] = str(int(str(record["sequence_no"]).strip()))
        record["randomised_date"] = _parse_date(record["randomised_date"]).isoformat()
        by_key[key] = record
    return list(by_key.values())


def _pct(active, subjects):
    value = Decimal(active) * Decimal(100) / Decimal(subjects)
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _outside(active_pct, tolerance):
    return abs(Decimal(str(active_pct)) - Decimal("66.7")) > Decimal(str(tolerance))


def _sequence_findings(rows):
    findings = []
    by_site = defaultdict(list)
    for row in rows:
        by_site[row["site"]].append(row)
    for site_rows in by_site.values():
        ordered = sorted(site_rows, key=lambda row: (_parse_date(row["randomised_date"]), row["subject_id"]))
        previous = None
        for row in ordered:
            sequence = int(row["sequence_no"])
            if previous is not None and sequence < previous:
                findings.append(row["subject_id"])
            previous = sequence
    return findings


def _read_csv(name):
    with (WORKSPACE / name).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _as_int(row, key):
    return int(row[key].strip())


def _as_float(row, key):
    return float(row[key].strip().rstrip("%"))


def test_stratum_balance_recomputes_from_allocations():
    source = _input_rows()
    delivered = _read_csv("stratum_balance.csv")
    keyed = {(row["factor"].strip().lower(), row["level"].strip()): row for row in delivered}
    groups = {("overall", "all"): source}
    for factor, source_key in (("site", "site"), ("severity", "disease_severity")):
        for level in sorted({row[source_key] for row in source}):
            groups[(factor, level)] = [row for row in source if row[source_key] == level]
    assert set(keyed) == set(groups), "stratum table must contain exactly the input-derived rows"

    sequence_by_site = defaultdict(int)
    for subject_id in _sequence_findings(source):
        site = next(row["site"] for row in source if row["subject_id"] == subject_id)
        sequence_by_site[site] += 1
    for key, rows in groups.items():
        actual = keyed[key]
        active = sum(row["arm"].strip().lower() == "active" for row in rows)
        subjects = len(rows)
        active_pct = _pct(active, subjects)
        status = "outside_tolerance" if _outside(active_pct, 5 if key[0] == "overall" else 8) else "within_tolerance"
        assert _as_int(actual, "subjects") == subjects
        assert _as_int(actual, "active") == active
        assert _as_int(actual, "control") == subjects - active
        assert abs(_as_float(actual, "active_pct") - active_pct) < 0.05
        assert actual["status"].strip().lower() == status
        if key[0] == "site":
            assert _as_int(actual, "out_of_sequence") == sequence_by_site[key[1]]


def test_block_balance_recomputes_from_allocations():
    source = _input_rows()
    delivered = _read_csv("block_balance.csv")
    keyed = {(row["stratum"].strip(), row["block_id"].strip()): row for row in delivered}
    groups = defaultdict(list)
    for row in source:
        groups[(row["site"], row["block_id"])].append(row)
    assert set(keyed) == set(groups), "block table must contain exactly the input-derived rows"
    for key, rows in groups.items():
        actual = keyed[key]
        subjects = len(rows)
        active = sum(row["arm"].strip().lower() == "active" for row in rows)
        status = "not_assessed" if subjects != 6 else ("outside_tolerance" if active < 3 or active > 5 else "within_tolerance")
        assert _as_int(actual, "subjects") == subjects
        assert _as_int(actual, "active") == active
        assert _as_int(actual, "control") == subjects - active
        assert actual["block_status"].strip().lower() == status


def test_results_reconcile_to_inputs_and_delivered_tables():
    source = _input_rows()
    strata = _read_csv("stratum_balance.csv")
    blocks = _read_csv("block_balance.csv")
    results = json.loads((WORKSPACE / "results.json").read_text(encoding="utf-8"))
    expected = {
        "active_proportion_pct": _pct(sum(row["arm"].strip().lower() == "active" for row in source), len(source)),
        "strata_outside_tolerance": sum(row["factor"].strip().lower() != "overall" and row["status"].strip().lower() == "outside_tolerance" for row in strata),
        "blocks_assessed": sum(row["block_status"].strip().lower() != "not_assessed" for row in blocks),
        "blocks_outside_tolerance": sum(row["block_status"].strip().lower() == "outside_tolerance" for row in blocks),
        "out_of_sequence_allocations": len(_sequence_findings(source)),
    }
    assert set(results) == set(expected)
    for key, value in expected.items():
        if key == "active_proportion_pct":
            assert isinstance(results[key], (int, float)) and not isinstance(results[key], bool)
            assert abs(float(results[key]) - value) < 0.05
        else:
            assert type(results[key]) is int, f"{key} must be a JSON integer count"
            assert results[key] == value


def test_findings_name_every_input_derived_sequence_exception():
    text = (WORKSPACE / "randomisation_findings.md").read_text(encoding="utf-8").lower()
    assert all(subject_id.lower() in text for subject_id in _sequence_findings(_input_rows()))

def test_findings_address_sequence_integrity():
    text = (WORKSPACE / "randomisation_findings.md").read_text(encoding="utf-8").lower()
    assert re.search(r"(?i)sequence|out of order|ascending", text), "Findings must address sequence integrity"


def test_findings_address_tolerances():
    text = (WORKSPACE / "randomisation_findings.md").read_text(encoding="utf-8").lower()
    assert re.search(r"(?i)toleran|percentage point|drift|range", text), "Findings must address tolerances"


def test_findings_address_overfill_or_incomplete():
    text = (WORKSPACE / "randomisation_findings.md").read_text(encoding="utf-8").lower()
    assert re.search(r"(?is)(?:B\d+[\s\S]{0,200}(?:not[_ ]?assessed|over-?fill|incomplete|still filling|still being filled|excluded from assessment|fewer than|not enough|under-?filled|under-?filling|not yet complete|not yet filled)|(?:not[_ ]?assessed|over-?fill|incomplete|still filling|still being filled|excluded from assessment|fewer than|not enough|under-?filled|under-?filling|not yet complete|not yet filled)[\s\S]{0,200}B\d+)", text), "Findings must address overfill/incomplete blocks"


def test_findings_address_boundary_blocks_or_equality():
    text = (WORKSPACE / "randomisation_findings.md").read_text(encoding="utf-8").lower()
    assert re.search(r"(?is)(?:B\d+[\s\S]{0,200}(?:within[_ ]?tolerance|outside[_ ]?tolerance|3 or 5|equality at 5\.0|5 pp|deviat|not deviat|breach|breaching|within limit|outside limit|compliant|non-?compliant)|(?:within[_ ]?tolerance|outside[_ ]?tolerance|3 or 5|equality at 5\.0|5 pp|deviat|not deviat|breach|breaching|within limit|outside limit|compliant|non-?compliant)[\s\S]{0,200}B\d+)", text), "Findings must address boundary blocks"


def test_findings_address_ledger_normalisation():
    text = (WORKSPACE / "randomisation_findings.md").read_text(encoding="utf-8").lower()
    assert re.search(r"(?is)(amendment[\s-]*ledger|correction[\s-]*ledger|ledger[\s-]*of[\s-]*amendments|allocation[\s_-]*amend\w*|amend\w*.{0,60}ledger|ledger.{0,60}amend\w*|reconcil\w*.{0,60}(ledger|amend)|applied.{0,60}(ledger|amend)|ledger.{0,60}(reconcil\w*|applied))", text), "Findings must reference the amendment ledger"


def test_findings_name_correct_outside_tolerance_strata():
    """Findings must name the correct outside-tolerance strata (computed from gold)."""
    source = _input_rows()
    strata = _read_csv("stratum_balance.csv")
    outside = [r for r in strata if r["status"].strip().lower() == "outside_tolerance" and r["factor"].strip().lower() != "overall"]
    within = [r for r in strata if r["status"].strip().lower() == "within_tolerance" and r["factor"].strip().lower() != "overall"]
    text = (WORKSPACE / "randomisation_findings.md").read_text(encoding="utf-8").lower()
    for r in outside:
        factor = r["factor"].strip().lower()
        level = r["level"].strip().lower()
        assert level in text, f"Findings must name {level} as outside tolerance"
        idx = text.find(level)
        context = text[max(0, idx - 100):idx + 100]
        # Must say outside/exceed/breach, NOT "not outside" or "within"
        assert ("outside" in context or "exceed" in context or "breach" in context or "fail" in context), f"Findings must describe {level} as outside/exceeding tolerance"
        assert "not outside" not in context and "not exceed" not in context, f"Findings must not negate {level} outside tolerance"
    for r in within:
        level = r["level"].strip().lower()
        idx = text.find(level)
        if idx >= 0:
            context = text[max(0, idx - 100):idx + 100]
            assert "outside" not in context or "not outside" in context or "within" in context, f"Findings must not describe {level} as outside when it is within tolerance"

def test_findings_state_overall_drift():
    """Findings must state the overall drift direction (active_pct vs target 66.7%)."""
    results = json.loads((WORKSPACE / "results.json").read_text(encoding="utf-8"))
    pct = results["active_proportion_pct"]
    text = (WORKSPACE / "randomisation_findings.md").read_text(encoding="utf-8").lower()
    pct_str = str(pct)
    assert pct_str in text or str(int(pct)) in text, f"Findings must state the active proportion ({pct}%)"
    # Must NOT claim "no drift" or "within tolerance" when outside
    if pct < 66.7:
        diff = round(66.7 - pct, 1)
        assert diff >= 5.0, "Overall is outside 5pp tolerance"
        # Must say it's outside/below, NOT claim within/no drift
        assert ("outside" in text or "below" in text or "under" in text or "less than" in text), f"Findings must state drift is outside tolerance (active_pct={pct} below target 66.7%)"
        assert "no drift" not in text and "within tolerance" not in text[:text.find(pct_str)+200] if pct_str in text else True, "Must not claim no drift when drift exists"
    else:
        assert ("above" in text or "over" in text or "exceed" in text), f"Findings must state overall drift (active_pct={pct} above target 66.7%)"

def test_balance_has_expected_columns():
    rows = _read_csv("stratum_balance.csv")
    cols = set(rows[0].keys()) if rows else set()
    expected = {"factor", "level", "subjects", "active", "control", "active_pct", "out_of_sequence", "status"}
    assert expected.issubset(cols), f"Missing columns: {expected - cols}"

def test_blocks_have_expected_columns():
    rows = _read_csv("block_balance.csv")
    cols = set(rows[0].keys()) if rows else set()
    expected = {"stratum", "block_id", "subjects", "active", "control", "block_status"}
    assert expected.issubset(cols), f"Missing columns: {expected - cols}"

def test_balance_covers_both_factors():
    rows = _read_csv("stratum_balance.csv")
    factors = {r["factor"].strip().lower() for r in rows}
    assert "site" in factors and "severity" in factors, "Must have both site and severity factors"

def test_site_levels_use_canonical_S_codes():
    rows = _read_csv("stratum_balance.csv")
    for r in rows:
        if r["factor"].strip().lower() == "site":
            level = r["level"].strip()
            assert re.match(r"^S[123]$", level), f"Site level must be S1/S2/S3, got {level}"

def test_out_of_sequence_blank_on_non_site_rows():
    rows = _read_csv("stratum_balance.csv")
    for r in rows:
        factor = r["factor"].strip().lower()
        oos = r.get("out_of_sequence", "").strip()
        if factor in ("overall", "severity"):
            assert oos == "", f"out_of_sequence must be blank on {factor} row, got {oos!r}"
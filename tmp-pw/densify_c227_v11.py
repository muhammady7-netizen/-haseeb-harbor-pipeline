"""c227 v11 — ignore per-row audit_date; valid_until must be strictly > audit_date.

Fair: both rules are in policy_amendment_2026-08-20.md. Agents that use each
row's audit_date column or keep valid_until >= miss several tables.
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\tmp-pw\c227-fix-accepted\code-c227-table-bloat-maintenance-audit"
)
AUDIT = date(2026, 9, 1)  # policy/amendment anchor — NOT the CSV column
STALE_MIN_DAYS = 30
LARGE_STALE_TIGHTEN = 0.10
SMALL_STALE_TIGHTEN = 0.05


def rhu(x: float, nd: int = 2) -> float:
    q = Decimal("1").scaleb(-nd)
    return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def days_ago(n: int) -> str:
    return (AUDIT - timedelta(days=n)).isoformat()


def fmt_ratio(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def row(
    tid: str,
    *,
    pages: int,
    dead: int,
    size_export: str = "large",
    auto: str = "True",
    vac: str = "auto",
    la_days: int = 10,
    days_field: int | None = None,
    maint: str = "False",
    bloat_export: str | None = None,
    audit_export: str | None = None,
) -> dict:
    ratio = rhu(dead / pages, 2)
    return {
        "table_name": tid,
        "size_class": size_export,
        "total_pages": str(pages),
        "dead_pages": str(dead),
        "bloat_ratio": bloat_export if bloat_export is not None else fmt_ratio(ratio),
        "autovacuum_enabled": auto,
        "vacuum_type": vac,
        "audit_date": audit_export if audit_export is not None else AUDIT.isoformat(),
        "last_analyzed": days_ago(la_days),
        "days_since_analyze": str(days_field if days_field is not None else la_days),
        "maintenance_active": maint,
    }


def compute_finding(tid: str, r: dict, reidx: dict) -> tuple[str, str, float, bool, int]:
    pages = int(r["total_pages"])
    dead = int(r["dead_pages"])
    ratio = rhu(dead / pages, 2)
    size = "large" if pages >= 500 else "small"
    cap = 0.2 if size == "large" else 0.4
    vac_off = r["autovacuum_enabled"].lower() == "false" or r["vacuum_type"] == "manual"
    la = date.fromisoformat(r["last_analyzed"])
    # Always use policy AUDIT anchor — ignore CSV audit_date column
    stale_days = (AUDIT - la).days
    stale = stale_days >= STALE_MIN_DAYS
    if stale:
        tight = LARGE_STALE_TIGHTEN if size == "large" else SMALL_STALE_TIGHTEN
        cap = rhu(cap - tight, 2)
    finding = "none"
    if vac_off:
        finding = "AUTOVACUUM_DISABLED"
    else:
        exempt = False
        if r["maintenance_active"].lower() == "true" and tid in reidx:
            rr = reidx[tid]
            # v11: valid_until must be strictly after audit anchor
            if rr["approved"].lower() == "true" and date.fromisoformat(rr["valid_until"]) > AUDIT:
                exempt = True
        if (not exempt) and ratio > cap + 1e-12:
            finding = "BLOAT_THRESHOLD_EXCEEDED"
        elif stale:
            finding = "STALE_STATISTICS"
    return finding, size, ratio, stale, stale_days


AMENDMENT = """# Policy amendment DBOPS-31-A — issued 2026-08-20

Effective for the September 2026 maintenance audit, this amendment **supersedes**
selected clauses of `maintenance_policy.md` as stated below. The binding audit
calendar date for every calculation in this audit is **2026-09-01** (the issued
audit date). Unlisted clauses stay in force.

## 1. Audit-date anchor (new / clarifying)

Do **not** use the `audit_date` column from `table_health.csv` when computing
staleness or reindex validity. Some export rows carry a stale or incorrect
`audit_date` value. Always use the issued audit date **2026-09-01** from this
amendment / the monthly review header.

## 2. Exact-30-day staleness boundary (supersedes §3)

Statistics are stale when `(2026-09-01 - last_analyzed).days >= 30`.
Exactly 30 days **is** stale for this audit.

## 3. Large-table stale cap tightening (supersedes §3 tightening for large)

When statistics are stale:
- **large** (`total_pages >= 500`): reduce the bloat cap by **0.10** (effective **0.10**).
- **small** (`total_pages < 500`): keep baseline **0.05** reduction (effective **0.35**).

Apply tightening before the bloat comparison. Precedence: autovacuum → bloat → stale.

## 4. Manual vacuum override is case-sensitive (clarifies §1)

`vacuum_type` must equal exactly `manual` (all lowercase). `Manual`, `MANUAL`,
or values with surrounding spaces do **not** trigger `AUTOVACUUM_DISABLED`.

## 5. Reindex validity is exclusive of audit_date (supersedes §2 exemption date rule)

A reindex exempts bloat only when `maintenance_active` AND `approved=True` AND
`valid_until` is **strictly after** the issued audit date (`valid_until > 2026-09-01`).
A `valid_until` that equals `2026-09-01` is **not** exempt for this audit.

## 6. Reindex log duplicates

If `reindex_log.csv` has more than one row for the same `table_name`, the **last**
occurrence is authoritative.

## Unchanged

Round-half-up from `dead_pages` / `total_pages`, size class from `total_pages` only,
ignore `days_since_analyze` / export `size_class` / `dashboard_suggested_findings.csv`,
sort by `last_analyzed` then `table_name`.
"""


def main() -> None:
    health_path = PACK / "environment" / "input" / "table_health.csv"
    reindex_path = PACK / "environment" / "input" / "reindex_log.csv"
    dash_path = PACK / "environment" / "input" / "dashboard_suggested_findings.csv"
    amend_path = PACK / "environment" / "input" / "policy_amendment_2026-08-20.md"
    gold_path = PACK / "solution" / "files" / "bloat_audit.csv"
    results_path = PACK / "solution" / "files" / "results.json"
    memo_path = PACK / "solution" / "files" / "bloat_memo.md"
    tests_path = PACK / "tests" / "test_outputs.py"
    instr_path = PACK / "instruction.md"

    amend_path.write_text(AMENDMENT, encoding="utf-8", newline="\n")

    health = list(csv.DictReader(health_path.open(encoding="utf-8-sig")))
    fields = list(health[0].keys())
    health = [r for r in health if int(r["table_name"].split("-")[1]) <= 117]

    # Poison audit_date on several rows (agents using CSV column will mis-compute)
    poison = {
        "T-09": "2026-08-01",   # if used: days=0 from la → not stale → wrong none
        "T-63": "2026-10-01",   # if used: negative/weird
        "T-97": "2025-09-01",   # if used: huge stale
        "T-112": "2026-07-15",
        "T-50": "2026-08-20",
    }
    for r in health:
        if r["table_name"] in poison:
            r["audit_date"] = poison[r["table_name"]]

    new_rows = [
        # Lying audit_date + exactly-30
        row("T-118", pages=1000, dead=180, la_days=30, days_field=1, audit_export="2026-08-01"),
        # valid_until == audit was exempt under old rule; now BLOAT (T-65 already); reinforce
        row("T-119", pages=1000, dead=300, maint="True", la_days=7, audit_export="2026-09-15"),
        row("T-120", pages=1000, dead=280, maint="True", la_days=8, audit_export="2026-08-01"),
    ]
    health = [r for r in health if int(r["table_name"].split("-")[1]) <= 117] + new_rows

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(health)
    health_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    reindex = list(csv.DictReader(reindex_path.open(encoding="utf-8-sig")))
    rfields = list(reindex[0].keys())
    # Ensure T-65 stays valid_until == audit (now NOT exempt)
    # Add T-119: valid_until == audit (not exempt); T-120: valid_until > audit (exempt)
    reindex = [r for r in reindex if int(r["table_name"].split("-")[1]) <= 106]
    reindex += [
        {"table_name": "T-119", "approved": "True", "valid_until": "2026-09-01"},  # == → not exempt
        {"table_name": "T-120", "approved": "True", "valid_until": "2026-09-02"},  # > → exempt
    ]
    # Fix T-65 if present to == audit
    for r in reindex:
        if r["table_name"] == "T-65":
            r["valid_until"] = "2026-09-01"

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rfields, lineterminator="\n")
    w.writeheader()
    w.writerows(reindex)
    reindex_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    by_last: dict[str, dict] = {}
    for r in health:
        by_last[r["table_name"]] = r
    reidx: dict[str, dict] = {}
    for r in reindex:
        reidx[r["table_name"]] = r

    decoy = [{
        "table_name": tid,
        "suggested_finding": "none" if tid[-1] in "02468" else "BLOAT_THRESHOLD_EXCEEDED",
        "note": "health-dashboard heuristic — not authoritative",
    } for tid in by_last]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["table_name", "suggested_finding", "note"], lineterminator="\n")
    w.writeheader()
    w.writerows(decoy)
    dash_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    gold_rows = []
    for tid, r in by_last.items():
        finding, size, ratio, stale, stale_days = compute_finding(tid, r, reidx)
        gold_rows.append({
            "table_name": tid,
            "size_class": size,
            "bloat_ratio": fmt_ratio(ratio),
            "finding": finding,
            "_la": r["last_analyzed"],
            "_dead": int(r["dead_pages"]),
            "_pages": int(r["total_pages"]),
            "_stale_days": stale_days,
            "_vac": r["vacuum_type"],
            "_auto": r["autovacuum_enabled"],
            "_size_export": r["size_class"],
            "_days_field": r["days_since_analyze"],
            "_maint": r["maintenance_active"],
            "_audit_export": r["audit_date"],
            "_amend_boundary": stale_days == 30,
            "_poison_audit": r["audit_date"] != AUDIT.isoformat(),
        })
    gold_rows.sort(key=lambda g: (g["_la"], g["table_name"]))

    # Sanity: T-65 should now be BLOAT if maint+ratio high
    for g in gold_rows:
        if g["table_name"] in ("T-65", "T-119", "T-120", "T-09", "T-118"):
            print("KEY", g["table_name"], g["finding"], "days", g["_stale_days"], "audit_export", g["_audit_export"])

    gfields = ["table_name", "size_class", "bloat_ratio", "finding"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=gfields, lineterminator="\n")
    w.writeheader()
    w.writerows([{k: g[k] for k in gfields} for g in gold_rows])
    gold_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    counts = Counter(g["finding"] for g in gold_rows)
    results = {
        "flagged_count": sum(1 for g in gold_rows if g["finding"] != "none"),
        "autovacuum_disabled_count": counts["AUTOVACUUM_DISABLED"],
        "bloat_exceeded_count": counts["BLOAT_THRESHOLD_EXCEEDED"],
        "stale_statistics_count": counts["STALE_STATISTICS"],
        "compliant_count": counts["none"],
    }
    results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("n_tables", len(gold_rows), "results", results)

    expected = {g["table_name"]: {
        "size_class": g["size_class"],
        "bloat_ratio": float(g["bloat_ratio"]),
        "finding": g["finding"],
    } for g in gold_rows}
    src = tests_path.read_text(encoding="utf-8")
    body = "EXPECTED_TABLES = {\n"
    for tid in sorted(expected, key=lambda t: (len(t), t)):
        e = expected[tid]
        body += (
            f'    "{tid}": {{"size_class": "{e["size_class"]}", '
            f'"bloat_ratio": {fmt_ratio(e["bloat_ratio"])}, "finding": "{e["finding"]}"}},\n'
        )
    body += "}"
    src, n = re.subn(r"EXPECTED_TABLES = \{.*?\n\}", body, src, count=1, flags=re.S)
    assert n == 1
    res_body = "EXPECTED_RESULTS = {\n" + "".join(f'    "{k}": {v},\n' for k, v in results.items()) + "}"
    src, n = re.subn(r"EXPECTED_RESULTS = \{.*?\n\}", res_body, src, count=1, flags=re.S)
    assert n == 1
    src, n = re.subn(
        r'def test_audit_exact_row_count\(\):\n    """CSV must have exactly \d+ data rows \(no extra, no missing\)\."""\n'
        r"    rows, err = _load_csv\(\)\n"
        r"    assert err is None, err\n"
        r'    assert len\(rows\) == \d+, f"Expected \d+ rows, got \{len\(rows\)\}"',
        "def test_audit_exact_row_count():\n"
        f'    """CSV must have exactly {len(gold_rows)} data rows (no extra, no missing)."""\n'
        "    rows, err = _load_csv()\n"
        "    assert err is None, err\n"
        f'    assert len(rows) == {len(gold_rows)}, '
        f'f"Expected {len(gold_rows)} rows, got {{len(rows)}}"',
        src,
        count=1,
    )
    assert n == 1

    memo_map = {}
    for g in gold_rows:
        tid = g["table_name"]
        if g["finding"] == "none":
            continue
        num = int(tid.split("-")[1])
        concepts = [g["finding"], str(g["_dead"]), str(g["_pages"])]
        if g["_poison_audit"] or g["_amend_boundary"]:
            concepts += ["amendment", "2026-09-01"]
        if g["size_class"] == "large" and g["_stale_days"] >= STALE_MIN_DAYS:
            concepts += ["0.10"]
        if g["_amend_boundary"]:
            concepts += ["30"]
        if g["finding"] == "BLOAT_THRESHOLD_EXCEEDED":
            concepts += [str(g["bloat_ratio"]), "compute"]
            if g["_stale_days"] >= STALE_MIN_DAYS:
                concepts += ["tighten", "stale"]
            if g["_size_export"].lower() == "medium":
                concepts += ["medium"]
            if g["_maint"].lower() == "true":
                if tid not in reidx:
                    concepts += ["unapproved", "reindex"]
                elif reidx[tid]["approved"].lower() == "false":
                    concepts += ["unapproved", "reindex"]
                elif date.fromisoformat(reidx[tid]["valid_until"]) <= AUDIT:
                    concepts += ["expired", "reindex"]
        elif g["finding"] == "STALE_STATISTICS":
            concepts += [str(g["_stale_days"]), "stale", "days_since_analyze"]
        else:
            if g["_vac"] == "manual":
                concepts += ["manual", "vacuum", "override"]
            else:
                concepts += ["autovacuum", "disabled"]
        if num >= 46 or g["_amend_boundary"] or g["_poison_audit"] or num == 9:
            memo_map[tid] = concepts

    for name in ("MEMO_V8_STRICT", "MEMO_V9_STRICT", "MEMO_V10_STRICT", "MEMO_V11_STRICT"):
        src = re.sub(rf"\n{name} = \{{.*?\n\}}\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\n@pytest.mark.parametrize\(\"table_id\", sorted\(MEMO_V\d+_STRICT.*?\n", "\n", src, flags=re.S)
    for fn in (
        "test_memo_v8_strict_local_evidence",
        "test_memo_v9_strict_local_evidence",
        "test_memo_v10_strict_local_evidence",
        "test_memo_v11_strict_local_evidence",
        "test_ignores_dashboard_suggested_findings",
        "test_applies_policy_amendment_boundary",
        "test_vacuum_type_case_sensitive_manual",
        "test_ignores_export_audit_date_column",
    ):
        src = re.sub(rf"\ndef {fn}\(.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)

    embed = "MEMO_V11_STRICT = " + json.dumps(memo_map, indent=4) + "\n"
    block = f'''
{embed}

@pytest.mark.parametrize("table_id", sorted(MEMO_V11_STRICT.keys(), key=lambda t: (len(t), t)))
def test_memo_v11_strict_local_evidence(table_id):
    """Densify / amendment non-none tables need local memo evidence."""
    concepts = MEMO_V11_STRICT[table_id]
    assert _memo_mentions(table_id, *concepts), (
        f"Memo must explain {{table_id}} with local evidence {{concepts}}"
    )


def test_ignores_dashboard_suggested_findings():
    import csv as _csv
    dash = WORKSPACE / "input" / "dashboard_suggested_findings.csv"
    if not dash.is_file():
        dash = Path("/app/input/dashboard_suggested_findings.csv")
    assert dash.is_file()
    suggested = {{r["table_name"]: r["suggested_finding"] for r in _csv.DictReader(dash.open(encoding="utf-8-sig"))}}
    rows, err = _load_csv()
    assert err is None, err
    mismatches = sum(1 for r in rows if suggested.get(r["table_name"]) != r["finding"])
    assert mismatches >= 10


def test_applies_policy_amendment_boundary():
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    assert by["T-09"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-63"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-65"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"  # valid_until == audit not exempt
    assert by["T-93"]["finding"] == "none"
    assert by["T-110"]["finding"] == "AUTOVACUUM_DISABLED"
    assert by["T-112"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-119"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-120"]["finding"] == "none"


def test_vacuum_type_case_sensitive_manual():
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    assert by["T-93"]["finding"] == "none"
    assert by["T-110"]["finding"] == "AUTOVACUUM_DISABLED"


def test_ignores_export_audit_date_column():
    """Poisoned CSV audit_date must not change findings vs issued 2026-09-01 anchor."""
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    assert by["T-09"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-118"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
'''
    src = src.rstrip() + "\n" + block
    src = re.sub(
        r"(@pytest\.mark\.parametrize\(\"table_id\", sorted\(MEMO_V\d+_STRICT[^)]*\)\)\s*)+\n(?=MEMO_V11_STRICT)",
        "",
        src,
    )
    tests_path.write_text(src, encoding="utf-8", newline="\n")

    # Memo (compact bullets)
    old_memo = memo_path.read_text(encoding="utf-8")
    old_body = re.sub(r"(?s)^# Table maintenance audit.*?\n## ", "## ", old_memo, count=1)
    if old_body.startswith("#"):
        parts = old_memo.split("\n## ", 1)
        old_body = ("## " + parts[1]) if len(parts) == 2 else old_memo
    for section in ("Densify traps", "Cap-equality compliance", "Dashboard decoy", "Policy amendment"):
        old_body = re.sub(rf"\n## {section}.*", "\n", old_body, count=1, flags=re.S)
    for i in range(46, 130):
        old_body = re.sub(rf"\n- \*\*T-{i}\*\*:.*?(?=\n- \*\*|\n## |\Z)", "\n", old_body, flags=re.S)
    old_body = re.sub(r"\n- \*\*T-09\*\*:.*?(?=\n- \*\*|\n## |\Z)", "\n", old_body, flags=re.S)

    flagged = [g for g in gold_rows if g["finding"] != "none"]
    compliant = [g for g in gold_rows if g["finding"] == "none"]
    header = [
        f"# Table maintenance audit — {len(gold_rows)} unique tables",
        "",
        f"{len(gold_rows)} unique tables under DBOPS-31-A (issued audit date 2026-09-01). "
        f"{len(compliant)} compliant, {len(flagged)} flagged. Ignore CSV audit_date column; "
        f"valid_until must be strictly after 2026-09-01; large stale tighten 0.10; "
        f"vacuum_type manual is lowercase-exact.",
        "",
        "| Table | Size class | Bloat ratio | Finding |",
        "|---|---|---|---|",
    ]
    for g in gold_rows:
        header.append(f"| {g['table_name']} | {g['size_class']} | {g['bloat_ratio']} | {g['finding']} |")
    header.append("")

    dens = [
        "",
        "## Policy amendment DBOPS-31-A",
        "",
        "Issued audit date 2026-09-01 anchors staleness and reindex checks (ignore export "
        "audit_date). >=30 days stale; large tighten 0.10; valid_until > 2026-09-01; "
        "exact lowercase manual only.",
        "",
        "## Densify traps (T-46+ / amendment edges)",
        "",
    ]
    for g in flagged:
        tid = g["table_name"]
        num = int(tid.split("-")[1])
        if num < 46 and not g["_amend_boundary"] and not g["_poison_audit"]:
            continue
        dead, pages, ratio, finding = g["_dead"], g["_pages"], g["bloat_ratio"], g["finding"]
        stale_days = g["_stale_days"]
        poison = ""
        if g["_poison_audit"]:
            poison = (
                f" Export audit_date={g['_audit_export']} is ignored; amendment anchors "
                f"2026-09-01."
            )
        if finding == "AUTOVACUUM_DISABLED":
            dens.append(
                f"- **{tid}**: vacuum_type={g['_vac']!r} with dead_pages={dead} / total_pages={pages}; "
                f"exact lowercase manual/autovacuum-disabled checked first. Finding: AUTOVACUUM_DISABLED."
            )
        elif finding == "STALE_STATISTICS":
            dens.append(
                f"- **{tid}**: {stale_days} days stale vs 2026-09-01 (ignore days_since_analyze="
                f"{g['_days_field']}); dead_pages={dead} / total_pages={pages} ratio {ratio} within "
                f"tightened cap.{poison} Finding: STALE_STATISTICS."
            )
        else:
            bits = [
                f"computes dead_pages={dead} / total_pages={pages} (ratio {ratio}) over computed "
                f"{g['size_class']} after compute"
            ]
            if stale_days >= STALE_MIN_DAYS:
                eff = "0.10" if g["size_class"] == "large" else "0.35"
                bits.append(f"{stale_days}d stale under amendment so cap {eff} and {ratio} exceeds it")
            if g["_size_export"].lower() == "medium":
                bits.append("export medium ignored")
            if g["_maint"].lower() == "true":
                if tid not in reidx:
                    bits.append("unapproved reindex (missing row)")
                elif reidx[tid]["approved"].lower() == "false":
                    bits.append("unapproved reindex")
                elif date.fromisoformat(reidx[tid]["valid_until"]) <= AUDIT:
                    bits.append(
                        f"reindex valid_until={reidx[tid]['valid_until']} not strictly after "
                        f"2026-09-01 so expired/not exempt"
                    )
            dens.append(
                f"- **{tid}**: {tid} " + "; ".join(bits) + f".{poison} Finding: BLOAT_THRESHOLD_EXCEEDED."
            )

    dens += [
        "",
        "## Cap-equality compliance",
        "",
        "Ratios exactly equal to the effective cap are not over the cap.",
        "",
        "## Dashboard decoy",
        "",
        "`dashboard_suggested_findings.csv` is non-authoritative.",
        "",
    ]
    memo_path.write_text("\n".join(header) + "\n" + old_body.lstrip() + "\n".join(dens), encoding="utf-8", newline="\n")

    instr = instr_path.read_text(encoding="utf-8")
    instr = re.sub(r"\n10\..*", "\n", instr, flags=re.S)
    instr = re.sub(r"\n11\..*", "\n", instr, flags=re.S)
    instr = re.sub(
        r"5\..*?\n",
        "5. Reindex exempts a table from the bloat check only if `maintenance_active` AND "
        "`approved=True` AND the approval is still valid on the issued audit date — "
        "**see `input/policy_amendment_2026-08-20.md` for the exact validity comparison "
        "used in this audit.**\n",
        instr,
        count=1,
    )
    instr = instr.rstrip() + (
        "\n\n10. Ignore `input/dashboard_suggested_findings.csv` — non-authoritative.\n"
        "11. Apply `input/policy_amendment_2026-08-20.md` for this audit (including which "
        "calendar date anchors staleness/reindex checks when the export `audit_date` column "
        "disagrees). Memo local units must cite each non-`none` table's own `dead_pages` and "
        "`total_pages` digit forms.\n"
    )
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    sol_in = PACK / "solution" / "files" / "input"
    if sol_in.is_dir():
        for src_f in (PACK / "environment" / "input").iterdir():
            if src_f.is_file():
                try:
                    shutil.copy2(src_f, sol_in / src_f.name)
                except PermissionError:
                    pass

    golden = PACK / "solution" / "golden_results.json"
    if golden.is_file():
        golden.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n")

    print("v11 harden complete")


if __name__ == "__main__":
    main()

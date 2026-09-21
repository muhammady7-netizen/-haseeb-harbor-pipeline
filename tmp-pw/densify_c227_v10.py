"""c227 v10 — case-sensitive vacuum_type=manual + large stale tighten 0.10.

Fair disclosures live in policy amendment. Agents that .lower() vacuum_type or
keep 0.05 tighten after reading only the >=30 clause should drop below 1.0.
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
AUDIT = date(2026, 9, 1)
STALE_MIN_DAYS = 30
LARGE_STALE_TIGHTEN = 0.10  # amendment: large only
SMALL_STALE_TIGHTEN = 0.05  # unchanged


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
        "audit_date": AUDIT.isoformat(),
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
    # v10: vacuum_type exact lowercase 'manual' only (case-sensitive)
    vac_off = r["autovacuum_enabled"].lower() == "false" or r["vacuum_type"] == "manual"
    la = date.fromisoformat(r["last_analyzed"])
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
            if rr["approved"].lower() == "true" and date.fromisoformat(rr["valid_until"]) >= AUDIT:
                exempt = True
        if (not exempt) and ratio > cap + 1e-12:
            finding = "BLOAT_THRESHOLD_EXCEEDED"
        elif stale:
            finding = "STALE_STATISTICS"
    return finding, size, ratio, stale, stale_days


AMENDMENT = """# Policy amendment DBOPS-31-A — issued 2026-08-20

Effective for the September 2026 maintenance audit (`audit_date` **2026-09-01**),
this amendment **supersedes** selected clauses of `maintenance_policy.md` as stated
below. Unlisted clauses stay in force.

## 1. Exact-30-day staleness boundary (supersedes §3)

Statistics are stale when `(audit_date - last_analyzed).days >= 30`
(thirty calendar days **or more**). Exactly 30 days **is** stale for this audit.

## 2. Large-table stale cap tightening (supersedes §3 tightening amount for large)

When statistics are stale:
- **large** tables (`total_pages >= 500`): reduce the bloat cap by **0.10**
  (effective large stale cap **0.10**, not 0.15).
- **small** tables (`total_pages < 500`): keep the baseline reduction of **0.05**
  (effective small stale cap **0.35**).

Apply tightening **before** the bloat comparison. Finding precedence remains
autovacuum → bloat → stale.

## 3. Manual vacuum override is case-sensitive (clarifies §1)

The manual-vacuum override applies only when `vacuum_type` equals exactly
`manual` (all lowercase). Values such as `Manual`, `MANUAL`, or `Manual `
do **not** trigger `AUTOVACUUM_DISABLED` under this amendment. (This differs from
size-class label matching, which remains case-insensitive.)

## 4. Reindex log duplicates

If `reindex_log.csv` contains more than one row for the same `table_name`, the
**last** occurrence is authoritative.

## Unchanged

Round-half-up from `dead_pages` / `total_pages`, size class from `total_pages`
only, reindex exemption (`maintenance_active` + `approved=True` +
`valid_until >= audit_date`), ignore `days_since_analyze` / export `size_class` /
`dashboard_suggested_findings.csv`, and sort by `last_analyzed` then `table_name`.
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
    policy_path = PACK / "environment" / "input" / "maintenance_policy.md"

    amend_path.write_text(AMENDMENT, encoding="utf-8", newline="\n")

    health = list(csv.DictReader(health_path.open(encoding="utf-8-sig")))
    fields = list(health[0].keys())
    health = [r for r in health if int(r["table_name"].split("-")[1]) <= 108]

    # Force T-93 to case-variant Manual (already is); add more case traps
    for r in health:
        if r["table_name"] == "T-93":
            r["vacuum_type"] = "Manual"
            r["dead_pages"] = "10"
            r["total_pages"] = "1000"

    new_rows = [
        row("T-109", pages=1000, dead=20, vac="MANUAL", la_days=5),  # case → not override
        row("T-110", pages=1000, dead=20, vac="manual", la_days=5),  # exact → AUTOVACUUM
        row("T-111", pages=1000, dead=20, vac="Manual ", la_days=6),  # trailing space → not
        row("T-112", pages=1000, dead=120, la_days=40, days_field=2),  # large stale 0.12 > 0.10 BLOAT
        row("T-113", pages=1000, dead=100, la_days=40, days_field=2),  # 0.10 = tight → STALE
        row("T-114", pages=1000, dead=95, la_days=40, days_field=1),  # 0.10? 0.095→0.10 =tight STALE
        row("T-115", pages=1000, dead=105, la_days=35, days_field=3, bloat_export="0.1"),  # 0.105→0.11 BLOAT
        row("T-116", pages=400, dead=148, size_export="large", la_days=40, days_field=1),  # small 0.37 > 0.35 BLOAT
        row("T-117", pages=400, dead=140, size_export="large", la_days=40, days_field=1),  # 0.35 =tight STALE
    ]
    # avoid dup ids on re-run
    health = [r for r in health if int(r["table_name"].split("-")[1]) <= 108]
    health = health + new_rows

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(health)
    health_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    reindex = list(csv.DictReader(reindex_path.open(encoding="utf-8-sig")))
    rfields = list(reindex[0].keys())
    # keep through T-106 densify reindex rows
    seen = []
    out_re = []
    for r in reindex:
        key = (r["table_name"], r["approved"], r["valid_until"])
        if key in seen:
            continue
        seen.append(key)
        out_re.append(r)
    reindex = out_re
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

    decoy = []
    for tid in by_last:
        decoy.append({
            "table_name": tid,
            "suggested_finding": "none" if tid[-1] in "02468" else "BLOAT_THRESHOLD_EXCEEDED",
            "note": "health-dashboard heuristic — not authoritative",
        })
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
            "_amend_boundary": stale_days == 30,
            "_case_vac": r["vacuum_type"] != "manual" and r["vacuum_type"].lower() == "manual",
        })
    gold_rows.sort(key=lambda g: (g["_la"], g["table_name"]))

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
    for g in gold_rows:
        num = int(g["table_name"].split("-")[1])
        if num >= 93 or g["_amend_boundary"] or g["_stale_days"] >= 30 and num >= 50:
            if num >= 93 or g["_case_vac"] or num in {9, 63, 64, 97, 98, 99, 100, 112, 113, 114, 115}:
                print("EDGE", g["table_name"], "vac=", repr(g["_vac"]), g["bloat_ratio"], g["finding"], "days", g["_stale_days"])

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

    # Patch instruction rule 2 to NOT claim case-insensitive for manual — point to amendment
    # Rebuild MEMO_V10
    memo_map = {}
    for g in gold_rows:
        tid = g["table_name"]
        if g["finding"] == "none":
            continue
        num = int(tid.split("-")[1])
        concepts = [g["finding"], str(g["_dead"]), str(g["_pages"])]
        if g["_amend_boundary"] or (g["_stale_days"] >= STALE_MIN_DAYS and g["size_class"] == "large"):
            concepts += ["amendment", "0.10"]
        if g["_stale_days"] == 30:
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
                elif date.fromisoformat(reidx[tid]["valid_until"]) < AUDIT:
                    concepts += ["expired", "reindex"]
        elif g["finding"] == "STALE_STATISTICS":
            concepts += [str(g["_stale_days"]), "stale", "days_since_analyze"]
        else:
            if g["_vac"] == "manual":
                concepts += ["manual", "vacuum", "override"]
            else:
                concepts += ["autovacuum", "disabled"]
        if num >= 46 or g["_amend_boundary"] or num in {9}:
            memo_map[tid] = concepts

    src = re.sub(r"\nMEMO_V8_STRICT = \{.*?\n\}\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\nMEMO_V9_STRICT = \{.*?\n\}\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\nMEMO_V10_STRICT = \{.*?\n\}\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\n@pytest.mark.parametrize\(\"table_id\", sorted\(MEMO_V8_STRICT.*?\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\n@pytest.mark.parametrize\(\"table_id\", sorted\(MEMO_V9_STRICT.*?\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_memo_v8_strict_local_evidence\(.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_memo_v9_strict_local_evidence\(.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_memo_v10_strict_local_evidence\(.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_ignores_dashboard_suggested_findings\(\):.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_applies_policy_amendment_boundary\(\):.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_vacuum_type_case_sensitive_manual\(\):.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)

    # Fix orphan decorators before dict if any
    src = re.sub(
        r"\n@pytest.mark.parametrize\(\"table_id\", sorted\(MEMO_V\d+_STRICT\.keys\(\).*?\)\)\n+",
        "\n",
        src,
        flags=re.S,
    )

    embed = "MEMO_V10_STRICT = " + json.dumps(memo_map, indent=4) + "\n"
    block = f'''
{embed}

@pytest.mark.parametrize("table_id", sorted(MEMO_V10_STRICT.keys(), key=lambda t: (len(t), t)))
def test_memo_v10_strict_local_evidence(table_id):
    """Densify / amendment non-none tables need local memo evidence incl. dead/total pages."""
    concepts = MEMO_V10_STRICT[table_id]
    assert _memo_mentions(table_id, *concepts), (
        f"Memo must explain {{table_id}} with local evidence {{concepts}}"
    )


def test_ignores_dashboard_suggested_findings():
    """Audit findings must not copy dashboard_suggested_findings.csv (policy wins)."""
    import csv as _csv
    dash = WORKSPACE / "input" / "dashboard_suggested_findings.csv"
    if not dash.is_file():
        dash = Path("/app/input/dashboard_suggested_findings.csv")
    assert dash.is_file(), "dashboard_suggested_findings.csv missing from input"
    suggested = {{r["table_name"]: r["suggested_finding"] for r in _csv.DictReader(dash.open(encoding="utf-8-sig"))}}
    rows, err = _load_csv()
    assert err is None, err
    mismatches = sum(1 for r in rows if suggested.get(r["table_name"]) != r["finding"])
    assert mismatches >= 10, f"Expected audit to diverge from dashboard decoy on >=10 tables, got {{mismatches}}"


def test_applies_policy_amendment_boundary():
    """Amendment: >=30 stale, large tighten 0.10, case-sensitive manual."""
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    assert by["T-09"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-63"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-93"]["finding"] == "none"  # Manual != manual
    assert by["T-109"]["finding"] == "none"  # MANUAL != manual
    assert by["T-110"]["finding"] == "AUTOVACUUM_DISABLED"  # exact manual
    assert by["T-112"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"  # 0.12 > 0.10
    assert by["T-113"]["finding"] == "STALE_STATISTICS"  # 0.10 == tight
    assert by["T-105"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-106"]["finding"] == "none"


def test_vacuum_type_case_sensitive_manual():
    """Only lowercase vacuum_type=manual disables; Manual/MANUAL do not."""
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    assert by["T-93"]["finding"] == "none"
    assert by["T-110"]["finding"] == "AUTOVACUUM_DISABLED"
'''
    src = src.rstrip() + "\n" + block
    tests_path.write_text(src, encoding="utf-8", newline="\n")

    # Memo rebuild
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
        f"{len(gold_rows)} unique tables against DBOPS-31 + amendment DBOPS-31-A "
        f"({len(health)} input rows after last-row collapse). {len(compliant)} compliant, "
        f"{len(flagged)} flagged. Large stale tighten is 0.10; vacuum_type manual is "
        f"case-sensitive lowercase only.",
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
        "Apply `policy_amendment_2026-08-20.md`: >=30 days stale; large stale cap "
        "tightens by 0.10 (effective 0.10); only lowercase `manual` triggers the "
        "autovacuum override; reindex_log last-row wins.",
        "",
        "## Densify traps (T-46+ / amendment edges)",
        "",
    ]
    for g in flagged:
        tid = g["table_name"]
        num = int(tid.split("-")[1])
        if num < 46 and not g["_amend_boundary"]:
            continue
        dead, pages, ratio, finding = g["_dead"], g["_pages"], g["bloat_ratio"], g["finding"]
        stale_days = g["_stale_days"]
        amend_bits = []
        if g["_amend_boundary"] or stale_days >= STALE_MIN_DAYS:
            amend_bits.append(
                f"amendment DBOPS-31-A treats a {stale_days}-day gap as stale (>= 30) and "
                f"for large tables tightens by 0.10 (effective cap 0.10)"
            )
        if finding == "AUTOVACUUM_DISABLED":
            dens.append(
                f"- **{tid}**: {tid} has vacuum_type={g['_vac']!r} and autovacuum_enabled={g['_auto']} "
                f"on total_pages={pages} with dead_pages={dead}; exact lowercase manual/autovacuum "
                f"disabled is checked first. Finding: AUTOVACUUM_DISABLED."
            )
        elif finding == "STALE_STATISTICS":
            dens.append(
                f"- **{tid}**: {tid} is {stale_days} days stale by audit_date minus last_analyzed "
                f"(ignore days_since_analyze={g['_days_field']}); dead_pages={dead} / total_pages={pages} "
                f"computes ratio {ratio} within the tightened cap so bloat does not fire. "
                + (" ".join(amend_bits) + ". " if amend_bits else "")
                + "Finding: STALE_STATISTICS."
            )
        else:
            bits = [
                f"{tid} computes from dead_pages={dead} and total_pages={pages} "
                f"(round-half-up ratio {ratio}) over its computed {g['size_class']} cap after compute"
            ]
            if stale_days >= STALE_MIN_DAYS:
                eff = "0.10" if g["size_class"] == "large" else "0.35"
                bits.append(
                    f"statistics are {stale_days} days stale so the cap tightens to {eff} and "
                    f"{ratio} exceeds the tightened effective cap"
                )
            if g["_size_export"].lower() == "medium":
                bits.append(f"export size_class medium is ignored because total_pages={pages} computes {g['size_class']}")
            if g["_maint"].lower() == "true":
                if tid not in reidx:
                    bits.append("maintenance_active but no approved reindex row so unapproved for exemption")
                elif reidx[tid]["approved"].lower() == "false":
                    bits.append("reindex is unapproved (approved=False) so not exempt")
                elif date.fromisoformat(reidx[tid]["valid_until"]) < AUDIT:
                    bits.append(
                        "approved reindex is expired before audit_date so not exempt "
                        "(reindex_log last-row wins when duplicates exist)"
                    )
            dens.append(
                f"- **{tid}**: " + "; ".join(bits)
                + ("; " + "; ".join(amend_bits) if amend_bits else "")
                + ". Finding: BLOAT_THRESHOLD_EXCEEDED."
            )

    dens += [
        "",
        "## Cap-equality compliance",
        "",
        "Ratios exactly equal to the effective (possibly tightened) cap are not over the cap.",
        "",
        "## Dashboard decoy",
        "",
        "`dashboard_suggested_findings.csv` is non-authoritative; DBOPS-31 + amendment decide every finding.",
        "",
    ]
    memo_path.write_text("\n".join(header) + "\n" + old_body.lstrip() + "\n".join(dens), encoding="utf-8", newline="\n")

    # Instruction: do not explain amendment details; keep baseline pointers
    instr = instr_path.read_text(encoding="utf-8")
    instr = re.sub(r"\n10\..*", "\n", instr, flags=re.S)
    instr = re.sub(r"\n11\..*", "\n", instr, flags=re.S)
    instr = re.sub(r"\n12\..*", "\n", instr, flags=re.S)
    instr = re.sub(
        r"2\..*?\n",
        "2. If `vacuum_type=manual`, the finding is `AUTOVACUUM_DISABLED` even when "
        "`autovacuum_enabled=True`. **Matching details may be clarified or narrowed by "
        "`input/policy_amendment_2026-08-20.md` — apply that amendment for this audit.**\n",
        instr,
        count=1,
    )
    instr = re.sub(
        r"3\..*?\n",
        "3. Baseline in `maintenance_policy.md`: statistics are stale if "
        "`(audit_date - last_analyzed).days > 30`. Ignore the export `days_since_analyze` "
        "field. **Apply `input/policy_amendment_2026-08-20.md` where it supersedes "
        "staleness or tightening for this audit.**\n",
        instr,
        count=1,
    )
    instr = re.sub(
        r"4\..*?\n",
        "4. When stats are stale, tighten the bloat cap before comparing (baseline policy "
        "reduces by 0.05). Finding precedence: autovacuum → bloat → stale. **Use the "
        "amendment's tightening amounts when they supersede the baseline.**\n",
        instr,
        count=1,
    )
    instr = instr.rstrip() + (
        "\n\n10. Ignore `input/dashboard_suggested_findings.csv` — non-authoritative dashboard "
        "heuristic; policy wins when it disagrees.\n"
        "11. Read and apply `input/policy_amendment_2026-08-20.md` for this audit wherever it "
        "supersedes DBOPS-31. For every non-`none` finding, the memo local unit must cite that "
        "table's own `dead_pages` and `total_pages` digit forms.\n"
    )
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    pol = policy_path.read_text(encoding="utf-8")
    if "policy_amendment_2026-08-20" not in pol:
        pol = pol.rstrip() + (
            "\n\n## 6. Amendments\n\n"
            "When an issued amendment file in `input/` states that it supersedes a section of "
            "this policy for a named audit, apply the amendment for that audit.\n"
        )
        policy_path.write_text(pol, encoding="utf-8", newline="\n")

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

    # Fix test file if orphan decorator left before MEMO dict
    src2 = tests_path.read_text(encoding="utf-8")
    src2 = re.sub(
        r"(def test_memo_explains_t45\(\):.*?),\s*\"Memo must explain T-45[^\"]*\"\n\n+"
        r"(@pytest\.mark\.parametrize\([^\n]+\n+)+",
        r"\1, \"Memo must explain T-45 stale-tighten densify trap\"\n\n\n",
        src2,
        count=1,
        flags=re.S,
    )
    # simpler: remove any parametrize immediately before MEMO_V10
    src2 = re.sub(
        r"(@pytest\.mark\.parametrize\(\"table_id\", sorted\(MEMO_V\d+_STRICT[^)]*\)\)\s*)+\n(?=MEMO_V10_STRICT)",
        "",
        src2,
    )
    tests_path.write_text(src2, encoding="utf-8", newline="\n")

    print("v10 harden complete")


if __name__ == "__main__":
    main()

"""c227 v9 — disclosed policy amendment (≥30 stale) + reindex last-wins.

Fair: amendment is in input/ and pointed from instruction. Agents that only
code instruction rule 3's baseline `> 30` keep T-09/T-63 compliant and fail.
Oracle stays file-copy 1.0 after gold rebuild.
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
# Amendment: stale when days >= 30 (supersedes baseline > 30)
STALE_MIN_DAYS = 30


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
    vac_off = r["autovacuum_enabled"].lower() == "false" or r["vacuum_type"].lower() == "manual"
    la = date.fromisoformat(r["last_analyzed"])
    stale_days = (AUDIT - la).days
    # v9 amendment: >= 30 is stale (baseline policy was > 30)
    stale = stale_days >= STALE_MIN_DAYS
    if stale:
        cap = rhu(cap - 0.05, 2)
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
this amendment **supersedes** §3 of `maintenance_policy.md` on the exact-30-day
staleness boundary only.

## Superseding rule

Statistics are stale when `(audit_date - last_analyzed).days >= 30`
(thirty calendar days **or more**). A difference of **exactly 30 days is stale**
under this amendment (the baseline policy text that says exactly 30 days is NOT
stale does **not** apply to this audit).

When this amendment makes a table stale, apply the usual **0.05 cap tightening**
before the bloat comparison, and keep the usual finding precedence
(autovacuum → bloat → stale).

## Reindex log duplicates

If `reindex_log.csv` contains more than one row for the same `table_name`, the
**last** occurrence is authoritative (same last-row rule as the health export).

## Unchanged

All other DBOPS-31 rules remain in force: autovacuum / manual override first,
round-half-up from `dead_pages` / `total_pages`, size class from `total_pages`
only, reindex exemption requires `maintenance_active` AND `approved=True` AND
`valid_until >= audit_date`, ignore `days_since_analyze` and export `size_class`,
ignore `dashboard_suggested_findings.csv`, and sort output by `last_analyzed`
then `table_name`.
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
    # Drop prior v9 extras if re-run; keep through T-96 densify matrix
    health = [
        r for r in health
        if int(r["table_name"].split("-")[1]) <= 96
    ]

    new_rows = [
        # Exactly-30 amendment edges (large)
        row("T-97", pages=1000, dead=140, la_days=30, days_field=7, bloat_export="0.14"),  # STALE under tight 0.15
        row("T-98", pages=1000, dead=150, la_days=30, days_field=2, bloat_export="0.15"),  # =tight → STALE
        row("T-99", pages=1000, dead=160, la_days=30, days_field=9, bloat_export="0.16"),  # BLOAT over tight
        row("T-100", pages=1000, dead=190, la_days=30, days_field=1, bloat_export="0.19"),  # BLOAT (like T-09)
        # Exactly-30 small
        row("T-101", pages=400, dead=140, size_export="large", la_days=30, days_field=0),  # 0.35 = tight 0.35 → STALE
        row("T-102", pages=400, dead=144, size_export="medium", la_days=30, days_field=3, bloat_export="0.36"),  # BLOAT
        # Lying days field at exactly 30
        row("T-103", pages=1000, dead=100, la_days=30, days_field=5),  # STALE
        row("T-104", pages=1000, dead=100, la_days=29, days_field=40),  # fresh (29) despite lying → none
        # Reindex last-wins (T-105): first row would exempt, last expires
        row("T-105", pages=1000, dead=300, maint="True", la_days=8),
        # Reindex last-wins (T-106): first expired, last approved → none
        row("T-106", pages=1000, dead=320, maint="True", la_days=9),
        # More RHU .x5 under amendment-irrelevant fresh
        row("T-107", pages=1000, dead=275, la_days=6, bloat_export="0.28"),  # 0.275→0.28
        row("T-108", pages=499, dead=207, size_export="large", la_days=11, bloat_export="0.41"),  # 207/499≈0.4148→0.41
    ]
    health = health + new_rows
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(health)
    health_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    reindex = list(csv.DictReader(reindex_path.open(encoding="utf-8-sig")))
    rfields = list(reindex[0].keys())
    # Keep baseline densify reindex rows (T<=70) and strip prior v9 extras
    reindex = [r for r in reindex if int(r["table_name"].split("-")[1]) <= 70]
    # Duplicate last-wins matrix
    reindex += [
        {"table_name": "T-105", "approved": "True", "valid_until": "2026-09-15"},  # would exempt
        {"table_name": "T-105", "approved": "True", "valid_until": "2026-08-31"},  # last → expired
        {"table_name": "T-106", "approved": "True", "valid_until": "2026-08-20"},  # expired first
        {"table_name": "T-106", "approved": "True", "valid_until": "2026-09-20"},  # last → exempt
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rfields, lineterminator="\n")
    w.writeheader()
    w.writerows(reindex)
    reindex_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    by_last: dict[str, dict] = {}
    for r in health:
        by_last[r["table_name"]] = r
    # Last-wins for reindex
    reidx: dict[str, dict] = {}
    for r in reindex:
        reidx[r["table_name"]] = r

    # Dashboard decoy
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
        if g["_stale_days"] == 30 or int(g["table_name"].split("-")[1]) >= 97:
            print("EDGE", g["table_name"], g["bloat_ratio"], g["finding"], "days", g["_stale_days"])

    # Patch EXPECTED in tests
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
    assert n == 1, "EXPECTED_TABLES patch failed"
    res_body = "EXPECTED_RESULTS = {\n" + "".join(f'    "{k}": {v},\n' for k, v in results.items()) + "}"
    src, n = re.subn(r"EXPECTED_RESULTS = \{.*?\n\}", res_body, src, count=1, flags=re.S)
    assert n == 1, "EXPECTED_RESULTS patch failed"
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
    assert n == 1, "row count patch failed"

    # Rebuild MEMO_V9_STRICT (replace V8)
    memo_map = {}
    for g in gold_rows:
        tid = g["table_name"]
        if g["finding"] == "none":
            continue
        num = int(tid.split("-")[1])
        concepts = [g["finding"], str(g["_dead"]), str(g["_pages"])]
        if g["_amend_boundary"] or num >= 97:
            concepts += ["amendment", "30"]
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
            if g["_vac"].lower() == "manual":
                concepts += ["manual", "vacuum", "override"]
            else:
                concepts += ["autovacuum", "disabled"]
        # Keep densify memo gates for T-46+ and amendment edges (incl T-09)
        if num >= 46 or g["_amend_boundary"]:
            memo_map[tid] = concepts

    # Strip old V8 blocks
    src = re.sub(r"\nMEMO_V8_STRICT = \{.*?\n\}\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\nMEMO_V9_STRICT = \{.*?\n\}\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_memo_v8_strict_local_evidence\(.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_memo_v9_strict_local_evidence\(.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_ignores_dashboard_suggested_findings\(\):.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_applies_policy_amendment_boundary\(\):.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)

    embed = "MEMO_V9_STRICT = " + json.dumps(memo_map, indent=4) + "\n"
    block = f'''
{embed}

@pytest.mark.parametrize("table_id", sorted(MEMO_V9_STRICT.keys(), key=lambda t: (len(t), t)))
def test_memo_v9_strict_local_evidence(table_id):
    """Densify / amendment non-none tables need local memo evidence incl. dead/total pages."""
    concepts = MEMO_V9_STRICT[table_id]
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
    """Exactly-30-day tables must follow amendment (>=30 stale), not baseline >30."""
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    # T-09 / T-63 flip from baseline-none to bloat under amendment tightening
    assert by["T-09"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-63"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"
    assert by["T-97"]["finding"] == "STALE_STATISTICS"
    assert by["T-98"]["finding"] == "STALE_STATISTICS"
    assert by["T-104"]["finding"] == "none"  # 29 days still fresh
    assert by["T-105"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"  # reindex last-wins expired
    assert by["T-106"]["finding"] == "none"  # reindex last-wins exempt
'''
    src = src.rstrip() + "\n" + block
    tests_path.write_text(src, encoding="utf-8", newline="\n")

    # Gold memo
    old_memo = memo_path.read_text(encoding="utf-8")
    old_body = re.sub(r"(?s)^# Table maintenance audit.*?\n## ", "## ", old_memo, count=1)
    if old_body.startswith("#"):
        parts = old_memo.split("\n## ", 1)
        old_body = ("## " + parts[1]) if len(parts) == 2 else old_memo
    old_body = re.sub(r"\n## Densify traps.*", "\n", old_body, count=1, flags=re.S)
    old_body = re.sub(r"\n## Cap-equality compliance\n.*", "\n", old_body, count=1, flags=re.S)
    old_body = re.sub(r"\n## Dashboard decoy\n.*", "\n", old_body, count=1, flags=re.S)
    old_body = re.sub(r"\n## Policy amendment.*", "\n", old_body, count=1, flags=re.S)
    for i in range(46, 120):
        old_body = re.sub(rf"\n- \*\*T-{i}\*\*:.*?(?=\n- \*\*|\n## |\Z)", "\n", old_body, flags=re.S)
    # Drop old T-09 none-style bullets if present; rewritten below when flagged
    old_body = re.sub(r"\n- \*\*T-09\*\*:.*?(?=\n- \*\*|\n## |\Z)", "\n", old_body, flags=re.S)

    flagged = [g for g in gold_rows if g["finding"] != "none"]
    compliant = [g for g in gold_rows if g["finding"] == "none"]
    header = [
        f"# Table maintenance audit — {len(gold_rows)} unique tables",
        "",
        f"{len(gold_rows)} unique tables against DBOPS-31 + amendment DBOPS-31-A "
        f"({len(health)} input rows after last-row collapse). {len(compliant)} compliant, "
        f"{len(flagged)} flagged. Ignore dashboard_suggested_findings.csv — policy decides. "
        f"Exactly-30-day staleness follows the amendment (>= 30), not the baseline > 30 text.",
        "",
        "| Table | Size class | Bloat ratio | Finding |",
        "|---|---|---|---|",
    ]
    for g in gold_rows:
        header.append(f"| {g['table_name']} | {g['size_class']} | {g['bloat_ratio']} | {g['finding']} |")
    header.append("")

    dens = ["", "## Policy amendment DBOPS-31-A", ""]
    dens.append(
        "Under `policy_amendment_2026-08-20.md`, a 30-day gap is stale; cap tightening "
        "applies before bloat. Reindex_log duplicates use last-row authority."
    )
    dens.append("")
    dens += ["## Densify traps (T-46+ / amendment edges)", ""]
    for g in flagged:
        tid = g["table_name"]
        num = int(tid.split("-")[1])
        if num < 46 and not g["_amend_boundary"]:
            continue
        dead, pages, ratio, finding = g["_dead"], g["_pages"], g["bloat_ratio"], g["finding"]
        stale_days = g["_stale_days"]
        amend_note = ""
        if g["_amend_boundary"] or num >= 97:
            amend_note = (
                f" Amendment DBOPS-31-A treats the {stale_days}-day gap (exactly 30 where "
                f"applicable) as stale (>= 30), superseding the baseline > 30 rule."
            )
        if finding == "AUTOVACUUM_DISABLED":
            dens.append(
                f"- **{tid}**: {tid} has vacuum_type={g['_vac']} and autovacuum_enabled={g['_auto']} "
                f"on total_pages={pages} with dead_pages={dead}; the autovacuum/manual rule is checked "
                f"first and overrides later bloat review. Finding: AUTOVACUUM_DISABLED."
            )
        elif finding == "STALE_STATISTICS":
            dens.append(
                f"- **{tid}**: {tid} is {stale_days} days stale by audit_date minus last_analyzed "
                f"(ignore days_since_analyze={g['_days_field']}); dead_pages={dead} / total_pages={pages} "
                f"computes ratio {ratio} within the tightened cap so bloat does not fire."
                f"{amend_note} Finding: STALE_STATISTICS."
            )
        else:
            bits = [
                f"{tid} computes from dead_pages={dead} and total_pages={pages} "
                f"(round-half-up ratio {ratio}) over its computed {g['size_class']} cap after compute"
            ]
            if stale_days >= STALE_MIN_DAYS:
                bits.append(
                    f"statistics are {stale_days} days stale so the cap tightens and {ratio} exceeds "
                    f"the tightened effective cap"
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
            dens.append(f"- **{tid}**: " + "; ".join(bits) + f".{amend_note} Finding: BLOAT_THRESHOLD_EXCEEDED.")

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

    # Instruction: keep baseline rule 3 text, point at amendment; drop v8 laundry list
    instr = instr_path.read_text(encoding="utf-8")
    instr = re.sub(r"\n10\..*", "\n", instr, flags=re.S)
    instr = re.sub(r"\n11\..*", "\n", instr, flags=re.S)
    instr = re.sub(r"\n12\..*", "\n", instr, flags=re.S)
    # Ensure rule 3 still states baseline >30 (trap bait) — rewrite if already amended
    instr = re.sub(
        r"3\..*?\n",
        "3. Baseline in `maintenance_policy.md`: statistics are stale if "
        "`(audit_date - last_analyzed).days > 30`. Ignore the export `days_since_analyze` "
        "field. **If `input/policy_amendment_2026-08-20.md` supersedes that boundary for "
        "this audit, apply the amendment.**\n",
        instr,
        count=1,
    )
    instr = instr.rstrip() + (
        "\n\n10. Ignore `input/dashboard_suggested_findings.csv` — non-authoritative dashboard "
        "heuristic; policy wins when it disagrees.\n"
        "11. Apply `input/policy_amendment_2026-08-20.md` for this audit. It supersedes the "
        "exact-30-day staleness boundary in DBOPS-31 §3 and states that duplicate "
        "`reindex_log.csv` rows use last-row authority. For every non-`none` finding, the "
        "memo local unit must cite that table's own `dead_pages` and `total_pages` digit forms.\n"
    )
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    pol = policy_path.read_text(encoding="utf-8")
    if "policy_amendment_2026-08-20" not in pol:
        pol = pol.rstrip() + (
            "\n\n## 6. Amendments\n\n"
            "When an issued amendment file in `input/` (for example "
            "`policy_amendment_2026-08-20.md`) states that it supersedes a section of this "
            "policy for a named audit, apply the amendment for that audit.\n"
        )
        policy_path.write_text(pol, encoding="utf-8", newline="\n")

    # Mirror inputs into solution/files/input if present
    sol_in = PACK / "solution" / "files" / "input"
    if sol_in.is_dir():
        for src_f in (PACK / "environment" / "input").iterdir():
            if src_f.is_file():
                shutil.copy2(src_f, sol_in / src_f.name)

    # Sync golden_results.json if used
    golden = PACK / "solution" / "golden_results.json"
    if golden.is_file():
        golden.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n")

    print("v9 amendment harden complete")


if __name__ == "__main__":
    main()

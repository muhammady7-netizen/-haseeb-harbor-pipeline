"""c227 v8 FULL fair harden — exhaust every disclosed edge; strict memo for all flags.

No hidden rules. Oracle must stay 1.0. Target local GLM ~0/4 before portal.
"""
from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\tmp-pw\c227-fix-accepted\code-c227-table-bloat-maintenance-audit"
)
AUDIT = date(2026, 9, 1)


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
    stale = stale_days > 30
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


def main() -> None:
    health_path = PACK / "environment" / "input" / "table_health.csv"
    reindex_path = PACK / "environment" / "input" / "reindex_log.csv"
    dash_path = PACK / "environment" / "input" / "dashboard_suggested_findings.csv"
    gold_path = PACK / "solution" / "files" / "bloat_audit.csv"
    results_path = PACK / "solution" / "files" / "results.json"
    memo_path = PACK / "solution" / "files" / "bloat_memo.md"
    tests_path = PACK / "tests" / "test_outputs.py"
    instr_path = PACK / "instruction.md"
    policy_path = PACK / "environment" / "input" / "maintenance_policy.md"

    health = list(csv.DictReader(health_path.open(encoding="utf-8-sig")))
    fields = list(health[0].keys())
    # Keep baseline T-01..T-45; rebuild densify from scratch
    keep = {f"T-{i:02d}" for i in range(1, 46)} | {f"T-{i}" for i in range(1, 46)}
    # normalize: existing uses T-01 style
    health = [r for r in health if r["table_name"] in keep or (
        r["table_name"].startswith("T-") and int(r["table_name"].split("-")[1]) <= 45
    )]
    # also keep duplicate baselines T-31/T-32 if present as duplicates
    base = [r for r in list(csv.DictReader(health_path.open(encoding="utf-8-sig")))
            if int(r["table_name"].split("-")[1]) <= 45]
    health = base

    new_rows: list[dict] = []
    # === FULL disclosed trap matrix (T-46+) ===
    new_rows += [
        # Round-half-up ≠ banker's, crosses large cap
        row("T-46", pages=1000, dead=205, la_days=7, bloat_export="0.2"),  # 0.205→0.21
        row("T-47", pages=1000, dead=225, la_days=6, bloat_export="0.22"),  # 0.225→0.23
        row("T-48", pages=1000, dead=215, la_days=5, bloat_export="0.22"),  # 0.215→0.22
        row("T-49", pages=1000, dead=405, size_export="small", la_days=8, bloat_export="0.4"),
        # Stale + RHU over tightened 0.15
        row("T-50", pages=1000, dead=155, la_days=33, days_field=10, bloat_export="0.16"),
        row("T-51", pages=1000, dead=165, la_days=36, days_field=3, bloat_export="0.16"),
        row("T-52", pages=1000, dead=205, la_days=34, days_field=2, bloat_export="0.2"),
        # Stale under tightened → STALE only (RHU≠RHE at 0.145)
        row("T-53", pages=1000, dead=145, la_days=35, days_field=5, bloat_export="0.14"),
        row("T-54", pages=1000, dead=144, la_days=42, days_field=1),
        row("T-55", pages=1000, dead=150, la_days=38, days_field=4),  # 0.15 = tightened → STALE
        row("T-56", pages=1000, dead=125, la_days=40, days_field=2, bloat_export="0.12"),  # 0.125→0.13
        # Page-class boundaries
        row("T-57", pages=499, dead=205, size_export="large", la_days=11, bloat_export="0.41"),
        row("T-58", pages=500, dead=105, size_export="small", la_days=11, bloat_export="0.21"),
        row("T-59", pages=499, dead=199, size_export="Large", la_days=9),  # 199/499≈0.3988→0.40 =cap none
        row("T-60", pages=499, dead=200, size_export="LARGE", la_days=9, bloat_export="0.4"),  # 0.4008→0.40
        row("T-61", pages=499, dead=201, size_export="medium", la_days=9, bloat_export="0.4"),  # →0.40? 201/499≈0.4028→0.40
        row("T-62", pages=499, dead=203, size_export="medium", la_days=9, bloat_export="0.4"),  # 0.4068→0.41 BLOAT
        # Exactly 30 days NOT stale
        row("T-63", pages=1000, dead=180, la_days=30, days_field=99),  # none
        row("T-64", pages=1000, dead=210, la_days=30, days_field=0),  # 0.21 BLOAT fresh
        # Reindex matrix
        row("T-65", pages=1000, dead=350, maint="True", la_days=8),  # valid_until==audit exempt
        row("T-66", pages=1000, dead=280, maint="True", la_days=9),  # no reindex row → BLOAT
        row("T-67", pages=1000, dead=250, maint="True", la_days=5),  # unapproved
        row("T-68", pages=1000, dead=240, maint="True", la_days=6),  # expired
        row("T-69", pages=1000, dead=300, maint="True", la_days=7),  # approved future → none
        row("T-70", pages=1000, dead=260, maint="True", la_days=7),  # expired-1d
        # Manual / autovacuum precedence
        row("T-71", pages=1000, dead=50, vac="manual", la_days=4),
        row("T-72", pages=1000, dead=400, vac="manual", la_days=50, days_field=0),
        row("T-73", pages=600, dead=50, size_export="small", auto="False", la_days=3),
        row("T-74", pages=1000, dead=500, auto="False", vac="auto", la_days=20),  # auto off overrides bloat
        # Medium / small traps
        row("T-75", pages=800, dead=168, size_export="medium", la_days=8),
        row("T-76", pages=450, dead=185, size_export="medium", la_days=10, bloat_export="0.4"),
        row("T-77", pages=450, dead=180, size_export="medium", la_days=10),  # 0.4 =cap none
        row("T-78", pages=400, dead=164, size_export="large", la_days=9, bloat_export="0.4"),
        row("T-79", pages=399, dead=163, size_export="large", la_days=12, bloat_export="0.4"),
        row("T-80", pages=399, dead=159, size_export="large", la_days=12),  # 0.4 =cap none
        # Lying days_since_analyze
        row("T-81", pages=1000, dead=100, la_days=40, days_field=5),  # STALE
        row("T-82", pages=1000, dead=80, la_days=55, days_field=0),  # STALE
        row("T-83", pages=1000, dead=100, la_days=5, days_field=55),  # fresh despite lying → none
        # Duplicates last-wins
        row("T-84", pages=1000, dead=100, la_days=12),
        row("T-84", pages=1000, dead=220, la_days=12),  # BLOAT
        row("T-85", pages=1000, dead=50, la_days=14),
        row("T-85", pages=1000, dead=100, la_days=14),
        row("T-85", pages=1000, dead=230, la_days=14),  # triple last BLOAT
        row("T-86", pages=1000, dead=200, la_days=40, days_field=40),  # first would STALE/BLOAT
        row("T-86", pages=1000, dead=100, la_days=5, days_field=5),  # last none
        # Stale small-cap tighten 0.40→0.35
        row("T-87", pages=400, dead=144, size_export="large", la_days=40, days_field=1),  # 0.36 over 0.35
        row("T-88", pages=400, dead=140, size_export="large", la_days=40, days_field=1),  # 0.35 =tight → STALE
        row("T-89", pages=400, dead=136, size_export="medium", la_days=41, days_field=2),  # 0.34 under → STALE
        # More RHU .x5 over large
        row("T-90", pages=1000, dead=235, la_days=6, bloat_export="0.24"),
        row("T-91", pages=1000, dead=245, la_days=6, bloat_export="0.24"),  # 0.245→0.25
        row("T-92", pages=1000, dead=255, la_days=6, bloat_export="0.26"),  # 0.255→0.26
        # Case-insensitive vacuum_type Manual
        row("T-93", pages=1000, dead=10, vac="Manual", la_days=4),
        # Fresh at original large cap with export wrong size
        row("T-94", pages=1000, dead=200, size_export="small", la_days=8),  # 0.2 =cap none
        row("T-95", pages=1000, dead=201, size_export="small", la_days=8, bloat_export="0.2"),  # 0.201→0.20 none
        row("T-96", pages=1000, dead=205, size_export="small", la_days=8, bloat_export="0.2"),  # →0.21 BLOAT
    ]

    health = health + new_rows
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(health)
    health_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    # Reindex: keep baseline + densify matrix
    reindex = list(csv.DictReader(reindex_path.open(encoding="utf-8-sig")))
    rfields = list(reindex[0].keys())
    base_re = [r for r in reindex if int(r["table_name"].split("-")[1]) <= 45]
    base_re += [
        {"table_name": "T-65", "approved": "True", "valid_until": "2026-09-01"},
        {"table_name": "T-67", "approved": "False", "valid_until": "2026-09-15"},
        {"table_name": "T-68", "approved": "True", "valid_until": "2026-08-31"},
        {"table_name": "T-69", "approved": "True", "valid_until": "2026-09-15"},
        {"table_name": "T-70", "approved": "True", "valid_until": "2026-08-31"},
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rfields, lineterminator="\n")
    w.writeheader()
    w.writerows(base_re)
    reindex_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    reindex = base_re

    by_last: dict[str, dict] = {}
    for r in health:
        by_last[r["table_name"]] = r
    reidx = {r["table_name"]: r for r in reindex}

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
        })
    gold_rows.sort(key=lambda g: (g["_la"], g["table_name"]))

    # Fix T-61 if 0.40 still none — bump was intentional check
    for g in gold_rows:
        if g["table_name"] in ("T-60", "T-61") and g["finding"] == "none":
            print("note", g["table_name"], "ratio", g["bloat_ratio"], "finding none (cap equality)")

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

    # Patch EXPECTED
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

    # Strip prior densify memo test dumps; add ONE parametrized strict gate for all flags T-46+
    src = re.sub(r"\n# --- v7 densify memo gates.*", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_memo_explains_t46\(:.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_memo_explains_t\d+_v7\(\):.*?(?=\ndef test_|\Z)", "\n", src, flags=re.S)

    # Build MEMO_V8_STRICT dict embedded in tests
    memo_map = {}
    for g in gold_rows:
        tid = g["table_name"]
        num = int(tid.split("-")[1])
        if num < 46 or g["finding"] == "none":
            continue
        concepts = [g["finding"], str(g["_dead"]), str(g["_pages"])]
        if g["finding"] == "BLOAT_THRESHOLD_EXCEEDED":
            concepts += [str(g["bloat_ratio"]), "compute"]
            if g["_stale_days"] > 30:
                concepts += ["tighten", "stale"]
            if g["_size_export"].lower() == "medium":
                concepts += ["medium"]
            if g["_maint"].lower() == "true":
                if tid in ("T-67",) or (tid in reidx and reidx[tid]["approved"].lower() == "false"):
                    concepts += ["unapproved", "reindex"]
                elif tid in reidx and date.fromisoformat(reidx[tid]["valid_until"]) < AUDIT:
                    concepts += ["expired", "reindex"]
                elif tid not in reidx:
                    concepts += ["unapproved", "reindex"]
        elif g["finding"] == "STALE_STATISTICS":
            concepts += [str(g["_stale_days"]), "stale", "days_since_analyze"]
        else:
            if g["_vac"].lower() == "manual":
                concepts += ["manual", "vacuum", "override"]
            else:
                concepts += ["autovacuum", "disabled"]
        memo_map[tid] = concepts

    embed = "MEMO_V8_STRICT = " + json.dumps(memo_map, indent=4) + "\n"
    block = f'''
{embed}

@pytest.mark.parametrize("table_id", sorted(MEMO_V8_STRICT.keys(), key=lambda t: (len(t), t)))
def test_memo_v8_strict_local_evidence(table_id):
    """Every densify non-none table needs dead_pages + total_pages in the local memo unit."""
    concepts = MEMO_V8_STRICT[table_id]
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
'''
    # remove old dashboard test if present then append
    src = re.sub(r"\ndef test_ignores_dashboard_suggested_findings\(\):.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\nMEMO_V8_STRICT = \{.*?\n\}\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\ndef test_memo_v8_strict_local_evidence\(.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)
    src = src.rstrip() + "\n" + block
    tests_path.write_text(src, encoding="utf-8", newline="\n")

    # Gold memo
    old_memo = memo_path.read_text(encoding="utf-8")
    # Keep pre-densify graded sections if possible
    old_body = re.sub(r"(?s)^# Table maintenance audit.*?\n## ", "## ", old_memo, count=1)
    if old_body.startswith("#"):
        parts = old_memo.split("\n## ", 1)
        old_body = ("## " + parts[1]) if len(parts) == 2 else old_memo
    old_body = re.sub(r"\n## Densify traps.*", "\n", old_body, count=1, flags=re.S)
    old_body = re.sub(r"\n## Cap-equality compliance\n.*", "\n", old_body, count=1, flags=re.S)
    old_body = re.sub(r"\n## Dashboard decoy\n.*", "\n", old_body, count=1, flags=re.S)
    # Drop prior densify bullets T-46+
    for i in range(46, 100):
        old_body = re.sub(rf"\n- \*\*T-{i}\*\*:.*?(?=\n- \*\*|\n## |\Z)", "\n", old_body, flags=re.S)

    flagged = [g for g in gold_rows if g["finding"] != "none"]
    compliant = [g for g in gold_rows if g["finding"] == "none"]
    header = [
        f"# Table maintenance audit — {len(gold_rows)} unique tables",
        "",
        f"{len(gold_rows)} unique tables against DBOPS-31 ({len(health)} input rows after last-row "
        f"collapse). {len(compliant)} compliant, {len(flagged)} flagged. "
        f"Ignore dashboard_suggested_findings.csv — policy decides.",
        "",
        "| Table | Size class | Bloat ratio | Finding |",
        "|---|---|---|---|",
    ]
    for g in gold_rows:
        header.append(f"| {g['table_name']} | {g['size_class']} | {g['bloat_ratio']} | {g['finding']} |")
    header.append("")

    dens = ["", "## Densify traps (T-46+ full matrix)", ""]
    for g in flagged:
        tid = g["table_name"]
        if int(tid.split("-")[1]) < 46:
            continue
        dead, pages, ratio, finding = g["_dead"], g["_pages"], g["bloat_ratio"], g["finding"]
        stale_days = g["_stale_days"]
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
                f"computes ratio {ratio} within the tightened cap so bloat does not fire. "
                f"Finding: STALE_STATISTICS."
            )
        else:
            bits = [
                f"{tid} computes from dead_pages={dead} and total_pages={pages} "
                f"(round-half-up ratio {ratio}) over its computed {g['size_class']} cap after compute"
            ]
            if stale_days > 30:
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
                    bits.append("approved reindex is expired before audit_date so not exempt")
            dens.append(f"- **{tid}**: " + "; ".join(bits) + ". Finding: BLOAT_THRESHOLD_EXCEEDED.")

    dens += [
        "",
        "## Cap-equality compliance",
        "",
        "Ratios exactly equal to the effective cap are not over the cap (T-55/T-77/T-80/T-88/T-94 style).",
        "",
        "## Dashboard decoy",
        "",
        "`dashboard_suggested_findings.csv` is non-authoritative; DBOPS-31 decides every finding.",
        "",
    ]
    memo_path.write_text("\n".join(header) + "\n" + old_body.lstrip() + "\n".join(dens), encoding="utf-8", newline="\n")

    # Instruction
    instr = instr_path.read_text(encoding="utf-8")
    instr = re.sub(r"\n10\..*", "\n", instr, flags=re.S)
    instr = re.sub(r"\n11\..*", "\n", instr, flags=re.S)
    instr = instr.rstrip() + (
        "\n\n10. Ignore `input/dashboard_suggested_findings.csv` — non-authoritative dashboard "
        "heuristic; policy wins when it disagrees.\n"
        "11. Full densify matrix (499/500 boundaries, exactly-30-day non-stale, "
        "`valid_until == audit_date` exemption, missing/unapproved/expired reindex, "
        "triple last-row duplicates, round-half-up `.x5` vs banker's rounding, lying "
        "`days_since_analyze`, case-variant `Manual` vacuum_type, and stale small-cap "
        "tightening 0.40→0.35) remains governed by rules 1–9 and `maintenance_policy.md`. "
        "For every non-`none` finding, the memo local unit must cite that table's own "
        "`dead_pages` and `total_pages` digit forms.\n"
    )
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    pol = policy_path.read_text(encoding="utf-8")
    if "dashboard_suggested_findings" not in pol:
        pol = pol.replace(
            "Where the database's own\nhealth dashboard disagrees, this policy decides.",
            "Where the database's own\nhealth dashboard disagrees (including "
            "`dashboard_suggested_findings.csv`), this policy decides.",
        )
        policy_path.write_text(pol, encoding="utf-8", newline="\n")

    print("v8 full harden complete")
    for g in gold_rows:
        if int(g["table_name"].split("-")[1]) >= 46:
            print(g["table_name"], g["bloat_ratio"], g["finding"])


if __name__ == "__main__":
    main()

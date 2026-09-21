"""v7 hard fair densify: more disclosed traps + decoy dashboard + strict memo gates.

Goal: Oracle 1.0, GLM toward 0/4. No hidden rules — policy/instruction only.
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

    # Drop prior densify waves T-46+
    drop = {f"T-{i}" for i in range(46, 99)}
    health = [r for r in health if r["table_name"] not in drop]

    # --- Fair hard traps (all disclosed) ---
    new_rows: list[dict] = []
    # T-46..T-54 (keep prior densify set)
    new_rows += [
        row("T-46", pages=1000, dead=155, la_days=33, days_field=10),  # RHU 0.16 over stale 0.15
        row("T-47", pages=1000, dead=100, la_days=12),  # first dup discard
        row("T-47", pages=1000, dead=220, la_days=12),  # last wins BLOAT 0.22
        row("T-48", pages=1000, dead=100, la_days=40, days_field=5),  # lying days → STALE
        row("T-49", pages=800, dead=168, size_export="medium", la_days=8),  # medium trap
        row("T-50", pages=1000, dead=250, maint="True", la_days=5),  # unapproved
        row("T-51", pages=1000, dead=240, maint="True", la_days=6),  # expired
        row("T-52", pages=1000, dead=50, vac="manual", la_days=4),  # manual override
        row("T-53", pages=1000, dead=145, la_days=35, days_field=5),  # =tightened → STALE
        row("T-54", pages=400, dead=164, size_export="large", la_days=9),  # small 0.41
    ]
    # T-55.. : volume + RHU/RHE killers + boundaries
    new_rows += [
        # RHU≠RHE: 205/1000→0.21 (RHE would 0.20=cap→none). Fresh large BLOAT.
        row("T-55", pages=1000, dead=205, la_days=7, bloat_export="0.2"),
        # 125/1000→RHU 0.13 RHE 0.12; stale tighten; still under 0.15 → STALE
        row("T-56", pages=1000, dead=125, la_days=40, days_field=2, bloat_export="0.12"),
        # 499 pages → small; 205/499≈0.4108→0.41 over 0.4; export large
        row("T-57", pages=499, dead=205, size_export="large", la_days=11, bloat_export="0.41"),
        # 500 pages → large; 105/500=0.21 over 0.2; export small
        row("T-58", pages=500, dead=105, size_export="small", la_days=11, bloat_export="0.21"),
        # exactly 30 days → NOT stale; ratio 0.18 under large → none
        row("T-59", pages=1000, dead=180, la_days=30, days_field=99),
        # valid_until == audit_date → exempt; ratio 0.35 would bloat
        row("T-60", pages=1000, dead=350, maint="True", la_days=8),
        # maintenance_active but NO reindex row → BLOAT 0.28
        row("T-61", pages=1000, dead=280, maint="True", la_days=9),
        # triple duplicate; last is BLOAT 0.23
        row("T-62", pages=1000, dead=50, la_days=14),
        row("T-62", pages=1000, dead=100, la_days=14),
        row("T-62", pages=1000, dead=230, la_days=14),
        # 0.225→RHU 0.23 / RHE 0.22; over large 0.2
        row("T-63", pages=1000, dead=225, la_days=6, bloat_export="0.22"),
        # 165/1000=0.165→0.17 stale over 0.15
        row("T-64", pages=1000, dead=165, la_days=36, days_field=3, bloat_export="0.16"),
        # 144/1000=0.144→0.14 stale under 0.15 → STALE
        row("T-65", pages=1000, dead=144, la_days=42, days_field=1),
        # manual + high bloat + stale → AUTOVACUUM only
        row("T-66", pages=1000, dead=400, vac="manual", la_days=50, days_field=0),
        # medium + 450 pages → small; 185/450≈0.411→0.41 over 0.4
        row("T-67", pages=450, dead=185, size_export="medium", la_days=10, bloat_export="0.4"),
        # medium + 450; 180/450=0.4 exactly → none (not over)
        row("T-68", pages=450, dead=180, size_export="medium", la_days=10),
        # lying days=0 but 55d stale; ratio under tightened → STALE
        row("T-69", pages=1000, dead=80, la_days=55, days_field=0),
        # 0.215→0.22 fresh large BLOAT (export half-even-ish 0.22 ok)
        row("T-70", pages=1000, dead=215, la_days=5, bloat_export="0.22"),
        # expired reindex by 1 day; maint True; 0.26 BLOAT
        row("T-71", pages=1000, dead=260, maint="True", la_days=7),
        # approved future reindex; 0.30 → none (exempt)
        row("T-72", pages=1000, dead=300, maint="True", la_days=7),
        # small 399 pages; 159/399≈0.3985→0.40 =cap → none
        row("T-73", pages=399, dead=159, size_export="large", la_days=12),
        # small 399; 160/399≈0.401→0.40 =cap → none; 161/399≈0.4035→0.40
        # use 163/399≈0.4085→0.41 BLOAT
        row("T-74", pages=399, dead=163, size_export="large", la_days=12, bloat_export="0.4"),
        # stale large; 0.150 raw 150/1000=0.15 = tightened → STALE not BLOAT
        row("T-75", pages=1000, dead=150, la_days=38, days_field=4),
        # autovacuum False; export size wrong
        row("T-76", pages=600, dead=50, size_export="small", auto="False", la_days=3),
        # RHU 405/1000=0.405→0.41; export bloat 0.40
        row("T-77", pages=1000, dead=405, size_export="small", la_days=8, bloat_export="0.4"),
        # first looks STALE-ish but last is fresh none
        row("T-78", pages=1000, dead=200, la_days=40, days_field=40),
        row("T-78", pages=1000, dead=100, la_days=5, days_field=5),
        # stale + 0.205→0.21 over tightened 0.15
        row("T-79", pages=1000, dead=205, la_days=34, days_field=2, bloat_export="0.2"),
        # 0.235→0.24 fresh BLOAT
        row("T-80", pages=1000, dead=235, la_days=6, bloat_export="0.24"),
    ]

    health.extend(new_rows)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(health)
    health_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print("health rows", len(health))

    # reindex
    reindex = list(csv.DictReader(reindex_path.open(encoding="utf-8-sig")))
    rfields = list(reindex[0].keys())
    reindex = [r for r in reindex if r["table_name"] not in drop]
    reindex += [
        {"table_name": "T-50", "approved": "False", "valid_until": "2026-09-15"},
        {"table_name": "T-51", "approved": "True", "valid_until": "2026-08-31"},
        {"table_name": "T-60", "approved": "True", "valid_until": "2026-09-01"},  # == audit
        {"table_name": "T-71", "approved": "True", "valid_until": "2026-08-31"},
        {"table_name": "T-72", "approved": "True", "valid_until": "2026-09-15"},
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rfields, lineterminator="\n")
    w.writeheader()
    w.writerows(reindex)
    reindex_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    # Decoy dashboard — wrong findings; agents must ignore
    by_last: dict[str, dict] = {}
    for r in health:
        by_last[r["table_name"]] = r
    decoy_rows = []
    for tid, r in by_last.items():
        # deliberately wrong
        decoy_rows.append(
            {
                "table_name": tid,
                "suggested_finding": "BLOAT_THRESHOLD_EXCEEDED"
                if tid.endswith(("1", "3", "5"))
                else "none",
                "note": "health-dashboard heuristic — not authoritative",
            }
        )
    dfields = ["table_name", "suggested_finding", "note"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=dfields, lineterminator="\n")
    w.writeheader()
    w.writerows(decoy_rows)
    dash_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    # Gold rebuild
    reidx = {r["table_name"]: r for r in reindex}
    gold_rows = []
    for tid, r in by_last.items():
        pages = int(r["total_pages"])
        dead = int(r["dead_pages"])
        ratio = rhu(dead / pages, 2)
        size = "large" if pages >= 500 else "small"
        cap = 0.2 if size == "large" else 0.4
        vac_off = r["autovacuum_enabled"].lower() == "false" or r["vacuum_type"].lower() == "manual"
        la = date.fromisoformat(r["last_analyzed"])
        stale = (AUDIT - la).days > 30
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
        gold_rows.append(
            {
                "table_name": tid,
                "size_class": size,
                "bloat_ratio": fmt_ratio(ratio),
                "finding": finding,
                "_la": r["last_analyzed"],
                "_dead": dead,
                "_pages": pages,
                "_stale_days": (AUDIT - la).days,
            }
        )
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

    # Patch EXPECTED + row count
    expected = {
        g["table_name"]: {
            "size_class": g["size_class"],
            "bloat_ratio": float(g["bloat_ratio"]),
            "finding": g["finding"],
        }
        for g in gold_rows
    }
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

    # Strict memo gates for densify wave (require dead_pages digits + finding evidence)
    memo_block = ["\n\n# --- v7 densify memo gates (strict local evidence) ---\n"]
    for g in gold_rows:
        tid = g["table_name"]
        if tid < "T-46" or g["finding"] == "none":
            continue
        dead = g["_dead"]
        pages = g["_pages"]
        ratio = g["bloat_ratio"]
        finding = g["finding"]
        stale_days = g["_stale_days"]
        if finding == "BLOAT_THRESHOLD_EXCEEDED":
            concepts = [finding, str(dead), str(pages), str(ratio), "compute"]
            if stale_days > 30:
                concepts += ["tighten", "0.15" if g["size_class"] == "large" else "0.35", "stale"]
            elif pages < 500:
                concepts += ["small"]
            else:
                concepts += ["large"]
        elif finding == "STALE_STATISTICS":
            concepts = [finding, str(stale_days), "stale", str(dead), "days_since_analyze"]
        else:  # AUTOVACUUM
            concepts = [finding, "manual" if by_last[tid]["vacuum_type"] == "manual" else "autovacuum", "vacuum", str(pages)]
        args = ", ".join(json.dumps(c) for c in concepts)
        memo_block.append(
            f"\ndef test_memo_explains_{tid.lower().replace('-', '')}_v7():\n"
            f'    """Strict local evidence for densify {tid}."""\n'
            f"    assert _memo_mentions({json.dumps(tid)}, {args}), "
            f'"Memo must explain {tid} with dead_pages/local evidence"\n'
        )
    # Remove prior v7 block / t46 densify append if present, then append
    src = re.sub(r"\n# --- v7 densify memo gates.*", "\n", src, count=1, flags=re.S)
    if "def test_memo_explains_t46" in src:
        src = re.sub(r"\ndef test_memo_explains_t46\(:.*", "\n", src, count=1, flags=re.S)
    src = src.rstrip() + "".join(memo_block) + "\n"

    # Dashboard ignore test
    if "def test_ignores_dashboard_suggested_findings" not in src:
        src += '''

def test_ignores_dashboard_suggested_findings():
    """Audit findings must not copy dashboard_suggested_findings.csv (policy wins)."""
    import csv as _csv
    dash = WORKSPACE / "input" / "dashboard_suggested_findings.csv"
    if not dash.is_file():
        # Harbor mounts input under /app/input
        dash = Path("/app/input/dashboard_suggested_findings.csv")
    assert dash.is_file(), "dashboard_suggested_findings.csv missing from input"
    suggested = {r["table_name"]: r["suggested_finding"] for r in _csv.DictReader(dash.open(encoding="utf-8-sig"))}
    rows, err = _load_csv()
    assert err is None, err
    mismatches = 0
    for r in rows:
        tid = r["table_name"]
        if tid in suggested and suggested[tid] != r["finding"]:
            mismatches += 1
    # Decoy is constructed to disagree on many rows; gold must diverge on >= 10
    assert mismatches >= 10, f"Expected audit to diverge from dashboard decoy on >=10 tables, got {mismatches}"
'''
    tests_path.write_text(src, encoding="utf-8", newline="\n")

    # Memo: preserve old graded prose; refresh table; append densify explanations
    old_memo = memo_path.read_text(encoding="utf-8")
    old_memo = re.sub(r"\n## Cap-equality compliance\n.*", "\n", old_memo, count=1, flags=re.S)
    old_memo = re.sub(r"\n## Densify traps \(T-46.*", "\n", old_memo, count=1, flags=re.S)
    old_body = re.sub(r"(?s)^# Table maintenance audit.*?\n## ", "## ", old_memo, count=1)
    if old_body.startswith("#"):
        parts = old_memo.split("\n## ", 1)
        old_body = ("## " + parts[1]) if len(parts) == 2 else old_memo

    flagged = [g for g in gold_rows if g["finding"] != "none"]
    compliant = [g for g in gold_rows if g["finding"] == "none"]
    header = [
        f"# Table maintenance audit — {len(gold_rows)} unique tables",
        "",
        f"{len(gold_rows)} unique tables checked against DBOPS-31 "
        f"({len(health)} input rows after last-row collapse). "
        f"{len(compliant)} are compliant and {len(flagged)} carry a finding. "
        f"The health dashboard suggested_findings file is ignored — policy decides.",
        "",
        "| Table | Size class | Bloat ratio | Finding |",
        "|---|---|---|---|",
    ]
    for g in gold_rows:
        header.append(
            f"| {g['table_name']} | {g['size_class']} | {g['bloat_ratio']} | {g['finding']} |"
        )
    header.append("")

    densify_lines = [
        "",
        "## Densify traps (T-46+)",
        "",
        "Edge cases stay inside DBOPS-31. Ignore `dashboard_suggested_findings.csv`.",
        "",
    ]
    for g in flagged:
        tid = g["table_name"]
        if tid < "T-46":
            continue
        r = by_last[tid]
        dead = g["_dead"]
        pages = g["_pages"]
        ratio = g["bloat_ratio"]
        finding = g["finding"]
        stale_days = g["_stale_days"]
        if finding == "AUTOVACUUM_DISABLED":
            densify_lines.append(
                f"- **{tid}**: {tid} has vacuum_type={r['vacuum_type']} / autovacuum_enabled="
                f"{r['autovacuum_enabled']} on total_pages={pages}; the manual/autovacuum rule is "
                f"checked first with dead_pages={dead}. Finding: AUTOVACUUM_DISABLED."
            )
        elif finding == "STALE_STATISTICS":
            densify_lines.append(
                f"- **{tid}**: {tid} is {stale_days} days stale by audit_date minus last_analyzed "
                f"(ignore days_since_analyze={r['days_since_analyze']}); dead_pages={dead} / "
                f"total_pages={pages} computes ratio {ratio} which stays within the tightened cap, "
                f"so bloat does not fire. Finding: STALE_STATISTICS."
            )
        else:
            extra = ""
            if tid == "T-50":
                densify_lines.append(
                    "- **T-50**: T-50 shows maintenance_active but the reindex is unapproved "
                    "(approved=False), so there is no exemption; dead_pages=250 / total_pages=1000 "
                    "computes ratio 0.25 over the large cap after compute. "
                    "Finding: BLOAT_THRESHOLD_EXCEEDED."
                )
                continue
            if tid == "T-51":
                densify_lines.append(
                    "- **T-51**: T-51 has an approved reindex that is expired (valid_until before "
                    "audit_date), so it is not exempt; dead_pages=240 / total_pages=1000 computes "
                    "ratio 0.24 over the large cap after compute. Finding: BLOAT_THRESHOLD_EXCEEDED."
                )
                continue
            if tid == "T-71":
                densify_lines.append(
                    "- **T-71**: T-71 has an approved reindex that is expired before audit_date, "
                    "so it is not exempt; dead_pages=260 / total_pages=1000 computes ratio 0.26 "
                    "over the large cap after compute. Finding: BLOAT_THRESHOLD_EXCEEDED."
                )
                continue
            if tid == "T-61":
                densify_lines.append(
                    "- **T-61**: T-61 shows maintenance_active but has no matching approved reindex "
                    "row, so it is unapproved for exemption; dead_pages=280 / total_pages=1000 "
                    "computes ratio 0.28 over the large cap after compute. "
                    "Finding: BLOAT_THRESHOLD_EXCEEDED."
                )
                continue
            if stale_days > 30:
                extra = (
                    f" Statistics are {stale_days} days stale so the {g['size_class']} cap tightens "
                    f"and ratio {ratio} exceeds the tightened effective cap."
                )
            elif r["size_class"] == "medium":
                extra = (
                    f" Export size_class says medium but total_pages={pages} computes "
                    f"{g['size_class']}."
                )
            densify_lines.append(
                f"- **{tid}**: {tid} computes from dead_pages={dead} and total_pages={pages} "
                f"(round-half-up ratio {ratio}) which is over its {g['size_class']} cap after "
                f"compute from pages.{extra} Finding: BLOAT_THRESHOLD_EXCEEDED."
            )

    densify_lines += [
        "",
        "## Cap-equality compliance",
        "",
        "Ratios that exactly equal the effective size-class cap are not over the cap, so bloat "
        "does not fire (see T-53/T-75 at the stale-tightened 0.15 boundary and T-68/T-73 at 0.4).",
        "",
        "## Dashboard decoy",
        "",
        "`dashboard_suggested_findings.csv` is a non-authoritative health-dashboard heuristic and "
        "must be ignored; DBOPS-31 / maintenance_policy.md decide every finding.",
        "",
    ]

    memo_path.write_text(
        "\n".join(header) + "\n" + old_body.lstrip() + "\n".join(densify_lines),
        encoding="utf-8",
        newline="\n",
    )

    # Instruction: decoy + densify note; dedupe duplicate rule 10
    instr = instr_path.read_text(encoding="utf-8")
    instr = re.sub(
        r"\n10\. Densified edge cases.*?(?=\n10\. Densified|\Z)",
        "\n",
        instr,
        flags=re.S,
    )
    if "dashboard_suggested_findings" not in instr:
        instr += (
            "\n10. Ignore `input/dashboard_suggested_findings.csv` — it is a non-authoritative "
            "health-dashboard heuristic. Where it disagrees with `maintenance_policy.md`, the "
            "policy wins (same as the policy intro).\n"
            "11. Densified edge cases (499/500 page boundaries, exactly-30-day non-stale, "
            "`valid_until == audit_date` exemption, missing reindex rows, triple last-row "
            "duplicates, round-half-up `.x5` values that differ from banker's rounding, and "
            "lying `days_since_analyze`) remain fully governed by rules 1–9 and the policy — "
            "do not invent extra rules. Memo explanations for each non-`none` finding must cite "
            "that table's own `dead_pages` and `total_pages` digit forms in the local prose unit.\n"
        )
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    # Policy note on dashboard
    pol = policy_path.read_text(encoding="utf-8")
    if "dashboard_suggested_findings" not in pol:
        pol = pol.replace(
            "Where the database's own\nhealth dashboard disagrees, this policy decides.",
            "Where the database's own\nhealth dashboard disagrees (including "
            "`dashboard_suggested_findings.csv`), this policy decides.",
        )
        policy_path.write_text(pol, encoding="utf-8", newline="\n")

    for tid in [f"T-{i}" for i in range(46, 81)]:
        if tid in by_last:
            g = next(x for x in gold_rows if x["table_name"] == tid)
            print(tid, g["bloat_ratio"], g["finding"])
    print("v7 densify complete")


if __name__ == "__main__":
    main()

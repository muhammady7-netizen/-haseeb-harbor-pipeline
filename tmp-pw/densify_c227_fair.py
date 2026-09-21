"""Fair densify c227 for GLM ~0/4: disclosed traps only, Oracle stays 1.0."""
from __future__ import annotations

import csv
import io
import json
import re
import textwrap
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


def main() -> None:
    health_path = PACK / "environment" / "input" / "table_health.csv"
    reindex_path = PACK / "environment" / "input" / "reindex_log.csv"
    gold_path = PACK / "solution" / "files" / "bloat_audit.csv"
    results_path = PACK / "solution" / "files" / "results.json"
    memo_path = PACK / "solution" / "files" / "bloat_memo.md"
    tests_path = PACK / "tests" / "test_outputs.py"
    instr_path = PACK / "instruction.md"
    policy_path = PACK / "environment" / "input" / "maintenance_policy.md"

    health = list(csv.DictReader(health_path.open(encoding="utf-8-sig")))
    fields = list(health[0].keys())
    existing = {r["table_name"] for r in health}

    # --- New trap rows (all use disclosed rules only) ---
    # T-46: round-half-up on stale-tightened large cap
    #   dead=155/1000=0.155→0.16, stale (>30d), large cap 0.2→0.15 → BLOAT
    # T-47: duplicate pair — first looks none (dead=100), LAST is authoritative BLOAT (dead=220)
    # T-48: export days_since_analyze=5 (looks fresh) but dates → 40d stale; ratio 0.10 under
    #       normal large cap → STALE_STATISTICS only
    # T-49: export size_class=medium, pages=800→large, dead=168→0.21 → BLOAT (medium trap)
    # T-50: maintenance_active=True but reindex unapproved → BLOAT (dead=250→0.25)
    # T-51: approved reindex expired valid_until=audit-1 → BLOAT (dead=240→0.24)
    # T-52: vacuum_type=manual, autovacuum_enabled=True, tiny bloat → AUTOVACUUM_DISABLED
    # T-53: stale + round 0.145→0.15 exactly at tightened cap → STALE (not BLOAT)
    # T-54: small pages=400, export large, dead=164→0.41 > small cap 0.4 → BLOAT

    new_rows = [
        # T-46 densify round+stale
        {
            "table_name": "T-46",
            "size_class": "large",
            "total_pages": "1000",
            "dead_pages": "155",
            "bloat_ratio": "0.16",  # export may match rounded; still must compute
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(33),
            "days_since_analyze": "10",  # trap: looks fresh
            "maintenance_active": "False",
        },
        # T-47 duplicate first (discard)
        {
            "table_name": "T-47",
            "size_class": "large",
            "total_pages": "1000",
            "dead_pages": "100",
            "bloat_ratio": "0.1",
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(12),
            "days_since_analyze": "12",
            "maintenance_active": "False",
        },
        # T-47 last wins → BLOAT
        {
            "table_name": "T-47",
            "size_class": "large",
            "total_pages": "1000",
            "dead_pages": "220",
            "bloat_ratio": "0.22",
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(12),
            "days_since_analyze": "12",
            "maintenance_active": "False",
        },
        # T-48 stale-only via dates; export days field lies
        {
            "table_name": "T-48",
            "size_class": "large",
            "total_pages": "1000",
            "dead_pages": "100",
            "bloat_ratio": "0.1",
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(40),
            "days_since_analyze": "5",
            "maintenance_active": "False",
        },
        # T-49 medium trap
        {
            "table_name": "T-49",
            "size_class": "medium",
            "total_pages": "800",
            "dead_pages": "168",
            "bloat_ratio": "0.21",
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(8),
            "days_since_analyze": "8",
            "maintenance_active": "False",
        },
        # T-50 unapproved reindex
        {
            "table_name": "T-50",
            "size_class": "large",
            "total_pages": "1000",
            "dead_pages": "250",
            "bloat_ratio": "0.25",
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(5),
            "days_since_analyze": "5",
            "maintenance_active": "True",
        },
        # T-51 expired approved reindex
        {
            "table_name": "T-51",
            "size_class": "large",
            "total_pages": "1000",
            "dead_pages": "240",
            "bloat_ratio": "0.24",
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(6),
            "days_since_analyze": "6",
            "maintenance_active": "True",
        },
        # T-52 manual vacuum override
        {
            "table_name": "T-52",
            "size_class": "large",
            "total_pages": "1000",
            "dead_pages": "50",
            "bloat_ratio": "0.05",
            "autovacuum_enabled": "True",
            "vacuum_type": "manual",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(4),
            "days_since_analyze": "4",
            "maintenance_active": "False",
        },
        # T-53 boundary: 145/1000=0.145→0.15 == tightened 0.15 → not over → STALE_STATISTICS
        # (models that treat equality as BLOAT fail)
        {
            "table_name": "T-53",
            "size_class": "large",
            "total_pages": "1000",
            "dead_pages": "145",
            "bloat_ratio": "0.15",
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(35),
            "days_since_analyze": "5",
            "maintenance_active": "False",
        },
        # T-54 size_class export large but pages=400→small; 164/400=0.41 > 0.4
        {
            "table_name": "T-54",
            "size_class": "large",
            "total_pages": "400",
            "dead_pages": "164",
            "bloat_ratio": "0.4",  # export round-half-even trap-ish; true is 0.41
            "autovacuum_enabled": "True",
            "vacuum_type": "auto",
            "audit_date": AUDIT.isoformat(),
            "last_analyzed": days_ago(9),
            "days_since_analyze": "9",
            "maintenance_active": "False",
        },
    ]

    # drop any prior densify rows if re-run
    drop = {f"T-{i}" for i in range(46, 55)}
    health = [r for r in health if r["table_name"] not in drop]
    health.extend(new_rows)

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(health)
    health_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print("health rows", len(health))

    # reindex log additions
    reindex = list(csv.DictReader(reindex_path.open(encoding="utf-8-sig")))
    rfields = list(reindex[0].keys())
    reindex = [r for r in reindex if r["table_name"] not in {"T-50", "T-51"}]
    reindex.append({"table_name": "T-50", "approved": "False", "valid_until": "2026-09-15"})
    reindex.append({"table_name": "T-51", "approved": "True", "valid_until": "2026-08-31"})  # day before audit
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rfields, lineterminator="\n")
    w.writeheader()
    w.writerows(reindex)
    reindex_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    # --- Gold: rebuild from input using disclosed rules ---
    by: dict[str, dict] = {}
    for r in health:
        by[r["table_name"]] = r  # last wins
    reidx = {r["table_name"]: r for r in reindex}

    gold_rows = []
    for tid, r in by.items():
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
                "bloat_ratio": (
                    f"{ratio:.2f}".rstrip("0").rstrip(".")
                    if f"{ratio:.2f}".endswith("0")
                    else f"{ratio:.2f}"
                ),
                "finding": finding,
                "_la": r["last_analyzed"],
            }
        )

    gold_rows.sort(key=lambda g: (g["_la"], g["table_name"]))
    for g in gold_rows:
        del g["_la"]

    gfields = ["table_name", "size_class", "bloat_ratio", "finding"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=gfields, lineterminator="\n")
    w.writeheader()
    w.writerows(gold_rows)
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
    for tid in [f"T-{i}" for i in range(46, 55)]:
        print(tid, next(g for g in gold_rows if g["table_name"] == tid))

    expected = {
        g["table_name"]: {
            "size_class": g["size_class"],
            "bloat_ratio": float(g["bloat_ratio"]),
            "finding": g["finding"],
        }
        for g in gold_rows
    }

    def _fmt_ratio(v: float) -> str:
        s = f"{v:.2f}".rstrip("0").rstrip(".")
        return s if s else "0"

    # --- patch EXPECTED_TABLES + EXPECTED_RESULTS in test_outputs.py ---
    src = tests_path.read_text(encoding="utf-8")
    # replace EXPECTED_TABLES block
    body = "EXPECTED_TABLES = {\n"
    for tid in sorted(expected, key=lambda t: (len(t), t)):
        e = expected[tid]
        body += (
            f'    "{tid}": {{"size_class": "{e["size_class"]}", '
            f'"bloat_ratio": {_fmt_ratio(e["bloat_ratio"])}, "finding": "{e["finding"]}"}},\n'
        )
    body += "}\n"
    src2, n = re.subn(
        r"EXPECTED_TABLES = \{.*?\n\}",
        body.rstrip(),
        src,
        count=1,
        flags=re.S,
    )
    assert n == 1, "EXPECTED_TABLES replace failed"
    src = src2

    res_body = "EXPECTED_RESULTS = {\n"
    for k, v in results.items():
        res_body += f'    "{k}": {v},\n'
    res_body += "}"
    src2, n = re.subn(
        r"EXPECTED_RESULTS = \{.*?\n\}",
        res_body,
        src,
        count=1,
        flags=re.S,
    )
    assert n == 1
    src = src2

    # Keep exact-row-count assertion in sync with densified population
    src2, n = re.subn(
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
    assert n == 1, "row-count test replace failed"
    src = src2
    memo_tests = '''

def test_memo_explains_t46():
    """T-46: round-half-up 0.155→0.16 over stale-tightened large cap 0.15."""
    assert _memo_mentions(
        "T-46", "BLOAT_THRESHOLD_EXCEEDED", "0.16", "0.15", "tighten", "stale", "1000"
    ) or _memo_mentions(
        "T-46", "BLOAT_THRESHOLD_EXCEEDED", "0.155", "0.15", "round", "stale", "1000"
    ), "Memo must explain T-46 round+stale densify trap"


def test_memo_explains_t47():
    """T-47: last duplicate row wins (dead=220→0.22 BLOAT); first row discarded."""
    assert _memo_mentions(
        "T-47", "BLOAT_THRESHOLD_EXCEEDED", "0.22", "duplicate", "last", "large"
    ) or _memo_mentions(
        "T-47", "BLOAT_THRESHOLD_EXCEEDED", "0.22", "authoritative", "1000", "large"
    ), "Memo must explain T-47 last-row duplicate collapse"


def test_memo_explains_t48():
    """T-48: export days_since_analyze lies; date math → STALE_STATISTICS."""
    assert _memo_mentions(
        "T-48", "STALE_STATISTICS", "40", "days_since_analyze", "stale"
    ), "Memo must explain T-48 legacy days field trap"


def test_memo_explains_t49():
    """T-49: medium export trap; computed large; 0.21 over 0.2."""
    assert _memo_mentions(
        "T-49", "BLOAT_THRESHOLD_EXCEEDED", "medium", "large", "compute", "0.21"
    ), "Memo must explain T-49 medium trap"


def test_memo_explains_t50():
    """T-50: maintenance_active but unapproved reindex → BLOAT."""
    assert _memo_mentions(
        "T-50", "BLOAT_THRESHOLD_EXCEEDED", "unapproved", "reindex", "0.25"
    ), "Memo must explain T-50 unapproved reindex"


def test_memo_explains_t51():
    """T-51: approved reindex expired (valid_until < audit_date) → BLOAT."""
    assert _memo_mentions(
        "T-51", "BLOAT_THRESHOLD_EXCEEDED", "reindex", "expired", "0.24"
    ), "Memo must explain T-51 expired reindex"


def test_memo_explains_t52():
    """T-52: manual vacuum overrides autovacuum_enabled=True."""
    assert _memo_mentions(
        "T-52", "AUTOVACUUM_DISABLED", "manual", "vacuum", "override"
    ), "Memo must explain T-52 manual vacuum"


def test_memo_explains_t53():
    """T-53: ratio equals stale-tightened cap → STALE not BLOAT."""
    assert _memo_mentions(
        "T-53", "STALE_STATISTICS", "0.15", "stale", "35"
    ) or _memo_mentions(
        "T-53", "STALE_STATISTICS", "0.145", "round", "stale"
    ), "Memo must explain T-53 equality-at-tightened-cap is STALE not BLOAT"


def test_memo_explains_t54():
    """T-54: export size_class large but pages=400→small; 0.41 over 0.4."""
    assert _memo_mentions(
        "T-54", "BLOAT_THRESHOLD_EXCEEDED", "400", "small", "0.41", "compute"
    ) or _memo_mentions(
        "T-54", "BLOAT_THRESHOLD_EXCEEDED", "400", "small", "round", "0.41"
    ), "Memo must explain T-54 size-class export trap"
'''
    if "def test_memo_explains_t46" not in src:
        src = src.rstrip() + "\n" + memo_tests
    else:
        # replace from t46 onward block roughly
        src = re.sub(
            r"\ndef test_memo_explains_t46\(:.*",
            "\n" + memo_tests.lstrip(),
            src,
            count=1,
            flags=re.S,
        )
        if "def test_memo_explains_t46" not in src:
            src = src.rstrip() + "\n" + memo_tests

    tests_path.write_text(src, encoding="utf-8", newline="\n")

    # --- Gold memo: preserve existing graded prose; refresh table + append new traps ---
    old_memo = memo_path.read_text(encoding="utf-8")
    # Drop trailing density notes that we rewrite
    old_memo = re.sub(
        r"\n## Cap-equality compliance\n.*",
        "\n",
        old_memo,
        count=1,
        flags=re.S,
    )
    # Strip old markdown summary table (regenerate)
    old_body = re.sub(
        r"(?s)^# Table maintenance audit.*?\n## ",
        "## ",
        old_memo,
        count=1,
    )
    # If strip failed, keep everything after first blank line after title
    if old_body.startswith("#"):
        parts = old_memo.split("\n## ", 1)
        old_body = ("## " + parts[1]) if len(parts) == 2 else old_memo

    # Remove any prior densify trap sections for T-46..T-54
    old_body = re.sub(
        r"\n## Densify traps \(T-46.*",
        "\n",
        old_body,
        count=1,
        flags=re.S,
    )
    for tid in [f"T-{i}" for i in range(46, 55)]:
        old_body = re.sub(
            rf"\n- \*\*{tid}\*\*:.*?(?=\n- \*\*|\n## |\Z)",
            "\n",
            old_body,
            flags=re.S,
        )

    flagged = [g for g in gold_rows if g["finding"] != "none"]
    compliant = [g for g in gold_rows if g["finding"] == "none"]
    header = [
        f"# Table maintenance audit — {len(gold_rows)} unique tables",
        "",
        f"{len(gold_rows)} unique tables checked against DBOPS-31 "
        f"({len(health)} input rows collapsed for duplicates including T-31/T-32/T-47). "
        f"{len(compliant)} are compliant and {len(flagged)} carry a finding.",
        "",
        "| Table | Size class | Bloat ratio | Finding |",
        "|---|---|---|---|",
    ]
    for g in gold_rows:
        # prefer compact ratio strings like existing gold (0.1 not 0.10)
        br = g["bloat_ratio"]
        if br.endswith("0") and "." in br:
            br = br.rstrip("0").rstrip(".")
        header.append(
            f"| {g['table_name']} | {g['size_class']} | {br} | {g['finding']} |"
        )
    header.append("")

    densify_section = [
        "",
        "## Densify traps (T-46–T-54)",
        "",
        "These additional edge cases stay fully inside DBOPS-31 / instruction rules 1–9.",
        "",
        "- **T-46**: T-46 is a densify trap: total_pages=1000 computes large, dead_pages=155 gives "
        "ratio 0.155 which round-half-up makes 0.16. Statistics are 33 days stale so the "
        "large cap tightens from 0.2 to 0.15, and 0.16 exceeds that tightened cap. "
        "Finding: BLOAT_THRESHOLD_EXCEEDED.",
        "- **T-47**: T-47 appears twice in the export; the last authoritative duplicate row has "
        "dead_pages=220 on total_pages=1000 (ratio 0.22) which is over the large cap 0.2, "
        "while the earlier snapshot is discarded. Finding: BLOAT_THRESHOLD_EXCEEDED.",
        "- **T-48**: T-48's export days_since_analyze field says 5 but the audit_date minus "
        "last_analyzed is 40 days, so statistics are stale; ratio 0.10 stays under the "
        "tightened large cap. Finding: STALE_STATISTICS.",
        "- **T-49**: T-49's size_class column says medium but total_pages=800 computes as large; "
        "dead_pages=168 yields ratio 0.21 which exceeds the large cap 0.2. "
        "Finding: BLOAT_THRESHOLD_EXCEEDED.",
        "- **T-50**: T-50 shows maintenance_active but the reindex is unapproved (approved=False), "
        "so there is no exemption and ratio 0.25 exceeds the large cap. "
        "Finding: BLOAT_THRESHOLD_EXCEEDED.",
        "- **T-51**: T-51 has an approved reindex that is expired because valid_until is before "
        "audit_date, so the table is not exempt and ratio 0.24 exceeds the large cap. "
        "Finding: BLOAT_THRESHOLD_EXCEEDED.",
        "- **T-52**: T-52 has autovacuum_enabled=True but vacuum_type=manual, so the manual vacuum "
        "override disables automatic protection. Finding: AUTOVACUUM_DISABLED.",
        "- **T-53**: T-53 is 35 days stale by the date fields even though days_since_analyze says 5; "
        "dead_pages=145 out of total_pages=1000 is 0.145 which round-half-up makes 0.15, "
        "equal to the tightened large cap 0.15 so bloat does not fire. "
        "Finding: STALE_STATISTICS.",
        "- **T-54**: T-54's size_class export says large but total_pages=400 computes as small; "
        "dead_pages=164 yields ratio 0.41 which is over the small cap 0.4 after "
        "round-half-up. Finding: BLOAT_THRESHOLD_EXCEEDED.",
        "",
        "## Cap-equality compliance",
        "",
        "Tables whose computed bloat ratio exactly equals their size-class cap remain "
        "compliant on the bloat check because the policy flags only ratios strictly over "
        "the cap. If statistics are also stale and bloat does not fire, the finding is "
        "`STALE_STATISTICS` (see T-53: 0.145→0.15 equals the tightened 0.15 cap).",
        "",
        "## T-53 boundary note",
        "",
        "T-53 is stale (35 days) with dead_pages=145 / total_pages=1000 → 0.145 which "
        "round-half-up makes 0.15, equal to the tightened large cap 0.15, so bloat does "
        "not fire and the finding is STALE_STATISTICS (not BLOAT_THRESHOLD_EXCEEDED).",
        "",
    ]

    memo_path.write_text(
        "\n".join(header) + "\n" + old_body.lstrip() + "\n".join(densify_section),
        encoding="utf-8",
        newline="\n",
    )

    # Instruction: reinforce last-row dedupe + densify awareness (fair disclosure)
    instr = instr_path.read_text(encoding="utf-8")
    if "last occurrence" not in instr.lower():
        instr = instr.replace(
            "6. Output exactly one row per unique `table_name` (dedupe duplicate input rows).",
            "6. Output exactly one row per unique `table_name` (dedupe duplicate input rows; "
            "when duplicates exist, the **last** occurrence is authoritative — see policy §5).",
        )
    if "T-46" not in instr:
        instr += (
            "\n10. Densified edge cases (including round-half-up on a stale-tightened cap, "
            "last-row duplicate collapse, lying `days_since_analyze`, `medium` size_class "
            "export traps, unapproved/expired reindex, and manual vacuum overrides) remain "
            "fully governed by rules 1–9 and `maintenance_policy.md` — do not invent extra rules.\n"
        )
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    # Policy encoding fix leftover mojibake optional skip
    print("densify complete")


if __name__ == "__main__":
    main()

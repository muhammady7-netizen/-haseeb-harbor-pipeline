"""c227 v12 — fair multi-hop harden via change-control tickets + aliases.

Disclosed in ops_bulletin.md + instruction pointer. Hard edges:
- Tickets never override AUTOVACUUM_DISABLED
- Valid BLOAT_HOLD suppresses only the bloat finding; stale can still fire
- status must be exactly 'Closed' (case-sensitive)
- exception_type must be exactly BLOAT_HOLD
- valid_until strictly after issued audit date 2026-09-01
- resolve table via table_name OR alias map; duplicate tickets last-wins
- dashboard remains decoy
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


BULLETIN = """# Ops bulletin OB-31-C — change-control holds (issued 2026-08-25)

This bulletin is **binding for the September 2026 maintenance audit** alongside
`maintenance_policy.md` and `policy_amendment_2026-08-20.md`.

## Purpose

`change_control_tickets.csv` records temporary **bloat holds**. A qualifying hold
suppresses a `BLOAT_THRESHOLD_EXCEEDED` finding only. It does **not** clear
`AUTOVACUUM_DISABLED`, and it does **not** clear `STALE_STATISTICS`.

## Qualifying hold (all must be true)

1. After resolving the ticket's target table (see Aliases), the ticket's
   `exception_type` equals exactly `BLOAT_HOLD` (other types such as
   `REINDEX_HOLD` or `FREEZE` do not suppress bloat findings).
2. `status` equals exactly `Closed` (case-sensitive). Values such as `closed`,
   `CLOSED`, `Open`, or `open` do **not** qualify.
3. `approved` equals `True` (case-insensitive boolean).
4. `valid_until` is **strictly after** the issued audit date `2026-09-01`
   (`valid_until > 2026-09-01`). Equality with the audit date does not qualify.
5. The ticket must target the table under review via `table_name` **or** via a
   name listed in `table_aliases.csv` that maps to that table.

## Finding interaction (order)

1. Autovacuum / exact-lowercase `manual` override still wins first. Holds never
   apply.
2. Compute the ordinary bloat decision (including amendment stale-cap tightening).
   If that decision would be `BLOAT_THRESHOLD_EXCEEDED` **and** a qualifying
   `BLOAT_HOLD` exists for the table, **suppress the bloat finding** and continue.
3. Then apply the ordinary stale-statistics rule. A table whose bloat was
   suppressed by a hold can still be `STALE_STATISTICS` when stale.
4. If neither autovacuum, (unsuppressed) bloat, nor stale applies, the finding is
   `none`.

## Duplicates and decoys

- If multiple tickets resolve to the same table, the **last** row in
  `change_control_tickets.csv` is authoritative.
- `dashboard_suggested_findings.csv` remains non-authoritative.
- Reindex exemption rules in the amendment are separate from change-control holds.
  A table may need both checks; a hold is not a reindex exemption and a reindex
  exemption is not a hold.

## Memo

When a hold changes the outcome (suppresses bloat, or you reject a near-miss
ticket), the local memo unit for that table must cite the ticket id (e.g. `CH-2201`)
and the word `hold` or `ticket`.
"""

AMENDMENT = """# Policy amendment DBOPS-31-A — issued 2026-08-20

Effective for the September 2026 maintenance audit. Binding audit calendar date:
**2026-09-01**. Also apply `ops_bulletin.md` for change-control holds.

## 1. Audit-date anchor

Do **not** use the `audit_date` column from `table_health.csv` for staleness or
reindex/hold validity. Always use issued audit date **2026-09-01**.

## 2. Exact-30-day staleness

Stale when `(2026-09-01 - last_analyzed).days >= 30`.

## 3. Large-table stale tightening

When stale: large (`total_pages >= 500`) reduce cap by **0.10** (effective 0.10);
small reduce by **0.05** (effective 0.35).

## 4. Manual vacuum case-sensitive

`vacuum_type` must equal exactly `manual`. `Manual` / `MANUAL` / spaced forms do not.

## 5. Reindex validity exclusive

Reindex exempts bloat only when `maintenance_active` AND `approved=True` AND
`valid_until > 2026-09-01`.

## 6. Reindex log duplicates

Last row per `table_name` in `reindex_log.csv` wins.
"""


def base_finding(tid: str, r: dict, reidx: dict) -> tuple[str, str, float, bool, int, bool]:
    """Return finding_without_hold, size, ratio, stale, stale_days, would_bloat."""
    pages = int(r["total_pages"])
    dead = int(r["dead_pages"])
    ratio = rhu(dead / pages, 2)
    size = "large" if pages >= 500 else "small"
    cap = 0.2 if size == "large" else 0.4
    vac_off = r["autovacuum_enabled"].lower() == "false" or r["vacuum_type"] == "manual"
    la = date.fromisoformat(r["last_analyzed"])
    stale_days = (AUDIT - la).days
    stale = stale_days >= STALE_MIN_DAYS
    if stale:
        tight = LARGE_STALE_TIGHTEN if size == "large" else SMALL_STALE_TIGHTEN
        cap = rhu(cap - tight, 2)
    if vac_off:
        return "AUTOVACUUM_DISABLED", size, ratio, stale, stale_days, False
    exempt = False
    if r["maintenance_active"].lower() == "true" and tid in reidx:
        rr = reidx[tid]
        if rr["approved"].lower() == "true" and date.fromisoformat(rr["valid_until"]) > AUDIT:
            exempt = True
    would_bloat = (not exempt) and ratio > cap + 1e-12
    if would_bloat:
        return "BLOAT_THRESHOLD_EXCEEDED", size, ratio, stale, stale_days, True
    if stale:
        return "STALE_STATISTICS", size, ratio, stale, stale_days, False
    return "none", size, ratio, stale, stale_days, False


def apply_hold(finding: str, would_bloat: bool, stale: bool, has_hold: bool) -> str:
    if finding == "AUTOVACUUM_DISABLED":
        return finding
    if would_bloat and has_hold:
        # suppress bloat; stale may still apply
        if stale:
            return "STALE_STATISTICS"
        return "none"
    return finding


def main() -> None:
    inp = PACK / "environment" / "input"
    health_path = inp / "table_health.csv"
    reindex_path = inp / "reindex_log.csv"
    dash_path = inp / "dashboard_suggested_findings.csv"
    amend_path = inp / "policy_amendment_2026-08-20.md"
    bulletin_path = inp / "ops_bulletin.md"
    tickets_path = inp / "change_control_tickets.csv"
    aliases_path = inp / "table_aliases.csv"
    gold_path = PACK / "solution" / "files" / "bloat_audit.csv"
    results_path = PACK / "solution" / "files" / "results.json"
    memo_path = PACK / "solution" / "files" / "bloat_memo.md"
    tests_path = PACK / "tests" / "test_outputs.py"
    instr_path = PACK / "instruction.md"

    amend_path.write_text(AMENDMENT, encoding="utf-8", newline="\n")
    bulletin_path.write_text(BULLETIN, encoding="utf-8", newline="\n")

    health = list(csv.DictReader(health_path.open(encoding="utf-8-sig")))
    fields = list(health[0].keys())
    # keep current population; only append a few join-trap tables
    health = [r for r in health if int(r["table_name"].split("-")[1]) <= 120]

    def row(tid, **kw):
        pages = kw.get("pages", 1000)
        dead = kw["dead"]
        ratio = rhu(dead / pages, 2)
        return {
            "table_name": tid,
            "size_class": kw.get("size_export", "large"),
            "total_pages": str(pages),
            "dead_pages": str(dead),
            "bloat_ratio": kw.get("bloat_export", fmt_ratio(ratio)),
            "autovacuum_enabled": kw.get("auto", "True"),
            "vacuum_type": kw.get("vac", "auto"),
            "audit_date": kw.get("audit_export", AUDIT.isoformat()),
            "last_analyzed": days_ago(kw.get("la_days", 10)),
            "days_since_analyze": str(kw.get("days_field", kw.get("la_days", 10))),
            "maintenance_active": kw.get("maint", "False"),
        }

    extra = [
        # Pure bloat fresh — will get valid hold → none
        row("T-121", dead=350, la_days=5),
        # Bloat + stale — valid hold → STALE (not none, not bloat)
        row("T-122", dead=350, la_days=40, days_field=2, audit_export="2026-08-01"),
        # Bloat fresh — near-miss status closed → still BLOAT
        row("T-123", dead=320, la_days=6),
        # Bloat fresh — wrong exception_type → BLOAT
        row("T-124", dead=310, la_days=7),
        # Bloat fresh — valid_until == audit → BLOAT
        row("T-125", dead=300, la_days=8),
        # Bloat fresh — alias-only ticket qualifies → none
        row("T-126", dead=330, la_days=4),
        # Autovacuum disabled + tempting hold → still AUTOVACUUM
        row("T-127", dead=50, vac="manual", la_days=3),
        # Bloat + stale — Open ticket then Closed last-wins → STALE
        row("T-128", dead=280, la_days=45, days_field=0),
        # Bloat fresh — Closed then Open last-wins → BLOAT
        row("T-129", dead=290, la_days=5),
        # Small stale bloat with hold → STALE (small tighten 0.35, 0.40 over)
        row("T-130", pages=400, dead=160, size_export="medium", la_days=40, days_field=1),
    ]
    health = health + extra
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(health)
    health_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    # Aliases
    aliases = [
        {"alias": "orders_fact", "table_name": "T-02"},
        {"alias": "billing_agg", "table_name": "T-08"},
        {"alias": "session_dim", "table_name": "T-126"},
        {"alias": "payments_raw", "table_name": "T-14"},
        {"alias": "legacy_t122", "table_name": "T-122"},
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["alias", "table_name"], lineterminator="\n")
    w.writeheader()
    w.writerows(aliases)
    aliases_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    alias_to_table = {a["alias"]: a["table_name"] for a in aliases}

    # Tickets (order matters — last wins per resolved table)
    tickets = [
        # Decoy: would help T-02 but wrong type
        {"ticket_id": "CH-2100", "table_ref": "orders_fact", "exception_type": "REINDEX_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-30"},
        # Valid hold for T-121
        {"ticket_id": "CH-2201", "table_ref": "T-121", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-15"},
        # Valid hold for T-122 via alias → STALE path
        {"ticket_id": "CH-2202", "table_ref": "legacy_t122", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-10-01"},
        # Near-miss lowercase status
        {"ticket_id": "CH-2203", "table_ref": "T-123", "exception_type": "BLOAT_HOLD",
         "status": "closed", "approved": "True", "valid_until": "2026-09-20"},
        # Wrong type
        {"ticket_id": "CH-2204", "table_ref": "T-124", "exception_type": "FREEZE",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-20"},
        # valid_until == audit
        {"ticket_id": "CH-2205", "table_ref": "T-125", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-01"},
        # Alias-only for T-126
        {"ticket_id": "CH-2206", "table_ref": "session_dim", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-18"},
        # Tempting hold on manual-vacuum table — must NOT clear AUTOVACUUM
        {"ticket_id": "CH-2207", "table_ref": "T-127", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-30"},
        # T-128: Open then Closed last-wins
        {"ticket_id": "CH-2208", "table_ref": "T-128", "exception_type": "BLOAT_HOLD",
         "status": "Open", "approved": "True", "valid_until": "2026-09-30"},
        {"ticket_id": "CH-2208b", "table_ref": "T-128", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-30"},
        # T-129: Closed then Open last-wins
        {"ticket_id": "CH-2209", "table_ref": "T-129", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-30"},
        {"ticket_id": "CH-2209b", "table_ref": "T-129", "exception_type": "BLOAT_HOLD",
         "status": "Open", "approved": "True", "valid_until": "2026-09-30"},
        # T-130 small stale+bloat with hold → STALE
        {"ticket_id": "CH-2210", "table_ref": "T-130", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-25"},
        # Also suppress a few existing high-bloat tables to reshape counts
        {"ticket_id": "CH-2211", "table_ref": "T-08", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-12"},
        {"ticket_id": "CH-2212", "table_ref": "billing_agg", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "False", "valid_until": "2026-09-12"},  # unapproved last? wait last for T-08
        # Fix: put unapproved first, approved last for T-08 via alias last
        # Actually reorder: CH-2212 unapproved on billing_agg then we need approved last
    ]
    # Rebuild T-08 tickets cleanly: unapproved then qualifying
    tickets = [t for t in tickets if t["ticket_id"] not in ("CH-2211", "CH-2212")]
    tickets += [
        {"ticket_id": "CH-2211", "table_ref": "T-08", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "False", "valid_until": "2026-09-12"},
        {"ticket_id": "CH-2212", "table_ref": "billing_agg", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-12"},
        # Existing stale+bloat T-50: hold → should become STALE if still stale+would_bloat
        {"ticket_id": "CH-2213", "table_ref": "T-50", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-20"},
        # T-46 RHU bloat fresh: hold → none
        {"ticket_id": "CH-2214", "table_ref": "T-46", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-22"},
        # T-09 amendment bloat: hold → STALE? T-09 is stale 30 + bloat → with hold → STALE
        {"ticket_id": "CH-2215", "table_ref": "T-09", "exception_type": "BLOAT_HOLD",
         "status": "Closed", "approved": "True", "valid_until": "2026-09-28"},
    ]

    buf = io.StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=["ticket_id", "table_ref", "exception_type", "status", "approved", "valid_until"],
        lineterminator="\n",
    )
    w.writeheader()
    w.writerows(tickets)
    tickets_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    def resolve_ref(ref: str) -> str | None:
        if ref.startswith("T-"):
            return ref
        return alias_to_table.get(ref)

    def ticket_qualifies(t: dict) -> bool:
        if t["exception_type"] != "BLOAT_HOLD":
            return False
        if t["status"] != "Closed":
            return False
        if t["approved"].lower() != "true":
            return False
        if date.fromisoformat(t["valid_until"]) <= AUDIT:
            return False
        return True

    # Last ticket per resolved table
    hold_ticket: dict[str, dict] = {}
    for t in tickets:
        tid = resolve_ref(t["table_ref"])
        if tid is None:
            continue
        hold_ticket[tid] = t  # last wins

    has_hold = {tid: ticket_qualifies(t) for tid, t in hold_ticket.items()}

    reindex = list(csv.DictReader(reindex_path.open(encoding="utf-8-sig")))
    reidx: dict[str, dict] = {}
    for r in reindex:
        reidx[r["table_name"]] = r

    by_last: dict[str, dict] = {}
    for r in health:
        by_last[r["table_name"]] = r

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
        raw, size, ratio, stale, stale_days, would_bloat = base_finding(tid, r, reidx)
        held = has_hold.get(tid, False)
        finding = apply_hold(raw, would_bloat, stale, held)
        tinfo = hold_ticket.get(tid)
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
            "_raw": raw,
            "_would_bloat": would_bloat,
            "_held": held,
            "_ticket": tinfo["ticket_id"] if tinfo else None,
            "_ticket_status": tinfo["status"] if tinfo else None,
            "_stale": stale,
        })
    gold_rows.sort(key=lambda g: (g["_la"], g["table_name"]))

    print("HOLD EFFECTS:")
    for g in gold_rows:
        if g["_ticket"] or g["table_name"] >= "T-121":
            print(
                g["table_name"], "raw=", g["_raw"], "held=", g["_held"],
                "final=", g["finding"], "ticket=", g["_ticket"], g["_ticket_status"],
            )

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

    # --- tests patch ---
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

    # Memo map: densify + hold-affected
    memo_map = {}
    for g in gold_rows:
        tid = g["table_name"]
        if g["finding"] == "none":
            continue
        num = int(tid.split("-")[1])
        concepts = [g["finding"], str(g["_dead"]), str(g["_pages"])]
        if g["finding"] == "BLOAT_THRESHOLD_EXCEEDED":
            concepts += [str(g["bloat_ratio"]), "compute"]
            if g["_stale_days"] >= STALE_MIN_DAYS:
                concepts += ["tighten", "stale"]
                if g["size_class"] == "large":
                    concepts.append("0.10")
            if g["_size_export"].lower() == "medium":
                concepts.append("medium")
        elif g["finding"] == "STALE_STATISTICS":
            concepts += [str(g["_stale_days"]), "stale", "days_since_analyze"]
            if g["_held"]:
                concepts += [g["_ticket"], "hold"]
        else:
            concepts += ["manual", "vacuum", "override"]
            if g["_ticket"]:
                concepts += [g["_ticket"], "hold"]
        if g["_held"] and g["finding"] != "AUTOVACUUM_DISABLED":
            # hold changed path into stale
            if g["_ticket"] and g["_ticket"] not in concepts:
                concepts += [g["_ticket"], "hold"]
        # near-miss tickets that still bloat — cite ticket when present and raw was bloat
        if g["_ticket"] and g["finding"] == "BLOAT_THRESHOLD_EXCEEDED" and not g["_held"]:
            concepts += [g["_ticket"], "hold"]
        if num >= 46 or num == 9 or g["_ticket"] or num >= 121:
            memo_map[tid] = concepts

    for name in ("MEMO_V8_STRICT", "MEMO_V9_STRICT", "MEMO_V10_STRICT", "MEMO_V11_STRICT", "MEMO_V12_STRICT"):
        src = re.sub(rf"\n{name} = \{{.*?\n\}}\n", "\n", src, count=1, flags=re.S)
    src = re.sub(r"\n@pytest.mark.parametrize\(\"table_id\", sorted\(MEMO_V\d+_STRICT.*?\n", "\n", src, flags=re.S)
    for fn in (
        "test_memo_v8_strict_local_evidence",
        "test_memo_v9_strict_local_evidence",
        "test_memo_v10_strict_local_evidence",
        "test_memo_v11_strict_local_evidence",
        "test_memo_v12_strict_local_evidence",
        "test_ignores_dashboard_suggested_findings",
        "test_applies_policy_amendment_boundary",
        "test_vacuum_type_case_sensitive_manual",
        "test_ignores_export_audit_date_column",
        "test_change_control_hold_multihop",
    ):
        src = re.sub(rf"\ndef {fn}\(.*?(?=\ndef test_|\Z)", "\n", src, count=1, flags=re.S)

    # Add hold/ticket concept patterns if needed — ticket ids match via escape
    embed = "MEMO_V12_STRICT = " + json.dumps(memo_map, indent=4) + "\n"
    block = f'''
{embed}

@pytest.mark.parametrize("table_id", sorted(MEMO_V12_STRICT.keys(), key=lambda t: (len(t), t)))
def test_memo_v12_strict_local_evidence(table_id):
    concepts = MEMO_V12_STRICT[table_id]
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


def test_change_control_hold_multihop():
    """Holds suppress bloat only; stale/autovacuum still apply; near-misses fail closed."""
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    assert by["T-121"]["finding"] == "none"  # hold clears fresh bloat
    assert by["T-122"]["finding"] == "STALE_STATISTICS"  # hold + stale → stale not none
    assert by["T-123"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"  # status closed ≠ Closed
    assert by["T-124"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"  # wrong type
    assert by["T-125"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"  # valid_until == audit
    assert by["T-126"]["finding"] == "none"  # alias ticket
    assert by["T-127"]["finding"] == "AUTOVACUUM_DISABLED"  # hold cannot clear manual
    assert by["T-128"]["finding"] == "STALE_STATISTICS"  # last-wins Closed
    assert by["T-129"]["finding"] == "BLOAT_THRESHOLD_EXCEEDED"  # last-wins Open
    assert by["T-130"]["finding"] == "STALE_STATISTICS"
    assert by["T-09"]["finding"] == "STALE_STATISTICS"  # hold suppressed amendment bloat
    assert by["T-46"]["finding"] == "none"
    assert by["T-08"]["finding"] == "none"  # alias last-wins approved hold


def test_vacuum_type_case_sensitive_manual():
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    assert by["T-93"]["finding"] == "none"
    assert by["T-110"]["finding"] == "AUTOVACUUM_DISABLED"


def test_ignores_export_audit_date_column():
    rows, err = _load_csv()
    assert err is None, err
    by = {{r["table_name"]: r for r in rows}}
    # T-122 poisoned audit_date but still stale vs issued 2026-09-01
    assert by["T-122"]["finding"] == "STALE_STATISTICS"
'''
    src = src.rstrip() + "\n" + block
    src = re.sub(
        r"(@pytest\.mark\.parametrize\(\"table_id\", sorted\(MEMO_V\d+_STRICT[^)]*\)\)\s*)+\n(?=MEMO_V12_STRICT)",
        "",
        src,
    )
    # concept pattern for hold
    if 'if low == "hold":' not in src:
        src = src.replace(
            'if low == "medium":\n        return r"\\bmedium\\b"',
            'if low == "medium":\n        return r"\\bmedium\\b"\n'
            '    if low == "hold":\n'
            '        return r"\\bhold(?:s|ing)?\\b|change[\\s-]?control|ticket"\n'
            '    if low == "ticket":\n'
            '        return r"\\bticket\\b|change[\\s-]?control|\\bhold(?:s|ing)?\\b"',
        )
    tests_path.write_text(src, encoding="utf-8", newline="\n")

    # --- memo ---
    old = memo_path.read_text(encoding="utf-8")
    # keep header table will rebuild
    flagged = [g for g in gold_rows if g["finding"] != "none"]
    compliant = [g for g in gold_rows if g["finding"] == "none"]
    header = [
        f"# Table maintenance audit — {len(gold_rows)} unique tables",
        "",
        f"{len(gold_rows)} unique tables under DBOPS-31-A + ops bulletin OB-31-C "
        f"(issued audit date 2026-09-01). {len(compliant)} compliant, {len(flagged)} flagged. "
        f"Change-control BLOAT_HOLD tickets suppress bloat only; stale and autovacuum still apply.",
        "",
        "| Table | Size class | Bloat ratio | Finding |",
        "|---|---|---|---|",
    ]
    for g in gold_rows:
        header.append(f"| {g['table_name']} | {g['size_class']} | {g['bloat_ratio']} | {g['finding']} |")
    header.append("")

    # Preserve older graded baseline sections if present
    old_body = re.sub(r"(?s)^# Table maintenance audit.*?\n## ", "## ", old, count=1)
    if old_body.startswith("#"):
        parts = old.split("\n## ", 1)
        old_body = ("## " + parts[1]) if len(parts) == 2 else old
    for section in (
        "Densify traps", "Cap-equality compliance", "Dashboard decoy",
        "Policy amendment", "Change-control",
    ):
        old_body = re.sub(rf"\n## {section}.*", "\n", old_body, count=1, flags=re.S)
    for i in list(range(9, 10)) + list(range(45, 140)):
        old_body = re.sub(rf"\n- \*\*T-{i}\*\*:.*?(?=\n- \*\*|\n## |\Z)", "\n", old_body, flags=re.S)
    old_body = re.sub(r"\n## Densify trap T-45\n.*?(?=\n## |\Z)", "\n", old_body, count=1, flags=re.S)

    dens = [
        "",
        "## Policy amendment and ops bulletin",
        "",
        "Issued audit date 2026-09-01. Apply `policy_amendment_2026-08-20.md` and "
        "`ops_bulletin.md`. Qualifying Closed BLOAT_HOLD tickets suppress bloat only.",
        "",
        "## Densify traps (full matrix and change-control edges)",
        "",
    ]
    for g in flagged:
        tid = g["table_name"]
        num = int(tid.split("-")[1])
        if not (num >= 45 or num == 9 or g["_ticket"] or num >= 121):
            continue
        dead, pages, ratio, finding = g["_dead"], g["_pages"], g["bloat_ratio"], g["finding"]
        stale_days = g["_stale_days"]
        if finding == "AUTOVACUUM_DISABLED":
            extra = ""
            if g["_ticket"]:
                extra = (
                    f" Ticket {g['_ticket']} is a hold decoy and cannot override the manual "
                    f"vacuum rule."
                )
            dens.append(
                f"- **{tid}**: {tid} has a manual vacuum override because vacuum_type is "
                f"exactly lowercase manual with dead_pages={dead} on total_pages={pages}, so "
                f"the finding is AUTOVACUUM_DISABLED.{extra}"
            )
        elif finding == "STALE_STATISTICS":
            hold_bit = ""
            if g["_held"]:
                hold_bit = (
                    f" Qualifying change-control hold {g['_ticket']} suppressed bloat, but "
                    f"staleness still applies."
                )
            dens.append(
                f"- **{tid}**: {tid} is {stale_days} days stale against issued audit date "
                f"2026-09-01 (ignore days_since_analyze={g['_days_field']}); dead_pages={dead} / "
                f"total_pages={pages} gives ratio {ratio} inside the tightened cap after any "
                f"bloat hold.{hold_bit} Finding: STALE_STATISTICS."
            )
        else:
            bits = [
                f"{tid} computes from dead_pages={dead} and total_pages={pages} "
                f"(round-half-up ratio {ratio}) over its computed {g['size_class']} class after compute"
            ]
            if stale_days >= 30:
                eff = "0.10" if g["size_class"] == "large" else "0.35"
                bits.append(f"{stale_days}d stale so effective cap {eff} and {ratio} exceeds it")
            if g["_ticket"] and not g["_held"]:
                bits.append(
                    f"ticket {g['_ticket']} does not qualify as a Closed BLOAT_HOLD hold "
                    f"(status/type/validity/approval), so bloat stands"
                )
            dens.append(f"- **{tid}**: " + "; ".join(bits) + ". Finding: BLOAT_THRESHOLD_EXCEEDED.")

    # Also explain key none-with-hold tables? Instruction says don't grade none — skip.

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
        "## Change-control holds",
        "",
        "See `ops_bulletin.md`. Holds suppress bloat only; memo cites ticket id + hold/ticket.",
        "",
    ]
    memo_path.write_text("\n".join(header) + "\n" + old_body.lstrip() + "\n".join(dens), encoding="utf-8", newline="\n")

    # Instruction
    instr = instr_path.read_text(encoding="utf-8")
    instr = re.sub(r"\n10\..*", "\n", instr, flags=re.S)
    instr = re.sub(r"\n11\..*", "\n", instr, flags=re.S)
    instr = re.sub(r"\n12\..*", "\n", instr, flags=re.S)
    instr = instr.rstrip() + (
        "\n\n10. Ignore `input/dashboard_suggested_findings.csv` — non-authoritative.\n"
        "11. Apply `input/policy_amendment_2026-08-20.md` and `input/ops_bulletin.md` for this "
        "audit. Change-control tickets in `input/change_control_tickets.csv` (with aliases in "
        "`input/table_aliases.csv`) may suppress a bloat finding only when the bulletin's "
        "qualifying-hold rules are met; they never clear autovacuum or stale findings. Memo "
        "local units must cite each non-`none` table's own `dead_pages` and `total_pages`, and "
        "must cite the ticket id plus hold/ticket wording when a hold (or rejected near-miss "
        "ticket) affects that table's outcome.\n"
    )
    # Soften rule 5 pointer already OK; add hold into task blurb
    if "ops_bulletin" not in instr.split("## Binding")[0]:
        instr = instr.replace(
            "noting that a table under an approved active reindex operation is exempt from the bloat check",
            "noting that a table under an approved active reindex operation is exempt from the bloat check, "
            "and that a qualifying change-control bloat hold (see `ops_bulletin.md`) can suppress a bloat "
            "finding without clearing stale or autovacuum findings",
        )
    instr_path.write_text(instr, encoding="utf-8", newline="\n")

    # Sync solution/files/input
    sol_in = PACK / "solution" / "files" / "input"
    sol_in.mkdir(parents=True, exist_ok=True)
    for src_f in inp.iterdir():
        if src_f.is_file():
            try:
                shutil.copy2(src_f, sol_in / src_f.name)
            except PermissionError:
                pass

    golden = PACK / "solution" / "golden_results.json"
    if golden.is_file():
        golden.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n")

    traj = PACK / "solution" / "golden_trajectory.json"
    traj.write_text(json.dumps({
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "oracle", "version": "harbor-0.21"},
        "steps": [
            {"step_id": 1, "source": "user",
             "message": f"Run monthly table maintenance audit ({len(gold_rows)} tables) with DBOPS-31-A + ops bulletin OB-31-C change-control holds."},
            {"step_id": 2, "source": "oracle",
             "message": f"Installed gold deliverables: bloat_audit.csv ({len(gold_rows)} tables), bloat_memo.md, results.json {results}."},
        ],
    }, indent=2) + "\n", encoding="utf-8", newline="\n")

    print("v12 multi-hop harden complete")


if __name__ == "__main__":
    main()

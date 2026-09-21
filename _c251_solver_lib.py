"""Solver for code-c251 PDF form field conversion audit."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


VALID_REQUIRED = {"True", "true", "TRUE"}
AUDIT_COLS = [
    "field_id",
    "field_name",
    "field_type",
    "required_flag",
    "tab_index",
    "finding",
]


def _trim(value: str | None) -> str:
    return (value or "").strip()


def _is_required_flag(raw: str) -> bool:
    return _trim(raw) in VALID_REQUIRED


def _is_mandatory(raw: str) -> bool:
    return _trim(raw) in VALID_REQUIRED


def _is_signature(field_type: str) -> bool:
    return _trim(field_type) == "signature"


def load_inputs(input_dir: str | Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Load converted and source inventories from input_dir."""
    input_dir = Path(input_dir)
    converted_path = input_dir / "converted_field_inventory.csv"
    source_path = input_dir / "source_form_inventory.csv"

    with converted_path.open(newline="", encoding="utf-8") as f:
        converted_rows = list(csv.DictReader(f))
    with source_path.open(newline="", encoding="utf-8") as f:
        source_rows = list(csv.DictReader(f))
    return converted_rows, source_rows


def _dedupe_last_wins(converted_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep last row per trimmed field_id; preserve first-seen order of field_ids."""
    order: list[str] = []
    by_id: dict[str, dict[str, str]] = {}
    for row in converted_rows:
        fid = _trim(row.get("field_id", ""))
        if fid not in by_id:
            order.append(fid)
        by_id[fid] = row
    return [by_id[fid] for fid in order]


def solve(
    converted_rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Apply FORMS-OPS-5 rules; return audit rows and results.json dict."""
    unique = _dedupe_last_wins(converted_rows)

    # Source lookup by trimmed field_name (last source row wins if duplicates).
    source_by_name: dict[str, dict[str, str]] = {}
    for srow in source_rows:
        name = _trim(srow.get("field_name", ""))
        if name:
            source_by_name[name] = srow

    # Tab-index frequency among unique converted fields (trimmed; blank shares).
    tab_counts = Counter(_trim(r.get("tab_index", "")) for r in unique)

    converted_names = {_trim(r.get("field_name", "")) for r in unique}
    converted_names.discard("")  # blank names do not satisfy source presence

    audit_rows: list[dict[str, str]] = []

    for row in unique:
        fid = _trim(row.get("field_id", ""))
        raw_name = row.get("field_name", "") or ""
        raw_type = row.get("field_type", "") or ""
        raw_req = row.get("required_flag", "") or ""
        raw_tab = row.get("tab_index", "") or ""

        trimmed_name = _trim(raw_name)
        trimmed_tab = _trim(raw_tab)

        finding = "none"

        if not trimmed_name:
            finding = "MISSING_ACCESSIBLE_NAME"
        else:
            src = source_by_name.get(trimmed_name)
            mandatory = bool(src) and _is_mandatory(src.get("mandatory", ""))
            if (
                mandatory
                and not _is_signature(raw_type)
                and not _is_required_flag(raw_req)
            ):
                finding = "MISSING_REQUIRED_FLAG"
            elif tab_counts[trimmed_tab] >= 2:
                finding = "DUPLICATE_TAB_INDEX"

        audit_rows.append(
            {
                "field_id": fid,
                "field_name": raw_name,
                "field_type": _trim(raw_type),  # type is trimmed in gold
                "required_flag": raw_req,
                "tab_index": raw_tab,
                "finding": finding,
            }
        )

    # MISSING_FIELD rows for source names absent from conversion (sorted).
    missing_sources: list[tuple[str, str]] = []
    for srow in source_rows:
        name = _trim(srow.get("field_name", ""))
        if not name:
            continue
        if name not in converted_names:
            missing_sources.append((name, f"MISSING-{name.upper().replace(' ', '_')}"))

    # Deduplicate by trimmed name (keep first source order for name, then sort ids).
    seen_missing: set[str] = set()
    missing_unique: list[tuple[str, str]] = []
    for name, mid in missing_sources:
        if name in seen_missing:
            continue
        seen_missing.add(name)
        missing_unique.append((name, mid))
    missing_unique.sort(key=lambda x: x[1])

    for name, mid in missing_unique:
        audit_rows.append(
            {
                "field_id": mid,
                "field_name": name,
                "field_type": "",
                "required_flag": "",
                "tab_index": "",
                "finding": "MISSING_FIELD",
            }
        )

    counts = Counter(r["finding"] for r in audit_rows)
    results = {
        "flagged_count": sum(1 for r in audit_rows if r["finding"] != "none"),
        "missing_accessible_name_count": counts.get("MISSING_ACCESSIBLE_NAME", 0),
        "missing_required_flag_count": counts.get("MISSING_REQUIRED_FLAG", 0),
        "duplicate_tab_index_count": counts.get("DUPLICATE_TAB_INDEX", 0),
        "missing_field_count": counts.get("MISSING_FIELD", 0),
    }
    return audit_rows, results


def audit_to_csv(audit_rows: list[dict[str, str]]) -> str:
    """Serialize audit rows as unquoted CSV (no extra quoting)."""
    lines = [",".join(AUDIT_COLS)]
    for row in audit_rows:
        lines.append(",".join(row[c] for c in AUDIT_COLS))
    return "\n".join(lines) + "\n"


def _norm_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def compare_to_gold(
    audit_rows: list[dict[str, str]],
    results: dict[str, int],
    gold_dir: str | Path,
) -> dict[str, Any]:
    """Compare audit CSV and results.json to gold (memo ignored)."""
    gold_dir = Path(gold_dir)
    gold_csv = _norm_newlines((gold_dir / "pdf_form_audit.csv").read_text(encoding="utf-8"))
    gold_results = json.loads((gold_dir / "results.json").read_text(encoding="utf-8"))

    got_csv = _norm_newlines(audit_to_csv(audit_rows))
    # Gold may or may not end with trailing newline consistently after normalize.
    if not gold_csv.endswith("\n"):
        gold_csv += "\n"
    if not got_csv.endswith("\n"):
        got_csv += "\n"

    gold_lines = gold_csv.splitlines()
    got_lines = got_csv.splitlines()

    line_diffs: list[str] = []
    max_len = max(len(gold_lines), len(got_lines))
    for i in range(max_len):
        g = gold_lines[i] if i < len(gold_lines) else "<missing>"
        o = got_lines[i] if i < len(got_lines) else "<missing>"
        if g != o:
            line_diffs.append(f"line {i + 1}:\n  gold: {g}\n  got:  {o}")

    results_match = results == gold_results
    results_diff = None if results_match else {"gold": gold_results, "got": results}

    return {
        "audit_match": not line_diffs and len(gold_lines) == len(got_lines),
        "results_match": results_match,
        "gold_audit_rows": len(gold_lines) - 1,  # exclude header
        "got_audit_rows": len(got_lines) - 1,
        "audit_line_diffs": line_diffs,
        "results_diff": results_diff,
    }


def main() -> int:
    pack = Path(
        r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
        r"\qc-out\ework\code-c251-portal\code-c251-pdf-form-field-conversion-audit"
    )
    if len(sys.argv) >= 2:
        pack = Path(sys.argv[1])

    input_dir = pack / "environment" / "input"
    gold_dir = pack / "solution" / "files"

    converted_rows, source_rows = load_inputs(input_dir)
    audit_rows, results = solve(converted_rows, source_rows)
    report = compare_to_gold(audit_rows, results, gold_dir)

    print(json.dumps({"results": results, **report}, indent=2))
    ok = report["audit_match"] and report["results_match"]
    print("MATCH" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

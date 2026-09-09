"""Tighten the-thread R6 Slack recount verifiers for portal PreQC QC1-1/QC1-2."""
from __future__ import annotations

import json
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17"
    r"\this-is-the-very-beginning-of\tasks\cb3_100381"
    r"\the-thread-hands-back-its-own-opener"
)

NORM = (
    "replace(replace(replace(replace(replace(replace(replace(replace(replace("
    "replace(replace(replace(lower(text), char(9),''), char(10),''), char(13),''), "
    "' ',''), '-',''), '_',''), '#',''), '.',''), ',',''), ':',''), '*',''), '`','')"
)
BASE = (
    "SELECT COUNT(*) FROM slack_messages WHERE user = 'UDV94ZXBF0PM' "
    "AND channel = 'CV22RIS8EUFS' AND "
)


def q(*likes: str) -> str:
    parts = [f"{NORM} LIKE '{like}'" for like in likes]
    return BASE + " AND ".join(parts)


# Instruction only requires a line per room + TOTAL — do not require markdown pipes.
TOTAL_Q = q("%total%", "%56%")
FIGURES_Q = q(
    "%generalmeshworkssecurity%",
    "%security095%",
    "%securityv1041%",
    "%securityv3065%",
    "%total%",
    "%56%",
    "%25%",
    "%17%",
    "%11%",
    "%15%",
    "%19%",
)


def patch_manifest(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))

    def upsert_sql(name: str, evidence: str, query: str, why: str) -> None:
        sqls = data.setdefault("sql_verifiers", [])
        for item in sqls:
            if item.get("name") == name:
                item["db_query"] = query
                item["evidence_span"] = evidence
                item.setdefault("metadata", {})["why_justification"] = why
                break
        else:
            sqls.append(
                {
                    "name": name,
                    "requirement_id": "R6",
                    "evidence_span": evidence,
                    "category": "core",
                    "db_query": query,
                    "expected_value": 1,
                    "comparison_type": "greater_or_equal",
                    "target_gym_server": "slack-gym",
                    "metadata": {"why_justification": why},
                }
            )

        states = data.setdefault("verifier_configs", [])
        state_name = f"{name}__state"
        for item in states:
            if item.get("name") == state_name:
                item["sql_query"] = query
                item["evidence_span"] = evidence
                item.setdefault("metadata", {})["why_justification"] = why
                break
        else:
            states.append(
                {
                    "name": state_name,
                    "description": f"gym-state assertion, benchmark-path twin of sql_verifier '{name}'",
                    "requirement_id": "R6",
                    "evidence_span": evidence,
                    "category": "core",
                    "verifier_type": "database_state",
                    "type": "database_state",
                    "weight": 1.0,
                    "target_gym_server": "slack-gym",
                    "sql_query": query,
                    "expected_value": 1,
                    "comparison_type": "greater_or_equal",
                    "metadata": {"why_justification": why},
                }
            )

    upsert_sql(
        "recount_carries_a_total_line",
        "and a TOTAL line",
        TOTAL_Q,
        "Requires a TOTAL line that carries the true combined count (56), not the bare word total.",
    )
    upsert_sql(
        "recount_figures_match_gold",
        "a line per room and a TOTAL line",
        FIGURES_Q,
        "Posted recount must carry gold room counts and TOTAL 56 / 25 / 17, not just room names.",
    )

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("patched", path)


def main() -> None:
    patch_manifest(PACK / "tests" / "manifest.json")
    mirror = PACK / "environment" / "_app" / "tests" / "manifest.json"
    if mirror.exists():
        patch_manifest(mirror)


if __name__ == "__main__":
    main()

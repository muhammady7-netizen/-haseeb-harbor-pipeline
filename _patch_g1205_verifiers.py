"""Patch gen-g1205 verifiers for portal PreQC QC1-1 (memo) + QC1-2 (results.json)."""
from __future__ import annotations

import json
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\OneDrive\Documents\NONC-B1-1002016"
    r"\gen-g1205-meal-prep-cost-claim-recompute-audit"
)
SPEC = PACK / "tests" / "verifier.json"

MEMO_SOURCE = {
    "type": "file",
    "file": {
        "type": "csv",
        "command": "extract_text",
        "arguments": {"path": "recipe_cost_memo.md"},
    },
}


def memo_v(name: str, how: str, why: str, pattern: str) -> dict:
    return {
        "name": name,
        "metadata": {"how_justification": how, "why_justification": why},
        "source": MEMO_SOURCE,
        "assertion": {
            "type": "deterministic",
            "expected": pattern,
            "deterministic": {"path": "$.text", "comparison": "regex_match"},
        },
    }


def main() -> None:
    data = json.loads(SPEC.read_text(encoding="utf-8"))
    out: list[dict] = []
    for v in data["verifiers"]:
        if v["name"] in {
            "memo_mentions_finding_labels",
            "memo_names_excluded_ingredient",
            "memo_covers_r03_exclusion",
        }:
            continue
        if v["name"] == "results_keys_exact":
            v = {
                **v,
                "metadata": {
                    "how_justification": (
                        "Opens results.json as text and requires the five instruction "
                        "keys in listed order with non-negative integer values and no extras."
                    ),
                    "why_justification": (
                        "Rejects reordered keys, negative counts, and undeclared pads."
                    ),
                },
                "assertion": {
                    "type": "deterministic",
                    "expected": (
                        r"(?s)\A\s*\{\s*"
                        r"\"recipe_count\"\s*:\s*\d+\s*,\s*"
                        r"\"flagged_count\"\s*:\s*\d+\s*,\s*"
                        r"\"cost_claim_flagged_count\"\s*:\s*\d+\s*,\s*"
                        r"\"stale_price_flagged_count\"\s*:\s*\d+\s*,\s*"
                        r"\"compliant_count\"\s*:\s*\d+\s*"
                        r"\}\s*\Z"
                    ),
                    "deterministic": {
                        "path": "$.text",
                        "comparison": "regex_match",
                    },
                },
            }
        out.append(v)
        if v["name"] == "memo_exists":
            out.append(
                memo_v(
                    "memo_mentions_finding_labels",
                    "Opens recipe_cost_memo.md and requires the three finding labels from the instruction.",
                    "Empty or generic memos cannot skip explaining COST_CLAIM_INVALID, PRICE_SHEET_STALE, and SERVING_COUNT_MISSING.",
                    r"(?s)(?=.*COST_CLAIM_INVALID)(?=.*PRICE_SHEET_STALE)(?=.*SERVING_COUNT_MISSING)",
                )
            )
            out.append(
                memo_v(
                    "memo_names_excluded_ingredient",
                    "Opens recipe_cost_memo.md and requires the exact pantry-staple ingredient name from the batch file.",
                    "Instruction requires naming the excluded extra ingredient exactly as tagged.",
                    r"(?s)finishing_salt",
                )
            )
    data["verifiers"] = out
    SPEC.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    names = [v["name"] for v in out]
    print("verifiers", len(names))
    for n in names:
        print(" ", n)


if __name__ == "__main__":
    main()

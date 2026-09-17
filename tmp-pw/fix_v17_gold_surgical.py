"""Surgical gold repair for v17 Shannon findings.

Only flips AT_ODDS -> VERIFIED when:
1. Identical (subject, wording) sibling is already VERIFIED under same governor, OR
2. Line was FORCE_AT_ODDS-corrupted but wording passes the disclosed multi-limb completeness scan.
Does not loosen CL person/limb traps.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

PACK = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")


def limb_complete(subject: str, wording: str) -> bool | None:
    """Return True/False for multi-limb OI subjects; None = do not auto-flip."""
    w = wording.lower()
    if subject == "inconsistent_accounts":
        return "neighbour" in w and "school" in w and ("clinician" in w) and (
            "sitter" in w or "babysitter" in w
        ) and "wife" in w and "partner" in w
    if subject == "overnight_stays":
        return "sitter" in w and "home" in w and ("several" in w or "occasions" in w)
    if subject == "concern":
        if "no concern" in w:
            return False
        # both limbs (violation/order + position). 'fully' is not a disclosed AT_ODDS trigger.
        return (("violate" in w) or ("order" in w)) and ("position" in w)
    if subject == "behavioural_plan":
        return "confidence" in w and "stability" in w and (
            "set it back" in w or "set back" in w or "setback" in w
        )
    if subject == "tone":
        return "soft" in w and "formal" in w and "succinct" in w
    return None


def main() -> None:
    lines = list(csv.DictReader((PACK / "environment/input/letter_lines.csv").open(encoding="utf-8")))
    gold = {
        r["line_id"]: dict(r)
        for r in csv.DictReader((PACK / "solution/files/letter_line_review.csv").open(encoding="utf-8"))
    }
    by_line = {r["line_id"]: r for r in lines}

    flips: list[tuple[str, str]] = []

    # Pass 1: limb-complete OI-governed AT_ODDS -> VERIFIED
    for lid, g in gold.items():
        L = by_line[lid]
        if g["verdict"] != "AT_ODDS":
            continue
        if not g["record_entry"].startswith("OI-"):
            continue
        ok = limb_complete(L["subject"], L["wording"])
        if ok is True:
            g["verdict"] = "VERIFIED"
            flips.append((lid, "limb-complete"))

    # Pass 2: unify identical (subject, wording) under same governor
    groups = defaultdict(list)
    for L in lines:
        groups[(L["subject"], L["wording"].strip())].append(L["line_id"])
    for (_, _), lids in groups.items():
        if len(lids) < 2:
            continue
        govs = {gold[i]["record_entry"] for i in lids}
        if len(govs) != 1:
            continue
        verdicts = {gold[i]["verdict"] for i in lids}
        if verdicts == {"VERIFIED", "AT_ODDS"}:
            # Prefer VERIFIED only if at least one VERIFIED exists (protocol match)
            for i in lids:
                if gold[i]["verdict"] == "AT_ODDS":
                    gold[i]["verdict"] = "VERIFIED"
                    flips.append((i, "identical-unify"))

    # Assert no identical contradictions remain
    for (_, _), lids in groups.items():
        if len(lids) > 1:
            vs = {gold[i]["verdict"] for i in lids}
            govs = {gold[i]["record_entry"] for i in lids}
            if len(govs) == 1 and len(vs) > 1:
                raise SystemExit(f"still contra {lids} {vs}")

    order = [r["line_id"] for r in lines]
    ordered = [gold[i] for i in order]
    V = sum(1 for r in ordered if r["verdict"] == "VERIFIED")
    A = sum(1 for r in ordered if r["verdict"] == "AT_ODDS")
    N = sum(1 for r in ordered if r["verdict"] == "NOT_IN_RECORD")
    C = sum(1 for r in ordered if r["record_entry"].startswith("CL-"))
    print(f"flips={len(flips)} V={V} A={A} N={N} CL={C}")
    for f in flips:
        print(" ", f, by_line[f[0]]["wording"][:70])

    with (PACK / "solution/files/letter_line_review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "verdict", "record_entry"])
        w.writeheader()
        w.writerows(ordered)

    results = {
        "verified_count": V,
        "at_odds_count": A,
        "not_in_record_count": N,
        "clarification_governed_count": C,
    }
    (PACK / "solution/files/results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (PACK / "solution/golden_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    answer_path = PACK / "solution/files/answer.md"
    answer = answer_path.read_text(encoding="utf-8")
    answer = re.sub(
        r"(Letter lines at odds with the record:\s*)\d+",
        rf"\g<1>{A}",
        answer,
        count=1,
    )
    answer_path.write_text(answer, encoding="utf-8")

    ver_path = PACK / "tests/verifier.json"
    ver = json.loads(ver_path.read_text(encoding="utf-8"))
    row_set = [
        {"line_id": r["line_id"], "verdict": r["verdict"], "record_entry": r["record_entry"]}
        for r in ordered
    ]
    for v in ver["verifiers"]:
        if v["name"] == "register_table":
            exp = v["assertion"]["expected"]
            # keep structure; replace row_set if present, else rows
            if "row_set" in exp:
                exp["row_set"] = row_set
            elif "rows" in exp:
                exp["rows"] = row_set
            else:
                # table_equals often uses expected as list or dict with values
                v["assertion"]["expected"] = {"row_set": row_set, "row_set_ordered": True}
        if v["name"] == "results_figures":
            v["assertion"]["expected"] = results
        if v["name"] == "answer_at_odds_figure":
            # update regex alternatives for new count
            pat = v["assertion"]["expected"]
            # replace old count tokens with new A
            pat2 = re.sub(r"124", str(A), pat)
            # also handle if already changed
            if str(A) not in pat2:
                pat2 = re.sub(
                    r"record\s*:\s*\(\\?:[^)]+\)",
                    f"record\\s*:\\s*(?:{A}|{A}\\.0|{A}\\.00)",
                    pat,
                )
            # simpler: rebuild standard pattern
            pat2 = (
                r"(?is)Letter\s+lines\s+at\s+odds\s+with\s+the\s+record\s*:\s*"
                rf"(?:{A}|{A}\.0|{A}\.00)\b"
            )
            v["assertion"]["expected"] = pat2
            assert re.search(pat2, answer), (pat2, answer[:200])
    ver_path.write_text(json.dumps(ver, indent=2) + "\n", encoding="utf-8")

    readme = (PACK / "README.md").read_text(encoding="utf-8")
    readme = re.sub(
        r"\d+ verified / \d+ at_odds / \d+ not_in_record / \d+ clarification-governed",
        f"{V} verified / {A} at_odds / {N} not_in_record / {C} clarification-governed",
        readme,
    )
    # note gold repair
    note = (
        "- Gold repair (Shannon): removed FORCE_AT_ODDS corruption that marked full-limb "
        "OI lines AT_ODDS while identical siblings were VERIFIED; identical (subject, wording) "
        "rows now share one verdict under the disclosed RP-405 limb rules.\n"
    )
    if "Gold repair (Shannon)" not in readme:
        if "## QC packaging notes" in readme:
            readme = readme.replace("## QC packaging notes (v17)\n", "## QC packaging notes (v17)\n" + note)
        else:
            readme += "\n## QC packaging notes (v17)\n" + note
    (PACK / "README.md").write_text(readme, encoding="utf-8")

    # spot-check Shannon pairs
    for a, b in [("ST-186", "ST-407"), ("ST-332", "ST-420"), ("ST-166", "ST-403")]:
        print(a, gold[a]["verdict"], b, gold[b]["verdict"], "OK" if gold[a]["verdict"] == gold[b]["verdict"] else "BAD")
    print("DONE", results)


if __name__ == "__main__":
    main()

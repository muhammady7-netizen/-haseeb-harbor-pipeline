"""Diagnose and propose consistent gold for v17 under disclosed RP-401..405."""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

P = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")

# Clarification subjects (from clarification.md headings)
CL = {
    "addressee": "CL-301",
    "request": "CL-302",
    "enclosure": "CL-303",
    "salutation": "CL-304",
    "copies": "CL-305",
    "delivery": "CL-306",
}
# Original subjects
OI = {
    "addressee": "OI-201",
    "right_of_first_refusal": "OI-202",
    "children_named": "OI-203",
    "overnight_stays": "OI-204",
    "inconsistent_accounts": "OI-205",
    "concern": "OI-206",
    "behavioural_plan": "OI-207",
    "request": "OI-208",
    "enclosure": "OI-209",
    "tone": "OI-210",
    "sender_signature": "OI-211",
}

# Canonical positions (simplified matchers) for VERIFIED
VERIFIED_PATTERNS = {
    "OI-206": [
        # both limbs, no "fully", mirrors OI text
        re.compile(r"may not appreciate that .{0,80}violate.{0,40}or the position", re.I),
    ],
    "OI-204": [
        re.compile(r"several occasions both children.{0,40}overnight.{0,40}home or with a sitter", re.I),
    ],
    "OI-210": [
        re.compile(r"soft,? formal and succinct", re.I),
        re.compile(r"softly,? formally and succinctly", re.I),
    ],
    "OI-207": [
        re.compile(r"confidence and stability.{0,40}set (it |back)", re.I),
        re.compile(r"confidence and stability.{0,40}set back", re.I),
    ],
}


def governor(subject: str) -> str:
    if subject in CL:
        return CL[subject]
    if subject in OI:
        return OI[subject]
    return "NONE"


def main() -> None:
    lines = list(csv.DictReader((P / "environment/input/letter_lines.csv").open(encoding="utf-8")))
    gold = {r["line_id"]: r for r in csv.DictReader((P / "solution/files/letter_line_review.csv").open(encoding="utf-8"))}

    # Group identical (subject, wording)
    groups = defaultdict(list)
    for L in lines:
        groups[(L["subject"], L["wording"].strip())].append(L["line_id"])

    print("=== identical (subject, wording) with mixed gold verdicts ===")
    flips = []
    for (subj, wording), lids in sorted(groups.items(), key=lambda x: -len(x[1])):
        vs = {(lid, gold[lid]["verdict"], gold[lid]["record_entry"]) for lid in lids}
        verdicts = {v[1] for v in vs}
        govs = {v[2] for v in vs}
        if len(lids) > 1 and len(verdicts) > 1:
            print(f"\n{subj} x{len(lids)} govs={govs} verdicts={verdicts}")
            for lid in lids:
                print(f"  {lid} {gold[lid]['verdict']} {gold[lid]['record_entry']}")
            print(" ", wording[:120])
            # Prefer VERIFIED if any VERIFIED with matching governor for subject
            g = governor(subj)
            # If any is VERIFIED under correct gov, all should be VERIFIED; else all AT_ODDS
            if any(gold[lid]["verdict"] == "VERIFIED" and gold[lid]["record_entry"] == g for lid in lids):
                target = "VERIFIED"
            elif any(gold[lid]["verdict"] == "VERIFIED" for lid in lids):
                target = "VERIFIED"
            else:
                target = "AT_ODDS"
            for lid in lids:
                if gold[lid]["verdict"] != target or gold[lid]["record_entry"] != g:
                    flips.append((lid, gold[lid]["verdict"], target, gold[lid]["record_entry"], g, "identical-unify"))

    # Also ST-332 should be VERIFIED (exact OI-206 paraphrase) same as ST-420
    print("\n=== ST-332 vs ST-420 ===")
    for lid in ("ST-332", "ST-420"):
        print(lid, gold[lid], lines[[x["line_id"] for x in lines].index(lid)]["wording"][:100] if False else "")

    # Count how many of the 19 GLM-miss rows are in contradiction groups
    glm19 = {
        "ST-106","ST-137","ST-139","ST-163","ST-164","ST-166","ST-169","ST-186","ST-187","ST-188",
        "ST-189","ST-191","ST-221","ST-329","ST-330","ST-331","ST-332","ST-335","ST-338"
    }
    contra_lids = set()
    for (subj, wording), lids in groups.items():
        if len(lids) > 1 and len({gold[l]["verdict"] for l in lids}) > 1:
            contra_lids.update(lids)
    print("\nGLM19 in contradiction groups:", sorted(glm19 & contra_lids))
    print("GLM19 NOT in contradiction groups:", sorted(glm19 - contra_lids))

    # For non-contra GLM19: show if they look protocol-VERIFIED
    print("\n=== GLM19 outside contra (why AT_ODDS?) ===")
    for lid in sorted(glm19 - contra_lids):
        L = next(x for x in lines if x["line_id"] == lid)
        print(f"{lid}|{gold[lid]['verdict']}|{gold[lid]['record_entry']}|subj={L['subject']}")
        print(f"  {L['wording'][:140]}")

    print("\nproposed identical-unify flips:", len(flips))
    for f in flips:
        print(f)


if __name__ == "__main__":
    main()

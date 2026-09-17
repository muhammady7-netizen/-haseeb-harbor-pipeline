"""Fair-fix Shannon gold defects without collapsing difficulty.

Mutate the 19 GLM-cluster lines so each is genuinely incomplete under RP-405
(unique wording vs any VERIFIED sibling). Gold stays AT_ODDS for those rows.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

PACK = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")

# line_id -> new wording that drops a required limb / differs from VERIFIED twins
MUTATIONS = {
    # concern: drop position limb (narrower) — was identical to ST-420 or 'fully'+both
    "ST-106": "I am concerned that Ms Corwin may not fully appreciate that these stays violate the custodial order.",
    "ST-164": "I am concerned that Ms Corwin may not fully appreciate that these stays violate the custodial order.",
    "ST-188": "I am concerned that Ms Corwin may not fully appreciate that these stays violate the custodial order.",
    "ST-331": "I am concerned that Ms Corwin may not fully appreciate that these stays violate the custodial order.",
    "ST-332": "I am concerned she may not appreciate that the stays violate the order.",
    # overnight: home only, no sitter — was identical to ST-403
    "ST-166": "On several occasions both children have stayed overnight at Ms Corwin's home while Mr Adler was away.",
    "ST-191": "On several occasions both children have stayed overnight at Ms Corwin's home while Mr Adler was away.",
    "ST-335": "On several occasions both children have stayed overnight at Ms Corwin's home while Mr Adler was away.",
    # tone: drop succinct — was identical to ST-407 or full three
    "ST-137": "The position is set out softly and formally below.",
    "ST-163": "The position is set out softly and formally below.",
    "ST-186": "Keep the letter soft and formal.",
    "ST-187": "The tone is soft and formal throughout.",
    "ST-221": "Keep the letter soft and formal.",
    "ST-329": "Keep the letter soft and formal.",
    "ST-330": "The tone throughout is soft and formal.",
    # behavioural: drop setback — was matching ST-406
    "ST-139": "Imogen's behavioural plan focuses on confidence and stability.",
    "ST-169": "Imogen's behavioural plan focuses on her confidence and stability.",
    "ST-189": "Imogen's behavioural plan focuses on confidence and stability.",
    "ST-338": "Imogen's behavioural plan focuses on confidence and stability.",
}

# De-meta the placeholder position labels (realism)
POSITION_FIXES = {
    "ST-415": "delivery language on request subject",
    "ST-416": "copies language on addressee subject",
    "ST-417": "salutation language on delivery subject",
    "ST-418": "enclosure language on copies subject",
}


def main() -> None:
    lines = list(csv.DictReader((PACK / "environment/input/letter_lines.csv").open(encoding="utf-8")))
    gold = {
        r["line_id"]: dict(r)
        for r in csv.DictReader((PACK / "solution/files/letter_line_review.csv").open(encoding="utf-8"))
    }

    for L in lines:
        lid = L["line_id"]
        if lid in MUTATIONS:
            L["wording"] = MUTATIONS[lid]
            assert gold[lid]["verdict"] == "AT_ODDS", (lid, gold[lid])
        if lid in POSITION_FIXES:
            L["position"] = POSITION_FIXES[lid]

    # identical (subject, wording) must share verdict
    groups = defaultdict(list)
    for L in lines:
        groups[(L["subject"], L["wording"].strip())].append(L["line_id"])
    contra = []
    for key, lids in groups.items():
        if len(lids) < 2:
            continue
        vs = {gold[i]["verdict"] for i in lids}
        if len(vs) > 1:
            contra.append((key[0], lids, vs))
    if contra:
        raise SystemExit(f"contradictions remain: {contra}")

    # write letter lines
    with (PACK / "environment/input/letter_lines.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "subject", "position", "cited_entry", "wording"])
        w.writeheader()
        w.writerows(lines)

    # gold/results/answer/verifier unchanged counts (still 67/124/39/87)
    V = sum(1 for r in gold.values() if r["verdict"] == "VERIFIED")
    A = sum(1 for r in gold.values() if r["verdict"] == "AT_ODDS")
    N = sum(1 for r in gold.values() if r["verdict"] == "NOT_IN_RECORD")
    C = sum(1 for r in gold.values() if r["record_entry"].startswith("CL-"))
    assert (V, A, N, C) == (67, 124, 39, 87), (V, A, N, C)

    readme = (PACK / "README.md").read_text(encoding="utf-8")
    note = (
        "- Gold/fairness repair (Shannon): the 19-line FORCE_AT_ODDS cluster had identical wording "
        "to VERIFIED siblings (false gold contradictions). Those draft lines were rewritten to drop "
        "a required limb under RP-405 so AT_ODDS is protocol-correct and unique; counts stay "
        "67/124/39/87. Placeholder position labels on ST-415..418 de-meta'd.\n"
    )
    if "Gold/fairness repair (Shannon)" not in readme:
        if "## QC packaging notes (v17)" in readme:
            readme = readme.replace("## QC packaging notes (v17)\n", "## QC packaging notes (v17)\n" + note)
        else:
            readme += "\n## QC packaging notes (v17)\n" + note
    (PACK / "README.md").write_text(readme, encoding="utf-8")

    print("mutated", len(MUTATIONS), "lines; contradictions=0; gold counts", V, A, N, C)
    # show a few before/after uniqueness vs siblings
    for a, b in [("ST-186", "ST-407"), ("ST-332", "ST-420"), ("ST-166", "ST-403")]:
        wa = next(x["wording"] for x in lines if x["line_id"] == a)
        wb = next(x["wording"] for x in lines if x["line_id"] == b)
        print(a, gold[a]["verdict"], "|", wa[:60])
        print(b, gold[b]["verdict"], "|", wb[:60], "| same?" , wa == wb)


if __name__ == "__main__":
    main()

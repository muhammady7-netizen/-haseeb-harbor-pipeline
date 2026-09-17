"""Apply Shannon fix plan wordings exactly (gold counts unchanged)."""
from __future__ import annotations

import csv
from pathlib import Path

PACK = Path("task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")

# (wording, position) — plan table
MUTATIONS = {
    "ST-137": ("Set out the position firmly and at length.", "firm and at length"),
    "ST-163": ("Set out the position firmly and at length.", "firm and at length"),
    "ST-186": ("Keep the letter firm and direct.", "firm and direct"),
    "ST-187": ("The tone throughout is firm and direct.", "firm and direct"),
    "ST-221": ("Keep the letter firm and direct.", "firm and direct"),
    "ST-329": ("Keep the letter firm and direct.", "firm and direct"),
    "ST-330": ("The tone throughout is firm and direct.", "firm and direct"),
    "ST-166": (
        "On several occasions both children have stayed overnight at Ms Corwin's home.",
        "home only no sitter",
    ),
    "ST-191": (
        "On several occasions both children have stayed overnight at Ms Corwin's home.",
        "home only no sitter",
    ),
    "ST-335": (
        "On several occasions both children have stayed overnight at Ms Corwin's home.",
        "home only no sitter",
    ),
    "ST-106": (
        "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order.",
        "violation limb only",
    ),
    "ST-164": (
        "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order.",
        "violation limb only",
    ),
    "ST-188": (
        "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order.",
        "violation limb only",
    ),
    "ST-331": (
        "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order.",
        "violation limb only",
    ),
    "ST-332": (
        "I am concerned she may not appreciate that the stays violate the order.",
        "violation limb only",
    ),
    "ST-139": (
        "Imogen's behavioural plan focuses on confidence, and the stays have set back her progress.",
        "confidence and setback missing stability",
    ),
    "ST-169": (
        "Imogen's behavioural plan focuses on confidence, and the stays have set it back.",
        "confidence and setback missing stability",
    ),
    "ST-189": (
        "Imogen's behavioural plan focuses on confidence, and the stays have set back her progress.",
        "confidence and setback missing stability",
    ),
    "ST-338": (
        "Imogen's behavioural plan focuses on confidence, and the stays have set back her progress.",
        "confidence and setback missing stability",
    ),
    "ST-415": (
        "I am writing to request a meeting with counsel.",
        "meeting request not overnight condition",
    ),
    "ST-416": (
        "Address the letter to the father directly.",
        "father directly not mother's attorney",
    ),
    "ST-417": (
        "Deliver it by email to counsel's office.",
        "email not post",
    ),
    "ST-418": (
        "Copy the father's attorney on this letter.",
        "copy someone not nobody",
    ),
}


def main() -> None:
    path = PACK / "environment/input/letter_lines.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for r in rows:
        if r["line_id"] in MUTATIONS:
            wording, position = MUTATIONS[r["line_id"]]
            r["wording"] = wording
            r["position"] = position
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "subject", "position", "cited_entry", "wording"])
        w.writeheader()
        w.writerows(rows)

    # gold unchanged — verify AT_ODDS on mutated ids
    gold = {
        r["line_id"]: r
        for r in csv.DictReader((PACK / "solution/files/letter_line_review.csv").open(encoding="utf-8"))
    }
    for lid in MUTATIONS:
        assert gold[lid]["verdict"] == "AT_ODDS", (lid, gold[lid])

    V = sum(1 for r in gold.values() if r["verdict"] == "VERIFIED")
    A = sum(1 for r in gold.values() if r["verdict"] == "AT_ODDS")
    N = sum(1 for r in gold.values() if r["verdict"] == "NOT_IN_RECORD")
    C = sum(1 for r in gold.values() if r["record_entry"].startswith("CL-"))
    assert (V, A, N, C) == (67, 124, 39, 87), (V, A, N, C)

    # identical (subject, wording) same verdict
    from collections import defaultdict

    groups = defaultdict(list)
    for r in rows:
        groups[(r["subject"], r["wording"].strip())].append(r["line_id"])
    for (_, _), lids in groups.items():
        if len(lids) > 1:
            vs = {gold[i]["verdict"] for i in lids}
            assert len(vs) == 1, (lids, vs)

    readme = (PACK / "README.md").read_text(encoding="utf-8")
    note = (
        "- All AT_ODDS rows have positions that genuinely differ from the governing entry "
        "(dropped limb, wrong tone, missing place, wrong delivery/copy/addressee). "
        "No identical-wording contradictions under the same subject/governor.\n"
    )
    # replace older shannon note if present
    import re

    readme = re.sub(
        r"- Gold/fairness repair \(Shannon\):[^\n]+\n",
        "",
        readme,
    )
    if "genuinely differ from the governing entry" not in readme:
        if "## QC packaging notes (v17)" in readme:
            readme = readme.replace(
                "## QC packaging notes (v17)\n",
                "## QC packaging notes (v17)\n" + note,
            )
        else:
            readme += "\n## QC packaging notes (v17)\n" + note
    (PACK / "README.md").write_text(readme, encoding="utf-8")

    # review.csv — update Layer 1 package consistency change_made / notes
    rev_path = PACK / "review.csv"
    rev_rows = list(csv.DictReader(rev_path.open(encoding="utf-8")))
    for r in rev_rows:
        if r["review_check"] == "Layer 1 - Package consistency":
            r["status"] = "FIXED_AND_VERIFIED"
            r["review_notes"] = (
                "9 checks; 230 draft lines; gold 67/124/39/87. "
                "Shannon gold-contradiction cluster fixed by rewriting 19 AT_ODDS wordings "
                "(and ST-415..418) so each position genuinely differs from its governing entry "
                "under RP-405; no identical-wording opposite-verdict pairs remain."
            )
            r["change_made"] = (
                "Replaced 19 FORCE_AT_ODDS wordings plus ST-415..418 with genuine limb/tone/place/"
                "delivery/copy mismatches; refreshed position labels; gold verdicts and counts unchanged."
            )
            r["what_to_record"] = "All checks declared; gold consistent with disclosed RP-405"
        if r["review_check"] == "Layer 5 - Verifier coverage and fairness":
            r["status"] = "FIXED_AND_VERIFIED"
            r["change_made"] = (
                (r.get("change_made") or "").rstrip(".")
                + "; removed identical-wording gold contradictions via letter_lines wording repair."
            )
    with rev_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["review_check", "status", "review_notes", "change_made", "what_to_record"],
        )
        w.writeheader()
        for r in rev_rows:
            assert not (r["status"] == "PASS" and (r.get("change_made") or "").strip())
            assert "consistency/requirements.json" not in (r.get("change_made") or "")
            assert "repeat-01..03" not in (r.get("change_made") or "")
            w.writerow(r)

    print("applied", len(MUTATIONS), "plan wordings; gold", V, A, N, C)


if __name__ == "__main__":
    main()

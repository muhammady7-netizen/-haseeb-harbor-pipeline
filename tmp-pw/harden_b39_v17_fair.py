"""v17 fair harden on duplicate: tighten multi-limb OI entries (RP-405 narrower)
so previously VERIFIED 3-limb lines become AT_ODDS unless they carry every limb.

Also add subject/wording-mismatch AT_ODDS under correct governors.
No alias NIR subjects.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path(r"task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v17")
LINES = PACK / "environment/input/letter_lines.csv"
GOLD = PACK / "solution/files/letter_line_review.csv"
OI = PACK / "environment/input/original_instruction.md"

COVERED_CL = {"addressee", "request", "enclosure", "salutation", "copies", "delivery"}
COVERED_OI = {
    "right_of_first_refusal",
    "children_named",
    "overnight_stays",
    "inconsistent_accounts",
    "concern",
    "behavioural_plan",
    "tone",
    "sender_signature",
}
UNCOVERED = {
    "reply_deadline",
    "school_reference",
    "mediation_offer",
    "mediation_terms",
    "legal_fees",
    "court_listing",
    "expert_report",
    "interim_contact",
}

# Rewrite original limbs — fair; protocol still RP-405.
NEW_OI = """# Original instruction — the client's first message

I am Delphine Marr. What follows is what I asked for to begin with, one entry per subject. The subject shown on each entry is the value the draft's `subject` column uses.

## OI-201 `addressee`

Address the letter to the father's attorney.

## OI-202 `right_of_first_refusal`

Say that the father agreed to a right of first refusal: the children are not to be left overnight without him present.

## OI-203 `children_named`

Name both children with their ages.

## OI-204 `overnight_stays`

State that on several occasions both children stayed overnight at her home or with a sitter while the father was away — both places must be mentioned.

## OI-205 `inconsistent_accounts`

Note that the father has called her his wife to the school, the person the child lives with to clinicians, a sitter to me, and his partner to the neighbours.

## OI-206 `concern`

Say I am concerned she may not appreciate that the stays violate the order or the position she has been put in — both limbs.

## OI-207 `behavioural_plan`

Say the behavioural plan is about confidence and stability and the stays have set it back — confidence, stability, and setback all required.

## OI-208 `request`

Ask that neither child remain overnight in her care unless the father is present.

## OI-209 `enclosure`

Say a certified copy of the custodial plan is enclosed.

## OI-210 `tone`

Keep it soft, formal and succinct — all three.

## OI-211 `sender_signature`

Sign it in my own name.
"""

# Force-flip gold for lines that no longer carry every required limb.
FORCE_AT_ODDS_OI = {
    # old 3-audience / missing neighbour limb
    "ST-105",
    "ST-122",
    "ST-130",
    "ST-136",
    "ST-168",
    "ST-193",
    "ST-197",
    "ST-198",
    "ST-224",
    "ST-225",
    "ST-333",
    "ST-334",
    "ST-343",
    "ST-344",
    # overnight missing "or with a sitter" / one place only
    "ST-106",
    "ST-141",
    "ST-166",
    "ST-191",
    "ST-199",
    "ST-227",
    "ST-335",
    "ST-345",
    "ST-346",
    # concern missing a limb
    "ST-138",
    "ST-164",
    "ST-188",
    "ST-195",
    "ST-196",
    "ST-226",
    "ST-331",
    "ST-332",
    "ST-341",
    "ST-342",
    # behavioural plan missing confidence/stability/setback
    "ST-107",
    "ST-139",
    "ST-169",
    "ST-189",
    "ST-201",
    "ST-230",
    "ST-338",
    "ST-351",
    "ST-352",
    # tone missing one of soft/formal/succinct
    "ST-110",
    "ST-119",
    "ST-127",
    "ST-137",
    "ST-145",
    "ST-163",
    "ST-186",
    "ST-187",
    "ST-200",
    "ST-221",
    "ST-229",
    "ST-329",
    "ST-330",
    "ST-349",
    "ST-350",
}

# New full-limb VERIFIED lines + hard traps
NEW = [
    # full 4-audience VERIFIED under OI despite wrong CL cite
    ("ST-401", "inconsistent_accounts", "all four audiences", "CL-303",
     "Mr Adler has described Ms Corwin as his wife to the school, as the person Imogen lives with to her clinicians, as a babysitter to me, and as his partner to the neighbours.",
     "VERIFIED", "OI-205"),
    ("ST-402", "inconsistent_accounts", "all four audiences", "OI-205",
     "The father has called her his wife to the school, the person the child lives with to clinicians, a sitter to me, and his partner to the neighbours.",
     "VERIFIED", "OI-205"),
    # full overnight both places
    ("ST-403", "overnight_stays", "home or sitter both", "CL-306",
     "On several occasions both children have stayed overnight at Ms Corwin's home or with a sitter while Mr Adler was away.",
     "VERIFIED", "OI-204"),
    ("ST-404", "overnight_stays", "home or sitter both", "OI-204",
     "On several occasions both children stayed overnight at her home or with a sitter while the father was away.",
     "VERIFIED", "OI-204"),
    # full concern both limbs
    ("ST-405", "concern", "both limbs", "CL-305",
     "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order, or the position she has been placed in.",
     "VERIFIED", "OI-206"),
    # full behavioural plan
    ("ST-406", "behavioural_plan", "confidence stability setback", "CL-301",
     "Imogen's behavioural plan focuses on confidence and stability, and the stays have set it back.",
     "VERIFIED", "OI-207"),
    # full tone three
    ("ST-407", "tone", "soft formal succinct", "CL-302",
     "Keep the letter soft, formal and succinct.",
     "VERIFIED", "OI-210"),
    # AT_ODDS: missing neighbour only (looks complete otherwise)
    ("ST-408", "inconsistent_accounts", "three without neighbours", "OI-205",
     "Mr Adler has described Ms Corwin as his wife to the school, as the person Imogen lives with to her clinicians, and as a babysitter to me.",
     "AT_ODDS", "OI-205"),
    ("ST-409", "inconsistent_accounts", "three without neighbours", "CL-304",
     "The father has called her his wife to the school, the person the child lives with to clinicians, and a sitter to me.",
     "AT_ODDS", "OI-205"),
    # AT_ODDS: overnight home only (no sitter alternative)
    ("ST-410", "overnight_stays", "home only no sitter", "OI-204",
     "On several occasions both children stayed overnight at Ms Corwin's home while Mr Adler was away.",
     "AT_ODDS", "OI-204"),
    ("ST-411", "overnight_stays", "sitter only no home", "CL-301",
     "On several occasions both children stayed overnight with a sitter while Mr Adler was away.",
     "AT_ODDS", "OI-204"),
    # AT_ODDS: tone soft+formal missing succinct
    ("ST-412", "tone", "soft formal not succinct", "OI-210",
     "Keep the letter soft and formal.",
     "AT_ODDS", "OI-210"),
    ("ST-413", "tone", "formal succinct not soft", "CL-306",
     "The tone is formal and succinct.",
     "AT_ODDS", "OI-210"),
    # AT_ODDS: behavioural confidence+stability missing setback
    ("ST-414", "behavioural_plan", "no setback stated", "OI-207",
     "Imogen's behavioural plan focuses on confidence and stability.",
     "AT_ODDS", "OI-207"),
    # subject/wording mismatch under CL governor
    ("ST-415", "request", "wording is delivery", "OI-208",
     "Send it by post to counsel's office.",
     "AT_ODDS", "CL-302"),
    ("ST-416", "addressee", "wording is copies", "OI-201",
     "Do not copy anyone on this letter.",
     "AT_ODDS", "CL-301"),
    ("ST-417", "delivery", "wording is salutation", "CL-306",
     "Dear Counsel,",
     "AT_ODDS", "CL-306"),
    ("ST-418", "copies", "wording is enclosure", "OI-299",
     "A certified copy of the custodial plan is enclosed.",
     "AT_ODDS", "CL-305"),
    # CL-matching wording but subject is original-only → OI governs; if wording matches OI VERIFIED else AT_ODDS
    ("ST-419", "tone", "soft formal succinct", "CL-304",
     "Keep it soft, formal and succinct.",
     "VERIFIED", "OI-210"),
    ("ST-420", "concern", "both limbs", "CL-301",
     "I am concerned she may not appreciate that the stays violate the order or the position she has been put in.",
     "VERIFIED", "OI-206"),
    # NIR with real-looking cites on uncovered subjects
    ("ST-421", "expert_report", "joint expert", "OI-207",
     "I enclose a joint expert report on Imogen.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-422", "interim_contact", "supervised", "CL-302",
     "Interim contact with Ms Corwin should be supervised only.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-423", "court_listing", "directions 14 days", "OI-204",
     "List the matter for directions within fourteen days.",
     "NOT_IN_RECORD", "NONE"),
]


def sync(rows, gold_ordered):
    order = [r["line_id"] for r in rows]
    V = sum(1 for r in gold_ordered if r["verdict"] == "VERIFIED")
    A = sum(1 for r in gold_ordered if r["verdict"] == "AT_ODDS")
    N = sum(1 for r in gold_ordered if r["verdict"] == "NOT_IN_RECORD")
    C = sum(1 for r in gold_ordered if r["record_entry"].startswith("CL-"))
    results = {
        "verified_count": V,
        "at_odds_count": A,
        "not_in_record_count": N,
        "clarification_governed_count": C,
    }
    (PACK / "solution/files/results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (PACK / "solution/golden_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    answer = f"""# The draft letter weighed against the client's two messages

Letter lines at odds with the record: {A}

The review applies the protocol strictly: where the clarification speaks, it governs even if the draft cites an original entry; where the clarification is silent, the original governs even if the draft cites a clarification id for the wrong subject; fabricated entry ids and subjects neither message covers are not in the record. Verified lines track the governing entry's position in full, including every limb the entry requires. At-odds lines reverse a person, harden the tone, drop a required limb, change delivery away from post, copy someone, or otherwise depart from that governing entry.

ST-104 directs the letter to counsel for the father under the original. The clarification sends it to the mother's attorney, so ST-104 is at odds under CL-301 whatever the draft cites.
"""
    (PACK / "solution/files/answer.md").write_text(answer, encoding="utf-8")

    ver = json.loads((PACK / "tests/verifier.json").read_text(encoding="utf-8"))
    words = {i: w for i, w in {
        90: "ninety", 91: "ninety-one", 92: "ninety-two", 93: "ninety-three", 94: "ninety-four",
        95: "ninety-five", 96: "ninety-six", 97: "ninety-seven", 98: "ninety-eight", 99: "ninety-nine",
        100: "one hundred", 101: "one hundred one", 102: "one hundred two", 103: "one hundred three",
        104: "one hundred four", 105: "one hundred five", 106: "one hundred six", 107: "one hundred seven",
        108: "one hundred eight", 109: "one hundred nine", 110: "one hundred ten", 111: "one hundred eleven",
        112: "one hundred twelve", 113: "one hundred thirteen", 114: "one hundred fourteen",
        115: "one hundred fifteen", 116: "one hundred sixteen", 117: "one hundred seventeen",
        118: "one hundred eighteen", 119: "one hundred nineteen", 120: "one hundred twenty",
        121: "one hundred twenty-one", 122: "one hundred twenty-two", 123: "one hundred twenty-three",
        124: "one hundred twenty-four", 125: "one hundred twenty-five", 126: "one hundred twenty-six",
        127: "one hundred twenty-seven", 128: "one hundred twenty-eight", 129: "one hundred twenty-nine",
        130: "one hundred thirty",
    }.items()}
    for v in ver["verifiers"]:
        if v["name"] == "register_table":
            exp = v["assertion"]["expected"]
            exp["rows"] = {
                r["line_id"]: {"verdict": r["verdict"], "record_entry": r["record_entry"]}
                for r in gold_ordered
            }
            exp["row_set"] = order
            v["metadata"]["how_justification"] = (
                f"Parses letter_line_review.csv with csv.read_rows and applies table_equals: every graded cell of {len(order)} rows plus the full {len(order)}-row population as a row_set lock."
            )
        if v["name"] == "results_figures":
            keys = v["assertion"]["expected"]["keys"]
            keys["verified_count"]["value"] = V
            keys["at_odds_count"]["value"] = A
            keys["not_in_record_count"]["value"] = N
            keys["clarification_governed_count"]["value"] = C
        if v["name"] == "answer_at_odds_figure":
            word = words.get(A, str(A))
            v["assertion"]["expected"] = (
                rf"(?is)Letter\s+lines\s+at\s+odds\s+with\s+the\s+record\s*:\s*(?:{A}|{A}\.0|{A}\.00|{word})\b"
            )
    (PACK / "tests/verifier.json").write_text(json.dumps(ver, indent=2) + "\n", encoding="utf-8")
    readme = (PACK / "README.md").read_text(encoding="utf-8")
    readme = re.sub(r"\d+ draft lines", f"{len(order)} draft lines", readme)
    readme = re.sub(
        r"gold: \d+ verified / \d+ at_odds / \d+ not_in_record / \d+ clarification-governed",
        f"gold: {V} verified / {A} at_odds / {N} not_in_record / {C} clarification-governed",
        readme,
    )
    readme = re.sub(r"table_equals with \d+-row", f"table_equals with {len(order)}-row", readme)
    (PACK / "README.md").write_text(readme, encoding="utf-8")
    pat = next(x["assertion"]["expected"] for x in ver["verifiers"] if x["name"] == "answer_at_odds_figure")
    assert re.search(pat, answer), pat
    print("n", len(gold_ordered), "V", V, "A", A, "N", N, "CL", C)


def main():
    OI.write_text(NEW_OI, encoding="utf-8")

    with LINES.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with GOLD.open(encoding="utf-8", newline="") as f:
        gold = list(csv.DictReader(f))
    gby = {r["line_id"]: dict(r) for r in gold}

    flipped = 0
    for lid in FORCE_AT_ODDS_OI:
        if lid in gby and gby[lid]["verdict"] == "VERIFIED" and gby[lid]["record_entry"].startswith("OI-"):
            gby[lid]["verdict"] = "AT_ODDS"
            flipped += 1
        elif lid in gby and gby[lid]["record_entry"].startswith("OI-"):
            # already AT_ODDS or ensure AT_ODDS
            gby[lid]["verdict"] = "AT_ODDS"

    # Also flip any remaining VERIFIED OI multi-limb subjects that still look incomplete by wording scan
    by_id = {r["line_id"]: r for r in rows}
    for lid, g in list(gby.items()):
        if g["verdict"] != "VERIFIED" or not g["record_entry"].startswith("OI-"):
            continue
        r = by_id.get(lid)
        if not r:
            continue
        w = r["wording"].lower()
        sub = r["subject"]
        bad = False
        if sub == "inconsistent_accounts" and "neighbour" not in w:
            bad = True
        if sub == "overnight_stays" and ("sitter" not in w or "home" not in w):
            bad = True
        if sub == "concern" and not (("violate" in w or "order" in w) and ("position" in w)):
            bad = True
        if sub == "behavioural_plan" and not ("confidence" in w and "stability" in w and ("set" in w or "setback" in w or "set back" in w)):
            bad = True
        if sub == "tone" and not ("soft" in w and "formal" in w and "succinct" in w):
            bad = True
        if bad:
            g["verdict"] = "AT_ODDS"
            flipped += 1

    have = {r["line_id"] for r in rows}
    for lid, subject, position, cited, wording, verdict, entry in NEW:
        if lid in have:
            continue
        rows.append(
            {
                "line_id": lid,
                "subject": subject,
                "position": position,
                "cited_entry": cited,
                "wording": wording,
            }
        )
        gby[lid] = {"line_id": lid, "verdict": verdict, "record_entry": entry}
        have.add(lid)

    rows = [r for r in rows if r["subject"] not in {"delivery_method", "carbon_copy_recipients"}]
    order = [r["line_id"] for r in rows]
    gold_ordered = [gby[i] for i in order]

    for r, g in zip(rows, gold_ordered):
        sub = r["subject"]
        if sub in COVERED_CL:
            assert g["record_entry"].startswith("CL-"), (r["line_id"], sub, g)
            assert g["verdict"] != "NOT_IN_RECORD"
        elif sub in COVERED_OI:
            assert g["record_entry"].startswith("OI-"), (r["line_id"], sub, g)
            assert g["verdict"] != "NOT_IN_RECORD"
        else:
            assert sub in UNCOVERED, (r["line_id"], sub)
            assert g["verdict"] == "NOT_IN_RECORD"

    with LINES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "subject", "position", "cited_entry", "wording"])
        w.writeheader()
        w.writerows(rows)
    with GOLD.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "verdict", "record_entry"])
        w.writeheader()
        w.writerows(gold_ordered)

    sync(rows, gold_ordered)
    print("flipped_to_at_odds", flipped)
    print("v17 fair multi-limb harden ok")


if __name__ == "__main__":
    main()

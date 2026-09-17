"""Aggressive FAIR harden on DUPLICATE pack (v16) — aim ~0/4 without alias NIR gotchas.

Rules (all gold from RP-401..406 + exact subject strings in OI/CL):
- Clarified subjects → always CL-* governor (never OI), cite ignored
- Original-only subjects → always OI-* governor, cite ignored
- Uncovered subjects only: reply_deadline, school_reference, mediation_offer,
  mediation_terms, legal_fees, court_listing, expert_report, interim_contact
- No delivery_method / carbon_copy_recipients aliases
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path(r"task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v16")
LINES = PACK / "environment/input/letter_lines.csv"
GOLD = PACK / "solution/files/letter_line_review.csv"

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

# Dense fair traps. Format: lid, subject, position, cited, wording, verdict, entry
NEW = [
    # ---- RP-401/402 VERIFIED under CL despite OI / wrong / fake cite ----
    ("ST-301", "request", "CL wording exact", "OI-208",
     "Neither child overnight in her care unless the father is present.", "VERIFIED", "CL-302"),
    ("ST-302", "request", "CL wording paraphrase", "OI-211",
     "I ask that neither child remain overnight in Ms Corwin's care unless Mr Adler is present.", "VERIFIED", "CL-302"),
    ("ST-303", "request", "CL wording paraphrase", "OI-299",
     "Neither child should stay overnight with her unless the father is there.", "VERIFIED", "CL-302"),
    ("ST-304", "addressee", "mother's attorney", "OI-201",
     "Address this letter to counsel for Ms Corwin — the mother's attorney.", "VERIFIED", "CL-301"),
    ("ST-305", "addressee", "mother's attorney", "OI-299",
     "The letter goes to Catherine's attorney.", "VERIFIED", "CL-301"),
    ("ST-306", "addressee", "mother's attorney", "OI-210",
     "To counsel for the mother.", "VERIFIED", "CL-301"),
    ("ST-307", "enclosure", "certified copy", "OI-209",
     "A certified copy of the custodial plan is enclosed.", "VERIFIED", "CL-303"),
    ("ST-308", "enclosure", "certified copy", "OI-299",
     "Enclosed: certified copy of the custodial plan.", "VERIFIED", "CL-303"),
    ("ST-309", "salutation", "Dear Counsel", "OI-211",
     "Dear Counsel,", "VERIFIED", "CL-304"),
    ("ST-310", "salutation", "Dear Counsel", "OI-201",
     "Dear Counsel,", "VERIFIED", "CL-304"),
    ("ST-311", "copies", "nobody", "OI-205",
     "Do not copy anyone on this letter.", "VERIFIED", "CL-305"),
    ("ST-312", "copies", "nobody", "OI-299",
     "There is no copy line; nobody is copied.", "VERIFIED", "CL-305"),
    ("ST-313", "delivery", "by post", "OI-204",
     "Send it by post to counsel's office.", "VERIFIED", "CL-306"),
    ("ST-314", "delivery", "by post", "OI-299",
     "The letter is to be posted to the offices of opposing counsel.", "VERIFIED", "CL-306"),
    # ---- RP-401 AT_ODDS under CL (superseded OI position / reverse / wrong channel) ----
    ("ST-315", "addressee", "father's attorney", "OI-201",
     "Address the letter to the father's attorney.", "AT_ODDS", "CL-301"),
    ("ST-316", "addressee", "father's attorney", "CL-301",
     "To counsel for Mr Adler.", "AT_ODDS", "CL-301"),
    ("ST-317", "addressee", "father's attorney", "OI-299",
     "Please send this to Adam's attorney.", "AT_ODDS", "CL-301"),
    ("ST-318", "request", "unless mother present", "OI-208",
     "Neither child overnight in her care unless Ms Corwin is present.", "AT_ODDS", "CL-302"),
    ("ST-319", "request", "father alone overnight ok", "CL-302",
     "Either child may remain overnight in her care even if the father is away.", "AT_ODDS", "CL-302"),
    ("ST-320", "enclosure", "unsigned draft", "OI-209",
     "An unsigned draft of the custodial plan is enclosed.", "AT_ODDS", "CL-303"),
    ("ST-321", "enclosure", "no enclosure", "CL-303",
     "Nothing is enclosed with this letter.", "AT_ODDS", "CL-303"),
    ("ST-322", "salutation", "Dear Mr Adler", "OI-211",
     "Dear Mr Adler,", "AT_ODDS", "CL-304"),
    ("ST-323", "salutation", "Dear Ms Corwin", "CL-304",
     "Dear Ms Corwin,", "AT_ODDS", "CL-304"),
    ("ST-324", "copies", "copy father", "OI-205",
     "Copy: Mr Adler.", "AT_ODDS", "CL-305"),
    ("ST-325", "copies", "copy school", "CL-305",
     "Copy the school for their file.", "AT_ODDS", "CL-305"),
    ("ST-326", "delivery", "by email", "OI-299",
     "Send the letter by email to opposing counsel.", "AT_ODDS", "CL-306"),
    ("ST-327", "delivery", "by courier", "CL-306",
     "Deliver by courier to counsel's office.", "AT_ODDS", "CL-306"),
    ("ST-328", "delivery", "hand delivery", "OI-204",
     "Hand-deliver this letter to counsel.", "AT_ODDS", "CL-306"),
    # ---- RP-403 VERIFIED under OI despite wrong CL cite ----
    ("ST-329", "tone", "soft formal succinct", "CL-301",
     "Keep the letter soft, formal and succinct.", "VERIFIED", "OI-210"),
    ("ST-330", "tone", "soft formal succinct", "CL-306",
     "The tone throughout is soft, formal and succinct.", "VERIFIED", "OI-210"),
    ("ST-331", "concern", "full two-limb", "CL-305",
     "I am concerned that Ms Corwin may not fully appreciate that these stays violate the custodial order, or the position she has been placed in.", "VERIFIED", "OI-206"),
    ("ST-332", "concern", "full two-limb", "CL-302",
     "I am concerned she may not appreciate that the stays violate the order or the position she has been put in.", "VERIFIED", "OI-206"),
    ("ST-333", "inconsistent_accounts", "all three", "CL-303",
     "Mr Adler has described Ms Corwin as his wife to the school, as the person Imogen lives with to her clinicians, and as a babysitter to me.", "VERIFIED", "OI-205"),
    ("ST-334", "inconsistent_accounts", "all three", "CL-304",
     "The father has called her his wife to the school, the person the child lives with to clinicians, and a sitter to me.", "VERIFIED", "OI-205"),
    ("ST-335", "overnight_stays", "several both", "CL-301",
     "On several occasions both children have stayed overnight at Ms Corwin's home or with a sitter while Mr Adler was away.", "VERIFIED", "OI-204"),
    ("ST-336", "children_named", "both with ages", "CL-305",
     "This concerns Noor, aged seven, and Imogen, aged twelve.", "VERIFIED", "OI-203"),
    ("ST-337", "right_of_first_refusal", "father agreed", "CL-306",
     "Mr Adler agreed to a right of first refusal, so the children are not to be left overnight without him present.", "VERIFIED", "OI-202"),
    ("ST-338", "behavioural_plan", "set back", "CL-302",
     "Imogen's behavioural plan focuses on confidence and stability, and the stays have set back her progress.", "VERIFIED", "OI-207"),
    ("ST-339", "sender_signature", "own name", "CL-303",
     "Yours sincerely, Delphine Marr.", "VERIFIED", "OI-211"),
    ("ST-340", "sender_signature", "own name", "CL-301",
     "Signed, Delphine Marr.", "VERIFIED", "OI-211"),
    # ---- RP-405 AT_ODDS under OI (narrower / reverse / different person) ----
    ("ST-341", "concern", "violation limb only", "OI-206",
     "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order.", "AT_ODDS", "OI-206"),
    ("ST-342", "concern", "position limb only", "CL-305",
     "I am concerned about the position Ms Corwin has been placed in.", "AT_ODDS", "OI-206"),
    ("ST-343", "inconsistent_accounts", "wife only", "OI-205",
     "Mr Adler has described Ms Corwin as his wife to the school.", "AT_ODDS", "OI-205"),
    ("ST-344", "inconsistent_accounts", "sitter and clinicians", "CL-301",
     "Mr Adler has described Ms Corwin as the person Imogen lives with to clinicians and as a babysitter to me.", "AT_ODDS", "OI-205"),
    ("ST-345", "overnight_stays", "one child once", "OI-204",
     "On one occasion Imogen stayed overnight at Ms Corwin's home while Mr Adler was away.", "AT_ODDS", "OI-204"),
    ("ST-346", "overnight_stays", "Noor only several", "CL-306",
     "On several occasions Noor stayed overnight at Ms Corwin's home while Mr Adler was away.", "AT_ODDS", "OI-204"),
    ("ST-347", "children_named", "Noor only", "OI-203",
     "This concerns Noor, aged seven.", "AT_ODDS", "OI-203"),
    ("ST-348", "children_named", "both no ages", "CL-304",
     "This concerns Noor and Imogen.", "AT_ODDS", "OI-203"),
    ("ST-349", "tone", "firm detailed", "OI-210",
     "I set out the position firmly and in full detail.", "AT_ODDS", "OI-210"),
    ("ST-350", "tone", "soft but not succinct", "CL-302",
     "The tone is soft and formal, and the facts are set out at length.", "AT_ODDS", "OI-210"),
    ("ST-351", "behavioural_plan", "no setback", "OI-207",
     "The stays have not affected Imogen's behavioural plan.", "AT_ODDS", "OI-207"),
    ("ST-352", "behavioural_plan", "confidence only", "CL-303",
     "Imogen's behavioural plan focuses on confidence.", "AT_ODDS", "OI-207"),
    ("ST-353", "right_of_first_refusal", "mother agreed", "OI-202",
     "Ms Corwin agreed to a right of first refusal.", "AT_ODDS", "OI-202"),
    ("ST-354", "right_of_first_refusal", "no overnight restriction", "CL-305",
     "Mr Adler agreed to a right of first refusal, but overnight stays without him are still permitted.", "AT_ODDS", "OI-202"),
    ("ST-355", "sender_signature", "signed as counsel", "OI-211",
     "Yours sincerely, for Delphine Marr, solicitor.", "AT_ODDS", "OI-211"),
    # ---- RP-404 truly uncovered (cite may be real — still NIR) ----
    ("ST-356", "reply_deadline", "7 days", "OI-210",
     "Please reply within seven days.", "NOT_IN_RECORD", "NONE"),
    ("ST-357", "reply_deadline", "14 days", "CL-306",
     "A reply within fourteen days is requested.", "NOT_IN_RECORD", "NONE"),
    ("ST-358", "school_reference", "principal", "OI-205",
     "Ms Oduya at the school can confirm the account.", "NOT_IN_RECORD", "NONE"),
    ("ST-359", "school_reference", "attendance", "CL-301",
     "The school has confirmed attendance in writing.", "NOT_IN_RECORD", "NONE"),
    ("ST-360", "mediation_offer", "open", "OI-206",
     "I remain willing to mediate.", "NOT_IN_RECORD", "NONE"),
    ("ST-361", "mediation_terms", "14 days", "CL-302",
     "I propose mediation within fourteen days.", "NOT_IN_RECORD", "NONE"),
    ("ST-362", "legal_fees", "father pays", "OI-201",
     "The father shall bear all legal fees.", "NOT_IN_RECORD", "NONE"),
    ("ST-363", "legal_fees", "shared", "CL-305",
     "Legal fees will be shared equally.", "NOT_IN_RECORD", "NONE"),
    ("ST-364", "court_listing", "directions", "OI-204",
     "Please list the matter for directions within 28 days.", "NOT_IN_RECORD", "NONE"),
    ("ST-365", "court_listing", "urgent hearing", "CL-303",
     "I will seek an urgent hearing if there is no reply.", "NOT_IN_RECORD", "NONE"),
    ("ST-366", "expert_report", "psychologist", "OI-207",
     "A psychologist's report on Imogen is available on request.", "NOT_IN_RECORD", "NONE"),
    ("ST-367", "expert_report", "joint expert", "CL-304",
     "I propose a joint expert on the overnight arrangements.", "NOT_IN_RECORD", "NONE"),
    ("ST-368", "interim_contact", "supervised only", "OI-208",
     "Pending resolution, contact with Ms Corwin should be supervised only.", "NOT_IN_RECORD", "NONE"),
    ("ST-369", "interim_contact", "video calls", "CL-306",
     "Interim contact may continue by video call twice weekly.", "NOT_IN_RECORD", "NONE"),
]


def sync(rows: list[dict], gold_ordered: list[dict]) -> None:
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

The review applies the protocol strictly: where the clarification speaks, it governs even if the draft cites an original entry; where the clarification is silent, the original governs even if the draft cites a clarification id for the wrong subject; fabricated entry ids and subjects neither message covers are not in the record. Verified lines track the governing entry's position in full. At-odds lines reverse a person, harden the tone, narrow a multi-limb instruction, change delivery away from post, copy someone, or otherwise depart from that governing entry.

ST-104 directs the letter to counsel for the father under the original. The clarification sends it to the mother's attorney, so ST-104 is at odds under CL-301 whatever the draft cites.
"""
    (PACK / "solution/files/answer.md").write_text(answer, encoding="utf-8")

    ver = json.loads((PACK / "tests/verifier.json").read_text(encoding="utf-8"))
    words = {
        i: w
        for i, w in {
            60: "sixty", 61: "sixty-one", 62: "sixty-two", 63: "sixty-three", 64: "sixty-four",
            65: "sixty-five", 66: "sixty-six", 67: "sixty-seven", 68: "sixty-eight", 69: "sixty-nine",
            70: "seventy", 71: "seventy-one", 72: "seventy-two", 73: "seventy-three", 74: "seventy-four",
            75: "seventy-five", 76: "seventy-six", 77: "seventy-seven", 78: "seventy-eight", 79: "seventy-nine",
            80: "eighty", 81: "eighty-one", 82: "eighty-two", 83: "eighty-three", 84: "eighty-four",
            85: "eighty-five", 86: "eighty-six", 87: "eighty-seven", 88: "eighty-eight", 89: "eighty-nine",
            90: "ninety", 91: "ninety-one", 92: "ninety-two", 93: "ninety-three", 94: "ninety-four",
            95: "ninety-five", 96: "ninety-six", 97: "ninety-seven", 98: "ninety-eight", 99: "ninety-nine",
            100: "one hundred",
        }.items()
    }
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


def assert_fair(rows: list[dict], gold_ordered: list[dict]) -> None:
    banned = {"delivery_method", "carbon_copy_recipients"}
    for r, g in zip(rows, gold_ordered):
        sub = r["subject"]
        assert sub not in banned, r["line_id"]
        if sub in COVERED_CL:
            assert g["verdict"] != "NOT_IN_RECORD", (r["line_id"], sub)
            assert g["record_entry"].startswith("CL-"), (r["line_id"], sub, g)
        elif sub in COVERED_OI:
            assert g["verdict"] != "NOT_IN_RECORD", (r["line_id"], sub)
            assert g["record_entry"].startswith("OI-"), (r["line_id"], sub, g)
        else:
            assert sub in UNCOVERED, (r["line_id"], sub)
            assert g["verdict"] == "NOT_IN_RECORD" and g["record_entry"] == "NONE"


def main() -> None:
    with LINES.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with GOLD.open(encoding="utf-8", newline="") as f:
        gold = list(csv.DictReader(f))
    gby = {r["line_id"]: r for r in gold}
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

    # strip any leftover alias subjects
    rows = [r for r in rows if r["subject"] not in {"delivery_method", "carbon_copy_recipients"}]
    order = [r["line_id"] for r in rows]
    gold_ordered = [gby[i] for i in order]
    assert_fair(rows, gold_ordered)

    with LINES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "subject", "position", "cited_entry", "wording"])
        w.writeheader()
        w.writerows(rows)
    with GOLD.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "verdict", "record_entry"])
        w.writeheader()
        w.writerows(gold_ordered)

    sync(rows, gold_ordered)
    print("v16 fair harden ok on duplicate pack")


if __name__ == "__main__":
    main()

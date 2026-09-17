"""Aggressive fair harden: densify cite≠governor + narrower + NOT_IN_RECORD traps for ~0/4."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path(r"task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit")
LINES = PACK / "environment/input/letter_lines.csv"
GOLD = PACK / "solution/files/letter_line_review.csv"

# Batch of hard traps. All gold follows RP-401..406 strictly.
NEW = [
    # --- RP-401: clarification subject, wording matches CL, draft cites OI ---
    ("ST-171", "request", "no overnight unless father present", "OI-208",
     "Neither child should remain overnight in her care unless Mr Adler is present.",
     "VERIFIED", "CL-302"),
    ("ST-172", "request", "no overnight unless father present", "OI-208",
     "I ask that neither child remain overnight in Ms Corwin's care unless the father is present.",
     "VERIFIED", "CL-302"),
    ("ST-173", "enclosure", "certified copy", "OI-209",
     "A certified copy of the custodial plan is enclosed with this letter.",
     "VERIFIED", "CL-303"),
    ("ST-174", "enclosure", "certified copy", "OI-209",
     "Enclosed is a certified copy of the custodial plan.",
     "VERIFIED", "CL-303"),
    ("ST-175", "salutation", "Dear Counsel", "OI-211",
     "Dear Counsel,",
     "VERIFIED", "CL-304"),
    ("ST-176", "addressee", "mother's attorney", "OI-201",
     "This letter is addressed to counsel for Ms Corwin.",
     "VERIFIED", "CL-301"),
    ("ST-177", "copies", "copy nobody", "OI-211",
     "Nobody is to be copied on this letter.",
     "VERIFIED", "CL-305"),
    ("ST-178", "delivery", "by post", "OI-210",
     "Send it by post to counsel's office.",
     "VERIFIED", "CL-306"),
    ("ST-179", "delivery", "by post", "OI-204",
     "The letter is to be sent by post to the offices of opposing counsel.",
     "VERIFIED", "CL-306"),
    # --- RP-401 AT_ODDS: clarification governs, wording follows original ---
    ("ST-180", "addressee", "father's attorney", "OI-201",
     "To counsel for Mr Adler.",
     "AT_ODDS", "CL-301"),
    ("ST-181", "addressee", "father's attorney", "CL-301",
     "Addressed to the father's attorney.",
     "AT_ODDS", "CL-301"),
    ("ST-182", "copies", "copied to father", "OI-205",
     "Copy: Mr Adler.",
     "AT_ODDS", "CL-305"),
    ("ST-183", "delivery", "by courier", "OI-299",
     "Deliver by courier to counsel.",
     "AT_ODDS", "CL-306"),
    ("ST-184", "salutation", "Dear Mr Adler", "OI-211",
     "Dear Mr Adler,",
     "AT_ODDS", "CL-304"),
    ("ST-185", "request", "unless mother present", "OI-208",
     "Neither child overnight in her care unless Ms Corwin is present.",
     "AT_ODDS", "CL-302"),
    # --- RP-403: original-only subject, draft cites CL for wrong subject ---
    ("ST-186", "tone", "soft formal succinct", "CL-305",
     "Keep the letter soft, formal and succinct.",
     "VERIFIED", "OI-210"),
    ("ST-187", "tone", "soft formal succinct", "CL-306",
     "The tone is soft, formal and succinct throughout.",
     "VERIFIED", "OI-210"),
    ("ST-188", "concern", "full two-limb concern", "CL-304",
     "I am concerned that Ms Corwin may not fully appreciate that these stays violate the custodial order, or the position she has been placed in.",
     "VERIFIED", "OI-206"),
    ("ST-189", "behavioural_plan", "stays set it back", "CL-304",
     "Imogen's behavioural plan focuses on confidence and stability, and the stays have set back her progress.",
     "VERIFIED", "OI-207"),
    ("ST-190", "children_named", "both with ages", "CL-305",
     "This concerns Noor, aged seven, and Imogen, aged twelve.",
     "VERIFIED", "OI-203"),
    ("ST-191", "overnight_stays", "several occasions both", "CL-302",
     "On several occasions both children have stayed overnight at Ms Corwin's home or with a sitter while Mr Adler was away.",
     "VERIFIED", "OI-204"),
    ("ST-192", "right_of_first_refusal", "father agreed", "CL-303",
     "Mr Adler agreed to a right of first refusal, so the children are not to be left overnight without him present.",
     "VERIFIED", "OI-202"),
    ("ST-193", "inconsistent_accounts", "three audiences", "CL-301",
     "Mr Adler has described Ms Corwin as his wife to the school, as the person Imogen lives with to her clinicians, and as a babysitter to me.",
     "VERIFIED", "OI-205"),
    ("ST-194", "sender_signature", "own name", "CL-306",
     "Yours sincerely, Delphine Marr.",
     "VERIFIED", "OI-211"),
    # --- RP-405 narrower / reverse under correct governor ---
    ("ST-195", "concern", "narrower concern only violation", "OI-206",
     "I am concerned that Ms Corwin may not appreciate that these stays violate the order.",
     "AT_ODDS", "OI-206"),
    ("ST-196", "concern", "narrower concern only position", "OI-206",
     "I am concerned about the position Ms Corwin has been placed in.",
     "AT_ODDS", "OI-206"),
    ("ST-197", "inconsistent_accounts", "wife to school only", "OI-205",
     "Mr Adler has described Ms Corwin as his wife to the school.",
     "AT_ODDS", "OI-205"),
    ("ST-198", "inconsistent_accounts", "sitter to me only", "CL-303",
     "Mr Adler has described Ms Corwin as a babysitter to me.",
     "AT_ODDS", "OI-205"),
    ("ST-199", "overnight_stays", "one child once", "OI-204",
     "On one occasion Imogen stayed overnight at Ms Corwin's home while Mr Adler was away.",
     "AT_ODDS", "OI-204"),
    ("ST-200", "tone", "firm detailed", "CL-302",
     "I set out the position firmly and in full detail.",
     "AT_ODDS", "OI-210"),
    ("ST-201", "behavioural_plan", "no effect", "OI-207",
     "The stays have not affected Imogen's behavioural plan.",
     "AT_ODDS", "OI-207"),
    ("ST-202", "right_of_first_refusal", "mother agreed", "OI-202",
     "Ms Corwin agreed to a right of first refusal.",
     "AT_ODDS", "OI-202"),
    ("ST-203", "children_named", "Noor only", "CL-304",
     "This concerns Noor, aged seven.",
     "AT_ODDS", "OI-203"),
    # --- RP-404 NOT_IN_RECORD with plausible fake ids / off-subjects ---
    ("ST-204", "reply_deadline", "seven days", "OI-299",
     "Please reply within seven days.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-205", "reply_deadline", "fourteen days", "CL-399",
     "A reply within fourteen days is requested.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-206", "school_reference", "principal named", "OI-298",
     "Ms Oduya at the school can confirm the account.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-207", "school_reference", "principal named", "CL-399",
     "The school principal is asked to confirm attendance.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-208", "mediation_offer", "open to mediate", "OI-297",
     "I remain willing to mediate.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-209", "mediation_terms", "mediate in 14 days", "CL-398",
     "I propose mediation within fourteen days.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-210", "legal_fees", "father pays", "OI-296",
     "The father shall bear all legal fees.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-211", "legal_fees", "shared fees", "CL-397",
     "Legal fees will be shared.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-212", "carbon_copy_recipients", "copy children", "OI-295",
     "Copy both children for their records.",
     "NOT_IN_RECORD", "NONE"),
    ("ST-213", "delivery_method", "email counsel", "OI-294",
     "Send the letter by email to opposing counsel.",
     "NOT_IN_RECORD", "NONE"),
]


def main() -> None:
    with LINES.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with GOLD.open(encoding="utf-8", newline="") as f:
        gold = list(csv.DictReader(f))
    have = {r["line_id"] for r in rows}
    gby = {r["line_id"]: r for r in gold}

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

    order = [r["line_id"] for r in rows]
    gold_ordered = [gby[i] for i in order]

    with LINES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "subject", "position", "cited_entry", "wording"])
        w.writeheader()
        w.writerows(rows)
    with GOLD.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "verdict", "record_entry"])
        w.writeheader()
        w.writerows(gold_ordered)

    V = sum(1 for r in gold_ordered if r["verdict"] == "VERIFIED")
    A = sum(1 for r in gold_ordered if r["verdict"] == "AT_ODDS")
    N = sum(1 for r in gold_ordered if r["verdict"] == "NOT_IN_RECORD")
    C = sum(1 for r in gold_ordered if r["record_entry"].startswith("CL-"))
    print("n", len(gold_ordered), "V", V, "A", A, "N", N, "CL", C)

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
        29: "twenty-nine",
        30: "thirty",
        31: "thirty-one",
        32: "thirty-two",
        33: "thirty-three",
        34: "thirty-four",
        35: "thirty-five",
        36: "thirty-six",
        37: "thirty-seven",
        38: "thirty-eight",
        39: "thirty-nine",
        40: "forty",
        41: "forty-one",
        42: "forty-two",
        43: "forty-three",
        44: "forty-four",
        45: "forty-five",
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
        r"letter_lines\.csv \(\d+ draft lines\)",
        f"letter_lines.csv ({len(order)} draft lines)",
        readme,
    )
    readme = re.sub(
        r"gold: \d+ verified / \d+ at_odds / \d+ not_in_record / \d+ clarification-governed",
        f"gold: {V} verified / {A} at_odds / {N} not_in_record / {C} clarification-governed",
        readme,
    )
    readme = re.sub(r"table_equals with \d+-row", f"table_equals with {len(order)}-row", readme)
    (PACK / "README.md").write_text(readme, encoding="utf-8")

    pat = next(x["assertion"]["expected"] for x in ver["verifiers"] if x["name"] == "answer_at_odds_figure")
    assert re.search(pat, answer), pat
    # quick fairness: every gold row has a line
    assert set(order) == set(gby) or set(order).issubset(set(gby))
    print("harden ok; D1 check next via linter")


if __name__ == "__main__":
    main()

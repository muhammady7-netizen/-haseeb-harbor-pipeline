"""Fair harden v15: remove subject-alias NIR gotchas; add only protocol-clear traps.

Unfair (removed/rewritten):
  - delivery_method ≈ delivery → was NOT_IN_RECORD by alias
  - carbon_copy_recipients ≈ copies → same

Fair hardness (kept/added), all gold from RP-401..406 + exact subject match:
  - clarification subject + OI/fake cite + CL-matching wording → VERIFIED under CL
  - clarification subject + OI wording / reverse / wrong channel → AT_ODDS under CL
  - original-only subject + wrong CL cite + OI-matching wording → VERIFIED under OI
  - original-only subject + narrower / reverse / different person → AT_ODDS under OI
  - truly uncovered subjects (reply_deadline, school_reference, mediation_*, legal_fees) → NIR
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path(r"task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit")
LINES = PACK / "environment/input/letter_lines.csv"
GOLD = PACK / "solution/files/letter_line_review.csv"

# Rewrite alias-gotcha rows into fair covered-subject traps.
REWRITES = {
    # was delivery_method / NIR — now delivery email → AT_ODDS under CL-306 (post)
    "ST-118": {
        "line": {
            "line_id": "ST-118",
            "subject": "delivery",
            "position": "sent by email to counsel",
            "cited_entry": "OI-299",
            "wording": "The letter shall be sent by email to opposing counsel.",
        },
        "gold": {"line_id": "ST-118", "verdict": "AT_ODDS", "record_entry": "CL-306"},
    },
    # was carbon_copy_recipients / NIR — now copies to children → AT_ODDS under CL-305
    "ST-128": {
        "line": {
            "line_id": "ST-128",
            "subject": "copies",
            "position": "copied to the children",
            "cited_entry": "OI-299",
            "wording": "A copy of this letter has been provided to both children for their records.",
        },
        "gold": {"line_id": "ST-128", "verdict": "AT_ODDS", "record_entry": "CL-305"},
    },
    # was carbon_copy_recipients / NIR — now copies father → AT_ODDS CL-305
    "ST-212": {
        "line": {
            "line_id": "ST-212",
            "subject": "copies",
            "position": "copy the father",
            "cited_entry": "OI-205",
            "wording": "Copy: Mr Adler.",
        },
        "gold": {"line_id": "ST-212", "verdict": "AT_ODDS", "record_entry": "CL-305"},
    },
    # was delivery_method / NIR — now delivery courier citing real OI-204 → AT_ODDS CL-306
    "ST-213": {
        "line": {
            "line_id": "ST-213",
            "subject": "delivery",
            "position": "by courier",
            "cited_entry": "OI-204",
            "wording": "Deliver this letter by courier to counsel's office.",
        },
        "gold": {"line_id": "ST-213", "verdict": "AT_ODDS", "record_entry": "CL-306"},
    },
}

# New fair traps only — exact covered subjects or clearly uncovered ones.
NEW = [
    # RP-401/402: clarification repeats request; cite OI; wording matches → VERIFIED CL-302
    (
        "ST-214",
        "request",
        "neither child overnight unless father present",
        "OI-208",
        "Neither child overnight in her care unless the father is present.",
        "VERIFIED",
        "CL-302",
    ),
    (
        "ST-215",
        "request",
        "neither child overnight unless father present",
        "OI-202",
        "The request is that neither child remain overnight in her care unless the father is present.",
        "VERIFIED",
        "CL-302",
    ),
    # RP-401 AT_ODDS: clarified subject, wording follows superseded original
    (
        "ST-216",
        "addressee",
        "father's attorney",
        "OI-201",
        "Please address this letter to the father's attorney.",
        "AT_ODDS",
        "CL-301",
    ),
    (
        "ST-217",
        "salutation",
        "Dear Ms Corwin",
        "CL-304",
        "Dear Ms Corwin,",
        "AT_ODDS",
        "CL-304",
    ),
    (
        "ST-218",
        "enclosure",
        "unsigned draft enclosed",
        "OI-209",
        "An unsigned draft of the custodial plan is enclosed.",
        "AT_ODDS",
        "CL-303",
    ),
    (
        "ST-219",
        "copies",
        "copy mother's attorney",
        "CL-305",
        "Copy: counsel for Ms Corwin.",
        "AT_ODDS",
        "CL-305",
    ),
    (
        "ST-220",
        "delivery",
        "hand delivery",
        "CL-306",
        "Hand-deliver the letter to counsel's office.",
        "AT_ODDS",
        "CL-306",
    ),
    # RP-403: original-only; draft cites CL id for another subject; full match → VERIFIED OI
    (
        "ST-221",
        "tone",
        "soft formal succinct",
        "CL-301",
        "Keep the letter soft, formal and succinct.",
        "VERIFIED",
        "OI-210",
    ),
    (
        "ST-222",
        "sender_signature",
        "own name",
        "CL-305",
        "Yours sincerely, Delphine Marr.",
        "VERIFIED",
        "OI-211",
    ),
    (
        "ST-223",
        "right_of_first_refusal",
        "father agreed",
        "CL-306",
        "Mr Adler agreed to a right of first refusal, so the children are not to be left overnight without him present.",
        "VERIFIED",
        "OI-202",
    ),
    # RP-405 narrower / reverse under original-only governor (correct or wrong cite)
    (
        "ST-224",
        "inconsistent_accounts",
        "wife and sitter only",
        "OI-205",
        "Mr Adler has described Ms Corwin as his wife to the school and as a babysitter to me.",
        "AT_ODDS",
        "OI-205",
    ),
    (
        "ST-225",
        "inconsistent_accounts",
        "clinicians only",
        "CL-302",
        "Mr Adler has described Ms Corwin as the person Imogen lives with to her clinicians.",
        "AT_ODDS",
        "OI-205",
    ),
    (
        "ST-226",
        "concern",
        "narrower violation limb only",
        "CL-301",
        "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order.",
        "AT_ODDS",
        "OI-206",
    ),
    (
        "ST-227",
        "overnight_stays",
        "Noor only several times",
        "OI-204",
        "On several occasions Noor stayed overnight at Ms Corwin's home while Mr Adler was away.",
        "AT_ODDS",
        "OI-204",
    ),
    (
        "ST-228",
        "children_named",
        "Imogen only with age",
        "CL-303",
        "This concerns Imogen, aged twelve.",
        "AT_ODDS",
        "OI-203",
    ),
    (
        "ST-229",
        "tone",
        "soft formal but detailed",
        "OI-210",
        "I keep the tone soft and formal, and I set the facts out in full detail.",
        "AT_ODDS",
        "OI-210",
    ),
    (
        "ST-230",
        "behavioural_plan",
        "confidence only no setback",
        "OI-207",
        "Imogen's behavioural plan focuses on confidence.",
        "AT_ODDS",
        "OI-207",
    ),
    # Fake cite on covered subject + matching clarification wording → VERIFIED CL (cite-blind)
    (
        "ST-231",
        "addressee",
        "mother's attorney",
        "OI-299",
        "This letter goes to counsel for Ms Corwin — the mother's attorney.",
        "VERIFIED",
        "CL-301",
    ),
    (
        "ST-232",
        "copies",
        "copy nobody",
        "OI-299",
        "Do not copy anyone on this letter.",
        "VERIFIED",
        "CL-305",
    ),
    (
        "ST-233",
        "salutation",
        "Dear Counsel",
        "OI-299",
        "Dear Counsel,",
        "VERIFIED",
        "CL-304",
    ),
    # Truly uncovered subjects only (no near-aliases of delivery/copies)
    (
        "ST-234",
        "reply_deadline",
        "twenty-one days",
        "OI-210",
        "Please reply within twenty-one days.",
        "NOT_IN_RECORD",
        "NONE",
    ),
    (
        "ST-235",
        "school_reference",
        "attendance letter",
        "CL-306",
        "The school has already confirmed attendance in writing.",
        "NOT_IN_RECORD",
        "NONE",
    ),
    (
        "ST-236",
        "mediation_offer",
        "open to mediate",
        "OI-206",
        "I remain willing to mediate the overnight issue.",
        "NOT_IN_RECORD",
        "NONE",
    ),
    (
        "ST-237",
        "legal_fees",
        "mother pays fees",
        "CL-301",
        "Ms Corwin shall bear the legal fees arising from this letter.",
        "NOT_IN_RECORD",
        "NONE",
    ),
    (
        "ST-238",
        "court_listing",
        "list for directions",
        "OI-204",
        "Please list the matter for directions within 28 days.",
        "NOT_IN_RECORD",
        "NONE",
    ),
]


def sync_artifacts(rows: list[dict], gold_ordered: list[dict]) -> None:
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
        40: "forty",
        41: "forty-one",
        42: "forty-two",
        43: "forty-three",
        44: "forty-four",
        45: "forty-five",
        46: "forty-six",
        47: "forty-seven",
        48: "forty-eight",
        49: "forty-nine",
        50: "fifty",
        51: "fifty-one",
        52: "fifty-two",
        53: "fifty-three",
        54: "fifty-four",
        55: "fifty-five",
        56: "fifty-six",
        57: "fifty-seven",
        58: "fifty-eight",
        59: "fifty-nine",
        60: "sixty",
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
    print("n", len(gold_ordered), "V", V, "A", A, "N", N, "CL", C)


def main() -> None:
    with LINES.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with GOLD.open(encoding="utf-8", newline="") as f:
        gold = list(csv.DictReader(f))
    gby = {r["line_id"]: r for r in gold}
    by_id = {r["line_id"]: r for r in rows}

    for lid, payload in REWRITES.items():
        assert lid in by_id, lid
        by_id[lid] = payload["line"]
        gby[lid] = payload["gold"]

    # rebuild rows in original order with rewrites applied
    rows = [by_id[r["line_id"]] for r in rows]
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

    # drop leftover alias subjects if any remain
    banned = {"delivery_method", "carbon_copy_recipients"}
    rows = [r for r in rows if r["subject"] not in banned]
    order = [r["line_id"] for r in rows]
    gold_ordered = [gby[i] for i in order]

    # fairness asserts
    covered = {
        "addressee",
        "right_of_first_refusal",
        "children_named",
        "overnight_stays",
        "inconsistent_accounts",
        "concern",
        "behavioural_plan",
        "request",
        "enclosure",
        "tone",
        "sender_signature",
        "salutation",
        "copies",
        "delivery",
    }
    uncovered_ok = {
        "reply_deadline",
        "school_reference",
        "mediation_offer",
        "mediation_terms",
        "legal_fees",
        "court_listing",
    }
    for r, g in zip(rows, gold_ordered):
        sub = r["subject"]
        if sub in covered:
            assert g["verdict"] != "NOT_IN_RECORD", (r["line_id"], sub)
            assert g["record_entry"] != "NONE"
            if sub in {
                "addressee",
                "request",
                "enclosure",
                "salutation",
                "copies",
                "delivery",
            }:
                assert g["record_entry"].startswith("CL-"), (r["line_id"], sub, g)
            else:
                assert g["record_entry"].startswith("OI-"), (r["line_id"], sub, g)
        else:
            assert sub in uncovered_ok, (r["line_id"], sub)
            assert g["verdict"] == "NOT_IN_RECORD" and g["record_entry"] == "NONE"

    with LINES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "subject", "position", "cited_entry", "wording"])
        w.writeheader()
        w.writerows(rows)
    with GOLD.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "verdict", "record_entry"])
        w.writeheader()
        w.writerows(gold_ordered)

    sync_artifacts(rows, gold_ordered)
    print("fair harden v15 ok")


if __name__ == "__main__":
    main()

"""v18 MAX fair harden: every remaining fair layer.

Layers applied:
1) Clarification overrides more subjects (tone, behavioural_plan, concern) — RP-401
2) Clarification repeats request (RP-402) already present; keep densified
3) Tighter multi-limb OI for overnight / inconsistent_accounts / children / RoFR / signature
4) Recompute ALL gold from subject+wording classifiers (no stale VERIFIED)
5) Densify every trap class: cite≠governor, wrong-cite VERIFIED, narrower AT_ODDS,
   person-swap, subject≠wording, fake-cite-on-covered, real-cite-on-uncovered NIR
6) No subject-alias NIR (delivery_method / carbon_copy_*)
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path(r"task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit-v18")
LINES = PACK / "environment/input/letter_lines.csv"
GOLD = PACK / "solution/files/letter_line_review.csv"

OI_TEXT = """# Original instruction — the client's first message

I am Delphine Marr. What follows is what I asked for to begin with, one entry per subject. The subject shown on each entry is the value the draft's `subject` column uses.

## OI-201 `addressee`

Address the letter to the father's attorney.

## OI-202 `right_of_first_refusal`

Say that Mr Adler — the father — agreed to a right of first refusal, and that the children are not to be left overnight without him present. Both the agreement and the overnight restriction must appear.

## OI-203 `children_named`

Name both children with their ages: Noor, aged seven, and Imogen, aged twelve. Both names and both ages are required.

## OI-204 `overnight_stays`

State that on several occasions both children stayed overnight at her home or with a sitter while the father was away — both places must be mentioned, both children, and several occasions.

## OI-205 `inconsistent_accounts`

Note that the father has called her his wife to the school, the person the child lives with to clinicians, a sitter to me, and his partner to the neighbours. All four audiences are required.

## OI-206 `concern`

Say I am concerned she may not appreciate that the stays violate the order or the position she has been put in — both limbs. (Superseded wherever the clarification speaks to concern.)

## OI-207 `behavioural_plan`

Say the behavioural plan is about confidence and stability and the stays have set it back — confidence, stability, and setback all required. (Superseded wherever the clarification speaks to behavioural_plan.)

## OI-208 `request`

Ask that neither child remain overnight in her care unless the father is present.

## OI-209 `enclosure`

Say a certified copy of the custodial plan is enclosed.

## OI-210 `tone`

Keep it soft, formal and succinct — all three. (Superseded wherever the clarification speaks to tone.)

## OI-211 `sender_signature`

Sign it in my own name as Delphine Marr — the full name is required; do not sign as counsel or on behalf of anyone else.
"""

CL_TEXT = """# Clarification — the client's later message

What the client added afterwards, one entry per subject. The subject shown on each entry is the value the draft's `subject` column uses; any subject missing here is one the clarification leaves alone.

## CL-301 `addressee`

To be clear: Adam is the father. The letter goes to Catherine's attorney — the mother's attorney — not to Adam's.

## CL-302 `request`

The request stands: neither child overnight in her care unless the father is present.

## CL-303 `enclosure`

Yes, enclose the certified copy of the custodial plan.

## CL-304 `salutation`

Open with Dear Counsel, since the attorney's name is still to be confirmed.

## CL-305 `copies`

Do not copy anyone on it.

## CL-306 `delivery`

Send it by post to counsel's office.

## CL-307 `tone`

Use a firm, formal and brief tone — not soft, and not long-winded.

## CL-308 `behavioural_plan`

The plan is about confidence, stability and peer relations. The stays have set back confidence only — not the whole plan.

## CL-309 `concern`

I am concerned only about the position she has been put in. Do not raise whether she appreciates that the stays violate the order.
"""

CL_SUBJECT = {
    "addressee": "CL-301",
    "request": "CL-302",
    "enclosure": "CL-303",
    "salutation": "CL-304",
    "copies": "CL-305",
    "delivery": "CL-306",
    "tone": "CL-307",
    "behavioural_plan": "CL-308",
    "concern": "CL-309",
}
OI_SUBJECT = {
    "right_of_first_refusal": "OI-202",
    "children_named": "OI-203",
    "overnight_stays": "OI-204",
    "inconsistent_accounts": "OI-205",
    "sender_signature": "OI-211",
    # superseded for governance but still in OI text for history:
    "request": "OI-208",
    "enclosure": "OI-209",
    "addressee": "OI-201",
    "tone": "OI-210",
    "behavioural_plan": "OI-207",
    "concern": "OI-206",
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
    "without_prejudice",
    "hearing_bundle",
}


def has(w: str, *needles: str) -> bool:
    wl = w.lower()
    return all(n.lower() in wl for n in needles)


def any_has(w: str, *needles: str) -> bool:
    wl = w.lower()
    return any(n.lower() in wl for n in needles)


def matches_governor(subject: str, wording: str, governor: str) -> bool:
    w = wording
    if governor == "CL-301":
        # mother's attorney / Catherine / Ms Corwin counsel — not father/Adam/Mr Adler counsel
        mother = any_has(w, "mother", "catherine", "ms corwin", "corwin's attorney", "counsel for ms")
        father = any_has(w, "father", "adam", "mr adler", "adler's attorney", "counsel for mr")
        if mother and not father:
            return True
        if father and not mother:
            return False
        # "counsel for the mother" etc.
        return mother
    if governor == "CL-302":
        return (
            any_has(w, "neither child", "neither of the children", "no child")
            and any_has(w, "overnight", "remain overnight", "stay overnight")
            and any_has(w, "father", "mr adler")
            and not any_has(w, "unless ms corwin", "unless the mother", "unless catherine")
        )
    if governor == "CL-303":
        # "uncertified" contains substring "certified" — require word-boundary certified, reject uncertified
        wl = w.lower()
        return (
            re.search(r"(?<![a-z])certified(?![a-z])", wl) is not None
            and "uncertified" not in wl
            and any_has(w, "custodial plan", "custody plan")
            and any_has(w, "enclos", "enclosed", "enclose")
        )
    if governor == "CL-304":
        return "dear counsel" in w.lower() and "dear mr" not in w.lower() and "dear ms" not in w.lower()
    if governor == "CL-305":
        return any_has(w, "nobody", "no one", "do not copy", "not copy", "no copy") and not any_has(
            w, "copy:", "copy mr", "copy ms", "copy the", "copied to", "copy both", "copy counsel"
        )
    if governor == "CL-306":
        return any_has(w, "post", "posted", "by post") and not any_has(
            w, "email", "courier", "hand-deliver", "hand deliver", "hand delivery"
        )
    if governor == "CL-307":
        # firm + formal + brief; not soft
        return (
            "firm" in w.lower()
            and "formal" in w.lower()
            and any_has(w, "brief", "succinct")
            and "soft" not in w.lower()
        )
    if governor == "CL-308":
        return (
            has(w, "confidence")
            and has(w, "stability")
            and any_has(w, "peer")
            and any_has(w, "confidence only", "set back confidence", "setback confidence")
        )
    if governor == "CL-309":
        # position limb only; must NOT raise order violation appreciation
        pos = any_has(w, "position")
        viol = any_has(w, "violate", "violation", "order")
        return pos and not viol
    if governor == "OI-202":
        # Must state the overnight restriction (not permitted without him). Reversals like
        # "overnight stays without him are still permitted" are AT_ODDS.
        wl = w.lower()
        if any_has(w, "still permitted", "are permitted", "may stay overnight without"):
            return False
        return (
            any_has(w, "right of first refusal")
            and any_has(w, "father", "mr adler")
            and any_has(w, "overnight")
            and any_has(w, "agreed", "agree")
            and ("not" in wl or "without him" in wl or "without the father" in wl)
            and not any_has(w, "ms corwin agreed", "mother agreed")
        )
    if governor == "OI-203":
        return (
            any_has(w, "noor")
            and any_has(w, "imogen")
            and any_has(w, "seven", "7")
            and any_has(w, "twelve", "12")
        )
    if governor == "OI-204":
        return (
            any_has(w, "several")
            and any_has(w, "both children", "both of the children")
            and "home" in w.lower()
            and "sitter" in w.lower()
        )
    if governor == "OI-205":
        return (
            any_has(w, "wife")
            and any_has(w, "school")
            and any_has(w, "clinician", "clinicians")
            and any_has(w, "sitter", "babysitter")
            and any_has(w, "neighbour", "neighbor")
        )
    if governor == "OI-211":
        return (
            any_has(w, "delphine marr")
            and not any_has(w, "for delphine", "solicitor", "on behalf", "counsel for")
        )
    return False


OI_ONLY = {
    "right_of_first_refusal",
    "children_named",
    "overnight_stays",
    "inconsistent_accounts",
    "sender_signature",
}


def classify(subject: str, wording: str) -> tuple[str, str]:
    if subject in CL_SUBJECT:
        gov = CL_SUBJECT[subject]
        ok = matches_governor(subject, wording, gov)
        return ("VERIFIED" if ok else "AT_ODDS"), gov
    if subject in OI_ONLY:
        gov = OI_SUBJECT[subject]
        ok = matches_governor(subject, wording, gov)
        return ("VERIFIED" if ok else "AT_ODDS"), gov
    return "NOT_IN_RECORD", "NONE"


NEW_LINES: list[tuple[str, str, str, str, str]] = [
    # ---- CL-307 tone VERIFIED (firm formal brief) with wrong/OI cites ----
    ("ST-501", "tone", "firm formal brief", "OI-210", "I set the tone as firm, formal and brief."),
    ("ST-502", "tone", "firm formal brief", "OI-299", "Keep it firm, formal and brief throughout."),
    ("ST-503", "tone", "firm formal brief", "CL-307", "The letter is firm, formal and brief."),
    ("ST-504", "tone", "soft formal succinct", "OI-210", "Keep the letter soft, formal and succinct."),
    ("ST-505", "tone", "soft formal", "CL-302", "The tone is soft and formal."),
    ("ST-506", "tone", "firm detailed", "CL-307", "I set out the position firmly and in full detail."),
    # ---- CL-308 behavioural_plan ----
    ("ST-507", "behavioural_plan", "confidence stability peer confidence-only", "OI-207",
     "Imogen's behavioural plan focuses on confidence, stability and peer relations, and the stays have set back confidence only."),
    ("ST-508", "behavioural_plan", "confidence stability peer confidence-only", "CL-301",
     "The plan covers confidence, stability and peer relations; the stays have set back confidence only."),
    ("ST-509", "behavioural_plan", "old full setback", "OI-207",
     "Imogen's behavioural plan focuses on confidence and stability, and the stays have set it back."),
    ("ST-510", "behavioural_plan", "confidence only no peer", "CL-308",
     "Imogen's behavioural plan focuses on confidence, and the stays have set back confidence only."),
    # ---- CL-309 concern ----
    ("ST-511", "concern", "position only", "OI-206",
     "I am concerned about the position Ms Corwin has been placed in."),
    ("ST-512", "concern", "position only", "CL-305",
     "My only concern is the position she has been put in."),
    ("ST-513", "concern", "both limbs old", "OI-206",
     "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order, or the position she has been placed in."),
    ("ST-514", "concern", "violation only", "CL-309",
     "I am concerned that Ms Corwin may not appreciate that these stays violate the custodial order."),
    # ---- CL addressee / request / delivery densify ----
    ("ST-515", "addressee", "mother", "OI-201", "This letter goes to counsel for Ms Corwin — the mother's attorney."),
    ("ST-516", "addressee", "father", "CL-301", "Address the letter to the father's attorney."),
    ("ST-517", "addressee", "father", "OI-299", "To counsel for Mr Adler."),
    ("ST-518", "request", "CL match", "OI-208", "Neither child overnight in her care unless the father is present."),
    ("ST-519", "request", "unless mother", "CL-302", "Neither child overnight in her care unless Ms Corwin is present."),
    ("ST-520", "delivery", "post", "OI-204", "Send it by post to counsel's office."),
    ("ST-521", "delivery", "email", "CL-306", "Send the letter by email to opposing counsel."),
    ("ST-522", "delivery", "courier", "OI-299", "Deliver by courier to counsel's office."),
    ("ST-523", "copies", "nobody", "OI-205", "Do not copy anyone on this letter."),
    ("ST-524", "copies", "copy father", "CL-305", "Copy: Mr Adler."),
    ("ST-525", "enclosure", "certified", "OI-209", "A certified copy of the custodial plan is enclosed."),
    ("ST-526", "enclosure", "unsigned", "CL-303", "An unsigned draft of the custodial plan is enclosed."),
    ("ST-527", "salutation", "Dear Counsel", "OI-211", "Dear Counsel,"),
    ("ST-528", "salutation", "Dear Mr Adler", "CL-304", "Dear Mr Adler,"),
    # ---- OI-only tightened ----
    ("ST-529", "children_named", "both with ages", "CL-301",
     "This concerns Noor, aged seven, and Imogen, aged twelve."),
    ("ST-530", "children_named", "both no ages", "OI-203", "This concerns Noor and Imogen."),
    ("ST-531", "children_named", "Noor only", "CL-304", "This concerns Noor, aged seven."),
    ("ST-532", "right_of_first_refusal", "full", "CL-306",
     "Mr Adler agreed to a right of first refusal, so the children are not to be left overnight without him present."),
    ("ST-533", "right_of_first_refusal", "mother agreed", "OI-202",
     "Ms Corwin agreed to a right of first refusal, so the children are not to be left overnight without her present."),
    ("ST-534", "right_of_first_refusal", "agreement only no overnight", "OI-202",
     "Mr Adler agreed to a right of first refusal."),
    ("ST-535", "overnight_stays", "full", "CL-302",
     "On several occasions both children stayed overnight at her home or with a sitter while the father was away."),
    ("ST-536", "overnight_stays", "home only", "OI-204",
     "On several occasions both children stayed overnight at Ms Corwin's home while Mr Adler was away."),
    ("ST-537", "overnight_stays", "one child", "CL-301",
     "On several occasions Imogen stayed overnight at her home or with a sitter while the father was away."),
    ("ST-538", "inconsistent_accounts", "all four", "CL-303",
     "Mr Adler has described Ms Corwin as his wife to the school, as the person Imogen lives with to her clinicians, as a babysitter to me, and as his partner to the neighbours."),
    ("ST-539", "inconsistent_accounts", "three no neighbour", "OI-205",
     "Mr Adler has described Ms Corwin as his wife to the school, as the person Imogen lives with to her clinicians, and as a babysitter to me."),
    ("ST-540", "sender_signature", "full name", "CL-305", "Yours sincerely, Delphine Marr."),
    ("ST-541", "sender_signature", "as counsel", "OI-211", "Yours sincerely, for Delphine Marr, solicitor."),
    ("ST-542", "sender_signature", "first name only", "CL-302", "Yours sincerely, Delphine."),
    # ---- subject≠wording under CL governors ----
    ("ST-543", "request", "wording delivery", "OI-208", "Send it by post to counsel's office."),
    ("ST-544", "tone", "wording copies", "OI-210", "Do not copy anyone on this letter."),
    ("ST-545", "concern", "wording enclosure", "CL-309", "A certified copy of the custodial plan is enclosed."),
    ("ST-546", "delivery", "wording salutation", "CL-306", "Dear Counsel,"),
    ("ST-547", "behavioural_plan", "wording addressee mother", "OI-207",
     "This letter goes to counsel for Ms Corwin — the mother's attorney."),
    # ---- NIR densify with real-looking cites ----
    ("ST-548", "reply_deadline", "7 days", "OI-210", "Please reply within seven days."),
    ("ST-549", "reply_deadline", "14 days", "CL-307", "A reply within fourteen days is requested."),
    ("ST-550", "school_reference", "principal", "OI-205", "The school principal can confirm the account."),
    ("ST-551", "mediation_offer", "open", "CL-309", "I remain willing to mediate."),
    ("ST-552", "legal_fees", "shared", "OI-201", "Legal fees will be shared equally."),
    ("ST-553", "court_listing", "directions", "CL-306", "List the matter for directions within 28 days."),
    ("ST-554", "expert_report", "joint", "OI-207", "I propose a joint expert on the overnight arrangements."),
    ("ST-555", "interim_contact", "supervised", "CL-302", "Interim contact should be supervised only."),
    ("ST-556", "without_prejudice", "mark letter", "OI-211", "This letter is sent without prejudice."),
    ("ST-557", "hearing_bundle", "bundle index enclosed", "CL-301", "A hearing bundle index is enclosed for the court."),
    # ---- more CL-matching densify ----
    ("ST-558", "tone", "firm formal brief", "OI-201", "Adopt a firm, formal and brief style."),
    ("ST-559", "concern", "position only", "OI-299", "I raise only the position she has been put in."),
    ("ST-560", "behavioural_plan", "full CL match", "OI-299",
     "The behavioural plan covers confidence, stability and peer relations; the stays have set back confidence only."),
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

The review applies the protocol strictly: where the clarification speaks, it governs even if the draft cites an original entry, including tone, behavioural plan and concern as later clarified; where the clarification is silent, the original governs even if the draft cites a clarification id for the wrong subject; fabricated entry ids and subjects neither message covers are not in the record. Verified lines track the governing entry's position in full, including every required limb. At-odds lines reverse a person, keep a superseded soft tone, drop a required limb, change delivery away from post, copy someone, or otherwise depart from that governing entry.

ST-104 directs the letter to counsel for the father under the original. The clarification sends it to the mother's attorney, so ST-104 is at odds under CL-301 whatever the draft cites.
"""
    (PACK / "solution/files/answer.md").write_text(answer, encoding="utf-8")
    ver = json.loads((PACK / "tests/verifier.json").read_text(encoding="utf-8"))
    # numeric fallback in regex always works; word form optional
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
            v["assertion"]["expected"] = (
                rf"(?is)Letter\s+lines\s+at\s+odds\s+with\s+the\s+record\s*:\s*(?:{A}|{A}\.0|{A}\.00)\b"
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
    assert re.search(pat, answer), (pat, answer[:200])
    print("n", len(gold_ordered), "V", V, "A", A, "N", N, "CL", C)


def main():
    (PACK / "environment/input/original_instruction.md").write_text(OI_TEXT, encoding="utf-8")
    (PACK / "environment/input/clarification.md").write_text(CL_TEXT, encoding="utf-8")

    with LINES.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    # drop alias subjects if any
    rows = [r for r in rows if r["subject"] not in {"delivery_method", "carbon_copy_recipients"}]
    have = {r["line_id"] for r in rows}

    for lid, subject, position, cited, wording in NEW_LINES:
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
        have.add(lid)

    gold_ordered = []
    for r in rows:
        verdict, entry = classify(r["subject"], r["wording"])
        gold_ordered.append({"line_id": r["line_id"], "verdict": verdict, "record_entry": entry})

    # fairness asserts
    for r, g in zip(rows, gold_ordered):
        sub = r["subject"]
        if sub in CL_SUBJECT:
            assert g["record_entry"] == CL_SUBJECT[sub], (r["line_id"], sub, g)
            assert g["verdict"] != "NOT_IN_RECORD"
        elif sub in OI_ONLY:
            assert g["record_entry"] == OI_SUBJECT[sub], (r["line_id"], sub, g)
            assert g["verdict"] != "NOT_IN_RECORD"
        else:
            assert sub in UNCOVERED, (r["line_id"], sub)
            assert g == {"line_id": r["line_id"], "verdict": "NOT_IN_RECORD", "record_entry": "NONE"}

    with LINES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "subject", "position", "cited_entry", "wording"])
        w.writeheader()
        w.writerows(rows)
    with GOLD.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "verdict", "record_entry"])
        w.writeheader()
        w.writerows(gold_ordered)

    sync(rows, gold_ordered)

    # layer checklist
    print("layers:")
    print("  CL overrides tone/behavioural_plan/concern: yes (CL-307/308/309)")
    print("  multi-limb OI overnight/accounts/children/RoFR/signature: yes")
    print("  gold recomputed by classifier: yes")
    print("  cite-blind densify + subject≠wording + NIR: yes")
    print("  alias NIR removed: yes")
    print("MAX fair harden v18 done")


if __name__ == "__main__":
    main()

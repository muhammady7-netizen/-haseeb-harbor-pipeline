"""Add harder traps targeting cited_entry-blind and NOT_IN_RECORD mistakes."""
from pathlib import Path
import json, csv, re

PACK = Path(r"task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit")
lines_path = PACK / "environment/input/letter_lines.csv"
gold_path = PACK / "solution/files/letter_line_review.csv"

# Harder traps: (1) wording matches clarification but cites original → VERIFIED under CL
# (2) plausible fake ids → NOT_IN_RECORD
# (3) cite CL for wrong subject while wording matches OI → VERIFIED OI
# (4) subtle reverse / person / narrower AT_ODDS under correct governor
new_lines = [
    dict(line_id="ST-153", subject="request", position="no overnight unless father present", cited_entry="OI-208",
         wording="I ask that neither child remain overnight in Ms Corwin's care unless Mr Adler is present."),
    dict(line_id="ST-154", subject="enclosure", position="certified copy enclosed", cited_entry="OI-209",
         wording="A certified copy of the custodial plan is enclosed."),
    dict(line_id="ST-155", subject="salutation", position="Dear Counsel", cited_entry="OI-211",
         wording="Dear Counsel,"),
    dict(line_id="ST-156", subject="addressee", position="mother's attorney", cited_entry="OI-201",
         wording="To counsel for Ms Corwin."),
    dict(line_id="ST-157", subject="copies", position="copy nobody", cited_entry="OI-205",
         wording="There is no copy line; nobody is copied on this letter."),
    dict(line_id="ST-158", subject="delivery", position="by post", cited_entry="OI-299",
         wording="The letter shall be sent by post to counsel's office."),
    dict(line_id="ST-159", subject="reply_deadline", position="reply in 10 days", cited_entry="OI-299",
         wording="I would be grateful for a reply within ten days."),
    dict(line_id="ST-160", subject="school_reference", position="principal confirms", cited_entry="CL-399",
         wording="The school principal can confirm what was said to the school."),
    dict(line_id="ST-161", subject="mediation_offer", position="open to mediation", cited_entry="OI-298",
         wording="I remain open to mediation if that assists."),
    dict(line_id="ST-162", subject="legal_fees", position="shared costs", cited_entry="CL-399",
         wording="Legal costs shall be shared equally between the parents."),
    dict(line_id="ST-163", subject="tone", position="soft formal succinct", cited_entry="CL-302",
         wording="The position is set out softly, formally and succinctly below."),
    dict(line_id="ST-164", subject="concern", position="full concern both limbs", cited_entry="CL-305",
         wording="I am concerned that Ms Corwin may not fully appreciate that these stays violate the custodial order, or the position she has been placed in."),
    dict(line_id="ST-165", subject="children_named", position="both with ages", cited_entry="CL-301",
         wording="This concerns Noor, aged seven, and Imogen, aged twelve."),
    dict(line_id="ST-166", subject="overnight_stays", position="several occasions both children", cited_entry="CL-306",
         wording="On several occasions both children have stayed overnight at Ms Corwin's home or with a sitter while Mr Adler was away."),
    dict(line_id="ST-167", subject="right_of_first_refusal", position="father agreed", cited_entry="CL-304",
         wording="Mr Adler agreed to a right of first refusal, so the children are not to be left overnight without him present."),
    dict(line_id="ST-168", subject="inconsistent_accounts", position="all three audiences", cited_entry="CL-303",
         wording="Mr Adler has described Ms Corwin as his wife to the school, as the person Imogen lives with to her clinicians, and as a babysitter to me."),
    dict(line_id="ST-169", subject="behavioural_plan", position="stays set it back", cited_entry="CL-301",
         wording="Imogen's behavioural plan focuses on her confidence and stability, and the stays have set it back."),
    dict(line_id="ST-170", subject="sender_signature", position="own name", cited_entry="CL-302",
         wording="Yours sincerely, Delphine Marr."),
]

new_gold = {
    # clarification governs despite OI cite
    "ST-153": ("VERIFIED", "CL-302"),
    "ST-154": ("VERIFIED", "CL-303"),
    "ST-155": ("VERIFIED", "CL-304"),
    "ST-156": ("VERIFIED", "CL-301"),
    "ST-157": ("VERIFIED", "CL-305"),
    # delivery by post cites fake OI-299 but CL-306 governs → VERIFIED CL-306
    "ST-158": ("VERIFIED", "CL-306"),
    # neither record
    "ST-159": ("NOT_IN_RECORD", "NONE"),
    "ST-160": ("NOT_IN_RECORD", "NONE"),
    "ST-161": ("NOT_IN_RECORD", "NONE"),
    "ST-162": ("NOT_IN_RECORD", "NONE"),
    # cite CL for wrong subject; wording matches OI → OI governs
    "ST-163": ("VERIFIED", "OI-210"),
    "ST-164": ("VERIFIED", "OI-206"),
    "ST-165": ("VERIFIED", "OI-203"),
    "ST-166": ("VERIFIED", "OI-204"),
    "ST-167": ("VERIFIED", "OI-202"),
    "ST-168": ("VERIFIED", "OI-205"),
    "ST-169": ("VERIFIED", "OI-207"),
    "ST-170": ("VERIFIED", "OI-211"),
}

with lines_path.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
have = {r["line_id"] for r in rows}
for nl in new_lines:
    if nl["line_id"] not in have:
        rows.append(nl)

with lines_path.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["line_id", "subject", "position", "cited_entry", "wording"])
    w.writeheader()
    w.writerows(rows)

with gold_path.open(encoding="utf-8", newline="") as f:
    gold = list(csv.DictReader(f))
gids = {r["line_id"] for r in gold}
for lid, (v, e) in new_gold.items():
    if lid not in gids:
        gold.append({"line_id": lid, "verdict": v, "record_entry": e})

order = [r["line_id"] for r in rows]
by = {r["line_id"]: r for r in gold}
missing = [i for i in order if i not in by]
if missing:
    raise SystemExit(f"missing gold for {missing}")
gold_ordered = [by[i] for i in order]

with gold_path.open("w", encoding="utf-8", newline="") as f:
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

The greater part of the draft matches what the client asked for and is verified where the wording tracks the governing entry — under the clarification wherever it speaks, even when the draft cites an original entry, and under the original wherever the clarification is silent, even when the draft cites a clarification id for the wrong subject. Lines that reverse overnight conditions, harden the tone, deny concern, change delivery away from post, name only one child, use the wrong salutation, claim the behavioural plan improved, copy the school, deny overnight stays, or otherwise depart from the governing entry are at odds with the record. Draft lines on reply deadlines, school principals, mediation offers and fee-splitting, including those that cite fabricated entry ids, are not in the record.

ST-104 directs the letter to counsel for the father, leaning on the original instruction, which did say so. The clarification sends the letter to the mother's attorney instead, and on a disagreement the clarification prevails whatever the draft cites, so ST-104 is at odds with the record under CL-301.
"""
(PACK / "solution/files/answer.md").write_text(answer, encoding="utf-8")

ver = json.loads((PACK / "tests/verifier.json").read_text(encoding="utf-8"))
words = {
    i: w
    for i, w in {
        16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
        21: "twenty-one", 22: "twenty-two", 23: "twenty-three", 24: "twenty-four",
        25: "twenty-five", 26: "twenty-six", 27: "twenty-seven", 28: "twenty-eight",
        29: "twenty-nine", 30: "thirty", 31: "thirty-one", 32: "thirty-two",
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
print("ok")

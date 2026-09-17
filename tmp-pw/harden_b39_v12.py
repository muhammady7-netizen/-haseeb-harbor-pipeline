from pathlib import Path
import json, csv, re

PACK = Path(r"task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit")
lines_path = PACK / "environment/input/letter_lines.csv"
gold_path = PACK / "solution/files/letter_line_review.csv"

new_lines = [
    dict(
        line_id="ST-143",
        subject="addressee",
        position="the father's attorney",
        cited_entry="CL-301",
        wording="To counsel for Mr Adler.",
    ),
    dict(
        line_id="ST-144",
        subject="request",
        position="no overnight unless the mother is present",
        cited_entry="CL-302",
        wording="I ask that neither child remain overnight in Ms Corwin's care unless Ms Corwin is present.",
    ),
    dict(
        line_id="ST-145",
        subject="tone",
        position="firm and detailed",
        cited_entry="CL-304",
        wording="I set out the position firmly and in full detail below.",
    ),
    dict(
        line_id="ST-146",
        subject="concern",
        position="no concern about the stays",
        cited_entry="OI-206",
        wording="I have no concern that Ms Corwin fails to appreciate the stays.",
    ),
    dict(
        line_id="ST-147",
        subject="delivery",
        position="sent by email",
        cited_entry="CL-306",
        wording="The letter shall be sent by email to counsel.",
    ),
    dict(
        line_id="ST-148",
        subject="children_named",
        position="Noor only",
        cited_entry="OI-203",
        wording="This concerns Noor, aged seven.",
    ),
    dict(
        line_id="ST-149",
        subject="salutation",
        position="Dear Sir or Madam",
        cited_entry="CL-304",
        wording="Dear Sir or Madam,",
    ),
    dict(
        line_id="ST-150",
        subject="behavioural_plan",
        position="stays improved the plan",
        cited_entry="OI-207",
        wording="Imogen's behavioural plan focuses on confidence and stability, and the stays have improved her progress.",
    ),
    dict(
        line_id="ST-151",
        subject="copies",
        position="copied to the school",
        cited_entry="CL-305",
        wording="Copy: the school principal.",
    ),
    dict(
        line_id="ST-152",
        subject="overnight_stays",
        position="never overnight at her home",
        cited_entry="OI-204",
        wording="Neither child has ever stayed overnight at Ms Corwin's home or with a sitter.",
    ),
]

new_gold = {
    "ST-143": ("AT_ODDS", "CL-301"),
    "ST-144": ("AT_ODDS", "CL-302"),
    "ST-145": ("AT_ODDS", "OI-210"),
    "ST-146": ("AT_ODDS", "OI-206"),
    "ST-147": ("AT_ODDS", "CL-306"),
    "ST-148": ("AT_ODDS", "OI-203"),
    "ST-149": ("AT_ODDS", "CL-304"),
    "ST-150": ("AT_ODDS", "OI-207"),
    "ST-151": ("AT_ODDS", "CL-305"),
    "ST-152": ("AT_ODDS", "OI-204"),
}

with lines_path.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
existing = {r["line_id"] for r in rows}
for nl in new_lines:
    if nl["line_id"] not in existing:
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

The greater part of the draft matches what the client asked for and is verified where the wording tracks the governing entry under the clarification wherever it speaks and under the original wherever it does not. Lines that send the letter to the wrong attorney, reverse overnight conditions, harden the tone, deny concern, change delivery away from post, name only one child, use the wrong salutation, claim the behavioural plan improved, copy the school, or deny overnight stays, together with the earlier traps on tone, accounts, courier or hand delivery, and the narrower concern wording, are at odds with the record. Several draft lines cite entries that do not exist or speak to subjects neither message covers, and those are not in the record.

ST-104 directs the letter to counsel for the father, leaning on the original instruction, which did say so. The clarification sends the letter to the mother's attorney instead, and on a disagreement the clarification prevails whatever the draft cites, so ST-104 is at odds with the record under CL-301.
"""
(PACK / "solution/files/answer.md").write_text(answer, encoding="utf-8")

ver_path = PACK / "tests/verifier.json"
ver = json.loads(ver_path.read_text(encoding="utf-8"))
words = {
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    21: "twenty-one",
    22: "twenty-two",
    23: "twenty-three",
    24: "twenty-four",
    25: "twenty-five",
    26: "twenty-six",
    27: "twenty-seven",
    28: "twenty-eight",
    29: "twenty-nine",
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

ver_path.write_text(json.dumps(ver, indent=2) + "\n", encoding="utf-8")

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
print("answer odds match ok")
print("done")

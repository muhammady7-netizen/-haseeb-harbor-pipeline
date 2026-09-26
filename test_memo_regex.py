import re, json
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")
spec = json.loads((ROOT / "tests/verifier.json").read_text(encoding="utf-8"))
memo = (ROOT / "solution/files/campaign_review.md").read_text(encoding="utf-8")

print("=== Gold memo ===")
for v in spec["verifiers"]:
    name = v.get("name", "")
    if name in ("memo_conversion_effect", "memo_counted_placements"):
        pattern = v["assertion"]["expected"]
        match = re.search(pattern, memo)
        print(name + ": " + ("PASS" if match else "FAIL"))
        if match:
            print("  matched: " + match.group()[:80])

print()
print("=== Counterexamples ===")
tests = [
    ("The conversion effect was 38831 streams.", "should PASS"),
    ("Conversion effect: 38831.", "should PASS"),
    ("Counted placements are 114.", "should PASS"),
    ("Counted placements: 114.", "should PASS"),
]
for text, desc in tests:
    for v in spec["verifiers"]:
        name = v.get("name", "")
        if name in ("memo_conversion_effect", "memo_counted_placements"):
            pattern = v["assertion"]["expected"]
            match = re.search(pattern, text)
            if match:
                print(name + " on [" + text[:50] + "]: MATCH (" + desc + ")")

import zipfile, json, os
from pathlib import Path

p = Path(r"C:\Users\Haseeb Mirza\Downloads\UPLOAD-THIS-TO-QC-health-h40.zip")
print("exists", p.exists(), "size", p.stat().st_size if p.exists() else None)
z = zipfile.ZipFile(p)
names = z.namelist()
# find pack root
roots = sorted({n.split("/")[0] for n in names if n.strip()})
print("roots", roots[:5], "nfiles", len(names))
# locate key files
def find(suffix):
    for n in names:
        if n.endswith(suffix):
            return n
    return None

rj = find("solution/files/results.json")
memo = find("solution/files/results_memo.md")
cr = find("environment/input/critical_results.csv")
vj = find("tests/verifier.json")
print("results.json", rj)
print(z.read(rj).decode())
print("critical has R-35", b"R-35" in z.read(cr))
print("memo has R-34", b"R-34" in z.read(memo))
data = json.loads(z.read(vj))
print("verifiers", len(data["verifiers"]))
print("ack breaches expected", next(v["assertion"]["expected"] for v in data["verifiers"] if v["name"]=="result_acknowledgement_breaches"))
print("ward clerk regex", "ward[_\\s-]?clerk" in next(v["assertion"]["expected"] for v in data["verifiers"] if v["name"]=="memo_names_the_unapproved_acknowledgement") or "ward[_\s-]?clerk" in next(v["assertion"]["expected"] for v in data["verifiers"] if v["name"]=="memo_names_the_unapproved_acknowledgement"))
pat = next(v["assertion"]["expected"] for v in data["verifiers"] if v["name"]=="memo_names_the_unapproved_acknowledgement")
print("pat snippet", pat[:120])

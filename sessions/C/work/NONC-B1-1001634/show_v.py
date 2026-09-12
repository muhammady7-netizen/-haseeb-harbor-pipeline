import json
from pathlib import Path
vj = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit\tests\verifier.json")
spec = json.loads(vj.read_text(encoding="utf-8"))
# Show memo checks and CSV checks
for v in spec["verifiers"]:
    name = v["name"]
    exp = v.get("assertion",{}).get("expected","")
    if not isinstance(exp, str):
        exp = str(exp)
    if "memo" in name.lower() or "coherence" in name.lower() or "brief" in name.lower():
        print(f"{name}: {exp[:150]}")

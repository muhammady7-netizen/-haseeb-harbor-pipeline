import json
from pathlib import Path

pack = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\qc-out\ework\UPLOAD-THIS-TO-QC-health-h40"
    r"\health-h40-critical-result-acknowledgement"
)
data = json.loads((pack / "tests" / "verifier.json").read_text(encoding="utf-8-sig"))
for v in data["verifiers"]:
    exp = v["assertion"].get("expected")
    if isinstance(exp, str) and len(exp) > 140:
        exp = exp[:140] + "..."
    print(f"{v['name']}: {v['assertion'].get('operator')}")
    print(f"  {exp}")

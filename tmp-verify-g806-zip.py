import zipfile
import json
from pathlib import Path

z = zipfile.ZipFile(r"C:\Users\Haseeb Mirza\Downloads\UPLOAD-THIS-TO-QC-gen-g806.zip")
for i in range(1, 6):
    names = [n for n in z.namelist() if f"/glm-5.2/r{i}/result.json" in n]
    if not names:
        print(f"r{i} MISSING")
        continue
    r = json.loads(z.read(names[0]))
    print(f"r{i}", r.get("reward"), r.get("judge_provenance"), r.get("overall_pass"))
gt = json.loads(z.read([n for n in z.namelist() if n.endswith("golden_trajectory.json")][0]))
print("GT style_audit", "script_style" in json.dumps(gt))
snaps = [n for n in z.namelist() if "snapshots/app/brief_coherence.csv" in n]
print("snapshot coherence files", len(snaps))
print(
    "synthetic",
    any(b"synthetic-placeholder" in z.read(n) for n in z.namelist() if n.endswith("trajectory.json")),
)
print(
    "verifiers",
    len(json.loads(z.read([n for n in z.namelist() if n.endswith("tests/verifier.json")][0]))["verifiers"]),
)
print("size", Path(r"C:\Users\Haseeb Mirza\Downloads\UPLOAD-THIS-TO-QC-gen-g806.zip").stat().st_size)
# gold move sample
coh = z.read([n for n in z.namelist() if n.endswith("solution/files/brief_coherence.csv")][0]).decode()
print(coh)

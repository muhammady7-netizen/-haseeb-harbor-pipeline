from pathlib import Path
import zipfile
import shutil
import json

pack = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\qc-out\ework\UPLOAD-THIS-TO-QC-health-h40"
    r"\health-h40-critical-result-acknowledgement"
)
ignore = {".DS_Store", "__pycache__", ".git", ".pytest_cache"}
tmp = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
    r"\UPLOAD-THIS-TO-QC-health-h40.zip"
)
if tmp.exists():
    tmp.unlink()
with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in pack.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignore or part.endswith(".pyc") for part in path.parts):
            continue
        if path.name.endswith(".zip"):
            continue
        if ".bak-" in path.name or path.name.endswith(".bak"):
            continue
        arc = (Path(pack.name) / path.relative_to(pack)).as_posix()
        zf.write(path, arcname=arc)
print("built", tmp, tmp.stat().st_size)
z = zipfile.ZipFile(tmp)
rj = json.loads(z.read("health-h40-critical-result-acknowledgement/solution/files/results.json"))
print("results", rj)
print(
    "R-35 in csv",
    b"R-35"
    in z.read(
        "health-h40-critical-result-acknowledgement/environment/input/critical_results.csv"
    ),
)
print(
    "verifiers",
    len(
        json.loads(
            z.read("health-h40-critical-result-acknowledgement/tests/verifier.json")
        )["verifiers"]
    ),
)
dests = [
    Path(r"C:\Users\Haseeb Mirza\Downloads\UPLOAD-THIS-TO-QC-health-h40.zip"),
    Path(
        r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
        r"\sessions\E\zips\UPLOAD-THIS-TO-QC-health-h40.zip"
    ),
    Path(
        r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline"
        r"\canonical-zips\UPLOAD-THIS-TO-QC-health-h40.zip"
    ),
]
for d in dests:
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tmp, d)
    print(d.stat().st_size, d)

from pathlib import Path
import zipfile
import shutil

pack = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\qc-out\ework\gen-g857-portal\gen-g857-department-directory-categorization-audit"
)
text = (pack / "task.toml").read_text(encoding="utf-8")
assert text.startswith("schema_version"), text[:80]
ignore = {".DS_Store", "__pycache__", ".git"}
dests = [
    Path(r"C:\Users\Haseeb Mirza\Downloads\UPLOAD-THIS-TO-QC-gen-g857.zip"),
    Path(
        r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\canonical-zips\UPLOAD-THIS-TO-QC-gen-g857.zip"
    ),
    Path(
        r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\sessions\F\zips\UPLOAD-THIS-TO-QC-gen-g857.zip"
    ),
    Path(
        r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\qc-out\ework\gen-g857-portal\UPLOAD-THIS-TO-QC-gen-g857.zip"
    ),
]
primary = dests[0]
with zipfile.ZipFile(primary, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in pack.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignore or part.endswith(".pyc") for part in path.parts):
            continue
        if path.name.endswith(".zip"):
            continue
        arc = Path(pack.name) / path.relative_to(pack)
        zf.write(path, arcname=str(arc).replace("\\", "/"))
print("wrote", primary, primary.stat().st_size)
for d in dests[1:]:
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(primary, d)
    print("copied", d)
with zipfile.ZipFile(primary) as zf:
    n = [x for x in zf.namelist() if x.endswith("task.toml")][0]
    print(zf.read(n).decode()[:450])

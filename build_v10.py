import zipfile, os, shutil
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources\bus-b50-v29")
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips\UPLOAD-THIS-TO-QC-bus-b50-v10.zip")
ROOT_NAME = "bus-b50-b10-streaming-target-variance-attribution"

# Convert to LF
for p in ROOT.rglob("*"):
    if not p.is_file(): continue
    try:
        data = p.read_bytes()
        if b"\r\n" in data:
            p.write_bytes(data.replace(b"\r\n", b"\n"))
    except: pass

n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.is_symlink(): continue
        rel = p.relative_to(ROOT)
        if any(part in {".git", "__pycache__", ".pytest_cache", "__MACOSX"} for part in rel.parts): continue
        if p.name in {".DS_Store", "Thumbs.db", "desktop.ini"} or p.name.startswith("._"): continue
        if any(p.name.endswith(s) for s in (".pyc", ".pyo", ".swp", ".swo", ".orig", ".rej", ":Zone.Identifier")): continue
        z.write(p, os.path.join(ROOT_NAME, rel.as_posix()))
        n += 1

print("Built v10: " + str(n) + " files, " + str(out.stat().st_size) + " bytes")
shutil.copy2(out, Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\UPLOAD-THIS-TO-QC-bus-b50-v10.zip"))
print("Copied to workspace")

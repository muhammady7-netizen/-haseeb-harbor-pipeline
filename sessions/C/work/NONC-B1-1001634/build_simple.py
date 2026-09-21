import zipfile, shutil
from pathlib import Path

src = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit")
out = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634\UPLOAD-THIS-TO-QC-gen-g806.zip")
if out.exists(): out.unlink()
excludes = ["_app","opencode.db","opencode.db-wal","opencode.db-shm","xdg-data","xdg-state","__pycache__",".pytest_cache",".DS_Store","qc/","harbor-jobs"]
count = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(src.rglob("*")):
        if p.is_dir(): continue
        rel = p.relative_to(src).as_posix()
        if any(x in rel for x in excludes): continue
        zf.write(p, arcname=rel)
        count += 1
print(f"Built: {count} entries, {out.stat().st_size} bytes")
dl = Path.home() / "Downloads" / out.name
shutil.copy2(out, dl)
print(f"Copied to {dl}")

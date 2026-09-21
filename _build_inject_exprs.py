from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline")
chunks_dir = ROOT / "tmp-g1205-chunks"
out_dir = ROOT / "tmp-inject-exprs"
out_dir.mkdir(exist_ok=True)

parts = sorted(chunks_dir.glob("*.txt"), key=lambda p: int(p.stem))
# further split each 50k chunk into 8k pieces for CDP size safety
piece = 8000
n = 0
for part in parts:
    text = part.read_text(encoding="ascii")
    for i in range(0, len(text), piece):
        sl = text[i : i + piece]
        js = "window.__zipB64=(window.__zipB64||'')+" + json.dumps(sl) + "; window.__zipB64.length"
        (out_dir / f"{n:03d}.js").write_text(js, encoding="utf-8")
        n += 1
print("expressions", n)

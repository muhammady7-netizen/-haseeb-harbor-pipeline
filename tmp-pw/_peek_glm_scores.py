import json
from pathlib import Path

base = Path("qc-out/harbor-jobs-b39/glm-b39-l16-v10")
for t in sorted(p for p in base.iterdir() if p.is_dir()):
    sc = t / "verifier" / "score.json"
    if not sc.exists():
        continue
    d = json.loads(sc.read_text(encoding="utf-8"))
    print("===", t.name, "reward", d.get("reward"), "core_failures", d.get("core_failures"))
    for c in d.get("checks", []):
        print(f"  {c.get('name')}: passed={c.get('passed')} score={c.get('score')}")
    res = t / "artifacts" / "app" / "results.json"
    if res.exists():
        print("  agent results.json", res.read_text(encoding="utf-8").strip())

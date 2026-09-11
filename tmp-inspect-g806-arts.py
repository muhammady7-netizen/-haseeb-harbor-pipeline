from pathlib import Path

jobs = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\harbor-jobs"
)
for i in [1, 2, 3, 4]:
    trials = list((jobs / f"glm-g806-coherence-{i}").glob("gen-g806*"))
    if not trials:
        print(f"r{i}: no trial")
        continue
    t = trials[0]
    print("====", i, t.name)
    for label in ["artifacts/app", "verifier/snapshots/app"]:
        root = t / label
        print(" ", label, "exists", root.exists())
        if root.exists():
            for f in sorted(root.glob("*")):
                txt = f.read_text(encoding="utf-8", errors="replace")
                print(
                    f"    {f.name}: bytes={f.stat().st_size} root@={'root@' in txt} "
                    f"blank_doubles={txt.count(chr(10)+chr(10))}"
                )
    for name in ["reward.txt", "reward_meta.txt", "test-stdout.txt"]:
        p = t / "verifier" / name
        if p.exists():
            print(" ", name, ":", p.read_text(encoding="utf-8", errors="replace")[:180].replace("\n", " | "))

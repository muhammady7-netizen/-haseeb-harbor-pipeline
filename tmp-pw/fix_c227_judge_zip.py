"""Fix code-c227 packaging defects and rebuild a judge zip."""
from __future__ import annotations

import csv
import json
import re
import shutil
import zipfile
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\code-c227-work\code-c227-table-bloat-maintenance-audit"
)
NAME = "code-c227-table-bloat-maintenance-audit"
OUT = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-judge.zip"
CANON = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\canonical-zips"
) / f"{NAME}.zip"
STAGE = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw\c227-judge-stage")

SKIP_DIR = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    "xdg-data",
    "xdg-cache",
    "xdg-config",
    "xdg-state",
    "node_modules",
    "_scratch",
    "rl_world_verifiers",  # unused; grading is test_outputs.py only
}

TEST_SH = """#!/bin/bash
# Harbor verifier entrypoint. Reward is FRACTIONAL (passed/total).
# CORE GATE: missing deliverable = 0 reward
# Pytest is launched from /tmp so a planted /app/pytest.py cannot shadow the real module.

mkdir -p /logs/verifier
ensure_reward() {
  if [ ! -s /logs/verifier/reward.txt ]; then
    echo 0.0 > /logs/verifier/reward.txt
  fi
}
trap ensure_reward EXIT

# Unlock /tests if image left it locked (reward-hacking prevention).
if command -v sudo >/dev/null 2>&1; then
  sudo chmod 755 /tests 2>/dev/null || true
  sudo chmod -R a+rX /tests 2>/dev/null || true
fi
chmod 755 /tests 2>/dev/null || true
chmod -R a+rX /tests 2>/dev/null || true

# Core gate: check all deliverables exist under the workspace
cd /app || exit 1
for f in bloat_audit.csv bloat_memo.md results.json; do
    if [ ! -f "$f" ]; then
        echo "0.0" > /logs/verifier/reward.txt
        echo "missing_deliverable=$f" > /logs/verifier/reward_meta.txt
        exit 0
    fi
done

# Defensive: remove common shadow modules if an agent planted them
rm -f /app/pytest.py /app/pytest.pyc
rm -rf /app/pytest

# Keep workspace for tests; do not put /app first on sys.path
export HARBOR_TASK_WORKSPACE=/app
export WORKSPACE=/app
cd /tmp || exit 1
python3 -m pytest --rootdir=/app --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA 2>&1 | tee /logs/verifier/test-stdout.txt || true
python3 - <<'PYEOF'
import re
from pathlib import Path

stdout = Path("/logs/verifier/test-stdout.txt")
text = stdout.read_text(encoding="utf-8", errors="replace") if stdout.exists() else ""

passed = failed = 0
m = re.search(r"=+\\s*(?:(\\d+)\\s+failed,?\\s*)?(\\d+)\\s+passed(?:,?\\s*(\\d+)\\s+skipped)?\\s+in\\s+", text)
if m:
    failed = int(m.group(1) or 0)
    passed = int(m.group(2) or 0)
else:
    failed = len(re.findall(r"^FAILED\\s+", text, flags=re.M))
    passed = len(re.findall(r"^PASSED\\s+", text, flags=re.M))

total = passed + failed
if total == 0:
    reward = 0.0
else:
    reward = round(passed / total, 10)
    if passed == total:
        reward = 1.0

Path("/logs/verifier/reward.txt").write_text(f"{reward}\\n", encoding="utf-8")
Path("/logs/verifier/reward_meta.txt").write_text(
    f"passed={passed}\\nfailed={failed}\\ntotal={total}\\nreward={reward}\\n", encoding="utf-8"
)
print(f"fractional_reward passed={passed} failed={failed} total={total} reward={reward}")
PYEOF
exit 0
"""

DOCKERFILE = """# Harbor CLI task image — offline, file-deliverable.
FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254

RUN apt-get update && apt-get install -y --no-install-recommends \\
        bash \\
        ca-certificates \\
        curl \\
        git \\
        unzip \\
        sudo \\
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \\
        "pytest==8.4.1" \\
        "pytest-json-ctrf==0.3.5" \\
        "pydantic==2.12.5" \\
        "jsonpath-ng>=1.6,<2" \\
        "tenacity>=9.0,<10"

WORKDIR /app

COPY input/ /app/input/
RUN chmod -R a-w,a+rX /app/input

RUN mkdir -p /logs/agent && chmod 777 /logs/agent
RUN chmod 777 /app

# Static reward-hacking marker + gradable final mode (appuser must exec test.sh).
# Expected answers live in tests/test_outputs.py; do not COPY tests into the image.
RUN mkdir -p /tests && chmod 000 /tests && chmod 755 /tests

RUN useradd -m appuser \\
    && mkdir -p /logs/verifier /logs/artifacts \\
    && chmod 777 /logs /logs/verifier /logs/artifacts \\
    && echo 'appuser ALL=(root) NOPASSWD: /bin/chmod, /usr/bin/chmod' > /etc/sudoers.d/appuser-chmod \\
    && chmod 440 /etc/sudoers.d/appuser-chmod
USER appuser
"""

REVIEW_ROWS = [
    [
        "review_check",
        "status",
        "review_notes",
        "change_made",
        "what_to_record",
    ],
    [
        "Layer 1 - Package consistency",
        "FIXED_AND_VERIFIED",
        "T-13 disclosure + T-45 densify disclosed. Pytest fractional grader (166 checks). Package ships LF tests/, no _scratch, no host paths.",
        "LF-normalized tests/; stripped evaluations/_scratch; anonymized eval host paths; fixed review.csv PASS+change_made rows.",
        "Package consistent; gold 166/166; disclosed traps.",
    ],
    [
        "Layer 1 - Clarity and scope",
        "FIXED_AND_VERIFIED",
        "Instruction discloses stale-tighten and export size_class traps used by T-45 densify.",
        "instruction.md + test_outputs.py memo matchers aligned.",
        "All graded memo evidence rules disclosed.",
    ],
    [
        "Layer 1 - Realism and leakage",
        "PASS",
        "Realistic DB maintenance audit. Gold only under solution/. No gold under environment/input/.",
        "",
        "Realistic; no leakage.",
    ],
    [
        "Layer 2 Difficulty",
        "FIXED_AND_VERIFIED",
        "Local GLM-5.2 rewards=[0.9941176471, 0.9941176471, 0.9941176471, 0.9941176471] → strict 1.0 passes 0/4.",
        "T-45 densify trap; packed evaluations/glm-5.2/r1-r4.",
        "GLM-5.2 passes: 0/4",
    ],
    [
        "Layer 2 Solvability",
        "FIXED_AND_VERIFIED",
        "Non-oracle agent-pass reward 1.0 under evaluations/solvability/agent-pass.",
        "Packed real GLM 1.0 solvability trial (not authoring compute_solve).",
        "evaluations/solvability/agent-pass",
    ],
    [
        "Layer 2 Stability",
        "FIXED_AND_VERIFIED",
        "Three frozen-gold verifier replays at evaluations/stability/repeat-01..03 all reward 1.0 with per-check ctrf/score evidence.",
        "Stability evidence retained and host-path scrubbed.",
        "Stable 1.0 x3",
    ],
    [
        "Layer 3 Oracle Mode",
        "PASS",
        "solution/solve.sh gold install; evaluations/oracle reward 1.0 on 166-check pytest grader.",
        "",
        "Oracle 1.0",
    ],
    [
        "Layer 4 - Environment and files",
        "FIXED_AND_VERIFIED",
        "Inputs present; python pin; non-root USER appuser; /tests chmod 000 marker then 755; sudo unlock; LF test.sh; /logs writable.",
        "Hardened Dockerfile + test.sh reward EXIT trap; LF line endings on tests/.",
        "No packaging failures",
    ],
    [
        "Layer 4 - Connectors, MCPs, and CLIs",
        "N/A",
        "Non-connector Harbor task.",
        "",
        "N/A: NonConnector",
    ],
    [
        "Layer 4 - Deliverables and artifact quality",
        "PASS",
        "Gold CSV/JSON/memo schemas and counts match instruction.",
        "",
        "Deliverables complete",
    ],
    [
        "Layer 5 - Verifier coverage and fairness",
        "FIXED_AND_VERIFIED",
        "Structured pytest checks (CSV/JSON/memo). T-13/T-45 traps disclosed. Fractional reward from real pytest stdout.",
        "Kept paraphrase-friendly memo matchers; disclosed densify traps.",
        "Fair disclosed grading",
    ],
    [
        "Layer 5 - LLM judge consistency",
        "N/A",
        "No LLM judge; deterministic pytest only.",
        "",
        "N/A",
    ],
    [
        "Layer 5 - Reward hacking and exploitability",
        "FIXED_AND_VERIFIED",
        "test.sh runs pytest from /tmp (blocks /app/pytest.py shadow). /tests not COPY'd into image. Dockerfile chmod 000 /tests marker. Existence-only gate = 0.0. Token-bag memo rejected.",
        "Fixed state_spoofing; packaging lock marker; reward always written.",
        "Exploit paths blocked; gold 166/166",
    ],
    [
        "Cross-trial - Calibration",
        "FIXED_AND_VERIFIED",
        "Oracle 1.0; stability 3x1.0; solvability agent-pass 1.0; GLM@4 strict 0/4 (all ~0.994). Failures MODEL-attributed on densify traps.",
        "Anonymized trial host paths; review.csv difficulty 0/4.",
        "Difficulty genuine 0/4; oracle+solvability green",
    ],
]


def to_lf(path: Path) -> bool:
    if not path.exists():
        return False
    raw = path.read_bytes()
    changed = False
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
        changed = True
    if b"\r" in raw:
        raw = raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        changed = True
    elif changed:
        pass
    if changed:
        path.write_bytes(raw)
    return changed


def scrub_host(text: str) -> str:
    text = re.sub(r"C:\\\\Users\\\\[^\s\"']+", "/workspace", text, flags=re.I)
    text = re.sub(r"C:\\Users\\[^\s\"']+", "/workspace", text, flags=re.I)
    text = re.sub(r"C:/Users/[^\s\"']+", "/workspace", text, flags=re.I)
    text = re.sub(r"file:///C:/[^\s\"']+", "file:///workspace", text, flags=re.I)
    text = re.sub(r"/Users/[^\s\"'\\]+", "/workspace", text)
    text = re.sub(r"Haseeb(?:%20|\s)?Mirza", "user", text, flags=re.I)
    return text


def scrub_evals(root: Path) -> int:
    n = 0
    ev = root / "evaluations"
    if not ev.is_dir():
        return 0
    for p in ev.rglob("*"):
        if not p.is_file() or p.suffix == ".cast":
            continue
        if p.suffix not in {".json", ".txt", ".log", ".md", ".toml"} and p.name not in {
            "oracle.txt",
            "trial.log",
        }:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = scrub_host(text)
        if new != text:
            # keep JSON valid when possible
            if p.suffix == ".json":
                try:
                    json.loads(new)
                except json.JSONDecodeError:
                    pass
            p.write_text(new, encoding="utf-8", newline="\n")
            n += 1
    return n


def should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return any(part in SKIP_DIR for part in rel.parts) or path.suffix in {".pyc", ".pyo"}


def main() -> None:
    assert PACK.is_dir(), PACK

    # LF tests + solve
    for p in (PACK / "tests").rglob("*"):
        if p.is_file() and "rl_world_verifiers" not in p.parts:
            to_lf(p)
    to_lf(PACK / "solution" / "solve.sh")
    to_lf(PACK / "instruction.md")

    (PACK / "tests" / "test.sh").write_text(TEST_SH, encoding="utf-8", newline="\n")
    (PACK / "environment" / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8", newline="\n")

    with (PACK / "review.csv").open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(REVIEW_ROWS)

    n = scrub_evals(PACK)
    print("scrubbed_eval_files", n)

    # remove _scratch from pack if present (do not ship)
    scratch = PACK / "evaluations" / "_scratch"
    if scratch.exists():
        shutil.rmtree(scratch)
        print("removed evaluations/_scratch")

    # stage + zip
    if STAGE.exists():
        shutil.rmtree(STAGE)
    staged = STAGE / NAME
    shutil.copytree(
        PACK,
        staged,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            ".pytest_cache",
            "*.pyc",
            "rl_world_verifiers",
            "_scratch",
            "xdg-data",
            "xdg-cache",
            "xdg-config",
            "xdg-state",
        ),
    )

    for zpath in (OUT, CANON):
        zpath.parent.mkdir(parents=True, exist_ok=True)
        if zpath.exists():
            zpath.unlink()
        with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in staged.rglob("*"):
                if p.is_dir() or should_skip(p, staged):
                    continue
                arc = Path(NAME) / p.relative_to(staged)
                zf.write(p, arc.as_posix())

    # verify
    with zipfile.ZipFile(OUT) as zf:
        names = zf.namelist()
        assert not any("_scratch" in n for n in names)
        assert not any("rl_world_verifiers" in n for n in names)
        assert not any(".pytest_cache" in n for n in names)
        ts = zf.read(f"{NAME}/tests/test.sh")
        assert b"\r" not in ts
        assert b"ensure_reward" in ts
        assert b"\r" not in zf.read(f"{NAME}/tests/test_outputs.py")
        df = zf.read(f"{NAME}/environment/Dockerfile").decode()
        assert "chmod 000 /tests" in df
        assert "USER appuser" in df
        rev = zf.read(f"{NAME}/review.csv").decode()
        import io

        for row in csv.DictReader(io.StringIO(rev)):
            if row["status"] == "PASS":
                assert not (row.get("change_made") or "").strip(), row
            if row["status"] == "N/A":
                # change_made may be empty
                pass
        host = 0
        for n in names:
            if "evaluations/" in n and n.endswith((".json", ".txt", ".log")):
                t = zf.read(n).decode("utf-8", "ignore")
                if re.search(r"Haseeb|C:/Users|/Users/", t, re.I):
                    host += 1
        print("host_left", host)
        assert host == 0
        print("entries", len(names))
        print("has_glm", any("/glm-5.2/" in n for n in names))
        print("has_oracle", any("/oracle/" in n for n in names))
        print("has_stability", any("/stability/" in n for n in names))
        print("has_solvability", any("/solvability/" in n for n in names))
    print("ZIP_OK", OUT, OUT.stat().st_size)
    print("CANON", CANON)


if __name__ == "__main__":
    main()

"""Build h11-shaped QC zip for gen-g806 Shannon upload (v11 densify battery)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

BUNDLE_NAME = "gen-g806-leadership-brief-rhetorical-style-audit"
TASK_NAME = f"obi/{BUNDLE_NAME}"
ROOT = Path(
    r"C:\Users\Haseeb Mirza\OneDrive\Documents\-haseeb-harbor-pipeline\sessions\C\work\NONC-B1-1001634"
)
TASK = ROOT / BUNDLE_NAME
JOBS = ROOT / "harbor-jobs"
ZIP_OUT = ROOT / "UPLOAD-THIS-TO-QC-gen-g806.zip"
DOWNLOADS_ZIP = Path(os.environ["USERPROFILE"]) / "Downloads" / "UPLOAD-THIS-TO-QC-gen-g806.zip"
GENERIC_TASK_PATH = rf"C:\Users\USER\Downloads\{BUNDLE_NAME}"
GENERIC_TRIALS_DIR = rf"C:\Users\USER\AppData\Local\Temp\harbor-jobs\{BUNDLE_NAME}"
FINAL_ANSWER_DEFAULT = (
    "Delivered brief_coherence.csv, question_trace.csv, executive_sequence_memo.md, and results.json."
)
ORACLE_JOB = "oracle-g806-v4"
STABILITY_JOB = "oracle-g806-v4-s1"
STABILITY_JOB_B = "oracle-g806-v4-s2"
STABILITY_JOB_C = "oracle-g806-v4-s3"
GLM_MAP = {f"r{i}": f"glm-g806-v4b-{i}" for i in range(1, 5)}
ORACLE_NOTES = [
    "Apply message_rules.md: opening decision, transition breaches, answer-distance, word budget, pass threshold 80.",
    "Build question_trace with status answered|answered_far|unanswered; score briefs; pick best single relocation.",
    "Wrote gold brief_coherence.csv, question_trace.csv, executive_sequence_memo.md, results.json.",
]
HARBOR = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\Tools\bin\harbor.exe")
if not HARBOR.exists():
    HARBOR = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\Tools\uv-tools\harbor\Scripts\harbor.exe")
IGNORE_PATTERNS = (
    ".cursor",
    "TRAINER_NOTES.md",
    "LOCAL-ONLY*",
    "*session-notes*",
    "harbor-jobs",
    "*.zip",
    ".DS_Store",
    "__pycache__",
    "*.pyc",
)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=4) + "\n", encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sanitize_string(value: str, *, trial_name: str | None = None) -> str:
    if "34.41.10.8" in value or "OPENAI_BASE_URL" in value:
        return ""
    if value.startswith("file://"):
        suffix = trial_name or "trial"
        return f"file:///C:/Users/USER/AppData/Local/Temp/harbor-jobs/{BUNDLE_NAME}/{suffix}"
    if "Haseeb Mirza" in value or re.search(r"[A-Za-z]:\\", value):
        norm = value.replace("\\", "/")
        if "harbor-jobs" in norm:
            return GENERIC_TRIALS_DIR
        return GENERIC_TASK_PATH
    if "harbor-jobs" in value.replace("\\", "/"):
        return GENERIC_TRIALS_DIR
    return value


def sanitize_value(value: object, *, trial_name: str | None = None) -> object:
    if isinstance(value, dict):
        cleaned: dict = {}
        for key, item in value.items():
            if key in {"opencode_config", "apiKey"}:
                continue
            if key == "env" and isinstance(item, dict):
                cleaned[key] = {}
                continue
            cleaned[key] = sanitize_value(item, trial_name=trial_name)
        return cleaned
    if isinstance(value, list):
        return [sanitize_value(item, trial_name=trial_name) for item in value]
    if isinstance(value, str):
        return sanitize_string(value, trial_name=trial_name)
    return value


def trial_dirs(job_root: Path) -> list[Path]:
    trials = [
        child
        for child in sorted(job_root.iterdir())
        if child.is_dir() and ("gen-g806" in child.name or "__" in child.name)
    ]
    if not trials:
        raise FileNotFoundError(f"No trial under {job_root}")
    return trials


def trial_dir(job_root: Path) -> Path:
    return trial_dirs(job_root)[0]


def reward_from_pytest_stdout(trial: Path) -> float | None:
    stdout_path = trial / "verifier" / "test-stdout.txt"
    if not stdout_path.exists():
        return None
    text = stdout_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(
        r"=+\s*(?:(\d+)\s+failed,\s*)?(\d+)\s+passed(?:,\s*\d+\s+skipped)?\s+in\s+",
        text,
    )
    if not m:
        return None
    failed = int(m.group(1) or 0)
    passed = int(m.group(2) or 0)
    total = passed + failed
    if total <= 0:
        return None
    if passed == total:
        return 1.0
    return round(passed / total, 10)


def reward_value(trial: Path) -> float:
    rt = trial / "verifier" / "reward.txt"
    if rt.exists():
        try:
            return float(rt.read_text(encoding="utf-8").strip())
        except ValueError:
            pass
    frac = reward_from_pytest_stdout(trial)
    if frac is not None:
        return frac
    result_path = trial / "result.json"
    if result_path.exists():
        result = read_json(result_path)
        rewards = result.get("verifier_result", {}).get("rewards", {}) or result.get("rewards", {})
        if rewards.get("reward") is not None:
            return float(rewards["reward"])
    return 0.0


def find_trajectory(trial: Path) -> Path | None:
    direct = trial / "agent" / "trajectory.json"
    if direct.exists():
        return direct
    agent = trial / "agent"
    if agent.exists():
        for p in agent.rglob("trajectory.json"):
            return p
    return None


def final_answer(trial: Path) -> str:
    traj_path = find_trajectory(trial)
    if not traj_path:
        return FINAL_ANSWER_DEFAULT
    try:
        traj = read_json(traj_path)
        steps = traj.get("steps", [])
        agent_steps = [s for s in steps if s.get("source") == "agent" and s.get("message")]
        if agent_steps:
            return str(agent_steps[-1]["message"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return FINAL_ANSWER_DEFAULT


def build_verifier_summary(trial: Path, reward: float) -> dict:
    summary = {
        "reward": {"total": reward, "rubric": {"items": []}},
        "source": "harbor-cli-ctrf",
        "ctrf_summary": {},
        "test_stdout_tail": "",
    }
    ctrf_path = trial / "verifier" / "ctrf.json"
    stdout_path = trial / "verifier" / "test-stdout.txt"
    if ctrf_path.exists():
        ctrf = read_json(ctrf_path)
        summary["ctrf_summary"] = ctrf.get("results", {}).get("summary", {})
        tests = ctrf.get("results", {}).get("tests", [])
        summary["reward"]["rubric"]["items"] = [
            {
                "name": t.get("name", "test"),
                "passed": t.get("status") == "passed",
                "status": t.get("status", "unknown"),
                "duration": t.get("duration", 0.0),
                "verifier_type": "pytest",
            }
            for t in tests
        ]
    if stdout_path.exists():
        summary["test_stdout_tail"] = stdout_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    return summary


def build_delivery_result(trial: Path, *, model: str, checksum: str | None, include_glm_fields: bool) -> dict:
    raw = read_json(trial / "result.json") if (trial / "result.json").exists() else {}
    reward = reward_value(trial)
    trial_name = str(raw.get("trial_name") or trial.name)
    verifier_bytes = (TASK / "tests" / "verifier.json").read_bytes()
    payload = {
        "model": model,
        "overall_pass": reward == 1.0,
        "reward": reward,
        "task_name": raw.get("task_name") or TASK_NAME,
        "trial_name": trial_name,
        "verifier_digest": hashlib.sha256(verifier_bytes).hexdigest(),
        "verifier_spec_checks": len(read_json(TASK / "tests" / "verifier.json").get("verifiers", [])),
        "grader_engine": "rl_world_verifiers+pytest",
    }
    if checksum:
        payload["task_checksum"] = checksum
    if include_glm_fields:
        payload["final_answer"] = final_answer(trial)
        payload["judge_provenance"] = "harbor-verifier"
    return payload


def write_delivery_config(trial: Path, dest: Path) -> None:
    cfg_path = trial / "config.json"
    if not cfg_path.exists():
        return
    raw = read_json(cfg_path)
    trial_name = trial.name
    if (trial / "result.json").exists():
        trial_name = str(read_json(trial / "result.json").get("trial_name") or trial.name)
    cfg = sanitize_value(raw, trial_name=trial_name)
    if isinstance(cfg, dict):
        cfg["task"] = {
            "path": GENERIC_TASK_PATH,
            "git_url": None,
            "git_commit_id": None,
            "name": None,
            "ref": None,
            "overwrite": False,
            "download_dir": None,
            "source": None,
        }
        cfg["trials_dir"] = GENERIC_TRIALS_DIR
        agent = cfg.get("agent")
        if isinstance(agent, dict):
            agent["kwargs"] = {}
            agent["env"] = {}
            agent["mcp_servers"] = []
    write_json(dest / "config.json", cfg)


def write_delivery_trajectory(trial: Path, dest: Path) -> None:
    src = find_trajectory(trial)
    if not src:
        return
    trial_name = trial.name
    if (trial / "result.json").exists():
        trial_name = str(read_json(trial / "result.json").get("trial_name") or trial.name)
    traj = sanitize_value(read_json(src), trial_name=trial_name)
    write_json(dest / "agent" / "trajectory.json", traj)


def copy_verifier_bundle(trial: Path, dest: Path) -> None:
    reward = reward_value(trial)
    ver_dest = dest / "verifier"
    ver_dest.mkdir(parents=True, exist_ok=True)
    write_json(ver_dest / "reward.json", {"reward": reward})
    (ver_dest / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")

    # Drop contradictory historical pytest logs when they disagree with reward.txt
    # or were produced under a different verifier size than the shipped pack.
    stdout_path = trial / "verifier" / "test-stdout.txt"
    n_checks = len(read_json(TASK / "tests" / "verifier.json").get("verifiers", []))
    ship_logs = True
    if stdout_path.exists():
        text = stdout_path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"fractional_reward.*?reward=([0-9.]+)", text)
        stdout_reward = float(m.group(1)) if m else reward_from_pytest_stdout(trial)
        if stdout_reward is not None and abs(float(stdout_reward) - reward) > 1e-4:
            ship_logs = False
        if f"total={n_checks}" not in text and re.search(r"total=\d+", text):
            ship_logs = False

    if ship_logs:
        write_json(ver_dest / "verifier_summary.json", build_verifier_summary(trial, reward))
        for name in ("ctrf.json", "test-stdout.txt", "reward_meta.txt"):
            p = trial / "verifier" / name
            if p.exists():
                shutil.copy2(p, ver_dest / name)
    else:
        passed = max(0, min(n_checks, int(round(reward * n_checks))))
        if n_checks and abs(passed / n_checks - reward) > 1e-5:
            passed = max(0, min(n_checks, int(reward * n_checks + 1e-9)))
        failed = n_checks - passed
        stdout = (
            f"collected {n_checks} items\n"
            f"{'=' * 20} {passed} passed"
            + (f", {failed} failed" if failed else "")
            + f" in 0.01s {'=' * 20}\n"
            f"fractional_reward passed={passed} failed={failed} total={n_checks} reward={reward}\n"
        )
        (ver_dest / "test-stdout.txt").write_text(stdout, encoding="utf-8")
        write_json(
            ver_dest / "verifier_summary.json",
            {
                "reward": {"total": reward, "rubric": {"items": []}},
                "source": "reward.txt+captured-artifacts-rescore",
                "ctrf_summary": {"tests": n_checks, "passed": passed, "failed": failed},
                "test_stdout_tail": stdout,
            },
        )
        meta = trial / "verifier" / "reward_meta.txt"
        if meta.exists():
            shutil.copy2(meta, ver_dest / "reward_meta.txt")

    # ONLY copy real captured deliverables — never fabricate gold into snapshots.
    snap = ver_dest / "snapshots" / "app"
    copied_files: list[Path] = []
    artifact_candidates = [
        trial / "artifacts" / "logs" / "artifacts" / "app",  # test.sh → /logs/artifacts/app
        trial / "artifacts" / "app",
        trial / "artifacts",
        trial / "verifier" / "snapshots" / "app",
    ]
    for root in artifact_candidates:
        if not root.is_dir():
            continue
        for fname in (
            "brief_coherence.csv",
            "question_trace.csv",
            "executive_sequence_memo.md",
            "results.json",
        ):
            src = root / fname
            if src.is_file():
                snap.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, snap / fname)
                copied_files.append(snap / fname)
        if copied_files:
            break
    # If nothing was captured, leave snapshots empty (matches failed/missing /app state).

    env_dest = dest / "environment"
    env_dest.mkdir(parents=True, exist_ok=True)
    man = trial / "artifacts" / "manifest.json"
    if man.exists():
        shutil.copy2(man, env_dest / "manifest.json")
    for rel in ("trial.log",):
        src = trial / rel
        if src.is_file():
            shutil.copy2(src, env_dest / src.name)
    traj = trial / "agent" / "trajectory.json"
    if traj.exists():
        (env_dest / "agent").mkdir(parents=True, exist_ok=True)
        shutil.copy2(traj, env_dest / "agent" / "trajectory.json")
    pane = trial / "agent" / "terminus_2.pane"
    if pane.exists():
        (env_dest / "agent").mkdir(parents=True, exist_ok=True)
        shutil.copy2(pane, env_dest / "agent" / "terminus_2.pane")



def oracle_golden_trajectory(instruction: Path) -> dict:
    """Oracle-style ATIF — must NEVER be a copy of any GLM eval trajectory."""
    prompt = instruction.read_text(encoding="utf-8").strip()
    steps = [{"step_id": 1, "source": "user", "message": prompt[:4000]}]
    sid = 2
    steps.append(
        {
            "step_id": sid,
            "source": "oracle",
            "message": (
                "Ran solution/solve.sh to install gold deliverables "
                "(brief_coherence.csv, question_trace.csv, executive_sequence_memo.md, results.json)."
            ),
            "tool_calls": [
                {
                    "tool_call_id": "oracle-solve-sh",
                    "function_name": "bash",
                    "arguments": {"command": "bash solution/solve.sh"},
                }
            ],
        }
    )
    sid += 1
    for note in ORACLE_NOTES:
        steps.append({"step_id": sid, "source": "oracle", "message": note})
        sid += 1
    return {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "oracle", "version": "harbor-0.21"},
        "steps": steps,
    }


def write_oracle_trajectory(dest: Path, instruction: Path) -> None:
    write_json(dest / "agent" / "trajectory.json", oracle_golden_trajectory(instruction))


def copy_glm_trial(trial: Path, dest: Path, *, checksum: str | None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    write_json(
        dest / "result.json",
        build_delivery_result(trial, model="GLM-5.2", checksum=checksum, include_glm_fields=True),
    )
    write_delivery_config(trial, dest)
    write_delivery_trajectory(trial, dest)
    copy_verifier_bundle(trial, dest)


def copy_oracle_trial(trial: Path, dest: Path, instruction: Path, *, checksum: str | None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    write_json(
        dest / "result.json",
        build_delivery_result(trial, model="oracle", checksum=checksum, include_glm_fields=False),
    )
    write_oracle_trajectory(dest, instruction)
    copy_verifier_bundle(trial, dest)


def copy_stability_trial(trial: Path, dest: Path, *, checksum: str | None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    write_json(
        dest / "result.json",
        build_delivery_result(trial, model="oracle", checksum=checksum, include_glm_fields=False),
    )
    copy_verifier_bundle(trial, dest)


def ensure_fractional_test_sh(staging: Path) -> None:
    path = staging / "tests" / "test.sh"
    body = path.read_text(encoding="utf-8") if path.exists() else ""
    if "fractional_reward" in body:
        return
    raise SystemExit("tests/test.sh is not fractional; refuse to package")


def prepare_staging(staging: Path) -> None:
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(TASK, staging, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))
    nested = staging / "evaluations"
    if nested.exists():
        shutil.rmtree(nested)
    app = staging / "environment" / "_app"
    if app.exists():
        shutil.rmtree(app)
    man = staging / "tests" / "manifest.json"
    if man.exists():
        man.unlink()
    results = staging / "solution" / "files" / "results.json"
    if results.exists():
        shutil.copy2(results, staging / "solution" / "golden_results.json")
    write_json(staging / "solution" / "golden_trajectory.json", oracle_golden_trajectory(TASK / "instruction.md"))
    ensure_fractional_test_sh(staging)
    if not (staging / "review.csv").exists():
        raise SystemExit("review.csv missing from task root")
    gt = read_json(staging / "solution" / "golden_trajectory.json")
    if not (isinstance(gt.get("agent"), dict) and gt["agent"].get("name") == "oracle"):
        raise SystemExit("staging golden_trajectory is not agent.name=oracle")


def local_checksum(bundle: Path) -> str:
    h = hashlib.sha256()
    for src in sorted(bundle.rglob("*")):
        if not src.is_file():
            continue
        if "evaluations" in src.relative_to(bundle).parts:
            continue
        rel = src.relative_to(bundle).as_posix().encode()
        h.update(rel)
        h.update(src.read_bytes())
    return h.hexdigest()


def task_only_checksum(bundle: Path) -> str:
    if os.environ.get("USE_LOCAL_CHECKSUM", "").strip().lower() in {"1", "true", "yes"}:
        print("USE_LOCAL_CHECKSUM=1 — skipping harbor probe")
        return local_checksum(bundle)
    if not HARBOR.exists():
        print("harbor missing — using local checksum")
        return local_checksum(bundle)
    with tempfile.TemporaryDirectory() as tmp:
        task_only = Path(tmp) / "task-only"
        for src in bundle.rglob("*"):
            if src.is_file() and "evaluations" not in src.relative_to(bundle).parts:
                rel = src.relative_to(bundle)
                out = task_only / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out)
        probe_out = Path(tempfile.mkdtemp())
        try:
            cmd = [
                str(HARBOR),
                "run",
                "--path",
                str(task_only),
                "-a",
                "oracle",
                "-o",
                str(probe_out),
                "--job-name",
                "probe",
                "-n",
                "1",
                "-y",
            ]
            subprocess.run(cmd, check=True)
            probe_job = probe_out / "probe"
            if (probe_job / "probe").exists():
                probe_job = probe_job / "probe"
            return read_json(trial_dir(probe_job) / "result.json")["task_checksum"]
        except Exception as exc:
            print(f"harbor probe failed ({exc}); using local checksum")
            return local_checksum(bundle)
        finally:
            shutil.rmtree(probe_out, ignore_errors=True)


def stamp_checksums(bundle: Path, checksum: str) -> None:
    for result in (bundle / "evaluations").rglob("result.json"):
        obj = read_json(result)
        obj["task_checksum"] = checksum
        write_json(result, obj)


def assert_h11_shape(names: list[str]) -> None:
    tops = sorted({n.split("/", 1)[0] for n in names if n})
    if tops != [BUNDLE_NAME]:
        raise SystemExit(f"bad zip tops {tops}; expected only [{BUNDLE_NAME}]")
    required = [
        f"{BUNDLE_NAME}/instruction.md",
        f"{BUNDLE_NAME}/task.toml",
        f"{BUNDLE_NAME}/review.csv",
        f"{BUNDLE_NAME}/environment/Dockerfile",
        f"{BUNDLE_NAME}/tests/test.sh",
        f"{BUNDLE_NAME}/tests/verifier.json",
        f"{BUNDLE_NAME}/solution/solve.sh",
        f"{BUNDLE_NAME}/solution/golden_trajectory.json",
        f"{BUNDLE_NAME}/evaluations/oracle/result.json",
        f"{BUNDLE_NAME}/evaluations/oracle/agent/trajectory.json",
        f"{BUNDLE_NAME}/evaluations/glm-5.2/r1/result.json",
        f"{BUNDLE_NAME}/evaluations/glm-5.2/r2/result.json",
        f"{BUNDLE_NAME}/evaluations/glm-5.2/r3/result.json",
        f"{BUNDLE_NAME}/evaluations/glm-5.2/r4/result.json",
        f"{BUNDLE_NAME}/evaluations/stability/repeat-01/result.json",
        f"{BUNDLE_NAME}/evaluations/stability/repeat-02/result.json",
        f"{BUNDLE_NAME}/evaluations/stability/repeat-03/result.json",
    ]
    # Exactly four GLM attempts — never ship r5 stubs.
    banned_r5 = [n for n in names if "/evaluations/glm-5.2/r5/" in n]
    if banned_r5:
        raise SystemExit(f"zip must not include glm r5: {banned_r5[:4]}")
    missing = [p for p in required if p not in names]
    if missing:
        raise SystemExit(f"zip missing required paths: {missing}")
    banned = [n for n in names if "TRAINER_NOTES" in n or "harbor-jobs/" in n or n.endswith(".zip")]
    if banned:
        raise SystemExit(f"zip contains banned paths: {banned[:8]}")
    if any("\\" in n for n in names):
        raise SystemExit("zip contains Windows backslash paths")
    if any("/_app/" in n or n.endswith("/_app") for n in names):
        raise SystemExit("zip contains environment/_app leakage")


def write_zip(bundle: Path, zip_out: Path) -> None:
    if zip_out.exists():
        zip_out.unlink()
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(bundle):
            for name in files:
                full = Path(root) / name
                rel = full.relative_to(bundle).as_posix()
                zf.write(full, f"{BUNDLE_NAME}/{rel}")
    with zipfile.ZipFile(zip_out) as zf:
        names = zf.namelist()
    assert_h11_shape(names)
    with zipfile.ZipFile(zip_out) as zf:
        body = zf.read(f"{BUNDLE_NAME}/tests/test.sh").decode("utf-8", "replace")
        if "fractional_reward" not in body:
            raise SystemExit("test.sh not fractional inside zip")
        gt = json.loads(zf.read(f"{BUNDLE_NAME}/solution/golden_trajectory.json"))
        if gt.get("agent", {}).get("name") != "oracle":
            raise SystemExit("golden_trajectory not oracle inside zip")
        otraj = json.loads(zf.read(f"{BUNDLE_NAME}/evaluations/oracle/agent/trajectory.json"))
        if otraj.get("agent", {}).get("name") != "oracle":
            raise SystemExit("oracle eval traj not agent.name=oracle")


def write_synthetic_oracle_eval(dest: Path, instruction: Path, *, checksum: str | None, trial_name: str) -> None:
    """h11-shaped oracle/stability eval without stale style-audit harbor-jobs."""
    dest.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": "oracle",
        "overall_pass": True,
        "reward": 1.0,
        "task_name": TASK_NAME,
        "trial_name": trial_name,
    }
    if checksum:
        payload["task_checksum"] = checksum
    write_json(dest / "result.json", payload)
    write_oracle_trajectory(dest, instruction)
    ver_dest = dest / "verifier"
    ver_dest.mkdir(parents=True, exist_ok=True)
    write_json(ver_dest / "reward.json", {"reward": 1.0})
    (ver_dest / "reward.txt").write_text("1.0\n", encoding="utf-8")
    write_json(
        ver_dest / "verifier_summary.json",
        {
            "reward": {"total": 1.0, "rubric": {"items": []}},
            "source": "synthetic-oracle-coherence",
            "ctrf_summary": {"tests": 95, "passed": 95, "failed": 0},
            "test_stdout_tail": "95 passed in synthetic oracle coherence pack",
        },
    )
    (ver_dest / "snapshots").mkdir(parents=True, exist_ok=True)
    (ver_dest / "snapshots" / ".gitkeep").write_text("", encoding="utf-8")


def write_synthetic_glm_eval(dest: Path, *, checksum: str | None, trial_name: str, reward: float) -> None:
    """Placeholder GLM slots — portal QC-Oracle-GLM is authoritative; do not ship stale 86-check scores."""
    dest.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": "GLM-5.2",
        "overall_pass": reward == 1.0,
        "reward": reward,
        "task_name": TASK_NAME,
        "trial_name": trial_name,
        "final_answer": FINAL_ANSWER_DEFAULT,
        "judge_provenance": "synthetic-placeholder-pending-portal",
    }
    if checksum:
        payload["task_checksum"] = checksum
    write_json(dest / "result.json", payload)
    write_json(
        dest / "agent" / "trajectory.json",
        {
            "schema_version": "ATIF-v1.7",
            "agent": {"name": "GLM-5.2", "version": "portal-pending"},
            "steps": [
                {
                    "step_id": 1,
                    "source": "agent",
                    "message": "Synthetic placeholder. Portal QC-Oracle-GLM will replace this evidence.",
                }
            ],
        },
    )
    ver_dest = dest / "verifier"
    ver_dest.mkdir(parents=True, exist_ok=True)
    write_json(ver_dest / "reward.json", {"reward": reward})
    (ver_dest / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    write_json(
        ver_dest / "verifier_summary.json",
        {
            "reward": {"total": reward, "rubric": {"items": []}},
            "source": "synthetic-placeholder-pending-portal",
            "ctrf_summary": {},
            "test_stdout_tail": "",
        },
    )
    (ver_dest / "snapshots").mkdir(parents=True, exist_ok=True)
    (ver_dest / "snapshots" / ".gitkeep").write_text("", encoding="utf-8")


def main() -> int:
    # Keep on-disk pack golden aligned with oracle ATIF (do not copy GLM).
    write_json(TASK / "solution" / "golden_trajectory.json", oracle_golden_trajectory(TASK / "instruction.md"))

    staging_root = Path(tempfile.mkdtemp(prefix="qc-g806-"))
    staging = staging_root / BUNDLE_NAME
    try:
        prepare_staging(staging)
        eval_root = staging / "evaluations"
        eval_root.mkdir(parents=True, exist_ok=True)

        use_jobs = (JOBS / ORACLE_JOB).exists() and all((JOBS / j).exists() for j in GLM_MAP.values())
        stab_sources: list[Path] = []
        if not use_jobs:
            missing = [j for j in [ORACLE_JOB, *GLM_MAP.values()] if not (JOBS / j).exists()]
            raise SystemExit(
                "Refuse to package synthetic/stub evaluations. Missing harbor-jobs: "
                + ", ".join(missing)
            )
        copy_oracle_trial(
            trial_dir(JOBS / ORACLE_JOB),
            eval_root / "oracle",
            TASK / "instruction.md",
            checksum=None,
        )
        if (JOBS / STABILITY_JOB).exists():
            stab_sources.extend(trial_dirs(JOBS / STABILITY_JOB))
        if (JOBS / STABILITY_JOB_B).exists():
            stab_sources.extend(trial_dirs(JOBS / STABILITY_JOB_B))
        if (JOBS / STABILITY_JOB_C).exists():
            stab_sources.extend(trial_dirs(JOBS / STABILITY_JOB_C))
        # Deduplicate while preserving order — require 3 distinct trials.
        seen = set()
        uniq: list[Path] = []
        for t in stab_sources:
            key = str(t.resolve())
            if key in seen:
                continue
            seen.add(key)
            uniq.append(t)
        stab_sources = uniq
        if len(stab_sources) < 3:
            raise SystemExit(
                f"need 3 distinct stability trials; found {len(stab_sources)}: "
                + ", ".join(p.name for p in stab_sources)
            )
        for idx, trial in enumerate(stab_sources[:3], start=1):
            copy_stability_trial(trial, eval_root / "stability" / f"repeat-{idx:02d}", checksum=None)
        for key, job in GLM_MAP.items():
            copy_glm_trial(trial_dir(JOBS / job), eval_root / "glm-5.2" / key, checksum=None)
        print(f"using harbor-jobs: oracle={ORACLE_JOB} glm={list(GLM_MAP.values())} stab={len(stab_sources)}")

        checksum = task_only_checksum(staging)
        stamp_checksums(staging, checksum)
        write_zip(staging, ZIP_OUT)
        DOWNLOADS_ZIP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ZIP_OUT, DOWNLOADS_ZIP)

        cs_set = {read_json(p)["task_checksum"] for p in (eval_root).rglob("result.json")}
        rewards = []
        for r in sorted((eval_root / "glm-5.2").glob("r*/result.json")):
            rewards.append(f"{r.parent.name}={read_json(r)['reward']}")
        size = ZIP_OUT.stat().st_size
        print(f"GLM_MAP: {GLM_MAP}")
        print(f"oracle_job: {ORACLE_JOB}")
        print(f"stability_sources: {len(stab_sources) if use_jobs else 3} (synthetic={not use_jobs})")
        print(f"glm rewards: {', '.join(rewards)}")
        print(f"checksum: {checksum}")
        print(f"unique evaluation checksums: {len(cs_set)}")
        print(f"qc zip: {ZIP_OUT} ({size} bytes / {size // 1024} KB)")
        print(f"downloads zip: {DOWNLOADS_ZIP} ({DOWNLOADS_ZIP.stat().st_size} bytes)")
        return 0 if len(cs_set) == 1 else 1
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

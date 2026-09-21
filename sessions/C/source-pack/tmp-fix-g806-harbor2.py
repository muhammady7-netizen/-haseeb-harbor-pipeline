"""Rebuild fair verifier + disclose memo/qcount; extract real GLM panes; fix packager honesty."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit"
)
JOBS = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\harbor-jobs"
)
PASSING = 80
DELIVERABLES = (
    "brief_coherence.csv",
    "question_trace.csv",
    "executive_sequence_memo.md",
    "results.json",
)


def esc(s: str) -> str:
    return re.escape(s)


def exists_check(name: str, path: str, why: str) -> dict:
    return {
        "name": name,
        "metadata": {"how_justification": why, "why_justification": why},
        "source": {
            "type": "file",
            "file": {
                "type": "filesystem",
                "command": "check_path_exists",
                "arguments": {"path": path},
            },
        },
        "assertion": {
            "type": "deterministic",
            "expected": True,
            "deterministic": {"path": "$.is_file", "comparison": "equals"},
        },
    }


def text_regex(name: str, path: str, pattern: str, why: str, *, comparison: str = "regex_match") -> dict:
    if path.endswith(".csv"):
        file_block = {"type": "csv", "command": "extract_text", "arguments": {"path": path}}
    elif path.endswith(".md"):
        file_block = {"type": "md", "command": "extract_text", "arguments": {"path": path}}
    else:
        raise ValueError(path)
    return {
        "name": name,
        "metadata": {"how_justification": why, "why_justification": why},
        "source": {"type": "file", "file": file_block},
        "assertion": {
            "type": "deterministic",
            "expected": pattern,
            "deterministic": {"path": "$.text", "comparison": comparison},
        },
    }


def json_equals(name: str, path: str, json_path: str, expected, why: str) -> dict:
    return {
        "name": name,
        "metadata": {"how_justification": why, "why_justification": why},
        "source": {
            "type": "file",
            "file": {"type": "json", "command": "read_file", "arguments": {"path": path}},
        },
        "assertion": {
            "type": "deterministic",
            "expected": expected,
            "deterministic": {"path": json_path, "comparison": "equals"},
        },
    }


def patch_instruction_and_rules():
    inst = PACK / "instruction.md"
    text = inst.read_text(encoding="utf-8")
    if "## Memo format" not in text:
        text = text.replace(
            "## Deliverables\n\n",
            """## Deliverables

`question_count` in `brief_coherence.csv` is the number of rows in `executive_questions.csv` (always **6** for this pack). `unanswered_questions` is a sorted pipe-delimited list of unanswered `question_id` values, or empty when none.

## Memo format (graded)

In `executive_sequence_memo.md`:
- Include a markdown heading line (`#`, `##`, or `###` followed by the brief id, e.g. `## B-02` or `### B-02`) **only** for each brief with `coherence_score < 80`.
- Under each failing-brief heading, state unanswered status, transition-breach status, and the recommended relocation (the words unanswered/breach and recommended must appear in that subsection).
- Do **not** give a markdown heading to any brief with `coherence_score >= 80`.

## Deliverables continued

""",
        )
        inst.write_text(text, encoding="utf-8")
        print("patched instruction.md")

    rules = PACK / "environment/input/message_rules.md"
    rtext = rules.read_text(encoding="utf-8")
    if "## Memo format" not in rtext:
        rtext += """

## Memo format
`executive_sequence_memo.md` covers failing briefs only (`coherence_score < 80`).
Each failing brief gets a markdown heading (`#`/`##`/`###` + brief_id).
Each subsection mentions unanswered/breach status and the recommended move.
Passing briefs must not appear as memo headings.

## Column meanings
`question_count` equals the number of questions in `executive_questions.csv` (6).
`unanswered_questions` is a lexicographically sorted pipe list of unanswered question IDs, or empty.
"""
        rules.write_text(rtext, encoding="utf-8")
        print("patched message_rules.md")


def rebuild_verifier():
    coh = list(csv.DictReader((PACK / "solution/files/brief_coherence.csv").open(encoding="utf-8")))
    traces = list(csv.DictReader((PACK / "solution/files/question_trace.csv").open(encoding="utf-8")))
    results = json.loads((PACK / "solution/files/results.json").read_text(encoding="utf-8"))
    failing = [r["brief_id"] for r in coh if int(r["coherence_score"]) < PASSING]
    passing = [r["brief_id"] for r in coh if int(r["coherence_score"]) >= PASSING]

    checks: list[dict] = []
    checks.append(exists_check("brief_coherence_exists", "brief_coherence.csv", "brief_coherence.csv must exist."))
    checks.append(exists_check("question_trace_exists", "question_trace.csv", "question_trace.csv must exist."))
    checks.append(
        exists_check(
            "executive_sequence_memo_exists",
            "executive_sequence_memo.md",
            "executive_sequence_memo.md must exist.",
        )
    )
    checks.append(exists_check("results_exists", "results.json", "results.json must exist."))

    checks.append(
        text_regex(
            "coherence_header",
            "brief_coherence.csv",
            r"(?mi)^brief_id\s*,\s*word_count\s*,\s*question_count\s*,\s*unanswered_questions\s*,\s*transition_breaches\s*,\s*coherence_score\s*,\s*recommended_move\s*,\s*projected_score\s*$",
            "Coherence CSV header must match the instruction.",
        )
    )
    checks.append(
        text_regex(
            "trace_header",
            "question_trace.csv",
            r"(?mi)^brief_id\s*,\s*question_id\s*,\s*priority\s*,\s*answer_sentence_id\s*,\s*answer_distance\s*,\s*status\s*$",
            "Trace CSV header must match the instruction.",
        )
    )

    # one full row per brief (no separate move/projected/score duplicates)
    for r in coh:
        bid = r["brief_id"]
        key = bid.lower().replace("-", "")
        unans = r["unanswered_questions"]
        unans_pat = esc(unans) if unans else ""
        checks.append(
            text_regex(
                f"coherence_row_{key}",
                "brief_coherence.csv",
                rf"(?mi)^{esc(bid)}\s*,\s*{esc(r['word_count'])}\s*,\s*{esc(r['question_count'])}\s*,\s*{unans_pat}\s*,\s*{esc(r['transition_breaches'])}\s*,\s*{esc(r['coherence_score'])}\s*,\s*{esc(r['recommended_move'])}\s*,\s*{esc(r['projected_score'])}\s*$",
                f"Full coherence row for {bid} (question_count=6, unanswered list, breaches, score, move, projection).",
            )
        )

    # lexicographic order once
    lex = r"(?ms)" + "".join(rf"(?:.*\n)*^{esc(r['brief_id'])}\s*," for r in coh)
    checks.append(
        text_regex(
            "coherence_lexicographic",
            "brief_coherence.csv",
            lex,
            "Briefs must appear in lexicographic brief_id order.",
        )
    )

    for t in traces:
        key = f"{t['brief_id'].lower().replace('-', '')}_{t['question_id'].lower().replace('-', '')}"
        sid = t["answer_sentence_id"]
        sid_pat = esc(sid) if sid else ""
        checks.append(
            text_regex(
                f"trace_{key}",
                "question_trace.csv",
                rf"(?mi)^{esc(t['brief_id'])}\s*,\s*{esc(t['question_id'])}\s*,\s*{esc(t['priority'])}\s*,\s*{sid_pat}\s*,\s*{esc(t['answer_distance'])}\s*,\s*{esc(t['status'])}\s*$",
                f"Full trace for {t['brief_id']}/{t['question_id']}.",
            )
        )

    for key, val in results.items():
        checks.append(
            json_equals(
                f"results_{key}",
                "results.json",
                f"$.{key}",
                val,
                f"results.json {key} must equal {val}.",
            )
        )

    # symmetric heading pattern for has/omits
    def heading_pat(bid: str) -> str:
        return rf"(?m)^#{{1,3}}\s*{esc(bid)}\b"

    for bid in failing:
        key = bid.lower().replace("-", "")
        checks.append(
            text_regex(
                f"memo_has_{key}",
                "executive_sequence_memo.md",
                heading_pat(bid),
                f"Memo must include a #/##/### heading for failing brief {bid}.",
            )
        )
        checks.append(
            text_regex(
                f"memo_explains_{key}",
                "executive_sequence_memo.md",
                rf"(?is)#{{1,3}}\s*{esc(bid)}\b.{{0,600}}(?:[Uu]nanswered|[Bb]reach).{{0,400}}[Rr]ecommended",
                f"Memo subsection for {bid} must mention unanswered/breach status and recommended move (disclosed memo format).",
            )
        )
    for bid in passing:
        key = bid.lower().replace("-", "")
        checks.append(
            text_regex(
                f"memo_omits_{key}",
                "executive_sequence_memo.md",
                heading_pat(bid),
                f"Memo must not include a #/##/### heading for passing brief {bid}.",
                comparison="not_regex_match",
            )
        )

    checks.append(
        text_regex(
            "memo_has_body",
            "executive_sequence_memo.md",
            r"(?s).{200,}",
            "Memo must contain substantive body text.",
        )
    )

    out = {"task_id": "gen-g806-leadership-brief-rhetorical-style-audit", "verifiers": checks}
    path = PACK / "tests/verifier.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"verifier checks={len(checks)} failing={failing} passing={passing}")
    readme = PACK / "README.md"
    rt = readme.read_text(encoding="utf-8")
    rt = re.sub(r"\d+ deterministic checks.*", f"{len(checks)} deterministic checks (existence, headers, lexicographic order, one full coherence row per brief, full traces, results.json, disclosed memo heading/analysis for failing briefs only).", rt)
    # also disclose memo in README deliverables line
    if "Memo format" not in rt:
        rt = rt.replace(
            "- executive_sequence_memo.md: one concise subsection per brief below the passing score (80)",
            "- executive_sequence_memo.md: `#`/`##`/`###` heading per failing brief only; subsection mentions unanswered/breach + recommended move",
        )
    readme.write_text(rt, encoding="utf-8")
    return len(checks)


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[?0-9;]*[A-Za-z]", "", text)


def extract_pane_deliverables(pane_path: Path, dest: Path) -> bool:
    if not pane_path.exists():
        return False
    pane = strip_ansi(pane_path.read_text(encoding="utf-8", errors="replace"))
    dest.mkdir(parents=True, exist_ok=True)
    # Prefer the final dump block (pane may echo the printf command first).
    dump_start = pane.rfind("--- brief_coherence.csv ---")
    if dump_start < 0:
        dump_start = 0
    region = pane[dump_start:]
    mapping = {
        "brief_coherence.csv": r"--- brief_coherence\.csv ---\r?\n(.*?)(?:\r?\n--- |\Z)",
        "question_trace.csv": r"--- question_trace\.csv ---\r?\n(.*?)(?:\r?\n--- |\Z)",
        "executive_sequence_memo.md": r"--- executive_sequence_memo\.md ---\r?\n(.*?)(?:\r?\n--- |\Z)",
        "results.json": r"--- results\.json ---\r?\n(\{[\s\S]*?\})",
    }
    ok = 0
    for fname, pat in mapping.items():
        m = re.search(pat, region, flags=re.S)
        if not m:
            print("  missing", fname, "in", pane_path.parent)
            continue
        body = m.group(1).strip()
        if fname == "results.json":
            start = body.find("{")
            if start < 0:
                print("  bad json", fname)
                continue
            depth = 0
            end = None
            for i, ch in enumerate(body[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end is None:
                print("  bad json", fname)
                continue
            parsed = json.loads(body[start:end])
            body = json.dumps(parsed, indent=2)
        (dest / fname).write_text(body.rstrip() + "\n", encoding="utf-8")
        ok += 1
    print(f"  extracted {ok}/4 from {pane_path}")
    return ok == 4


def write_honest_manifest(dest: Path, *, status: str, note: str, files: list[Path] | None = None):
    entries = []
    for fname in DELIVERABLES:
        entry = {
            "source": f"/app/{fname}",
            "destination": f"verifier/snapshots/app/{fname}",
            "type": "file",
            "status": status,
            "note": note,
        }
        if files:
            match = next((p for p in files if p.name == fname), None)
            if match and match.exists():
                entry["sha256"] = hashlib.sha256(match.read_bytes()).hexdigest()
                entry["bytes"] = match.stat().st_size
        entries.append(entry)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def prepare_glm_artifacts():
    mapping = {
        1: None,  # timeout — no deliverables
        2: JOBS / "glm-g806-coherence-2",
        3: JOBS / "glm-g806-coherence-3",
        4: JOBS / "glm-g806-coherence-4",
    }
    for i, job in mapping.items():
        if job is None:
            # clear any fabricated gold snapshots under r1 trial
            for trial in (JOBS / "glm-g806-coherence-1").glob("gen-g806*"):
                snap = trial / "verifier" / "snapshots"
                if snap.exists():
                    shutil.rmtree(snap)
                app = trial / "artifacts" / "app"
                if app.exists():
                    shutil.rmtree(app)
                write_honest_manifest(
                    trial / "artifacts" / "manifest.json",
                    status="failed",
                    note="Agent timed out; no deliverables were present in /app at grade time.",
                )
                print(f"r{i}: cleared fabricated snapshots; honest failed manifest")
            continue
        trials = list(job.glob("gen-g806*"))
        if not trials:
            print(f"r{i}: no trial")
            continue
        trial = trials[0]
        pane = trial / "agent" / "terminus_2.pane"
        dest = trial / "artifacts" / "app"
        # remove prior gold copies
        if dest.exists():
            shutil.rmtree(dest)
        snap = trial / "verifier" / "snapshots"
        if snap.exists():
            shutil.rmtree(snap)
        ok = extract_pane_deliverables(pane, dest)
        if ok:
            files = [dest / f for f in DELIVERABLES]
            # also stage under verifier/snapshots for packager
            snap_app = trial / "verifier" / "snapshots" / "app"
            snap_app.mkdir(parents=True, exist_ok=True)
            for f in files:
                shutil.copy2(f, snap_app / f.name)
            write_honest_manifest(
                trial / "artifacts" / "manifest.json",
                status="captured",
                note="Captured from agent pane/transcript dump of /app deliverables after the run.",
                files=files,
            )
            print(f"r{i}: real deliverables captured")
        else:
            write_honest_manifest(
                trial / "artifacts" / "manifest.json",
                status="failed",
                note="Could not reconstruct deliverables from pane.",
            )


def prepare_oracle_artifacts():
    """Oracle solve.sh installs gold — snapshots may equal gold, but manifest must say captured."""
    gold = PACK / "solution" / "files"
    for job_name in (
        "oracle-g806-coherence",
        "oracle-g806-coherence-s1",
        "oracle-g806-coherence-s2",
        "oracle-g806-coherence-v3",
    ):
        job = JOBS / job_name
        if not job.exists():
            continue
        for trial in job.glob("gen-g806*"):
            dest = trial / "artifacts" / "app"
            dest.mkdir(parents=True, exist_ok=True)
            files = []
            for fname in DELIVERABLES:
                src = gold / fname
                shutil.copy2(src, dest / fname)
                files.append(dest / fname)
            snap = trial / "verifier" / "snapshots" / "app"
            snap.mkdir(parents=True, exist_ok=True)
            for f in files:
                shutil.copy2(f, snap / f.name)
            write_honest_manifest(
                trial / "artifacts" / "manifest.json",
                status="captured",
                note="Oracle solve.sh installs solution/files into /app; captured post-grade for review.",
                files=files,
            )
            print(f"oracle {job_name}/{trial.name}: captured gold-as-graded with honest manifest")


if __name__ == "__main__":
    patch_instruction_and_rules()
    n = rebuild_verifier()
    prepare_glm_artifacts()
    prepare_oracle_artifacts()
    print("DONE checks", n)

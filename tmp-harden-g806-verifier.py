"""Rebuild g806 verifier.json (full schema) from corrected gold + Harbor hardenings."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit"
)
PASSING = 80


def esc_re(s: str) -> str:
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


def json_equals(name: str, path: str, json_path: str, expected, why: str) -> dict:
    return {
        "name": name,
        "metadata": {"how_justification": why, "why_justification": why},
        "source": {
            "type": "file",
            "file": {
                "type": "json",
                "command": "read_file",
                "arguments": {"path": path},
            },
        },
        "assertion": {
            "type": "deterministic",
            "expected": expected,
            "deterministic": {"path": json_path, "comparison": "equals"},
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


def main():
    coh = list(csv.DictReader((PACK / "solution/files/brief_coherence.csv").open(encoding="utf-8")))
    traces = list(csv.DictReader((PACK / "solution/files/question_trace.csv").open(encoding="utf-8")))
    results = json.loads((PACK / "solution/files/results.json").read_text(encoding="utf-8"))
    memo = (PACK / "solution/files/executive_sequence_memo.md").read_text(encoding="utf-8")
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

    # lexicographic order of briefs
    lex = r"(?ms)" + "".join(rf"(?:.*\n)*^{esc_re(r['brief_id'])}\s*," for r in coh)
    checks.append(
        text_regex(
            "coherence_lexicographic",
            "brief_coherence.csv",
            lex,
            "Briefs must appear in lexicographic brief_id order.",
        )
    )

    for r in coh:
        bid = r["brief_id"]
        key = bid.lower().replace("-", "")
        unans = r["unanswered_questions"]
        unans_pat = esc_re(unans) if unans else ""
        # full row (grades previously ungraded columns)
        checks.append(
            text_regex(
                f"coherence_row_{key}",
                "brief_coherence.csv",
                rf"(?mi)^{esc_re(bid)}\s*,\s*{esc_re(r['word_count'])}\s*,\s*{esc_re(r['question_count'])}\s*,\s*{unans_pat}\s*,\s*{esc_re(r['transition_breaches'])}\s*,\s*{esc_re(r['coherence_score'])}\s*,\s*{esc_re(r['recommended_move'])}\s*,\s*{esc_re(r['projected_score'])}\s*$",
                f"Full coherence row for {bid} (counts, unanswered, breaches, score, move, projection).",
            )
        )
        checks.append(
            text_regex(
                f"move_{key}",
                "brief_coherence.csv",
                rf"(?mi)^{esc_re(bid)}\s*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,\s*{esc_re(r['recommended_move'])}\s*,",
                f"Recommended move for {bid} is {r['recommended_move']} (rules-derived).",
            )
        )
        checks.append(
            text_regex(
                f"projected_{key}",
                "brief_coherence.csv",
                rf"(?mi)^{esc_re(bid)}\s*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,\s*{esc_re(r['projected_score'])}\s*$",
                f"Projected score for {bid} is {r['projected_score']} (rules-derived).",
            )
        )
        checks.append(
            text_regex(
                f"score_{key}",
                "brief_coherence.csv",
                rf"(?mi)^{esc_re(bid)}\s*,[^,]*,[^,]*,[^,]*,[^,]*,\s*{esc_re(r['coherence_score'])}\s*,",
                f"Coherence score for {bid} is {r['coherence_score']}.",
            )
        )
        checks.append(
            text_regex(
                f"breaches_{key}",
                "brief_coherence.csv",
                rf"(?mi)^{esc_re(bid)}\s*,[^,]*,[^,]*,[^,]*,\s*{esc_re(r['transition_breaches'])}\s*,",
                f"Transition breaches for {bid} is {r['transition_breaches']}.",
            )
        )
        checks.append(
            text_regex(
                f"qcount_{key}",
                "brief_coherence.csv",
                rf"(?mi)^{esc_re(bid)}\s*,[^,]*,\s*{esc_re(r['question_count'])}\s*,",
                f"question_count for {bid} is {r['question_count']}.",
            )
        )
        if unans:
            checks.append(
                text_regex(
                    f"unanswered_{key}",
                    "brief_coherence.csv",
                    rf"(?mi)^{esc_re(bid)}\s*,[^,]*,[^,]*,\s*{unans_pat}\s*,",
                    f"Unanswered pipe list for {bid} is {unans}.",
                )
            )
        else:
            checks.append(
                text_regex(
                    f"unanswered_{key}_empty",
                    "brief_coherence.csv",
                    rf"(?mi)^{esc_re(bid)}\s*,[^,]*,[^,]*,\s*,",
                    f"Unanswered list for {bid} is empty.",
                )
            )

    for t in traces:
        key = f"{t['brief_id'].lower().replace('-', '')}_{t['question_id'].lower().replace('-', '')}"
        sid = t["answer_sentence_id"]
        sid_pat = esc_re(sid) if sid else ""
        checks.append(
            text_regex(
                f"trace_{key}",
                "question_trace.csv",
                rf"(?mi)^{esc_re(t['brief_id'])}\s*,\s*{esc_re(t['question_id'])}\s*,\s*{esc_re(t['priority'])}\s*,\s*{sid_pat}\s*,\s*{esc_re(t['answer_distance'])}\s*,\s*{esc_re(t['status'])}\s*$",
                f"Full trace for {t['brief_id']}/{t['question_id']} including priority and answer_sentence_id.",
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

    for bid in failing:
        key = bid.lower().replace("-", "")
        checks.append(
            text_regex(
                f"memo_has_{key}",
                "executive_sequence_memo.md",
                rf"(?m)^##\s*{esc_re(bid)}\b",
                f"Memo must include a subsection heading for failing brief {bid}.",
            )
        )
        checks.append(
            text_regex(
                f"memo_explains_{key}",
                "executive_sequence_memo.md",
                rf"(?is)##\s*{esc_re(bid)}\b.{{0,400}}Unanswered:.{{0,200}}Transition breaches:.{{0,200}}Recommended:",
                f"Memo subsection for {bid} must explain unanswered, breaches, and recommended move.",
            )
        )
    for bid in passing:
        key = bid.lower().replace("-", "")
        checks.append(
            text_regex(
                f"memo_omits_{key}",
                "executive_sequence_memo.md",
                rf"(?m)^##\s*{esc_re(bid)}\b",
                f"Memo must omit subsection for passing brief {bid}.",
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

    # sanity against gold
    for bid in failing:
        assert re.search(rf"(?m)^##\s*{bid}\b", memo), bid
    for bid in passing:
        assert not re.search(rf"(?m)^##\s*{bid}\b", memo), bid

    out = {"task_id": "gen-g806-leadership-brief-rhetorical-style-audit", "verifiers": checks}
    path = PACK / "tests/verifier.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"checks={len(checks)} failing={failing} passing={passing} -> {path}")


if __name__ == "__main__":
    main()

"""Rebuild g806 gold from message_rules.md (Harbor-correct)."""
from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

PACK = Path(
    r"C:\Users\Haseeb Mirza\Documents\Codex\2026-08-17\this-is-the-very-beginning-of\tasks\NONC-B1-1001634\gen-g806-leadership-brief-rhetorical-style-audit"
)
PASSING = 80


def half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def parse_qids(raw: str) -> list[str]:
    raw = (raw or "").strip().strip('"')
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def load_sentences():
    rows = list(csv.DictReader((PACK / "environment/input/brief_sentences.csv").open(encoding="utf-8")))
    by = defaultdict(list)
    for r in rows:
        r["position"] = int(r["position"])
        r["word_count"] = int(r["word_count"])
        r["qids"] = parse_qids(r.get("question_ids", ""))
        by[r["brief_id"]].append(r)
    for bid in by:
        by[bid].sort(key=lambda x: x["position"])
    return by


def load_questions():
    rows = list(csv.DictReader((PACK / "environment/input/executive_questions.csv").open(encoding="utf-8")))
    rows.sort(key=lambda r: r["question_id"])
    return rows


def apply_move(sents: list[dict], sentence_id: str, to_pos: int) -> list[dict]:
    ordered = deepcopy(sorted(sents, key=lambda x: x["position"]))
    idx = next(i for i, s in enumerate(ordered) if s["sentence_id"] == sentence_id)
    item = ordered.pop(idx)
    insert_at = max(0, min(len(ordered), to_pos - 1))
    ordered.insert(insert_at, item)
    for i, s in enumerate(ordered, 1):
        s["position"] = i
    return ordered


def question_coverage(sents: list[dict], all_qids: list[str]) -> dict[str, str | None]:
    """Map question -> earliest sentence_id answering it."""
    ordered = sorted(sents, key=lambda x: x["position"])
    ans: dict[str, str | None] = {q: None for q in all_qids}
    for s in ordered:
        for q in s["qids"]:
            if q in ans and ans[q] is None:
                ans[q] = s["sentence_id"]
    return ans


def score_brief(sents: list[dict], all_qids: list[str]) -> dict:
    ordered = sorted(sents, key=lambda x: x["position"])
    score = 100.0
    breaches = 0

    # opening
    if ordered[0]["purpose"] != "decision":
        score -= 15
        # opening penalty is NOT a transition_breach (Harbor/gold base counts)

    # transitions
    for i in range(1, len(ordered)):
        prev, cur = ordered[i - 1], ordered[i]
        if cur["purpose"] == "decision":
            score -= 10
            breaches += 1
        if cur["purpose"] == prev["purpose"]:
            score -= 5
            breaches += 1

    # answer distances
    cov = question_coverage(ordered, all_qids)
    pos_by_id = {s["sentence_id"]: s["position"] for s in ordered}
    unanswered = []
    traces = []
    for q in all_qids:
        sid = cov[q]
        if sid is None:
            score -= 20
            unanswered.append(q)
            traces.append(
                {
                    "answer_sentence_id": "",
                    "answer_distance": -1,
                    "status": "unanswered",
                    "question_id": q,
                }
            )
        else:
            dist = pos_by_id[sid] - 1
            if dist > 5:
                score -= 5
            traces.append(
                {
                    "answer_sentence_id": sid,
                    "answer_distance": dist,
                    "status": "answered",
                    "question_id": q,
                }
            )

    words = sum(s["word_count"] for s in ordered)
    if words > 220:
        score -= 10

    final = half_up(score)
    return {
        "score": final,
        "breaches": breaches,
        "words": words,
        "unanswered": unanswered,
        "coverage": cov,
        "traces": traces,
    }


def best_move(sents: list[dict], all_qids: list[str], base: dict) -> tuple[str, int]:
    base_cov = {q: base["coverage"][q] for q in all_qids}
    base_score = base["score"]
    candidates = []
    n = len(sents)
    for s in sents:
        for to_pos in range(1, n + 1):
            if to_pos == s["position"]:
                continue
            moved = apply_move(sents, s["sentence_id"], to_pos)
            sc = score_brief(moved, all_qids)
            # coverage must not change (same answering sentence ids per question)
            if sc["coverage"] != base_cov:
                continue
            if sc["score"] < base_score:
                continue
            dist = abs(to_pos - s["position"])
            move = f"{s['sentence_id']}:{s['position']}->{to_pos}"
            gain = sc["score"] - base_score
            candidates.append((gain, -dist, s["sentence_id"], move, sc["score"]))
    if not candidates:
        # no improving move — pick no-op? Harbor requires a move. Prefer best non-lowering
        # If nothing improves, allow equal score with smallest move (stay/coverage ok)
        for s in sents:
            for to_pos in range(1, n + 1):
                if to_pos == s["position"]:
                    continue
                moved = apply_move(sents, s["sentence_id"], to_pos)
                sc = score_brief(moved, all_qids)
                if sc["coverage"] != base_cov:
                    continue
                if sc["score"] < base_score:
                    continue
                dist = abs(to_pos - s["position"])
                move = f"{s['sentence_id']}:{s['position']}->{to_pos}"
                candidates.append((0, -dist, s["sentence_id"], move, sc["score"]))
    if not candidates:
        # absolute last resort: report a zero-gain identity-like best equal (shouldn't happen)
        s0 = sorted(sents, key=lambda x: x["sentence_id"])[0]
        return f"{s0['sentence_id']}:{s0['position']}->{s0['position']}", base_score
    candidates.sort(key=lambda t: (-t[0], -t[1], t[2]))
    # sort: largest gain, then smallest movement distance (we stored -dist), then sentence id
    best = candidates[0]
    return best[3], best[4]


def main():
    by = load_sentences()
    questions = load_questions()
    all_qids = [q["question_id"] for q in questions]
    qprio = {q["question_id"]: q["priority"] for q in questions}

    coherence_rows = []
    trace_rows = []
    memo_parts = ["# Executive sequence memo", ""]
    total_unanswered = 0
    total_breaches = 0
    scores = []

    for bid in sorted(by.keys()):
        sents = by[bid]
        base = score_brief(sents, all_qids)
        move, proj = best_move(sents, all_qids, base)
        # verify move doesn't lower
        assert proj >= base["score"], (bid, move, base["score"], proj)
        unanswered = "|".join(base["unanswered"]) if base["unanswered"] else ""
        coherence_rows.append(
            {
                "brief_id": bid,
                "word_count": base["words"],
                "question_count": len(all_qids),
                "unanswered_questions": unanswered,
                "transition_breaches": base["breaches"],
                "coherence_score": base["score"],
                "recommended_move": move,
                "projected_score": proj,
            }
        )
        scores.append(base["score"])
        total_unanswered += len(base["unanswered"])
        total_breaches += base["breaches"]

        for tr in sorted(base["traces"], key=lambda x: x["question_id"]):
            trace_rows.append(
                {
                    "brief_id": bid,
                    "question_id": tr["question_id"],
                    "priority": qprio[tr["question_id"]],
                    "answer_sentence_id": tr["answer_sentence_id"],
                    "answer_distance": tr["answer_distance"],
                    "status": tr["status"],
                }
            )

        if base["score"] < PASSING:
            memo_parts.append(f"## {bid} (score: {base['score']})")
            memo_parts.append(
                f"Unanswered: {unanswered or 'none'}. Transition breaches: {base['breaches']}. Recommended: {move} (projected {proj})."
            )
            memo_parts.append("")

    # write coherence
    out_dir = PACK / "solution/files"
    with (out_dir / "brief_coherence.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "brief_id",
                "word_count",
                "question_count",
                "unanswered_questions",
                "transition_breaches",
                "coherence_score",
                "recommended_move",
                "projected_score",
            ],
        )
        w.writeheader()
        w.writerows(coherence_rows)

    with (out_dir / "question_trace.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "brief_id",
                "question_id",
                "priority",
                "answer_sentence_id",
                "answer_distance",
                "status",
            ],
        )
        w.writeheader()
        w.writerows(trace_rows)

    (out_dir / "executive_sequence_memo.md").write_text("\n".join(memo_parts).rstrip() + "\n", encoding="utf-8")

    passing = sum(1 for s in scores if s >= PASSING)
    failing = len(scores) - passing
    avg = round(sum(scores) / len(scores) + 1e-12, 2)  # 2 decimal half-ish via round banker's — use explicit
    # explicit 2dp half-up
    avg_raw = sum(scores) / len(scores)
    avg = math.floor(avg_raw * 100 + 0.5) / 100

    results = {
        "brief_count": len(scores),
        "passing_briefs": passing,
        "failing_briefs": failing,
        "avg_score": avg,
        "total_unanswered": total_unanswered,
        "total_breaches": total_breaches,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (PACK / "solution/golden_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    print("COHERENCE:")
    for r in coherence_rows:
        print(r)
    print("RESULTS", results)


if __name__ == "__main__":
    main()

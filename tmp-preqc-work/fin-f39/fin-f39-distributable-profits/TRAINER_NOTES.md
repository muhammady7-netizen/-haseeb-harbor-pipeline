# TRAINER_NOTES — NONC-B1-1000070 / fin-f39-distributable-profits

**Trainer:** Muhammad Haseeb Younas
**Started:** Aug 2026

## Package review

Gold v3 soft-ease: distributable 2,195,000; paid 750,000; max further 1,445,000; proposed 1,420,000 lawful. Verifiers: 32 structured checks (schedule + anchored memo + results.json). Arithmetic unchanged from v2.

## Trainer edits

1. v2 fair densify (policy-stated traps).
2. v3 soft-ease after GLM v2 0/5 near-misses: broaden listed/Denby/declared-interim schedule anchors to accept paraphrase-safe "no adjustment" / "not yet paid" language (not only literal amount 0); slightly broaden memo anchors; keep non_distributable_on_schedule as residual densifier. Fractional test.sh retained.
3. Recomputed gold unchanged; re-oracle 1.0 + stability 2× @ 1.0.

## Harbor (authoritative v4)

| Job | Reward |
|-----|--------|
| oracle-f39-v3b | 1.0 |
| oracle-f39-stability-v3b-a | 1.0 |
| oracle-f39-stability-v3b-b | 1.0 |

**GLM v2:** 0/5 @ 1.0 (near-misses 0.84–0.94).
**GLM v3:** 0/5 @ ~0.9687.
**GLM v4:** **1/5** @ 1.0 (1.0, 0.9677, 0.9677, 0.9355, 0.9677); first-four **1/4**.

## Ship

- QC zip: `UPLOAD-THIS-TO-QC-fin-f39.zip` from v4 battery (in band).
- Harden script: `harden_f39_v3.py`

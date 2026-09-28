# Task

I run release campaigns at a small independent label and the rock single we put out last month closed its five-week push a long way short of the streams the plan promised the artist. Before I sit down with them I want to know where that shortfall actually went, not a story about it. `input/channel_plan.csv` is what each channel was meant to deliver and what the plan assumed it would convert at, `input/placement_log.csv` is every placement we booked and when it actually went out, `input/streaming_ledger.csv` is what came back week by week and `input/campaign_calendar.csv` is the weeks the push covered. `input/attribution_note.md` is the method the label agreed and it is the only thing that settles how a gap gets split. One or two of these channels read one way off the ledger and another once the method is applied to them, so please work each one all the way through rather than going on the headline. Save `shortfall_attribution.csv`, write `campaign_review.md` for me, and put the campaign figures in `results.json`. File layout is in `input/submission_format.md`.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `shortfall_attribution.csv` — Per-channel split of the shortfall to target into the three parts the note fixes
    - `campaign_review.md` — A short note for the label head on where the push's shortfall sits
    - `results.json` — a JSON object with the keys `counted_placement_count`, `placements_effect_streams`, `conversion_effect_streams`, `residual_reach_effect_streams`, `shortfall_to_target_streams`
- The exact headers, key sets, allowed values and worked examples are specified in `input/submission_format.md` — follow it precisely.
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.

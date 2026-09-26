# Submission format

Deliver exactly these files, in your working directory:

- `shortfall_attribution.csv` — Per-channel split of the shortfall to target into the three parts the note fixes
- `campaign_review.md` — A short note for the label head on where the push's shortfall sits
- `results.json` — a JSON object; see below.

## `shortfall_attribution.csv`

Header, exactly: `channel_id,counted_placements,placements_effect_streams,conversion_effect_streams,residual_reach_effect_streams,shortfall_to_target_streams`
One row per record, keyed by `channel_id`.
One row per channel in `input/channel_plan.csv`, in that file's order. `counted_placements` is a whole number of placements; every other figure is a whole number of streams, a part that is zero written `0` and a part that ran the other way written with a leading minus sign.
For every row, `placements_effect_streams`, `conversion_effect_streams` and `residual_reach_effect_streams` add to `shortfall_to_target_streams` exactly, with nothing left over.
Write `counted_placements`, `placements_effect_streams`, `conversion_effect_streams`, `residual_reach_effect_streams`, `shortfall_to_target_streams` as plain numbers: no thousands separators, no currency symbols, and no more decimal places than the source data carries (`6` or `6.0`, never `6,000` or `$6`).

Example (sample row):

```
channel_id,counted_placements,placements_effect_streams,conversion_effect_streams,residual_reach_effect_streams,shortfall_to_target_streams
CH-00,0,0,0,0,0
```

## `campaign_review.md`

A short prose note for the label head. Name, by its id as the channel plan prints it, the one channel whose shortfall the method leaves entirely to a single part of the split, and name that part — beside it in the same paragraph. State two figures as findings, each one taken from the register you deliver: `Conversion effect`, the campaign total of the conversion part, and `Counted placements`, the number of placements counted across every channel. At least sixty words of prose. Each figure stands beside its label once, stated as the finding — not offered as one of two candidates.

## `results.json`

A JSON object with exactly these keys and nothing else:

- `counted_placement_count` — number
- `placements_effect_streams` — number
- `conversion_effect_streams` — number
- `residual_reach_effect_streams` — number
- `shortfall_to_target_streams` — number

Shape example (sample values):

```json
{
  "counted_placement_count": 0,
  "placements_effect_streams": 0,
  "conversion_effect_streams": 0,
  "residual_reach_effect_streams": 0,
  "shortfall_to_target_streams": 0
}
```

Every figure is a total of one column of the register you deliver, taken across every channel. `counted_placement_count` is the total of the `counted_placements` column, and `placements_effect_streams` is the total of the `placements_effect_streams` column.

`conversion_effect_streams` is the total of the `conversion_effect_streams` column, `residual_reach_effect_streams` the total of the `residual_reach_effect_streams` column, and `shortfall_to_target_streams` the total of the `shortfall_to_target_streams` column. The first three stream totals add to the fourth exactly.

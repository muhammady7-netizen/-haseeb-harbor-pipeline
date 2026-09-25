# Release campaign attribution — standing method, rev 4

This note is the sole authority for how a single's shortfall to its streaming target is
split across the channels that carried the campaign. The campaign being measured is the
`We the People` release push, and the analysis is carried out as at 2026-09-18, once
the window has closed; nothing in it depends on the date it is read.

## 1. Scope

Every channel listed in `channel_plan.csv` is measured, in that file's order. The
campaign window is the set of weeks `campaign_calendar.csv` marks `yes` (case-insensitive) in its
`in_campaign_window` column; a week it marks `no` sits outside the push and
belongs to no channel's figures. Every figure this analysis produces is a whole number
of streams.

## 2. Which placements count as delivered

**2.1** A placement is counted in the week it ran, as `placement_log.csv` records that
week. Where a placement ran in a week other than the one it was planned for, it is still
counted, provided the week it ran falls inside the campaign window: a channel's target is
measured across the whole window rather than week by week, so a booking that slipped
within the window is a placement the channel delivered.

**2.2** A placement whose `ran_week` falls outside the campaign window is not counted at
all. It is spend that landed after the push and belongs to the next review.

**2.3** A placement whose `placement_status` is `cancelled` never ran and is not
counted. A booking is not a delivery.

**2.4** A placement whose `offer_type` is `guaranteed_streams` is a bought-stream package
rather than a promotional placement, and is not counted under this section.

## 3. Reading the ledger

**3.1** A channel's delivered reach and delivered streams are the totals of its rows in
`streaming_ledger.csv` for weeks inside the campaign window. A ledger row for a week
outside the window is counted in neither total.

**3.2** A ledger row naming a placement whose `offer_type` is `guaranteed_streams` is not
counted: neither the reach nor the streams a bought-stream package returns are the
campaign's, and both are kept out.

**3.3** A ledger row naming no placement at all is organic listening the release earned
for itself, and is counted in full.

**3.4** A ledger row carrying negative streams is a platform correction and is counted as
it stands, sign included. It is neither dropped nor reversed.

**3.5** A ledger row naming a placement that does not appear in `placement_log.csv` is
treated as organic listening under 3.3, because a placement the log does not record is
a placement the campaign did not book.



**3.6** A ledger row whose `placement_id` is `NULL`, `N/A`, or any non-empty
string that is not a valid placement identifier in `placement_log.csv` is
treated as organic listening under 3.3.

**3.7** A ledger row carrying negative `delivered_reach` is a platform
correction and is counted as it stands, sign included, exactly as 3.4 treats
negative streams.

**3.8** Fractional `delivered_streams` or `delivered_reach` are rounded to
the nearest whole number, halves away from zero, before being added to the
channel's totals.

**3.9** An empty `delivered_streams` or `delivered_reach` field is treated
as zero.

**3.10** Whitespace in `placement_id`, `channel_id`, `campaign_week`,
`placement_status`, and `offer_type` fields is stripped before matching.


**3.11** A ledger row carrying `delivered_reach` of 0 is counted
for its `delivered_streams` (which contributes to the channel's
total delivered streams) but contributes 0 to the conversion effect
expected streams for that row. The row is not excluded from the
ledger; its streams count, its reach does not.

**1.1** The `in_campaign_window` column is matched case-insensitively after
stripping whitespace. A week is in the campaign window if and only if its
`in_campaign_window` value, after stripping and case-folding, is `yes`.

**2.5** Week identifiers (`W1`, `W2`, ...) are matched case-insensitively
after stripping whitespace in both `placement_log.csv` and
`streaming_ledger.csv`.

**2.6** A placement whose `placement_status` is `completed` is treated as
`ran` under 2.1. Only `cancelled` placements are excluded under 2.3.


**2.7** A placement whose `offer_type` is empty is a promotional placement
that is neither guaranteed nor organic, and is counted under 2.1 exactly as
any other `ran` placement is counted.


**2.8** A placement whose `offer_type` is `partnership` is counted
under 2.1 exactly as any other `ran` placement is counted.

**4.3** The target is not prorated, does not move during the push, and is
not rounded: it is the exact value of `planned_placements` multiplied by
`planned_reach_per_placement`, multiplied again by
`planned_streams_per_1000_reach` and divided by one thousand. The shortfall
is this target less the delivered streams, rounded to a whole number
of streams per 5.5.
## 4. The plan's target

**4.1** A channel's target is its `planned_placements` multiplied by its
`planned_reach_per_placement`, multiplied again by its `planned_streams_per_1000_reach`
and divided by one thousand. It is not prorated and it does not move during the push.

**4.2** A channel's shortfall to target is its target less its delivered streams. A
channel that beat its target carries a negative shortfall.

## 5. Splitting the shortfall, in this order

The three parts below are the placements effect, the conversion effect and the residual
reach effect, and they are taken in that order.

**5.1 Placements delivered.** The channel's `planned_placements` less its counted
placements, multiplied by its `planned_reach_per_placement` and by its
`planned_streams_per_1000_reach`, divided by one thousand. This is the part of the
shortfall that is placements the campaign did not run, valued at the conversion the plan
assumed and never at the conversion the channel achieved.

**5.2 Conversion.** The channel's delivered reach multiplied by its
`planned_streams_per_1000_reach` and divided by one thousand, less its delivered
streams. This part is measured on the reach the campaign actually delivered, not on the
reach the plan assumed its placements would bring.

**5.3 Residual reach.** What is left of the shortfall once the first two parts have been
taken off. It is the reach the counted placements brought above or below what the plan
expected of them, and no amount of better creative reaches it.

**5.4 Rounding and additivity.** The placements effect is taken to the nearest whole
stream, its tie-break fixed by 5.7. The conversion effect is taken to the nearest whole
stream, halves toward zero. The residual is then the balance of the shortfall, so the
three parts add back to the shortfall exactly, per channel and across the campaign.


**5.5 Shortfall rounding.** The shortfall to target is rounded to the nearest
whole number of streams, halves toward zero, before the three parts are taken.
This makes every figure in the analysis a whole number of streams as section 1
requires, and it is taken before the placements effect and conversion effect
are computed, so the three parts add back to the rounded shortfall exactly.

**5.6 Time-dependent conversion rate.** The conversion effect is measured using
the `planned_streams_per_1000_reach` at its full rate for campaign weeks W1
through W3, and at ninety per cent of that rate for campaign weeks W4 through
W7. Each ledger row's contribution to the conversion effect is
`delivered_reach x rate x planned_streams_per_1000_reach / 1000` where `rate`
is one for weeks W1-W3 and nine-tenths for weeks W4-W7, and the row's
`campaign_week` determines which rate applies. The conversion effect is the
sum of these per-row contributions less the channel's delivered streams, taken
in place of the total-reach form in 5.2, and rounded per 5.4.

**5.7 Conditional placements-effect rounding.** The placements effect is
rounded to the nearest whole stream, halves away from zero when the channel's
shortfall to target is positive, and halves toward zero when the shortfall is
negative. The conversion effect is always rounded halves toward zero as before.


**6.1** Where a channel's shortfall to target is zero, all three parts
are zero, regardless of the intermediate computation. A channel that
met its target has no gap to attribute, and the three parts are
recorded as `0` even where the placements effect and conversion effect
computed before rounding would produce non-zero values that cancel out.

## 6. Recording it

Against every channel record how many placements were counted, the three parts and the
shortfall itself. A part that is zero is written `0`, and a part that ran the other way
is written with a leading minus sign.

## 7. Mid-campaign plan amendments

**7.1** A channel's `planned_streams_per_1000_reach` may be amended mid-campaign
by a note in this section. An amendment applies only to the channel it names,
and only to ledger rows in weeks on or after the amendment's effective week.
Where an amendment is in force, the conversion effect for affected rows uses
the amended `planned_streams_per_1000_reach` in place of the plan's value, and
the placements effect uses the plan's original value throughout.

**7.2** Amendment A1: For CH-59, the `planned_streams_per_1000_reach` is amended
to 35 (from 40) for campaign weeks W4 through W7. The original value of 40
applies for W1 through W3.

## 7. Mid-campaign plan amendments

**7.1** A channel's `planned_streams_per_1000_reach` may be amended mid-campaign
by a note in this section. An amendment applies only to the channel it names,
and only to ledger rows in weeks on or after the amendment's effective week.
Where an amendment is in force, the conversion effect for affected rows uses
the amended `planned_streams_per_1000_reach` in place of the plan's value, and
the placements effect uses the plan's original value throughout.

**7.2** Amendment A1: For CH-59, the `planned_streams_per_1000_reach` is amended
to 35 (from 40) for campaign weeks W4 through W7. The original value of 40
applies for W1 through W3.
**7.3** Amendment A3: For CH-61, the `planned_streams_per_1000_reach` is amended
to 35 (from 40) for campaign weeks W4 and W5. The original value of 40 applies
for all other weeks.

**7.4** Amendment A4: For CH-61, the `planned_streams_per_1000_reach` is further
amended to 25 (from 35) for campaign week W7. Where both A3 and A4 could apply,
the amendment naming the later week takes precedence. The original value of 40
applies for W1 through W3.

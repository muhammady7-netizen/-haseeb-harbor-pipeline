# Release campaign attribution — standing method, rev 4

This note is the sole authority for how a single's shortfall to its streaming target is
split across the channels that carried the campaign. The campaign being measured is the
`We the People` release push, and the analysis is carried out as at 2026-09-18, once
the window has closed; nothing in it depends on the date it is read.

## 1. Scope

Every channel listed in `channel_plan.csv` is measured, in that file's order. The
campaign window is the set of weeks `campaign_calendar.csv` marks `yes` (case-insensitive after stripping) in its
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


**2.7** A placement whose `offer_type` is empty is a promotional placement
that is neither guaranteed nor organic, and is counted under 2.1 exactly as
any other `ran` placement is counted.

## 3. Reading the ledger

**3.1** A channel's delivered reach and delivered streams are the totals of its rows in
`streaming_ledger.csv` for weeks inside the campaign window. A ledger row for a week
outside the window is counted in neither total.

**3.2** A ledger row naming a placement whose `offer_type` is `guaranteed_streams` is not
counted: neither the reach nor the streams a bought-stream package returns are the
campaign's, and both are kept out.

**3.3** A ledger row naming no placement at all is organic listening the release earned
for itself, and is counted in full.


**3.5** Where a ledger row carries a fractional `delivered_streams` or
`delivered_reach`, the value is rounded to the nearest whole number,
halves away from zero, before it is summed into the channel's totals.
The channel's delivered reach and delivered streams are the sums of
these per-row rounded values.

**3.4** A ledger row carrying negative streams is a platform correction and is counted as
it stands, sign included. It is neither dropped nor reversed.

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

**5.4 Rounding and additivity.** The placements effect is taken to the nearest whole stream,
halves away from zero when the shortfall is positive and halves toward
zero when the shortfall is negative (see 5.7). The conversion effect is
taken to the nearest whole stream, halves toward zero, always. The
residual is then the balance of the shortfall, so the three parts add
back to the shortfall exactly, per channel and across the campaign.


**5.6 Time-dependent conversion rate.** The conversion effect is measured
using the `planned_streams_per_1000_reach` at its full rate for campaign weeks
W1 through W3, and at ninety per cent of that rate for campaign weeks W4
through W7. Each ledger row's contribution to the conversion effect is
`delivered_reach × rate × planned_streams_per_1000_reach / 1000` where `rate`
is one for weeks W1-W3 and nine-tenths for weeks W4-W7, and the row's
`campaign_week` determines which rate applies.

**5.7 Conditional placements-effect rounding.** The placements effect is
rounded to the nearest whole stream, halves away from zero when the
channel's shortfall to target is positive, and halves toward zero when the
shortfall is negative. The conversion effect is always rounded halves
toward zero.

## 6. Recording it

Against every channel record how many placements were counted, the three parts and the
shortfall itself. A part that is zero is written `0`, and a part that ran the other way
is written with a leading minus sign.

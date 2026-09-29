# Shortcut audit

**Goal:** find the fewest tool calls that reach a fully-passing answer, using
`instruction.md` only.

## Shortest path found

Two calls clear every deterministic content check:

1. `search_calendar(start_date=2026-05-19T00:00:00-05:00, end_date=2026-05-26T00:00:00-05:00, queries=[])`
   returns all 9 events for the window with organizer_email, status,
   eventType and attendees (with optional/responseStatus) already
   embedded - everything needed to compute all 4 counts and identify both
   named meetings and both attendee emails.
2. `draft_email(to=["morgan.thompson@maplewoodhospital.org"], subject="Confirming your attendance: Technical Interview (May 22)", body=...)`
   performs the write-back directly from step 1's own response, with no
   additional call needed to re-confirm anything.

This clears the content checks. `the_search_and_write_actually_ran`'s floor
is set to `minimum_tool_calls: 2`, matching this proven shortest path exactly
- an efficient, genuinely correct 2-call solve is NOT penalised by the floor
check. The floor only blocks a fabricated answer (zero or one gym call).

## Honest accounting against the declared hops

`task.toml`'s `=== HOPS ===` block declares `hops=5, chain_depth=3, over 6
steps`. Four of those five declared hops - the Skip Level narrow re-search,
the Technical Interview narrow re-search, the Morgan Thompson email search,
and the post-write verification search - are genuinely DEPENDENT (their
purpose derives from step 1's own classification, which is why they count as
real hops under the strict-provenance definition), but they are not strictly
REQUIRED to reach a passing answer: nothing in the classification or the
write-back needs a second look at the same day once step 1's bulk response
already carries every field (organizer_email, status, eventType, attendees
with responseStatus) for every event in the window.

Shortest-path ratio: 2 calls found vs. 5 declared hops = **0.4x**, below the
general 0.6x floor this document's own methodology sets.

**This is not task padding - it is the documented, accepted shape of this
specific connector.** As recorded identically in every other email_calendar
task mined in this batch, `search_calendar` hands over the entire calendar
window, attendees included, in one call - there is no per-item fan-out to
make artificially deeper. A per-task shortcut ratio below 0.6x is already the
established, written-down reality for this connector, not a defect specific
to this task. Closing it would require either a different connector or
padding in the arithmetic sense this project explicitly forbids (do not
write the counting rule into the prompt; harden the discovery, not the
arithmetic).

**What is NOT accepted, and does not apply here:** a one-tool-call solve.
The shortest path found is two calls (one read, one write), and
`search_calendar` alone cannot satisfy the task (the write-back is a
separate, required action, and its target - which specific attendee, which
specific meeting title in the subject line - depends on classifying the
decline-vs-tentative trap first), while `draft_email` alone cannot satisfy
it either (there is nothing to write back without first reading the
calendar).

## Conclusion

Recorded honestly rather than silently passed: this connector's
read-mostly-once, write-once shape means the raw fewest-calls number (2)
sits below the 0.6x guideline against the declared hop count (5), consistent
with every other email_calendar task mined in this project to date. The task
still clears the harder, non-negotiable floor (no one-call solve). No
redesign was made in response to this finding, per the accepted per-connector
exception already on record for `email_calendar`. Unlike an earlier draft of
this task, the `tool_execution` floor (`minimum_tool_calls: 2`) now matches
this proven shortest path exactly rather than sitting one call above it - a
genuinely efficient correct solve is never penalised.

A separate, decisive check specific to this task: the shortest 2-call path
above still requires the solver to correctly classify Morgan Thompson's two
different, real responses (declined on Skip Level 1:1, tentative on
Technical Interview) from the SAME bulk response before it can write the
draft correctly - a naive shortcut that never distinguishes decline from
tentative would still make the same 2 tool calls, but would draft to the
wrong meeting, fail `no_draft_chases_the_declined_meeting`, and be caught
regardless of call count. Fewer calls does not mean an easier or less
discriminating task here.

## Window choice and the recurrence finding (round 1 harbor_check)

This task's first `harbor_check` round found that an earlier two-week window
draft (2026-05-19 to 2026-06-02) silently required an undisclosed
series-collapsing rule: the served `search_calendar` response over that
wider window returns 16 rows, not 14, because two Weekly Risk Sync
recurring series each contribute a second expanded occurrence
(`recurring_event_id` pointing back to the master) inside the window. Whether
a recurring series should count once or once per occurrence was a real,
undisclosed judgment call the instruction never resolved.

The fix actually shipped: the window was narrowed to exactly one week
(2026-05-19 to 2026-05-26, matching `instruction.md`'s own "through
2026-05-25" wording), which excludes both series' second occurrence
entirely. Confirmed live against the pinned image: `search_calendar` over
this exact window returns exactly 9 rows, with every entry - including both
Weekly Risk Sync masters - appearing exactly once. No recurring-series-
collapsing rule is ever load-bearing for this task. This is the honest fix,
not a workaround: it removes the undisclosed rule entirely rather than
disclosing a rule this connector's other mined tasks do not need.

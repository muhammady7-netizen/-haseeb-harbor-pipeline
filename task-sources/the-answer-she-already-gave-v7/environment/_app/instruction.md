# System Prompt
You are a careful task-execution agent. Use the tools provided by the configured gym to complete the user's task. Base conclusions on retrieved evidence and return the requested result in the requested format.

# Task
Pull up my calendar for 2026-05-19 through 2026-05-25 (America/Chicago). I know it's a mix of
real meetings, out-of-office blocks, focus-time holds, working-location entries, and a couple
of things other people organized that just happen to show up on my calendar too. I need the
real picture of which meetings I'm actually running are properly confirmed and which aren't.

A meeting counts as one I'm running only if I am the organizer, it is a genuine meeting (not a
focus-time hold, out-of-office block, or working-location entry), and it is actually confirmed
(not tentative or cancelled). When classifying each calendar entry, check the entry's own
organizer, eventType, and status fields — do not classify based on the title text alone. For each
such meeting, it is "fully confirmed" only if every REQUIRED (non-optional) attendee has accepted.
An optional attendee's response never affects whether a meeting is fully confirmed.

For a meeting that is not fully confirmed, look at exactly why a required attendee hasn't
accepted: someone who has DECLINED has already given a definitive answer and is not "still
waiting" on anything - there is nothing left to chase. Someone whose response is still
tentative or has not responded at all is genuinely still undecided.

Write your findings to `/workspace/meeting_confirmation_audit.json` as a single JSON object
with these keys:

- `real_meetings_count` (number): how many meetings I am actually running in the window.
- `fully_confirmed_count` (number): how many of those have every required attendee accepted.
- `still_pending_count` (number): how many of those have a required attendee who is genuinely
  still undecided (tentative or has not responded).
- `declined_required_count` (number): how many of those have a required attendee who has
  already declined.
- `still_pending_meeting` (string): the exact title of the meeting counted in
  `still_pending_count` (there is exactly one).
- `still_pending_attendee_email` (string): the email address of the required attendee who is
  still undecided on that meeting.
- `declined_meeting` (string): the exact title of the meeting counted in
  `declined_required_count` (there is exactly one).
- `declined_attendee_email` (string): the email address of the required attendee who declined
  that meeting.
- `pending_attendee_email_thread_exists` (boolean): whether an existing email thread with the
  still-pending attendee already addresses their tentative response. Search email for the
  pending attendee to find out.
- `draft_type_new_or_reply` (string): whether your confirmation draft is a new message or a
  reply to an existing thread — `"new"` or `"reply"`. Search email first to see if a thread
  exists for this attendee before deciding.
- `pending_attendee_has_other_response` (boolean): whether the still-pending attendee has
  given a definitive response (accepted or declined) on any other meeting you are running
  in the window.
- `fully_confirmed_with_unanswered_optional` (number): how many of the fully confirmed
  meetings have at least one optional attendee who has not responded.
- `total_optional_attendees` (number): the total count of optional attendee appearances across
  all the real meetings you are actually running in this window. Count each (meeting, attendee)
  pair separately — if the same person is an optional attendee on two different meetings, count
  them twice.
- `pending_attendee_other_meeting_count` (number): how many OTHER meetings you are actually
  running is the still-pending required attendee also a required attendee on? This requires
  checking every real meeting's attendee list, not just the pending one. Do not count the
  pending meeting itself.
- `pending_attendee_other_meeting_verdict` (string): on that other meeting where the
  still-pending attendee also appears, what was their response? One of "accepted", "declined",
  "tentative", or "no_response". If the pending attendee is not on any other meeting, use
  "none".
- `optional_attendee_tentative_count` (number): how many optional attendees across all meetings
  you are actually running are marked as tentative (not accepted, not declined, and not
  no-response — specifically the "tentative" response status only).
- `organizer_also_attendee_count` (number): how many of the meetings you are actually running
  also list you (the organizer) as an attendee. Check the attendee list of each real meeting —
  if the organizer's own email appears in the attendee list, that meeting counts.
- `optional_attendee_cross_meeting_count` (number): how many optional attendees appear on more
  than one of the meetings you are actually running. An optional attendee who appears on two
  different real meetings counts once, regardless of whether their response differs between
  the two.
- `non_real_meeting_events_count` (number): how many calendar entries in the window are NOT
  meetings you are actually running. This includes focus-time holds, out-of-office blocks,
  working-location entries, events organized by someone else, and events with a tentative
  status (even if you organized them).
- `attendee_needs_action_count` (number): across ALL events in the window (not just your real
  meetings), how many attendees have a response status of "needsAction" (has not responded at
  all — this is distinct from tentative, declined, or accepted).
- `pending_attendee_on_non_meeting_count` (number): how many events that are NOT meetings you
  are actually running is the still-pending required attendee also listed on as an attendee?
  Check every calendar entry in the window — including tentative events, focus-time holds,
  working-location entries, and events organized by others.
- `same_title_different_meeting_count` (number): how many events share their exact title with
  at least one other event in the window? Two events with the same title but different event
  IDs and different attendee lists are separate events that happen to share a title. Count the
  events, not the pairs.
- `optional_attendee_accepted_count` (number): how many optional attendees across all meetings
  you are actually running have response status "accepted"? Only count optional attendees on
  your real meetings, not on tentative events or working-location entries.
- `required_attendee_tentative_count` (number): how many required (non-optional) attendees
  across all meetings you are actually running have response status "tentative"? This is
  different from optional attendees who are tentative — only count required attendees whose
  response is specifically "tentative".
- `attendee_on_both_real_and_non_real_count` (number): how many unique attendee email addresses
  appear on at least one meeting you are actually running AND at least one event that is NOT a
  meeting you are running? This requires cross-referencing the attendee lists of every event
  in the window, real and non-real.

Then, for the one meeting that is genuinely still waiting on someone (not the one that was
already declined), search email for any existing thread with that attendee, then draft an
email (do not send it) to that attendee asking them to confirm their attendance, since
they're still marked as tentative. The draft body must explicitly ask the recipient to
confirm their attendance — an empty body or a body that does not mention confirming or
attending does not satisfy this requirement. Put the meeting's exact title somewhere in the
SUBJECT line of that draft. Do not put the other (already-declined) meeting's title anywhere
in the subject line, and do not draft anything else about the already-declined meeting - that
person already gave their answer and does not need to be chased about it.

State your conclusion in your reply: how many meetings you're running are properly confirmed,
which one is still genuinely open and who you drafted a confirmation request to, and which one
was already resolved by a decline (and therefore was not chased) - be specific about why the
declined one doesn't need chasing and the tentative one does.

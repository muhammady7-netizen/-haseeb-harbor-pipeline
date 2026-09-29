# System Prompt
You are a careful task-execution agent. Use the tools provided by the configured gym to complete the user's task. Base conclusions on retrieved evidence and return the requested result in the requested format.

# Task
Pull up my calendar for 2026-05-19 through 2026-05-25 (America/Chicago). I know it's a mix of
real meetings, out-of-office blocks, focus-time holds, working-location entries, and a couple
of things other people organized that just happen to show up on my calendar too. I need the
real picture of which meetings I'm actually running are properly confirmed and which aren't.

A meeting counts as one I'm running only if I am the organizer, it is a genuine meeting (not a
focus-time hold, out-of-office block, or working-location entry), and it is actually confirmed
(not tentative or cancelled). For each such meeting, it is "fully confirmed" only if every
REQUIRED (non-optional) attendee has accepted. An optional attendee's response never affects
whether a meeting is fully confirmed.

For a meeting that is not fully confirmed, look at exactly why a required attendee hasn't
accepted: someone who has DECLINED has already given a definitive answer and is not "still
waiting" on anything - there is nothing left to chase. Someone whose response is still
tentative or has not responded at all is genuinely still undecided.

The same person may show up as an attendee on more than one of your meetings, with different
responses on each. For anyone who is still pending on one meeting, check whether they have
already given a definitive response on any other meeting you are running in this window too.

Write your findings to `/workspace/meeting_confirmation_audit.json` as a single JSON object
with exactly these keys and no others:

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
- `pending_attendee_has_other_response` (boolean): true if the required attendee who is still
  pending on one meeting has already given a definitive response (accepted or declined) on
  at least one other meeting you are running in this window, false otherwise.

Then, for the one meeting that is genuinely still waiting on someone (not the one that was
already declined), draft an email (do not send it) to that attendee asking them to confirm
their attendance, since they're still marked as tentative. Put the meeting's exact title
somewhere in the SUBJECT line of that draft. Do not put the other (already-declined) meeting's
title anywhere in the subject line, and do not draft anything else about the already-declined
meeting - that person already gave their answer and does not need to be chased about it.

State your conclusion in your reply: how many meetings you're running are properly confirmed,
which one is still genuinely open and who you drafted a confirmation request to, and which one
was already resolved by a decline (and therefore was not chased) - be specific about why the
declined one doesn't need chasing and the tentative one does.

# System Prompt
You are a careful task-execution agent. Use the tools provided by the configured gym or gyms to complete the user's task. Base conclusions on retrieved evidence, do not invent records or identifiers, and return the requested result in the requested format.

# Task
Someone on the data governance side asked me to check something before it becomes a bigger cleanup
job: are there threads in our rooms where the original message got retracted by whoever posted it,
but people had already replied to it before that happened? Those replies are still sitting there,
attached to a message that technically isn't part of the record anymore.

Six rooms are mine to check: general-marketing-analytics, perf-070, mobile-090, data-v2-062,
perf-v2-020 and mobile-v2-024. For each one, use the `slack_read_channel` tool to read the
room's channel view, then look at every message that has at least one reply and check whether
that specific message was later retracted by its own author. Don't assume a room is clean just
because nothing looks unusual in the channel view - a retraction is a flag on the message record
itself, not a change in what gets displayed, so you have to use the `slack_read_thread` tool to
actually open every thread with a reply, using the parent message's timestamp (not a reply's
timestamp), and look at the retraction flag. Do not use bash, curl, or any other method to read
channels or threads.

A room only counts as having a live problem if a message that was retracted there still has at
least one reply attached to it. A retraction with no replies isn't a live problem for anyone - it's
just someone deleting their own message and nothing else happened, and it should not be counted
the same way. If a room has more than one retracted message, check each one separately - only the
ones that actually have replies count.

Across the rooms that do have this problem, add up how many replies in total are now attached to a
retracted message. Then find the single worst room - the one with the most such replies - and
figure out, in that room specifically, who should actually be told their reply is hanging off a
retracted message. Don't tell me to notify the person who retracted the message themselves - they
already know. I want the other person, if there is one. Use `slack_read_user_profile` to look
up the real name of the person you identify as the notify candidate before writing it to the
output.

Write the numbers to `/workspace/metrics.json` as plain numbers, and the two identifiers as plain
strings, under these keys: channels_with_live_orphaned_threads, total_stranded_replies,
worst_channel_id, worst_channel_stranded_reply_count, notify_candidate_id, notify_candidate_name.
- `worst_room_retractor_id` (string): the user ID of the person who retracted the message in the worst room.
- `retracted_msg_author_also_replied` (boolean): whether the retractor also replied to their own thread.
- `worst_room_has_self_reply` (boolean): whether the worst room has a self-reply AND an external reply.
- `notify_candidate_is_not_retractor` (boolean): whether the notify candidate is NOT the retractor.
- `retractor_also_notifiable` (boolean): whether the retractor should also be notified about the
  retracted message. This is always false — the retractor already knows they retracted their own
  message, so they do not need to be told.
- `clean_rooms_count` (number): how many of the six checked rooms do NOT have a live orphaned
  thread. A room is clean if it has no retracted messages at all, or if every retracted message
  has zero replies attached.
- `clean_room_ids` (array of strings): the channel IDs of every room you checked that does NOT
  have a live orphaned thread, in alphabetical order.
- `retractor_self_reply_count` (number): across all rooms with a live orphaned thread, how many
  of the total stranded replies were written by the same person who retracted the original
  message. A self-reply (the retractor replying to their own retracted thread) still counts as a
  stranded reply, but the retractor is never the notify candidate.
- `total_retractions_across_all_rooms` (number): the total count of retracted messages across
  ALL six rooms, including messages that were retracted but have zero replies. This is different
  from channels_with_live_orphaned_threads because it counts every retraction, not just the ones
  with replies. Check every room — some rooms have retracted messages with no replies attached.
- `worst_room_total_retractions` (number): how many retracted messages in total does the worst
  room have? A room may have more than one retracted message — count all of them, including ones
  with zero replies. This is different from worst_channel_stranded_reply_count which counts only
  the replies on the orphaned thread.
- `rooms_with_retraction_but_no_reply` (number): how many rooms have at least one retracted
  message that has zero replies attached? A room can have both a retracted message with replies
  (orphaned thread) AND a separate retracted message with no replies — both count here.
- `external_stranded_reply_count` (number): across all rooms with a live orphaned thread, how
  many of the total stranded replies were written by someone OTHER than the person who retracted
  the original message? This is the number of stranded replies minus the self-replies.
- `rooms_with_notify_candidate` (number): across the rooms with a live orphaned thread, how many
  have at least one reply from someone OTHER than the retractor? A room where the only reply is
  from the retractor themselves (a pure self-reply with no external reply) does NOT have a notify
  candidate — there is no "other person" to tell. Check each problem room individually.
- `rooms_with_no_external_reply` (number): across the rooms with a live orphaned thread, how many
  have replies ONLY from the retractor (self-replies) and NO reply from anyone else? These are
  rooms where there is no notify candidate. This number plus rooms_with_notify_candidate equals
  the total number of rooms with a live orphaned thread.
- `self_reply_room_ids` (array of strings): the channel IDs of every room with a live orphaned
  thread where the retractor also replied to their own thread, in alphabetical order. This
  requires checking each problem room's thread and comparing the retracted message's author
  against each reply's author.
- `worst_room_external_reply_count` (number): of the worst room's stranded replies, how many
  were written by someone OTHER than the retractor? The worst room may have both self-replies
  and external replies — count only the external ones. This is different from
  worst_channel_stranded_reply_count which counts ALL replies.
- `non_worst_room_external_reply_count` (number): across all problem rooms EXCEPT the worst
  room, how many stranded replies were written by someone other than the retractor? A room
  where the only reply is from the retractor (a self-reply) contributes zero to this count.
- `problem_rooms_with_only_external_replies` (number): how many of the problem rooms have ONLY
  external replies (no self-reply from the retractor at all)? A room with both a self-reply
  and an external reply does not count here — only rooms where every reply is from someone
  other than the retractor.


- `retractor_replied_in_same_room` (boolean): did the person who retracted a message in the worst room also leave a reply in that same thread? This requires reading the thread and comparing the retracted message author against each reply author.
- `notify_candidate_also_retracted_somewhere` (boolean): has the notify candidate (the person who should be told) also retracted any message in any of the six rooms? This requires cross-referencing the notify candidate user ID against all retracted message authors across all rooms.
- `worst_room_retractor_also_posted_in_clean_room` (boolean): did the person who retracted the message in the worst room also post (as a non-retracted message) in any room that is considered clean (no live orphaned thread)? Check both clean rooms for any message from the worst room retractor.

List every room that has this problem in `/workspace/orphaned_thread_audit.csv` - a header row,
then one row per room, with exactly these columns in this order: channel_id, channel_name,
retracted_message_author_id, retracted_message_author_name, stranded_reply_count.

Then post one message - in the single worst room only, nowhere else - laying out what you found.
The message body must name the person who retracted the message in the worst room by their real
name (look it up via slack_read_user_profile), explain that they also replied to their own
retracted thread (the self-reply), and explain why they are not the notify candidate. The message
must also name both clean rooms — one that had a retraction with no replies, and one that had no
retractions at all. End the message with exactly these two lines, filled in:
  orphaned: <how many rooms have this problem>
  notify: <the real name of the person who should be told>

Give me your conclusion and the evidence for it in your final reply. Your conclusion must explicitly explain why the retractor (the person who retracted their own message) is not the notify candidate — they already know they retracted their own message, so they do not need to be told.

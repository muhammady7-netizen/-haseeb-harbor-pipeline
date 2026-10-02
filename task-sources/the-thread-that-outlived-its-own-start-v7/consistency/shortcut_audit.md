# Shortcut audit — the-thread-that-outlived-its-own-start

## Method

The slack-gym allowlist exposes exactly 14 tools (confirmed by reading
`connectors/slack-connector/app/core/obi_tool_allowlist.py` directly): `slack_send_message`,
`slack_schedule_message`, `slack_create_canvas`, `slack_update_canvas`, `slack_search_public`,
`slack_search_public_and_private`, `slack_search_channels`, `slack_search_users`,
`slack_read_channel`, `slack_read_thread`, `slack_read_canvas`, `slack_read_user_profile`,
`slack_send_message_draft`, `slack_delete_message`.

None of them exposes a channel-level or workspace-level "this message was retracted" flag or
index. `deleted_ts` only appears on an individual message object, and only `slack_read_channel`
(top-level messages) and `slack_read_thread` (a specific thread's replies) ever return a message
object at all — confirmed by reading `api/common/utility.py`, which serializes `deleted_ts`
whenever it is set, with no filtering anywhere in `mcp/conversation_handlers.py` or
`database/managers/conversation.py`. There is no way to ask "which messages in this workspace
were retracted" in one call.

`slack_search_public` / `slack_search_public_and_private` were tried as a possible shortcut (a
single broad query that might surface every retracted-and-replied message at once without the
full per-channel/per-thread walk). Both are message full-text search over content, ranked by
relevance to a query string — they do not expose `deleted_ts` as a filterable or even a
consistently-returned field in their result shape (confirmed by reading their own
`search_messages_validation.py` / `slack_search_public_and_private_validation.py` schemas, and by
a live query against a known-retracted message's own text, which came back as an ordinary
ranked hit with no retraction indicator at all in the search result shape). They cannot replace
the per-channel `slack_read_channel` + per-thread `slack_read_thread` walk this task's graded
figures depend on.

`slack_read_channel`'s own `reply_count` field on a top-level message DOES already carry the
correct stranded-reply count for a qualifying message, once you know which message qualifies —
but knowing whether a specific message with `reply_count >= 1` was ALSO retracted requires
reading that same message's own `deleted_ts` field, which is only present in the full message
object slack_read_channel already returns. The real discipline this task tests is not extracting
a hidden number (the channel view already carries it) — it's not skipping the retraction check on
any of the 27 threads with a reply just because a room "looks clean" from a glance at the channel
view, and not conflating "this room has a retraction somewhere" with "this room has a live
orphaned thread," since two of the six rooms in scope have at least one retraction that never
generated a reply and must NOT be counted (perf-v2-020's only retraction, and data-v2-062's
second, unrelated retraction alongside its real orphaned thread).

## Result

The golden trajectory (`solution/golden_trajectory.json`, 45 steps) is the shortest path found: 6
`slack_search_channels` calls to resolve every room to its id, 6 `slack_read_channel` calls to
read every room's top-level view, 27 `slack_read_thread` calls (one per threaded post across all
six rooms — every thread has to be opened in every room, not just the four that turn out to have
a live problem, since opening the thread is the only way to confirm a message's `deleted_ts`
status alongside its reply content), 5 `slack_read_user_profile` calls (the four rooms' retracted
message authors, one of whom doubles as the account that must be ruled OUT as the notify
candidate, plus the one genuine notify candidate), and 1 `slack_send_message` write-back.

**No shortcut was found.** Every one of the 39 dependent hops (the 6 initial searches start the
chain and depend on nothing, so they are not counted as hops) is load-bearing for at least one
graded figure: dropping any single `slack_read_thread` call on a thread that turns out to have a
retracted root risks missing that room from `channels_with_live_orphaned_threads` entirely, and
dropping a `slack_read_thread` call on a thread that turns out clean still risks a false positive
if the agent instead guesses based on `reply_count` alone (which cannot distinguish a live
thread-root from a retracted one). Dropping any `slack_read_user_profile` call on a candidate
before naming it risks either an unresolved id in the CSV or, worse, silently picking the wrong
notify target between the two repliers in data-v2-062's thread. A one-tool-call solve does not
exist: even confirming a single room is clean needs a channel read and one thread read per
threaded post in it, and confirming a room IS a live problem needs the same plus, eventually, a
profile read.

A second shortcut candidate considered and rejected: relying on `reply_count` alone (visible on
the plain channel view, no thread-opening needed) to compute `total_stranded_replies` and
`worst_channel_id` directly, since `reply_count` on a qualifying message does happen to already
equal the correct per-message stranded count in this data. This was rejected as the DESIGNED
solve path (not merely tolerated) precisely because it does not, on its own, tell you WHICH
messages qualify — a message's own `deleted_ts` is not visible without reading the full message
object via `slack_read_channel`/`slack_read_thread`, and a room's live-vs-retracted status cannot
be inferred from `reply_count` alone (perf-v2-020 and one of data-v2-062's two retractions each
have `reply_count = 0` and must be excluded; the messages that DO qualify still need their
`deleted_ts` field actually read, not assumed). The mutation battery in `consistency/mutations.json`
confirms this discrimination concretely: mutating `total_stranded_replies` to 6 (the total-
retraction-count shortcut) or 38 (the sum-every-reply shortcut) each fails exactly the one check
it should, with no collateral failures or passes.

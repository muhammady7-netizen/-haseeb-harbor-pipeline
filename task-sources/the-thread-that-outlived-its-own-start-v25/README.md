# the-thread-that-outlived-its-own-start

## Summary
Slack connector task: across six rooms, find threads where the original message was retracted by its author but replies are still attached. Size the problem, name the worst room, and identify who should be notified (not the retractor).

## Difficulty
2/4 GLM-5.3 strict passes (in band). 3 interpretive discriminators: clean_rooms_count, clean_room_ids, retractor_self_reply_count.

## Verifiers
25 verifiers, all core. Flat scoring with core gate (metrics.json must exist for reward > 0).

## Oracle
1.0 on portal (content-48ee699a v7). Golden trajectory: 45 steps (6 search_channels + 6 read_channel + 27 read_thread + 5 read_user_profile + 1 send_message).

## Fixes from previous versions
- v7: Added tool disclosure (slack_read_channel, slack_read_thread, slack_read_user_profile) + parent-ts requirement
- v7: Fixed retractor_self_reply_count gold from 1 to 2 (Ellie + Levi both self-replied)
- v7: Fixed CRLF in manifest.json
- v7: Fixed healthcheck retries 40 → 150
- v7: Added core gate to test_outputs.py
- v7: Raised minimum_tool_calls from 10 to 25

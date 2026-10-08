# the-thread-that-outlived-its-own-start

## Summary
Slack connector task: find retracted messages with live replies across six rooms.

## Difficulty
2/4 GLM-5.3 strict passes (in band). 8 rubric checks create variance in message quality judging.

## Verifiers
43 verifiers, all core. Binary reward (0 or 1, not fractional). Core gate prevents do-nothing reward.

## Oracle
1.0 on portal. Golden trajectory: 45 steps (6 search_channels + 6 read_channel + 27 read_thread + 5 read_user_profile + 1 send_message).

## Gold Values (agent-detectable)
- worst_room_total_retractions = 1 (only retraction detectable via slack_read_thread)
- total_retractions_across_all_rooms = 5 (1 per room with detectable retraction)
- rooms_with_retraction_but_no_reply = 1 (perf-v2-020)
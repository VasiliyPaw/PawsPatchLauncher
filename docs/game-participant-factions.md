# Participant race and subrace transport

`20260914012000_game_participant_factions.sql` extends the existing private
activity validator with optional `race` and `subrace` fields on each participant.
Both are native IDs, 1–80 ASCII letters, digits, underscores or hyphens. Missing
and JSON-null values are accepted for older clients and unknown native state.
The launcher uses the exact ID `random` for a lobby choice that is still random.
The two choices are independent and pass through the server unchanged.

The 16 KiB envelope, 64-participant limit, current-row retention, session checks,
social visibility rules and function privileges stay the same. Regular friend
polling continues to exclude the roster. Race/subrace appear only in the existing
details response and never grant profile, avatar or friendship access.

The server still requires an explicit local participant key to identify the
publishing account. A single human in a roster is not sufficient evidence: a
viewer could be observing a saved match. Same-room conflicting claims remain
unlinked, and nicknames are never used to establish identity.

## Isolated verification

`tools/AdminDatabaseTests/run.mjs`: **5,272 checks passed**, including **123 game
activity checks**. New coverage includes linked players, bots and unknown players;
separate random lobby choices; omitted/null values and future native IDs; rejected
markup, paths, controls, wrong types and oversized strings; and preservation of the
existing identity ambiguity and social-access protections. Tests use disposable
PostgreSQL/WASM data, with no production account, friendship or message mutations.

Before applying the migration, the normalized validator function source must
still have MD5 `46fe7efeb2f9afa3fc0a3ed486c09be9`. The tested result is
`b01105abadb6bdb525395136b46be7b9`. Neither `anon` nor `authenticated` may execute
the private validator directly. The migration does not alter the public heartbeat
or details function. Production deployment and separate read-only verification
completed on 2026-09-14 with all ten contract checks true; see
`validation-launcher-0.7.9-activity.md` for the complete validation boundary.

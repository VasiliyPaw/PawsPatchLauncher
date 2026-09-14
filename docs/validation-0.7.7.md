# Launcher 0.7.7 validation — 2026-09-14

The release fixes maximized client bounds, profile re-entry, participant avatars/navigation and friendship actions. It does not change game files or the native game activity reader.

## Checks

- .NET suite: **16,192 PASS**, including 142 activity/parser checks.
- PostgreSQL/WASM suite: **5,230 PASS**, including 81 activity/participant checks. All user rows, requests and messages in this suite are synthetic and local.
- WPF participant checks: **18 RU + 18 EN**. Photo rendering, color marker, nonfriend profile navigation, add/pending/accept actions, duplicate request prevention, unchanged avatar caching, late profile/image responses and non-reentrant profile avatar.
- Existing WPF social action checks: **19 RU + 19 EN**; existing activity checks: **22 RU + 22 EN**.
- Native placement checks: **80 PASS on three monitors**, including maximized visible content and launch button entirely inside each monitor's work area, reopening maximized and restoring normal bounds. These are invisible isolated HWNDs; the user's launcher is not operated.
- Native caption/modal checks: **28 RU PASS**, plus the existing home layout checks.
- Build: no warnings or errors. Fixture screenshots reviewed at 1050 × 680.

## Server

Applied `20260914010000_game_participant_profiles.sql` and `20260914011000_profile_request_identity_lock.sql` to the existing PawsPatch production database. Transactions verified existing function bodies before alteration and the resulting bodies against the locally tested migration result before commit. Post-deployment privilege checks passed. No production account, friendship or message rows were changed for testing.

A participant must be uniquely resolved by the existing fresh room/slot identity rules in a roster visible to the viewer. Blocks, stale sessions, different rooms, bots and ambiguous claims do not grant access. This permits identity, avatar and activity viewing without granting chat, files or configuration access. Friend request UUID/username checks occur before and after locking the selected profile.

Avatars remain normalized 256 × 256 JPEGs, at most 200 KiB; originals are not uploaded or stored. Participant image caches are bounded, revision-aware, in memory and cleared on account changes. Profile navigation cancels lower-priority image downloads.

## Scope of evidence

Real two-client Steam play and identification during a live lobby/match were not run. Networking/UI checks used fake transport; production deployment verification checked definitions and privileges without using player data. The existing launcher process was left running.

Window sizing uses the monitor work area through [WM_GETMINMAXINFO](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-getminmaxinfo); it does not change the Windows taskbar or make the launcher always on top.

# Launcher 0.5.9: friends/chat candidate and save-transfer foundation

2026-09-08. Separate local candidate; no public launcher feed, release, tag, push, game or VM changes.

## Candidate

- `release_workspace_059/friends/launcher/win-x64/PawsPatchLauncher.exe`
- 72,062,523 bytes; SHA-256 `C2084AE81827690116C057EA168195729E1F2A7194F113CCAF5EFD82A57C5581`.
- Adjacent `launcher.config.json` retains the previous candidate's signed **local** components-v2 feeds. Those G: paths are specific to this PC, not a distributable configuration for friends.
- Existing account-avatar candidate untouched. No real launcher/game was started or stopped.

## Included

- Correct Darquan Mortis attribution: he distributes the mod on the linked Discord server; no ownership claim.
- Red account deletion action; deletion feedback describes the account, not the avatar. Removed the login/register back-to-Friends action.
- Distinct email delivery quota feedback; HTTP 429 without valid JSON still reports a generic request limit. Invalid email does not start the local recovery cooldown.
- Exact-nickname requests, explicit accept/decline, outgoing cancellation, removal, bilateral blocking and unblock without automatically restoring friendship.
- Friends list on the left, selected private chat on the right instead of the changelog. Existing launcher buttons, colors, animation and RU/EN localization retained.
- Last 50 messages, 2000 UTF-16 code units per native message. Ctrl+Enter sends. Plain text only, never rendered as HTML or executed.
- Stable random message ID persisted before sending. DPAPI-encrypted per-account queue, atomic writes, file locks, 100 pending limit, manual discard. Same sender/ID/body retry returns the original server acknowledgement; a changed payload is rejected.
- Poll/retry while Friends is open, 10-second normal interval, bounded network backoff, 60-second rate-limit wait. No background notifications, presence, older-history pagination or end-to-end encryption claim.
- Account switch/logout clears selected conversation, message controls and drafts. Queue cannot be sent under a different remembered account.

## Server

Applied `20260908060000_friends_messages.sql`, `20260908063000_social_message_validation.sql` and `20260908064000_nonempty_message_ids.sql` only to project `trdzsdclscuwwmxnepyt`.

Server constraints match the native UTF-16 length bound, Unicode whitespace/control rules and nonempty message IDs. A malicious friend cannot insert a row that would poison native chat parsing via these fields. The bounded read response also accommodates JSON Unicode escaping.

RLS-protected friendship, block and message tables; clients have SELECT only, writes use bounded authenticated RPCs. Private quota table has no client grants/policies. Actors require a confirmed, non-deleted user, active profile and live session. Ordered profile locks serialize sends and friendship changes against block/deletion.

Only accepted, unblocked participants can read/write the conversation. No email addresses exposed. Max 100 friends/pending requests, 200 blocks, 20 new requests/minute (cancel does not reset quota), 20 new messages/minute, 10000 sent messages per account. Exact retries do not consume message quota. Account deletion cascades these rows.

Security advisor reviewed: authenticated SECURITY DEFINER notices are intentional for these guarded RPCs; private RLS-without-policy is intentional deny-all. Existing warnings remain for nickname availability, auto-RLS event trigger and disabled leaked-password protection. These are not a claim that every project advisor is clean. See [Supabase advisor explanations](https://supabase.com/docs/guides/database/database-linter) and [password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Save foundation, not enabled transport

`SaveTransferGuard` validates .RSG filenames, Windows reserved names/links/format characters, size 16 bytes–20 MiB, TGCK header, exact size and SHA-256. Header/hash validation is **not** malware scanning or complete game-format parsing.

Installation is local staging with a snapshot of verified bytes. Existing files require an explicit approved prior hash; changed/disappearing files require a new decision. Atomic replacement creates an exact `.paw-backups/*.bak` copy; game-running checks and cancellation abort before commit. Tests use generated fixtures in temporary directories only.

**Not implemented/enabled yet:** save upload/download, private save bucket/authorization, cloud retention/deletion cleanup, configuration-message import UI. Consequently this stage does not claim a two-account cloud-file isolation test. Complete that transport and its blocked/outsider/account-deletion tests before exposing Send save.

## Verification

- .NET suite: **6014 PASS**, including **77** new social/save-foundation checks.
- Account UI: **89 RU + 89 EN**; Social UI: **20 RU + 20 EN**; help attribution: **19 RU + 19 EN**; motion: **35**.
- Account Edge mocked suite: **24/24**, including WPF-normalized avatar fixture, no real Auth writes.
- SQL `supabase/tests/social_access.sql`: PASS in BEGIN/ROLLBACK with two participants plus an outsider. Checks direct table grants/RLS, crossed requests, explicit acceptance, both directions of blocks, removal, retry/id conflict, limits, unconfirmed/deleting/revoked actors and anonymous rejection.
- Post-test new tables contain zero friendships, blocks, messages and quota rows: fixtures left no residue.
- Builds/publish succeeded without warnings. `git diff --check` passed (existing LF/CRLF notices only).
- Detached WPF render/layout inspected at RU 1440x900 and EN 1050x680. Narrow windows intentionally scroll; controls remain reachable. No actual user UI was operated.

## Manual gate before release

Use two launcher instances on different PCs/accounts: send/accept a request, exchange messages, disconnect/reconnect after Send, restart with a queued message, then block/unblock/remove. Check no duplicates, correct empty/guest view and no stale private UI after changing account. This manual acceptance has not been performed by the agent.

Resend DNS/SMTP setup remains a separate pending step; no SMTP credentials were read or changed by this stage. Do not start a public release or activate save transfers before manual chat acceptance and completion of transport tests.

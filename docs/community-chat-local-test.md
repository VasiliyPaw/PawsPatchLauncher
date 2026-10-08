# Community chat — local test, 2026-10-08

## Delivery

- Local, self-contained Windows x64 EXE; release feeds, tags and public launcher version unchanged.
- Output: `../../outputs/community-chat-local/PawsLauncher-Chat-Test.exe`.
- SHA-256: `DBC31051999C890F6B24582A367C5304E73380F540390A03A9C71F1750597202`.
- Build: `dotnet publish src/PawsPatchLauncher/PawsPatchLauncher.csproj -c Release -r win-x64 --self-contained true -p:CommunityChatTestBuild=true`.
- Separate settings/session root: `%LOCALAPPDATA%\PawsPatchLauncher-CommunityTest`; no production credentials copied. The first login is independent of the installed launcher's local profile, but existing server session rules still apply.
- Self-update disabled in this test build. No game files are modified just by opening the test launcher.

## Implemented

- Persistent community column on all pages, initially 35% of available workspace width, constrained to usable bounds. Native mouse divider, keyboard arrows, double-click/Home reset; saved width survives page switches/restarts and temporary display-size clamping.
- Page content uses the freed width when chat narrows. Components settings wrap; narrow Friends view switches between list and conversation while keeping community visible. Hidden private conversations do not mark incoming messages read.
- Separate RU and EN channels with remembered selection, per-channel read positions, drafts and scroll position. A guest can read public messages and sees a sign-in action instead of a composer.
- History loads in pages of 100, with at most 200 message controls mounted. Older pages are available by scrolling or the earlier/later buttons; jumping to the newest cached messages also works offline. No remote media or executable rich content.
- User-approved retention is independent for RU and EN: the send that reaches 10,000 messages removes the oldest 5,000 from that channel. Retention, moderation of old messages, account removal and identity changes invalidate older cached pages. A disconnected client never joins disjoint windows while hiding a gap.
- Reconnect/backoff, immutable IDs for safe explicit retries, server rate limits (3 seconds between posts, 10 per minute across channels), 1000 Unicode code points per message.
- Shared private-chat glyph picker and `ChatMessageText` rendering, including Shift for multiple insertions, normal edit/copy commands and independent private/community drafts. No duplicate picker implementation.
- Public names open the existing profile/friend-request flow. Users can remove their own messages; moderators can remove messages according to existing roles. Removed text is not returned by the public endpoint. Banned/deleting accounts cannot post.
- Unchanged histories return a short revision response and skip history merging/layout. Only changed/new controls are reconciled using hash sets; selected text and the visible scroll anchor survive arrivals. At most four visible new rows animate through the existing private-chat arrival helper. Reads are asynchronous, UI application yields to input/render, concurrent polls are excluded, minimized windows defer rendering, and unread totals are cached independently of typing.
- A late poll cannot replace a newer send/removal. Histories/drafts are held in memory, not silently sent on reconnect/restart.
- Release history opens in a resizable modal via a history icon with a gold unread indicator. Progress/cancel/error actions remain next to the page's bottom actions.

## Validation

- Full launcher suite: **34,129 PASS**, including **81 community client checks**.
- Isolated PostgreSQL/WASM migration suite: **12,189 PASS**, including **5,045 community checks**. Verified both retention thresholds, every retained row across 50 pages, retries, access control and old-cache invalidation. No production mutations during tests.
- Community WPF UI checks: **52 RU + 52 EN**. Includes native splitter drag events, page expansion, persistence, channel isolation, drafts, selected text/row identity, history navigation, trim reset, stale-response guard, reconnect, small composer layout and the shared glyph picker.
- Private glyph regression: **62 RU + 62 EN** (`--chat-glyph-checks`), including Shift, dismissal, edit commands and no interception of ordinary typing. Twenty unchanged community polls took 9 ms / 7 ms in isolated UI fixtures; this is not a production network benchmark.
- The broader legacy `--chat-interaction-checks` runner also invokes `FriendSettingsChecks`. That separate configuration-copy fixture is not certified here: its component-count expectation is stale (8 instead of 9); temporarily adjusting it exposed an `inactive_update` assertion as well. The temporary fixture change was reverted. Its failed log is retained in `private-chat-ui-v2.log`; no friend-copy implementation was changed by this update.
- Built EXE startup smoke: `window-ready.txt`, version `0.8.13.0`, process 23520, no error log. The dedicated smoke process was stopped afterward. Game not launched.
- UI render images and test logs are in `../../outputs/community-chat-local/`. Message data in the UI check images is an isolated fixture, not real community content.

## Server deployment — applied 2026-10-08

Applied the complete `supabase/migrations/20261008000000_community_chat.sql` transaction through the authorized SQL Editor in Supabase project `trdzsdclscuwwmxnepyt`. The UI returned `Success. No rows returned`. Saved executed SQL matches the source exactly after line-ending normalization.

Live endpoint verification:
- Anonymous RU and EN reads: HTTP 200, `status: ok`, empty initial histories.
- Repeated reads with known revision: `unchanged: true` in each channel.
- Guest send with null payload: HTTP 401 / PostgreSQL 42501, permission denied. No message created.
- Evidence: `server-migration-success.jpg`, `server-verification.json`, `applied-community-chat.sql`.

Signed-in posting, cross-client delivery and deletion still require manual live acceptance with the test EXE. No public test messages were sent. The 10,000/5,000 retention and permissions were validated in the isolated database suite listed above; production history was not populated for testing.

The browser failure was a missing IAB route for this conversation, not an SQL migration failure. Once the desktop registered this conversation's browser sidebar route, browser access recovered.

The EXE remains local-only; production release feeds and launcher version were not changed.
## UI revision 3 — 2026-10-08

- Splitter gold highlight follows hover/drag only; retained keyboard focus no longer leaves it highlighted.
- Guest hint shortened to “Войдите, чтобы написать.” / “Sign in to write.”
- Release-history action uses a document/list icon.
- Compact vector-flag EN then RU buttons at the top right; unread counts remain separate and capped visually at 99+.
- Fresh profiles start in EN; an existing saved selection is preserved.
- Updated community UI checks: 56 RU and 56 EN passed, including focused splitter state, default language and saved selection across window construction.
- Release build: zero warnings/errors. Published test EXE reached window-ready marker; only its own smoke process was closed. Git whitespace check passed.
- New test executable: `v3/PawsLauncher-Chat-Test.exe`; SHA-256 `53DB14C7DAA8E7A030EF1D203BEE1142B9FDB42ADB0F72E4DBAB8EC33B239DB3`.
- Existing running test/production launchers were not replaced or stopped. No public release or server changes in this UI revision.
## UI revision 4 — 2026-10-08

- Added vector conversation icon and notification menu: muted / mentions only (default) / all messages. Local selection persists; global notification sound/volume preferences still apply.
- Notifications use the existing private-message audio player, at most once per poll. Per-account, per-channel watermarks suppress initial history, repeated reads, own/deleted messages and muted backlog. No OS toast mechanism was added.
- Complete @username matching is case-insensitive. Matching rows are highlighted for that account. Nickname clicks insert @username at the current caret without replacing the draft.
- Avatar clicks open existing own/friend profiles; other authors have a public identity card containing the name and username already visible in chat plus an Add friend action. No stranger presence, configuration, private account data or unrestricted avatar endpoint was exposed. Avatar images reuse existing authorized caches; otherwise a silhouette is shown.
- Release history uses a custom dark caption, native window resizing, close/Escape and integrated document icon, retaining the existing filters and changelog rendering.
- Full launcher suite: 34,154 PASS, including notification baselines and mention boundaries. Community WPF checks: 65 RU + 65 EN; verified menu selection/persistence, mention insertion/highlight, avatar profile click, history caption and existing chat regressions. Visual fixtures saved in v4; these messages were never sent to production.
- Test EXE startup reached ready marker; only that smoke process was stopped. Build and whitespace checks passed.
- Executable: v4/PawsLauncher-Chat-Test.exe; SHA-256 AC327C9B2490E7FDE516F4E8783D45031C65DECB7F67F100BC3844015A462970.
- Local test only: no server migration, publication or public chat messages in this revision.

## 0.9.0 release validation — 2026-10-08

- Release source version 0.9.0. Production build omits CommunityChatTestBuild and the local test marker.
- Full launcher suite: 34,154 PASS; isolated database suite: 12,189 PASS.
- WPF RU and EN: community 65 each, private chat keyboard/glyph interaction 62 each, release history 24 each, friend configuration 639 each. Default home layout and transfer checks also passed.
- Fixed an existing cross-mod configuration-copy bug: checking an incoming Arcane Wars ×2 configuration used the currently selected mod. Both preflight and application now use the incoming selection. The inactive-mod update scenario covers this path.
- Updated older UI fixtures for the ninth component and the separate history dialog; friend-copy tests use an isolated catalog cache.
- Production community migration matches the checked-in SQL. Public EN/RU reads succeeded; no test messages were posted.
- Visual fixtures reviewed for the dark history dialog. Privacy policy now describes public guest reads and per-channel retention.
- Publication uses the tag workflow and verifies the resulting immutable EXE/ZIP and all four signed update catalogs. Game packages and existing patch histories remain unchanged.

## UI revision 5 — 2026-10-08

- Community avatars and author names have no hover fill or border. Author links are limited to the text width; avatar profile navigation remains available.
- Community messages reuse the private-message copy button, including hover/focus visibility and copied feedback. Removed messages have no copy button.
- Rendered-message context menus omit Copy and Select all; keyboard selection and Ctrl+C remain available. Empty menus do not open. Available deletion actions remain, and actions without icons no longer reserve an empty icon column. Composer editing menus are unchanged.
- The own-profile header has a smaller, subtler highlight. Clicking it again returns to the preceding page.
- WPF checks: community 73 RU + 73 EN; account 114 RU + 114 EN; shared message copy/audio 38; text selection 39. Build and whitespace checks passed. Final evidence: `v5-ui-verified.log`; visual fixtures are isolated local messages.
- Self-contained test EXE reached the startup-ready marker as version 0.9.0. Only its own smoke process was closed.
- Executable: `v5/PawsLauncher-Chat-Test.exe`; SHA-256 `7F6B53788F1B731D32F396C4F4AAC0BD20233DA1B75E89680BA6445C76AFC554`.
- Local test only; no publication, server changes or public chat messages in this revision.

## UI revision 6 — 2026-10-08

- Public author cards show Sign in for guests and Add friend for members. The guest action opens the account form.
- Author avatars load without authentication through a narrow Storage read policy: only the fixed avatar.jpg for an author with a retained, non-removed community message. Other avatars, buckets and private presence remain inaccessible. The avatar bucket remains private.
- Avatar revision changes invalidate chat snapshots. The client uses bounded downloads, background decoding, a memory cache and at most four author downloads per refresh, updating images without rebuilding message rows.
- The chat header shows the aggregate signed-in launcher online count. It uses existing server-timed presence and live-session checks with a 40-second expiry; guests are not counted. Failed requests show an unknown count.
- Community message times include seconds and align with the right edge; the copy action is to the left of the time. Private message timestamps already included seconds.
- Validation: 34,160 launcher tests; 12,199 isolated database checks; 80 community WPF checks in each of RU and EN. Guest sign-in action, avatar decode/cache, unknown online state and right-aligned seconds are covered. Build and whitespace checks passed.
- Applied `20261008010000_community_avatars_online.sql` to production; SQL Editor returned Success. Anonymous live reads succeeded for EN/RU, the online endpoint returned 2 at verification, and an author avatar returned HTTP 200 with a 14,122-byte JPEG. No public test messages were sent.
- Local test executable: `v6/PawsLauncher-Chat-Test.exe`. No launcher publication or update-feed changes.
- Final EXE startup reached the ready marker; only its isolated smoke process was closed. SHA-256: 03007CDF9A856A496E58E8ADE854ED163F1C7C14D075924C97A6F078DE9E2AF6.

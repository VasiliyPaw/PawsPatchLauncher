# Chat and friend presence candidate — 2026-09-08

## Delivery

- Host: `release_workspace_059/chat-presence/launcher/win-x64/PawsPatchLauncher.exe`
- VM share: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Chat-Presence\PawsPatchLauncher.exe`
- Guest: `\\VBOXSVR\KohanShare\PawsPatch-Chat-Presence\PawsPatchLauncher.exe`
- EXE size: 72,080,146 bytes.
- SHA-256, host and VM: `6C33A5412CFC3295E412638F80D93EFC3D459FDDB0EDFF7C4B0FDBD64508E528`.
- Host config uses the existing signed local components-v2 feeds. VM config uses the existing signed public GitHub feeds. Only EXE/config copied; no sessions, outbox, passwords or game files.
- VirtualBox read-only check: Kohan II Test running; KohanShare maps to the verified Shared directory. Guest EXE was not launched by this task.
- Previous candidate directories preserved; public releases and update feeds not published or changed.

## Changes

- Font-independent More/Send icons; no clipped more-button padding. Popup background initialized opaque so its first hover does not interpolate from transparent white; the entire stretched item has a hit surface.
- Right conversation is a full-height Grid with a star-height message scroller. Composer is 38 px single-line, automatically wraps/grows to 132 px then scrolls, and shrinks again. Send sits on the same bottom edge. Enter sends, Shift+Enter inserts a line.
- Confirmed and pending messages share a timeline and have sender avatars. Pending bodies are muted; the one-minute deadline persists across restart. Failed entries expose retry/delete inline; retry keeps the immutable UUID/body. A late acknowledgement does not duplicate the entry. Previous-format encrypted outboxes use their stable file write time instead of resetting deadlines on every read.
- Friend avatars/status badge (offline/online/playing); Details shows duration or last seen, channel and applied component flags. Presence sends no local paths, email, saved files or drafts. Avatar memory cache is per identity and invalidated by revision/friend removal.
- Presence heartbeat approximately every 10 seconds; server TTL 40 seconds. Logout/launcher takeover also invalidates presence via the existing active-instance registry. Playing duration is server-observed (up to one heartbeat behind actual game start). Applied settings are read from installation state, never unsaved UI switches.

## Backend

- After auto-review requested explicit production approval, user answered `всё разрешаю`. Migration `friend_presence` then applied through the migration tool (not raw DDL execution).
- Private RLS-denied `social_presence` table; bounded/allow-listed heartbeat; preserved relationship/unread RPC wrapped with accepted/unblocked-friend metadata only. Private avatar bucket remains private.
- Published account-actions version 4, ACTIVE. Existing custom Auth verification and `verify_jwt=false` setting unchanged. New friend_avatar_get checks active instance + accepted friendship before and after storage read, with a fixed target/avatar.jpg path. Service key remains server-only.
- Edge bundle: `93ccc261ed59f1efd593568a88d0121f8918e578a2f6e8fa1239d718ea402e7c`.
- Security advisor reviewed: new private-table no-policy INFO is intentional deny-all; authenticated SECURITY DEFINER notices correspond to guarded RPCs. Existing nickname availability/rls_auto_enable notices and disabled leaked-password protection remain; this is not a claim of a clean global security audit.

## Automated evidence

- .NET tests: **6097 PASS**, including legacy outbox deadlines, retry ID stability, prior-attempt race isolation, encrypted persistence, account takeover, ownership and save safeguards.
- Edge: **32/32 PASS, zero skips**, using the WPF-normalized avatar fixture. Includes outsider/malformed target denial, strictly boolean permission, and block/takeover during download.
- Live SQL disposable-identity rollback suites: friend_presence, social_access, social_unread, single_launcher passed. No real messages or profiles were changed by fixtures. Tests cover pending/stranger/block denial, private grants, avatar helper service-only access, TTL, play duration, game exit, stale launcher writes and old session guards.
- RU/EN: Social UI 49, Refresh+Toast 23, Session+Menu 20, new Chat Presentation 43 checks each; account 95, feedback 27, window/confirmation 30; Motion 35. New checks measure full-height layout, wrap/newline/cap/shrink, Send alignment, Enter policy, full-width popup hit geometry, avatars, inline expiry/actions, late-ack dedup and closing details on friend removal.
- Screenshots inspected: 1440×900 RU chat; 1050×680 EN failed-send state; 1050×680 RU details. Native interactive hover and real host/VM conversations remain manual acceptance, not implied by detached WPF tests.
- Build/publish: zero warnings/errors. git diff --check passed. Existing unrelated working-tree changes were preserved.

## Manual acceptance gate

Close old test builds on host and VM; run this candidate on both with distinct accounts for chat/presence. Check hover across entire menu items, Enter/Shift+Enter, wrapping/shrinking, friend photos and blue/green/gray indicators. Start/stop Kohan II normally and inspect Details. Disconnect network, send a message, verify inline red retry/delete after a minute, reconnect/retry and verify one copy. Real game launching and guest UI acceptance were not performed here.

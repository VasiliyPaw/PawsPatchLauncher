# Launcher 0.5.9: compact Friends and account UI

2026-09-08. Separate local candidate; no public release/feed/tag/push, game or VM changes. The existing friends candidate was not replaced or launched.

## Candidate

- `release_workspace_059/friends-compact/launcher/win-x64/PawsPatchLauncher.exe`
- 72,065,139 bytes; SHA-256 `7B65AAF69A26409985853F91D8091EAB6EA09D3B7AEA3704EFD4CF161761BC32`.
- Adjacent `launcher.config.json` is byte-identical to the prior friends candidate: signed local components-v2 G: feed paths. This configuration is for this PC, not a distributable friend package.

## Changes

- Removed all six user-highlighted explanatory blocks and the redundant account header/status card.
- Avatar save/removal no longer shows a technical success banner; errors still surface.
- Header avatar enlarged from 23 to 48 pixels, moved beside the patch-ready status with nickname underneath. Profile-page highlight retained; main title can ellipsize safely.
- Friends now uses compact Chats/Requests tabs, incoming-request badge, and a green Add friend button with a collapsible nickname form.
- Chats contains only friends; empty view says No friends yet. Requests separates incoming/sent; blocked users are available in a collapsed group.
- Remove/block actions in friend rows appear behind the actions button. Existing confirmations and server restrictions retained.
- Per-chat/tab unread counts; main Friends navigation badge when another page is active. 99+ presentation bound.
- Both Friends columns enter with the existing fade system; tab/form changes animate. Windows reduced-animation preference honored.
- Identical polls preserve row instances/focus; switching tabs preserves the selected-chat draft. Logout/account switch clears private views and badges.
- Normal background polling every 10 seconds on all pages, existing bounded network/rate-limit backoff and encrypted queue retry. No OS toast, sound, presence or websocket/realtime claim.

## Unread receipt authorization

Applied `20260908070000_social_unread.sql` only to Supabase project `trdzsdclscuwwmxnepyt`. Adds server ordinals, indexed private per-owner/per-peer receipt cursors, unread counts and the authenticated `paw_mark_messages_read` RPC.

The client acknowledges only an active, non-minimized launcher showing the selected chat at its bottom, with no confirmation overlay. A displayed incoming message ID is sent, not client time. Server checks a live confirmed identity, accepted/unblocked friendship and that the marker is incoming from the requested peer. Profile locks serialize against send/block/delete; the cursor only advances. Messages arriving after the acknowledged snapshot remain unread. Private receipts have no client grants or policies.

Security advisor reviewed: the receipt table's [RLS without policy notice](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy) is intentional deny-all; the [authenticated SECURITY DEFINER notice](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable) is expected for this guarded RPC. Existing nickname availability/auto-RLS notices and [disabled leaked-password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection) remain; not an all-clean advisor claim.

## Verification

- .NET suite: **6060 PASS**, including **123** social/save-foundation checks.
- Account UI: **95 RU + 95 EN**; Social UI: **46 RU + 46 EN** (including inactive/minimized/hidden/scrolled-up/overlay read-policy cases).
- Motion **35**; window/confirmation regressions **30 RU**; help attribution **19 RU**.
- Detached WPF previews inspected: RU/EN chats, RU requests, empty Friends and avatar profile. Layout at 1440x900 and 1050x680; narrow layouts wrap actions and retain scrolling.
- SQL `social_access.sql` and `social_unread.sql` both pass inside BEGIN/ROLLBACK with generated participants/outsider. Covers RLS/direct grants, request/block lifecycle, immutable retries, late-arrival unread race, monotonic/idempotent cursors, persistence across a new session, and outsider/blocked/revoked access denial.
- Post-fixture counts: 2 existing profiles, 1 existing friendship, 0 messages, 0 receipts. No fixture rows retained.
- Build/publish: zero warnings/errors. `git diff --check` passes. Existing unrelated dirty files preserved.
- No real launcher/game was started, closed, or updated. No real email was sent and no SMTP credentials were read.

## Manual gate

Before release: have a friend send a request/message while Home is open; check the navigation badge, Chats/Requests counts and selected conversation. Test minimization, leaving an unread chat, scrolling above the latest message, restart persistence and receipt convergence after viewing. Check the larger avatar and transitions at the user's DPI. Actual two-PC visual/network acceptance is still pending.

Save/config transport remains out of scope and is not enabled by this UI work. The prior save-validation foundation is unchanged.

## Email setup

The user's latest Resend screenshot shows `pawspatch.xyz` verified. Supabase custom SMTP is **not configured by this turn**. Official [Resend Supabase SMTP guide](https://resend.com/docs/send-with-supabase-smtp): host `smtp.resend.com`, port `465`, username `resend`; the Resend API key belongs directly in the Supabase SMTP password field, never in source, launcher config or chat. Suggested sender `noreply@pawspatch.xyz`, name `Paw's Patch`.

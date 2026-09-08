# Launcher layout and registration candidate — 2026-09-09

Local candidate only. Launcher package/feed/tag/release has not been published.
The executable still reports 0.6.3; a public version number has not been assigned.
Game binaries, installed patch, user settings, live accounts and messages were not modified by tests.

## Changes

- Game observation retains the handle of an adopted process, reads unavailable exit codes safely, and completes observation once. Unknown exit code is not called a crash. Non-adopted process enumeration objects are disposed.
- Default window is 1600 × 1000 DIPs, bounded by the monitor work area. A separate placement LayoutRevision=1 resets legacy geometry once, retaining the chosen monitor, then persists normal user resizing/maximizing.
- Friends always shows chats and permanent live search. Header order: Add friend, Requests, Broadcast, Blocked. Blocked uses a person-with-prohibition icon.
- Add friend, incoming/outgoing requests and blocked users use an animated overlay, outside-click/Escape dismissal, focus restoration and independent rows. Opening a dialog preserves chat selection and draft; an obscured chat is not acknowledged as read.
- Requests show avatars and names. Incoming has direct Accept/Decline; outgoing has direct Cancel. Action buttons are 26 px high.
- Broadcast defaults to Save, followed by Configuration. Game folder has a green Send save action.
- Changelog defaults to Launcher, with separate Release and Beta tabs. Both signed channel feeds already read by the launcher-update check supply history, independently of the selected installation channel.
- Six-digit email confirmation has its own compact form, code resend and automatic sign-in. The existing single-launcher claim, trusted profile checks and encrypted remember-me storage are reused. Passwords are not retained for verification; duplicate UI submissions are blocked.

## Production email template

With explicit user approval, only Supabase Confirm sign up subject/body was saved through the authenticated dashboard and verified after reload. Subject: Paw's Patch — подтверждение почты / email confirmation.

Source: supabase/templates/confirmation.html. Previous body: supabase/templates/confirmation.previous.html.
The template uses {{ .Token }}, not ConfirmationURL. SMTP, recovery/other templates and Auth policies were not changed.
Older launchers without the confirmation-code form need an update to complete new registrations.

Reference: https://supabase.com/docs/reference/javascript/auth-verifyotp and https://supabase.com/docs/guides/auth/auth-email-templates

## Automated verification

- Core suite: PASS 8637, including leading-zero OTP, remember on/off, expired code, signed-in guard, unavailable process code and real harmless adopted subprocess exits (0 and 7). Auth/network/media use mock transport.
- New layout suite: PASS 61 RU and 61 EN: minimum/default geometry, title fit, toolbar order/icon, incoming/outgoing layout, separate dialogs, draft preservation, Save default, delayed OTP UI → profile with duplicate-submit guard, remember choice and independent changelogs.
- Native placement: PASS 28, including invisible isolated windows on three monitors, legacy maximized migration, migration saved on display, custom resize preserved on next launch, normal/maximized/minimized round trips.
- Account UI: PASS 113 RU and EN. Changelog: PASS 32 RU and EN. Friends polish: PASS 24 RU and EN. Broadcast/social hub: PASS 48 RU and EN. Admin UI: PASS 148 RU.
- Social regression chain passed: basic UI, unchanged poll identity, session/menu, chat layout/input, friend configuration, offers, identity/media, social refinement, outside dismissal/clipboard and decoded-media layout. The final direct incoming buttons are covered by the EN session/menu suite (22).
- Build: no warnings/errors. Whitespace diff check clean.
- Visually inspected detached RU/EN layouts at 1050 × 680 and 1600 × 1000: friends toolbar, add dialog, incoming/outgoing requests, broadcast, email confirmation. No real user credentials, chat data or saves in these previews.

## Manual acceptance before public release

1. Close the normal launcher, run release_workspace_064/test/win-x64/PawsPatchLauncher.exe.
2. Confirm one-time larger size, change size, close and reopen; custom size must remain.
3. Register using a real mailbox, enter its fresh six-digit code, confirm automatic login; check remember-me on/off across restarts. No real signup or email delivery was exercised automatically.
4. Review request buttons, blocked icon, dialog motion, search and broadcast; send/accept a test save with a consenting friend.
5. Play and close the game normally; verify the repeated ExitCode error no longer appears. The unrelated NVIDIA/game crash is not claimed fixed.

Do not publish until the user accepts the visible UI and real registration flow.

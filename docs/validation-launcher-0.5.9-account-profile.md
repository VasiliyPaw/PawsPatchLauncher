# Account/profile candidate, 2026-09-08 (unpublished)

Supersedes the account-only preview in `validation-launcher-0.5.9-accounts.md`. Game files/processes, real launcher processes and VM were not touched. No public release, commit, push or tag.

Candidate: `release_workspace_059/account-profile/launcher/win-x64/PawsPatchLauncher.exe` (72,027,008 bytes).
SHA-256: `5913DBE81B1AFE443ABCBD783D0CD77BD1222506E4F44E272CB2D2B8431DF510`.
Adjacent config uses the existing local signed components-v2 Release/Beta feeds. This config is for local testing only, not public distribution. Publish completed successfully and the final whitespace diff check passed. Final server check: zero Auth users and zero profiles, confirming rollback fixture cleanup.

## Changes

- Fixed PasswordBox clipping: remove the second vertical inset from the 36px input's content host; keep rounded dark inputs and animated focus border. Filled-password pixel regression and screenshot now show masked dots.
- Rightmost account control, before the window buttons: circular person icon, Guest or unique server nickname, animated hover and nickname transition. Opens guest login/registration choices or the account overview.
- Profile: identity icon, nickname, private email and creation date. Long names/addresses are ellipsized with full-value tooltips. Nickname/email/password editors replace the overview instead of adding unnecessary scrolling below it. Existing launcher Motion and reduced-animation behavior reused.
- Remember me is on by default in both registration and login. Unchecked sign-in is memory-only through refresh and profile changes, and removes an earlier saved local sign-in when successful. Failed sign-in does not delete existing credentials. Restart becomes Guest. Checked sign-in still uses current-user DPAPI. No passwords in settings/diagnostics.
- Password length is **6-128 characters**, including registration, change and recovery, per user request. Existing password sign-in remains compatible.
- Rename RPC locks the caller's profile row and enforces a five-minute server-clock cooldown after a successful change. Same-name request is a no-op; invalid/occupied names do not consume the timer. Uniqueness remains case-insensitive for Latin/Russian including Ё/ё. Player UUID stays unchanged. A UI timer is informational only; direct clients cannot edit the timestamp or bypass server enforcement.
- Email and password changes reauthenticate the same user with the current password. Pending email is never shown as confirmed before the Auth user response changes. Auth confirmation/security settings are not weakened.
- Forgot password has a separate request/recovery form. Accepts an email OTP or the original Supabase recovery button link copied from the message. Only the configured HTTPS project `/auth/v1/verify` path and recovery purpose are accepted; arbitrary URLs/redirects are never followed. Verification uses POST at a fixed endpoint. Returned user email must match the request before password mutation. Recovery tokens remain separate and are never stored or shown as ordinary account login. Successful reset requests revocation of prior sessions and returns to password login; revocation failure is reported honestly.

## Verification

- Main suite: **5805 assertions passed**, including 132 profile/remember/recovery assertions and 94 earlier account assertions. Mock HTTP only; actual Windows DPAPI round trips.
- WPF account UI: **48 RU and 48 EN**. Filled-password pixel comparison, fields/modes, remember toggle, async guards, profile opening, editor secrets cleared on navigation, recovery stages and diagnostic exclusion.
- Existing Motion: **35 checks** (interpolation, reverse/rapid changes, buttons, checkboxes/radios, hover and isolation).
- Existing launcher updater UI: 13 EN. Patch channel: 16 EN. Caption tested at 1050x680 with an update button and account control together.
- RU previews at 1440x900: registration with fixture text/dots, profile, nickname timer, password and recovery. EN compact login at 1050x680. Headless WPF renders, not control of the user's desktop.
- Applied `profile_nickname_cooldown` migration to project `trdzsdclscuwwmxnepyt`. `supabase/tests/profile_nickname_cooldown.sql` passed on the server, all fixture writes rolled back. Tests cover server cooldown, no-op, invalid/taken names, old/new exact lookup, stable identity, RLS and denied direct timestamp writes/anonymous calls.
- Advisor warnings reviewed: the new authenticated SECURITY DEFINER rename RPC is intentional, locked to `auth.uid()`, with fixed empty search_path, bounded validation and no client grants for direct updates. Earlier exact-name lookup/availability and pre-existing `rls_auto_enable` warnings remain. This is not a zero-warning claim.

## Manual acceptance still needed

1. Configure SMTP before player email flows can be accepted. No real signup, password/email change or recovery message was sent by these checks.
2. Recommended Auth Reset Password email template: `supabase/templates/recovery.html`, which includes `{{ .Token }}`. It has NOT been applied to remote Auth configuration. Without this template, the native form also supports copying the original default recovery link (not opening it and copying the redirected URL).
3. Check existing Auth Site URL and secure email-change confirmation settings. Do not disable confirmation just to hide missing mail setup.
4. Test real login/restart with remember on and off; rename/occupied name/cooldown; confirm a new email; change password then login; receive a recovery email and set a new password. Test expired/used codes and a failed email request. Each test requires the user's test account/mailbox.
5. Friends, chat, save transfer and match rooms are still the next stage, not represented as working here.

Official protocol references: https://supabase.com/docs/guides/auth/passwords ; https://supabase.com/docs/reference/javascript/auth-updateuser ; https://supabase.com/docs/guides/auth/auth-email-templates ; https://supabase.com/docs/reference/javascript/auth-verifyotp

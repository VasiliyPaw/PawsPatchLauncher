# Accounts test candidate (unpublished)

Historical account-foundation snapshot. The newer profile/remember/recovery preview and the updated 6-character password minimum are documented in `validation-launcher-0.5.9-account-profile.md`.

This is the account/registration foundation, not a finished social release. Existing 0.5.9 changes are preserved. No game files, launcher process, game process or VM were changed or started by these checks.

## Local candidate

- EXE: `release_workspace_059/accounts/launcher/win-x64/PawsPatchLauncher.exe`.
- SHA-256: `079809FE16AA97C7CFFAFDFCFDEF646C8EBAF6E0A1D94165DEA0440C76803C6D`.
- The adjacent test-only `launcher.config.json` uses the existing local signed `components-v2` feeds. Both paths were checked present. The production config was not changed; do not distribute this local config.
- Final main-suite rerun after the build: `PASS 5673`; whitespace diff check passed. Final 1440x900 registration render reviewed with aligned 36px fields and no unnecessary vertical scrollbar.

## Implemented

- Friends navigation between Multiplayer and Settings. About remains last.
- Guest-only invitation to Sign in / Register; patch installation, configuration and game launching remain independent of accounts.
- Email/password login and registration with repeated password. Email confirmation is once at registration, not every launcher start. Resending is rate-limited in the UI; server limits still apply.
- Mandatory nickname: 3-24 characters, Latin/Russian letters, digits, underscore, dot, hyphen; first character alphanumeric. No spaces, control characters, invisible marks or emoji. Case-insensitive uniqueness on the server, including Russian and Ё/ё. Availability checked before signup; the DB unique constraint handles concurrent signups.
- A nickname is assigned atomically by the auth signup trigger. User-editable Auth metadata is not trusted for the displayed nickname or future friend lookup. Direct client profile writes are forbidden.
- Exact-name authenticated lookup is prepared on the backend; it returns only id and nickname of an email-confirmed player. No public profile enumeration or email columns.
- Current-user Windows DPAPI protects refresh/access tokens and account details in a separate account/session.dat, never in ordinary settings. Atomic encrypted writes and a cross-process file lock serialize refresh/logout. Passwords are not persisted. A valid session is restored and expiring tokens rotate automatically. Network failure retains the session but puts the account offline. Revocation clears it. Offline logout deletes the local copy and explicitly reports that remote revocation was not confirmed.
- RU/EN inline account errors never show/log raw server responses, credentials or input. Password boxes are cleared on submission, navigation, logout and close. Account requests do not lock patch navigation.

## Validation

- Main automated suite: **5673 passed**, including **94 new account assertions** with injected HTTP responses and real Windows DPAPI round trips. No real signups or emails.
- WPF account suite: **29 assertions per RU/EN**, including guest gating, login/registration field separation, asynchronous duplicate-submit protection, main navigation independence, unique server profile, and exclusion of protected sessions from diagnostics.
- Retained regression checks: component UI 61 RU; credits 19 RU; common launcher update 13 EN; patch channel 16 EN.
- Visual renders: RU 1440x900 guest and registration; EN 1050x680 registration. Existing layout/font/scrollbar checks pass. Password fields aligned to the other 36px inputs.
- Live read-only client probe with the user-provided publishable key: email auth enabled, signup enabled, email confirmation required; nickname-availability RPC responds correctly.
- Supabase SQL transactional tests passed: invalid/valid nicknames, Cyrillic case uniqueness, duplicate signup rollback, blank signup rejection, immunity to mutable metadata, self-only RLS, immutable profile, hidden internal column, exact lookup, guest restrictions. Test users/profiles were rolled back, not left in the project; no email was sent.
- Build has no errors or warnings. No public commit, push, tag or launcher release.

## Remote schema change

Applied `accounts_nicknames` to project `trdzsdclscuwwmxnepyt` (previously no public tables or Auth users).
Migration source: `supabase/migrations/20260907220000_accounts_nicknames.sql`.
Regression script: `supabase/tests/accounts_nicknames.sql` (all test writes inside rollback).

Security advisor warnings are reviewed, not reported as zero:

- `paw_nickname_available` intentionally allows a public boolean query about one exact nickname. It exposes no user record, email or credential.
- `paw_find_player` intentionally allows a signed-in exact nickname lookup returning id/nickname only. No wildcard search or unsigned access.
- The pre-existing Supabase `rls_auto_enable` event-trigger function is also reported as executable. Its setup predates this change and was not modified.
- Remediation/reference: https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable

## Manual acceptance / remaining work

1. Configure and verify confirmation-email delivery for players (custom SMTP for production). Check the Auth Site URL/confirmation destination as well; default hosted projects can redirect to localhost after confirmation. Do not disable email confirmation to hide this setup requirement. No real registration/confirmation was claimed tested.
2. Manually register with a new nickname, confirm email, sign in, close and reopen the candidate, and verify the account remains signed in; sign out and reopen to verify guest mode.
3. Test a taken nickname, case variant, invalid whitespace and wrong password with the real UI.
4. Add actual friends/requests by nickname, chat, settings comparison, save transfers and match rooms. The signed-in test screen explicitly says these are not connected yet. Password recovery, account deletion and anti-abuse production limits are also release gates for the social feature, not features to imply already work.

Sources: https://supabase.com/docs/guides/auth/passwords ; https://supabase.com/docs/guides/auth/sessions ; https://supabase.com/docs/guides/auth/auth-smtp ; https://supabase.com/docs/guides/auth/managing-user-data

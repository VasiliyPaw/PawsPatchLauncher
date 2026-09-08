# Launcher 0.5.9 — six-digit password recovery

Date: 2026-09-08.

## Implemented

- Chose the user's six-digit-code alternative. No OS URL protocol/deep-link registration was introduced.
- Recovery form uses a compact visible six-digit field instead of a password/link field, with RU/EN text. Leading zeroes are preserved. Keyboard input, paste and the service reject non-ASCII digits, URLs and oversized codes without silently truncating a pasted value. Whitespace-separated copies such as `001 234` normalize to `001234`.
- Submit stays disabled until all six digits are present. Enter in the code field focuses the new-password field. The adjacent resend action retains the existing 60-second request interval and displays its countdown. Successful resend clears the old proof and password fields. Code/undo data is cleared on leaving the page.
- Supabase Auth remains the verifier: POST `/verify` with `type=recovery`, email and token. The returned email must match the requested account; password mutation uses only the transient recovery session. Recovery sessions are not persisted or claimed as ordinary launcher logins. Existing global logout after success and local cleanup on errors remain.
- No automatic email/OTP attempts, real password changes, accounts, game files or save files were used by the automated checks.

## Hosted configuration

- Existing project: `trdzsdclscuwwmxnepyt`, domain `pawspatch.xyz`, configured Resend SMTP unchanged.
- Observed `Email OTP length=8` initially. The user changed it to **6** in the Supabase dashboard and saved; reopening the provider form verified **6**. This is a global email OTP length setting, not recovery-only. Existing expiration **3600 seconds** and the observed provider/security switches were unchanged. The agent did not modify those security settings.
- After explicit action-time user approval, saved only the Reset password template subject/body. Subject: `Paw's Patch — код восстановления / recovery code`. Body contains `{{ .Token }}` and no confirmation link; Russian instructions plus English summary, no external assets or tracking URLs. Reload + preview verified persistence and absence of the old link/extra text.
- Canonical template: `supabase/templates/recovery.html`. Previous public body retained in `recovery.previous.html`; previous subject was `Reset your password`. Dashboard editor automatically indents source, so the saved body is presentation-equivalent, not asserted byte-identical to the canonical file.
- Other email templates, SMTP credentials, redirect URLs, database schema and edge functions were not changed.
- Supabase's supported template variable and recovery verification were checked against [Email Templates](https://supabase.com/docs/guides/auth/auth-email-templates) and [verifyOtp](https://supabase.com/docs/reference/javascript/auth-verifyotp).

## Validation

- Final unit suite: **8644 assertions passed**, including **192 account-profile assertions**. Tests cover exact purpose/email/token payload, leading zeroes, normalization, rejection before network, mismatched account cleanup, expiry preventing password mutation, and absence of persisted recovery sessions.
- Final WPF account suite: **115 checks each in RU and EN**. Includes compact width, six-digit limit, undo off, empty/partial/complete submit state, invalid keyboard/paste, resend timer and duplicate prevention, code clearing, and prior account regressions.
- Layout/font/caption/navigation/typography checks passed at RU **1050×680** and EN **1440×900**. Visually inspected generated RU preview `artifacts/recovery-code-ru.png` and the hosted email preview. Normal small-window scrolling is retained; submit and back buttons remain reachable. No sidebar/logo changes.
- Initial fixture-only keyboard event construction needed its WPF RoutedEvent set; corrected the fixture. An initial Consolas field violated the launcher's Arial rule; production field now inherits Arial with tabular numerals. Final checks passed.
- Release build/publish completed without warnings/errors. Automated checks use simulated Auth; the new six-digit email/reset path still needs manual end-to-end acceptance. The previous link-based delivery/reset was user-confirmed before this change, not evidence for the new path.

## Test candidates

Host: `release_workspace_059/recovery-code/launcher/win-x64/PawsPatchLauncher.exe`.

VM host directory: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Recovery-Code`.

VM guest: `\\VBOXSVR\KohanShare\PawsPatch-Recovery-Code\PawsPatchLauncher.exe` (existing share mapping from the prior candidate).

Both EXEs: **72,218,381 bytes**. SHA-256 **C88F8CA6F58203C4D65EC3DBBD4BD8BE9C141791C96F445FD2D323826918AEDC**.

Separate new folders; original running Arrival-Polish EXE left untouched. Each device's configuration copied from its own Arrival-Polish candidate and hash-verified. Only EXE and launcher configuration copied to VM share; no account sessions, credentials or saves copied. Guest executable was not launched. No public feed publication or commit/push.

## Manual acceptance

Close the old launcher and start the new candidate. Request a **new** recovery email, enter its six digits, set a new password and sign in. Do not reuse the earlier link-based email. Check the resend countdown and optionally a mistyped code. Never share a real code or password in chat. Successful new-code delivery/reset/login remains the final manual gate.

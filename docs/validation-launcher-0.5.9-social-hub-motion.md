# Launcher 0.5.9 — broadcast selection and notification motion

Date: 2026-09-08.

## Scope

- Broadcast recipients use a dedicated whole-card template: no checkbox glyph, animated full-row hover, selected fill/gold border/left accent, keyboard-focus outline and disabled appearance. CheckBox toggle semantics, accessible names, five-recipient cap, eligibility and partial-retry behavior are preserved.
- Toast expiry fill uses one linear WPF animation clock per notification instead of changing ScaleX every 33 ms. A 100 ms timer only checks expiry and existing hover/focus retention. Localization/refresh does not restart progress; repeated messages renew the lifetime without replaying a settled entrance.
- Dismissal slides down and fades over 220 ms. Reopening during dismissal cancels the previous completion and reverses from current visual values. Dismissing during entrance preserves the current opacity/position; completed hides/window closure release animation clocks. Non-animated Windows mode remains immediate for entrance/exit.
- Notification placement, modal layering, success/error lifetimes (3/8 seconds), sidebar/logo, transmission limits and account/security policies are unchanged.

## Verification

- Full unit suite: **8666 assertions passed**, including **22 Social Hub policy checks** (six new animation identity/remaining-time cases).
- WPF Feedback: **39 checks each RU/EN**, including progress advancing with the expiry timer stopped, linear intermediate values, refresh/repeat timing, close/reopen races, slide/fade intermediate frames, dismissal during entrance and cleanup.
- WPF Social Hub: **47 checks each RU/EN**, including six new card-template/hit-area/accessibility/highlight checks. Existing cap, eligibility, partial retry, cancellation and account-replacement scenarios passed. The fixture now uses a real off-screen presentation source for input hit testing.
- Motion **35** and Smooth Experience **33**, RU/EN: intermediate frames, reversal, fast input, existing overlay dismissal/reopening, scrolling and reduced-animation branches. Actual Windows animation preference during runs was enabled; disabled-mode fallback retained in source, not manually toggled on the user's system.
- Account **113**, social **49**, refresh/toast **23**, session/menu **20**, chat **43**, friend settings **249**, offers **112**, identity/media **16**, social refinements **35**, social finish **54**, media layout **26**, background update **25**, arrival polish **75**, each RU/EN, passed.
- Synthetic UI/mock transports only: no actual messages, files, Auth requests or clipboard data used by tests. No game launch or save installation.
- Visually inspected selected/unselected cards at 1050x680 and a centered mid-life success toast above the broadcast overlay. Previews: `artifacts/broadcast-motion-selected-ru.png`, `artifacts/broadcast-motion-selected-en.png`, `artifacts/broadcast-motion-toast-ru.png`, `artifacts/broadcast-motion-toast-en.png`.
- Release publish succeeded without warnings/errors; Git whitespace check passed. Existing dirty worktree preserved; no commit/push/public feed release.

## Cooldown investigation — no policy changes

Read-only inspection of current Supabase function definitions confirmed separate fixed five-minute restrictions for display name, username, email and password changes. Existing client countdowns compute locally and disable submission; they do not send a request per second.

An escalating cooldown can be calculated lazily from a level and timestamp in the existing atomic operation, without scheduled jobs or extra polling. This would mainly deter repeated changes; normal users rarely mutate their profile, and an attacker can still submit rejected requests. Meaningful infrastructure savings cannot be quantified without traffic measurements. A blanket escalation to 24 hours for password recovery is not recommended because it can obstruct restoring control of an account. Existing Auth rate limits and recovery protections remain separate.

Official references checked: https://supabase.com/docs/guides/auth/rate-limits and https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html.

## Test builds

Host: `release_workspace_059/social-hub-motion/launcher/win-x64/PawsPatchLauncher.exe`.

VM host share: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Social-Hub-Motion\PawsPatchLauncher.exe`.

Guest route through the existing share: `\\VBOXSVR\KohanShare\PawsPatch-Social-Hub-Motion\PawsPatchLauncher.exe`.

Both EXEs: **72,227,188 bytes**, SHA-256 **AA78E3C480F0A6A926EDE013384F5494DF239A1F2F5D67DBEF9167610C60027E**.

Each device's launcher.config.json was copied from its own Social-Hub candidate and hash-verified. Only the EXE and device-specific configuration were copied to the new VM folder; no sessions, saves or credentials were copied between devices. The running Social-Hub launcher (observed PID 24184) was not stopped or replaced. The new guest build was not launched.

## Manual acceptance

Close the old launcher before opening this candidate. Check empty-space/card hover, selected highlighting, keyboard selection, success/error progress and dismissal on the actual display/VM. Automated off-screen WPF frames and rendered PNGs do not establish real GPU/VM perceived smoothness; that remains the user's visual acceptance gate.

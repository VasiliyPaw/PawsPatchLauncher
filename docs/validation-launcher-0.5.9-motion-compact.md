# Launcher 0.5.9 — smooth scrolling, dismissal and compact header

Date: 2026-09-08.

## Changes

- Global `ScrollViewer` behavior eases wheel and scrollbar line/page commands over 180 ms. Same-direction wheel ticks accumulate; reversing direction starts from the displayed position. Nested areas consume scrolling first and hand off to a parent at the edge. System wheel-line/page settings and high-resolution deltas are respected.
- Native thumb dragging, touch manipulation, caret navigation, logical/virtualized lists and application `ScrollTo*` calls retain their native semantics. Hidden/unloaded views, external offset changes, content/viewport resizing and mouse input cancel the render subscription. No idle render callbacks remain. Windows' disabled-animation preference uses immediate offsets instead.
- Profile close button, Escape and outside click use an awaited 180 ms fade. Content remains visible during the fade; card actions are disabled and the overlay continues blocking clicks. After completion, private content is cleared. A generation guard protects a newly reopened profile from an older close continuation. Account/friend removal still tears down immediately without exposing stale identity data.
- Confirmation dismissal now awaits the actual fade completion instead of an independent 130 ms delay. The underlying interface remains locked throughout. Cancel retains the already-open profile beneath the confirmation. Help and toast closing use the same race-safe fade mechanism. A bounded fallback completes transitions if render clocks stop, e.g. while minimized.
- Chat read acknowledgements triggered by scrolling are debounced for 200 ms, and an active smooth-scroll animation cannot mark messages read. This avoids per-frame network activity and retains the existing account, incoming-message-ID, active-window and visibility checks.
- Header top margin 24→12, content gap 18→10, profile button height 74→70: **24 DIP more vertical content space**. Main heading 29→26 and subtitle 14→13. Avatar stays 48×48, nickname remains fully inside the profile button. No sidebar redesign or additional decorative effects were implemented without a separate request.

## Validation

- .NET: **8611 assertions passed**.
- WPF: new **Smooth Experience 33** in RU and EN using real off-screen native render surfaces. Covers intermediate scrolling/fade values, rapid ticks, reversal, nested/edge handoff, vertical/horizontal paging, immediate drag, external navigation, resize, hidden-view cleanup, editor caret preservation, modal locking, reopen races and header bounds at 1050×680 / 1440×900. Windows animations were enabled during these runs; the disabled-preference branch was code-reviewed, not tested by changing the user's OS setting.
- Existing RU/EN checks passed: Motion 35, Feedback 27, Account 95, Social 49, Refresh/Toast 23, Session/Menu 20, Chat 43, Friend Settings 249, Offers 112, Identity/Media 16, Social Refinement 35, Social Finish 54, Media Layout 26, Window Experience 30, plus standard layout/scrollbar checks.
- Final source built without warnings/errors and the RU complete UI suite was rerun after final cleanup. EN complete suite passed before only removal of unused transition-version bookkeeping, a comment update and the per-frame reduced-animation preference recheck.
- Compact RU preview visually inspected: `release_workspace_059/motion-compact/compact-ru.png`; final normal preview: `release_workspace_059/motion-compact/final-ru.png`; normal EN preview: `release_workspace_059/motion-compact/preview-en.png`.
- `git diff --check` passed. Existing mixed changes preserved. No commit, push, feed publication, database mutation, real account test, game launch, clipboard access or save replacement.

## Test build

Host: `release_workspace_059/motion-compact/launcher/win-x64/PawsPatchLauncher.exe`.

VM host folder: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Motion-Compact`.

Guest path: `\\VBOXSVR\KohanShare\PawsPatch-Motion-Compact\PawsPatchLauncher.exe`.

Both executable copies: **72,214,201 bytes**; SHA-256 **4D9C8CEC62829E7E6FD2992CF4A732E84CF4155E225D279D8745798191402FA8**.

Device-specific `launcher.config.json` copied from Clipboard-Polish and hash-checked. VM is running with the expected KohanShare mapping. Only executable/configuration placed in a new VM candidate folder; credentials, sessions and saves were not copied, and the guest executable was not launched. Previous candidates remain.

## Manual acceptance

Close the previous test launcher before starting this build. Check wheel/trackpad feel in long settings, news, chat, profile components and confirmation previews; test fast reversal, nested-scroll boundaries, dragging the scrollbar and closing/reopening a profile. Automated intermediate-frame checks do not replace the user's preference for scroll speed or perceived smoothness on their mouse/display/VM.

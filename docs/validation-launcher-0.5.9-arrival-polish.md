# Launcher 0.5.9 — quiet background checks and arrival polish

Date: 2026-09-08.

## Scope and results

- Sidebar width (228 DIP), logo (108 × 108), navigation layout and the already compact header are unchanged, following the user's explicit correction.
- History is shown only on Home. Account, Components, Settings, Multiplayer and About reclaim the right column; Friends retains its list/chat split. Queued page reveals cannot reopen the hidden history. Active progress/cancel/error actions are retained in a temporary footer outside Home; an idle/background check does not consume additional height.
- New visible messages and requests get a 180 ms opacity/4 DIP entrance, capped at four rows per render. First history snapshots, opening another chat, unchanged polls, pending-to-sent ACKs and offer state changes do not replay arrivals. Loaded empty chats establish a baseline before their first live message. Sending-card opacity is preserved. Unloaded/stale rows cannot be animated by delayed callbacks.
- Incoming requests/unread increases briefly brighten visible navigation/tab counters once. Initial login, count decreases, navigation and identical snapshots are quiet. No perpetual flashing or shared-brush mutation. Motion checks honor the current Windows animation preference and clean up their short-lived clocks/listeners.

## Automatic-check investigation and authorized correction

The actual `CheckFeedAsync(background: true)` path was exercised with a held synthetic HTTP response, both success and failure, in a loaded off-screen WPF window. No real server/account/game was used.

Baseline: chat row/message objects, chat height, composer text and caret remained unchanged. The sign-out button changed enabled state **four times for two checks**. The minute timer also refreshed history by rebuilding its controls, and the background progress bar could resize Home's history pane. This confirms unnecessary visual state changes elsewhere, but **does not prove the user's entire chat flashed** on their real machine.

After the user's additional approval:

- A background feed request no longer blocks/dims action buttons or displays installation-style progress.
- Manual checks still reserve the UI. Starting a manual check, protected operation or confirmation cancels/supersedes the background request. Request generations and operation revisions discard old results/finally callbacks, including the independent launcher-version request.
- The legacy installation-state write is restricted to the foreground check; background checks do not perform that game-directory write.
- Identical history data retains its controls and reading position. Real changes to history/language/category still render normally.
- Background failures retain the existing quiet status behavior; foreground failures retain accessible error actions outside Home.

## Validation

- Final .NET suite: **8611 assertions passed**.
- New WPF checks, both RU and EN: **Arrival Polish 83**, **Update Refresh 25**. Covers narrow/wide layout, unchanged sidebar/logo, all page spans, progress relocation, delayed reveal cancellation, first-load/empty-history/live arrivals, pending ACKs, requests, counters, cleanup, held success/failure, confirmation/manual preemption and stale callback isolation.
- Full RU and EN suites passed on final production source: Motion 35, Feedback 27, Smooth Experience 33, Changelog 31, About 54, Global Launcher Update 13, Component Settings 63, Account 95, Social 49, Refresh/Toast 23, Session/Menu 20, Chat 43, Friend Settings 249, Offers 112, Identity/Media 16, Social Refinement 35, Social Finish 54, Media Layout 26, Window Experience 30, Storage Confirmation 34, Patch Channel 16; standard caption, typography, spacing, navigation and scrollbar checks also passed.
- Legacy fixture corrections: initialize radio state consistently after fixture settings; count actual launch guards separately from presentation-only game-status queries; call the now-instance `IsGameRunning` method in the storage fixture. No gameplay implementation was changed to make these tests pass.
- Windows animations were enabled for these runs. The disabled-preference branch was reviewed, not tested by modifying the user's OS setting.
- Visually inspected generated previews: `components.png`, `account-compact.png` (1050 × 680), `final-ru.png` (1440 × 900). RU/EN full preview renders completed.
- Build/publish: no warnings/errors. `git diff --check` passed. No commit, push, feed publication, database change, real account/network/clipboard test, game launch or user save replacement.

## Test candidate

Host: `release_workspace_059/arrival-polish/launcher/win-x64/PawsPatchLauncher.exe`.

VM host folder: `D:\Virtual Machines\Kohan Test\Shared\PawsPatch-Arrival-Polish`.

Guest: `\\VBOXSVR\KohanShare\PawsPatch-Arrival-Polish\PawsPatchLauncher.exe`.

Both EXEs: **72,217,600 bytes**; SHA-256 **0728A92B457B558A5510FD989EB267326F2243578437D55F797F2B9EA0E66EAD**.

VM is running; KohanShare mapping verified. Only EXE and device-specific `launcher.config.json` were copied into the new VM candidate folder. Host/VM configurations were preserved from Motion-Compact and hash-checked independently; EXE hashes match. No sessions, credentials or saves were copied, and the guest executable was not launched. Previous candidates remain available.

## Manual acceptance

Close the previous test launcher and start this candidate. Leave an open chat through the next automatic check (one-minute timer), including while typing. Test a new message/request, repeated polling, tab changes and opening/closing a profile. Confirm that brief arrival effects feel right and report whether the originally observed chat flash persists. Automated state/layout checks do not substitute for visual acceptance on the user's actual display and VM.

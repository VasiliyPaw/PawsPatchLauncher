# Match pause and speed test candidate

Test only, based on published 0.8.8. No GitHub release, tag, signed catalog or
public update changes. Assembly/file version 0.8.8.1; package version
0.8.8-timing-test.1. The normal installed launcher is not replaced.

## Behavior

The match-time row displays a yellow localized pause label, current speed
percentage with a Game speed tooltip, and elapsed time, in that order.
The native simulation controller provides explicit pause and selected speed,
including in-match hotkeys and single-player auto-pause. The local clock scales
by the received multiplier and does not advance a paused sample. Out-of-order
samples cannot undo a newer pause. Existing stale/offline limits remain active.

Older launchers do not publish these fields; no percentage or pause is guessed
for their matches. Both publisher and viewer need the test candidate for this
feature to be visible. Updates follow the existing presence and detail polling
intervals (publisher at least eight seconds, open detail polling fifteen seconds).

## Validation

- Full Release console suite: **27442 PASS**, including **116 timing checks**.
- Database suite: **6548 PASS** using isolated PostgreSQL/WASM, both with the
  migration and with the guarded production deployment SQL.
- WPF match-detail checks: **51 PASS per language**, Russian and English,
  at 1050×680. Pause color, percentage tooltip, horizontal order, frozen clock,
  resume without reopening, old publishers and roster scrolling checked.
- New strings also translated into Ukrainian, Czech, German and French.
- Native provenance documented in `game-activity-1372.md`. Three relocated memory
  fixtures cover explicit/automatic pause, focus behavior in multiplayer, live
  logarithmic speed, malformed values and changes during a sample.
- No running game was changed. Live pause/hotkey switching and two-account
  viewing still require manual acceptance; rendered screenshots use fixtures.

## Server

Applied `supabase/tests/deploy_game_activity_timing.sql` to project
`trdzsdclscuwwmxnepyt` on 2026-09-25 through its authenticated SQL editor.
The transaction checked the previous validator hash before replacement and the
tested hash afterward. Only the private activity validator changed; no game,
account, message or presence rows were used as production fixtures.

- Before normalized source MD5: `c3d0db57bc183dac69c62f6988d337ec`.
- After normalized source MD5: `220fd9aadd8dffa754d1067161050b78`.
- Fresh production checks: timing accepted, legacy activity accepted, negative
  speed rejected, lobby pause rejected, direct validator execution still denied
  to both anon and authenticated roles.

Logs, fixture screenshots and candidate build are in the enclosing workspace's
`outputs/launcher-088-timing-*` paths.

## Deliverable

`C:\Users\Paw\Downloads\PawsLauncher-0.8.8-timing-test\PawsPatchLauncher.exe`

- Standalone win-x64 executable: 73,142,125 bytes.
- SHA-256: `5AE99361DD90B5511A92430608F301C35FCC7074C627D5007238A9C9FF35960B`.
- Built with no errors or warnings; isolated executable smoke run reached
  `window-ready.txt` and exited normally. The Downloads copy matches the build.
- Close the regular launcher before opening this candidate to use the existing
  account/profile; the installed executable remains unchanged.

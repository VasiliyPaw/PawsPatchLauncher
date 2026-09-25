# Launcher 0.8.9 verification

## Scope

Match details show the explicit native pause state and selected simulation speed.
The yellow pause label precedes the speed percentage and elapsed time. The speed
has a localized tooltip. The local timer freezes on pause and scales with the
latest received speed, including in-match hotkey changes.

Unknown native timing or older publishers do not produce an invented pause or
percentage. Existing polling intervals and the forty-second stale-sample limit
remain in effect. Both publisher and viewer need 0.8.9 for the full feature.
No game package, save, game configuration or process memory is modified.

## Validation

- Final Release console suite with source version 0.8.9: **27466 PASS**,
  including **116 timing checks**, plus **AI_OPTIONS_PASS 307**.
- Isolated account database suite: **6548 PASS**, including **157 game-activity checks**.
- The unchanged feature implementation passed **51 WPF checks per language**
  in Russian and English at the minimum 1050×680 size. Fixture screenshots were
  rendered and inspected. The strings are translated in all six languages.
- The test executable passed an isolated startup/exit smoke check. Native memory
  fixtures cover three image bases, explicit and automatic pause, live speed,
  invalid data and transitions during reads. Provenance is recorded in
  `game-activity-1372.md` and `match-timing-test-20260925.md`.
- Live pause/hotkey switching with two signed-in accounts has not been manually
  verified; automated fixture tests do not establish that end-to-end result.

Release logs and staging are under `outputs/launcher-089-release/` in the
enclosing workspace. Earlier UI and test-build evidence is under
`outputs/launcher-088-timing-*`.

## Server

The production timing validator was already applied on 2026-09-25 to project
`trdzsdclscuwwmxnepyt` using the guarded deployment SQL. It was then checked with
fresh read-only queries: new and legacy activity accepted, negative speed and
lobby pause rejected, direct execution still denied to anon/authenticated.
The normalized function-source MD5 is `220fd9aadd8dffa754d1067161050b78`.
Only the private validator changed; no public RPC, privilege or user data changed.
The additive migration is included in the release; it is not applied twice.

## Publication procedure

The tag-triggered workflow builds and verifies the autonomous win-x64 EXE and ZIP.
Authenticode policy is unchanged. `tools/PrepareLauncher089.py` verifies the
published tag, manifest, GitHub asset digests and downloaded package contents,
then signs all four stable/beta legacy/v2 catalogs with the production ECDSA key.
All game data and earlier release-history entries must remain unchanged.

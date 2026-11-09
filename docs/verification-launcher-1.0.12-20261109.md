# Launcher 1.0.12 publication — 2026-11-09

Promotes the reviewed download/comparison/privacy preview, with final account-profile
placement. The manual visibility reload button has been removed, Save uses a concise
label, and initial load failures now retry automatically after a bounded backoff.
Periodic refresh preserves unsaved choices. All player-facing release notes use
short bullets in RU/EN/UK/CS/DE/FR.

## Local validation

- C# suite: 38,894 passed after the final translation correction.
- Isolated database suite: 12,703 passed; 156 target visibility checks.
- Focused WPF UI: 30 passed in each of RU/EN/UK/CS/DE/FR. This includes no reload
  button, the Save label, failed-initial-load backoff/retry, account isolation,
  minute refresh and protection of an unsaved selection.
- The previous full preview also checked background installer responsiveness,
  friend actions during download, community and game participant navigation.
- All authored UI strings introduced in this release have entries in every supported language catalog. Existing catalog tests verify nonempty translations and preserved format arguments.
- The inherited zero-morale comparison label is also translated in every language;
  targeted comparison assertions cover all four external catalogs.
- Visibility cards in RU/UK/CS/DE/FR and the French comparison layout were visually inspected; all six language variants rendered successfully.
- Server preflight: all twelve installed function source MD5s and grants match the
  tested migration; guest denial, RLS and migration registration all passed the
  live aggregate readback. No new production migration or account data write was
  needed in this publication turn.
- Migration `20261109000000_profile_visibility.sql` was already deployed during
  the test-build work. Its full evidence and test-build checks are recorded in
  `verification-usability-test-20261109.md`.
- Game research, monitor changes and earlier unrelated test edits are excluded.
  Only the privacy test import/call is staged from the shared database runner.

Release workflow, public artifacts and signed catalogs are verified separately
before completion. The ordinary release build does not enable the usability or
community test constants and includes no test profile marker.

## Distribution validation

- Source/tag commit: `8073221c543c3c0f1b2a12603a77241c8042fca0`.
- [Build and test](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/42552338287): success.
- [Publish launcher](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/42552340972): success,
  including account database, Windows packaging and artifact identity checks.
- [Public release](https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v1.0.12).
- Downloaded EXE: 74,390,262 bytes; SHA-256
  `240198095DBC9EB5AE631C22253E979A17E7855D6B1636A13CE17EA2F0D317F4`.
- Downloaded ZIP: 68,983,041 bytes; SHA-256
  `0C6B3A58AFDF8D20B1D00E28E02D5A38043FDC46F71A4482E5F5F768A8F6749C`.
- The public EXE and every ZIP entry match the tagged CI artifact manifest.
- Public EXE startup completed with version 1.0.12 and file version 1.0.12.0.
  Health metadata confirms `usabilityTest=false` and
  `automaticLauncherUpdatesDisabled=false`; the startup check used a separate
  profile and exited without launching the game.
- Six update catalogs were signed and verified before promotion. All game
  package fields remain byte-for-byte equivalent as structured data.
- Catalog publication evidence is kept in top-level outputs under
  `release1012-catalogs-20261109`: `preparation.json`, `readback.json` and
  `live-readback.json`. The last two are produced by post-push verification.

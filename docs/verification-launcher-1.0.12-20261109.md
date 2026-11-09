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

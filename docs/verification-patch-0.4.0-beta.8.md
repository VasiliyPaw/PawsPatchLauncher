# Paw's Patch 0.4.0-beta.8 verification

Arcane Wars beta: lobby revision 3, AI revision 38. Release tag:
`patch-0.4.0-beta.8`. Launcher 0.8.9, stable and other mod packages are preserved.

## Changes

The lobby remembers explicit per-bot and bulk difficulty choices instead of
treating native in-place map-setting resets as new user choices. Restoration
uses the original replicated command. Pending echoes are throttled; saved-game,
replay, campaign and client paths remain excluded. The callback wrapper forwards
the original dispatcher argument and preserves its `ret 4` convention.

The gold button's title-only tooltip now passes native hover selection. The
private button is recognized before the stock empty-body rejection; other
widgets retain native selection and parent fallback. Native visibility and
hover-delay checks, compact placement above the button, 100 by 100 geometry,
artwork and overlapping audio are retained.

Recent beta.4 through beta.8 release descriptions contain player-facing changes
only, across their translations. Editorial policy is in `RELEASE_NOTES_STYLE.md`.

## Evidence

- Launcher Release suite: 27,485 checks passed.
- Bot lobby: 120 native policy/ABI cases at three relocation bases, plus 675
  installation/rollback checks. Engine services in policy cases are mocked.
  The published r2 code fails the in-place reset regression.
- Tooltip/button: 276 native hover-selection checks, 127 tooltip ABI/formatting
  checks, 63 checks using the original native rectangle layout, 481 native
  button/click checks and 203 presentation installation checks. Font measurement
  and selected engine services are stubbed; these are not screenshot tests.
- All eight production helper variants rebuilt and passed 40 offline self-tests.
  The standalone test-only launch entry point is excluded from release helpers.
- Signed package verification checks all eight embedded lobby/UI payloads,
  versions, unchanged artwork/audio/geometry, and corrected recent changelogs:
  161 checks passed.
- Isolated installation matrix: 73,728 selections, 15,024 distinct plans,
  69 verified archives, eight helpers, 18 frame checks, 30 runtime preflights
  and 45 install/component/language/rollback transitions passed.
- The AI payload is byte-identical to beta.7:
  `B357D48C5B030C26918E2D9DA536E4292055463693373BBF5AAF47C0E6CAEBEE`.
  Dependency sources were hash-checked against beta.7 evidence. Those unchanged
  dependency regressions are reused; the redundant partial rerun was deliberately
  stopped. No new full AI regression run is claimed for this release.

Stage evidence: `outputs/release-20260927-beta8` in the parent workspace;
`offline-verification.json`, `reused-dependencies.json`,
`lobby-tooltip-package-verification.json`, `installation-verification.json`,
`publication/public-verification.json` and `catalog-public-verification.json`.

No game was launched or installed by this release procedure. New live lobby,
tooltip appearance and multiplayer acceptance remain separate from the automated
checks. The source game and its settings are not modified by isolated validation.

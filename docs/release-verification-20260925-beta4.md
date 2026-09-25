# Arcane Wars 0.4.0-beta.4 verification

## Scope

This release fixes two independently reproduced host/client policy differences:
builder route decisions used a host-only AI controller/strategic goal, and shared
recruitment admission could veto a native command using host-only demand data.
See [the audit](desync-audit-20260925.md) for evidence and the limits of attribution.

Only four Arcane Wars beta packages change: `pawpatch-core`, `player-colors`,
`desync-continue`, and `common-ui`. Their payload changes are limited to eight
runtime helpers and `paws_patch_versions.ini`. Every other payload byte is
compared with the signed beta.3 baseline. Stable 0.3.3, launcher 0.8.9, legacy
catalogs and other mods are unchanged. Improved AI remains optional.

The immutable source revision is `ca38e9aae5660f14373492c5b21beb166c4fd2e2`.
Its [GitHub CI run](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/36149683291)
passed before publication.

## Automated validation

- The full launcher Release test suite passed 27,466 checks before packaging.
  It passed the same 27,466 checks again against the final signed catalog and
  curated history before catalog promotion to the public branch.
- The canonical eight-helper build completed, including its existing compiled
  native, relocation, ABI, guard, transaction and rollback suites.
- The new regression passed 189 differential host/client checks and 2,358 route
  ABI checks. Native engine services are explicitly stubbed. Cases cover missing
  local AI controllers, different local goals, shared bot/human identity, native
  recruitment results, and human/Haroun/Undead builder recipes at three bases.
- Existing coverage includes 15,285 routing, 14,268 recruitment-count, 4,929
  builder-fleet, 1,053 replacement-completion, 516 city-sharing, 58,568 AI
  transaction and 151,560 saved-owner checks.
- All eight packaged helpers report beta.4 / AI revision 36 and contain the exact
  complete native policy payload used in the passing regressions.
- The build has existing CS0649 warnings in isolated managed test fixtures;
  it completed without errors. No warning-free claim is made.
- The signed-package installation matrix passed 73,728 selections, 15,024
  unique plans, 69 verified archives, all eight helper variants, 18 frame
  checks, 30 preflights and 45 installation transitions. It covers AI on/off,
  optional modules, six text languages, data-only mode, master-off, stable
  rollback and uninstall. Save-sentinel and stock-executable preservation
  passed in the isolated fixture; the user's game was read-only.

Build output and machine-readable evidence are retained in
`outputs/release-20260925-beta4` in the release workspace. Old-payload differential
reproductions are retained in `outputs/desync-20260925` and
`outputs/desync-fix-r36-20260925`.

## Publication

The [prerelease](https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/patch-0.4.0-beta.4)
contains four immutable ZIP assets. All four passed anonymous public download,
length, SHA-256 and GitHub digest verification before signed-catalog promotion.
Every helper embeds native policy SHA-256
`55B7237E31DBC2CE643AEC8190EDF546C88F6853D888C80D4AF7C8E777483236`.

A final scope check validates the beta signature, exactly four changed package
records, unchanged launcher/stable/legacy/other-mod content, and preservation of
all existing standalone history entries. The release preparation tool was adjusted
to prepend to the curated history rather than replacing it with an older catalog
copy; this publication-only adjustment does not change the tagged game runtime.

## Multiplayer acceptance boundary

The supplied archives agree on compatibility identity and runtime hashes, but do
not provide paired fresh native histories identifying the very first differing
command. The confirmed defects can cause desync; neither establishes the first
trigger in this match. No two-machine gameplay acceptance is claimed.

All peers must update and start a new match. The optional continue-after-desync
mode does not resynchronize worlds; use native desync handling when collecting
first-error evidence. No checksum suppression/reset was introduced by this fix.

The user's installed game, running match, lobby name and player count were not
modified during this release preparation.

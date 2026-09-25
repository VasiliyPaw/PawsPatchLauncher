# Launcher 0.8.8 verification

## Scope

Game preferences are available through the gear beside the Components channel selector.
The resolution dropdown uses the existing ReleaseCombo template and popup scrolling
isolation, with nine common widescreen sizes from 1280×720 through 3840×2160.
The same window provides an FPS limit, five volume controls, match timer and
minimap player colors, in all six launcher languages.

Preferences are read from the current Windows user's Documents/Kohan2/data/User/UVars.tgi.
Only explicit edits are saved. Existing unrelated values, comments, encoding and
untouched floating-point precision are preserved; atomic replacement retains a backup.
The game must be closed, and external file changes are rejected rather than overwritten.

Game preferences are separate from UserSettings, configuration sharing and presence.
No server migration, gameplay package or signed-feed schema change is required.
The explicit observer support published in 0.8.7 is retained.

## Local validation

- Full Release console suite with source version 0.8.8: **PASS 27322**, plus **AI_OPTIONS_PASS 307**.
- Game preferences contribute **152** assertions: precise/percentage values, BOM and
  newline preservation, backups, validation, missing/locked/malformed/oversized files,
  game startup and concurrent changes during save, and sharing isolation.
- Final-source Russian WPF fixture: **42 PASS** at the minimum 1050×680 size, including
  all three mod modes, gear placement, visible selected resolution, bounded scrolling,
  popup and modal Escape behavior, cancel, exact saves and external-change errors.
- The previously accepted local candidate also passed **38** WPF assertions in each
  of English, Ukrainian, Czech, German and French. Layouts and the native dropdown
  were rendered and visually inspected.
- No real game settings or saves were edited by these fixtures. Actual game/driver
  acceptance of each resolution is not established by these automated tests.

Local logs and release staging are in the enclosing workspace under
`outputs/launcher-088-release/`.

## Publication procedure

The existing tag-triggered workflow tests and builds the autonomous win-x64 EXE,
checks packaging, and publishes immutable EXE/ZIP/manifest assets. It also runs
the account database tests. Authenticode policy is unchanged from 0.8.7.

`tools/PrepareLauncher088.py` verifies the public tag identity, manifest and GitHub
asset digests, downloads and verifies EXE/ZIP bytes, then signs all four legacy/v2
stable/beta catalogs with the existing production ECDSA P1363 key. Every field
outside launcher metadata, publication time and release notes must remain identical.
The separate history file receives one localized launcher entry per channel;
all previous history entries are preserved.

## Published artifacts

- Source/tag: `7779bbc84d845df6cb6f748286e6e30c1508f538`, `v0.8.8`.
- [Release](https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v0.8.8).
- [Release workflow](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/36134099372): success.
- [Independent build/test workflow](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/36134097138): success.
- Downloaded EXE: **73,124,465 bytes**, file version `0.8.8.0`, product version `0.8.8`.
  SHA-256: `8203012D548B3790923B66059B66938B41B157968BC2AE199F1CCB50090F3140`.
- Downloaded ZIP: **67,717,814 bytes**.
  SHA-256: `14CC653BD270F1DF069F2FA643D46E937ACC0868EDA54FAD2077B16462F776B7`.
- EXE/ZIP sizes and digests match the artifact manifest and GitHub asset digests.
  Every packaged file matches its manifest. Windows independently reports
  `NotSigned`, matching the unchanged release policy and manifest.
- All four staged catalog signatures were verified before promotion, and all
  prior game/catalog fields and previous release-history entries were preserved.

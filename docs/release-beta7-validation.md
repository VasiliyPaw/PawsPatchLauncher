# Beta 7 and launcher 0.5.7 validation

Prepared and tested on 2026-09-07 before public feed advertisement.

## User-accepted gameplay

The accepted r8 test build used the r20 native color payload and the terrain/random-map fixes included here. The user passed seven scenarios: different saves/new game, saved kingdom reassignment, rejoin to a saved lobby, surrender/lobby/restart, new game after save, occupied remembered color on rejoin, and two all-random-color matches with bots.

The associated read-only log audit paired nine recordings with 75,347 equal indexed checksums/event entries and no differences. Three host-only recordings were not counted as verified. Seven paired world-generation attempts agreed on their inputs and chosen map type; one failed identically and was not counted as a successful match.

Two unrelated unresolved incidents were explicitly accepted for release by the user: a VM shutdown access violation and identical object-placement failure on a crowded map. Their root causes are not claimed fixed.

## Release integration

- Six x86 WinExe helpers built from accepted native payloads. Each passed 534 quiet-startup/mock-memory assertions, native color resource verification and common-UI offline verification.
- Exported public helper sources rebuilt independently, with all six sets of offline checks passing.
- Live host startup of the all-off helper and combined colors+bypass helper reached QUIET_READY with no helper window. Both new test games were closed; the existing game installation was not replaced. The original k2.exe SHA-256 remains `1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.
- The combined live log confirms terrain, random-map, common-UI, 49-color r20, sync-bypass and family hooks installed together. This is startup evidence, not a new full multiplayer match with bypass enabled.
- New Beta package audit covered 192 supported combinations with no unreviewed file overlap or lost translation keys. Historical pre-fix package findings remain recorded separately and are not waived.
- Four complete clean installations and removals passed: Release/Beta, English/Russian. Stock EXE and an unmanaged save sentinel survived removal.
- Eight Beta startup-profile transitions passed actual package reconciliation, file verification, critical-file checks and native-helper data guards without launching the game.
- Launcher suite: 399 checks passed, including 19 signed-guide/capability checks. Russian and English About UI checks: 53 each, plus new/old-Beta combined-option UI behavior.
- Signed guide delivery, refresh without a package fingerprint change, offline restart, pinned release, malformed-guide fallback and tampered-cache rejection passed. Displayed text is plain text only.
- Rendered 1050x680 Russian and 1440x900 English About pages were checked for layout and typography.
- Real launcher 0.5.6 -> 0.5.7 self-update passed in a path with Cyrillic, spaces, ampersand, apostrophe and brackets: replacement, previous EXE backup and new-window acknowledgement.

## Immutable release assets

| Asset | Size | SHA-256 |
| --- | ---: | --- |
| common-ui-1.3.72-ui.2-beta.7.zip | 199350 | 6E170136AE35E6865A2CA50567358B5F45A1189AC506AF9CB205C5EB304742C1 |
| player-colors-0.1.0-beta.7.zip | 139037 | 8508062FCB60537364203FB2A3A5103215F0EBF8C04DA694ADE78D05E8674104 |
| PawsPatchLauncher.exe 0.5.7 | 71982521 | A2E3D987E5376F641852721960710454D559D92E471996C3D62D7FC82EC93AF3 |
| PawsPatchLauncher-v0.5.7-win-x64.zip | 66395092 | 9936F5554C5A3CCC3170409D21584E41C289F878303DC85C7A4D1F1C5603992D |

Only the two Beta packages change game files. Release gameplay package identities are preserved. Launcher metadata and signed feature documentation are updated in both channels. All multiplayer peers must update Beta together.

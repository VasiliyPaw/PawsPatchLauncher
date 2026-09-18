# Launcher 0.8.4 and Arcane Wars 0.3.1 release validation

Release source: `770b6be281783685aa8a9b527cca38d2f24ea608`.

## Scope

- Launcher: the accepted 0.8.4 test change promotes newly accepted friends to the top of the chat list and preserves their ordering across restarts. Incoming messages still reorder chats normally; accounts retain separate protected local histories.
- Arcane Wars: promote the accepted 0.3.1-beta.1 gameplay to stable 0.3.1. The camera limit is 2. All eight helpers retain the accepted camera and lair recovery payloads; only release identity changes.
- Four Arcane archives are replaced: core, common UI, player colors and desync continuation. Other beta/stable manifest differences were checked: their normalized payload manifests are identical, so existing stable localization and powers packages remain in place.
- Vanilla, Immortals, beta gameplay and legacy gameplay catalogs retain their packages. All four catalogs receive the 0.8.4 launcher pointer and concise Russian/English launcher notes. Stable Arcane receives the 0.3.1 notes and guide.
- The newly reported friend's crash has no fix in this release.

## Validation

- Full local launcher regression suite passed. Both GitHub build/test and release workflows passed for the exact release source.
- New-friend persistence tests: 17 checks. Chat UI tests: 106 checks in Russian, with an isolated smoke-test profile.
- All eight game helpers built successfully with the native city, transfer, saved-owner, lair and camera regression suites.
- Native city/lair/camera payload files match the accepted beta byte for byte.
- Final compiled helpers: 161 checks, including actual startup calls, lair and camera relocation equivalence, incompatible patch rejection and unsupported game rejection.
- Offline installation matrix: 36,864 selections, 9,840 unique plans, 59 validated archives, 270 minimap file checks, 16 preflights and 31 transitions. Stable/beta switching, localization, file-only mode, disabled patch, rollback and uninstall passed; a save sentinel and the source game executable remained unchanged.
- Launcher distribution is built by GitHub Actions and bound by source commit, size and SHA-256 in `launcher-artifact.json`. Authenticode is not enabled; signed update catalogs use the existing release key.

Integration testing uses a separate fixture and never starts the game. Manual gameplay acceptance is inherited from the user's accepted beta; this publication does not claim a new multiplayer playtest or change the main game installation.

Public releases:

- https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v0.8.4
- https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/patch-0.3.1

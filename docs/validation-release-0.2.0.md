# Release 0.2.0 / launcher 0.5.8 validation

## Scope

Promotion of accepted Beta 7 gameplay. The r20 lobby-color payload and accepted
terrain/random-map payloads are unchanged. New native variants compile the existing
color helper with `SYNC_ONLY;PAW_COLORS`, optionally `SYNC_CONTINUE`, excluding the
family-hostility hooks. This is not a claim of new live multiplayer acceptance for
every switch combination. The user accepted the previous Beta tests and a long match.

The seven accepted badge models and 80%-strength shading textures are now mandatory
data. Prior public Beta 7 contained the textures but not these models. Stock `k2.exe`
is not modified on disk.

## Automated evidence

- General suite: 1,432 assertions passed.
- 512 current configurations: 256 Release plus 256 Beta, all supported, no missing
  dependencies or translation-key losses. Real signed archive hashes, per-file
  precedence, combined roaming overlays, executable selection and future-overlap
  rejection checked. Historical broken archives remain in the audit as findings.
- Eight native WinExe variants: quiet startup (534 assertions each), common UI,
  color payload and compile-time feature reporting checked without launching a game.
- Real-package Release EN/RU clean installs and uninstall passed. All eight Release
  color/bypass/hostility profiles passed file verification and native preflight;
  compiled flags exactly match chosen switches. All 7 NIF + 7 TGA files survive
  colors OFF. Stock EXE and user-save sentinel survive uninstall.
- Migration: Beta 7 -> Release combined colors/bypass without hostility -> all OFF
  -> rollback -> pinned Beta 7 -> Release -> uninstall. Restores a preexisting model
  and preserves a user-save sentinel. Real installer, small affected packages only.
- WPF: 16 native-switch combinations across channels, enabled controls, configuration
  import, old-feed guards; About RU/EN (54 checks each), rapid tabs, typography,
  scrolling, signed guide 0.2.0 and empty-Beta explanation. Render inspected at 1440x900.
- Real launcher self-update 0.5.7 -> 0.5.8 in an isolated Unicode/ampersand/bracket path:
  replacement, retained old EXE and startup/window acknowledgement passed.

Fixture outputs are under ignored `release_workspace_020`; no game was launched,
attached, stopped or modified in the user's installation. No live desktop control.
The animation-crash capture/diagnosis from the preceding task was not changed.

## Packages

| Module | Version | Files | Archive SHA-256 |
| --- | --- | ---: | --- |
| pawpatch-core | 0.2.0 | 1047 | 8EB644232A51FF84D0B0FBB4F1B92794BD11532532BE05516FE3B028755FD101 |
| common-ui | 1.3.72-ui.3 | 23 | 55C54F3DADC975A722FFCC9545B897114EF129C123FB786FC3A4FE9A280C7BEA |
| player-colors | 0.2.0 | 6 | 4CB42EA992CE50683B9C02B4C4AE09A6F5215AF552F62E2B12003C4862C5CD3C |

The core payload is copied from the verified accepted package; only its module
version is advanced. Other gameplay-overlay archives are reused unchanged.
Launcher EXE SHA-256: `19ACD915FFFFF83DF24F2BC31DF0DF6A7BA8106986B265EA6C3D0EFBA27BCED9`.

## Limits and publication order

Two recent animation-path crashes are still under diagnosis; no fix for them is
claimed here, and their relationship to patch code is not established. A long
successful match does not establish that every possible crash is fixed.

Publish source first, then immutable `patch-0.2.0` and `v0.5.8` assets. Verify anonymous
downloads against signed sizes/hashes before advertising canonical feeds. Keep old
signed Release/Beta history entries for rollback. Patch release must not replace the
launcher as GitHub's latest launcher release. Never publish private signing keys,
settings, crash dumps or raw player logs.

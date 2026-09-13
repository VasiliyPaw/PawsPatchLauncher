# Launcher 0.7.0 release validation

The user explicitly authorized publication on 2026-09-13 and selected version 0.7.0.
This release includes the accumulated launcher/mod work and the final prerelease audit.

## Candidate validation

- Main .NET suite: **12,915 checks passed**, including eight official-catalog migration checks after the version bump.
- Prerelease UI matrix: **94/94 scenarios**, 47 each in Russian and English. Affected critical cases were repeated after the last audit fixes.
- Local database: **5,149 checks**, plus **44** banned-account-deletion and **24** team-role checks. Account-actions handler: **37/37 tests**, no skips.
- Actual package installations: **176 checks**, covering three mods, two text languages and two speech languages, offline reuse and scoped updates.
- Signed source catalogs: **41 distinct archives / 12,233 payload files** verified by size/hash. Publication stages 25 new/changed immutable archives and reuses verified existing assets. Five internal development package versions become production identifiers; payload bytes are unchanged.
- Offline rapid selection: 45 changes, maximum under 12 ms in the measured fixtures; applied settings were not modified.
- Computer Use checked connection loss/recovery, cached chat, disabled network actions, centered composer and outside-click consumption for both menus, without sending messages.
- The actual published 0.6.4 updater passed replacement/startup acknowledgement in short and long Cyrillic/special-character paths. Success, crash and acknowledgement-timeout fixtures passed, including rollback.

Detailed logs are retained locally in `work/launcher-release-audit-round24` of the task workspace. Real multiplayer matches and hosted server behavior are not covered by those local test counts.

## Publication design

The existing production signing key is retained. `feed/v2/*` serves the new mod
library; the old endpoints retain all old gameplay metadata so 0.6.4 users may
defer the launcher update safely. The new EXE recognizes only the exact official
legacy URLs with the expected signature key and migrates them in memory. Custom
feeds, unsigned local fixtures, cache paths and user configuration are preserved.

The release workflow builds public artifacts from the tagged source. Archives and
the final public EXE must be downloaded and verified before catalog promotion.
Server migration/publication results will be recorded below after verification.

## Public release and server verification

- Source/tag: `fe724c7f39ab5823b50d4ea40c01728f08816c6d`, `v0.7.0`.
- [Build and test 34784262258](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/34784262258): success.
- [Publish launcher 34784450345](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/34784450345): success, including unit tests and artifact/signing-policy validation.
- [Public 0.7.0 release](https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v0.7.0): published, not a draft or prerelease; 28 immutable assets. Gameplay archives were staged before the workflow published the final EXE and ZIP together with them.
- Public EXE: **0.7.0.0**, **72,439,349 bytes**, SHA-256 `E9359D31FF0C216333128234D09AD764314E52077195133AA05B74F71095C038`.
- Public ZIP: **67,031,716 bytes**, SHA-256 `9E1F5FA9F84C82627A34238F1D02B3F304C2E938953D82C816ED12B37B183D3A`. Contains only the identical EXE and production config; no local test profile, signing key or test-mode marker.
- Anonymous public download validation: **41 archives / 12,233 payload files**, with matching sizes, hashes and module identities. The 25 new assets match the staged artifacts; older immutable assets are reused.
- Actual installation from public signed catalogs: **176 checks passed**, all 12 mod/text/voice combinations, cache reuse, selective language downloads and scoped updates.
- **Actual public 0.6.4 → public 0.7.0 self-update passed twice**, using 0.6.4's extracted updater code in short and long Unicode/special-character paths. Both resulting EXE hashes and update-confirmation logs match 0.7.0; the long acknowledgement path was 273 characters.
- Hosted migrations `mod_modes`, `paws_team`, `banned_account_deletion` and `social_versions` applied atomically. Each source was checksum-verified before execution; ledger entries use the four repository migration versions. Eight readback checks confirm schema, profile-column permissions and authenticated/anonymous presence grants.
- Updated hosted `account-actions`; its source read back after reload matches the tested handler. The existing entry point and custom JWT authentication remain. Anonymous POST returns **401 / unauthorized**. No real accounts were banned, deleted, assigned roles or used to send messages during validation.

Both legacy and v2 catalogs are signed with the existing production feed key. The
EXE is **not Authenticode signed**: SignPath production signing is not enabled.
Real Steam multiplayer matches were not run for this publication.

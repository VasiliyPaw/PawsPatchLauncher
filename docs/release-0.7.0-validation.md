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

# Arcane Wars 0.3.0 promotion

This release promotes the accepted 0.3.0-beta.9 gameplay to the stable channel.
Only release identities change in the eight helpers and the version INI. The
nine promoted packages preserve every other beta payload byte. This includes
the graphics DLL, corrected animations, city settings/UI, Powers and Shards,
localization files, and all 18 static minimap frames. The frames have no runtime
resolution handling.

The current beta catalog, both legacy catalogs, launcher 0.8.3, and the stable
Vanilla/Immortals packages and guides remain unchanged. Only the canonical v2
stable Arcane packages, stable patch guide and scoped changelog are updated.
City automation and fast save transfer move into the always-enabled guide
section; beta-only wording is removed from the stable guide.

## Offline verification

- `Arcane030Tests`: 36,864 setting selections across the source beta and proposed
  stable release; 9,840 unique file/launch plans. Six text languages, four voice
  languages, all three roaming rates, all eight native helper combinations,
  other gameplay switches, master-off and data-only modes are covered.
- Archive and payload hashes are checked before using the real installer in an
  isolated fixture. Installed file winners must provide the selected helper;
  data-only plans must contain no executable-dependent modules.
- `ReleaseVariantTests`: 105 checks across all eight final EXEs. Checks the
  startup call to the lair installer, exact accepted native payload bytes at
  three image bases and two cave addresses, matching release identity, rejection
  of older patch/game files, and absence of resolution-handling code.
- The full existing launcher regression suite passes 26,830 checks.
- The full helper build's native and managed regression suites pass: lairs,
  transaction rollback, saved owners, city planning/queue/militia/preferences,
  markets, lobby protocol, UI/color payloads and fast transfers.
- All 32 compared files (native payloads, binary fixtures and the lobby DLL)
  are byte-identical to beta.9.

The isolated installation report, transition counts and preflight results are
recorded in `outputs/release-arcane-030/installation-verification.json` in the
parent workspace: PASS, 59 verified archives, 16 successful preflights, 31
installation transitions and 270 installed frame checks. It covers upgrades
from 0.2.1, every helper, all six text
languages, all four voice languages, master-off/data-only transitions, beta to
stable switching, rollback and uninstall while preserving an original EXE and
a save sentinel. Only explicit `--preflight` entry points are invoked.

No game session or game window is started. The source game is read-only. The
user's prior multiplayer acceptance applies to the unchanged beta gameplay;
offline checks do not claim a fresh runtime multiplayer test.
All 66 protected source-installation files, including the original EXE,
installed state, helpers, frames and corrected animations, remain unchanged.

## Publication verification

`PrepareArcane030.py` requires the known signed stable/beta baselines, verifies
all nine immutable archives and payloads, signs the candidate, and permits
catalog promotion only after public asset readback and installation validation.
The publication retains the launcher as GitHub's latest release. The canonical
catalog must be downloaded and signature-checked again after its public push.

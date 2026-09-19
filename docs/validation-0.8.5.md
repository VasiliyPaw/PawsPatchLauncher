# Launcher 0.8.5: friend configuration repair

## Problem and change

The client can publish `PAW-BETA-VANILLA-PP1-CL1-OOS1` and its Immortals equivalent,
but the server's old configuration expression rejects CL1/OOS1 for these modes.
The compatibility fallback consequently publishes only component flags and the
channel. The peer loses the mod, exact configuration and version envelope, while
the card misleadingly asks the player to open a newer launcher.

- A shared private, bounded validator now covers presence, the table constraint
  and configuration offers. Invalid channel/patch/file-only combinations remain
  rejected; old Arcane configurations and supported language suffixes remain
  readable. Component flags are derived from the accepted configuration.
- Missing exact settings show an explicitly unknown mod and a neutral explanation.
  Missing version data no longer claims that an update is required. Confirmed old
  versions retain their existing update requirement and copying remains guarded.
- New UI messages and release-feed notes cover Russian, English, Ukrainian,
  Czech, German and French. No game payload, mod catalog or patch guide changes.

## Validation

- Launcher regression suite: 26,872 assertions passed.
- Isolated PostgreSQL/WASM suite: 6,504 assertions passed, including 1,232 new
  configuration checks. Exercises actual authenticated presence and offer RPCs,
  friend readback, component derivation, retained version metadata, malformed
  values, executable-option restrictions and equivalent-offer rejection.
- Rendered player-card checks: 92 assertions across all six UI languages,
  including enabled copying for both valid modes and disabled copying for unknown
  configurations. The rendered Russian missing-data card was inspected.
- The exact guarded deployment transaction also passed the full database suite.
  Production's pre-change function hashes matched the tested baseline. Existing
  function owners, grants, security modes and search paths are retained.
- Production deployment through the authenticated Supabase SQL editor passed all
  nine post-commit contract checks. No test messages or fake player rows were
  created in production; the game was not launched or modified.

The release workflows repeat both client and isolated database tests before
publishing the launcher. Signed feeds are updated only after public assets have
been verified against the immutable CI artifact.

## Release evidence

- Source commit: `619c58389ec42b047311f098818a9ac2c98b4f59`; immutable tag `v0.8.5`.
- Both GitHub workflows passed: [build and test](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/35442159868)
  and [release](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/35442160895).
- Public EXE: 73,106,054 bytes, version `0.8.5.0`, SHA-256
  `623D0B011458872A693D88EA2274207D6AA5EDF29EAEE062A54CAB97C3D9F085`.
- Public EXE and ZIP match GitHub asset digests and all four CI artifact entries;
  the ZIP's executable is identical to the standalone download.
- All 83 unique assets referenced by the four signed catalogs passed anonymous
  download, size and SHA-256 verification before catalog publication. The four
  catalogs preserve all existing game packages, guides and compatibility data.

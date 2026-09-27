# Pure 0.3.0 / launcher 0.8.10 verification

Source revision: `9401a87ce9273ab82bd5920c97f3b25cf4a661b6`.
Release tags: `patch-pure-0.3.0` and `v0.8.10`.

## Scope

- Vanilla and Immortals share pure data 0.3.0, runtime 1.3.72-pure.11,
  and optional player colors 0.3.0 in both modern catalog channels.
- The data and color payloads, excluding versioned package manifests, are
  byte-identical to the accepted pure 0.3.0-beta.2 payloads. No Arcane Wars
  staging menu, units, balance, city assistant or AI module is imported.
- The optional desync helper now uses the unchanged shared
  `game/beta7/SyncDiagnostics1372.cs` wrapper. It invokes the native log writer
  for the first failure, rearms on a new baseline, and keeps code RX with a
  separate RW signal page. Checksum calculation is unchanged.
- Non-pure game packages and the game packages in legacy v1 feeds are unchanged.

## Completed local checks

| Check | Result |
| --- | --- |
| Complete Release launcher suite | 27,864 passed |
| Isolated account database suite | 6,652 passed |
| Installer regression | 1,686 assertions; 384 selections; 32 transactions; 16 native preflights |
| Pure optional sync guards and failure rollback | 480 passed |
| Shared native sync emulation | 21,312 checks across three relocations |
| Real CPU state preservation | First/repeated failure, complete FXSAVE state including FIP passed; native I/O stubbed |
| Reproducible runtime builds | Four helpers each built twice with identical bytes |

Installer scenarios cover both mods, both channels, six interface languages,
upgrade from stable and beta, downgrade, file-only mode, master off, and
uninstallation. Fixture saves and the supported executable remain unchanged.
The game was not launched and the live installation was not modified.
Native writer emulation and the isolated CPU test are not an in-game network test.

## Production server

`20260927000000_pure_stable_options.sql` was applied to the PawsPatch production
project on 27 September 2026. An independent query after commit verified all
eight conditions: the expected function definition, valid stable Vanilla and
Immortals options, retained beta support, required master patch, rejected
file-only executable options, Arcane AI remaining beta-only, and no public
EXECUTE access to the private validator.

The normalized validator definition MD5 changed from
`8ed7bc2f5e9d4183aaadc8ac7aee9949` to
`c7e552eb159ab343ae719f92a28286b8`. The migration checks both definitions and
changes only the pure channel restriction; existing authorization is retained.

## Publication verification

The release workflow [36329215683](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/36329215683)
and the source build/test workflow both completed successfully. The complete
launcher suite was rerun with the final catalogs: 27,864 passed. Downloaded
EXE, ZIP (including each contained file), and all three pure packages matched
their recorded sizes and SHA-256 hashes. The existing unsigned Authenticode
policy remains unchanged; update catalogs are separately signed with the
production ECDSA key.
`tools/PreparePure030.py` requires the completed installation and production
server evidence before promoting the catalogs. It verifies immutable tag
commits, the launcher artifact manifest, downloaded asset sizes and SHA-256,
all four catalog signatures, and unchanged Arcane packages. A final readback
compares the public catalogs and history against the catalog commit.

Local evidence is retained in `outputs/release-pure-030-20260927` in the outer
workspace, including the production readback screenshot and JSON reports.

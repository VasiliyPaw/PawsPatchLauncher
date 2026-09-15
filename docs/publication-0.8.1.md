# Launcher 0.8.1 publication — 2026-09-15

The user accepted the language tests and authorized publishing the launcher and
its localization packages. Release: https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v0.8.1

## Artifact identity

- Source commit: `8e8c180cb713f32704b1768192304d120a2092a3`.
- EXE: 73,110,054 bytes, SHA-256 `8912B7BBE87A497C6FCAE7DE93325473AF66C2286AC9E344652A93D077635622`.
- ZIP: 67,708,044 bytes, SHA-256 `B187587EFBA39BBE868F00AA416BA0A4C6BBC3C228E89614B6A37B8698206993`.
- Self-contained Windows x64 build, product version `0.8.1`, production feed URLs,
  no test marker or test profile. Third-party audio notices are embedded in the
  executable and included in the ZIP.
- Authenticode: unsigned, matching the repository's current signing configuration.
  The four update catalogs are independently signed with the existing production key.

## Validation

- 26,400 core checks passed.
- 52,161 language checks: 576 configurations across three mods, two channels,
  six text languages, four speech languages, patch on/off and file-only on/off.
- 76 real resource reconciliations in an isolated folder, including cached offline
  reuse with zero network requests. No game process was started by this release audit.
- Eight translation regression tests passed, including validation of 30,252
  translated engine strings.
- All 53 current patch-feature descriptions present in UK/CS/DE/FR resources.
- Nine packaging/signature checks passed; production configuration and ZIP contents
  checked separately against the build.
- GitHub build and tests passed for the source commit:
  https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/34995663304
- 33 new immutable module archives, containing 8,573 validated payload files.
  Preview version labels were removed from module manifests where applicable;
  every tested payload file was preserved byte-for-byte.
- Anonymous download verification passed for all 75 unique URLs referenced by the
  four catalogs (612.2 MiB), checking both size and SHA-256. The public portable ZIP
  and artifact descriptor were also downloaded and verified.

## Catalog scope

Each v2 channel contains 59 packages. Both v2 catalogs retain the current game
compatibility metadata and use the accepted language-aware package selection and
guides. Legacy catalogs retain their previous gameplay packages and advertise the
new launcher. Previous signed catalogs are preserved under `feed/history/`.

The stable/beta Arcane Wars core identifiers remain `0.2.1` / `0.3.0-beta.7`:
the tested helpers validate that exact core identity. This multilingual build has
new immutable release URLs and archive hashes; no earlier release asset is
overwritten. Native EXE hashes remain part of the beta lobby compatibility check.
Balance and the existing beta.7 crash fixes are retained.

Working evidence and signed candidates are retained in the workspace's
`outputs/release-0.8.1/`. Publication scripts separate staging, upload, public
verification and catalog promotion, and reject changed public baselines.

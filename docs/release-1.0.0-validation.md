# Launcher 1.0.0 release validation

Authorized release of the reviewed ModDB/Darquan download flow. Arcane Wars is
publicly accessible; the red access badge and local repeat-download button are
not shown. No test build flag/profile is compiled into the release.

- Local Release build: zero warnings/errors.
- Full suite: 37,681 assertions passed.
- WPF public Arcane access: 29 checks passed, including guest, ordinary signed-in
  and offline selection, download guards, hidden notice and no admin escalation.
  Shared layout/transfer checks passed; no repeat-download button remains in XAML.
- Original RAR + unchanged author patch: 6,599 files and module manifest exactly
  match the existing `0.82.1.8-clean.1` package.
- Only the two reviewed archive hashes are equivalent in multiplayer reports.
  Tests verify equal network fingerprints/report comparisons and detection of
  an actually changed file. Download and installed-file hash checks stay strict.
- NuGet vulnerability audit reports no known vulnerable direct/transitive packages.
- The prior isolated real-file installation/verification/uninstall fixture passed.
  No game or VM was launched for this release.

## Feed rollout

`feed/v3` contains the signed split-source package. Existing v1/v2 game catalogs
remain untouched so old clients can obtain the new launcher before migrating.
Only exact official URLs with the production signing key migrate to v3; custom
and unsigned feeds remain unchanged. Launcher metadata/news are subsequently
promoted across all six signed feeds using the tagged CI EXE/ZIP and artifact
manifest, followed by public signature/hash readback.

The author patch bundle is uploaded unchanged to the v1.0.0 draft before tagging,
so it is available when CI publishes the EXE. No local path is present in v3.
Future game catalog publications must update v3 as well as any intentionally
maintained older channel generation; v3 is the current launcher's primary feed.

## Known boundary

Direct ModDB requests currently encounter a Cloudflare challenge on this
connection, including the user-supplied mirror link. The normal browser download
and verified RAR import remain the supported fallback. No challenge bypass is
implemented. The author's download-counter attribution has not been measured.

Tag publication/CI and final feed readback are recorded after completion in the
release output folder; build/test success alone is not publication proof.

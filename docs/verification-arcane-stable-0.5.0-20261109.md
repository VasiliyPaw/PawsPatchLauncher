# Arcane Wars 0.5.0 stable promotion — 9 November 2026

The user authorized promoting the current beta before integrating the next beta.
This promotion inherits public 0.5.0-beta.4 and its beta.3 data overlays. New
performance/UI/recon/voice changes are excluded. Launcher 1.0.12 and all Pure,
Immortals, beta and legacy package references remain unchanged.

Eight helpers are rebuilt from the hash-pinned accepted no-hotjoin snapshot
`C:/PawsNoHotJoinQA-20261107/helpers-r2/build-report.json`. Every embedded resource
and source is verified; only `LargeMapsLocal.PatchVersion` becomes `0.5.0`.
All feature dictionaries exactly match the beta apart from that version.
All 40 native/helper self-tests pass; active-match admission remains disabled,
and legacy save/lobby recovery remains disabled.

Seventeen archives change release metadata; helper EXEs and their version INI
are the only payload differences from the accepted public beta. Every remaining
payload byte is compared and preserved. Six-language notes use short player
visible bullets. The stale base guide version is corrected to 0.5.0.

Launcher-native checks: **619,010 assertions / 55,296 selections**, including
all three mods, six text languages and component combinations. Only the intended
stable Arcane configurations receive the update. **12** real transactional
installation/rollback compositions pass: eight helper combinations, locale
overlays and patch-off rollback, with hash/preflight validation. No game was
launched by this promotion QA. Cached verified original Arcane files avoid an
unrelated ModDB 403; public new archives are downloaded separately before catalog
promotion. The installed EXE and both original saves retain their initial hashes.

Scripts and audit records: `tools/Arcane051Release/` and
`outputs/arcane-051-release-20261109/stable/`. Publication gates check public asset
size/hash/digest, ECDSA signatures, unrelated catalog scope and pinned public
baseline before publishing signed catalogs. These checks do not claim a new
live multiplayer test; gameplay payloads are inherited from the accepted beta.

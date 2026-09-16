# Arcane Wars beta.9 validation

Only the v2 Arcane Wars beta changes. Launcher 0.8.3, stable, legacy catalogs,
Vanilla, Immortals and all unrelated payloads retain their existing identities.

## Native helpers

- Eight x86 release EXEs compiled with the full beta city, lobby and transfer
  features plus `LAIR_RECOVERY`. Standalone-only launch-data overrides are absent.
- Every variant passed its five existing offline self-tests. The lair build
  passed 2,664 native cases and 3,981 transactional installation/rollback checks.
- Existing city planning, militia, preferences, construction, market, transport,
  saved ownership and fast-transfer regressions passed. No game was launched.
- The native r3 payload is byte-identical to the user's accepted standalone
  test: SHA-256 `2965D9DFA1A5EBD1FB20D718C78248DFE67DA92AE9396A700BEE5424F173A004`.
- Final assembly audit: 97 checks across all eight helpers. Each startup calls
  the guarded lair installer; six relocated outputs per helper equal the accepted
  test. Matching beta.9 configuration passes and beta.8 configuration is rejected.
  No minimap runtime type or resolution handling is present.

## Package delivery

Four immutable modules change: pawpatch-core, common-ui, player-colors and
desync-continue. All 11 copies of the eight helper names are replaced. Other
payload changes are exactly the version INI and 18 new static frame files.
Package staging verifies all file sizes/hashes, signatures, scope and preservation
of unrelated packages before publication. Public assets are downloaded and
hash-checked before advertising the signed catalog.

The dedicated launcher-installer regression exercises 192 selections across
six text languages, master on/off, file-only mode and eight option combinations.
It installs beta.8 into an isolated fixture, upgrades through all eight beta.9
combinations, verifies 144 installed frame copies, runs eight explicit preflights,
then downgrades and uninstalls. Save sentinel and stock game EXE are retained;
new frames are removed on rollback. The user's real game is read only.

## Frames and remaining boundaries

The 18 textures (six races × three UI texture groups) are exact copies of the
approved local files. Their TGA dimensions, alpha, minimap pixels and existing
art outside the old gutters are preserved. They target 16:9 including 1080p and
1440p. The user explicitly requested plain file replacement, so there is no
resolution detection or automatic choice. Other aspect ratios are not claimed
as fitted. The release adds no separate gameplay, save-format or ownership change.

The earlier fire-dragon combat checks were performed by the user; they accepted
wounded redeployment and no premature dead redeployment. The release validation
here is offline, not a new live multiplayer session. See the lair recovery README
for the conservative rule for wounded home defenders after loading a save.

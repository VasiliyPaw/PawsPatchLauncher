# Arcane Wars 0.5.1 stable promotion — 2026-11-15

Promotes the existing public Arcane Wars 0.5.1-beta.5 composition. Gameplay, native payloads, resource settings, language files and optional component behavior are retained. Eight ordinary x86 helpers are rebuilt from the exact hash-bound beta.5 compiler inputs, changing only the single patchVersion literal in each LargeMapsIdentity source from 0.5.1-beta.5 to 0.5.1. The shipped patch-version INI receives the same identity change. No new optimization is introduced.

Seventeen changed Arcane packages receive stable module version 0.5.1 and experimental=false. Except for the rebuilt helpers and version INI, all payload files match their accepted beta archives. Files outside those packages, including the original Arcane distribution, retain their identities and URLs. The accompanying build-input ZIP contains the exact compiler inputs, resource hashes and reproduction notes; no game executable, RWD, save, profile or signing key.

Validation completed before publication:

- Eight helper variants, five built-in self-tests each: 40 successful self-tests.
- Ninety-six embedded resources compared byte-for-byte between the eight beta and stable helpers: unchanged.
- Launcher 1.0.18 local assembly: 619010 assertions across 55296 component/settings selections, covering both channels, all three mods and six text languages. Stable update detection is limited to enabled Arcane patch installations; other mods and beta retain their previous composition.
- Twelve actual transactional installations into a new marked G: fixture: eight helper combinations and DE/FR/CS/UK language paths, including patch-disabled rollback. Installer reconciliation, generated menu metadata and selected executable hashes passed. Original base Data.rwd/Music.rwd hashes match before and after. The game was not launched.
- Package manifests, archive SHA-256, payload lengths and payload SHA-256 verified. Final signed feed packages match the exact package bytes used in installation acceptance.

Only feed/v3/stable.json, feed/v2/stable.json, feed/changelog.history.json and feed/patch-guide.json are promoted after release-asset upload and public byte verification. Launcher 1.0.18, Vanilla/Immortals packages and guides, all beta feeds, and legacy v1 feeds are preserved. Git publication uses a private index and commit-tree; shared checkout HEAD and its pre-existing staged change are preserved. Each publication rejects unexpected public-main movement.

Release notes summarize the retained 0.5.1 beta fixes in six languages. The first beta's obsolete claim about experimental troop rendering optimization is omitted because that experiment is disabled in beta.5. This promotion does not claim a new live-match, graphics, aircraft-deletion or multiplayer regression pass. Earlier beta.5 validation limits remain applicable; this is an authorized promotion of its existing implementation.

Required GitHub Build and test must pass on the promotion source commit before assets are published. Final catalog CI and a readback from immutable commit URLs and canonical stable URLs are checked after publication. The full local acceptance, upload and readback records are retained under outputs/arcane-promote-20261115 in the project workspace.

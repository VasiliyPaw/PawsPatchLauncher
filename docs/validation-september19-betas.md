# Arcane 0.3.2-beta.2 and pure 0.3.0-beta.2

## Scope

Arcane's four native-containing modules replace all 11 helper copies with the
eight company-position-recovery builds and update the package version marker.
Every other payload byte, including the 39-color palette, accepted camera/lair
fixes and 18 minimap frames, is retained. The new company payload matches the
accepted local save test: SHA-256
`6b04df6597a0d8ac8b33734755a8932bf4fcf2390fb8eff4dceb53e93833839b`.

Vanilla/Immortals beta replaces the selectable palette with the accepted 39
colors, retaining saved-game lookup of retired colors and their original IDs.
The four optional native combinations retain their existing pure-mode features.
The data module preserves its original 16 files and adds the exact 18 Arcane
frame textures for six races and three texture groups. No Arcane gameplay,
company fix, city automation or runtime resolution handling enters pure modes.
The frames remain available in file-only mode and are removed with Paw's Patch.

Only the v2 beta catalog changes, with scoped patch guides and brief changelog
entries. Stable, legacy catalogs, launcher 0.8.5 and unrelated module identities
remain unchanged. New immutable release tags are `patch-0.3.2-beta.2` and
`patch-pure-0.3.0-beta.2`.

## Validation

- Company installer: 138 transaction/rollback checks and 78 emulation cases,
  156 invocations, three relocated layouts, original native eligibility preserved.
- Eight compiled Arcane variants: 217 startup/identity/payload comparisons,
  including accepted company, camera and lair bytes, and unsupported EXE rejection.
- Compiled palette: 19,873 Arcane and 4,969 pure checks across six languages,
  two relocation layouts, visible/retired colors, IDs, RGB values and ordering.
- Pure helpers built reproducibly; pure, transfer and optional desync regressions
  passed. All four explicitly reject an unsupported game executable.
- Actual launcher installer: 384 configuration selections, 29 install/upgrade/
  component-switch/rollback/uninstall transitions, 288 frame hash checks and
  16 explicit preflights covering all 12 distinct helper names in three mods.
- Pure upgrade/rollback restores 39/48 colors; rollback removes added frame files.
  Master-off and file-only selection, stock EXE and save preservation passed.
- Launcher regression suite: 26,872 passing checks; build has no warnings/errors.

These release checks are offline and use isolated fixtures. The accepted live
Arcane test used the user's same save through the Internet lobby: one recovery,
native position restored, replenishment from one to nine members, game left
paused, original save unchanged. No new live game or multi-PC session was run
for this publication. Existing battle and hero-replacement acceptance boundaries
remain documented in `game/company-position/README.md`.

The publication script validates public package bytes and tag source identity
before catalog promotion. Public catalog readback is a separate final step;
local staging alone is not publication evidence.

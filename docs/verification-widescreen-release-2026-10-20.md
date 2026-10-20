# Widescreen repair beta publication

Scope: Arcane Wars **0.4.2-beta.4**; shared Vanilla/Immortals
**0.4.1-beta.6**, runtime **1.3.72-pure.15-beta.6**.

This release includes the app-state-based menu/movie canvas correction, square
lowered Paw button with viewport-relative tooltip, and the confirmed panel
client-rectangle fix described in verification-widescreen-menus-2026-10-20.md.
The user confirmed working battlefield selection and Paw button in a local
Arcane Wars match after the equivalent 12-byte UI-geometry correction.
No match was launched or controlled during publication preparation.

## Scope and source provenance

The four Arcane packages and three Pure packages are rebuilt from the signed
public terrain-beta baseline. Source SHA at preparation: fab960f09fbe15c59a6debbd4ec6b4d702dff7a2.
Unrelated gameplay data, terrain pool, localization/keybind rules, installed
main game and launcher identity remain unchanged. Shared Pure packages target
both Vanilla and Immortals. Stable and legacy catalogs are preserved.

The release utility verifies every source package and per-file hash, replaces
only known helpers/version INI and UI resources, adds 42 lossless atlas crops
per family, and verifies unchanged payload bytes. Existing 21 strips and
three layout overrides are reconciled without introducing a separate switch.
A button-only transformation preserves the remaining game_interface contents.
All 67 Arcane UI resource files match the accepted local fixture byte for byte.
All 12 helper feature reports match the accepted candidate except version IDs.
Pure sources are built with their existing AI profile and native recovery/save
modules; excluded Arcane gameplay payloads remain excluded by the builder.

## Validation

- Eight Arcane helpers: all five offline self-test modes passed each.
- Four Pure helpers: deterministic rebuilds; 816 guarded composition installs,
  477 random-map transaction checks, 24 channel checks, 12 save-copy checks.
- AI option tests: 145 for each profile.
- Presentation composition: 1013 uniform and 605 legacy checks passed.
- Native aspect/poll emulation: 2448 checks; phase/button: 738 checks.
- Native panel picking: 2344 checks, two families, ten sizes, three image bases.
- Asset generation: 5483 checks; visual alpha sampling: 6532 checks.
- Pure installer/preflight matrix: 16/16, six languages per mod, stable rollback
  and patch-disable. Native game executable unchanged; no game launched.

Arcane installation/rollback and publication readback are recorded separately
below once complete. Full visual acceptance across every aspect ratio and mod,
intro-video playback and restart of the persisted manual candidate were not
performed by this release automation; offline checks are not claimed as those
manual tests.

Evidence: task workspace outputs/publish-widescreen-fix-20261020.
Isolated installation fixture: D:/PawWidescreenReleaseQA-20261020.
New fixture files are independent copies; no hard links into the installed game.

# Launcher 0.7.12 / Arcane Wars maintenance validation

Scope: launcher 0.7.12, Arcane Wars stable 0.2.1 and Beta 0.3.0-beta.4. Vanilla and Immortals package identities, guides and game requirements are unchanged.

## Gameplay packages

- Seven immutable replacement archives. Both core packages and the shared `aw-roaming-x4-new` profile change only `dark_rift.tgi`'s `event_time` from 240 to 360 and `event_chance` from 0.4 to 0.3. The other 48 files of the shared roaming profile remain byte-identical. The real ×2 profile already contains 360 / 0.3. Standard, ×2 and profiles without new companies are unchanged.
- 184 package-scope assertions pass. All archive members are checked against module paths, sizes and SHA-256; replacement helpers match their completed build manifests. Four signed candidate catalogs pass verification against the launcher trust root. The finalizer independently verifies all seven archive manifests, release identities, notes and catalog/history/guide consistency.
- All eight helper variants compile in stable and Beta. Feature reports confirm starting-city militia and city policy r15 only in Beta. Beta-generated native resources match tracked resources before compilation.
- Beta checks: city planner 1395; militia lifecycle 59; offline settings 46; emitted native policy 3528, construction 2004, resource input 1755, automation 1332, transport 144; managed fast transfer 663; native fast transfer 8421. Native tests use three relocations and both resource layouts. Helper build self-tests also pass for all variants. Test-fixture CS0649 warnings remain; no failed checks.

## Starting city

The native bridge retains the first observed world time independently of incomplete local-kingdom snapshots. Existing cities are eligible when that timestamp lies within simulation second 0–1, even if the managed reader arrives later. Dispatch waits for an advancing simulation and native militia capability, using the ordinary game command. Later manual closure is respected. Existing cities in established saves remain a baseline. A save made within the first second follows the initial-world rule; this is an observed-time boundary, not an explicit engine new-game flag.

Tests execute the actual native capture entry, covering world changes, rollback, menu boundaries and delayed managed reads. A code-reservation assertion prevents overlap with other emitted routines. Final resources contain 455 relocations; hashes are recorded in the city-assistant README.

## Launcher

- Core regression suite: **16,501 checks pass**. Includes component combinations, offline mod switching, channel isolation and update behavior.
- Offscreen WPF: **63 checks per language, Russian and English**. Actual frequency buttons follow the selected current guide while preserving explicitly pinned archive text. Hover and clicked help agree. Existing channel and layout checks pass. PreviewRenderer build: zero warnings/errors.
- An initial core run rejected an em dash in the new fallback localization string. The string was adjusted to the existing punctuation convention, and the full suite passed afterward.

No user launcher restart, live game launch, game-file installation or multiplayer session was performed for these maintenance checks. Native emulation and planner fixtures do not substitute for live gameplay acceptance. NVIDIA overlay and driver settings were not changed; this release does not claim to fix the previously diagnosed graphics-driver crash.

## Publication procedure

`PrepareMaintenance0712.py` stages hash-verified archives and signed catalogs without changing public feeds or game files. `FinalizeMaintenance0712.py` verifies the final launcher CI artifact, immutable public tags/assets and prior public feeds before atomic local promotion, retaining rollback catalogs. Public catalog publication and normal-URL readback are recorded separately after the release workflow succeeds.

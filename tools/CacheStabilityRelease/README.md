# Three-beta cache stability release, 2026-11-14

Normal helpers for Arcane Wars 0.5.1-beta.5 and Vanilla/Immortals
0.5.0-beta.6 (runtime 1.3.72-pure.20-beta.6). This release uses exact
hash-bound compiler inputs from the preceding published buffer-ownership
release, then the NativeRenderPolicy and ExpandedCache candidate builders.
The build-input ZIPs accompanying each release contain all final compiler
inputs, native sources, emitted hook metadata and a SHA-256 inventory.
They contain no game executable, RWD, player saves or signing keys.

The standalone ordinary build scripts retain their historical defaults.
`context.env()` selects the release output directory, 90% RAM coefficient,
four-hook payload and final versions. Run commands below with the existing
project Python from the checkout; context keeps temporary build data on G:.

1. Pin public HEAD and save the eight original feed files plus shared-index
   snapshot before preparing anything. Never overwrite other work or feeds
   from a stale checkout.
2. Through `context.run`, run ExpandedCache/build.py native, then helpers,
   CacheStabilityRelease/test_native.py and ExpandedCache/verify.py.
3. `prepare.py assets`, `archives`, `catalogs`; `verify.py catalog` and
   `installers`. The no-launch installer fixtures are separate from the
   user's game and the three retained manual QA copies.
4. Copy the unchanged presentation C/header sources alongside the pinned DLLs,
   write validation documentation and `prepare.py bundle`.
5. `publish.py gate`, `source`, `source-ci`. Required public CI must succeed.
6. `publish.py release` uploads and downloads every immutable asset for byte
   verification. Then `promote`, `catalog-ci`, `readback`.

Publication uses a private Git index and a bounded source allowlist. Shared
HEAD, staging, installed game, launcher 1.0.16, stable/legacy catalogs and
unrelated packages stay intact. Only v2/v3 beta catalogs, beta history and
beta guide are promoted. Both releases are prereleases.

The three closed retained QA copies can be updated with `update_qa.py`;
it does not launch a game. The primary copy retains its private-profile
wrapper. These wrappers and memory-pressure injection are never shipped.
Do not run a game or pressure test while another chat owns the active game.

Validation limits: the 80% candidate had an actual heavy-save run, native
pressure eviction/recovery and a new independent save. The final 90% and
aircraft branch have emitted-code/ABI/rollback tests. The user explicitly
deferred the final live run because another chat was running the game.
Do not claim verified final corpse deletion, fog-of-war removal, LAN
compatibility, FPS improvement or an exhaustive visual regression pass.

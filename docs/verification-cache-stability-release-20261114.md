# Cache stability and aircraft falling — three beta releases

Prepared versions: Arcane Wars 0.5.1-beta.5; Vanilla / Immortals
0.5.0-beta.6, runtime 1.3.72-pure.20-beta.6. Public baseline is launcher
1.0.16 and Arcane beta.4 / Pure beta.5 at
3e6346261e4965d937407c741a1db29b11f36a5f.

## Behavior

- Removed bounded model/effect preparation and accelerated graphics-group
  Find from all twelve normal helper variants. Native lookup/allocation is
  used; the preceding published D3D ownership repairs are retained byte for
  byte (DLL SHA-256 3B596B4A9435A8BDCD183906CAABE9CB60706FCE56783D42E8C66C52DA43944E).
- Terrain pool 2048 entries, NIF weights 40/40, animation weights 120/120.
  RAM coefficient 90%, VRAM 60%. These are logical cache budgets/weights,
  not preallocated memory or a guaranteed proportion of physical RAM.
- Adaptive RAM and VRAM budget ceilings 3072 MiB; per-class ceiling 1792 MiB.
  Reserve 768 MiB free virtual addresses and 384 MiB available physical RAM.
  Disable growth in the 768–1024 MiB VA band. Low VA, low physical RAM or
  90% system memory load triggers lower quotas and native eviction under
  native resource locks. VIEW watchdog checks once per second; normal
  native periodic recalculation remains enabled. API failures cannot leave
  a new budget above the historical signed limit.
- Fix the zero-speed fixed point in native aircraft falling at RVA 213DD0.
  The captured dead snowowl had HP 0, falling set, speed exactly zero,
  height 13.3922 and decay not started. At +/-0, retain the existing first
  gravity impulse rather than multiply it by zero. For every nonzero speed
  the original instruction and arithmetic remain bit-identical. This
  changes simulation, so participants must use matching helper versions.
  It does not directly delete actors or change their visibility flags.

## Verification

- Final emitted native cache code: 164 cases at four ASLR/cave combinations,
  including a cave above 2 GiB; unsigned budgets, pressure boundaries,
  overflow, API failure, invalid fractions, class quotas and watchdog ABI.
  The release configuration exercises 90%, not the earlier default 80%.
- Actual emitted fourth aircraft hook: 36 cases including +/-0, normal,
  negative, Inf and NaN speeds; flags, stack, general registers, XMM1 and
  upper XMM0 lanes preserved. Native initialization sets the UVar to 90.
- Twelve normal helpers: 188 compiled resource/hash checks, 36 terrain
  startup guards, 393 transaction checks covering all four hooks, ASLR,
  preflight, partial writes and rollback. Quiet startup and existing
  Arcane feature selftests pass. Other native resources are unchanged.
- Actual launcher 1.0.16 catalog selector: 617474 assertions across 55296
  combinations. Package ownership, helper selection, all six locales,
  stable preservation, Pure and the launcher descriptor are checked.
- Actual transactional installer: 20 Pure cases (Vanilla and Immortals,
  all six languages, data-only, reapply, disable and stable rollback) and
  12 Arcane cases (all eight helpers plus locale selections). Original
  base RWD archives were hashed before/after and remain unchanged.
- Seven archives were derived from exact currently published packages.
  Only normal helpers, the terrain/cache UVar overlay and Arcane version
  INI changed. D3D and all unrelated packaged files retain their hashes.
  Signed v2/v3 candidates preserve launcher 1.0.16 and unrelated packages.
  Only the two beta catalogs, beta history and beta guide are promoted.
  Releases include exact build-input ZIPs with SHA-256 manifests.

## Live evidence and limits

The preceding 80% candidate loaded the user's copied heavy save with all
six players (human plus five bots), 177 companies, visible own armies and
continued simulation. A temporary QA-only memory-query callback exercised
native eviction/recovery without exhausting actual system memory. It was
restored and that QA process exited normally. A separate new save was
created; the original source and QA input saves retained their hashes.

The user explicitly deferred the final live run because another chat was
running the installed game. No second game was launched for this release.
Final 90% live behavior, corpse removal and loss of scout-provided vision,
LAN play, a multi-hour soak, true memory exhaustion/fragmentation and FPS
A/B remain unverified. The 80% run is not presented as a final 90% test.
Native code and installer evidence do not establish an FPS improvement or
the absence of every historical texture/animation symptom. Large logical
quotas can reduce reloads, but higher residency/eviction can also cost
memory and frame time; the actual benefit needs comparable live measures.

Three existing closed manual QA copies were updated atomically on G:
without launching them. The primary copy retains a private-profile helper;
QA helper/pressure injection are absent from public packages. The installed
game, source save, shared checkout HEAD/staging and unrelated work are not
modified. Detailed local evidence is under
outputs/cache-stability-release-20261114. The root project storage and
retired-resource preservation rules remain in effect.

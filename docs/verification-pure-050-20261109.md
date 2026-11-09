# Pure 0.5.0 beta 1 verification — 2026-11-09

Vanilla and Immortals use the native Kohan II 1.3.72 executable, SHA-256
`1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.
The preceding Pure 0.4.1 stable promotion removed automatic network recovery;
its multiplayer save/copy runtime remains unchanged in this beta.

The scoped build scripts are in `tools/Pure050Release`. Private build evidence
is under `outputs/pure-041-050-20261109`; disposable live profiles are under
`G:/PawPure050QA-20261109`. These are separate from the installed player game.
No original game archive, signing key or private QA input DLL is distributed.

## Scope and native data

- Dynamic lighting is installed at the native simulation tick and mission Sun
  assignment. It uses native `GWorld+E8` time, a 600-second cycle, the creator
  seed, and the serialized integer `PawsDayPhase`. The clock only reads this
  state. Native pause and game-speed changes apply to both.
- Both modes have three native climates: temperate, arctic and desert.
  There is no imported cursed climate or Arcane object catalog. Each mode's
  object definitions are transformed independently. The 61 climate spawn masks
  match between modes; the object data retain the native mode differences.
- The generator combines broad regions; Random chooses a count of 1–3 and
  distinct native climates. Lair/technology densities follow actual areas.
- Maximum map size is 2048. The extended registry supports 262143 total IDs,
  including 65535 primary actors and 196608 scenery objects. New worlds use
  the extended save format; old-format worlds retain their original format.
- Company and kingdom-point caps retain their native values. The three Arcane
  company-cap hooks are excluded. City automation, automatic militia, extra
  building slots, foundations, fractional points and Arcane recon/fort changes
  are not linked into the Pure presentation module.
- Four native helpers retain the existing color/desync variants. The optional
  roaming packages keep their timings/companies; two higher-priority hostility
  template packages receive the same expanded size list.
- The common package adds separate text resources for six languages, the clock
  label and native game-menu layout. It does not replace complete locale tables.
  File-only and disabled-Paw modes exclude the native-dependent common/rules.

## Final candidate

The accepted compiler inputs/resources are bound by `beta-helpers-r4/build-report.json`.
Runtime version: `1.3.72-pure.17-beta.1`; patch version: `0.5.0-beta.1`.
Native presentation DLL SHA-256:
`228A41B3750043BB08E5CBF0F5D6E14C022B1EF8878815295E68F5F12E9965C0`.

The production DLL exports only its queued installer and view-thread frame.
There are no QA exports, external loader/marker requirements, actor hooks or
performance modules. Its frame is called by the native minimap update.
`paws_presentation.ini` is runtime-owned, with exact UTF-8 bytes
`[Runtime]\nstartupReadyEvent=1\n`. The helper signals the process/start-time-bound
readiness event after all modules finish installing.

`ui-native-r3` changes only the native game-directory comparison from r2:
equivalent trailing separators are removed before comparison. The UI C source,
clock header and managed loader are byte-identical to the preceding live-tested
snapshot. This fixes the ordinary helper entry point, whose application base
directory ends with a separator; explicit `--game-dir` had masked that case.

## Offline and actual Win32 checks

- 108443 relocated x86 world checks: actual compiled generation, paint adapter,
  all seven native biome subsets, deterministic partitions across three bases,
  saved start offsets, lighting interpolation, static/native fallback.
- 1431 extended-registry checks, including save encoding, terrain and minimap
  rasterization; 528 installer fault/partial-write/guard/rollback checks.
- 519 world-installer transactions with faults at every operation and native
  guard mismatches, at three image bases.
- 1464 guarded installs in 12 complete helper compositions at three bases;
  477 random-map transactions, 24 lobby/channel cases and 12 save-copy Block
  preservation compositions. Native UI call sites remain available to the
  presentation installer.
- 2634 compiled x86 minimap/clock checks, including 0.1 wheel steps, partial
  detents/clamps, forward/inverse transforms, camera movement without cached
  image deletion, pause/static/random lighting and HUD clock reuse/deduplication.
- 27864 actual emitted HUD checks: three image bases, nine resolutions, menus
  versus matches, register/SSE/flag/stack preservation, named/template-named
  dialogs and the native anonymous resign vtable.
- 22 actual Win32 queued-validator checks: old and corrected DLL, 11 cases
  each. The old default-directory form rejects at path guard 3; the fixed form
  reaches the intentionally absent native engine prologue and rejects safely
  at guard 6. Wrong directory/API/image/view thread and active-game cases remain
  rejected. The fake executable runs no game and applies no native patch.
- 20 real launcher installer compositions: six locales, all helper variants,
  optional hostility/roaming choices, stable rollback, patch disabled, file-only
  and beta reapply. Compiler/runtime dependencies were snapshotted; the shared
  launcher project and build directories were not rebuilt by these checks.

## Native game acceptance

`vanilla-large-r7` completed an actual 2048×2048 Mixed / Dynamic / All match.
Settings were selected through native widgets and checked again in the loaded
world. Terrain census contains exactly the three native climates. One clock is
visible; pause freezes time, light and clock; its displayed minute matches the
serialized phase. Game speed advances the same simulation time. Native save and
normal exit succeeded without assertions/desync errors.

Its independent lighting readback contains 1940 coherent samples spanning
1064.25 game seconds, exceeding a complete 600-second cycle. Maximum error
against the original native Sun profiles is `8.613425939163477e-8`. Screenshots
also verify wheel input/camera motion, centered game menu and save dialog.
The largely black minimap under Full fog is expected unexplored terrain; the
stable fixture behaves the same, with only the owned city's small revealed area.

`immortals-reload-r1` created and saved an actual Mixed / Dynamic / Random 384
match; its pause, lighting, clock, speed and native save checks passed. Its later
automatic navigation failed because normal departure opens score/LAN screens,
so that entire run is retained as a partial result, not a complete pass.

`immortals-resume-r2` cold-loaded that real save, preserved phase 2692, displayed
one clock and advanced simulation. It then returned through the native score/LAN
flow and created a new match in the same process. The new match has a different
random phase and exactly one clock. Normal exit and error scan passed.

The final two-peer candidate result and exact package hashes are recorded in the
publication acceptance/readback receipts. Local LAN coverage does not claim a
new Internet/VM, three-player, host-migration or historical-film compatibility run.

## Failures found and corrections

- The first mode port referenced Arcane-only `arctic_snowswamp01` and
  `desert_quicksand01`. Native generation correctly failed. They were replaced
  by native tundra/scrub and the builder now validates all referenced climate
  terrain IDs against the original stock archive.
- Console-only QA could edit a dormant dialog clone while the active lobby
  still used 384/static settings. Those attempts are not Dynamic/2048 coverage.
  Accepted settings use native widget input and loaded-world assertions.
- A 2048 clock check originally ran during loading, at tick zero, before the
  HUD existed. The driver now waits for the actual ready world and interface.
- The ordinary helper's trailing-directory mismatch was reproduced and fixed
  with the real queued Win32 validator, independently of the game fixture.
- Native phase values with an empty label appeared in save-lobby summaries.
  Every RMC now explicitly hides `PawsDayPhase` through its native Rules UI flag.
- Earlier pair attempts are retained as failures. One stopped at the private
  memory reserve; another never completed the client's queued startup script.
  Pair r3 entered the native LAN lobby but timed out before launch. The old QA
  `StagingReady 0` command clears readiness: native button logs confirm that 1
  sets it. Manual toggles and repeated launch requests made that attempt
  unsuitable for acceptance. Later manual pair navigation uses only an Echo
  startup script, then individual native requests after actual helper/menu
  readiness. It preserves command sequence numbers and explicitly enables the
  known private `MPRunWhenInactive` setting. Map settings still use real widgets.
- Disposable single-player checks retain a 2 GiB available-commit reserve;
  pair checks use 1 GiB and retain the separate 3 GiB physical-memory guard.
  Memory readback is recorded throughout. These are QA stop conditions, not
  shipped game or system-memory changes.
- Computer Use initialization was unavailable on this machine. A fallback QA
  input driver targets only a marked game path, PID plus creation time and its
  unique native window. Native PrintScreen captures the Direct3D scene; desktop
  capture returned black. None of this instrumentation is shipped.

Failed/partial artifacts remain available. No test closes a foreign process or
modifies the installed game. Publication scripts preserve stable and legacy
feeds and every non-Pure package/guide from the freshly verified public baseline.

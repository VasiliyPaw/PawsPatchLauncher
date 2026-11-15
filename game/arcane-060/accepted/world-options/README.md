# Dynamic time and mixed-biome selection — local 2026-11-07 build

Latest follow-up: the random-map rule panel now fits three complete rows without scrolling (verified at 800×600); enum fields are wide enough to show Russian Dynamic in full. The panel takes 24 logical units from the object/preview panels and keeps the buttons in place. This UI fix is part of `prepare.py` for normal builds as well.

Temporary visual preview: `C:\PawsWorldOptionsQA-20261107\manual-fast30\Start-Game.cmd`, version `0.5.0-local-world.2-fast30`. Select Dynamic when creating a map. This copy cycles in **30 game seconds**, and its six language descriptions say 30 seconds. Private profiles and zero QA plugins; native main-menu startup and normal exit verified. The old manual copy remains intact.

Preview inputs/results: `native-fast30`, `source-fast30-r2`, `helpers-fast30`, `qa-helper-fast30`, `live-fast30`. Normal compact UI build: `source-compact`, `helpers-compact600`, version `0.5.0-local-world.2`. Its 600-second native payload is byte-identical to the previous accepted build. Both sets of eight helpers passed their five self-tests (80 checks total). The canonical checked-in generated payload remains the normal 600-second one.

`live-fast30/world-options-acceptance.json`: accepted, 68.8125 simulated seconds after cold return (more than two preview cycles), 68 common native CRC samples spanning 67 seconds, zero mismatches; saved phase and pause behavior preserved. Maximum color error against the 30-second formula: 1.04e-7. Actual generated subset: desert and temperate.

Rebuild the preview with `build_native.py --cycle-seconds 30`, `prepare.py --cycle-seconds 30`, and `build_helpers.py --version 0.5.0-local-world.2-fast30`; use fresh output directories. Default arguments retain 600 seconds. The helper builder rejects mismatched data/native cycle durations. Native validation supports `validate_live.py <run> --cycle-seconds 30 --minimum-seconds 60`.

Earlier accepted local patch version: `0.5.0-local-world.1`. No release, feed, server, VM or installed-game deployment was performed.

## Behavior

- Sun gains **Dynamic**: a random continuous starting phase followed by morning/day/dusk/night, with a complete cycle every **600 simulated seconds**. Simulation pause stops the cycle; game speed changes its wall-clock duration.
- The phase is a hidden native integer WorldRule, initialized from the map creator seed and serialized by the original save/network system. Colors come from the original Arcane Sun profiles, interpolated with smoothstep. No runtime random generator calls, wall-clock timers or asynchronous simulation writes are added.
- Mixed maps gain **Biomes → All / Random**. All keeps the existing four-region policy. Random uniformly chooses a count of 1–4, then distinct biomes. Regions retain their broad irregular geometry; shared building density and the existing climate spawn gate use the same remapped partition.
- Native WorldRules defaults are unlocked. Explicit `show_ui = false` entries in the other RMC definitions hide Biomes there; the mixed RMC explicitly enables it. `PawsBiomes` and `PawsDayPhase` also have native SVars, required by the engine loader.
- Six languages: English, Russian, German, French, Czech and Ukrainian. Russian Arcane's later full-table hotfix must receive the strings as well because localization layers replace whole files.
- Launcher custom RWD management is a tab of **Components → gear**, with the existing import/order/replace/apply behavior. It no longer occupies a sidebar page. Existing translated tab names are reused.

## Local files

Root: `C:\PawsWorldOptionsQA-20261107` (G: had insufficient free space).

- `manual-game\Start-Game.cmd`: tested private game entry point. Uses the owned copy, Steam app ID, explicit game directory and private Documents/AppData. The startup adapter changes process/profile isolation only; gameplay is the compiled patch. QA observer/input plugins are disabled (`Mods\plugins.txt` is empty).
- `launcher-local\PawsPatchLauncher.exe`: current launcher build with a private test profile pointing to the owned game. Marker `01-offline` blocks launcher HTTP transports; this copy is for local UI checks, not public installation/update.
- `helpers-final\build-report.json`: all eight production-style helper variants and 40 successful helper self-tests.
- `source-r5\preparation.json`: final data composition, baseline and changed hashes, six locale tables plus the Russian override, four RMC files.
- `native-rebuilt\native`: reproducible native payload, matching the checked-in `game/mixed-biomes/MixedBiomesPayload.cs`.
- `accepted-beta2-inputs-r2\build-report.json`: self-contained hash-pinned snapshot of 84 accepted beta.2 compiler inputs. Use this snapshot after updating the canonical generated payload; the old historical report refers to its old repository hash.

Native payload SHA256: `E84004C26D59B77BF866B2EA9BD1B5C408B6E0C16FD44F2EA064DCFE3E153AF4`.
Canonical generated C# SHA256: `CF409C809B2C2E782FE45D533BDC4DE0A6C16301BAB4E31C385D698A75CB39EF`.
Existing shipped hotjoin DLL is unchanged: `3FAAB2651FA26C2C6CE42E96B0566ADF63070FA2724AF7B70069DF75AE475974`.

## Verification

- `policy-r1/acceptance.json`: real C policy, 10,000 seeds; counts 1/2/3/4 occur 2396/2570/2517/2517 times; all 15 nonempty biome subsets; 128 region maps; 9,601 interpolation samples.
- `native-tests-r1/native-tests.json`: 3,646 actual x86 region/gate/cap checks at three image bases, including 89 spawn definitions.
- `transactions-r1/verification.log`: 1,104 install/guard/rollback checks for the eight-hook payload.
- Launcher: custom-mod UI 96 checks × six languages; existing game-settings UI 42 checks in Russian. Russian 1050×680 and 1440 screenshots were inspected.
- `live-r10/world-options-acceptance.json`: two owned native peers, Mixed 896, Dynamic/Random actually selected in the UI, ordinary client exit, automatic cold checkpoint transfer and return. **634.25 simulated seconds after return; 634 matching CRC samples spanning 633 seconds; zero mismatches**. Actual terrain: arctic 57,723, desert 111,328, cursed 31,653 cells. Hidden phase 3934 survives reload; pause freezes colors; transferred native save bytes match.
- `live-r11/world-options-acceptance.json`: translated UI and another 384 map, different initial phase, successful return; short 13-second follow-up only.
- `live-r12/world-options-acceptance.json`: **final data composition**, ordinary-map Biomes hidden and mixed-map Biomes shown, Dynamic/Random selected. Successful exit/cold return; 68 seconds of matching native CRC evidence, two actual biomes (arctic/cursed), phase 6150 survives reload.
- Manual deliverable also booted to the native main menu with `0.5.0-local-world.1` displayed and zero QA plugins, then exited through the normal menu.

The independent sampler includes loading-screen tick-zero observations. The validator reports these separately; color/pause acceptance starts after native simulation begins. Maximum live color error against the clock formula is approximately 1.13e-7.

Scope: local LAN on the same PC, two native peers. New Internet/VM, three-player and host-migration combinations were not rerun for this change. Existing hotjoin implementation was retained. Old external saves were not migrated or rewritten. No game-balance day/night buffs were introduced; this uses Arcane's existing Sun profiles.

Earlier negative/partial QA attempts are preserved. `live-r7/r8` ran standard 384 maps with static Sun and must not be cited as Dynamic/Random coverage. Early `r4` identified missing native SVars; `r6` exposed an invalid QA-only editor command before a world exists. That QA command path was corrected, and accepted scenarios selected settings through the actual window. No failed build/run output was deleted.

## Repeat

From the main checkout, with the bundled Python executable:

```powershell
$py = 'C:/Users/Paw/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $py game/world-options/build_native.py --out C:/PawsWorldOptionsQA-new/native
& $py game/world-options/prepare.py --source G:/PawHotJoinLab-20261107-release-two-survivors-r6/host/game --out C:/PawsWorldOptionsQA-new/source
& $py game/world-options/build_helpers.py --baseline C:/PawsWorldOptionsQA-20261107/accepted-beta2-inputs-r2/build-report.json --native C:/PawsWorldOptionsQA-new/native --fixture C:/PawsWorldOptionsQA-new/source --out C:/PawsWorldOptionsQA-new/helpers
& $py game/hotjoin-test/prepare_composed.py --report C:/PawsWorldOptionsQA-new/helpers/build-report.json --data-root C:/PawsWorldOptionsQA-new/source/game --out C:/PawsWorldOptionsQA-new/qa-helper
& $py game/hotjoin-test/experiment.py --out C:/PawsWorldOptionsQA-new/live --mode coordinated --automatic --release-observer --scenario return --leave-mode menu --world-options --manual-world-setup --observe 630 --port 5875 --game-source C:/PawsWorldOptionsQA-new/source/game --composed-helper C:/PawsWorldOptionsQA-new/qa-helper/k2_paws_lobby_colors_mp_1372_experimental.exe --language ru
```

During the lobby hold, select Mixed, Dynamic and Random through the native UI, confirm, then create `live/continue-setup.flag` within 600 seconds. The driver asserts the actual loaded WorldRules; a map-selection command merely being queued is insufficient evidence. While live, `census.py <live/host>` records read-only terrain IDs. After normal completion:

```powershell
& $py game/world-options/validate_live.py C:/PawsWorldOptionsQA-new/live
```

Native hooks: existing six mixed/map/UI hooks plus guarded calls at RVA `246a40` (simulation boundary) and `2462bc` (StartMission Sun assignment). Simulation/world layout and color routines are documented in `world_rules.h`, `day_cycle.h` and `build_native.py`. Historical `game/mixed-biomes/build.py` is reused as the emission base; **use the world-options wrapper to include both new Sun hooks**.

# Local Arcane update: graphics diagnostics, siege balance, minimap, KP display

Not published. No patch or launcher version bump. User manually accepted the installed test on 2026-09-20: «всё проверил, вроде вссё робит».

Existing local AI, recruitment capacity, stale city center, exhaustion and bulk bot lobby changes remain included. Do not rebuild from the last published helper alone.

## Changes

- `game/graphics-diagnostics`: native crash recorder embedded in every selected helper, started automatically with the freshly launched game's PID, creation time and exact path. Local full-memory capture on a graphics-driver access violation or second-chance exception; continue normal exception handling and detach. Reports use `Logs/PawsGraphics/log-graphics-*.log` and matching `.dmp`, already supported by the published launcher's diagnostic collector. No uploads. This records evidence; it does not claim to fix the unresolved driver crash.
- `game/fractional-points`: display-only hooks select fractional formats for `kingdom_points_consumed` in the live/preview top bars and resource tooltips. Other resource formats and all economic calculations are unchanged. Whole values have no trailing decimal zeros.
- `tools/GameplayPresentationData.py`: Maelstrom Destroyer (`data/units/gauri/aw_maelstrom_destroyer.tgi`) consumes 0.75 KP per engine with siege balance. Two engines therefore consume 1.5 KP, plus any other members' own costs. Original costs/upkeep/attacks are preserved.
- The same tool sets `radar=false` on both ambient individuals and groups in eagle, snowowl, vulture, AW_duck, AW_ikaris, AW_raven, AW_spineling and lake_fish. Ground herds and the combat unit AW_ikaris_flyer are untouched.
- Siege description/help updated for five engines in Russian, English, Ukrainian, Czech, German and French. Launcher source is prepared; the currently running published launcher was not replaced.

## Required integration at the later authorized publication

1. Build all eight helpers with existing switches `-CityAssistant -LobbyCompatibility -LairRecovery -CameraZoom -CompanyPositionRecovery -ExhaustionRecovery -AiPolicy -BotLobby`, adding `-FractionalKingdomPoints -GraphicsDiagnostics` and the existing native compiler. The recorder is embedded: its loose build EXE is not a user-facing launcher.
2. Apply `GameplayPresentationData.apply_modules(modules, stock)` to verified, normalized payload dictionaries before packaging/signing. It preserves original Arcane data, modifies core, adds the inverse Maelstrom file to `siege-balance-standard`, and updates `aw-siege-balance` when present. Provide stock lake_fish from Data.rwd. Never apply only the core Maelstrom change while forgetting the disabled overlay.
3. `PrepareModModes.py` and `BuildGameplayOptionSources.ps1` also include the fifth engine for their corresponding standalone/inverse option workflows.
4. Include the updated launcher language sources at the next launcher publication. Do not publish as part of this local task.

## Evidence and local installation

Workspace outputs: `outputs/graphics-ui-update-20260920/` (two levels above repository root).

- `helpers/`, `build.log`, `features.json`: all eight helpers built and existing regression suites passed.
- `verification.json`: final machine-readable result; 75 native format/ABI/ASLR checks, 219 patch transaction checks, 8 recorder behavior/identity/Unicode-path cases, 3 verified full-memory dumps, 292 collector/archive checks.
- `installed.json` and `installed-before/`: hashes and backup of the 18 installed files; k2.exe, d3d9.dll, launcher state and unrelated local data preserved.
- `common-data/`, `siege-enabled/`, `unchanged/`, `data-manifest.json`: staged data and original bytes. Local siege option was already enabled.
- Live PID 22760 reached ready state with the new hooks and recorder armed. UI showed 18.5/20 KP. Read-only snapshot found 26 ambient actors with the radar bit disabled. User then took over testing; no further UI inputs or game shutdown were performed.

Game entry point remains `D:/SteamLibrary/steamapps/common/Kohan II/k2_paws_lobby_colors_mp_sync_1372.exe`.

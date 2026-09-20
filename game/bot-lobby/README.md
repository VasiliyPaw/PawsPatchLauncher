# Host bulk bot controls

Build through `beta7/build.ps1 -AiPolicy -BotLobby`, alongside the current Arcane features. The matching UI templates from `prepare_ui.py` are required. Included in Paw's Patch 0.4.0 Beta, independently of the AI improvements setting. Turning off the Paw's Patch master option removes the templates and native controls together.

The lobby has three independent controls: race, faction and difficulty. Custom leaves that property untouched; race/faction also support Random. A changed control applies once to each current host-owned AI participant and establishes the default for subsequently added bots. Manual row edits remain in place until the corresponding common control changes again. Human participants and observers are excluded. Saved-game and replay lobbies are excluded; existing saved kingdom assignments are never rewritten.

Faction choices use the native race compatibility lists. Native definitions supply the translated race/faction/difficulty labels. Custom/Random and UI labels/tooltips support en, ru, de, fr, cs and uk.

`controls.c` uses the existing player-row callbacks, including their native replicated orders. It runs on the UI thread, without additional RNG or gameplay actor writes. Generations are tracked per property and participant, with cleanup on row/menu destruction. The controls are created before visual initialization, populated after initialization, and moved above the stock background panels so their text and input remain accessible.

Five guarded call sites (image-relative): 104a79 menu tick, 127c70 row tick, 12c0ef row destruction, 1057ac menu destruction, 1041d4 menu creation. Menu creation takes its menu object from ESI; the other callbacks use ECX. Each wrapper invokes the original engine call exactly once and preserves its return, flags and floating-point/SIMD state. Failed installation uses the shared transactional rollback mechanism.

Validation: 48 native policy/ABI cases across three relocation bases and 507 managed installation-fault checks. Live Russian Internet lobby verified existing/new bots, all three properties, a persistent manual override, independent Custom behavior, human exclusion, a short new match, returning to the lobby, saved-lobby exclusion and loading the unchanged save. Other language templates were generated, but not visually tested. Two-client network synchronization and long-match AI balance remain untested.

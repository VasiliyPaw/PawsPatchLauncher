# Built-in city policy — 0.3.0-beta.2

Supported executable: Kohan II 1.3.72, Steam build 25068126. The stock EXE is not modified on disk. This feature is mandatory in Beta and absent from Release 0.2.0. The build integrates it with all eight combinations of extended colors, independent hostility and desync bypass.

## Controls and behavior

- F1 opens Settlement Management. Auto-upgrade cities and a 2000 gold reserve are enabled on each new match and each loaded save.
- F1 has four native income-target inputs (stone, wood, iron, mana) with icons and a separate reserve. Enter commits without opening chat. Esc or leaving an input cancels uncommitted editing. Resource targets have moved out of the settings window.
- Shortages have priority. Gold income is the fallback if targets are satisfied or no currently legal improvement can safely remedy a shortage. Orders preserve resource floors or, for an existing deficit, must not worsen it. Markets favor profitable conversion branches (human Bazaar, not Bank).
- Separate cities build concurrently. Real active/manual work is observed; already registered economic effects are subtracted. Future losses reserve capacity immediately; future gains never fund an order before completion. Unknown forecasts fail closed. Siege excludes only its city but does not erase its committed costs.
- A fair local intention queue issues normal engine orders, one pending command at a time. Accepted construction in one city does not serialize other cities. The game handles normal multiplayer replication and payment. No direct gold/building-state or synchronized RNG writes are used.
- A candidate is revalidated before submission, including ownership, busy state, affordability and reserve. Manual construction is observed; switching automation off clears unsent intentions, not an already accepted building order.
- When desync bypass is selected, the game's native chat notification and error sound warn at most once per five minutes. With bypass disabled, ordinary native desync handling remains; city automation still works.

The reserve/toggle are not serialized into saves. Loading resets them to ON/2000. Targets/general rules persist in `%LOCALAPPDATA%/PawsPatch/city-policy.ini`; first production use imports a previous `city-policy-test-v2.ini` without overwriting it. City exceptions reset with the world. The settings window offers general rules, upgrade paths and city exceptions. All peers should install matching Beta and gameplay settings. This experimental release is not a guarantee against desyncs.

City policy and R2 native save-transfer acceleration are built into every Beta helper, not optional launcher components. The in-game checkbox still stops automatic orders.

## Resource-order contract

Every package combination audits the active TGIs: without Shards, nine native resources start `gold, stone, wood, iron, mana`; with Shards, ten start `gold, shards, stone, wood, iron, mana`. `CityResourceOrder` projects either onto five canonical economic resources. Native final-order validation and construction aggregates use the same mapping; raw records retain native order. Unknown counts reject orders. Shards is not another configurable target; native payment rules remain intact.

## Source and payload provenance

`CityPlanner.cs` is the pure, independently tested intention queue. `PawAssistantRuntime.cs` checks the fresh game's path, original instructions/layout and package inputs, installs the payload transactionally, and services its requests. Code pages and writable state are separate. No already-running game can be attached through this release helper.

`build_policy_native.py` extends the verified local `work/city_assistant_1372` base with the accepted policy-r13 controls, construction observer and native inputs, plus the production Shards-order correction. The build byte-compares regenerated resources before compilation. They contain patch-owned x86 code/fixups, not a stock executable.

- `AssistantPayload.bin`: `A8CD806B01F8D87A89DE2AFDB8169AEE8B47CD5E9E954DDF00ABE9BA25846EF1`
- `AssistantFixups.bin`: `CC14DD8BB7D560DB3AC5A8D34F22FAE15EC41B115BFB06F8347876A0765502E2`

The UTF-8 source layouts are encoded as native UTF-16LE files by `game/beta7/build.ps1 -CityAssistant`. RU/EN selection follows the installed localization, independently of the launcher UI language. Both layouts are required package files; the standard city layout is not overwritten.

## Packaging and validation

`tools/PrepareCityPolicyBeta.py` stages three signed replacements, without publishing. Common UI supplies non-color helpers and RU/EN layouts/dictionaries; player colors supplies the other helpers. Core records the version. Other packages, the stock EXE, Stable gameplay and launcher metadata remain unchanged; only shared About help is refreshed in Stable. `tools/FinalizeCityPolicyBeta.py` verifies anonymous immutable downloads, source tag, signatures and unchanged feeds before optional local promotion.

See [the scoped validation record](../../docs/release-030-beta2-validation.md). Native self-tests, package combination audits and single-player smoke checks must not be described as exhaustive multiplayer acceptance.

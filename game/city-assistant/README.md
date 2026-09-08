# Built-in city assistant — 0.3.0-beta.1

Supported executable: Kohan II 1.3.72, Steam build 25068126. The stock EXE is not modified on disk. This feature is mandatory in Beta and absent from Release 0.2.0. The build integrates it with all eight combinations of extended colors, independent hostility and desync bypass.

## Controls and behavior

- F1 opens Settlement Management. Auto-upgrade cities and a 2000 gold reserve are enabled on each new match and each loaded save.
- Enter commits the reserve without opening chat. Esc or leaving the field cancels an uncommitted edit. The two buttons adjust the committed reserve by 100.
- Resource deficits have priority, then gold income, then a randomly selected legal improvement. The local random selection does not consume the synchronized game RNG.
- A fair local intention queue issues normal engine orders, one outstanding order at a time. The game handles their normal multiplayer replication and payment. No direct gold/building-state writes are used.
- A candidate is revalidated before submission, including ownership, busy state, affordability and reserve. Manual construction is observed; switching automation off clears unsent intentions, not an already accepted building order.
- When desync bypass is selected, the game's native chat notification and error sound warn at most once per five minutes. With bypass disabled, ordinary native desync handling remains; city automation still works.

The reserve/toggle are not serialized into saves. This intentionally leaves the save format unchanged, but loading resets them to ON/2000. All multiplayer peers should install the same Beta and matching gameplay settings. This experimental release is not a guarantee against desyncs.

## Source and payload provenance

`CityPlanner.cs` is the pure, independently tested intention queue. `PawAssistantRuntime.cs` checks the fresh game's path, original instructions/layout and package inputs, installs the payload transactionally, and services its requests. Code pages and writable state are separate. No already-running game can be attached through this release helper.

The two binary resources are the accepted r9 interaction/order payload from the local `work/city_assistant_1372` experiment. Regeneration from that experiment's `build_city_interaction.py` was byte-compared before publication. They contain patch-owned x86 code and fixups, not a stock game executable.

- `AssistantPayload.bin`: `DD915732D136F82DAC9DA02D03569EC4A992EFC0709F9D7794E85779494C0BDF`
- `AssistantFixups.bin`: `E469FE6BF24FA145AB00CE0A1DC0D5161D276D1CA0501D065E809FF810023214`

The UTF-8 source layouts are encoded as native UTF-16LE files by `game/beta7/build.ps1 -CityAssistant`. RU/EN selection follows the installed localization, independently of the launcher UI language. Both layouts are required package files; the standard city layout is not overwritten.

## Packaging and validation

`tools/PrepareCityAssistantBeta.py` stages and signs four replacement Beta packages; it does not upload or advertise them. Common UI supplies the four non-color helpers and both layouts; player colors supplies the other four helpers. Core records the new patch version. Powers/Shards additionally fixes an old resource definition incorrectly inserted into a comment. Other packages, the stock EXE, the stable feed and the launcher release remain unchanged.

See [the scoped validation record](../../docs/release-030-beta1-validation.md). Native self-tests, package combination audits and a live single-player smoke check must not be described as an exhaustive multiplayer test.

# Built-in city policy — 0.3.0-beta.3 / r14

Supported executable: Kohan II 1.3.72, Steam build 25068126. The stock EXE is not modified on disk. City policy is included in all eight Arcane Wars Beta helper variants. Stable Arcane Wars and the separate Kohan II fixes channels do not enable it.

## Controls and persistence

- F1 auto-upgrade and a 2000 gold reserve start enabled for each new match or loaded save. Four native inputs set stone, wood, iron and mana income targets. Enter applies; Esc or leaving an input cancels editing.
- The new F1 option “Open militia in newly acquired cities” defaults ON and persists across matches and restarts. Newly built or captured cities are eligible after the first coherent world snapshot. Existing cities, including the starting city and cities restored from a save, form a baseline: load/toggle changes never rewrite them. Recapture counts as a new acquisition; later manual militia changes are respected.
- Targets, general permissions, global branches and the militia preference persist in `%LOCALAPPDATA%/PawsPatch/city-policy.ini`. A previous experimental file is imported only when this production file does not exist. City exceptions reset with the world. Auto-upgrade ON/2000 still resets on load; the separate militia preference does not.
- Settings contains build/upgrade permissions, exact branch preferences and city exceptions. Random idle development has no optional toggle; legacy `other` preferences are ignored.

## Economy and native construction queue

Resource-income shortages take priority, considering the expected completion of all accepted manual and automatic construction. Useful gold-income upgrades come next, followed by resources needed for an available profitable branch. If no useful income action remains and all four current incomes after outstanding adverse effects strictly exceed their targets, the planner randomly chooses an eligible building or upgrade. This includes non-economic buildings, city centers and mines; saved permissions and native legality still apply.

Markets of every race have the same exception: when all four resource incomes strictly exceed their targets **before** the order, a market may lower income below a target afterward. Already queued adverse effects count before the comparison. Expected positive income from unfinished work cannot make an early market eligible. Other buildings retain floor protection. Gold income cannot be driven into a new/deeper deficit. Actual resources, native payment legality and the separate gold reserve apply to all orders. Native definition/property queries provide prices and effects; there is no hard-coded race economy or Bazaar-only rule.

Multiple distinct buildings can join the game's own queue inside one city while other work waits or progresses. Haroun's native builders may work concurrently. The assistant maintains one outbound intention awaiting acknowledgement, then can issue another affordable order after native work becomes visible. It neither replaces manual tasks nor creates a private construction queue. Independent owned mines receive resource, gold and random priorities. An actor already upgrading cannot receive its duplicate or alternative branch; a later upgrade step becomes available when the game exposes the completed definition's branches.

Accepted build command 13 follows `67F305 -> 680A80`: it creates the child actor, charges at `680BF7 -> 6959D8`, records construction cost and attaches the actor before builders progress. Upgrade command 21 follows `665D6F -> 665DE0`, charging at `665E28` and storing the target at `ConstructionComponent +28`. These actors/components represent waiting as well as active construction; the recruitment/research `StructureQueueItem` list is a separate system.

The snapshot reads every owned settlement's center/children and independent structures. It deduplicates actors and subtracts the EconomyComponent contribution already registered with the kingdom. `Forecast` includes only outstanding adverse changes for protection. `GoalIncome` includes expected positive and negative changes to avoid redundant suppliers. Future income never pays for a new order, and accepted work is not charged twice. Completion, cancellation and ownership changes regenerate these views. Siege/sale keeps potential losses but excludes unreliable gains; unknown work pauses new spending.

## Transport phase and reserve protection

Sent commands that have not reached simulation are separate from accepted/prepaid work. `native_transport.py` observes the common command serializer `5343B8` only for the real local player's request writer (`admin +274`). Both targeted and selected-command sends pass through this serializer after native send eligibility succeeds. Decrees and replay/film writers are excluded.

A pending group is keyed by native issuing-player ID, command kind and target definition, retaining duplicate counts. It remains pending until the entire original targeted Process (`533D81`) or selected Process (`5339DC`) returns. The latter includes all selected actors' native payments. Foreign/film players cannot acknowledge local groups. Hooks only observe patch-owned state and preserve original bodies, registers, flags and XMM0; they do not substitute simulation processing or change network packets.

Automatic planning and the final native dispatcher wait while any group is pending or unknown. A generation seqlock also requires a fresh capture after send/completion, preventing the final gate from using a pre-payment forecast after a pending group clears. Example: gold 3000, reserve 2000, manual cost 600 followed by auto cost 500. Automation waits for the manual order; after payment only 400 is spendable, so the auto order remains unaffordable. An empty writer or elapsed timeout never counts as acknowledgement. A transport rejection before native Process fails closed until a native world/menu/load boundary; normal rejection inside Process acknowledges its group without a phantom debit.

## Militia authority

Native registration maps `sally_forth` to command 23 (`68FE28`) and `recall` to 24. DenizenComponent updates the center actor's capabilities at `668FD9` and handles these commands at `669664`. The settlement actor itself has no militia capability. Capture and dispatch resolve `city +98 -> settlement +14` to the current center and revalidate its owner. The bridge uses the ordinary command constructor, `KKC_TellActorCommandOrder.Validate`, Send and destructor. It never writes a guessed militia flag or directly invokes simulation processing. An unconfirmed sent militia command is not repeatedly retried.

F1 initialization renders the retained preference using native Check (`7186D4`) or Uncheck (`7186F2`). These are separate operations with `(notify, update)` arguments, so rendering uses `(0, 1)` and selects the operation from the saved value. The next tick therefore cannot mistake an initially unchecked widget for a user choosing OFF. Tests execute both actual native methods for first creation, reopening, saved ON/OFF and later manual toggles.

## Resource layout and provenance

Without Shards, nine native resources begin `gold, stone, wood, iron, mana`; with Shards, ten begin `gold, shards, stone, wood, iron, mana`. CityResourceOrder, native final validation and queued-work aggregates project both onto five economic resources. Unknown counts fail closed. Native payment checks still include every resource, including Shards.

The runtime audit image SHA-256 is `B865D8206990C4F055C51DE857F0B09B88AB5EE3B6AE74EE5232134001AA591C`; the stock executable is `1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`. `fixtures/stock_markets_1372.json` records all six actual stock market definitions/effects and source-entry hashes. Mod/property effects remain native-query driven.

`build_policy_native.py` composes the accepted legacy bridge with native_construction, native_resource_inputs, native_automation and native_transport. Generated resources are byte-compared before compilation. They contain patch-owned code/fixups, not a stock executable. Runtime installation is transactional, restricted to the launcher's own fresh verified game, with executable/state pages separated.

Final r14 resources (448 relocations):

- `AssistantPayload.bin`: `C487A57C8F8A69F1468EC678D5C792F24083B60C9A23089D41E7D168735E5169`
- `AssistantFixups.bin`: `4E19EFB39823B0FBC074F1CE3ADC7B0E77136A88CA1D7B7B0D2551F88476CD61`

## Build and validation

```powershell
game/beta7/build.ps1 -CityAssistant -OutputDirectory C:/PatchBuild/city-beta3 -LegacyWorkDirectory C:/VerifiedKohanWork
```

Use a new output directory. LegacyWorkDirectory contains the verified city_assistant_1372, city_policy_v2 and fast_transfer_1372 sources plus their documented Python dependencies. The accepted local migration path is also recognized; other machines should specify the source root explicitly.

The build runs planner/persistence, militia lifecycle, offline settings-form and emitted-x86 policy/construction/input/automation/transport tests across three relocations and both resource layouts. It also runs eight helper installation/rollback checks and transfer regressions. RU/EN UTF-8 source layouts are emitted as native UTF-16LE. No game is launched by the build. A release-ready manifest is written only after complete output/check validation; packaging verifies all helper and UI hashes. Live game and multiplayer acceptance are separate evidence.

# Native identity and race evidence, 2026-09-14

The existing reader compared the roster player's network peer (`player +4`)
against the manager's local player (`manager +0xc`). Those pointers have different
types. The corrected reader compares the wrapper address itself; it does not use
nicknames, a single-human heuristic, or command serialization's temporary player.

Reference: the previously captured, read-only Steam 1.3.72 mapped image at base
`0x460000`, SHA-256
`B865D8206990C4F055C51DE857F0B09B88AB5EE3B6AE74EE5232134001AA591C`.
Production disk SHA remains the baseline recorded in `game-activity-1372.md`.
No process was launched, stopped, injected into, or modified for this analysis.

## Exact local identity

The following native routines were inspected and executed unchanged as x86 in
Unicorn against an isolated fixture with different wrapper, network peer, world,
and kingdom pointers:

| Routine | Native behavior | Result |
| --- | --- | --- |
| `0x5c94ba` | Read global `0xa53fec`, return its `+0xc`. | Returns the player wrapper. |
| `0x5c94c3` -> `0x5bd1d7` | Obtain that same local player, then read `+0x28` if world exists. | Returns that wrapper's kingdom. |
| `0x5bd1e7` | Return `this +4`. | Returns the distinct network peer. |
| `0x48eec4` | Return address `this +8`. | Confirms shared definition IDS storage. |
| `0x5c94ba`, network peer cleared | Same native local-player lookup. | Wrapper identity still works without network peer. |

All five native executions passed. This confirms the pointer semantics; it is
not a new live two-client multiplayer acceptance test. The new reader also
checks manager and local-wrapper pointers again before accepting a snapshot.

## Race and subrace

The game calls these Nation and Faction. Their descriptors are distinct from
display names, color descriptors, team IDs, and roster nicknames.

- Lobby WorldCreator kingdom entry `+0x18` is the Nation definition, `+0x1c`
  the Faction definition. `0x5c9206`/`0x5c920b` resolves a Nation IDS and stores it
  at `+0x18`; `0x5c9215` uses an existing Faction definition's `+8` as its IDS.
- `0x6f5150` calls the live Nation setter with lobby `+0x18`;
  `0x6f5162` calls the Faction setter with lobby `+0x1c`.
- `0x695cfe` stores the Nation definition at live kingdom `+0x240`.
  `0x695c90` creates a Faction instance at kingdom `+0x23c`;
  constructor `0x6869bc` stores the Faction definition at instance `+4`.
- `0x6f529e` onward explicitly resolves random settings. A null Nation is
  selected from available Nations; a null Faction is selected from that Nation's
  legal Factions. Therefore null lobby choices are independently `random`, while
  a missing match descriptor is unavailable and is omitted.
- The IDS string lives at definition `+8`. `+0xc` is a numeric serialization index
  (see `0x4fa31a` / `0x4fa36e`) and must not be read as a string.

The reader emits lowercase, bounded native IDs in optional `race` and `subrace`
fields, with literal `random` only for null lobby choices. It accepts current and
mod-defined IDs; it does not assign race by player nickname or rely on a fixed
descriptor-array order. Overlong, unterminated, malformed, and unavailable IDS
values are omitted. A changed live race, faction instance or its definition, or
lobby selection discards the torn sample.

`GameActivityNativeRaceTests.Run()` exercises the reader at three relocated image
bases. Its cases include six stock races, five factions, mod-defined IDs, separate
and combined random choices, each WorldCreator source variant, actual match
definitions after random assignment, null match data, invalid IDs, and identity
transitions. A twelve-slot fixture uses a human named Dyspro plus eleven bots and
a separate network peer: it verifies the direct local-wrapper identity without
any sole-human inference.

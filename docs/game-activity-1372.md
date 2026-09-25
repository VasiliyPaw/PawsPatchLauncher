# Read-only game activity

Target: Steam Kohan II 1.3.72, baseline SHA-256
`1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.
Installed helper EXEs are accepted only with this saved baseline and an exact
installed-file hash. Each sample additionally verifies two unmodified native
routines. Addresses below are RVAs relative to the live module, not fixed VAs.

## Native provenance

The disassembly reference is a read-only mapped image captured previously at
base `0x460000`. No game image is added to this repository.

| Field | Evidence / offset |
| --- | --- |
| Session | global RVA `0x5f3fe4`; session state `+0xf0`. Native `KKCSession::ChangeToState` at reference VA `0x5c6113` writes it at `0x5c618f`. |
| Menu/lobby/match | Steam rich-presence routine at `0x4dcf41` uses session state 0/1/2; state 2 without a world is reported as loading. Unknown state is omitted. |
| Editor | application state at RVA `0x5f92f4`, values 5 or 13, from the same Steam routine. |
| Multiplayer | session `+0x100`, also used by the native Steam presence routine. |
| World/time | global RVA `0x5f3fb8`; float at world `+0xe8`; native `0x5c0eb6` labels this `g_gworld->GetGameTimeBeginTick()`. |
| Match timing controller | Global RVA `0x5f3fe8`. Native `SetPaused` at reference VA `0x5c12a2` writes controller `+0x28`; multiplayer vote-to-pause/unpause branches at `0x5abc13` / `0x5abf6b` call this setter. |
| Effective pause | `0x5c1381` returns whether simulation runs: controller bytes `+0x28` and `+0x29` must both be zero. Single-player focus auto-pause additionally applies when bit 1 at RVA `0x5f921c` is clear and the option at `[global RVA 0x5f9480]+0x37c` points to an enabled boolean. Multiplayer ignores this focus branch. GamePausedLabel also reads controller `+0x28` at `0x532de2`. The launcher mirrors the effective gate, including automatic pause, without treating a stalled clock or network as proof of pause. |
| Selected simulation speed | Controller float `+0x20` is logarithmic: `0x5c102d` stores it and computes `pow(2, value)`, multiplied by 100 for the native speed notice (`0x5c10f3`). The hotkey routine at `0x5c1231` updates this same field. Read current memory, not the starting configuration. Timing getter/signature checks use RVAs `0x1612a2`, `0x1613aa`, `0x16107b`; stable controller/state reads bracket the time sample. |
| Participants | session linked-list head `+0xc8`; node `[player,next]`. Native lookup at `0x5c6c0a`; wrapper constructor at `0x5bd080` (vtable RVA `0x4bd914`). |
| Player fields and local identity | wrapper `+0x20` ID, `+8` UTF-16 name, `+0xc` bot, `+4` network peer. Manager global RVA `0x5f3fec`, `+0xc` is the local **wrapper itself**, not its network peer. `0x5c94ba` returns it; `0x5c94c3` passes that same pointer to `0x5bd1d7`, which reads the wrapper's kingdom at `+0x28`. Compare the roster wrapper address directly. |
| Lobby matching | cached native Steam connect string at RVA `0x5f21e0`; accepts only `+connect_lobby <uint64>`, hashes it with a Kohan-specific prefix. No join command/Steam ID is published. |
| Map dimensions | native preview `0x563a35` calls `0x5c747f`, which selects the WorldCreator via `0x5c18a5`, then reads float `+0x3c/+0x40` and passes them to `0x562848`. Session world-source kind `+0x64`: 0 -> creator `+0x80`, 2 -> `+0x7c`, 5 -> `+0x88`, other known values -> `+0x78`. |
| Team order | WorldCreator teams `+8/+0xc`, entries `0xc` bytes, first field ID. Native serialization `0x6f571e` / `0x6f5e37` / `0x6f5d9f`. Numbers are the one-based native team-list order; only populated teams are shown. |
| Lobby team/color | WorldCreator kingdoms `+0x14/+0x18`, stride `0x6c`; entry ID `+0`, team ID `+0x14`, color descriptor `+0x20`. Lookup `0x6f56d7`; world configuration `0x6f5110` / `0x6f5174`. Joined to player `+0x24` kingdom ID, never to the nickname. |
| Live match team/color | Player `+0x28` actual kingdom; kingdom `+0x1f8` team and `+0x1f4` color. Native setters `0x695869` / `0x695844`; team ID `+0x18` verified by `0x6a5711`. Actual state takes precedence over the pre-game template, including saves/random colors. |
| Lobby race/subrace | WorldCreator kingdom `+0x18` Nation definition, `+0x1c` Faction definition. Native `0x5c9206` looks up Nation by IDS and stores it at `+0x18`; `0x6f5150` / `0x6f5162` pass these fields into the live kingdom setters. Null lobby definitions are the native random choices, independently for each field. |
| Match race/subrace | Kingdom `+0x240` Nation definition (`0x695cfe`); kingdom `+0x23c` live Faction instance (`0x695c90`). Faction instance `+4` is its definition (`0x6869bc`). Report actual descriptors after random assignment, with missing data omitted rather than guessed from the lobby template. |
| Definition IDS | Nation/Faction definition `+8` points to its UTF-16 IDS (`0x48eec4` accessor; `0x5c9215` feeds faction definition `+8` back to the IDS lookup). `+0xc` is a numeric serialization index and must not be decoded as a string. Stable IDs are bounded to 80 ASCII letters/digits/underscore/hyphen; unknown mod IDs remain supported. |
| RGB | Color descriptor normalized floats `+0x18/+0x1c/+0x20`, verified by the existing player-color label generator. Non-finite/out-of-range values are omitted. |
| Pending Paw palette | Published r20 WorldCreator detour at RVA `0x295516`, payload `create_world_hook +0x20000`, independently checked `state_init +0x1d000`. Session/init guards, at most 16 kingdom IDs, 64 colors. Pending choice comes from `+0x600`; descriptor list `+0x200`. Random remains unspecified until allocation; saved lobbies use their saved descriptor. Unknown detours do not expose a misleading template color. |

OpenProcess requests only `QUERY_LIMITED_INFORMATION | VM_READ`. No injection,
patch writes, suspension, network hooks or process dumps. Reads happen off the UI
thread. Every handle is closed. Native pointer/list changes discard the sample;
cycles, duplicate IDs, more than 64 nodes, unknown layouts and invalid numeric
values are rejected. The generic Playing status does not depend on this reader.
From 0.7.6, sampling continues past helpers, unsupported/exited bootstraps and
inaccessible processes until a verified native snapshot is found. The existing
helpers may stay alive while waiting for k2.exe to exit; their presence must not
terminate the search. Only the successful game's disk hash is retained in the cache.

## Transport and lifecycle

- The local timing candidate adds optional `paused` and `speed` fields to matches.
  Speed is a positive simulation multiplier, not a percentage; the UI formats it
  as a percentage. Unknown native layouts and legacy publishers omit the fields.
  The bounded display clock scales both sample age and local progression by speed,
  and freezes immediately upon receiving a paused sample. Pause/resume and speed
  changes arrive through the existing heartbeat/detail cadence; they are not instant
  remote notifications. Stale running estimates stop after forty wall-clock seconds.
- From 0.8.7 the optional boolean `observer` is sent explicitly and validated by
  the server. Legacy participants without it retain an unknown role. A true
  observer is human and carries no kingdom-derived team, color, race or faction.
  Lobby detection requires a readable, empty native kingdom IDS at player `+0x24`;
  missing/unresolved WorldCreator entries alone never establish this role.
  During a match the native glyph routine at RVA `0x15d3d9` selects
  `ObserverGlyphInfo` when player `+0x28` is null. Pointer changes discard the sample.
- Optional `_activity` envelope on the existing authenticated heartbeat; legacy
  server rejection falls back to ordinary presence and backs off for 15 minutes.
- Maximum 16 KiB incoming activity; one current private row, no match history.
- Normal friend polling receives only phase/mode/time/map summary. Details are
  available only under existing social visibility/session checks, never to an
  anonymous caller or an arbitrary unrelated account.
- Detail queries strip room/self metadata. Same-room/local-slot matching uses an
  index and reads at most two candidates; ambiguous matches are not linked.
- Closed dialogs stop polling and cancel pending requests. Generation checks
  prevent old requests from reopening/repopulating a closed or different profile.
- Sharing preference and suspended component selection are local preferences;
  friend configurations do not export them.

## Validation boundary

The native layout is supported by disassembly and deterministic relocated-memory
tests. Fresh live menu/lobby/match and two-client Steam account matching have **not**
been accepted in this change. Do not report those scenarios as live-tested.
Production migration was deployed atomically on 2026-09-14. The transaction checked
the two previous function hashes and all five resulting function hashes against
the isolated schema. Read-only production checks confirmed RPC/private grants,
the roster index, valid team/color acceptance and rejection of invalid values.
No production profile, friendship or message rows were used as test fixtures.

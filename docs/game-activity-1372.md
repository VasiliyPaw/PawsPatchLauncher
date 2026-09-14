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
| Participants | session linked-list head `+0xc8`; node `[player,next]`. Native lookup at `0x5c6c0a`; wrapper constructor at `0x5bd080` (vtable RVA `0x4bd914`). |
| Player fields | wrapper `+0x20` ID, `+8` UTF-16 name, `+0xc` bot, `+4` network player. Local network player is manager global RVA `0x5f3fec`, `+0xc`. |
| Lobby matching | cached native Steam connect string at RVA `0x5f21e0`; accepts only `+connect_lobby <uint64>`, hashes it with a Kohan-specific prefix. No join command/Steam ID is published. |
| Map dimensions | native preview `0x563a35` calls `0x5c747f`, which selects the WorldCreator via `0x5c18a5`, then reads float `+0x3c/+0x40` and passes them to `0x562848`. Session world-source kind `+0x64`: 0 -> creator `+0x80`, 2 -> `+0x7c`, 5 -> `+0x88`, other known values -> `+0x78`. |

OpenProcess requests only `QUERY_LIMITED_INFORMATION | VM_READ`. No injection,
patch writes, suspension, network hooks or process dumps. Reads happen off the UI
thread. Every handle is closed. Native pointer/list changes discard the sample;
cycles, duplicate IDs, more than 64 nodes, unknown layouts and invalid numeric
values are rejected. The generic Playing status does not depend on this reader.

## Transport and lifecycle

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
The server migration is validated against isolated PostgreSQL/WASM, not production.

# Lair return observer, Kohan II 1.3.72

Local diagnostic requested after a report that wounded fire/storm dragons return
to their lair, the sword bar remains partly full, but defender counts become zero
and subsequent attacks do not release them. No gameplay fix is claimed here.

`PawsLairDiagnostics.exe` starts the **installed** Arcane Wars helper selected
from `.pawpatch/state.json` (all eight color/hostility/desync combinations), or
attaches to an already-running `k2.exe` in that same installation. Default path:
`D:\SteamLibrary\steamapps\common\Kohan II`; override with `--game <path>`.
`--attach` waits for a user-launched game without starting one.

The observer requests only `PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`.
It does not inject code, call game functions, change options, alter kingdom
ownership, modify saves or replace installed executables. Launching the existing
published helper retains that helper's normal behavior. A mismatch of the stock
EXE SHA-256 or three native code signatures rejects observation.

## Reproduction

1. Run the diagnostic EXE and load the affected save / create the affected match.
2. Attack the lair, retreat, let surviving defenders return, then attack again.
3. If convenient, mark the incident with `Баг воспроизвёлся` in the observer.
4. Exit the game. The observer closes its log and makes a ZIP next to the session
   folder under `Kohan II/Logs/PawsLairDiagnostics/`.

Closing only the observer stops observation and archives logs; it never closes
the game. It reads all Denizen components so normal towns/other lairs provide
controls. Observations are **non-atomic**, normally every 500 ms; they do not
capture every engine call. Bounded lists, identities, registry generations and
home back-references reject invalid reads. A snapshot flagged incomplete is not
evidence that a defender really disappeared.

## Native evidence and recorded fields

Verified against the flat 1.3.72 runtime image at base `0x460000`, SHA-256
`b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c`.
Addresses below are **RVAs**:

- `0x21117`: object ID low 16 bits select a pointer at registry `+0x20004`;
  high 16 bits must match the generation at `+4`.
- Actor `+0x88` is the Denizen component; vtable RVA `0x4E0434`, home `+4`.
- `0x20A28C`: returned unit's current/max health ratio becomes stored group HP.
- `0x20A12E`: the native displayed count does not count a wounded home defender
  with a positive resupply rate until its HP reaches the definition maximum.
- `0x2090FA`: the bar uses health ratios and strength weights. Thus an 80% bar
  and zero fully recovered home defenders can coexist in the stock code.
- `0x20AE2A`: resupply depends on definition rate/max HP, delta time, and the
  home owner's `+0x1FC` penalty (factor `1-penalty` when positive).
- `0x20AC04`: only selected not-deployed groups are resupplied per tick.
- Actor data max health `+0x284`, resupply rate `+0x2CC`, strength `+0x1E4`.
- Group list at component `+0x18`, node: ID `+0`, data `+4`, HP `+8`, flags `+C`,
  next `+10`. Intruder IDs at component `+24`, next node `+4`. Deployment list
  `+40`, next node `+4`; organization pointer in deployment record `+28`.

The log records those values, all owning kingdoms and their penalties/relations,
live deployed actors' HP and owner, intruders, component/actor flags, world time,
installed module/EXE identity, and relevant installed TGI definitions.
`fullyRestoredAtHomeCount` is an explicitly derived diagnostic count, not a
direct read of an on-screen widget. Missing observations are called
`NOT_OBSERVED`, not asserted to be destroyed actors.

Neither a kingdom-penalty bug nor a deployment-state bug is established without
the user's reproduction. Do not fix this by rewriting save ownership or
instantly restoring all defender health.

## Validation

`build.ps1 -OutputDirectory <folder>` compiles an x86 WinExe and runs 22 offline
checks: wounded/live/stale-ID separation, sword bar vs full-health count,
bounded/cyclic lists, wrong-home rejection, invalid floats, save-transition
cache invalidation, option selection, and JSONL/ZIP output. No game is started.

`test_native_conditions.py --legacy <verified legacy work directory>` executes
13 probes against the original x86 count/bar/resupply code in Unicorn. Output
map containers and owner virtual lookup are fixtures; arithmetic and readiness
branches are original. It confirms 0/50/80/99.98/100% HP states and resupply
penalties 0/0.5/1. These probes do not reproduce a live dragon fight.

The installed beta.8 helper was also checked with its non-launching `--features`
and `--preflight` paths.

## Observer r2: Steam bootstrap handoff

The first user's runs stopped after 1-2 seconds because the first k2.exe process
exited before verification. The observer mistook this for incompatible memory.
The final Steam-launched process passed all three signatures at its actual image
base `0x00E40000`. r2 re-enumerates until a path-verified process has a window and
matching code; an exited/unready bootstrap is not retained. Three new regression
checks cover process replacement, incompatible-process timeout and cancellation.

A read-only live collector attached to existing PID 9212 on 2026-09-16 without
starting/restarting the game. It detected 97 Denizen components, including three
fire-dragon lairs, in about 45-50 ms per observation. All three lair samples were
complete and initially had five fully restored home defenders. The overall frame
was marked incomplete; do not interpret absent unrelated objects as deaths.
The user subsequently reproduced the fight/return/re-attack sequence below.

## Confirmed live reproduction (2026-09-16)

Read-only session:
`D:\SteamLibrary\steamapps\common\Kohan II\Logs\PawsLairDiagnostics\20260916-163700-26004`
and the adjacent ZIP (2,210,701 bytes). The observer was stopped and archived
without closing the game; the user later exited the game.

Target: actor ID 92, `active_lair_dragon_lair`, position (18, 227), five home
groups with maximum HP [600, 600, 600, 6000, 3600]. Owner resupply penalty was 0.
The target observations were complete, although unrelated world objects made
the global frame incomplete.

At game time 3152.94 all surviving defenders had returned. Stored HP was
[0, 0, 51, 5944, 3560.6]; full-ready count was 0 while the weighted sword bar
was 2060.107 / 2220.628 (92.8%). The first recovering youngling gained 6 HP/s;
the almost-healthy adult and young dragon were not selected for healing.
On re-attack at 3171.44 the values were [0, 0, 159, 5944, 3560.6], with no
deployments. The youngling healed at the native siege rate (1.5 HP/s), while
the two larger dragons remained unchanged. At 3197.31 the lair was down to
1550 HP and still deployed no defenders. The user then reported destruction.

This confirms the full-health deployment gate plus first-wounded resupply
queue interaction. It does **not** establish that changing kingdom ownership
caused the issue, nor that every absent unrelated actor died. A local fix and
its separate manual acceptance boundary are in `../../lair-recovery/README.md`.

# Organization position event recovery — Arcane 0.3.2-beta.2

The provided multiplayer save has company 47618 (`horde_sovereign_nightbringer`)
whose actor remains at (337.16796875, 795.546875) while its organization target
and surviving member move elsewhere. Its own timed-event chain lacks kind 0,
event 1. The normal position setter does not restart this event when the old
target already differs from the actor's position. Initial loss of the event
and the reported hero replacement trigger are not yet reproduced.

## Integration

Opt in using `game/beta7/build.ps1 -CompanyPositionRecovery` with the complete
current Arcane helper options. The public build defaults remain unchanged.
The accepted local test retains its installed package version. Publication
uses Arcane 0.3.2-beta.2, including the existing version/hash lobby checks.
All peers must use matching helpers. No save format or kingdom changes.

Replace the CALL at RVA 0x218666 in the native organization periodic tick.
The original eligibility routine at 0x2148D3 runs exactly once. Its result,
registers and flags reach the original caller unchanged. If native movement
is blocked, no recovery runs. Otherwise, a validated organization with finite,
different actor/target coordinates and no own kind-0/event-1 event schedules
that event using the original 0x2922ED method.

The organization target is not recalculated by the patch. No captain pointer
is consulted, no unit or banner coordinate is directly written, and no order,
formation, combat target, speed, collision rule, strategic goal or RNG call is
changed. The hook's native caller already checks for a leading member, which
need not be a living hero. The event chain uses node+0x10, not the global list.
Malformed owner links and chains longer than 64 entries fail closed.

The final stub is 278 bytes, with six relocation sites. The first allocation
page is RX and the second stays RW. Diagnostic counters at +0x1000 contain
periodic calls, recovery calls and last recovered actor ID. They have no effect
on decisions. The original ECX is stored before the native call; after pushfd,
pushad, 528-byte FXSAVE storage and its pointer, saved AL is at ESP+560.

## Verification and limits

- 138 managed transaction checks: mismatched engine, partial writes, rollback,
  persistent rollback failure and three relocation layouts.
- 78 native emulation cases / 156 calls: healthy/missing/duplicate events,
  native movement blocked, absent hero, unrelated hero position, invalid
  coordinates, invalid list owner, cyclic list and register/FPU preservation.
  The original eligibility function and own-list insertion execute verbatim;
  virtual state getters and the allocator/world scheduler are modeled.
- The full helper build also runs its existing city, militia, save-owner,
  camera, lair and transfer regressions.
- Runtime evidence belongs to the workspace `outputs/company-position-test-r2`
  directory. Internet-lobby launch is a single local client test, not proof of
  synchronization between two computers. Broad battle behavior, hero replacement
  and the reported bot inactivity at match start still need separate acceptance.

The accepted save recovered company 47618 once; by game time 1:00:04.625 its
actor reached the native organization target. At 1:03:57.0625 it still matched
that target and had replenished from one member to nine. Recovery count remained
one. The original save was unchanged. Release assembly checks compare the
company, lair and camera payloads against this accepted local helper.

The first local iteration also rearmed events in native-blocked states. It was
replaced before delivery by the version which preserves native eligibility.

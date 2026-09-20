# Exhaustion recovery — local test r1

An observed pioneer company spent more than 33 game minutes in Exhausted with
16/16 morale and a recovery breakpoint of 20 on desert deadland. Native recovery
requires current morale strictly above that breakpoint, which is unreachable.

The test replaces only the CALL at RVA `0x274A1A` inside
`CAIStateExhausted::Update`. The original decision at `0x2147EC` still executes
once. Native result 2 remains unchanged. Results 0 or 1 may become 2 only when
current, maximum and breakpoint are finite, maximum is positive and no greater
than the breakpoint, and current morale has reached that maximum. The caller
then performs its own native state transition.

No morale, health, orders, positions or save records are written by the stub.
Other callers of the shared decision, including routing/combat logic, retain the
original function. All registers and original flags are restored except for the
intentional return value. Code is RX; two diagnostic counters use a separate RW
page. Code signatures, write verification and rollback follow existing helpers.

Build the current Arcane helpers with the existing full-feature switches plus
`-ExhaustionRecovery`. This option also requires `-CompanyPositionRecovery`.
It is opt-in and does not change published package versions or release defaults.

Validation: 126 transaction checks and 90 native emulation cases across three
image/cave address layouts. The tests execute the original decision bytes and
the actual caller's exit branch, including both CAI virtual-query responses,
partial recovery, the ordinary 20.125/48 exit, nonfinite values, register/FPU
preservation and absence of game-object writes. The external CAI query is mocked.

Local live test on 2026-09-19: the installed helper starts, guards pass and
`Случайно.RSG` loads through an Internet lobby. Company 15688 begins Exhausted
at 40:23.5, but reload has already produced 36/36 morale instead of the original
16/16. It exits normally at 40:23.625, moves at 40:25.5625, then enters Construct
and Repair. The new recovery counter stays zero: this is startup/save-load and
ordinary-exit acceptance, **not a live reproduction of the lowered-cap fix**.
That specific 16/16 case is currently verified by native emulation only.

Evidence and rollback are in `outputs/exhaustion-test-r1` in the outer workspace.
Only the installed `k2_paws_lobby_colors_mp_sync_1372.exe` was replaced for this
test. The engine EXE, package data and the original save remain unchanged.

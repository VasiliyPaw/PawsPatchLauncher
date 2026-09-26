# City tribute target correction

## Live evidence

Read-only inspection of the existing beta.6 match on 2026-09-26, process
14488. At game time 1136.625, Shahzadeh (kingdom 32, `paws_light_pink`)
owned 11 settlements, including one sovereign. Allied Caleb (kingdom 33,
`paws_dark_red`) owned two. Both share the same native team pointer.
All eleven donor centers were alive; none was besieged in this sample.
The city-tribute cache subsequently showed checks at game times 1392.625
and 1396.8125, with no pending city command. The policy was running.

The existing code submitted the settlement-container actor ID to
`TeamCommand::SetActor` and `Validate`. These container actors lack the
native selectable-target flag `0x4000`. The native target validator
(RVA `0x6EC8F`, rejection at `0x6ECC0`) therefore returns code 1 before
checking tribute capacity or recipient rules.

An external Unicorn emulator executed the installed native constructor,
target normalization and validation against copied VM_READ process pages.
Only private emulator allocation/free and initialized TLS bookkeeping were
provided by the harness; no native command was executed in the live game.
All 11 container targets were rejected. Using the corresponding central
building IDs admitted all 10 ordinary cities; the sovereign stayed rejected.
This confirms an incorrect command target, not a lack of cities or a race
restriction in this match.

## Change and validation

`city_sharing.c` now supplies the current central building ID both while
choosing a city and in the final command validation. Pending-command tracking
continues to use the stable settlement ID, so upgrading a center does not
invalidate tracking of the settlement. Native ownership, capacity, diplomacy
and command transport remain in charge of the actual transfer.

The regression fixture previously represented a settlement and its center
as the same actor. They now have distinct registered IDs and target flags.
The updated test rejects the released beta.6 payload in the ordinary `give`
case, and passes the corrected compiled payload: 603 checks at three image
bases. Evidence and emulator harnesses are saved under
`outputs/live-peers-20260926-beta6/`; the candidate native payload is under
`outputs/city-sharing-20260926/ai-native/` in the workspace root.

This correction is included in beta.7. The ongoing match was not modified.
Successful command validation in the emulator does not replace live acceptance
of a completed transfer.

# First-tick desync: PC and VirtualBox, 25 September 2026

## Preserved evidence

Both players ran Arcane Wars beta.5. The user closed both games after evidence
capture; further investigation used files only. No guest password or Windows
security setting was changed. An 8.7 GB VirtualBox ELF core preserves guest RAM.
Guest k2.exe PID 2984 and its WOW64 memory were recovered through its EPROCESS
directory table base and x64 page tables. The host process was PID 21536.
Both peers' 157262-byte r36 AI payloads were verified against the published
binary after ASLR relocation; all 59 guest hook targets also match. This rules
out mismatched AI helper bytes for this capture, not all game-data differences.

Local evidence directory: `outputs/live-peers-20260925-beta5` in the parent
workspace. `host/synclog_Paw1.txt` is the first native host history; guest native
history fragments are in `guest-cached-records.json`. `guest-process.json` and
`host/live.json` preserve first-error metadata.

Both first-error records report index **305126** at game time **1.1875**. Both
diagnostic wrappers captured/returned once, retaining the first error despite
subsequent failures. Host history ends at 300554; guest history reaches 305719.
Guest cached fragments have page-boundary gaps, so absent guest lines are not
treated as mismatches; one false line joined across unrelated physical pages
at index 283413 was excluded. Of the comparable unique records, 295936 have equal
rolling checksums through index **300544**. Host/client serialization label
differences (`o.GetBitSize` / `i.GetBitSize`) are expected.

The first unequal record at 300545 is a decree serialization boundary on the
host, versus the next tick event and world-update records on the client. The
host log says `ValidateChecksum() - getting a value beyond what we've currently
seen`. Host simulation still advances: these missing entries alone are not
evidence that its world stopped or that an individual bot made the first wrong
decision.

## Reproduced cause

The added expansion pulse called native SelectGoals from tactical player update
`64F0D9` (addresses here use the recorded image base 460000). SelectGoals yields
through `64156B`, the strategic yield. That function clears only strategic flag
`sai+68`, switches to the main fiber and sets it back on return. Tactical flag
`sai+69` remains set while the world runs. The native synchronizer (`5CDFF2`
and its other typed variants) skips records whenever either flag is nonzero.
On resume, the strategic flag is also set although the current fiber is still
tactical. A subsequent normal tactical yield clears only `sai+69`.

This is a concrete defect in the patch's scheduling, and reproduces the missing
world-record pattern in this match. The host AI log starts with an extra
SelectGoals pass before native dynamic map analysis; it reports an overrun of
1797399 ms against the stale strategic deadline. Live host flags at the instant
of its first failure were not captured, so the exact runtime call stack is not
claimed as observed. Initial checksum agreement is not proof that no other
later simulation defect exists.

## Local correction and validation boundary

Revision 37 runs the extra work after a completed iteration of the strategic
scheduler, with explicit fiber and per-player exclusion guards. It retains
native yields and network commands. The common checksum implementation is
unchanged. A regression executes original yield/synchronizer/scheduler machine
code with controlled OS/engine service stubs at three ASLR bases. The shipped
r36 payload fails its invalid-context regression; r37 must pass the same test.

The related call-site review found both extra native selection and execution
in `expansion_pulse.c`; both now run inside this strategic reservation. There
is no other direct extra SelectGoals/ExecuteGoals entry in the AI policy C
sources. Shared routing and common command admission retain the beta.4 peer
parity correction and its differential regression. This is a bounded review,
not a claim that all possible desync causes have been excluded.

A new played two-peer match is not part of this offline verification. The user
explicitly requested no game launch. Build, isolated installation and publication
results are recorded separately in `verification-patch-0.4.0-beta.6.md`.
The existing match is already divergent and cannot certify the correction.
Run a fresh host/client match with identical corrected helpers and preserve
both first-error journals if it fails again.

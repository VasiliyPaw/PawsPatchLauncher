# Shared crash guards, local revision 1

Opt-in `-EngineCrashFixes` for the full Arcane Wars helper build. This does not
publish a release or alter game assets. For a helper launched outside the game
directory, also use the existing `-LairWoundedTest` local-data mode: it resolves
the presentation, language and palette from the verified installation.

## Evidence and scope

- Friend log 24 on 2026-09-20: native animation update at RVA `31EAB5` calls
  a data address, RVA `57CA1C`, through the target's type-query slot. This matches
  the earlier dangling animation target signature. The current minidump does
  not contain enough heap data to name its animation asset.
- The earlier full diagnostic identified one destroyed target in a sequence
  of 27 controllers (zero references and a destructed base-class vtable).
- Local logs 354 and 355: RVA `14C04A` reads `[eax+28]` when the player pointer
  at administration-entry `+0C` is null. Disconnect/reset precedes the first
  load failure. A later load succeeded; these dumps do not prove save damage.

## Animation guard

At `31EAA6`, preserve the original target load, all integer registers and flags.
Check the target reference count, native read-only vtable range and executable
type-query range before the original virtual call. A bad target skips only this
controller's current update, using the stock next-controller branch at `31EB1A`.
Valid and null targets retain the original update semantics. No reference counts,
target pointers, ownership, assets or simulation objects are changed.

An OS-registered vectored handler handles read access violations only inside the
new probe. It returns to the probe's own failure exit, never into a faulting game
routine. Writes, execute violations and faults at game addresses propagate.
No dynamic SEH-chain entry or Windows mitigation changes are used. The handler
remains until process exit, like the patch code. Failed registration preserves
stock behavior and records a failure once; there is no per-controller retry.

This addresses the observed invalid animation-target class, not every possible
animation crash, nor the underlying lifetime bug or a readable recycled object.
The guard does not call `VirtualQuery` or allocate per frame. The one-time
handler registration uses the verified corresponding Windows DLL entry point.

## Network guard

At `14C047`, omit an entry with a null administration/player pointer from the
existing active-client count. Keep the original result for all valid entries
and continue through the list. Do not change membership, packets, loading state,
kingdom ownership, saves, simulation or the optional desync bypass.

## Installation and diagnostics

Both hooks have exact instruction/context checks before mutation. The code page
is RX and the counter page RW. Partial writes roll back; uncertain rollback retains
the allocation. Installation applies only to the newly launched verified process.

`ENGINE_CRASH_FIXES` and changed `ENGINE_CRASH_COUNTERS` are appended to the
existing helper status log, already covered by launcher diagnostics. Counters
distinguish dead targets, invalid vtables, invalid type-function addresses,
unreadable targets and missing network clients. These are skipped operations,
not a proven count of crashes prevented. No automatic upload is added.

## Validation

- `test_native.py`: 126 instruction-level cases across three ASLR bases. Uses
  stock loop instructions with controlled objects and mocked type/update callees;
  compares valid behavior, one bad controller among 27, and client counts 0–7.
- `TransactionTests.cs`: 217 checks including the real Windows API resolver,
  relocation, identity rejection, partial writes, rollback and uncertain rollback.
- `ProbeWindowsTests.cs`: 52 checks in a disposable x86 Windows process. Executes
  the generated probe and real exception dispatcher with inaccessible target and
  vtable pages, page-boundary reads, unaffected valid probes, unrelated-exception
  rejection and simulated registration failure. Does not start the game.
- The full helper build also runs the existing feature regression suites.

The eight local helper variants require matching `0.4.0-beta.1` data. Their actual
EXE hash participates in lobby compatibility: all peers must use the same test
helper variant and settings. Live game validation remains a separate manual step.

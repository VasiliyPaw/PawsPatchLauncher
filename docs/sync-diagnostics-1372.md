# First-error diagnostics with continued play (1.3.72)

## Evidence and scope

The paired beta.4 archives from 2026-09-25 use the same runtime hashes and report
the first error at sync index 304230. The host also reports an index beyond the
local history. These facts do not identify the original simulation divergence.
By the later live capture, the network ring had advanced past the first error.

The old optional bypass replaced `SyncFailure` with a counter and `ret 4`, so it
also skipped the engine's detailed file writer. Closing the game cannot recover
overwritten first-error records. This change is diagnostic, not resynchronization
or a claim that the underlying multiplayer defect is fixed.

## Native implementation

Verified mapped engine image SHA-256:
`B865D8206990C4F055C51DE857F0B09B88AB5EE3B6AE74EE5232134001AA591C`.
All offsets below are RVAs, relative to the actual ASLR base.

- `0x14A5F2`: `SyncFailure`, original SEH prefix guarded. The original routine
  logs the failure and calls `0x14D1F4`, which chooses a numbered synclog filename
  and calls the synchronizer dump routine at `0x16E375`. Its existing fallback
  path handles a failed initial write. The function returns without halting the
  session; the separate local-OOS marker at `0x14A4FE` remains bypassed.
- `0x16DFCA`: native synchronizer baseline reset. The observer only rearms
  capture when ECX equals the network synchronizer at `[image + 0x5F3FF0]`.
  Replay/film synchronizer resets do not rearm network capture. Original reset
  instructions, parameters and ring operations remain intact.
- The first failure atomically claims the current diagnostic epoch before
  calling the original writer. Repeated/nested failures update the old counter
  and last-index ABI without writing another full file. The reset observer
  permits a new capture even if a later match/load reuses the same world address.
- Private metadata records the first index, ring start/end, rolling checksum and
  game time. Missing metadata is zeroed rather than inherited from the previous
  match. Native file output preserves record labels, values and checksums, plus
  host/client and floating-point environment information.
- The wrapper preserves integer registers, flags and x87/SSE state around disk
  output. It does not change engine checksums, RNG, orders, world state or saves.
  Baseline changes are observed, never initiated by this patch.
- A returned writer is recorded as a return, not proof of disk success. Native
  logs contain the filename or IO/fallback errors. A failed write is not retried
  on every later mismatch. The first native dump is synchronous; its cost depends
  on the available history and disk, as with the engine's normal desync handling.

The change applies to Arcane Wars beta helpers with `SYNC_CONTINUE`; official
desync handling is unchanged. Vanilla/Immortals packages are outside this release.
Launcher 0.8.9 already collects `synclog*.txt` under the game's Documents tree;
no launcher upgrade is required. Each machine must supply its own diagnostic
archive after the next error. Continued play still leaves the worlds divergent.

## Automated coverage

The canonical helper build includes the actual emitted wrappers in Unicorn at
three relocated bases. 21,312 checks cover first/repeated failures, original
this/argument and SEH relocation, all stack alignments, integer registers/flags,
floating-point values/control/status/tags, MXCSR and XMM, write boundaries, an
index beyond the local ring, metadata retention/nulls, epoch/counter rollover,
new-match/save-load rearming and exclusion of film resets.

The original native reset instructions run with explicitly stubbed ring-container
services. Native disk IO is also explicitly stubbed; these are ABI and state tests,
not a two-machine desync reproduction. Unicorn does not restore the last x87
instruction address on FXRSTOR; the test excludes only that four-byte metadata
field from its saved-state comparison.

A separate isolated 32-bit hardware probe executes the same emitted wrapper on
the real CPU. It verifies both first and repeat calls and compares the complete
512-byte FXSAVE state, including the instruction address omitted by Unicorn.
Its native IO body is also a deliberate surrogate; no game process is involved.

Launcher tests verify a fresh network synclog among older film logs. The complete
ZIP test checks inclusion, unchanged bytes, hashes and source preservation.
Evidence is retained in `outputs/release-20260925-beta5` in the release workspace.

# Paw's Patch 0.4.0-beta.6 verification

Arcane Wars beta only; native AI policy revision 37.
Source: `786080f1aeedece0277c01808a7a31c2c137314f`.
Release tag: `patch-0.4.0-beta.6`.

## Reproduction and correction

The added expansion pass previously ran in the tactical fiber but could invoke
the strategic yield. Original 1372 x86 code reproduces the resulting suppression
of world checksum records and leaked AI-active flag. The corrected pass runs
between completed strategic scheduler iterations and reserves the current player
against overlapping tactical work. The common checksum implementation is unchanged.

See `desync-live-peers-20260925.md` for the paired trace evidence and its limits.

## Automated verification

- Fiber/synchronizer regression: 1,160 checks at three ASLR bases, including
  original native yields, checksum guard, scheduler, cdecl arguments and stack,
  invalid contexts, suspension, and player ownership restoration. The old r36
  payload fails the context regression. OS and engine services are explicit stubs.
- Launcher Release suite: 27,485 checks passed.
- All 29 native AI regression suites passed against the same r37 payload;
  all eight helpers were built and completed their offline self-tests.
- Peer parity: 189 differential checks plus 2,358 route ABI checks passed.
- First-desync capture: 21,312 checks at three ASLR bases. The separate real
  x86 CPU probe passed first/repeated calls with the complete 512-byte floating
  point state preserved. Native file IO is explicitly stubbed in these probes.
- Signed package installation matrix: 73,728 selections, 15,024 unique plans,
  69 verified archives, eight helpers, 30 preflights and 45 transitions passed.
  Tests used a separate fixture and preserved its save sentinel and stock EXE;
  the user's game directory was read-only. No game was launched.
- All four published package downloads passed anonymous size and SHA-256
  verification against the tested signed catalog and GitHub asset digests.

Tested native payload SHA-256:
`8CC30B81243C12E935C513F68AFABD2A2058F6F8421C70E58764946AEC306216`.

Tested multiplayer colors/continue helper SHA-256:
`66114012CE8200957A419E0DF14F9FD1EA36B9A73ACF743BCC8C4A53B7A5A82A`.

The original build stopped at an old builder fixture that lacked strategic-fiber
state. The fixture and its cdecl caller were updated; affected suites were rerun.
The continuation rebuild verifies byte identity with the already-tested payload.
Both logs and the exact continuation script are retained rather than presenting
the interrupted run as a single uninterrupted success.

## Acceptance boundary

The user explicitly requested no game launch. No new game process, live startup
check, or multiplayer match was run for beta.6. The paired match used for diagnosis
was already divergent and cannot validate the fix. A fresh match with the same
updated version on every peer remains pending user acceptance.

Only the Arcane Wars beta runtime helpers and patch version metadata change.
Stable, other mods, gameplay data, and launcher 0.8.9 remain unchanged.

Local evidence: `outputs/live-peers-20260925-beta5` and
`outputs/release-20260925-beta6` in the parent workspace.

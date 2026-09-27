# Paw's Patch 0.4.0-beta.9 verification

Arcane Wars beta, AI revision 39. Tag: `patch-0.4.0-beta.9`.
The launcher, stable channel and other mods retain their published versions.

## Fix

The original strategic queue shifted all later deadlines after every insertion.
With four active players on longer intervals and six empty players on shorter
intervals, repeated insertion could postpone active players indefinitely.
Tactical updates continued, so existing orders could finish while recruitment
and new strategic orders stopped.

The patch retains native allocation, sorted insertion, duplicate handling,
player exclusion, initial staggering and coroutine yields. It skips only the
post-insertion deadline-shifting tail and enforces the configured global gap at
dispatch through the temporary peek result. Stored deadlines are left intact.
The pacing clock uses game time and resets on player reconstruction, world or
SAI replacement, and time rollback. Tactical scheduling and disabled bot
improvements retain native behavior.

Expansion reevaluation now skips tombstones and stale state-bucket entries.
Foreign ownership and invalid traversal still abort the pass. Goals are not
called through a mismatched state bucket. Native installation guards include
whole relocation operands at the new hook sites.

## Live saved-match check

The user loaded the same save with the local fix and confirmed it worked.
Read-only verification of that running process matched all 63 hooks and the
entire rebased native payload to the tested r39 build. The game was not restarted,
controlled or modified during this check.

Across game times 12607.75 to 12667.375:

| Bot | Strategic updates | Tactical updates | Changed company assignments | New company IDs | Unit capacity at end |
| --- | --- | --- | --- | --- | --- |
| Shahzadeh | 24 to 26 | 276 to 299 | 9 | 2 | 19/20 |
| Nicomedes | 24 to 27 | 276 to 299 | 12 | 1 | 20/20 |
| Zahra | 25 to 27 | 276 to 299 | 5 | 4 | 20/20 |
| Ravyn | 25 to 27 | 276 to 300 | 12 | 0 | 20/20 |

All 75 surviving companies present in both snapshots changed position by more
than two world units. New assignments and seven successful recruitment events
in this interval distinguish continuing AI decisions from merely finishing
old orders. The copied session log contains 81 successful recruitment events.

This observation establishes that the reported global AI stall is resolved in
this save. It does not independently demonstrate city transfer or army
replacement, which did not occur in the observation window. The built-in full
snapshot exceeded its report-size limit; independent read-only memory captures
succeeded. These are asynchronous snapshots, not synchronized peer checks.

## Automated evidence

- All 30 native AI regression suites passed against the new payload.
- Strategic queue: 127,643 checks at three relocation bases, using the original
  native queue, ScheduleThink and strategic scheduler. In 600 simulated seconds,
  the four active players received zero updates with original deadline shifting
  and 21 each with the fix. Both runs dispatched 300 total updates.
- Expansion reevaluation: 6,867 checks, including stale entries and foreign
  ownership. Native transaction/rollback/relocation checks: 66,568.
- Synchronization regression: 1,160 checks retain original yields, player
  exclusion and checksum behavior. Peer parity: 189 differential checks and
  2,358 route ABI checks. These are emulated native tests, not a new two-PC match.
- Launcher Release suite: 27,485 checks passed.
- All eight production helpers rebuilt with the tested r39 payload; 40 offline
  helper self-tests passed. The local-test launch entry point is excluded.
- Signed package validation: 174 checks across all eight helpers and four
  updated archives, including the retained lobby/UI fixes and unchanged button
  artwork, audio, geometry and recent player-facing notes.
- Unchanged non-AI dependencies reuse beta.8 evidence with source hashes checked.
- Isolated installation matrix: 73,728 selections, 15,024 distinct plans,
  69 verified archives, eight helpers, 18 frame checks, 30 runtime preflights
  and all 45 install/component/language/rollback transitions passed. The save
  sentinel and stock executable survived uninstall unchanged; the source game
  was read only.

AI payload SHA-256:
`07BE67290F55108D6DA5D92A88DC4694ACC5BFFCCF53767F0B16752B5CC37751`.

Evidence is in the parent workspace at
`outputs/ai-save-scheduler-r39-20260927` and
`outputs/release-20260927-beta9`. The release stage contains live-read reports,
source hashes, native regression reports, helper hashes, package scope and
installation/publication verification. Release preparation never installs to
the user's game or invokes the normal game entry point.

# Paw's Patch 0.4.0-beta.7 verification

Arcane Wars beta only; native AI policy revision 38.
Release tag: `patch-0.4.0-beta.7`.

## Changes

City tribute now targets the settlement's current central building, as the
native GIVE_ACTOR command requires. The prior settlement-container target was
rejected before the transfer could be sent. Native ownership and network
transport remain authoritative. See `city-sharing-live-20260926.md` for the
read-only match evidence and the original engine validator reproduction.

The gold-button tooltip contains only `Paw's Patch`. Its existing native font
measurement and padding determine the window size; no empty body paragraph is
inserted. The button remains 100 by 100 pixels at 2560 by 1440, in the same
position, with unchanged artwork and overlapping audio.

## Automated verification

- Launcher Release suite: 27,485 checks passed.
- All 29 native AI regression suites passed against the same r38 payload.
  City tribute: 603 checks at three ASLR bases, with distinct settlement and
  central-building IDs. The old beta.6 payload fails the updated target case.
  Command dispatch in this regression is stubbed; the independent reproduction
  executes the original native target validator against copied process data.
- Fiber/synchronizer: 1,160 checks; peer parity: 189 differential checks plus
  2,358 route ABI checks. The previous synchronization fixes remain enabled.
- Gold-button native regression: 481 checks; tooltip ABI and original empty-body
  formatter branch: 127 checks; original native rectangle layout: 63 checks at
  three ASLR bases and three font metrics. Font measurement is stubbed in the
  rectangle test; this is not a screenshot or live rendering test.
- Presentation-hook installation: 166 checks in an isolated process.
- Signed package inspection: 85 checks, 40 string tables, all six game languages.
  All eight helpers embed the tested UI payload and the exact current English
  and Russian localization hashes. Unrelated packages retain their prior hashes.
- Final installation matrix: 73,728 selections, 15,024 unique plans, 69 verified
  archives, eight helpers, 30 preflights, 45 transitions and 18 frame checks
  passed. The isolated fixture preserved its save sentinel and stock EXE;
  the source game directory was read-only and no game was launched.

The first installation attempt caught the old strict localization hash guards
after removal of the translated tooltip body. Both guards were updated in all
six helper sources, and all eight helper variants were rebuilt and passed their
40 offline self-tests. The native payload did not change during this rebuild;
the complete native-suite evidence therefore still describes the shipped code.
The failed installation log and exact guard-only rebuild script are retained.

Tested AI payload SHA-256:
`B357D48C5B030C26918E2D9DA536E4292055463693373BBF5AAF47C0E6CAEBEE`.

Tested presentation payload SHA-256:
`EC1747463734DED216F24E80C1FDE523653E0E9693B83E4BC6C9B03315B8E590`.

## Acceptance boundary

The ongoing match was not modified, closed or restarted. No new game was
launched. A completed city transfer and the tooltip's appearance in a fresh
beta.7 match still require live acceptance. Offline native and installation
checks do not substitute for that acceptance.

Only Arcane Wars beta packages and their signed beta catalog change. Stable,
other mods and launcher 0.8.9 remain unchanged. All multiplayer participants
must use the same patch version.

Local evidence: `outputs/live-peers-20260926-beta6` and
`outputs/release-20260926-beta7` in the parent workspace.

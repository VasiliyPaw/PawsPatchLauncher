# Lobby colors after leaving a match and creating a new room

Status: fixed locally; not installed into the user's game or published.
Baseline checkout was d4dae62a2f72c78f0d9c45abde7b6659d12ba4a1. Unrelated
staged/unstaged/untracked work was preserved. Artifacts and input snapshots:
`F:/PawsLobbyColorsQA-20261109`.

## Cause and behavior

Room-local colors were indexed by the replicated native `player+0x20` ID.
`state_init` invalidated them only when its initialization flag or Session
address changed. Stock `Session::Reset` reuses the object, zeros the ID counter
at `session+0xF4`, and generates a new GUID at `session+0x170`. A different
arrival order in the next room can give the same IDs to different people.

Primary evidence is the verified mapped 1.3.72 image, stock reset at model VA
`0x5c208b..0x5c21f3` (361 bytes). The independent pseudocode export is
`work/kohan-ii-decompilation/exports/code/rva_16/0056208b.c` relative to the
project root; it uses image base 0x400000 instead of the mapped 0x460000.
Native reset calls CoCreateGuid and formats its eleven components as unpadded
hexadecimal, at most 32 WCHARs.

The lifetime key now includes a bounded *copy* of the GUID. Checking a string
pointer alone is insufficient because the allocation may be reused too. A new
lifetime clears choices, seat owners and participant preferences. Returning
to the original lobby after a match, changing seat, or spectating in that same
room retains the existing participant preference. New rooms start at Random;
this does not add persistent Steam-account preferences.

No new native patch sites or wire/save fields were added. The two existing
network orders, palette IDs/RGB, retired saved colors and save read-only rules
are unchanged. The payload stays 270336 bytes; its relocation table adds three
references to the reserved GUID buffer. Loader diagnostic revision is r23.

## Validation

- Rebuilt the released payload before editing: byte-identical to the embedded
  production payload, SHA-256
  `92AE781BF115EA61683D2F0D45FDCB7B25CBB61187A45535E0D18A99C9CD778F`.
- `test_session_lifetime.py`: old payload reproduces the bug (72 checks);
  fixed payload passes 92 checks. Two address layouts, reused Session and
  string addresses, final-character-only GUID change, three participants in
  changed order, new-room host/client snapshots and late join. These are
  native x86 emulation checks, not three live network clients.
- `test_native_session_reset.py`: executes the original stock reset procedure,
  including its real ID-counter writes and GUID formatting argument setup.
  The released payload inherits `[3,9]`; the fix returns `[39,39]` (Random).
  External GUID/timer/formatter and unrelated cleanup calls are stubbed.
- Existing participant/native seat-setter/linked-list, transport, saved-color
  and allocation suite: 37,753 assertions passed at two address layouts.
- Existing picker rectangle/ABI suite: 96 assertions passed.
- All eight current Arcane helper variants built with unchanged feature
  dictionaries and passed their quiet-startup, common UI, lobby payload,
  assistant and fast-transfer self-tests. Final builds are in `final-helpers`.
  Their patch identity remains 0.5.1-beta.1 for local comparison only; no feed
  points to these binaries. Only color resources and the loader diagnostic
  string differ from the accepted helper inputs.
- Live isolated game: native UI selected red, match entered state 2 with a
  world, RequestMainMenu/ScoringExit returned to the same lobby, red remained
  selected, and the Session/GUID were unchanged. The final r23 helper was
  exercised in `normal-menu-live`; screenshots and read-only snapshots are
  retained. No modifications of simulation/session memory were used.

Live acceptance limit: a complete same-process transition into a newly created
room was **not** accepted. The isolated game exited on native StagingExit,
including a retry without the startup +Exec argument. The logs were closed as
`log-0-ok.log`, with no assertion/desync found; these runner failures must not
be counted as a successful new-room test or as proof of a game crash. The
new-room fix is validated by the actual stock reset plus payload emulation.
A multiplayer Internet retest with human clients remains unverified.

All owned test games were closed. Installed k2.exe stayed at SHA-256
`1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`;
original Случайно/Случайно2 saves retain the previously recorded hashes.

## Reproduction

Use `game/lobby-colors/build_native.py --legacy <verified lobby_colors_1372>
--out <unused candidate>`. Run `test_session_lifetime.py` and
`test_native_session_reset.py` with the same `--legacy`, `--candidate` and
`--expect-fixed 1`; use the baseline folder and `--expect-fixed 0` to check
the original failure. Run the existing participant and popup suites too.
`build_lifetime_candidate.py --helpers <accepted helper directory> --native
<candidate> --loader game/beta7/LobbyColorsNative.cs --out <unused output>`
checks all accepted input hashes, freezes inputs, rebuilds all variants, checks
features and self-tests. It performs no installation or publication.

Accepted fixed payload SHA-256:
`74A1978F800CC86AA429F55CAEA582C1EF6143560EB25B71701BACA0FEBC2C32`.
Fixups SHA-256:
`3799FB880302F602AB726783F6B5BC4D1224618B6DC10CE11CA83B14367C5190`.

Player-facing changelog draft:
- Исправлено перепутывание цветов игроков в новом лобби после матча.

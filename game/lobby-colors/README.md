# Arcane Wars player palette

## 0.3.1-beta.2: 39 selectable colors

The Arcane beta palette removes original 48-color table entries 6, 18, 20,
22, 24, 29, 30, 35 and 37. Remaining IDs, RGB bytes and ordering are unchanged.
`palette-48.ini` is the immutable comparison fixture, not an installable palette.

`retired-colors.json` retains those nine shades and the earlier Light Red as
save-only descriptors. They are not added to the native stock color database,
selectable pointer array or random allocation. Saved color IDs still resolve to
the original RGB. Each retired descriptor has a reserved tagged network ID;
Light Red retains `0x5044fffe`. A loaded save keeps its kingdom colors.

The payload keeps the accepted size and hook addresses. New descriptors and
localized name pointers use the previously reserved region before `0x3e000`.
The compiled loader supplies all ten localized names, including old saves.
Existing peer compatibility checks require the matching patch version/palette.

Build and validation commands use the verified `lobby_colors_1372` legacy input:

- `build_native.py --legacy <directory> --out <candidate>`
- `test_participant_colors.py --legacy <directory> --candidate <candidate>`
- `test_popup_width.py --legacy <directory> --candidate <candidate>`
- `PalettePayloadTests.cs`: compiled loader, selectable and retired names,
  RGB/ID/order checks at two address layouts in all six text languages.
- Launcher `--verify-palette39`: isolated 48-to-39 update, eight option variants,
  explicit preflight, rollback and uninstall; source game and save sentinel stay intact.

The release changes only the Arcane beta package feed. Launcher 0.8.4 and
Vanilla/Immortals game packages remain unchanged. The current launcher has one
feed-level count for its short color caption; per-mod help retains each mod's
own palette description (39 for Arcane beta, 48 for the pure betas).

## Historical compact-picker acceptance

# Local Arcane Wars beta.8 color review

This is a local test, not a published release. The launcher remains 0.8.2;
the full Arcane Wars helper version is `0.3.0-beta.8-test.1`.

`build_native.py` incorporates the accepted r20 generator and adds:

- One-row staging entries and a 20-unit arrow beside the native color badge.
  The native dropdown layout normally overwrites the list width with the arrow
  width. A guarded SetRect call changes only registered Paw lists to 200 units.
- A bounded preference table keyed by replicated native `player+0x20` IDs.
  The native session assigns these IDs from `session+0xF4`; they survive seat
  changes, spectating, and object reconstruction. They are not nicknames.
  A fresh connection has a new ID and starts at Random; this is not a persistent
  Steam-account color preference across disconnects or new lobbies.
- A hidden descriptor for `paws_light_red`, preserving old save colors and
  multiplayer save transfer without including it in the 48-color picker or RNG.

The existing host permission checks, native request/decree transport, save
read-only behavior, random allocation, stock color database, city assistant,
graphics fixes, and fast save transfer remain in the full eight helper variants.

## Build inputs

Use `--legacy` to point to the verified `lobby_colors_1372` research directory.
The generator verifies the mapped game input against SHA-256
`B865D8206990C4F055C51DE857F0B09B88AB5EE3B6AE74EE5232134001AA591C`.
That directory also supplies the original UI and assembler/emulator dependencies.
Run `build_native.py --legacy <directory> --out <candidate>`, copy `payload.bin`
and `fixups.bin` into the corresponding beta7 resource files, then build all eight
helpers with `game/beta7/build.ps1 -CityAssistant -LobbyCompatibility` and the
verified native compiler. No game is launched by these build commands.

`tools/PrepareColors48Test.py` repacks only core, common UI, and player colors
from the released 0.8.1 package assets. It writes a separately signed local feed
using the supplied local review key and leaves public feeds unchanged.
`compact_menu.py` preserves the existing localized menu outside the two player
row templates. `--stage-colors48-review` in the launcher test runner installs
the three verified local packages through the normal installer, keeps the
applied configuration, refuses a running game, and verifies installed files.

## Validation on 2026-09-15

Final native payload SHA-256:
`BE05D24C1C7C52EBBFB832A80E0968369F6ED29C0E0F9FE26976CF98C191AB7B`.

- Participant ownership: 37,023 assertions, actual x86 at two ASLR layouts,
  all 48 colors and Random, host/client, native linked-list and seat setter.
- Popup scope and ABI: 96 assertions, including first/last record and unrelated
  stock dropdowns; original registers, flags, stack and other rectangle fields.
- Lobby compatibility identity: 98 assertions including EXE-only differences.
- Full helper build and its city/transfer/parser tests passed.
- Launcher core suite: 26,435 assertions; palette labels: 49 checks.
- Live main Steam game: online list and lobby creation, existing name and
  16-player creation limit untouched, compact picker, red selection, spectating,
  return to another seat, newcomer bot on the old seat, player/bot swap, and
  successful match load with the chosen red color. Clean exit (`log-281-ok.log`).
- Live launcher: 0.8.2, main Steam game path, beta.8-test.1 installed version,
  local changelog and 48-color component description confirmed.

Live network acceptance used one human Steam client plus a bot; a second remote
human connection was not exercised. Multiplayer peer behavior was emulated.
The initial UI candidate failed template inheritance at startup; the delivered
candidate retains the inherited view type and passed the subsequent launches.

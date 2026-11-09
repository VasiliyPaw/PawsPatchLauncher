# Three-beta lobby color hotfix — 2026-11-09

User authorized publication of the local color fix, then explicitly added
Vanilla and Immortals beta. Accepted candidate versions:

- Arcane Wars: 0.5.1-beta.2 (eight existing helper variants).
- Vanilla / Immortals: 0.5.0-beta.3 (four shared Pure helper variants,
  runtime identity 1.3.72-pure.19-beta.3).

The public baseline was main d4dae62a2f72c78f0d9c45abde7b6659d12ba4a1.
All six signed feeds, history and beta guide were fetched at that immutable
commit and compared with the local files before preparing candidates.
Other chat confirmed there was no competing publication/feed operation.
Its bridge work and GPU/game processes were left alone.

## Scope

The native fix and its limits are described in
[verification-lobby-color-lifetime-20261109.md](verification-lobby-color-lifetime-20261109.md).
The native Session reset GUID now scopes participant ID ownership. New rooms
start at Random rather than inheriting another player's color. Existing-room
preferences remain attached to the same native participant.

Helpers were rebuilt from the exact accepted Arcane beta1 and Pure beta2
compiler inputs. All source/resource hashes were checked and frozen before
rebuilding. Only the color payload/fixups, r23 diagnostic label and version
identities changed. Feature dictionaries remain identical apart from package
and Pure runtime identities. Existing optimizations, speech configuration,
world options, AI and interface fixes are preserved.

Six archives change: Arcane core/colors/desync/common UI, and Pure native/data.
Every payload change is restricted to an existing helper or the Arcane version
INI. Pure data receives a new module identity for lobby compatibility; its
payload is byte-identical. Arcane powers/shards and Pure common/graphics/world
packages are retained at their original versions/hashes. The actual public
Pure color package was independently downloaded and verified: it currently
contains 39 colors, despite older notes describing 48. Its contents and package
identity remain unchanged.

Only v2/v3 beta feeds, beta history and the standalone Arcane beta guide are
promoted. Stable feeds, legacy feeds, launcher 1.0.13 and unrelated package
records remain unchanged. Both mode guides and changelogs receive their own
new version. All six changelog languages use one short player-visible bullet.

## Accepted checks

- Native lifetime regression: 92 checks for Arcane and 92 using the actual
  public Pure palette. Reused Session/player/string addresses, last-character
  GUID difference, changed three-participant order, authoritative snapshot and
  late join; two native address layouts.
- Actual 361-byte stock Session::Reset executed against old and fixed payloads:
  old code inherits two explicit colors, fixed code resets both to Random.
  External OS/logging/formatting/unrelated cleanup calls are stubbed.
- Compiled offline checks: 1,656 assertions across all 12 final helpers,
  embedded payload hash, real palette loader, relocation and palette injection
  at two cave addresses; GUID storage remains isolated from localized data.
- Arcane helper quiet-startup, common UI, color payload, city assistant and fast
  transfer self-tests passed in every variant. The 37,753 participant/native
  setter/transport/save checks and 96 popup ABI checks from the local fix still
  apply to the identical native payload.
- Real launcher selection/update detection: 635,906 assertions across 55,296
  settings combinations. All three active betas detect their correct update;
  stable and patch-disabled modes keep their prior packages/helper choices.
- Actual transactional installer: 20 Vanilla/Immortals cases, covering six
  text locales, all four helpers, stable rollback, master disabled, file-only
  and beta reapplication. Native preflight passed for native Pure modes.
- Actual transactional installer: 12 Arcane cases, covering all eight helper
  variants and six text locales. Installed module files/hashes and chosen
  helpers matched the new archives.

No new live games were launched for publication. The previous live isolated
Arcane selection/match/return-to-same-lobby test remains the live evidence.
Complete new-room Internet acceptance with multiple human peers remains
unverified and is not claimed here. The actual reset procedure and emitted
native color code are covered by the emulation checks above.

## Artifacts and publication procedure

`F:/PawsLobbyColorsPublish-20261109` contains frozen helper inputs/reports,
package audit, signed candidates, native proof JSON/logs, compiled offline
checks, installer fixtures/logs and release receipts. The installed game and
the user's original saves are outside these fixtures and rehashed by the gate.

`tools/LobbyColorsRelease/prepare.py` snapshots, builds, repacks and signs
candidate catalogs. `verify.py` performs the accepted checks without launching
games. `publish.py` gates publication, preserves unrelated staged work, commits
only the explicit color-fix/release-tool/document paths, uploads immutable
prerelease assets, verifies public bytes, and then promotes the four scoped
catalog/history paths. Source and catalog commits are separate. Public
readback verifies all six feeds and both mode versions after the push.

Each prerelease includes an exact compiler-input/source/resource attachment;
the game executable, saves and signing keys are excluded. PE timestamps are
not claimed deterministic. GitHub release/catalog receipts are written only
after their respective remote operations succeed.

# Arcane Wars 0.5.0-beta.4: remove active-match admission

The active-match return module caused persistent player pauses on temporary
connection-recovery events. The user requested removal of the entire feature,
preservation for future work, and no reactivation of the previous automatic
save-and-lobby recovery.

`game/hotjoin/build_without_hotjoin.py` rebuilds all eight helpers from the
digest-pinned published beta.3 inputs. It removes the `PAW_HOTJOIN` define,
managed startup/install calls, `PawHotJoin.cs`, and `PawHotJoinNative` resource.
Features explicitly report `hotJoinRevision=0`, `legacySaveLobbyRecovery=false`.
All other native resources are byte-identical, including mixed biomes,
600-second dynamic daylight, faster lobby transfers, company behavior, AI,
interface changes and the lobby DLL without integrated recovery.

Only four Arcane beta packages change: pawpatch-core, common-ui, player-colors,
desync-continue. Unchanged data/localization packages retain beta.3. Stable,
Pure, Immortals, the base mod and launcher 1.0.8 keep their existing releases.
Current beta guide no longer advertises joining active matches. Changelog:
short player-visible bullets in en/ru/de/fr/cs/uk.

Offline evidence: `C:/PawsNoHotJoinQA-20261107`.

- All eight helpers compile and pass 40 built-in self-tests.
- Reflection-only inspection confirms no active-match or old save-recovery
  resource and unchanged hashes of every remaining embedded resource.
- Catalog check: 55,296 component selections, 635,906 assertions. Update scope
  is limited to enabled Arcane beta patch selections; all selected helpers
  are supplied by the four updated packages.
- Installation/rollback and effective data checks use a private marked fixture
  and the real selector, downloader and installer. No game process is launched.
- The first candidate build was rejected because its feature metadata omitted
  the existing dynamic-day/biome-selection fields; helpers-r2 preserves them.

No live games, multiplayer tests, VM or installed-game updates are authorized
for this release while the user is playing. Offline checks do not establish
multiplayer/visual acceptance or a rendering-performance improvement. Removing
the module restores native active-match admission rejection; it does not claim
to solve the friend's dense-army rendering hitch.

Preservation: workspace `outputs/hotjoin-preserved-20261107/` contains a verified
ZIP with 170 entries, 165 verified input/file records, both sets of eight helpers
(published beta.3 and private pause-fix), full native sources, original compiler
input mappings, working-tree patch and RESTORE.md. SHA-256:
`4AB8BD182F41A2D79739CC360EE3838C14BE17956E0CC11905351B2943E9D873`.
No private signing key or personal reconnect ticket is included. The private
pause fix has native wrapper tests and helper self-tests, but its live run was
interrupted at the user's request and is not accepted multiplayer evidence.
Earlier prototypes, external fixtures and unrelated dirty work are retained.

Publication uses a new immutable patch-0.5.0-beta.4 prerelease and verified
public downloads before switching only v2/v3 beta catalogs/history/guide.
Final release URL, source/catalog revisions and public verification receipt
are recorded in the workspace handoff after publication.

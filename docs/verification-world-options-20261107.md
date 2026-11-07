# Arcane Wars 0.5.0-beta.3 / launcher 1.0.8

Candidate: dynamic Sun, mixed-biome subset selection, three-row random-map rule panel and launcher mod-manager relocation. The release uses **600 simulated seconds**, not the separate 30-second preview. All eight helpers retain the previously shipped production hotjoin runtime and disable legacy save/lobby recovery.

Source and reproduction: `game/world-options/README.md`. Local evidence root: `C:/PawsWorldOptionsQA-20261107`. Production staging is its `publication` subdirectory; previous local builds/prototypes are preserved.

Accepted behavioral evidence before packaging:

- `policy-r1/acceptance.json`: 10,000 seeds, counts 1/2/3/4 approximately uniform, all 15 nonempty subsets, 128 broad-region maps and 9,601 interpolation observations.
- `native-tests-r1/native-tests.json`: 3,646 x86 geometry, spawn-gate and limit checks at three image bases; 89 spawn definitions.
- `transactions-r1/verification.log`: 1,104 guard/installation/rollback assertions for eight native hooks.
- `live-r10/world-options-acceptance.json`: Dynamic/Random genuinely selected through the game window, two native local peers, normal departure and cold native checkpoint return. 634.25 simulated seconds after return, 634 matching world CRC samples spanning 633 seconds, no mismatches. The same serialized random phase persists; pause freezes colors; native checkpoint bytes match on both peers.
- `live-r12/world-options-acceptance.json`: final translated data composition, mixed-only rule visibility, another 68 seconds of matching post-return CRC evidence.
- `live-fast30/world-options-acceptance.json`: temporary preview only, two complete 30-second cycles with matching CRCs. This payload is excluded from production.
- `native-default600/native/payload.bin`: SHA256 `E84004C26D59B77BF866B2EA9BD1B5C408B6E0C16FD44F2EA064DCFE3E153AF4`, byte-identical to the accepted 10-minute native payload.
- The compact rule panel was visually accepted at 800×600: three complete rows, no vertical rule scrollbar and an untruncated Russian Dynamic label. The object/preview panels give up 24 logical units; button positions are retained.
- Launcher custom-mod management: 96 UI checks on each of en/ru/de/fr/cs/uk; 42 existing game-settings checks in Russian; narrow/wide layouts visually inspected. Existing import/order/replace/apply and draft cancellation behavior retained.

Publication download defect diagnosed and corrected first: beta.2 metadata had new version/size/SHA256 but retained beta.1 in its `urls` array. The publisher had written an unused singular `url`. Commit `950363472e0372b752f15241293e8ff8485c339f` fixes both active signed catalogs and the producer, and adds catalog URL-version validation plus an end-to-end downloader command. Its CI passed: run 42372667175. Native FeedClient downloaded all ten corrected public beta.2 assets with a deliberately incorrect old partial file preseeded; size/hash validation stayed enabled. Correct archives were added to the user's download cache only; no installed game files were changed. GitHub raw main can temporarily serve an earlier cached catalog, so publication audits must verify actual `urls` and repeat the client-path check after propagation.

Boundaries: behavioral tests were local LAN on one PC. Internet/NAT, VM, new three-player and host-migration combinations were not rerun for this change. Existing production hotjoin code is retained. User game EXE and original Случайно/Случайно2 saves were hash-checked and preserved. The six unrelated social/admin-test edits remain outside these commits.

Final archive, catalog, installation matrix, source-commit and public download receipts are recorded under `publication` after release gates complete. This document does not itself claim publication succeeded.

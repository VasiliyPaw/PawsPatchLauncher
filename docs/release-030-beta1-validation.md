# Patch 0.3.0-beta.1 validation — 2026-09-08

## Scope

Built-in Beta assistant from the locally accepted r9 implementation. No launcher release, stable promotion, account-service change, stock EXE modification or save-format change. Release remains 0.2.0 and launcher remains 0.6.3. Eight native helper variants preserve independent settings.

## Automated results

- Launcher regression suite: **8606 PASS**, mocked network/account transports; no production user operations.
- Eight helpers: **534** quiet-startup assertions and **177** assistant installation checks each; common-UI and lobby-payload self-tests also exited successfully. Compile-time features matched colors/bypass/hostility independently.
- Pure queue: **92** assertions. Emitted native interaction/order/engine tests: **399 / 294 / 159** checks. Regenerated payload and fixups matched the checked-in resources byte-for-byte.
- Signed package audit: **384 Beta + 384 Release configurations**, including standard/×2/×4 roaming. Checks effective overlays, helper selection, mandatory Beta layouts, translation preservation and active resource/scoring order. This is a file-level audit, not 768 launched matches.
- Full real-package clean install: Release and Beta, EN and RU, eight helper combinations each (**32 profiles**), then uninstall; stock EXE and save sentinel preserved.
- Final Beta common-UI installation test: all eight profiles and uninstall passed.
- Actual installer transitions: Release → Beta all-on → Beta all-off → Release → rollback to Beta → Release → uninstall. Installed version/channel, helper restoration, original custom layout and save sentinel passed.

The lengthy clean-install run used candidate v1's core/common-UI/player-colors archives. Every entry, including module manifests, was compared byte-for-byte to final v2 for those three packages; only ZIP metadata changed. That run used the default disabled-Powers option. The corrected v2 Powers overlay was covered separately by every Beta selection audit and the live test below, not by that full clean-install run.

## Live single-player check

A separate QA game folder used the final v2 **EN / colors OFF / bypass OFF / hostility OFF / original Powers and Shards** configuration. Desktop interaction verified startup, the 0.3.0-beta.1 menu label, a new custom match, restored Shards and the native F1 panel.

F1 initially showed ON/2000. While typing 350, spending remained paused. Enter committed 350 without opening chat. One normal building order costing 125 was accepted: gold changed from about 509.69 to 384.84, and the city became busy. The next order waited for enough money to preserve the reserve. The QA game was closed afterward.

This live test exposed a pre-existing Powers overlay bug: the actual Shards definition was inside a header comment, causing the scoring resource order to disagree with the game. The builder was corrected to insert only into active content. A new regression check reproduced the old failure and passed with v2. Only Beta receives the fixed Powers package; stable was not changed by this release.

Earlier user testing covered the local assistant in multiplayer and save loading. The final eight integrated Beta binaries were **not each retested in a two-PC multiplayer match** during publication. The warning's native event/sound path is covered by the existing payload and offline checks; no intentional live desync was induced in this release check. Reserve/toggle still reset to ON/2000 on load, as documented.

## Immutable final assets

| Archive | Bytes | SHA-256 |
|---|---:|---|
| pawpatch-core-0.3.0-beta.1.zip | 1545645 | A8D35FA4105AD8F0BCE8A3F99D64660715ED8D4C39545E2BCC6272CC915F19BC |
| common-ui-1.3.72-ui.4-beta.1.zip | 286406 | 19599EAA6DEB361A0A86038D5D34E1E623ED83B635E9BE63BDFD1832A2EC74B6 |
| player-colors-0.3.0-beta.1.zip | 252978 | 570DBD148D8EAC0ADE4FCD6AD1B0E541CE1A33278E6761B81D628E5CF4BD5A1C |
| powers-shards-original-1.3.72-powers.2-beta.1.zip | 140339 | 71988FDEC95B1BB61F89082FD7FCF0F88BD78AFAF2F51262041120824054CA93 |

Publication order: source commit, immutable prerelease assets, anonymous asset verification, signed Beta feed promotion, public feed verification. Stable feed bytes and launcher metadata must remain unchanged. The previous signed Beta feed is retained for rollback.

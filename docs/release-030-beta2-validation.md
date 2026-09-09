# Beta 0.3.0-beta.2 validation — 2026-09-09

## Release boundary

This is the advanced city policy r13/native F1 resource-input update plus the
previously accepted R2 native lobby save-transfer tuning. Both are compiled into
all eight Beta launch helpers. Neither is an optional launcher component. The
in-game city automation checkbox still stops automatic orders.

Release gameplay remains 0.2.0; launcher remains 0.6.4. Only Beta packages
`pawpatch-core`, `common-ui`, and `player-colors` change. The shared About guide
is refreshed in both signed feeds. Existing Beta feed is retained as
`feed/history/beta-before-city-beta2.json` when the update is promoted.

## Automated verification

- Final launcher regression executable: **8,801 passing assertions**.
- Package/configuration audit: **384 Beta + 384 Release combinations**. Checks
  include selected helper, package ownership/conflicts, translation keys,
  effective resource order and the two built-in features. This is an offline
  audit, not 768 live multiplayer games.
- All eight final helpers pass five self-test modes: quiet startup (534 checks
  per helper), common UI, lobby payload, assistant installation (207 checks per
  helper), and fast transfer (663 checks per helper).
- Managed city planner: **1,096** assertions; settings form: **44** checks.
- Native policy: **2,016** checks; construction forecast: **2,004**; native F1
  inputs: **1,755**. Actual x86 instruction tests include multiple relocation
  bases, both resource layouts, invalid input and fail-closed cases.
- Fast transfer: **663** managed and **8,421** native checks. These do not execute
  network socket or disk-transfer I/O and do not establish WAN throughput.
- Clean real-package installs: Release/Beta × English/Russian, with all eight
  helper selections reconciled and uninstall verified for each profile.
  Stock executable and save sentinel were preserved.
- Component switching, Release → Beta → Beta all-off → Release, rollback to
  Beta, and uninstall passed against the final signed candidates.
- Final .NET regression build: zero warnings/errors. Standalone C# fixture
  compilation emits expected unassigned-field warnings for partial test views.

The first candidate was discarded after the configuration audit exposed the
Powers/Shards resource-index difference. The final build maps canonical
gold/stone/wood/iron/mana to both native 9- and 10-resource layouts in managed
planning, native order validation, and in-progress construction accounting.
Native contribution caching accepts the last economic resource in either layout.
Unknown resource layouts fail closed. Shards is not a new automation target.

## Final live checks

Computer Use verified the actual game in isolated copies made from final signed
packages, without a VM or video recording:

1. **English / optional components off / Powers and Shards enabled.** New Shadow
   match; four native F1 fields and English rules dialog render correctly. Enter
   applies the target without opening chat. A crystal target of 2 selects a
   library giving crystal income, not the adjacent resource; the native order
   succeeds and the completed building raises crystal income. Gold-priority
   orders and construction forecasting continue afterwards. Test preferences
   were returned to their original resource targets.
2. **Russian / optional components on / Powers and Shards disabled.** Existing
   pre-crash autosave loads successfully at approximately 37 minutes. F1 shows
   the four resource icons/fields, Russian captions, enabled automation, reserve
   2000 and a waiting-for-gold status. Existing city construction is present.

Both live runs report `FAST_TRANSFER_R2_READY`, all 15 live code guards pass,
native settings are 20/64/256, file budget is 1200 bytes, and maximum burst is
16 packets per peer per pass. Both sessions were closed normally and their
helpers reported `MONITOR STOPPED`.

R2's approximately nine-second PC-to-VM transfer was accepted in the earlier
user-operated test. That network test was **not repeated** for this release;
R3/aggressive transfer tuning is not included. Multiplayer participants should
all update and use compatible gameplay settings. Exhaustive latency/loss and
multi-peer network tests remain outside this validation.

Existing rotating autosaves were backed up and hash-verified before live tests.
The English QA match created a new normal autosave; the pre-test copy remains
available. No manual saves were overwritten. The stock game executable remains
SHA-256 `1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.

The earlier game crash had its first recorded access violation in NVIDIA's
`nvd3dum.dll`. This does not establish the ultimate cause, and this release does
**not** claim to fix it. Successful short runs and loading the autosave do not
substitute for long-session stability testing.

## Final immutable package identity

| Package | Bytes | SHA-256 |
| --- | ---: | --- |
| pawpatch-core-0.3.0-beta.2.zip | 1545645 | `94B9D9FC86136C6B1E878BBBF7B76AACD3D7983BE24F7416807D73E0156AC018` |
| common-ui-1.3.72-ui.4-beta.2.zip | 374269 | `86C1BC6369B4B8E3D915D9A5631F425DC231C9EF9785CF05B223247BEC2AEADD` |
| player-colors-0.3.0-beta.2.zip | 338847 | `00C7E6DDC4A584029B659BBF8E0371E030499168D70FE387FA8BC08D110035FF` |

Assistant payload: 196608 bytes,
`A8CD806B01F8D87A89DE2AFDB8169AEE8B47CD5E9E954DDF00ABE9BA25846EF1`.
Fixup table: 359 records,
`CC14DD8BB7D560DB3AC5A8D34F22FAE15EC41B115BFB06F8347876A0765502E2`.

Publication is gated by immutable tag/source verification, anonymous download
and per-file validation of all three public archives, feed signature validation,
and unchanged-current-feed checks before signed feed promotion. Release and
launcher package identity must remain unchanged throughout promotion.

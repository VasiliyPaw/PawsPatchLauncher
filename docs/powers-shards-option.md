# Powers and Shards option: local candidate

Not published. No user game installation or in-game validation was performed.

## Setting and compatibility

- RU: `Отключение Powers и Shards`; EN: `Disable Powers and Shards`.
- `DisablePowersAndShards = true` by default, including old JSON settings. ON keeps the existing Paw's Patch removal; OFF restores both mechanics.
- Default configuration codes remain byte-identical to legacy codes. OFF adds the final `PS0` field; explicit `PS1` is accepted and canonicalized to the legacy form. Unknown fields are rejected. An old launcher rejects `PS0` instead of silently applying a different configuration.
- Import, last-working configuration, rollback settings, readiness invalidation, package selection and detailed multiplayer comparison use the same flag.
- The restoration package is prefetched with the selected channel. After preparation, either direction uses cached local files through the existing transactional installer and pre-launch apply path.
- Feeds lacking the restoration package cannot install OFF. The control explains the missing package. An imported OFF setting is retained, not silently altered; ON remains available to return to the legacy mode.
- All multiplayer participants must use matching settings. Begin a new match after switching; compatibility with saves created in the other mode is not claimed.

## Data provenance

`tools/BuildPowersShardsSources.py` applies a reviewed byte-oriented inverse of the Powers/Shards removals to the current core. It does not replace the whole core with the Arcane Wars original.

- Original reference: `release_workspace_20260905/original_extract/Arcane Wars 0.82beta/data`.
- Current core: `release_workspace_20260905/sources/pawpatch-core/data`.
- Published archive hashes and all 160 relevant original/core input file hashes are checked against the existing local signed feeds.
- Restores shard resource declarations, costs/production, scoring and the Powers definitions in five factions plus the AI template.
- Four reviewed UI files restore the Powers toggle and shard columns/editor controls. Resource/scoring localization keys are retained.
- Six reviewed input hashes guard whole-file/special-case inverses; ambiguous changes fail instead of overwriting newer fixes.
- No overlap with any other currently selectable module across 12 distinct Release/Beta package identities, including colors, common UI, roaming profiles, siege balance and localization.
- No EXE, hotkey changes or removal entries in the overlay. F9 remains deferred.
- All 167 restored shard declarations, costs and production entries match the original source; faction/AI removal comments are absent. The builder checks these invariants and fails on an incomplete restoration.

Package: `release_workspace_056/powers-shards/packages/powers-shards-original-1.3.72-powers.1.zip`.

160 files, 140,333 bytes, priority 450, dependencies `arcane-wars` and `pawpatch-core`.

SHA-256: `0B8D93803E75D9218809F9D8D5D338CBF2537B57EB9E10DB83682DADD75EC025`.

The source audit lists per-file core/restored hashes at `release_workspace_056/powers-shards/sources/powers-shards-original-audit.json`.

## Local test feeds

`tools/PreparePowersShardsTestFeeds.ps1` creates a new local candidate feed directory. It verifies every referenced archive, signs with the configured project key and re-verifies the result. It makes no remote writes and does not change the online feeds.

- `release_workspace_056/powers-shards/feed/stable.signed.json`: 11 packages.
- `release_workspace_056/powers-shards/feed/beta.signed.json`: 13 packages.
- Existing package bytes are unchanged; URLs point to verified local archives. Previous-release URLs are omitted from this isolated fixture.
- The candidate's adjacent `launcher.config.json` uses these local feeds and a separate cache. Do not distribute this local configuration to friends.

## Validation

- Core policy tests: 366 assertions, including 31 new Powers/Shards checks.
- WPF About: 48 checks per language; Powers UI: 16 per language.
- Existing motion, feedback, appearance, changelog, diagnostics, window, channel, placement, typography and confirmation checks pass in RU/EN.
- 28 layouts pass: five pages, all three About categories, RU/EN, 1050×680 and 1440×900. Actual narrow About and component previews were visually inspected.
- Published local EXE starts with and without external configuration in isolated smoke mode. No user launcher was closed or replaced.
- Real signed local packages pass fresh Release and Beta installations followed by four OFF/ON/OFF/ON states per channel, with Russian localization/colors on Beta and alternate roaming/siege selections. Every selected module hash verifies, all 160 overlay/core winning files match exactly, resource and faction definitions match the option, applied settings persist and no false pending update remains.
- Both channels pass rollback to the preceding configuration and actual uninstall on disposable game copies. Original `k2.exe` and the personal-save sentinel survive unchanged. This is file-level acceptance, not a real game launch.
- Completed fixture: `C:\Users\Paw\AppData\Local\Temp\PawsPowersShardsAcceptance\f334d759a9fe456f830ba7cd141aa9cf`. Test exit code 0; fixtures are retained. The local candidate's feed metadata and public key also match its final EXE and signer.
- Live gameplay, AI behavior and multiplayer still require manual acceptance. Automated file checks do not establish in-game correctness.

The real-file test command is `--verify-powers-shards <stable-feed> <beta-feed> <public-key> <fixture-root>` on the test executable. Use a fresh ordinary temporary folder, not this linked workspace. The fixture preflight preserves the uninstall link/junction guard. An initial workspace run was stopped without a result; a subsequent run verified Release transitions and rollback, then correctly refused uninstall because `C:\Users\Paw\Documents\Codex` is a junction. No protection was relaxed.

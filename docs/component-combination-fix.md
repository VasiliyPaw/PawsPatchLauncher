# Component combination corrections, 2026-09-07

Local candidate only. No upload, online feed change, actual game launch, installed-game modification or replacement of the user's launcher. The user asked to fix the audit findings before deciding to publish.

## Corrected behavior

1. The two roaming profiles without additional companies and the original-siege profile preserve current `#awloc_...` references. There are 22 corrected package files across 13 unique paths: 9 files in each roaming profile and 4 siege files. English definitions and Russian definitions were checked. Reversing only the quoted-string replacements reproduces the old bytes exactly, proving that damage, timing, costs, attacks and other gameplay data were not changed.
2. Siege remains a complete rebalance switch, matching its name. Component description, RU/EN help, About guide and feed-generation descriptions now include cost, damage, minimum range and attack/bombardment parameters. OFF restores the original balance of all four affected engines, with localization preserved.
3. `EffectiveSettings` creates a detached active snapshot. Release always masks custom colors; Beta also requires an available colors package in the matching feed. The remembered Beta preference remains intact. Package selection, launch EXE selection, displayed/copied codes, readiness reports, diagnostics, applied-state snapshots and observed-run settings use the active snapshot. Importing/recovering a Release configuration or changing its Russian-localization checkbox does not erase the user's Beta color preference. Only an explicit available Beta color toggle updates that preference. The parser still rejects invalid incoming Release `CL1` codes; normal generated Release codes contain `CL0`.

All previous 0.5.6 work is retained, including the nearby Powers/Shards help icon, concise tooltip, default-enabled removal option, and 160-file restoration overlay.

## Candidate identities

Launcher: `release_workspace_056/combination-fix/win-x64/PawsPatchLauncher.exe`

- Version: 0.5.6
- Size: 71,975,808 bytes
- SHA-256: `DB6BBA6B065401AF86EB895D531AFFB5C2ACDDF3F90FA411A4129DF15EE48F83`
- Adjacent `launcher.config.json` points to signed local-only Release/Beta feeds and a separate candidate cache. Do not distribute this local configuration.

The following packages under `release_workspace_056/combination-fix/packages` are version `1.3.72-options.2`. Old `options.1` archives are retained, not overwritten.

| Module | Payloads | Archive bytes | SHA-256 |
| --- | ---: | ---: | --- |
| roaming-profile-x4-no-new | 34 | 36,659 | `8291BA7D920567BA1D357D02FC5447D7F8B342BFBBD3792C8DCF877D25049C48` |
| roaming-profile-standard-no-new | 48 | 47,770 | `77CC509BD0700C01F3F895CDFA4BFA5668494E8A433F4B8D048FD7EEBCE3F8E5` |
| siege-balance-standard | 4 | 8,897 | `91DAC7964764B7D8E4DC5606992939AEF34985DBE7C37F777C9E99895D90D4E7` |

Signed local feeds retain all other package hashes, priorities, dependencies and game executables from the preceding Powers/Shards candidate. The localization correction will need these three package updates in BOTH patch channels, not just a new launcher EXE. Previously prepared Powers/Shards restoration also needs publication when that feature is released. No new Beta color/EXE fixes are included in this turn.

## Repeatable preparation and checks

- `tools/RepairComponentLocalization.py --output <fresh-source-root>` verifies original local archives and produces repaired sources. `--repair-generated <root> --core-source <data> --ru-source <strings>` is also called by `BuildGameplayOptionSources.ps1`. It fails on ambiguous/missing translations or non-localization byte changes. Verified the generated-source path on a fresh fixture: all 86 files matched the archived-source repair; repeating changed zero files.
- `BuildReleaseFeeds.ps1` uses a separate `LocalizedModuleVersion`, default `1.3.72-options.2`, for the three repaired profiles. Unchanged profiles retain their prior version. A fresh unsigned local fixture passed in both channels: exactly three repaired versions and the full siege description; unrelated versions unchanged. The older script's other release arguments still need explicit review before real publication. It was not run against the actual publication metadata.
- `PrepareCombinationFixFeeds.ps1` packs the three new profiles, verifies reused local packages, signs/verifies candidate feeds and writes the isolated adjacent configuration. It rejects an existing feed output directory.
- Core tests: **PASS 379**, including 13 new effective-settings/description assertions.
- Package combination audit: **128 Release + 160 Beta** supported combinations, zero translation-key losses, no unreviewed differing-file overlap. Includes the 432 historical combinations in a total of 720; historical losses remain in the evidence, not silently waived. Verifies 8,086 payloads across 16 archive identities. Evidence: `release_workspace_056/combination-fix/audit/combinations.json`.
- WPF, RU and EN: actual Beta colors ON -> Release -> import/recovery -> Beta path passes. Release code is importable, active colors are false, preference true, return restores the checkbox. Powers UI 21 assertions/language; patch-channel checks 16/language; About 48/language. Typography, spacing, help layout and scrolling pass at 1050x680. RU/EN siege-help and Russian About siege-card PNGs were visually inspected and fit without clipping.
- Offscreen About test previously sampled opacity before WPF's first animation tick. It now waits up to 500 ms for that first tick and still requires an intermediate frame strictly between 0 and 1. Production animations are unchanged; rapid-switch/cancellation tests pass.
- Isolated self-contained launcher startup succeeds with local configuration and with EXE only. Candidate hash/size match both local feed declarations.

Full real-package integration completed successfully in `C:\Users\Paw\AppData\Local\Temp\PawsCombinationFixAcceptance\cadecb8fcaa642ff840335a20645802c`:

- Release and Beta each completed fresh install and four Powers/Shards states with varying roaming, siege, language and color options. All installed hashes, winning modules, resource/faction definitions, applied settings and cache-only transitions passed.
- Both channels completed upgrades from `options.1` to `options.2` with additional roaming and siege balance OFF, at both x4 and standard frequency. Every currently required core localization reference was present in installed overlay files (13 x4 files and 20 standard files checked, including unchanged localized files).
- All four old-version upgrade scenarios detected the new packages, settled without a pending update, and rolled back to the exact prior file-hash map. Ordinary option rollback also passed.
- Uninstall passed for both channels, restoring the fixture's original EXE sentinel and preserving its personal-save sentinel. Only test-installed files were removed; recoverable fixtures and their old/new archives remain. No actual game was launched or uninstalled.

The final launcher-only preference guard was then rebuilt, WPF-tested in both languages and smoke-tested with and without external config. Package bytes were unchanged by that final EXE revision. Do not rebuild the test project's shared output while a real-package test is using its DLL; an overlapping attempt hit the file lock and was retried only after the fixture completed.

## Manual acceptance / publication boundary

No live matches, new-save compatibility, third-party mod combinations or multiplayer VM acceptance have been performed here. The automated tests verify package bytes, selection, installer behavior and WPF handlers, not all game behavior. Publication requires a separate user go-ahead, online release-asset URLs, updated signed feed metadata and post-upload download verification. Preserve old release assets for rollback.

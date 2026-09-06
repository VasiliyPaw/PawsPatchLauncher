# Component combination audit, 2026-09-07

Status update: the three findings below are now corrected in a separate, unpublished candidate. This document retains the original read-only findings as historical evidence. See [combination fixes](component-combination-fix.md) for changed files, versions, current checks and remaining manual acceptance.

Scope: read-only inspection of the checked-in signed Release/Beta feeds and the new local Powers/Shards candidate feeds. Every archive and all 8,000 declared payloads across 13 distinct package identities were verified against SHA-256. No online feed was fetched, game launched, game files installed, launcher replaced or release published during this audit.

## What the installer actually does

The launcher does not merge TGI/EXE contents automatically. `GamePackageSelector` chooses complete, prepared variants; `ModuleInstaller` orders modules by priority and ID and chooses a whole file (or a removal) for each path. A higher priority alone cannot preserve two independent edits to the same file.

The existing roaming features already use the required joint profiles:

| Frequency | Additional companies | Applied profile |
| --- | --- | --- |
| x4 | On | Core default |
| Standard | On | `roaming-profile-standard-with-new` |
| x4 | Off | `roaming-profile-x4-no-new` |
| Standard | Off | `roaming-profile-standard-no-new` |

The combined Standard/Off package has 48 files and exactly matches the reviewed composition of the Standard/On and x4/Off changes. Their 19 overlapping paths disable the added sources; standard frequency is retained for the remaining sources. The selector never installs two roaming-profile packages together.

Other reviewed overlaps:

- Russian localization overrides `startup/autoexec.txt`, preserving the writable `%USERDATA%` work depot. The selected locale line matches the setting in every combination.
- Beta `common-ui` overrides the older core/desync helper EXEs with already-combined versions. The actual launch selector picks an installed helper for every supported combination. Colors still require independent hostility and official desync handling; invalid combinations are not counted as supported.
- The new Powers/Shards overlay's 160 files do not overlap other optional feature packages. Its overlaps with Arcane Wars/core are deliberate restoration of that layer.
- The obsolete standard-map package remains unselected. Large maps stay enabled.

## Exhaustive selection results

| Feed set | Channel | Supported combinations | Configurations with translation-key loss |
| --- | --- | ---: | ---: |
| Checked-in public feed | Release | 64 | 24 |
| Checked-in public feed | Beta | 80 | 30 |
| New local candidate | Release | 128 | 48 |
| New local candidate | Beta | 160 | 60 |

432 supported combinations in total. All eight binary settings were enumerated; the real configuration parser rejects unsupported color states, and the old feeds cannot restore Powers/Shards. Selection and whole-file precedence agree with the installer's `MultiplayerCheck.Expected` model, including removals. Dependencies, profile exclusivity, selected EXE presence, common-UI precedence, permanent map sizes and startup/work-depot contents were checked.

No unreviewed co-selected differing-file overlap was found. This is NOT a statement that all gameplay combinations are correct: the semantic issues below remain.

## Findings not fixed in this audit

### 1. Some optional profiles lose localization keys

Full-file restoration from original Arcane Wars drops `#awloc_...` references present in the current core:

- New roaming companies OFF, either frequency: 9 files, 12 distinct keys across those files.
- Siege balance OFF: 4 files, 23 keys across those files.
- Together these affect 13 unique file paths. Both checked-in feeds and the new local candidate contain these issues.

Examples include the four foundation camps, Grim Spider/Scorpion lairs and units, Rhaksha, Plague/Crimson Catapults, Vorpal Engine and Dragonfire Ballista. These files restore literal English names rather than the current lookup keys. The separate Russian language package cannot restore keys that the gameplay file no longer references. Live UI rendering was not tested, so the exact visible untranslated labels remain a manual acceptance item.

The report lists all affected paths/keys and every affected configuration. A safe correction would preserve current localization references while changing only the intended gameplay fields; creating separate RU/non-RU copies is not necessary if both use the same localization keys.

### 2. Siege behavior is broader than its description

The tooltip/guide describe 0.75 kingdom-point cost. The OFF package restores entire original unit definitions, not just that cost. In particular, Vorpal Engine also changes damage and minimum range; Dragonfire Ballista changes damage, bombard parameters and effect definitions. Plague/Crimson Catapult diffs include cost and localization references.

This is not a collision between two currently separate balance toggles. It is a mismatch between the advertised scope and the actual full-file variant. Before editing the package, decide whether the switch is intended to control the whole siege rebalance or cost only. If the whole rebalance is intended, explain it accurately and preserve localization. Future separately configurable balance edits need a joint variant when they share these definitions.

### 3. Remembered Beta colors leak into the Release friend code

An isolated WPF test calls the real color handler and channel-change path using local fixture feeds:

1. Select colors in Beta.
2. Switch to Release.
3. The visible color checkbox is OFF, but remembered `CustomPlayerColors` remains true.
4. The displayed/copied code is `PAW-STABLE-IW1-SP4-RM1-SG1-LM1-RU1-CL1-OOS0`.
5. The real configuration parser rejects that code because Release does not support colors.

Returning to Beta correctly restores the remembered selection. The needed correction is to distinguish remembered preferences from the effective active-channel configuration used for sharing/readiness/applied settings; do not simply discard the user's Beta preference. No production fix was made here.

## Repeatable audit and future features

Run the test project with `--audit-combinations <repo> <report-directory-inside-repo>`. It reads signed local feeds and local archives only. Machine-readable evidence is at `release_workspace_056/component-audit/combinations.json`, including exact feed/archive hashes, every selected combination, all reviewed collisions and translation losses.

The audit fails on an unknown differing-file overlap, even if numeric priorities would otherwise choose a winner. Byte-identical shared files are harmless. A synthetic future-balance/siege overlap is explicitly rejected. This is an audit tool, not a new runtime merge engine or an automatically wired publication hook.

The WPF reproduction runs through PreviewRenderer with `--smoke-test --combination-audit`. It uses isolated settings and does not touch the actual clipboard or user game. Existing core tests still pass 366 assertions; they did not previously cover these semantic combinations.

Before publication, fix the localization/code findings and resolve the intended siege scope, then rerun the audit and representative fresh-match tests. Exhaustive live multiplayer, save compatibility and arbitrary third-party mods were not tested.

## Follow-up correction, 2026-09-07

The fixed feeds at `release_workspace_056/combination-fix/feed` add 128 Release and 160 Beta combinations, all with zero translation-key losses and no unreviewed differing-file collisions. The current audit retains the 432 historical combinations, for 720 total, verifying 8,086 payloads across 16 archive identities. New evidence is `release_workspace_056/combination-fix/audit/combinations.json`.

The siege toggle retains the complete existing rebalance; its description now matches the scope. Only localization references were repaired in the affected game files. Effective active-channel settings now exclude remembered Beta colors from Release sharing, readiness, applied snapshots and game-run records while preserving the Beta preference. Core checks now pass 379 assertions; real WPF channel-transition/import tests pass in both languages. These are not live multiplayer or save-compatibility checks.

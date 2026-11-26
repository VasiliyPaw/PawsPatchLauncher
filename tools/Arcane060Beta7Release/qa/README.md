# Arcane Wars 0.6.0-beta.7 release QA

Source-only candidate. No SDK, compiler, Python preparation or tests were run by the author while the shared slot is held. The owner runs this after Main25 explicitly closes **all** activity and the final packages/material manifest/signed feeds exist.

The project references the current release source at `../source/src/PawsPatchLauncher/PawsPatchLauncher.csproj`. It does not copy or load the historical launcher-reference assembly. All fixture paths and outputs are physically on G:, with reparse points rejected. No game executable, helper, video, capture or installed-game directory is launched or touched.

## Inputs

Run `prepare.py` only after the final package build and catalog signing. It imports the release owner's `context.py` and verifies all four v3 feed signatures before preparing metadata. If artifacts are pending it prints `PENDING` and exits zero without producing a passing result.

It reads the real four beta.6 ZIPs from the retained `outputs/ui-revert-release-20261118/arcane/assets`, and the four final beta.7 paths from `outputs/arcane060-beta7-release-20261126/package-audit.json`. It hashes the actual eight archives, reads their original module manifests, and records independent production pins from accepted Water/Bridges, helper, Shadow and AO evidence.

## Run after the shared slot is released

Use the approved explicit SDK executable already selected by the release owner. Set `$sdk` to that exact path; do not probe/install another SDK or edit persistent PATH. These are process-only variables:

```powershell
$qa = 'G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3/work/arcane060-beta7-release-20261126/qa'
$release = Split-Path $qa
$env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = 'false'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_CLI_HOME = "$release/dotnet-home"
$env:NUGET_PACKAGES = 'G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3/work/arcane060-beta3-release-20261116/nuget'
$env:NUGET_HTTP_CACHE_PATH = "$release/nuget-http"
$env:NUGET_SCRATCH = "$release/nuget-scratch"
$env:TEMP = "$release/Temp"
$env:TMP = "$release/Temp"
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'C:/Users/Paw/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' "$qa/prepare.py"
# Stop here if prepare reported PENDING; do not run with stale inputs.json.
& $sdk build "$qa/QA.csproj" -c Release
& $sdk "$qa/bin/Release/net8.0-windows/QA.dll" "$qa/inputs.json"
```

## Expected coverage

- Exactly **28,944** before/after profiles: three mods, stable/beta, patch/data-only states, six text languages, four speech languages, three roaming modes, and all 64 combinations of colors/sync/hostility/new companies/siege/powers where active. AI and zero-morale flags also take both values independently through existing spawn/voice dimensions.
- **96** additional explicit AI/zero-morale boundary pairs across all three mods, channels and patch/data-only states, using the real effective-settings, selection and helper APIs.
- Real `EffectiveSettings`, `GamePackageSelector`, `GameExecutableSelector` and `UpdateDetector`, unchanged selected IDs/settings/executable choices, all eight Arcane production helpers. The real package masks are checked as four common-ui helpers (family/sync-family/sync-continue/ui) plus four player-colors lobby helpers. Common-ui wins its overlaps over core/desync; player-colors supplies lobby helpers. Only four Arcane beta package identities may change; stable and every non-Arcane package remain identical. Beta.6 receives an update and beta.7 satisfies every detector.
- A new empty private fixture, **four actual beta.6 packages** prepared/installed, then **four actual beta.7 packages** prepared/upgraded. Base/colors/sync/both combinations exercise actual installer priority and live helper hashes.
- Full `ModuleInstaller.VerifyAsync` and independent live SHA checks of every effective file, every production DLL, **952** water PNG, **56** Shadow NIF, **672** AO replacements and **1,132** preserved HD removal paths. All eight helpers must be installed and SHA-checked during full upgrade/reapply. Configurations without colors must have no lobby helpers, except an explicitly recorded original sentinel which must retain its exact original bytes. Non-helper pins remain mandatory in every active configuration.
- Tiny original sentinels at all 1,132 removal paths plus one helper and one unmanaged file. Disable-all restores exact original bytes and exact original file set; a real `PatchRecovery.RollbackAsync` restores the installed configuration; disabling again and reapplying both pass. No full BaseGame copy or game process is required.
- Logical fixture size stays below **3 GiB**, checked after every installed stage. The real beta.6 payloads already total **437.28 MiB** (core 328.68, common-ui 95.20, colors 8.96, sync 4.44). Preparing both real versions, installing the selected files and retaining transaction rollback copies is expected to use approximately **2–2.5 GiB** at peak. The earlier 1 GiB estimate did not account for all uncompressed package/recovery copies. The test retains the complete eight-package scope; it does not copy an installed game, BaseGame/Data.rwd or the unchanged terrain master package.

## Result contract

Success is `outputs/arcane060-beta7-release-20261126/qa/result.json` with:

- `passed: true`, `selections: 28944`, `featureCases:96`, `checks`, `installedFileChecks`;
- `counts` (`dll`, `helper:8`, `water:952`, `shadow:56`, `ao:672`, `hd:1132`);
- `packageAssets`: keys `old:<id>` / `new:<id>` for each of the four IDs. Each records **actual archive** `path`, `version`, `size`, `sha256` and `signedSha256`. The publisher must rehash final uploads against these values;
- `helperHashes`: eight exact production helper SHA values checked against installed payloads;
- `installedHelpersSeen`: all eight helpers observed and SHA-checked in the real fixture; `helperPackageMasks` records the verified common-ui/player-colors 4+4 allocation;
- `fixture`, `stages`, `realLauncherAssembly`, `launcher`, `nativeGameLaunched:false`.
- `fixtureBudgetBytes:3221225472`, `peakObservedFixtureBytes`: the 3 GiB limit and maximum observed logical fixture size after a stage.

On error the process returns 1 and writes `failure.json`; no `passed:true` is manufactured. A private fixture is retained for inspection. The fixture is never automatically deleted, moved, reused or substituted with an old QA installation.

The release wrapper supports a generic-only runtime of the same compiled assembly without the optional `--upgrade-private`. The failed optional upgrade of the retired native fixture is preserved separately: its historical custom-voice package cache had been removed. It is not a release QA pass and does not change the full generic install/rollback assertions. Native fixture assembly is documented in README-native-save.md.

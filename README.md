# Paw's Patch Launcher

Windows launcher and transactional updater for Kohan II, Arcane Wars and Paw's Patch.

## Intended release layout

- `arcane-wars`: required base module.
- `pawpatch-core`: required Paw's Patch data and the default runtime launcher.
- `localization-ru`: optional Russian localization.
- `player-colors`: optional experimental multiplayer color selection, available through the Beta channel.
- `desync-continue`: optional experimental out-of-sync bypass launcher.
- `roaming-profile-*`: mutually exclusive overlays for standard/×4 timing and original/additional roaming-company sets.
- `siege-balance-standard`: restores the original Arcane Wars siege-engine costs when Paw's balance is disabled.
- `large-map-sizes-standard`: removes only the two Paw map sizes while preserving the remaining random-map fixes.

The default core profile keeps independent hostility, ×4 roaming frequency, additional roaming companies, Paw's siege balance, and the two large map sizes enabled. Small higher-priority overlays restore the original behavior when a setting is disabled, so switching an option does not require reinstalling Arcane Wars.

## Update model

1. A small signed channel envelope is checked at startup.
2. Archives are downloaded from the first available mirror and verified by SHA-256.
3. Each archive contains `module.json` plus a `payload` directory with per-file hashes.
4. Packages are extracted with path traversal protection.
5. Enabled modules form an ordered overlay. Disabling a module reapplies the next lower layer instead of blindly deleting files.
6. Installation is staged and rolled back if a copy fails.
7. The launcher can download a new signed launcher executable, hand replacement to a temporary helper script, exit and restart.

The Stable and Beta channels use separate signed feeds. Stable keeps the last accepted patch, while Beta can add early modules without changing Stable. Returning to Stable and applying the update removes files that belonged only to the Beta module.

The active channel is checked at startup, after a channel switch, and once per minute while the launcher remains open. Patch updates are reported for the selected channel. Launcher self-updates are offered through a visible button instead of closing the launcher without user action.

Launching the game also reconciles the selected channel and every component setting first. A failed update prevents the game from starting with a partially applied configuration.

Gameplay options that affect multiplayer produce a compact configuration code. Players can copy it before a match and compare codes to catch mismatched settings. The diagnostic archive command collects available logs, sync logs, dumps, launcher state, module versions and SHA-256 hashes; crash dumps should be reviewed before public sharing because they can contain memory fragments.

Every installed module records its complete file list. Files dropped by a newer version are removed automatically, and a package can additionally contain explicit removal entries for legacy manual installations. Original files are backed up and restored transactionally when appropriate.

No private signing key belongs in this repository or in a public release.

Arcane Wars is a free non-commercial third-party mod by Darquan Mortis. Its files are not part of this source repository and are not covered by the launcher source-code license.

## Hosting

The feed supports multiple URLs. Recommended initial setup:

1. GitHub Releases for packages and launcher binaries.
2. A small signed `stable.json` feed on GitHub Pages or a raw repository URL.
3. Optional Cloudflare R2 custom-domain mirror if download speed requires it.

## Development

Use the workspace portable .NET 8 SDK:

```powershell
& 'C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe' build .\src\PawsPatchLauncher\PawsPatchLauncher.csproj -c Release --ignore-failed-sources
& 'C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe' run --project .\tests\PawsPatchLauncher.Tests\PawsPatchLauncher.Tests.csproj -c Release --ignore-failed-sources
```

Pushing a version tag such as `v0.1.0` builds the self-contained Windows launcher and creates a GitHub Release. Module archives and the signed stable feed are published separately so the signing key never leaves the maintainer's computer.

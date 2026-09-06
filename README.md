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
7. Launcher updates preserve the previous executable and require a startup acknowledgement. The independent helper automatically restores a failed update.

The Release and Beta channels use separate signed feeds. Release keeps the last accepted patch, while Beta can add early modules without changing Release. Installing or switching a channel downloads every settings variant for that channel into the verified local cache. Changing gameplay switches after that is a local overlay operation performed before launch and is not reported as a new patch update. Returning to Release and applying the update removes files that belonged only to the Beta module. The internal `stable` ID, `stable.json` URL and `PAW-STABLE` configuration codes are retained for compatibility with existing installations.

The active channel is checked at startup, after a channel switch, and once per minute while the launcher remains open. The main action reads `Install`, `Update <channel>`, or a disabled `Installed` according to the actual state. Launcher self-updates run automatically at startup and remain available through a visible button during the session.

Version 0.5.0 adds persistent patch rollback, configuration import, an exact multiplayer file comparison, working-settings recovery, crash/unclean-exit diagnostics, critical launch checks, resumable downloads, unread changelog markers and pinned previous Beta releases. See [reliability behavior and validation](docs/RELIABILITY.md).

Launching the game also reconciles the selected channel and every component setting first. A failed update prevents the game from starting with a partially applied configuration.

Gameplay options that affect multiplayer produce a compact configuration code. Players can copy it before a match and compare codes to catch mismatched settings. The diagnostic archive command collects available logs, sync logs, dumps, launcher state, module versions and SHA-256 hashes; crash dumps should be reviewed before public sharing because they can contain memory fragments.

Every installed module records its complete file list. Files dropped by a newer version are removed automatically, and a package can additionally contain explicit removal entries for legacy manual installations. Original files are backed up and restored transactionally when appropriate.

No private signing key belongs in this repository or in a public release.

## Window placement

The launcher saves its normal size/position, monitor connection and maximized state on an accepted close, in `%LOCALAPPDATA%\PawsPatchLauncher\window-placement.json`. The file is shared by launcher versions/copies for that Windows account, but is separate from patch settings, configuration codes and multiplayer fingerprints. A minimized window reopens in its preceding normal/maximized state, never minimized. Cancelled closes do not save; missing/invalid metadata uses the default window.

Monitor interface identifiers, not model names, distinguish identical displays and take priority over `DISPLAY1/2/3` numbering. A changed/disconnected monitor layout chooses an available screen and bounds the window to its work area. Native placement accounts for restored bounds, taskbars and effective window DPI; unchanged geometry preserves negative coordinates and intentional multi-screen placement. Port/driver/remote-desktop changes can change identifiers, so that case uses a safe fallback rather than claiming permanent physical-monitor identity. The local placement file is removed only by launcher uninstall, not by patch removal/cache cleanup.

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

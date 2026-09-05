# Paw's Patch Launcher

Windows launcher and transactional updater for Kohan II, Arcane Wars and Paw's Patch.

## Intended release layout

- `arcane-wars`: required base module.
- `pawpatch-core`: required Paw's Patch data and the default runtime launcher.
- `localization-ru`: optional Russian localization.
- `player-colors`: planned optional multiplayer color selection. The launcher keeps this switch disabled until a compatible package is published.
- `desync-continue`: optional experimental out-of-sync bypass launcher.

Balance and random-map data remain in `pawpatch-core` until overlapping `.tgi` files are split into reproducible variants. The UI must not promise unsafe per-feature toggles before that work is complete.

## Update model

1. A small signed channel envelope is checked at startup.
2. Archives are downloaded from the first available mirror and verified by SHA-256.
3. Each archive contains `module.json` plus a `payload` directory with per-file hashes.
4. Packages are extracted with path traversal protection.
5. Enabled modules form an ordered overlay. Disabling a module reapplies the next lower layer instead of blindly deleting files.
6. Installation is staged and rolled back if a copy fails.
7. The launcher can download a new signed launcher executable, hand replacement to a temporary helper script, exit and restart.

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

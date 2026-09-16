# Paw's Launcher

Windows launcher and transactional updater for Kohan II, Immortals, Arcane Wars and optional Paw's Patch components.

Version **0.8.3** adds shorter match player cards and independent Vanilla/Immortals
Beta switches for compact player colors and ignoring desyncs.
See the [launcher release notes](docs/release-0.8.3.md).
Vanilla and Immortals Paw's Patch **0.2.0** includes fast native save transfers;
**0.3.0-beta.1** adds the two optional features. See the
[stable notes](docs/release-pure-0.2.0.md) and [beta notes](docs/release-pure-0.3.0-beta.1.md).
Arcane Wars **Paw's Patch 0.3.0-beta.8** adds compact participant colors,
improved city development, per-match preferences, militia handling and preserved
saved ownership. See the [Beta release notes](docs/release-patch-0.3.0-beta.8.md).

[Download PawsPatchLauncher.exe](https://github.com/VasiliyPaw/PawsPatchLauncher/releases/latest/download/PawsPatchLauncher.exe)
or see the [latest release](https://github.com/VasiliyPaw/PawsPatchLauncher/releases/latest).
The other game-package archives are downloaded automatically by the launcher.

## Code signing policy

See the [code signing policy](docs/CODE_SIGNING.md) and
[privacy policy / конфиденциальность](docs/PRIVACY.md).
Current launcher 0.8.3 downloads are unsigned. No SignPath approval or immediate
removal of SmartScreen warnings is claimed. The [setup guide](docs/SIGNPATH_SETUP.md)
describes activation. Update catalogs are separately signed and downloaded files
are checked against their SHA-256 hashes.

## Mod library (0.7.0)

Vanilla is selected on a fresh installation. Each mod retains its installed releases
and available patch components. Selection does not modify the game; Apply performs
the verified local overlay operation. Only selected localization packages download.
The launcher retains text and speech choices independently of mods. Game text is
available in English, Russian, German, French, Czech and Ukrainian; speech is
available in English, Russian, German and French. New font resources are included
with the Czech and Ukrainian text packages. All six languages are also available
for the launcher interface.

Vanilla and Immortals have optional Paw's Patch fixes and separate Release/Beta
channels. Arcane Wars also supports disabling Paw's Patch entirely. Its access
policy is described in [Paw's Team](docs/paws-team.md). Mod authorship is separate
from this launcher and its patch.

The current signed catalogs are `feed/v2/stable.json` and `feed/v2/beta.json`.
Legacy `feed/stable.json` and `feed/beta.json` retain the previous game packages and
only advertise the new launcher. Updating an older standalone EXE/ZIP migrates the
official sidecar URLs in memory; custom feeds and signing keys remain unchanged.
Both catalog generations must receive future launcher updates. Publish assets and
verify them before promoting any signed catalog.

## Legacy release layout (before 0.7.0)

- `arcane-wars`: required base module.
- `pawpatch-core`: required Paw's Patch data and the default runtime launcher.
- `localization-ru`: optional Russian localization.
- `player-colors`: optional 49-color multiplayer selection, available in Release and Beta.
- `desync-continue`: optional out-of-sync bypass. It skips detected mismatches, including serious ones; it does not repair divergent game state.
- `common-ui`: mandatory terrain-startup, random-map/time, version/zero-display fixes and all seven company-badge models with soft shading.
- `roaming-profile-*`: mutually exclusive overlays for standard/×2/×4 timing and original/additional roaming-company sets.
- `siege-balance-standard`: restores the original Arcane Wars siege costs, damage and attack parameters when Paw's balance is disabled.
- `powers-shards-original`: restores Arcane Wars Powers and Shards when their default-on removal switch is disabled.
- Large maps remain always enabled. The legacy `large-map-sizes-standard` archive is not selected by current launchers.

The default core profile keeps independent hostility, ×4 roaming frequency, additional roaming companies, Paw's siege balance, and the two large map sizes enabled. Small higher-priority overlays restore the original behavior when a setting is disabled, so switching an option does not require reinstalling Arcane Wars.

## Update model

1. A small signed channel envelope is checked at startup.
2. Archives are downloaded from the first available mirror and verified by SHA-256.
3. Each archive contains `module.json` plus a `payload` directory with per-file hashes.
4. Packages are extracted with path traversal protection.
5. Enabled modules form an ordered overlay. Disabling a module reapplies the next lower layer instead of blindly deleting files.
6. Installation is staged and rolled back if a copy fails.
7. Launcher updates preserve the previous executable and require a startup acknowledgement. The independent helper automatically restores a failed update.

The Release and Beta channels use separate signed feeds. Release remains patch 0.2.0; Beta 0.3.0-beta.1 adds the mandatory [city assistant](game/city-assistant/README.md) and an in-game warning for desync bypass. There is no separate launcher component switch for the assistant; its F1 checkbox still controls automation during a match. Every optional switch is independent, including colors with independent hostility OFF and with either desync mode. Native startup uses eight compiled variants; it does not silently enable another option. Old pinned feeds retain their genuine helper-availability restrictions. Installing or switching a channel downloads every settings variant into the verified local cache. Changing switches after that is a local overlay operation performed before launch, not a new patch update. The internal `stable` ID, `stable.json` URL and `PAW-STABLE` configuration codes are retained for compatibility.

The installed-patch label describes the last successfully applied version and channel, not the channel currently selected for update checking. It changes after installation/reconciliation succeeds. See the [Beta validation record](docs/release-030-beta1-validation.md).

The current Release and Beta feeds carry the same About guide, authored in `feed/patch-guide.json`. The existing Always included, Configurable and In Beta sections describe availability; selecting a patch channel must not hide another section's documentation. Run `tools/SyncPatchGuide.py <new-staging-directory> --apply` to sign the shared guide into both current feeds, then validate with `--verify-shared-guide <repository> <staging-directory>` before publishing. Documentation-only changes preserve package hashes, the installed release identity and launcher version. Historical pinned feeds retain their original documentation; `feed/patch-guide-beta.json` is an identical compatibility mirror, not a separately authored catalog.

The active channel is checked at startup, after a channel switch, and once per minute while the launcher remains open. The main action reads `Install`, `Update <channel>`, or a disabled `Installed` according to the actual state. Launcher self-updates run automatically at startup and remain available through a visible button during the session.

From launcher 0.6.0, launcher availability is session-wide and independent of patch
selection. Both signed channel endpoints and their configured mirrors are checked
for the highest launcher version. A stale response, failed source or pinned patch
cannot erase an already-discovered update. One working source is sufficient even
if another fails; if all sources fail the failure is not reported as "no updates".
Launcher-only checks do not archive or apply gameplay packages. Manifest requests
ask HTTP caches to revalidate; signed metadata and verified downloads stay mandatory.

Version 0.5.0 adds persistent patch rollback, configuration import, an exact multiplayer file comparison, working-settings recovery, crash/unclean-exit diagnostics, critical launch checks, resumable downloads, unread changelog markers and pinned previous Beta releases. See [reliability behavior and validation](docs/RELIABILITY.md).

Launching the game also reconciles the selected channel and every component setting first. A failed update prevents the game from starting with a partially applied configuration.

Gameplay options that affect multiplayer produce a compact configuration code. Players can copy it before a match and compare codes to catch mismatched settings. The diagnostic archive command collects available logs, sync logs, dumps, launcher state, module versions and SHA-256 hashes; crash dumps should be reviewed before public sharing because they can contain memory fragments.

Every installed module records its complete file list. Files dropped by a newer version are removed automatically, and a package can additionally contain explicit removal entries for legacy manual installations. Original files are backed up and restored transactionally when appropriate.

No private signing key belongs in this repository or in a public release.

## Window placement

Version 0.6.4 applies a larger 1600 × 1000 default, bounded by the available screen, once to legacy window geometry. Later resizing is remembered normally; the selected monitor and language are retained. This migration uses its own layout revision and does not reset component settings.

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

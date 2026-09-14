# Paw's Patch for Vanilla and Immortals

`build_channels.py` builds both scoped patch channels. It writes local archives
and verification evidence; it does not change feeds, publish, install, attach
to the game or launch one.

| Channel | Public patch / data package | Runtime package | Native transfer |
| --- | --- | --- | --- |
| Stable | `0.1.1` | `1.3.72-pure.6` | Stock |
| Beta | `0.2.0-beta.1` | `1.3.72-pure.7-beta.1` | Built-in R2 |

Both retain the accepted badge assets, display-only negative-zero correction,
terrain initialization and menu version label. Beta inherits Stable and adds
only R2. Neither imports Arcane Wars city automation, balance, maps, palettes,
diplomacy, random-time selection or synchronization bypasses.

## Controls and language layers

The data package copies the verified current Arcane Wars **Dvorak profile**:

- W/A/S/D press/release bindings move the camera.
- F runs `GoToTeamCommands; SelectTeamKingdom; TeamCommand team_explore` to
  select the allied map marker.
- The old A action-button binding is removed because A moves the camera.
  Every other positional Dvorak action and formation binding is preserved.
- Original arrow press/release bindings remain in `hotkeys_core.txt`.
  That file and all other input profiles are unchanged.

The game must have Dvorak selected for its bindings to apply. No UVars, user
configuration or active profile is changed by the package.

`pure-fixes-data` contains exactly 16 files: the original fourteen badge
NIF/TGA assets, byte for byte, plus the same Dvorak text at
`data/Localization/Hotkeys/Actions/hotkeys_visual_dvorak_k2.txt` and
`Local_base_ru/Localization/Hotkeys/Actions/hotkeys_visual_dvorak_k2.txt`.
The second path overrides the separate Russian profile when Russian text is
selected. Its presence alone does not select Russian or change game text.
Stock and Russian arrow bindings are verified separately; unrelated legacy
Russian debugging shortcuts are retained.

The builder verifies source archives and every contained file against current
`feed/v2/stable.json`, compares the profile to stock `Data.rwd`, and requires
exactly nine added bindings and one removed A binding. No other Arcane Wars
file is carried into these modes.

## Runtime, channel composition and validation

`PAW_PURE_CHANNEL` selects the new runtime. Stable excludes R2 code and guard
resources entirely. Beta additionally defines `PAW_PURE_FAST_TRANSFER` and
compiles the same `../fast-transfer/FastTransfer.cs` core used by Arcane Wars,
with the pure runtime's path-verified memory interface. No city source is
needed. R2 retains the accepted 1200-byte file-stage budget, 16 packets per peer
per send pass, native wire format, block size, ACKs, retries and bandwidth
checks. R3 is not included.

All pure and R2 signatures and live transfer values `20/64/256` are checked
before either feature writes. The fresh game is suspended throughout the
transaction. If R2 fails, its hooks and the installed pure hooks are restored.
Uncertain rollback retains possibly referenced code; startup stops only its
verified fresh process. The existing menu-only hook remains separate.

The supported Steam executable, launch identity checks and tooling commands
are described below. Both helpers remain `k2_paws_pure_fixes_1372.exe` and keep
the existing Steam bootstrap through the selected `k2.exe`. `--features` now
includes exact package/public versions, channel and `nativeTransferRevision`.

Both package IDs retain `mods: ["vanilla", "immortals"]`, `required: false`:

- `pure-fixes-data`: priority 900, executable-independent, no dependencies.
- `pure-fixes-runtime`: priority 910, native, `dependsOn: ["menu-runtime"]`.
  Its Beta package is experimental. Retain the existing menu-runtime package
  and launcher-generated `paws_launch_versions.ini`.

With Paw's Patch off, neither pure package is selected. File-only mode selects
data and uses the stock executable; R2 is unavailable there. Game localization
remains independent. Changing channel replaces the same runtime path.

```text
python game/pure-fixes/build_channels.py --out <fresh-output> --dotnet <dotnet.exe> --analysis-work <verified-analysis-work> --archives <verified-public-cache> --rwd <stock-Data.rwd>
```

The analysis-work input provides the pinned plaintext 1.3.72 image and Python
dependencies. Generated R2 guards cover 15 regions / 1815 bytes. Each x86 .NET
Framework runtime is built twice and must be byte-identical; ZIPs are also
deterministic. Output `packages.json` has `{ "stable": [...], "beta": [...] }`
with local archive URLs for the parent feed composer. Per-channel folders
contain packages, module manifests, `features.json` and
`build-verification.json`; `mod-games.json` supplies scoped game requirements.

The existing base tests run on both channel builds. `ChannelTests.cs` adds
feature boundaries, checks before all writes, stable R2 exclusion and combined
rollback at every injected operation failure. Beta also runs the original
663 managed and 8421 R2 x86 checks through the shared implementation. These
checks do not establish a new WAN speed or visible acceptance; the parent
integration workflow records isolated launches and visible input checks.

## Historical two-hook baseline

The older `build.py` remains an isolated baseline build without menu or channel
features. The following specification documents that baseline only. The
historical local launcher review used `../menu-labels/build.py`. Its
`pure-fixes-runtime 1.3.72-pure.4` enables the separate menu-label block in
`Program.cs`, while retaining the two fixes below. The standalone baseline build
in this folder still excludes that block. `menu-runtime` is a distinct helper
with no engine fixes, used when the mod is selected and Paw's Patch is off.

This independent x86 .NET Framework helper applies exactly two guarded fixes to
the newly launched, path-verified Kohan II 1.3.72 process:

- The limit formatter receives `0` for an exact IEEE-754 negative-zero display
  value. Resource/capacity state itself is not modified.
- The object terrain-flatten caller initializes descriptor field `+0x1C` to
  `-1.0` after invoking the original constructor. The constructor return value,
  flags, floating-point state and RNG call sequence are preserved.

The stock out-of-sync marker and error-handler call are verified before and
after installation and are never changed. There are no game-rule, menu-version,
palette, diplomacy, map-selection, time-selection, hotkey, assistant or transfer
features. The helper does not read or modify language files; game language does
not depend on enabling these fixes.

`pure-fixes-data` is separate: the fourteen accepted company-badge assets from
`../release-assets` (seven NIF models and seven TGA textures). It contains no TGI,
executable or localization file. Its package is executable-independent.

## Packages and launcher integration

- `pure-fixes-data`, version `1.0.0-pure.1`, priority 900,
  `executableIndependent: true`.
- `pure-fixes-runtime`, version `1.3.72-pure.2`, priority 910,
  `executableIndependent: false`; contains only
  `k2_paws_pure_fixes_1372.exe`.
- Both have `required: false`, no dependencies, and
  `mods: ["vanilla", "immortals"]`.

For a selected Vanilla/Immortals Paw component, install the data package. Add the
runtime only when that mode's executable requirement matches and file-only mode
is not active. With incompatible executables keep the data package and launch
`k2.exe`; the runtime itself also rejects an unknown hash before launching.
With the Paw component disabled neither package is required. Game localization
is a separate choice/package in every combination.

The supported original executable is identified by its exact SHA-256:
`1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.
It is Kohan II 1.3.72 / Steam build 25068126; its PE FileVersion resource is
absent, so the helper does not rely on that resource or editable data strings.
Keep this requirement scoped to Vanilla/Immortals rather than inheriting future
Arcane Wars executable support automatically. `mod-games.json` is emitted for
that integration.

Supported commands:

```text
k2_paws_pure_fixes_1372.exe
k2_paws_pure_fixes_1372.exe --game-dir "C:\Path\To\Kohan II"
k2_paws_pure_fixes_1372.exe --features
k2_paws_pure_fixes_1372.exe --preflight "C:\Path\To\Kohan II"
```

Normal startup defaults to the helper's own directory. No attach mode exists.
The tooling commands exit before process enumeration or log writing and do not
launch the game. Runtime errors use a nonzero exit code and
`paws_pure_fixes_1372_status.txt`; there are no helper dialogs or console windows.
The helper stays alive until its game exits, so add its process name to launcher
game-observation checks. A failed partial install rolls both hooks back and
stops only the helper's verified, newly created process. Native process handles
are independently checked against the expected path and exact creation time.

## Build and offline checks

Run `build.py` with a new empty output directory, an installed .NET SDK's
`dotnet.exe`, and a Python dependency directory containing Unicorn:

```text
python build.py --out <new-directory> --dotnet <dotnet.exe> --native-deps <Unicorn-directory>
```

Optional arguments:

- `--original-ui-payload <PawCommonUiPayload.bin>` proves that the 47-byte zero
  handler is identical to the previously validated handler at its baseline
  relocation. None of the old menu payload is included.
- `--game-directory <Kohan II-directory>` performs only the hash preflight of
  that installation. It never launches or attaches to the game.

The build uses Roslyn with deterministic output and Windows .NET Framework
references. It compiles the runtime twice in distinct output directories and
requires byte equality. ZIP manifests/payloads are deterministic and verified
by hash. Existing package archives are never overwritten with different bytes.

`Tests.cs` tests both-hook installation, every injected operation failure,
rollback after partial writes, unknown-signature rejection before allocation,
ASLR, launch identity and unknown executable rejection. A separate inert,
hidden instance of the test executable checks native handle identity and
suspend/read/resume rights. It is not k2.exe and creates no UI.

`test_native.py` executes the exact C#-generated machine code in Unicorn. Tests
cover negative zero, positive zero, ordinary numbers, NaNs/infinities, 1,000
random bit patterns, poisoned terrain fields, register/FP/stack preservation,
write boundaries and calls to only the original formatter/constructor. The
remaining allocated bytes must be zero, proving no additional embedded feature
payload is present.

Build outputs include `packages.json`, `mod-games.json`, `features.json`, all
module manifests and `build-verification.json`. These checks do not replace
visual badge/HUD acceptance or real repeated-match/network validation. The build
does not install into a game, start k2.exe, open native windows, or publish.

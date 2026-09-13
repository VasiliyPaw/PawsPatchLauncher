# Pure fixes for Vanilla and Immortals

The current local launcher review also uses `../menu-labels/build.py`. Its
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

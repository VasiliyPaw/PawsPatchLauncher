# Mod and patch versions in the main menu

This local review adds `menu-runtime 1.3.72-menu.3` to compatible mod launches.
It launches the original, hash-verified `k2.exe` and installs only the existing
main-menu label hook. The original executable on disk is never rewritten.

- Immortals and Arcane Wars without Paw's Patch use the menu-only helper.
- Independently enabled Arcane Wars native components keep their selected
  features and use the same menu-only presentation path.
- Vanilla/Immortals with Paw's Patch use `pure-fixes-runtime 1.3.72-pure.5`:
  their two existing engine fixes plus the separate menu label.
- Original Vanilla with Paw's Patch off uses the original executable.
- Unsupported game builds select `k2.exe` and omit all native packages,
  including the menu-only helper and layout overlay.

The launcher writes `paws_launch_versions.ini` from the applied, signed release
immediately before starting a supported custom helper. This generated metadata
is separate from the immutable `paws_patch_versions.ini` used by older AW cores.
Mod names are an enum; version values, channel and size are constrained. The
launcher and runtime both validate them. An off patch never produces a Paw
version line. Existing signed AW core helpers retain their existing version UI.
The menu shows the patch version without a parenthetical Release/Beta suffix.
The channel remains validated in launch metadata and available in the launcher.

The package has only two files: the menu helper and the original `main.tgi`
layout with its version label moved up to make room for four lines. It does not
add palette, diplomacy, negative-zero, terrain, map-selection or transfer fixes.

`build.py` verifies its signed input feeds, builds reproducible menu/pure helpers,
executes `Tests.cs` against disposable allocations in its own process, compiles
the eight coreless AW helpers and signs local review feeds with the provided
test key. The 126 native checks cover metadata, all applicable mod/patch/channel
combinations, actual hook installation and the untouched negative-zero site.
No game is started by that build. Real-game smoke checks are separate.

Nothing is uploaded or published by this workflow.

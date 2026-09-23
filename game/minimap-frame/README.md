# Minimap frame fit r1 — Arcane Wars beta.9

The 1024x768 stock UI gives `GameMiniMap` a 240x240 view at (15,12)
relative to a 256-pixel-high control panel. The panel artwork stretches with
the screen while the rendered map remains square. At 16:9, this leaves dark
side gutters inside the racial diamond frames. The user's 2560x1440 images
provide the reference geometry; no game launch is needed for this asset edit.

This trial keeps the map's area, coordinates and controls unchanged. Six
ImageGen material plates, matched to the original racial art, are imported
only into the dark opaque gutters outside the map diamond. A small bevel
clarifies the boundary, including when the map is unexplored. Original visible
art, alpha values and all pixels inside the actual map diamond are preserved.

Scope: Human, Gauri, Drauga, Haroun, Undead and Shadow; stock UI, UI/800 and
UI/1280 texture variants (18 uncompressed 32-bit TGA files). No executable,
layout, localization, save or simulation change. Beta.9 includes these exact
18 accepted files in common-ui, alongside the separately built lair survivor r3.

## Display scope

These assets are fitted to **16:9**, including 2560x1440 and 1920x1080. Do not
claim fitted support for 4:3, 16:10 or ultrawide screens. The user explicitly
requested static file replacement for this release and rejected resolution
handling in the EXE on 2026-09-16. There is no resolution detection, adaptive
renderer, launch-time texture generation or file replacement in the helper.
The release notes and patch guide state the 16:9 scope. The local preview
installer performs no UI work and never starts or stops the game.

## Reproduction and evidence

Workspace artifacts: `outputs/minimap-fit-test/` under the root workspace,
two directories above this repository. `source/` contains the exact racial
backgrounds extracted from the installed RWD archives. `materials/` contains
the six built-in ImageGen outputs; `generation-specs.json` records each prompt
and generated file. This is asset integration, not an AI-generated gameplay
screenshot. The comparison pages render actual old/new TGA pixels and reuse
the same minimap contents from the user's screenshot.

Compile `BuildMinimapAssets.cs` with .NET Framework csc and System.Drawing.
Run it with the artifact directory, aspect `1.7777777777777778`, and the
2560x1440 `k2_Thb7gCnvE5.jpg` reference. The importer validates TGA layout and
checks that changes remain outside the map, inside the old dark hole, with
all alpha values unchanged. `assets.tsv` records source/result SHA-256 hashes.

`Install-MinimapPreview.ps1` installs precisely the 18 listed textures as loose
racial skin overrides, saves existing files first, refuses unreviewed custom
frames, verifies installed hashes and protected EXEs/archives/settings, and
rolls back if installation fails. `installed.json` identifies the exact backup
receipt. `Restore-MinimapPreview.ps1 -ReceiptPath ...` restores only those
paths and refuses to overwrite any later edit. No recursive deletion is used.

The preview is not evidence of in-game rendering. User checks still required:
all six races, fog at the four diamond corners, minimap camera clicks, supply
toggle, pause, chat and menu controls. Geometry is unchanged, but runtime asset
loading and final appearance have not been verified in this turn.

## Observer assets, September 23

Pass `--observer` as the third importer argument to build the three unskinned
`data/UI[/800|/1280]/Game/ControlPanel/Background.tga` overrides. The default
observer background is Human stone; the stock 800/1280 alternatives are Gauri
stone and reuse that accepted material plate. The importer preserves all alpha,
the actual map diamond and the surrounding visible artwork, as for racial skins.
This extends the same static 16:9 fit; it does not alter map coordinates.
Artifacts and pixel/hash evidence are in
`outputs/capture-observer-button-r31-20260923` at the workspace root.

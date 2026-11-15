# Local engineer road prototype — drag revision, 2026-10-12

Run `work/roads-drag-20261012/PawsRoadsTest.exe` from the project root. This starts a separate stock 1.3.72 copy with private data and saves. Nothing is installed into the normal game, Documents/Kohan2, or a public channel.

## Try it

1. Start the helper and launch the separate test game.
2. Single Player → Custom → floppy icon → **Engineers-ready** → Load → Launch → Continue. The lobby may already remember this save.
3. Select the engineer company and click **Строить дорогу** above the lower-right panel.
4. Hold the left mouse button at the road's start, drag to its end, then release. Engineers approach the start and build the planned straight segment gradually. Ordinary movement never paints roads.
5. Right click or Esc cancels an unconfirmed plan. The road button stops an active task; an ordinary right-click order also replaces that task.

The existing **Drag-road-built** save in the local output contains the verified first road. Engineers-ready has one human engineer company on a flat 192×192 editor test map. The native editor saved this fixture; it does not need the original temporary RMP. The player kingdom's race is Haroun, while the deliberately placed test company is Human.

## Rules and coverage

The eligible workers are the six stock engineer definitions: engineer, caretaker, forge, crafter, nightbringer, boneweaver. Pioneers are excluded. A living engineer must be in the selected player's own company. Each company has one planned segment; there are eight simultaneous task slots.

The dedicated `paws_engineer_road01` terrain uses **PawsCobble.tga**, separate from stock dirt roads. It gives **+20% of base speed** through a native terrain property. In the live test the company moved at 2.25 on grass and 2.85 on the new road. The bonus does not accumulate when roads overlap.

Completed terrain saves and loads through the native save format. Unfinished plans/tasks are session-only: after loading, issue a new plan. Planning uses continuous grid lines independent of mouse event frequency. Native markers preview the segment during dragging. Impassable tiles/water and a safety margin block the plan; no terrain elevation is changed.

EN/RU/DE/FR/CS/UK road controls are prepared. The separate stock game's remaining UI is English. The prior climate/shape controls are retained.

## Current boundaries

Local single-player only; no multiplayer/replay integration, bridge construction, AI planning, costs, dedicated work animation, or multi-segment/freehand queue. Prototype maps are limited to 1024 world units. The live test uses a small flat map; large-map performance and visual quality on other climates have not been established. Terrain texture dimensions and road width are provisional.

## Build and checks

From the launcher checkout, using the bundled Python, TinyCC and C# compiler:

```text
python -B game/engineer-roads/prepare.py --game <stock-game> --out ../roads-drag-20261012
python -B game/map-shapes/build.py --out ../roads-drag-20261012/native --compiler <tcc.exe> --menu --roads
csc /target:winexe /platform:x86 /warnaserror+ /r:System.Drawing.dll /r:System.Windows.Forms.dll /r:System.Web.Extensions.dll /out:..\roads-drag-20261012\PawsRoadsTest.exe game\map-shapes\MapTest.cs
python -B game/engineer-roads/test_roads.py --out ../roads-drag-20261012
python -B game/engineer-roads/test_assets.py --game <stock-game> --out ../roads-drag-20261012
python -B game/map-shapes/test_native.py --native ../roads-drag-20261012/native
python -B game/map-shapes/test_menu.py --out ../roads-drag-20261012
python -B game/engineer-roads/validate_live.py --out ../roads-drag-20261012
```

Native compiled regressions cover engineer identity, mouse-release planning, all line directions, water margins, ownership/lifecycle, cancellation, approach without painting, command ABI and relocation. Live evidence covers gradual construction, no painting during ordinary movement, road/grass speed, exact terrain/elevation save-load, and new construction after loading. Active-task cancellation is covered by compiled tests; the live right-click samples captured ordinary movement after short segments had already completed.

Two integration defects found in native testing were fixed: movement now uses ActorCommand validation/execution on the local simulation thread instead of SAIPlayer's incompatible queue layout; the new terrain is appended to the explicitly loaded stock terrain file with all required names. A standalone new TGI filename is not automatically scanned. Stock road definitions remain intact.

See `validation.json`, JSON snapshots and `road-in-game.png` in the output directory for measured results. No release has been published.

## Texture provenance

The built-in image-generation tool produced `assets/PawsCobble-source.png`; the runtime asset is a 256×256 RGB TGA export. Prompt is recorded in `assets/prompt.txt`. The texture was inspected in the running game. It is an initial material, not final art.

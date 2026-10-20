# Integrated widescreen UI (Kohan II 1.3.72)

Ensrick identified the stock `WidescreenUniformUI` setting (PR #14). The beta
helpers enable its aspect calculation inside Paw's Patch while the current
application-state object has the verified `KKC_GameAppState` vtable, without
changing the user's saved UVars or adding a launcher switch.
Menus, lobby and startup movies use the stock coordinate system. The native
setting-change poll recalculates the canvas on screen transitions. During a match
the UI width is at least 1024
logical units, so 4:3 and narrower screens retain the original widget grid.
World rendering, simulation, keybinds and localization are unchanged.

`GamePresentation1372.cs` guards all three native sites before writing: the
aspect branch, a minimum-width clamp, and the stock main-thread setting-change
poll. The latter handles attachment after the first resolution calculation.
Failures restore attempted patches; no generic assertion skipping is involved.
Core-less Arcane Wars helpers do not enable the feature.

The stock background would stretch even with uniform UI enabled. A fixed-width
panel was rejected during visual QA because it left the entire HUD on the left.
The earlier beta used `DecalVETiledHorizontal`. Both it and the first ordinary
decal replacement swallowed clicks above the visible panel. Native picking
checks client rectangles, not texture alpha. All three decorative decals now
explicitly use `client_T = 183b`, preserving the stock panel client band while
their full artwork remains visible. The local replacement uses three ordinary
`DecalVE` elements:

- Lossless crops of the original atlas halves anchor the minimap left and
  commands right, retaining the original pixels and transparency.
- A two-column lossless crop of the original centre fills the extra width.
- Side-panel tabs and action buttons anchor to the right; the object display
  fills the middle. At width 1024 all original coordinates remain unchanged.
- All six racial skins and the observer skin have all three stock atlas sizes.
- Arcane Wars retains its original compact company-member spacing; that mod's
  layout is separately pinned and only its right edge anchor is changed.

The 21 former loose minimap-frame filler textures are retired only in these
beta packages. Stock backgrounds remain in their original RWD archives.

Build the 66 resource overrides from owned stock archives (no game launch):

```powershell
dotnet run --project game/widescreen-ui/BuildAssets -c Release -- STOCK_GAME game/widescreen-ui/source-assets.json NEW_OUTPUT ARCANE_ORIGINAL_OBJECT_DISPLAY
```

The builder checks every source SHA-256, TGA encoding, crop row and layout
anchor. `source-assets.json` pins the supported retail resources. Outputs are
three layouts, 21 small TGA strips, 42 atlas halves and a hash manifest per mod family.
`test_panel_alpha.py ASSET_OUTPUT` verifies transparent world/button positions
and opaque panel positions across all skins and texture variants. It does not
substitute for live picking/selection acceptance.
`test_panel_picking.py --legacy RESEARCH_ROOT --assets ASSET_OUTPUT --out REPORT`
executes original GroupVE and VE picking against a minimal widget tree at
three image bases and ten resolutions. It reproduces the old obstruction,
then verifies field/button routing and preservation of minimap, pause and
opaque-panel hits using client bounds parsed from the generated layouts.
The equivalent three-rectangle change in the user's running test match was
manually accepted on 2026-10-20; restart acceptance of the persisted asset
remains separate. The beta staging
tool checks this manifest, preserves unrelated payload bytes, and requires
live UI, native and installation/rollback evidence before feed promotion.

`test_native.py --legacy RESEARCH_ROOT` emulates actual stock executable bytes
at three ASLR bases, nine dimensions and both saved flag values. Native
presentation composition tests exercise the guarded patches and rollback.

Revision 2 also uses `button.tgi` for the beta Paw's Patch button. Its square
56-unit frame sits six units above the visible lower bar; the tooltip
follows the logical right edge. `prepare_button.py` updates only this widget.
`test_phase_button.py` emulates the emitted C# app-state and tooltip payloads.
The engine run phase at RVA `0x5f9218` does not distinguish menus from matches:
the first local candidate used it incorrectly and failed manual acceptance.
The current candidate bounds the index at `0x5f92f4`, reads the native state
table at `0x5f92b4`, and compares the state object's vtable with RVA `0x48d0dc`.
The native test verifies that vtable's RTTI as `KKC_GameAppState`.
Pass `--emitted PRESENTATION_TEST_FIXTURE` to `test_native.py` so it tests the
actual C# payload rather than a duplicated implementation.
Legacy builders retain the original gold-button asset.

`prepare_local_test.py` creates an isolated Arcane Wars copy and private user
settings for manual acceptance. Compile `ManualTestLauncher.cs` into that
fixture; preparation does not launch the game. Revision 2 is a local candidate:
visual checks of menus, movies, match transitions and button clicks remain
required before release.

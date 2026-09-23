# Local gold-mine sound button

`prepare.py --game <installed root> --out <artifact directory>` appends an
independent `PushButtonWidget` child to the existing Game interface and copies
the user-provided PNG byte for byte. It refuses a duplicate button. The input
interface hash and resulting hashes are recorded in `button-input.json`.

The button occupies x=960..1020, y=490..570 in the 1024x768 virtual interface,
above the lower-right command panel (right offset 4, bottom offset 198).
At 2560x1440 the frame is 150x150 and its image is 145x145 pixels,
preserving the annotated Haroun artwork's square ratio on the user's 16:9 viewport.
The source is the 1254x1254 generated edit with two red arrows and a circle.
No tooltip name or body is set, so hovering does not open a tooltip.
It does not consume a native action slot. It is not nested under the ally or
selected-object controls, so its definition is available in solo and observer
interfaces as well. The complete image is used, without cropping.

Kohan constructs the widget hierarchy in code. `GamePresentation1372.cs`
therefore hooks the Game UI constructor at RVA `0xC772E`, preserves its original
virtual EconomyBar attachment and attaches one native PushButton to the Game root. This hook
is installed only when both the layout section and PNG exist; old packages and
menu-only launches retain their original hook set. No running match is patched.
The Game owns and destroys the button. Failed attachment deletes it immediately.
A private copy of the native vtable makes programmatic Activate a no-op, because
the original implementation assumes a non-null action; mouse handling is native.
Its normal zero sort key and early creation put it after VWorld and before
SidePanel and ControlPanel. Thus F1-F4 panels cover it and take input first.
The former separator position required a 1.0 key to avoid being covered by the
bottom ControlPanel; that key must not be used at the new position.

`build_native.py --analysis <readable 1.3.7.2 analysis> --out <proof directory>`
rebuilds the common payload while checking and retaining the original formatter
and menu bytecode. `test_native.py` covers relocated x86 calling conventions,
FP/SSE preservation, attachment/deletion and the game's original click code.
`PresentationTests.cs` checks installation into disposable process allocations,
including menu-only and missing-asset combinations. Neither is a rendering test.

Native `ButtonWidget.set_sound = resource_gold_select` points to the same
Audio definition used by a gold mine's selection event. No command, network
message, simulated action or per-frame callback is added. Native focus/pressed
border textures supply the button states; releasing it is silent.

Source/asset inspection does not prove live widget loading or audible playback.
Before marking runtime acceptance, check solo, team and observer matches,
click sound, pressed appearance and neighboring native command buttons.

# Local gold-mine sound button

`prepare.py --game <installed root> --out <artifact directory>` appends an
independent `PushButtonWidget` child to the existing Game interface and copies
the user-provided PNG byte for byte. An existing button definition is replaced without creating a duplicate. The input
interface hash and resulting hashes are recorded in `button-input.json`.

The button occupies x=980..1020, y=516.666667..570 in the 1024x768 virtual interface,
above the lower-right command panel (right offset 4, bottom offset 198).
At 2560x1440 the frame is 100x100 and its image is 95x95 pixels,
preserving the annotated Haroun artwork's square ratio on the user's 16:9 viewport.
The source is the 1254x1254 generated edit with two red arrows and a circle.
The tooltip contains only the `Paw's Patch` heading in every language.
An empty body makes the native formatter skip paragraph separators. The old
localized body key is removed from all shipped language tables.
The native tooltip rectangle hook at RVA `0xC88BD` identifies this button by
its private vtable, measures the formatted heading width with the native text
function at RVA `0x1B0F17`, adds the current tooltip horizontal padding, and
uses the original rectangle layout to fit its height above the button at
virtual y=512. It restores the
interface's original anchor fields immediately after measurement; every other
widget retains its native tooltip placement. `test_tooltip.py` checks this
wrapper and restoration at three ASLR bases with native measurement stubbed.
`test_tooltip_layout.py` also runs the original rectangle calculation with
three font metrics at each base and checks a single-line fitted rectangle.
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

Native `ButtonWidget.set_sound = paws_gold_button_select` uses the same gold
mine WAV through a separate AudioFeedback definition (`audio.tgi`). Explicit
`control_flags = NULL` and `simultaneous_limit = 64` allow overlapping presses
without interrupting earlier instances or adding a click cooldown. Available
engine audio channels still bound playback. The normal gold mine selection
sound is unchanged. No command, network
message, simulated action or per-frame callback is added. Native focus/pressed
border textures supply the button states; releasing it is silent.

Source/asset inspection does not prove live widget loading or audible playback.
Before marking runtime acceptance, check solo, team and observer matches,
click sound, pressed appearance and neighboring native command buttons.

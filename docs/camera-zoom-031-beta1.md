# Arcane 0.3.1-beta.1 camera integration

The requested limit is **2**, replacing the earlier experimental 2.5 setting.
The eight Arcane helper variants embed the same guarded native detour. There
is no camera companion process, memory scan or polling loop. The stock Steam
executable is unchanged on disk. Use `game/beta7/build.ps1` with
`-CityAssistant -LobbyCompatibility -LairRecovery -CameraZoom`, the verified
legacy work directory and the existing x86 TinyCC compiler.

The detour replaces the eight-byte `movss xmm0,[edi+0x20C]` at RVA 0x175D2D.
Installation validates the complete clamp block starting at 0x175D20 and four
KKC_Camera vtable methods. The installation runs suspended, only in the fresh
game process whose path, start time and stock executable hash were verified.
Writes are checked, instruction caches flushed and partial installs rolled back.

The native code requires the exact KKC_Camera vtable, gameplay minimum 0.5,
near plane 1, FOV 15, maximum 1.21 or 2, and far plane 512 or 1024. It changes
only that object's maximum to 2 and far plane to 1024. It restores flags,
replays the displaced instruction and resumes the native clamp. Thus new
gameplay cameras are handled automatically without relying on heap addresses.
Global far plane, interface cameras, current zoom calculations and save format
remain unchanged. The far-plane adjustment matches the scoped manual test;
the abandoned global-far override is not included.

Validation without launching the game:

- 138 installation/rollback checks, including partial writes and unknown code.
- 5,976 emulated clamp cases at three image/allocation layouts, using the
  compiled payload and 693 relocated camera records from the three captured
  near/far snapshots. Register, flag, SSE, object and active stack state are
  compared against the original clamp with the expected limits.
- All existing native city, transfer and lair tests, plus the eight helper
  variants' offline self-tests.
- The normal launcher regression suite and isolated installer/preflight
  matrix cover all six text languages and eight native option combinations.

The integrated hook has not received a new live-game acceptance run. Previous
manual camera tests established the camera fields, but are not a substitute
for live acceptance of this integration. The currently running game is not
attached to, relaunched or updated by the publication procedure.

Publication changes only four Arcane beta archives, their signed beta feed,
patch guide and changelog. Every non-EXE payload byte except the patch version
file is required to match the previous beta. The stable feed, other mods,
localization hotfix archives, and launcher 0.8.3 remain unchanged.

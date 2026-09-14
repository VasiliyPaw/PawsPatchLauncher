# Arcane Wars Beta 5 graphics workaround

The release carries the exact two payloads used in the successful local replay:

| File | SHA-256 |
| --- | --- |
| d3d9.dll (11,264 bytes) | 94A0EC76C89F2122712C04D8F276E853C20670A0EEC000BC55F67DCC1E464E2E |
| data/Units/Human/Ranger/RangerDie1.KF (14,564 bytes) | 990CF3DDADD764A12126768FDEC606C8469A7C0C19AD55252F94301475A8A781 |

`graphics_guard.c` is the tested v2 source, unchanged. The DLL forwards D3D9 factory creation to the real system library. It checks bound index-buffer size before each indexed draw. A rejected draw returns success without submitting invalid geometry. This is a rendering workaround, not a repair of the engine's geometry producer. It does not modify Windows DLL files, game logic, save formats, DRM or networking.

The game replaced its device vtable after its first draws, so v2 installs a process-local method-entry hook. Installation requires the real system module, eight-byte alignment and the exact `8b ff 55 8b ec` prologue; replacement uses an aligned atomic compare/exchange and an executable trampoline. If those checks fail the hook is declined and logged as `entry_guard=0`. Other graphics wrappers are not chained. The installer preserves unrelated existing files through its ordinary original-file backup mechanism.

The tested match ran for over 25 minutes including menus. Its captured counters were 123,440,441 checked draws, 22,705 rejected draws and zero unchecked draws. The user completed the match without another crash or visible artifacts. These are draw counts, not counts of individually prevented crashes. Detailed rejected samples required exactly 131,072 bytes more than their buffers, suggesting an engine index-count truncation; the producer instruction has not been fixed. Only the current Windows/NVIDIA machine received this gameplay validation; multiplayer and other GPU/OS combinations remain beta coverage.

## Rebuild and validate

Use official TinyCC 0.9.27 win32 (`https://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win32-bin.zip`, archive SHA-256 `02E2BFE8C272A549B15E4BFA4507BD7E05304692AF1761DB6C1E8E88AF675651`) and Python 3:

`build.ps1 -Compiler <tcc.exe> -Python <python.exe> -Output <new-output-directory>`

This builds the proxy and runs 20 offline cases plus a hidden-window real D3D integration test covering valid/invalid draws and vtable replacement. It never launches Kohan II. The COM slot constants were checked against the public mingw-w64 d3d9.h declarations. `prepare_guard_exports.py` fixes stdcall export names in the newly built owned DLL; optional `--game-exe` checks the game's imports read-only.

`build_ranger_candidate.py <original-RangerDie1.KF> <output-KF> --pyffi-path <PyFFI-2.2.3-directory>` requires the stock asset hash `1BDBEBFAF0D6272EAE094C1DCE75F5DC3B6530A18E0661F43A5C549F8D4BC493`. It removes only track 9 (bow material self-illumination), verifies the remaining 26 movement tracks byte-for-byte and preserves all animation events. No original assets, saves, dumps or personal diagnostic logs are committed here.

Only `pawpatch-core` gains the two payload files. `common-ui` changes only `paws_patch_versions.ini`. Existing helper executables and their beta.4 build identifiers are deliberately unchanged: this release contains no helper logic changes; the active patch label comes from the version INI. Stable, Vanilla, Immortals, localization packages and launcher releases are unchanged.

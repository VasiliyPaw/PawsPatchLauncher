# Release 0.2.0 game startup helpers (Beta 7 lineage)

These are the patch-owned C# sources and native resources used for the quiet startup package. The original Kohan II EXE is not included or modified on disk. The supported game is 1.3.72, Steam build 25068126.

Build with Windows .NET Framework 4:

```powershell
./build.ps1 -OutputDirectory C:/PatchBuild/beta7
```

The output directory must be new. The script compiles eight x86 WinExe variants and runs their offline tests; it does not launch or install the game. Install through a matching signed 0.2.0 feed so map, UI, version and palette files are present. The historical directory name is retained for source continuity.

- All eight variants install the accepted terrain initializer and random-map selector.
- The mandatory common-ui package provides all four non-color startup variants.
- The optional player-colors package provides four variants: hostility ON/OFF crossed with official-handling/bypass. `SYNC_ONLY;PAW_COLORS` excludes family-hostility hooks without disabling colors.
- `--features` reports the compile-time switches without starting the game; package tests check them against the actual selected settings.
- Bypass remains an explicit setting and is not a substitute for synchronization.
- Runtime installation is restricted to a freshly launched, path-verified game process. A failed partial startup stops only that verified new process.
- Normal startup creates no helper window, console or child helper. Actual startup errors still receive an error message.

The color payload is the user-accepted r20 payload:
`CC23162A1313E5AC7FBAC8F1B2D13092CCADA550B4AB73F4FBD846688C9BDA6D`.
The random-map payload remains
`FC8AAE172AE11AE4E0C31CF4E3E27527738444737E1EAA7926086B51B1E6D46D`.

Native self-test flags and mock-memory checks are distinct from multiplayer acceptance. See the release validation record.

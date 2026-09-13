Original loose Steam files used when legacy adoption recorded them as absent.

Steam app 97130, depot 97131, manifest 827975205587039857, build 25068126.
Recovered from the user's pre-patch backup and checked byte-for-byte by SHA-1
and size against Steam's locally downloaded depot manifest on 2026-09-10.

| Path | Bytes | Steam SHA-1 |
| --- | ---: | --- |
| startup/autoexec.txt | 1264 | c3f6eeb72118197ef411196b4b7b479cca5a1850 |
| data/UI/Shared/options_dialog.tgi | 30687 | 6a74a4e2dc7b9b0dc06853c28758980c379fbdfa |

Restoration is gated by the matching k2.exe SHA-256 and never replaces a valid
recorded original backup. The options file is required by the Steam executable;
the older copy inside Data.rwd lacks AutoSaveOptionsPanel. These files do not add
Paw's Patch gameplay or presentation changes.

The six stock skins/*.rwd archives are checked against the same depot manifest.
Arcane Wars distributes these unchanged. They must be kept as originals even
when their hash also matches the mod. Legacy restoration recovers missing
original records from a hash-verified live file or cached Arcane Wars payload;
the large archives are not embedded in the launcher.

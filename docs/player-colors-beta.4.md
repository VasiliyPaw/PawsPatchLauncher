# Player colors 0.1.0-beta.4 (r14)

Beta-only module update for launcher 0.5.1; no launcher self-update required.

- Fixed the native multiplayer registry guard and first-entry Random caption.
- Gray markers for empty slots, without allowing empty slots to reserve colors.
- Random allocation uses a private shuffle of the finalized shared world seed;
  the game RNG and map generation are not modified. Explicit choices still win.
- Company badges retain 80% of their original shading, preserving depth.
- The 50-color palette, independent kingdom colors and Stable remain unchanged.

The package contains exactly 10 files: the tested helper EXE, palette INI, lobby
UI and seven badge textures. No removals or additional gameplay changes.

EXE SHA-256: `EAECD317C759DA5CAE16B87C9EF41EF110B25D55CDED27DDC7E1025302957A11`.
The accepted candidate passed 140515 actual-x86 emulator assertions, including
132 shared seed cases with different host/peer relocation bases. User confirmed
local operation. Two-machine Steam multiplayer and save/replay acceptance are
not claimed; this Beta is being published for that testing.

On both machines select **Beta**, **Latest**, and **Extended player colors**,
check for updates, install the module and use matching game/component settings.
The prior signed Beta feed is retained for rollback.

Publication checks passed: all 15 unique referenced current/historical assets
were anonymously downloaded and matched signed sizes and SHA-256; 136 launcher
assertions passed. The real installer downloaded the candidate, reconciled Beta
to Stable, removed Beta-only files, restored lower-priority content, then rolled
back to Beta and verified all managed hashes. Checks used an isolated temporary
directory, not either player's game installation.

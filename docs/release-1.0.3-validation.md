# Launcher 1.0.3 validation

The user authorized agent verification and publication on 2026-10-22.

- Final build: zero warnings/errors.
- Full launcher suite: 38,188 checks passed (includes the pre-existing local Arcane source tests; CI verifies the exact committed release independently).
- WPF UI checks: 81 per language, 486 total across ru/en/de/fr/cs/uk. The final run raises Click on the actual replacement button, checks the tooltip path, and exercises cancellation, invalid replacement, Undo, apply/reopen, overlap changes, ordering, game-running guards, capacity and replacement at capacity.
- All six final renders visually inspected at a 1050x680 launcher test-window size: no text/button clipping in the tested dialog.
- No game or VM was launched. Installer operations use disposable fixtures.
- Local evidence: task workspace outputs/launcher-103-20261022, build-final.log, tests.log, ui-final-LANGUAGE.log and custom-mods-enhanced-LANGUAGE.png. Earlier UI logs are not final evidence: an initial build hit a locked preview DLL; after it exited, the build and all six UI runs were repeated successfully in sequence.

Release EXE/ZIP verification, standalone window-start smoke checks and public signed-feed readback are recorded after publication.

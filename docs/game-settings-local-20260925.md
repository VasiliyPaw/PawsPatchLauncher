# Game settings — local candidate, 2026-09-25

This records the initially unpublished local candidate based on release 0.8.7. At that point the project version,
signed feeds, GitHub release, server schema and shared configuration format are unchanged.

## User-visible behavior

- Components has a gear button immediately after the channel controls, in all three mod modes.
- The modal uses the existing dark/gold theme and the shared ReleaseCombo template, including popup scrolling isolation.
- Resolution presets: 1280×720, 1366×768, 1600×900, 1920×1080, 2048×1152,
  2560×1440, 2880×1620, 3200×1800 and 3840×2160. No manual dimensions input.
  An existing nonstandard resolution remains selected and unchanged until the user chooses a preset.
- Additional settings: FPS limit, master/interface/world/speech/music volume, match timer and player colors on the minimap.
- English, Russian, Ukrainian, Czech, German and French UI.
- These are local game preferences. They are not stored in launcher UserSettings,
  configuration codes, friend configuration exchange or server presence.

## Persistence

The path resolves Windows' current Documents known folder and appends
`Kohan2/data/User/UVars.tgi`. Save updates only explicitly edited variables.
Comments, unknown settings, hotkey profile, untouched numeric precision, line endings
and supported original encoding are preserved. Missing files receive only explicit selections.

Saving an existing file uses a flushed temporary file and atomic replacement, with an
exact original backup in the adjacent `PawsLauncherBackups` directory. The game must be
closed. Process state and original file contents are checked twice; detected external
edits, file locks, malformed files and IO failures do not silently overwrite the file.
Cancel and Escape leave the file unchanged.

## Validation

- Full Release console test suite: **PASS 27322**, plus the separate **AI_OPTIONS_PASS 307**.
- Included game-settings tests: **152 PASS**, covering encoding/newline byte preservation,
  percent and precise volume values, atomic backups, missing/locked/oversized/malformed files,
  concurrent changes, game startup during save, preset validation and configuration isolation.
- WPF tests at the minimum 1050×680 window: **38 PASS per language** for all six languages.
  Russian rerun after the final error-handling check: **42 PASS**, also verifying native
  dropdown Escape handling, modal Escape, and an oversized file created during editing.
- WPF renders inspected for the button position, modal layout and open resolution list.
- Release build and standalone win-x64 publish succeeded.
- The real user UVars.tgi was not edited. Its before/after SHA-256:
  `B024F9AA54C7163F6E0AA1CEB00BD8E50838ED70BE27EA73C84256062572B782`.
- The game was not launched or restarted to test different display modes. Actual
  driver/game acceptance of each preset remains a manual check.

Logs and rendered previews:
`G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3/outputs/game-settings-20260925/`.

## Candidate EXE

`G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3/outputs/launcher-game-settings-test-20260925/PawsPatchLauncher.exe`

- Local build metadata: 0.8.7-local.1; file/assembly version: **0.8.7.1**.
- Size: **73,140,913 bytes**.
- SHA-256: `9CC092C5772A2CB2F0134AA8E65A924194D20D5526895DB20D9E884DC4537D4C`.
- The normal launcher profile is used when started without test arguments. Close
  another running launcher before opening this EXE because the normal instance is exclusive.
- Saving through this EXE updates the actual user's game preferences. No preferences
  are changed merely by opening the launcher or the modal.

The user subsequently authorized publication as launcher 0.8.8. See
`release-0.8.8.md` and `release-0.8.8-verification.md` for the published release.
Actual game acceptance of a chosen resolution is still distinct from the automated checks above.

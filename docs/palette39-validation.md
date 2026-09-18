# Arcane 0.3.1-beta.2 validation

Scope: remove original palette entries 6, 18, 20, 22, 24, 29, 30, 35, 37.
The 39 remaining entries preserve IDs, RGB bytes, names and order. Ten retired
colors (including the older Light Red) retain save lookup and reserved network
serialization; they are excluded from selection and random allocation.

Offline validation on 2026-09-18:

- Native participant/color execution: 37,753 assertions, 39 colors and Random,
  10 retired colors, two ASLR layouts, host/client/snapshot and seat ownership.
- Compact popup hook: 96 assertions; unrelated dropdowns, ABI and registers preserved.
- Compiled palette injection: 19,873 checks, eight helpers, six languages and
  two address layouts; visible/retired names, IDs, RGB values and order.
- Installation: 192 selections, eight helpers, 16 explicit preflights,
  144 frame checks, 11 upgrade/configuration/rollback/uninstall transitions.
  The 48-color beta upgrades to 39 and rolls back to 48. Save sentinel retained.
- Compiled release startup: 161 checks including accepted camera/lair payloads,
  supported game identity and rejection of mismatched game/patch versions.
- Full launcher regression suite: 26,848 checks; color captions: 61 checks.
- Full helper build passed city automation, economy, militia, save preferences,
  compatibility, transfer, camera and lair regressions.
- Nine accepted city/lair/camera native artifacts match the previous beta byte-for-byte.
- Reproducible color payload SHA-256:
  `92AE781BF115EA61683D2F0D45FDCB7B25CBB61187A45535E0D18A99C9CD778F`.

No game was launched. The main Steam installation was read only (original
executable copied into an isolated preflight fixture), never modified.
Live rendering and remote multiplayer gameplay were not retested in this turn.

Publication changes four Arcane-only packages and its beta guide/history/count.
The stable feeds, legacy feeds, launcher release and other mods' packages are
unchanged. Launcher 0.8.4 uses one short count caption per channel; its pure-beta
caption can consequently say 39 although the pure palettes and mod-specific
help remain 48. Fixing that per-mod caption requires a future launcher update.

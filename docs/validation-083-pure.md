# Launcher 0.8.3 and pure patch channels: validation

Validated on 2026-09-16 against the supported Steam Kohan II 1.3.72 executable.
Its SHA-256 is `1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.

## Automated checks

- Launcher suite: 26,830 assertions, including 355 pure-option cases covering both mods, every option/master/file-only combination, independent preferences, configuration import and old catalogs.
- Real WPF controls: 232 checks across both mods, both channels and RU/EN/DE/FR/CS/UK. Master-off clears and disables the optional switches; unsupported-EXE state blocks both. Arcane Wars-only cards stay hidden.
- All pure guide titles/bodies have catalog translations for DE/FR/CS/UK; RU/EN are built in.
- Five native helper variants compile reproducibly, byte-identically on two builds, and pass exact-game preflight.
- Per channel: 211 baseline checks; 998 channel checks, including 663 R2 checks; baseline x86 emulation; 8,421 native transfer checks.
- Desync hook: 339 managed checks for signatures, relocation and rollback, plus 1,000 executions of the actual C#-generated x86 stub checking return behavior, registers, flags, reason/counter and write bounds.
- Color payload/fixups and 48-entry palette reuse the accepted Arcane Wars beta.8 implementation. The pure menu starts from stock staging, without Arcane Wars map, kingdom or simulation changes.

## Observed game launches

Installed each selection using the launcher's transactional installer and package selector, then launched and inspected the actual game window through Computer Use. All eight beta combinations reached the main menu with the expected patch label and runtime diagnostics.

| Mode | Colors | Ignore desyncs | Text language | Result |
| --- | --- | --- | --- | --- |
| Vanilla beta | off | off | German | pass |
| Vanilla beta | on | off | French | pass |
| Vanilla beta | off | on | Czech | pass |
| Vanilla beta | on | on | English | pass |
| Immortals beta | off | off | Russian | pass |
| Immortals beta | on | off | English | pass |
| Immortals beta | off | on | French | pass |
| Immortals beta | on | on | Ukrainian | pass |

Both modes also reached the menu with stable 0.2.0; R2 installation was confirmed in runtime logs. Master-off launches succeeded for both modes and installed no pure patch modules or custom palette.

Steam Internet lobbies were created for both beta modes with colors and desync bypass enabled. Lobby name and player count were left unchanged. Compact color selection worked, and a multiplayer map loaded with the chosen color on the settlement flags and minimap. No second computer joined these checks. The final Vanilla helper was additionally checked after diagnostic-only refinements; its earlier map check used the identical gameplay payload.

This is launch, UI and native-hook validation, not a long multiplayer endurance test or a new WAN throughput benchmark. Ignore desyncs suppresses interruption; it does not repair divergence.

## Compatibility fallback

For each mod, a local signed fixture deliberately declared a different supported EXE hash. The real compatibility policy automatically selected file-only mode despite both optional features being requested. Both installations contained only data modules, with colors disabled and desync mode set to official, and launched successfully through stock `k2.exe`. No native patch helper ran. The actual game EXE remained byte-identical; this tests the mismatch path rather than claiming compatibility with an untested older executable.

## Test cleanup

Restored the five package identities present before this test series through the transactional installer and verified their files. Restored the original preferences and menu metadata byte-for-byte. All 40 protected save/policy files retained their original SHA-256 hashes, and stock `k2.exe` remained unchanged. The game was left closed. A maintenance-only restoration log message was made mod-neutral after its old Arcane Wars-specific key failed after successful restoration of a Vanilla installation.

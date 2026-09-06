# Player colors beta.5 and common UI ui.1

This release ships the byte-identical r15 candidate accepted locally by the user on 2026-09-06.

Local crash dumps 133-135 showed a null string in native kingdom permission checking after a color request. The previous request used player-object serializers as if they serialized strings. r15 uses the real native uint32 serializers for a tagged kingdom ordinal and a palette ordinal, validates both before resolving local strings, and rejects malformed/legacy payloads before permission checking.

The mandatory `common-ui` package provides mod-version labels and exact negative-zero display normalization in all five active launch helpers. The stock `k2.exe` is not changed on disk. When all optional features are off, launcher 0.5.4 selects `k2_paws_ui_1372.exe` if the signed channel requires this package. No simulation-resource or RNG values are written by these two presentation hooks.

The color package depends on `common-ui`. Priority 900 ensures the common helpers override old helper files supplied by core/desync packages. Stable receives the launcher presentation update only, not these Beta game packages.

Validation: 140,999 color x86 assertions; 12,289 common-UI x86 assertions; eight real-package launch-profile combinations covering five helpers; four clean-install/uninstall profiles; stock EXE and save sentinels preserved. The final helper revision additionally validates relocated absolute instruction operands.

All multiplayer peers require the same new build. Mixed r14/r15 compatibility is not supported. Exhaustive live multiplayer and save/load validation are not claimed.

Archives:

- `common-ui-1.3.72-ui.1.zip`: `BC91A73F79976C6C7D1D172D313A370BD1FAD7D07CE315422DE4302BD7BCEA6A`
- `player-colors-0.1.0-beta.5.zip`: `9A74C9877F0CFED47689B695FD5F09BD62A9F384FA0D7DF72DAF9705C0F391B1`

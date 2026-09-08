# Launcher 0.6.4 publication validation

The user accepted the local candidate and explicitly requested publication on 2026-09-09. Scope is the accumulated launcher changes documented in `release-0.6.4.md`; gameplay packages are not changed.

## Pre-publication

- Local source and origin/main started at `fd457e13a616a3e0b0db94653b705c57acee40ce`. No existing v0.6.4 tag/release.
- Both anonymously fetched production feeds have valid signatures, launcher 0.6.3, and the same signed payload/signature as the local baseline. Text-file line endings may differ.
- Downloaded public 0.6.3: SHA-256 `143EB6199DE1B4706B8C721EF0E63B6B54772BE032F130DE2EA0C901ABA4D829`, 72,262,340 bytes.
- Versioned 0.6.4 source: build with zero warnings/errors; core **PASS 8801**. Detached UI suites **61 layout + 104 chat/broadcast checks on each of RU and EN**, with generic layouts at 1600 × 1000 RU and 1050 × 680 EN.
- Tests use isolated files and mocked authentication/delivery. No live game, user settings or real conversation is altered. Prior manual acceptance and additional regression evidence: `validation-launcher-layout-refresh-20260909.md` and `validation-chat-activity-quick-save-20260909.md`.

## Published assets and feed promotion

- Source/tag commit: `52a85a6838d0e8933f283677fce2cd5a7365453c`, tag `v0.6.4`.
- GitHub Build and test `34288993403`: success. Publish launcher `34288994971`: success.
- Public release: https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v0.6.4 (not a draft or prerelease).
- Public EXE: **0.6.4.0**, **72,273,730 bytes**, SHA-256 `330A30E1D5C66A5EEECBF08201DDA3D45AD0B4CD32754D7D49F729B67AE9A76B`.
- Public ZIP: **66,866,260 bytes**, SHA-256 `8EBB4774A0D2021E52E47B414B1C5A36597BA6F5B53F77C05943C1308E01EBE4`. Anonymous downloads match GitHub asset digests. Archive contains only the identical EXE and unchanged production `launcher.config.json`.
- Published EXE startup: **SMOKE PASS twice**, including the standalone EXE with no sidecar configuration. No new launcher exceptions.
- **REAL SELF-UPDATE PASS: 0.6.3 -> 0.6.4** with actual public binaries in a disposable Unicode/special-character path. Replacement, old-binary backup and new-window acknowledgement verified. The user's running launcher was not closed or replaced by these checks.
- Additional versioned-source checks: account UI **113 RU**, changelog **32 RU**.
- Both channel feeds are signed with the existing production key and target the verified public EXE. Comparison excluding only launcher metadata, publication time and news/changelog confirms all game data unchanged: **15 packages per channel**, unchanged release identities and shared guide. The private key remains local and is not included in the commit or assets.

This release uses the existing tag workflow; signed feeds are committed only after all public-asset and self-update checks above pass. Prior candidate-only records remain historical test evidence; publication is authorized by the user's later acceptance.

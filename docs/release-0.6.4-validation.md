# Launcher 0.6.4 publication validation

The user accepted the local candidate and explicitly requested publication on 2026-09-09. Scope is the accumulated launcher changes documented in `release-0.6.4.md`; gameplay packages are not changed.

## Pre-publication

- Local source and origin/main started at `fd457e13a616a3e0b0db94653b705c57acee40ce`. No existing v0.6.4 tag/release.
- Both anonymously fetched production feeds have valid signatures, launcher 0.6.3, and the same signed payload/signature as the local baseline. Text-file line endings may differ.
- Downloaded public 0.6.3: SHA-256 `143EB6199DE1B4706B8C721EF0E63B6B54772BE032F130DE2EA0C901ABA4D829`, 72,262,340 bytes.
- Versioned 0.6.4 source: build with zero warnings/errors; core **PASS 8801**. Detached UI suites **61 layout + 104 chat/broadcast checks on each of RU and EN**, with generic layouts at 1600 × 1000 RU and 1050 × 680 EN.
- Tests use isolated files and mocked authentication/delivery. No live game, user settings or real conversation is altered. Prior manual acceptance and additional regression evidence: `validation-launcher-layout-refresh-20260909.md` and `validation-chat-activity-quick-save-20260909.md`.

Publication uses the existing GitHub tag workflow. Signed channel feeds are promoted only after validating the downloadable public EXE, ZIP contents, startup, and isolated self-update from 0.6.3. Final results will be appended after publication.

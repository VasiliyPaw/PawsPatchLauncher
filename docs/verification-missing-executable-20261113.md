# Launcher 1.0.14: missing executable recovery

Scope: preserve a recognizable installation when its base EXE disappears, show a themed recovery warning, recognize the selected installed patch helper, and allow explicit reapplication of unchanged settings to repair a missing helper. RU/EN/UK/CS/DE/FR included. Game-status refresh cannot re-enable launch while the file is missing.

Validation from an isolated clean release worktree:

- Full launcher suite: `PASS 39306`, including 19 missing-executable detector checks.
- Database suite: `ADMIN DATABASE CHECKS: 12682 PASS`, isolated PostgreSQL/WASM; no production changes.
- WPF UI scenarios: 10 per supported language. Covers retained path, no silent Steam fallback, disabled launch, restoration/recheck, disappearance after discovery, periodic launch-state refresh and separate base/helper recovery dialogs.
- Production fixtures use only disposable text files under an explicit G: profile. No game executable was executed, removed from an installed game or restored from a real quarantine.

Reports, build/smoke logs and screenshots: project-root `outputs/launcher-missing-executable-20261113/`.

Recovery advice distinguishes a possible quarantine from a confirmed cause. It offers trusted-file restoration, Steam verification or patch-settings reapplication as appropriate. It does not change antivirus settings.

## Release validation

- Source/tag: `42b2ab93125e3237183cf84efbd71ef4d1b0c9e7`, `v1.0.14`.
- [GitHub release workflow](https://github.com/VasiliyPaw/PawsPatchLauncher/actions/runs/43334718352): success, including launcher/database tests and packaging checks.
- [Published release](https://github.com/VasiliyPaw/PawsPatchLauncher/releases/tag/v1.0.14): executable, ZIP and artifact manifest downloaded and verified against GitHub SHA-256 digests and the source commit.
- Public EXE: 74,417,282 bytes, SHA-256 `6964D346AA392FD2C8B8CCDC83D2CF709305DF746F267C7F8E5BF02E188B03B6`, version `1.0.14.0`.
- ZIP EXE matches the separate public EXE; packaged configuration matches the committed production configuration.
- Public EXE smoke passed both with its distribution files and as a standalone EXE.
- Real replacement/backup/window acknowledgement: `REAL SELF-UPDATE PASS: 1.0.13 -> 1.0.14`, isolated Unicode path. The user's installed launcher was not replaced during this test.
- Signed launcher-only catalogs prepared for legacy, v2 and v3 Stable/Beta. Game packages, requirements and all other game sections are unchanged.
- Authenticode remains `NotSigned`; catalog signatures are verified separately. No signing certificate or antivirus exclusion was installed.

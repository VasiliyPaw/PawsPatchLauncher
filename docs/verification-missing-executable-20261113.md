# Launcher 1.0.14: missing executable recovery

Scope: preserve a recognizable installation when its base EXE disappears, show a themed recovery warning, recognize the selected installed patch helper, and allow explicit reapplication of unchanged settings to repair a missing helper. RU/EN/UK/CS/DE/FR included. Game-status refresh cannot re-enable launch while the file is missing.

Validation from an isolated clean release worktree:

- Full launcher suite: `PASS 39306`, including 19 missing-executable detector checks.
- Database suite: `ADMIN DATABASE CHECKS: 12682 PASS`, isolated PostgreSQL/WASM; no production changes.
- WPF UI scenarios: 10 per supported language. Covers retained path, no silent Steam fallback, disabled launch, restoration/recheck, disappearance after discovery, periodic launch-state refresh and separate base/helper recovery dialogs.
- Production fixtures use only disposable text files under an explicit G: profile. No game executable was executed, removed from an installed game or restored from a real quarantine.

Reports, build/smoke logs and screenshots: project-root `outputs/launcher-missing-executable-20261113/`.

Recovery advice distinguishes a possible quarantine from a confirmed cause. It offers trusted-file restoration, Steam verification or patch-settings reapplication as appropriate. It does not change antivirus settings.

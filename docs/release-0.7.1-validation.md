# Launcher 0.7.1 validation

## Reproduced incident

The reported 0.7.0 executable matched the published SHA-256. Its current signed catalog contained all 37 packages. The affected mod library nevertheless contained empty Vanilla entries adopted from older 15-package Arcane Wars catalogs. `All()` on an empty package list classified them as installed, and retaining that release hid the new Vanilla patch and Russian language packages. Because the selected mode was not active, it could neither be installed nor updated through the normal actions.

`LegacyModMigrationChecks` reproduces this condition with signed local catalogs, a previous Arcane Wars installation and an already-written empty Vanilla entry. On unmodified 0.7.0 source it fails with `Paw's Patch disappeared from Vanilla`. With the fix it passes 44 checks in Russian and 44 in English, including the actual Install action, all four text/speech combinations, unchanged active files before Install, retention of Arcane Wars, and offline reuse after installation. The executable fixtures cannot run a game; no real account, game directory or external network is used.

## Validation before publication

- Main .NET suite: **12,915 PASS**. The mod-library subset includes four new regression assertions for empty entries, recovery and preservation of a real installed release.
- UI: **8/8 scenarios** — migration, retained mod library, mod controls and per-mod channels in Russian and English.
- Mod-library UI: **275 checks per language**; 45 rapid offline switches per run preserve the applied installation. No extra network request was added to mode selection.
- The rendered migration view shows **Vanilla**, an operable Paw's Patch toggle and the Install button; Apply and Launch are unavailable before installation.
- Build: no warnings or errors. Game packages, executable payloads, balancing and server behavior are unchanged.

Evidence is retained locally in `work/launcher-hotfix-071/`. Release distribution and signed catalog identity are verified separately after the public build.

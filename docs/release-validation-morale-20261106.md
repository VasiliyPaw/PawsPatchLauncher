# Arcane Wars 0.4.2-beta.11 — validation scope

This beta completes the opt-in ignore-zero-morale policy. The native classifier
runs once and only depleted result 0 becomes ordinary low-morale result 1.
Racial thresholds, normal low-morale retreat, explicit Run, Stun and actual
morale loss/recovery remain native. Disabled-option behavior is unchanged.

- 15,609 emitted-code assertions: 1,527 classification fixtures, 27 native
  TakeMoraleDamage cases and 30 native AddMorale cases at three address layouts.
  Thresholds 8/16/20/25/40/48, signed zero, lowered caps and both CAI-query
  results are covered. Transition/actor-flag callbacks are modeled.
- 138 retreat transaction checks, 323 exhaustion/option checks, 72 option checks
  per Arcane/Pure profile, and 2,544 existing native company-behavior checks.
- Full launcher regression: 38,206 assertions. Additional focused launcher
  behavior/options checks: 348 + 325.
- Eight Arcane helpers are rebuilt from pinned prior-release inputs. Native
  resources and feature manifests are retained except patch identity and the
  company-behavior/ignore-zero-morale revisions, now 2.
- Only five Arcane beta modules are repackaged. Unchanged payload files are
  compared byte for byte. Base Arcane Wars, Pure/Immortals, stable catalogs,
  legacy gameplay catalogs and launcher identity remain unchanged.
- Local release evidence, installation/network/replay logs, package manifests
  and publication receipts are kept under outputs/release-morale-20261106 in
  the project workspace. Failed/incomplete attempts are retained separately.

The original reported long-lived company stall cleared after loading the save
on the previous installed build. It was not reproduced as a persistent failure
in the local observation. These changes address the remaining depleted-morale
code paths; this report does not claim that every stall is fixed, that all older
recordings are compatible, or that local peers prove multi-machine/NAT behavior.

The user's installed game, original saves and unrelated uncommitted work are
not test destinations. The decompilation project and original game binaries
remain local and are excluded from publication.

## Release live-test outcome

The installer applied the signed staged package set to a fresh marked fixture.
The adapted helper logged COMPANY_EXHAUSTION r2 and QUIET_READY with the new
identity. Two network attempts stopped at the existing available-commit-memory
guard before the menu/match. Only QA-owned games were terminated. This is
startup confirmation, not completed live gameplay, network or replay acceptance.
Source CI completed successfully. No network/replay pass is claimed for this beta.

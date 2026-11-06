# Ignore zero morale and explicit retreat

Kohan II 1.3.72. Revision 1 shipped with the 2026-10-29 betas; revision 2 is
prepared for Arcane Wars 0.4.2-beta.11 with the ordinary racial retreat policy retained.

## Exhaustion policy

`COMPANY_BEHAVIOR` reads the installed `.pawpatch/state.json`, not unsaved launcher preferences. A missing `appliedSettings.ignoreZeroMorale` is false. True is accepted only for Arcane Wars with the core patch enabled in stable/beta, never data-only or Pure compositions. The launcher exposes the switch only when the selected Arcane Wars feed advertises `companyBehaviorRevision >= 1`.

Enabled ignore policy guards and replaces the entry to CAI's Exhausted transition at RVA `2778C6` with `mov al,0; ret`. This prevents entering Exhausted, including its strategy cancellation. The separate Exhausted update call at RVA `274A1A` returns decision 2 so a company already in that state in a save leaves through native cleanup. An order already discarded before the save cannot be reconstructed by this patch.

Local revision 2 (2026-11-04) also wraps the native morale classifier at RVA
`2147EC`. It calls the original body exactly once through an eight-byte trampoline
and changes only result 0 (depleted) to result 1 (ordinary low morale). Native
results 1/2, effective morale caps, racial thresholds at Organization+0xB8 and
CAI queries remain native. Low-morale retreat, explicit Run and Stun are retained.
Morale is neither clamped upward nor frozen. This also allows native AddMorale
to send its normal depleted-flag clearing notification while morale is recovering.
No command, position, health, ownership or save bytes are written by the adapter.

Disabled ignore policy retains the stock classifier and entry plus the existing
scoped `ExhaustionRecoveryPatch`. All three installed sites use byte guards,
readback and instruction-cache flushes. Rollback attempts every site; an uncertain
classifier-hook rollback retains its allocated code instead of freeing live code.

## Retreat priority

The entry gate for native group combat detection at RVA `233035` returns false only when the group's current command definition kind is 7 (explicit Run). All other commands continue through the complete native function. This prevents the combat-support path from replacing Run with guarding another company. Normal formation spacing and group movement coordination remain active.

The gate adds no world writes or RNG calls. Its executable allocation and installed jump are verified and rolled back on failure. It composes with the separate same-target combat cohort patch.

## Compatibility

The option is included in native lobby identity, launcher configuration export/import (`ZM1`), friends' configurations, effective settings, change detection, and applied installation state. Missing and false have identical identities; true differs. Local language and keybind preferences remain outside this setting.

## Validation (2026-10-29)

- Native installer tests: 138 retreat + 323 exhaustion/option checks, including rollback failures.
- Installed options: 72 Arcane + 72 Pure checks.
- x86 execution: 2,544 cases using the emitted gate and native combat body; command kinds, 1/6/14/64 members, relocation, register/stack behavior, exhaustion entry/exit.
- Revision 2: 15,609 assertions across 1,527 native classifier cases, 27 native
  TakeMoraleDamage cases and 30 native AddMorale cases at three image/cave layouts.
  Thresholds 8/16/20/25/40/48, signed zero, lowered caps, command overrides, both
  CAI-query responses and register/flag/SSE preservation are covered. Transition
  and actor-flag callbacks are modeled; these cases are not full gameplay tests.
- Launcher: 348 option checks plus 325 existing AI configuration checks.
- Native lobby identity: 101 checks in the complete Arcane build.
- WPF isolated installation: 10 checks for visibility, default off, pending changes, applying on/off and persisted state.
- Complete Arcane runtime and four Pure runtime variants compile; previous feature manifests retained with the explicit added behavior fields.
- Fresh isolated game startup verified in memory with the option on and off. Final QA state is off.
- Live 13-company Run observation: no combat-support/Guard replacement during 28.8 simulated seconds. This does not replace a multiplayer test with a naturally stunned groupmate.
- Live zero-morale move and targeted attack observations retained the same command pointer and destination/target. The attack test subsequently moved toward the target. The stock-enabled control also continued at zero morale in this fixture; these observations establish order retention, not a controlled reproduction of every Exhausted transition.

Evidence and scripts: workspace `outputs/selection-scroll-20261029/`, especially `morale-disabled-moving.json`, `morale-disabled-attack.json`, `retreat-after-group.jsonl`, and `startup-exhaustion-{on,off}.json`.

## Local revision 2 observation and limits

Both user saves `Случайно.RSG` / `Случайно2.RSG` were copied unchanged to
`outputs/zero-morale-20261104/` in the outer workspace. Selected actor 72517
(stoneriders) had 0.527/148 morale and Rout; actor 65575 (Royalist Noble) in the
second save had 0/134 morale and Rout. The installed r1 hooks were read back.
After the user authorized unpausing, actor 65575 moved, left Rout for Sleep and
recovered to 26.34 morale in about 25 game seconds **without revision 2**.
The game was returned to pause. This does not reproduce the pre-load persistent
stall and does not establish that revision 2 fixes its cause.

The original revision 2 local candidate used a helper with separate identity
`0.0.0-morale-r2-local` was built from pinned release inputs and queried only with
`--features`; it was not launched into a game during that local investigation.
The 0.4.2-beta.11 release uses separately rebuilt/versioned helpers and new
immutable packages. See `../../docs/release-validation-morale-20261106.md` for
release checks. A live before/after reproduction of the original persistent
stall is still outstanding; no claim of fixing every stall is made.

The Arcane beta advertises this capability with compatible native helpers. Multiplayer peers must use the same option and runtime package. Two-peer Arcane simulation and a fresh recorded replay passed with the option enabled; see ../../docs/release-validation-20261029.md for scope and evidence.

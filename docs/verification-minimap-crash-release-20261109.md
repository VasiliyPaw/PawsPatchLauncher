# Minimap crash hotfix — three betas, 2026-11-09

The user authorized publishing the fix after diagnosis of the current crash.
Targets: Arcane Wars 0.5.1-beta.3 and Vanilla/Immortals 0.5.0-beta.4
(Pure runtime 1.3.72-pure.19-beta.4). Baseline main is
bf6790df9fa45ece457339a911a26fea779d51cf. Public package bytes and all six
signed catalogs were checked against the baseline before preparation.

## Cause and correction

The native inverse-coordinate routine RVA 2A42AA returns the output pointer
in EAX. The minimap hook incorrectly declared both the function pointer and
callback as void. Subsequent branches and x87 comparisons clobbered EAX.
The native caller at RVA D5000 immediately reads [EAX] and [EAX+4].

The 18:22:54 crash dump has EIP 00B25005 (image A50000 + D5005), EAX 4021,
and an access violation reading 4021. The coordinate result itself was
already written at EBP-24. The accepted compiled callback reproduces the
exact EIP/EAX when the x87 status contains 21. Other zoom paths can instead
return out+4, yielding incorrect coordinates without an immediate fault.

Both the typedef and callback now return U. The original result is saved
and returned after any zoom coordinate adjustment. Original instructions,
not the decompiler's erroneous void inference, establish this contract.

## Scope

Hash-verified accepted native sources for Arcane and Pure were copied to new
build folders. Only ui.c's return contract changes; runtime.c, find.c and all
headers retain their hashes. The new shipping DLLs retain exactly the two
production exports. QA exports are compiled only in separate test DLLs.

All eight Arcane and four Pure helpers are rebuilt from their exact last
released compiler inputs, preserving the lobby-color lifetime fix and every
feature value except the new release identities. The only changed helper
inputs are the native DLL, its integrity metadata, and version identity.
Graphics, animation/resource caches, models and game data retain their bytes.
The Pure data module changes only its module version for compatibility.

The four Arcane helper packages and two Pure packages receive new immutable
URLs. Other package records, the launcher, stable and legacy catalogs remain
unchanged. v2/v3 beta guides, beta history and standalone beta guide receive
the new versions. Changelogs use a short player-facing bullet in Russian,
English, German, French, Czech and Ukrainian.

The user's installed game and original saves are outside all write targets.
No new game is launched. Wall-corner and bridge experiments are excluded;
their local files and unrelated staged/dirty work are preserved.

## Validation

- Compiled inverse return-contract tests: 468 assertions / 144 caller cases
  for each of Arcane and Pure; three address layouts, four scales, match and
  widget branches, all four intercepted callers, EAX and stack cleanup.
- Existing compiled native UI tests: 4295 Arcane and 2634 Pure assertions.
- Final helper resources: all 12 embed the fixed mode-specific DLL and its
  correct loader hash (36 checks). The unchanged native lobby-color payload
  passes the established 1656 compiled offline checks.
- Actual launcher selection/update detection: 635906 assertions across 55296
  selections, covering all modes, text locales and component combinations.
- Real transactional installer gate: 20 Pure and 12 Arcane cases, covering
  native helper variants, six locales, rollback, disabled patch, file-only
  and beta reapplication. It runs in private no-launch fixtures.

The native tests execute compiled x86 code in an emulator with explicit
native-command stubs. A live match after this fix is not claimed.

## Reproduction and publication evidence

F:/PawsCrashQA-20261109-1823 retains the private crash evidence and original
compiled failing reproduction. It is not uploaded with the release.

F:/PawsMinimapCrashPublish-20261109 retains accepted input hashes, fixed native
sources/DLLs, helper compiler sources/resources, native/installer/catalog
reports, payload audit, signed candidates and publication receipts. The exact
compiler-input attachments exclude game EXE, saves, keys and experiments.

tools/MinimapCrashRelease contains the repeatable build, verification and
publication procedure. Only explicit source paths are committed. Source CI
must succeed before immutable assets are published; public downloads and
digests are checked before beta catalog promotion. The final public readback
verifies catalog signatures, mode versions and unchanged out-of-scope feeds.

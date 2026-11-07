# Arcane Wars 0.5.0-beta.2 — packaged active-match return

Date: 2026-11-07. Baseline source: `7318b8ddd3af19301530a6ba8b645cccdc9f9419`.
This report supplements the historical private-lab reports; it does not replace
their failed attempts or attribute their complete scenario matrix/long soak to
the final binary.

## Product composition

All eight Arcane helper variants embed the same x86 runtime:
`3FAAB2651FA26C2C6CE42E96B0566ADF63070FA2724AF7B70069DF75AE475974`.
Features: `hotJoinRevision=1`, `hotJoinProtocol=R`,
`legacySaveLobbyRecovery=false`. Activation follows FastTransfer installation
unconditionally; no new user toggle/package is required. Existing gameplay/UI
payloads are pinned to the accepted beta.1 build, with the version changed to
beta.2. The release compiler mode omits the laboratory command-file loop,
test-hold mechanism, marker gate and periodic QA instrumentation.

Every embedded `PawLobbyCompatibilityNative` was rebuilt without
`PAW_RECOVERY_INTEGRATED`. All eight were inspected for the absence of
`PawRecovery`, `PAW_PURE_RECOVERY` build arguments and
`PawMultiplayerSavesNative` resources. Old save-and-lobby recovery is disabled
in Arcane, while the independent Pure implementation remains unchanged.

Exact compiler/source/resource pins and helper self-test results:
`../../outputs/hotjoin-beta-20261107/helpers-r5/build-report.json` and
`native-inputs.json`. Actual embedded resource audit:
`../../outputs/hotjoin-beta-20261107/embedded-runtime-audit.json`.
Eight helpers × five existing self-tests = **40 passes**.

## Host loss with two remaining original players

Accepted laboratory case:
`G:/PawHotJoinLab-20261107-two-survivors-load-r1/acceptance.json`.
Four original humans; one has left, the current host disappears after the
shared load barrier. Two original humans retain the match paused, elect a host,
explicitly resume and run for a minute with matching native world checksums.
The absent participant retries, reclaims the original kingdom, and all three
run for another minute: 68 common checksum samples spanning 67 seconds.

Accepted **final packaged runtime** case:
`G:/PawHotJoinLab-20261107-release-two-survivors-r6/acceptance.json`.
The final beta.2 helper/runtime performs all admission and recovery; a separate
QA observer samples native state/checksums and dispatches ordinary test-player
commands. It does not install the private experimental admission implementation.

This case starts four original humans on the preserved Arcane Wars
`Случайно2` save. One exits normally. During that participant's cold return,
the current host is terminated while native checkpoint bytes are still being
transferred. The two remaining original humans:

* retain their original session and pre-barrier world, paused;
* elect a native host and cancel the uncommitted arrival without a false chat notice;
* explicitly resume and advance over a minute with matching native world CRCs.

The absent participant then starts a fresh process, reconnects to the elected
host, transfers/validates the checkpoint, and reclaims the original kingdom
with no AI controller. All three load the same full native commit and advance
for **67 matching checksum seconds / 68 common samples**, with no mismatches,
native errors or forced shutdowns of the surviving games. Native localized
return notices are present on all active peers. Native content/auth/version
checks were enabled (`bypass=false`). `validate_run.py` accepts every check,
including the separate two-survivor minute before the retry.

The preceding packaged attempt `...release-two-survivors-r5` recovered the
two-player match but could not create the retry fixture because the drive ran
out of space copying a large archive. It is retained as **incomplete**, not a
passing game test. Identical archives in explicitly owned test roots were
deduplicated after SHA-256 verification; user/installed files were not linked,
deleted or modified. The fresh r6 run above completes the full retry.

## Other final-release checks

* `G:/PawHotJoinLab-20261107-release-no-colors-startup-r5/acceptance.json`:
  accepted startup of the actual packaged runtime without custom colors,
  using the original serializer ABI. Main menu reached, native checks retained,
  legacy recovery absent and normal exit. **This is startup only.**
* Real package selector/update/executable selection: **55,296 settings selections,
  632,066 assertions**, both channels, all mods and six languages, main patch
  on/off, three spawn modes, 64 component bit combinations, AI and zero-morale
  switches on/off. Only Arcane beta with the main patch selects beta.2; every
  selected helper contains the runtime. No new optional hot-join module.
  Receipt/source: `../../outputs/hotjoin-beta-20261107/catalog-tests/`.
* Real installer, rollback, helper selection and read-only preflight:
  **12/12 cases** covering six languages and minimum/maximum option sets.
  `G:/PawHotJoinPackageQA-20261107/summary.json`. This matrix launches no games.
* Six native notice localizations (en/ru/de/fr/cs/uk) are packaged in their
  corresponding data modules. The live final-runtime test exercises Russian;
  the other five languages have package/preflight evidence, not live chat QA.
* Signed v2/v3 beta catalogs target the ten new immutable beta.2 archives.
  Stable catalogs, legacy v1 catalogs, Pure packages, other dependencies and
  the launcher release entry remain unchanged. Existing mixed biomes and UI
  corrections are retained.

## Scope and reproduction

All native runs use isolated, owned game/Documents profiles and the original
1.3.72 executable, SHA-256
`1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.
No installed game or original save is changed. Accepted roots retain inputs,
source snapshots, commands, logs, process identities and independent acceptance.
For the packaged run use `experiment.py --release-observer --witness
--second-witness --scenario return --leave-mode menu --continue-without
--edge-case host-partial-transfer` with the owned composed source and the
QA startup adaptation of the packaged helper; see the retained `inputs.json`
and QA manifest for exact paths/pins. Then run `validate_run.py ROOT`.

These are multiple local processes over LAN. Real Steam Internet across
computers/NATs is **not verified** here. The user plans that acceptance after
publication. Host loss during admission deliberately requires the incoming
participant to retry with the new host. Earlier repeated-return, simultaneous
arrival, timeout and resign tests remain precisely scoped in the preceding
local-edge and safety reports; they are not claimed as new full reruns of the
packaged DLL. Full match completion during admission remains outside this
release's final requested test.

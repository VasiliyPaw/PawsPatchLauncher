# Pure 0.5.0 beta 2 optimization port — 2026-11-09

This ports the four accepted generic Arcane Wars presentation modules into
Vanilla and Immortals, above the published Pure 0.5.0-beta.1. Mode data,
simulation, balance, world generation, save format, AI and automatic network
recovery are unchanged by this port. No Arcane actor/recon/fort module is linked.

## Exact production inputs

The Arcane owner confirmed `C:/PawsArcane051ReleaseQA-20261109/native-r7` and
`helpers-r3/source` as frozen production inputs. The combined Arcane DLL itself
is not used: it contains Arcane-specific UI/actor code. The new Pure DLL combines
the already accepted Pure minimap/clock code with only generic Find and frame
code. Its SHA-256 is
`FE845954451123B95EE4119AA5C45313D2E85CD7ED3616336686CA551E07904D`.

The graphics DLL is byte-identical to the accepted Arcane production DLL:
`112920FF0CB9A38158A12E9F8875B6B4FBBCE9ADA5C364EF55936EBBE4A83179`.
The resource payload and per-Find headers also retain their exact frozen bytes.
`outputs/pure-050-optimizations-20261109/baseline.json` binds the frozen inputs;
the four-helper build report binds every compiler input and embedded resource.

## Behavior and boundaries

- Resource-cache per-class weights are repaired. Previously requested model,
  effect and animation resources use native request/wait/precache/release,
  without retaining native resource pointers between callbacks. Loading or
  paused-world preparation is bounded and stops under pressure; running combat
  does not perform speculative preparation.
- Animation retention uses the accepted 80% RAM and NiSeq 100/100 policy, only
  after the native memory gate permits it: at least 512 MiB free process virtual
  address space, 384 MiB available physical memory and global load below 90%.
  Native eviction remains in use.
- The exact accepted VB/IB pool has a 32 MiB/512-entry cap, eight-second TTL,
  three-frame age, identity/binding/thread checks and reset/world cleanup.
- The per-Find stack bitsets apply only on the native VIEW thread, preserving
  order, allocations, key writes and fallback. All seven native code bodies
  are guarded after the rest of the Pure hooks have been installed.
- The frame callback is attached once through resource state +104. The old
  extra Pure minimap-frame call is removed to avoid two frame callbacks.
  Animation-policy state is at +108. The typed native fastcall is retained.
- GPU prewarming is forcibly disabled. Prepared-view/view reuse, render
  registration cache, D3D state cache, old Find index/reject paths and diagnostic
  scope hooks remain disabled. Production has two presentation exports and no
  laboratory loader, marker, observer or QA export requirement.

## Installation ownership

Three packages change: the four native helpers in `pure-fixes-runtime`, the
graphics DLL in `pure-beta-common`, and the version identity of `pure-fixes-data`.
Every data payload in the latter stays byte-identical. The only changed common
payload is `d3d9.dll`; world, clock, minimap data and localization stay identical.

Early private staging incorrectly put graphics in runtime priority 910, while
the existing common package at 930 still owned the old graphics DLL. The real
installer rejected that combination during preflight. Final staging retains
one graphics owner in the common package. Another private staging attempt
correctly failed the existing lobby contract because the core data package
version was not bumped. Neither attempt was published. A partially configured
private match was closed through native ReallyQuit before final fixtures were
created. Code-generation failures are retained separately as QA failures.

## Offline/native validation

- Resource cache: 25 native checks, eight production policy/callback boundaries,
  165 actual managed transaction checks including partial writes and rollback.
- Find: 4001 native equivalence cases, 3000 native read-only getter/predicate
  checks and 45 full-body/ASLR/corruption checks. Allocation and selected leaf
  calls are controlled stubs; these are not complete-game emulations.
- UI: 2634 actual compiled minimap/clock checks, 27864 unchanged emitted HUD
  checks and 11 queued Win32 path-validator cases.
- Combined Pure composition: 1488 guarded installs in 12 compositions across
  three image bases, all seven complete Find bodies preserved, plus 477 map
  transactions, 24 lobby/channel cases and 12 save-copy Block compositions.
- Graphics: range/fake-COM/atomic replacement checks, system D3D9 creation and
  valid/invalid draw guards, plus 33 buffer-pool stages covering age, ownership,
  bounds, reset, cap and purge. The separate fixture DLL is not distributed.
- Actual installer: 20 cases with six locales, four helper variants, optional
  components, beta reapply, stable rollback, master off and file-only. Every
  case checks the installed graphics hash, including its removal/restoration
  when the optimization package is no longer selected. The previously frozen
  launcher snapshot is used without rebuilding shared launcher sources.

## Live acceptance and limits

`vanilla-pair-r3` passes with the exact final helpers and final three-package
ownership: 53 shared native world CRC pairs and no mismatches. Both peers use
normal rendering, a new Mixed / Dynamic / All 384 match, a native save and normal
exits. Clock uniqueness, pause, lighting/native-time agreement, simulation and
speed pass. The final readback reports 544 prepared resources (179 models,
365 animations), zero preparation failures, active 80% animation policy and
31214 buffer hits. Those counters establish coverage, not an FPS improvement.

`immortals-resume-r1` loads the actual beta 1 save with phase 2692, advances it,
then returns through the normal score/LAN flow and creates another Dynamic/All
match in the same process. Serialized phase, new random phase, one clock in each
world and normal exit pass. Both worlds pass the resource/cache/Find/buffer
checks: prepared resources 491 then 546, buffer hits 530 then 3454, no preparation
failures and the same guarded animation policy. The old save's cached lobby
description still includes its historical bare phase value; it is not rewritten.

Exact live results, optimization state and package hashes are recorded in the
adjacent verification JSON and publication receipt.
Private Documents/AppData and disposable copies are used. Native UI settings
and actual menu registration are checked before launch. Harmless native Echo
commands flush the real buffered native log; no fabricated log lines are written.

Graphics counter addresses are derived from the exact compiled
`PawBufferPoolStats` scalar-copy instructions and read externally. They are
non-atomic QA observations, not timing measurements; the test does not call a
lock-taking graphics API from an arbitrary engine callback.

This is functional compatibility acceptance. No isolated Vanilla/Immortals
performance A/B, uncapped FPS gain, other GPU/PC, Internet session or many-hour
match is claimed. The earlier Arcane performance percentages are not assigned
to these two modes or added together.

# Arcane Wars 0.5.1 beta / Launcher 1.0.13 integration

The accepted Arcane 0.5.0 beta was promoted to stable first, without adding the
new performance, UI or voice work. Stable publication/readback is recorded in
`outputs/arcane-051-release-20261109/stable/publication.json`.

The new beta combines repaired resource quotas and finite model preparation,
80/100/100 animation caching, bounded vertex/index buffer reuse, per-call Find
bitsets, the frozen UI/scouting fixes, and global launcher faction speech.
GPU warming, prepared-view caching, render registration experiments, old Find
indexes/rejection and graphics state caching remain disabled. Both forms of
automatic multiplayer recovery remain disabled.

All eight managed variants passed 40 existing self-tests. The exact product
payload passed 25 resource regressions, eight additional memory-policy and
callback cases, 4,295 UI callback checks and 11 real Win32 path cases against
both old and fixed validators. The default helper directory's trailing slash
is now accepted; different directories and incompatible native guards remain
rejected. Readiness is signaled after the helper finishes all startup patches.

Catalog selection passed 631,298 assertions over 55,296 configurations; 12 real
transactional installer/rollback cases passed. Five changed archives preserve
the other accepted payloads. Scouting data is updated in both overlapping
templates, including the powers/shards restoration package.

Live acceptance uses isolated paths/profiles and a documented startup adapter;
the embedded product DLL and graphics DLL are unchanged. Source/helper hashes
and test-only differences are recorded separately. The actual production
launcher voice API runs from a clean export of the 43 intended launcher paths.
The clean export passes 39,143 tests and builds PreviewRenderer, excluding
unrelated dirty work. Changelogs and new launcher strings cover six languages.

- New map: simulation, save and normal exit pass.
- Original copied `Случайно2`: 20 seconds of simulation, new save, exact native
  speech settings and normal exit pass. Native preparation reports 638 assets,
  zero failures and completed finite scans.
- Two ordinary rendered processes with genuinely different faction/common
  voice banks: both advance 70.0 seconds; 272 shared native world/net checksum
  samples match, both save/exit normally, no assert or desync is reported.
- A fresh match with custom speech is recorded and replayed to the native
  `END_OF_FILM` event, without film desync. Playback receives `UserReady`; the
  test does not blindly unpause it.

Proofs are indexed by
`outputs/arcane-051-release-20261109/beta-r2/native-acceptance.json`.
Earlier attempts stopped on conservative test memory reserves or test control
errors, not confirmed game crashes. The test now waits for the actual fresh
main-menu registration; benign native Echo commands flush buffered logs.
Native code independently confirms `StagingReady 0` means ready.

The earlier A/B/B/A performance series reduced the mean of four repeated-view
frame peaks from 188.05 to 167.89 ms; p99 did not improve. This is a limited
result on this PC, not a general FPS claim or elimination of stutters. This
release acceptance does not cover Internet play, another GPU, long sessions or
audible acceptance of every faction line in Vanilla and Immortals. The user's
audible acceptance is for Arcane Wars.

Exact managed/native patch inputs are included in a separate build-inputs
attachment. It contains no game installation, original saves, credentials or
signing key. Existing experiments and unrelated staged/unstaged work are
preserved. The installed game and original saves are checked by hash at the
publication gate.

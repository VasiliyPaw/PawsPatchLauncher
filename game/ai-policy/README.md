# Optional AI improvements and integrated diagnostics

Build: `beta7/build.ps1 -AiPolicy -ExhaustionRecovery` with the other current Arcane features. Paw's Patch 0.4.0 Beta exposes one launcher option, enabled by default, for both the data changes and native AI/exhaustion fixes. The installed module and applied setting must agree before launch. Turning off Paw's Patch disables the option; bulk host bot setup remains a separate built-in Paw's Patch feature.

The existing game helper installs seventeen guarded native call-site wrappers. Each observation/eligibility wrapper calls the original engine function exactly once. The child-building precondition may veto an invalid command before its original callee. `policy.c` runs on the native AI thread, without OS calls, additional RNG, actor commands, health or ownership writes. Recruit eligibility uses native short-lived ResourceVectors on the same simulation thread, forwarding the definition and default formation layout; final admission is still native. An unchanged floating-point score retains its original 80-bit return. The helper's existing monitor drains a bounded ring; no separate diagnostic attachment or utility is needed.

## Enabled behavior

Mask 1 prevents a Construct candidate from targeting a location where another AI with the same nonzero team parent already has an active, assigned Construct goal. If both already committed, native player-list order chooses one. A matching settlement center already owned by that ally also vetoes the candidate. The veto only lowers an already positive native candidate score to zero. It does not make an illegal candidate legal. Native goal cancellation/reselection handles the result; Repair goals are unaffected. This is not a global reservation manager and does not cancel existing Repair goals.

Team parents were compared with the recorded 3v3 kingdoms: the three participants in each team share a distinct parent. No ownership or saved-kingdom remapping is performed.

The native policy does not change recruitment budgets, combat-force thresholds, or neutral-target selection. The accompanying local data experiment (`prepare_data.py`) restores vanilla insufficient-income thresholds where AW explicitly replaced them with zero, adds economic weight 0.2 to AW-added combat recruitment requests, and restores the settlement influence radius factor from 0.1 to 1.7. Attack priority, including the emergency attack bonus, remains unchanged. A resource deficit is acceptable when net gold income after its cost and the new company's upkeep remains healthy. The insufficient-income penalty is a soft candidate penalty, not a recruitment ban.

Mask 2 filters native-eligible recruitment templates by the native limited-resource definitions and their paired capacity resources. It counts both company capacity and kingdom points, including a sovereign pioneer consuming 11 points and units in the default formation. Ordinary resource deficits do not veto candidates. Later native budget/admission checks retain actual customized layouts and reservations. No decisions are cached.

Mask 4 rejects a child-building command if the settlement or its center is removed, the center ownership differs, or its body is missing/dead. The original affordability, placement and siege checks still execute for valid centers. This is a stale-command guard; the reported one-second building flash has not been reproduced yet.

## Reports

`<game>/paws_ai_diagnostics/<timestamp>-<pid>/` contains session metadata, rolling decision JSONL, periodic snapshot JSONL, the first snapshot, status and a `closed.json` shutdown marker with final counters. Revision 5 retains four 4 MiB decision files, four 4 MiB snapshot files, two 4 MiB recruitment/veto files, two 4 MiB compact economy timeline files, and one initial snapshot, below 56 MiB total. Old sessions are not deleted automatically. `totalBytesWritten` is cumulative output, not retained disk usage.

- kind 0: goal type/state/base/final priority.
- kind 1: recruitment preparation and chosen city ID, when present.
- kind 2: construction candidate and before/after priority; counter 20 counts vetoes.
- kind 3: native recruitment requirements result and city ID. Zero means this requirements check passed; it does not promise recruitment. Nonzero is the original engine code, not a guessed explanation.

- kind 4: early recruitment eligibility; zero passes; `4294967295` means native template rejection; otherwise `result-1` is the blocked resource index. For capacity refusals `before=requested`, `after=remaining`, `stateOrCityId=used`, `finalPriority=capacity`.
- kind 5: final planning budget with actual layout; same fields; `4294967294` means an unclassified native refusal.
- kind 6: the native recruit queue-insertion call was executed. This is not completed recruitment.
- kind 7: final queued/direct recruitment validation: 1 passed, 0 refused.
- kind 8: native limited-resource admission: zero passes, otherwise resource index + 1.
- kind 9: child-building lifecycle guard; 0 passed to native checks, 1 invalid settlement, 2 missing center, 3 ownership mismatch, 4 dead/invalid body. City and center IDs occupy the two legacy state/priority fields.

- kind 10: direct company creation through the AI path: 1 succeeded, 0 failed, plus city ID.

Counters 27, 28, 29 respectively count new diagnostic duplicates, early capacity vetoes and invalid-center vetoes. Actual queue insertions and final validation events bypass deduplication.

Repeated evaluations are sampled every five game seconds; counters count all evaluations. Revision 4 groups priorities by kingdom, goal type, definition, state and positive/nonpositive transition rather than short-lived goal object addresses. A per-game-second budget limits bulk goal-priority and unchanged construction events to 64 each. Recruitment preparation, requirements checks and actual vetoes bypass that bulk budget and have a separate retained file. Counters 21-24 record intentional deduplication; 25-26 record intentional bulk sampling. These are distinct from `dropped`, which counts transport losses. The older 3v3 trace lost 53.23% of detailed ring entries and cannot establish every individual recruitment decision.

Snapshots and compact economy summaries run every ten wall-clock seconds and are explicitly asynchronous; compare their start/end game times. The compact timeline preserves a much longer economic history than full snapshots. Invalid/loading/transient snapshots are rejected and reported, never used to make AI decisions. File errors do not stop the game. Hook installation failures roll back all attempted writes, retaining payload memory if rollback cannot be verified.

## Validation boundaries

Native tests mock engine callees and verify relocated calling conventions, output preservation, diagnostic-only write boundaries, sampling, floating-point precision and ally/enemy/reservation cases. Managed tests cover transaction faults and snapshot fixtures. These do not replace observing a full match or verifying multiplayer determinism with multiple clients.

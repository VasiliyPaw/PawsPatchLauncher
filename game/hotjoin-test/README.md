# Active-match join research — private 1.3.72 lab

This directory is an isolated development harness. Do not copy its laboratory
DLL into an installation. The separate production wrapper in `../hotjoin`
compiles shared native sources with `PAWS_HOTJOIN_RELEASE`; see its README and
`docs/verification-hotjoin-release-20261107.md` for current shipping evidence.
Nothing here publishes a build or modifies the installed game. The November 7
QA additionally uses read-only copies of the user's preserved saves in wholly
separate game/Documents directories.

## Current evidence

All game tests use the stock 1.3.72 EXE with SHA-256
`1eb79bbb678668be5a05f8c98103cd9988048490ce7c53c74c9a1d0813e9cd45`.
The original tests below do not establish Steam Internet compatibility.
The extended local QA also validates a full Arcane Wars 0.5.0-beta.1 composition
on a 1280 map for 1510 matching checksum seconds across three peers. Follow-up
safety tests accept cancellation/retry after host loss during a partial Arcane
transfer and after the shared load barrier, plus deferred native resign voting
with two simultaneous arrivals. See `docs/verification-hotjoin-safety-20261107.md`
for exact snapshots and limits; the earlier soak is not a run of the newest DLL.
The historical laboratory DLL described below is not the shipping DLL.
See `docs/verification-hotjoin-local-edges-20261107.md` in the checkout for the
accepted/failed evidence, preserved user-save hashes and composition limits.

* `G:/PawHotJoinLab-20261106-baseline-r3`: the unmodified engine rejects an
  arriving player while the host is playing (native reason 10).
* `G:/PawHotJoinLab-20261106-admission-r1`: removing that rejection only joins
  the session. The client remains in staging with no world. This is not hot join.
* `G:/PawHotJoinLab-20261106-snapshot-r1`: a wrong inferred creator type caused
  a host crash. Dump and analysis are preserved. Resource `+90` is a 0x68-byte
  WorldCreationSettings object, not a 0x54-byte WorldCreatorLoad object.
* `G:/PawHotJoinLab-20261106-snapshot-r5`: the arriving observer receives and
  verifies the native checkpoint, creates its world, and leaves the host's
  original world allocated. Local loading polluted the shared network trace.
* `G:/PawHotJoinLab-20261106-snapshot-r6`: a balanced native local-operation
  scope around private loading fixes that trace error. The host must also mark
  its already-existing world ready; otherwise task completion never happens.
* `G:/PawHotJoinLab-20261106-snapshot-r7` and `-r8`: both peers enter the game
  and advance, but a full native world check finds genuine differences between
  a live world and a restored save (RNG, kingdom Z coordinates, recreated object
  IDs). Preserving serialized world rules alone is insufficient. These fail.
* `G:/PawHotJoinLab-20261106-coordinated-r1`: a coordinated checkpoint restore
  **inside the same native network session**, without host staging, produces
  identical full-world commit checksums (`105219 / 37577` on both peers), then
  runs the observer for over a minute with native checks and failure handling
  active. This first run preseeded the identical checkpoint in the private
  client cache. It validates the restore approach, not production completeness.
* `G:/PawHotJoinLab-20261106-ticket-return-r3`: a participant returns with a
  different nickname and the private credential, replaces the implicit AI, and
  retains the original kingdom. Both restored human kingdoms have `isSAI=0`
  and no remaining AI controller. The validator passes: 65.375 simulated seconds,
  73 common checksum samples spanning 72 seconds, identical full-world native
  commit (`133509 / 53420`), same host session and no host staging. This run
  **preseeded** the checkpoint and does not validate network transfer timing.
* `G:/PawHotJoinLab-20261106-menu-return-cold-r1`: normal exit correctly leaves
  the client in staging with an inert retained world allocation. The first
  driver incorrectly expected that allocation to be freed; evidence retained.
* `G:/PawHotJoinLab-20261106-menu-return-cold-r2`: normal native exit replaces
  the participant with AI and the host continues. The returning copy receives
  the checkpoint through the unchanged native transfer, but then hits native
  `SyncFailure(85930)` at load completion. **Failed; not a usable cold return.**
* `G:/PawHotJoinLab-20261106-auto-menu-cold-r4`: **accepted two-peer automatic
  cold return after normal exit**. The connection itself captures a unique
  checkpoint, transfers it through the native channel, reclaims the original
  kingdom, dismisses loading and restores the previous pause. Native full-world
  commit is `180359 / 61983` on both peers; 66 matching samples span 65 seconds,
  and simulation advances 64.5 seconds. No driver save, preload or resume.
* `G:/PawHotJoinLab-20261106-auto-impostor-cold-r1`: the same name without its
  credential correctly remains an observer and the AI retains the kingdom.
  Full-world commits match, but the client's first post-load selection order
  crashes at `80e03` with a missing current sender. **Failed stability test.**
  The fix invalidates the native outgoing sender-prefix cache after commit so
  the next normal order identifies its sender explicitly. The later accepted
  `impostor-ai-r2core-r1` below closes this retest; actor lookup and checksum
  failure handling are not bypassed.
* `G:/PawHotJoinLab-20261106-three-menu-cold-r6`: **accepted three-human
  automatic cold return after ordinary client exit**. All three full native
  commits match; 70 common samples span 69 simulated seconds; no native errors.
  This retained run used the earlier automatic-resume policy. It does not
  establish the new manual-resume policy or host departure.
* `G:/PawHotJoinLab-20261106-three-pause-menu-r1`: departure and return both
  retained pause on all three peers. The test cast only one Resume vote and
  timed out because native multiplayer requires a majority. Retained as an
  incomplete stability test; the driver now casts ordinary votes from peers.
* `G:/PawHotJoinLab-20261106-host-pause-menu-r1` and `-r2`: native host election
  preserves the remaining match at a constant world tick. The first exposed a
  credential overwritten by empty local staging after Leave; issuance now
  happens on real peer admission. The second verifies ownership on the new
  host, but stock migrated-host state 1 blocks SetMapTransferStatus. A narrow
  current-checkpoint transfer exception is accepted in the later r3 below.
  Neither of these earlier two runs passes.
* `G:/PawHotJoinLab-20261106-host-pause-menu-r3`: **accepted ordinary host exit
  and return with three participants, manual-resume policy**. The two remaining
  peers elect a host natively, retain the original session, and remain paused
  at tick 178 until the former host returns to kingdom01 as HotJoinRenamed.
  All three native full-world commits match. Pause survives return; ordinary
  player Resume votes are then required. 70 matching common checksum samples
  span 69 seconds; simulation advances 69.8125 seconds with no native errors.
  This is isolated stock LAN, not Steam Internet/Arcane Wars acceptance.
* `G:/PawHotJoinLab-20261106-client-uncleared-r1`: unsuitable fault injection
  for the unresolved-dialog test. Terminating a local UDP peer sends an ICMP
  reset and native code immediately removes it. The replacement AI is paused,
  but this does not establish recovery from an uncleared connection dialog.
* `G:/PawHotJoinLab-20261106-client-uncleared-r2`: retained failed recovery
  prototype. Local pause writes at asynchronous timeout strand host/witness at
  ticks 218/217. Ordinary per-player kick votes also cannot settle while normal
  decrees are blocked. The candidate now queues a shared native Pause order,
  and uses the native CSD backup vote through its separate backup channel.
  Do not restore the asynchronous Sim.pause write at SetBackupMode.
* `G:/PawHotJoinLab-20261106-client-uncleared-r3`: **accepted three-peer return
  from an unresolved native connection-status dialog**. The owned fault process
  was suspended, retaining its socket. The original native human slot remains
  present before return; the driver never sends Delete/kick. Both live peers
  naturally stop at tick 228 with identical native network/world checksums.
  Authenticated return triggers native backup-channel voting and native stale
  connection removal, followed by the verified cold checkpoint path. All three
  full commits match (`143186 / 6014`); 70 common samples span 69 seconds and
  simulation advances 69.6875 seconds after explicit player Resume. No native
  errors. This is a timeout/hung-peer simulation, not a literal process crash.

* `G:/PawHotJoinLab-20261106-repeat-menu-r2`: **accepted five returns in one
  retained three-human match**. The same participant returns three times, then
  the other participant and current host return. Paused/running admissions
  alternate; native Sally/Recall execute after every return. Matching common
  CRC windows span 76, 62, 61, 62 and 61 simulated seconds, with no native
  errors including shutdown. Ownership, AI retirement, all-peer native notices,
  original kingdoms, retained nondeparting sessions and native host migration
  pass the independent repeat validator. Ordinary exits use new owned return
  processes here; same-process menu return is accepted separately below.

* `G:/PawHotJoinLab-20261107-simultaneous-return-r2`: **accepted two returning
  owners admitted together**, including the former host. Native connect
  requests arrive 63 ms apart and share one checkpoint. Both original kingdoms
  execute militia controls; pause remains until explicit player Resume.
  Three common checksum streams span 77 seconds, all notices occur once per
  peer, no native errors or forced active-peer shutdown. An initial checker
  nickname assumption failed because stock UI truncated the long second name;
  that output is retained separately. The corrected checker identifies its
  original kingdom and verifies orders against that holder's kingdom pointer.
  One early mirrored ready message lacked its ordering context; this warning
  did not prevent loading or stability, and was addressed in the next build.
* `G:/PawHotJoinLab-20261107-simultaneous-observer-reuse-r5`: **accepted four
  peers: same-process owner return plus simultaneous fresh observer**. The
  observer actually arrives first; both roles and all four native full-world
  commits match. Four-way common checksums span 80 seconds, native controls
  succeed, the running match automatically resumes, every peer sees both
  localized notices once, no native errors or forced shutdown. Private native
  headers serialize the active ordering context; no refused ready messages.
  A scoped native capacity wrapper permits authenticated live spectators up
  to the existing 16-connection ceiling without changing kingdom/start slots.
* `G:/PawHotJoinLab-20261107-two-out-host-uncleared-r2core-r3`: **accepted two
  hung/timed-out owners, including the former host, recover without driver
  Delete**. Owned processes are suspended with their sockets open, not labelled
  literal crashes. Both original slots remain before credential proof. Native
  backup recovery elects the remaining host, removes stale connections and
  preserves pause before AI takeover. Sequential returns use two checkpoints;
  both original kingdoms execute militia controls after explicit Resume.
  All three common CRC streams span 77 seconds, no errors or forced active-peer
  shutdown. The final checkpoint is byte-identical on all three copies. This
  run uses the unchanged lobby R2 core: native transfer/CRC-ready times are
  2.001 s for the first newcomer, then 2.066 s existing / 3.002 s incoming.
* `G:/PawHotJoinLab-20261107-simultaneous-observer-r2core-r6`: **accepted
  four-peer simultaneous owner/observer admission with the original lobby R2**.
  Same-process return, original kingdom control, fresh observer, automatic
  resume, all notices, native full commits and role maps pass. All four common
  CRC streams span 80 seconds; all active processes exit normally, no errors
  or refused ready controls. The 228961-byte checkpoint is identical on every
  peer. CRC-ready times are 4.006/4.008/4.068 s, compared with about 114 s in the
  earlier corresponding stock-pacing run (roughly 28 times faster locally).
* `G:/PawHotJoinLab-20261107-impostor-ai-r2core-r1`: **accepted same-name,
  no-credential observer while the original kingdom's AI keeps playing**.
  The match automatically resumes, all three full commits/role maps match,
  common CRC spans 73 seconds, file bytes match, no native errors or forced
  shutdown. Original lobby R2 transfers/CRC-checks the 239815-byte checkpoint
  in 3.003/3.061 s. This supersedes the old failed first-selection-context run;
  display names still confer no kingdom ownership.
* `G:/PawHotJoinLab-20261107-exact-block-r2core-r2`: **accepted native lobby
  transfer of the exact preserved 224000-byte regression file**. No padding,
  repair, preseed or world launch: native save selection and transfer deliver
  all bytes, the sender receives its normal final acknowledgement, SHA-256
  matches the original, both peers exit normally with no errors. Elapsed time
  including acknowledgement/state polling is 1.797 s. This is transfer-only
  acceptance, not a separate hot-join stability claim.

Credential and returning-player development follows that experiment. Newer
runs retain `source/`, DLL, input hashes, exact owned process paths, JSON state,
native logs, and native checksum samples. `validate_run.py` is the acceptance
checker; a completed driver is not itself a passing hot-join claim.

### Follow-up failures retained during pause-state work

* `G:/PawHotJoinLab-20261106-two-out-host-menu-r3`: after the first of two
  returns, the existing peer recreated the other kingdom's implicit AI with a
  different session ID. Native world commit alone did not catch the roster
  difference. The scoped `1688cf -> 16adee` hook now preserves implicit session
  players during coordinated reload; native world/controller teardown remains.
* `G:/PawHotJoinLab-20261106-two-out-host-menu-r4`: AI IDs match, but Resume
  exposes a second divergence. The old host retained a pause owner while the
  arriving peer had none. The former immediately resumed and the latter waited
  for another vote, shifting simulation clocks. The new pause metadata restores
  the same owner by native player ID and clears stale Resume votes on all peers.
* `G:/PawHotJoinLab-20261106-two-out-host-menu-r5`: first return and manual
  continuation with the other kingdom still held by AI succeed without the
  earlier pause-owner divergence. The second admission is refused because the
  previous checkpoint's indexed resource has an unloaded header (`flags=8`).
  A read-only source census is retained under the analysis directory. Native
  SaveGame (`1c1a15`) requires that source header; the fix reloads it with native
  `1c384a` under balanced private resource-read scopes before requesting the
  next save. The refused-arrival fixture was manually stopped, recorded in its
  intervention marker. **Not** a passing two-return run; no native exceptions.
* `G:/PawHotJoinLab-20261106-visitor-prior-pause-r1`: observer join into an
  initially running match automatically resumes without player Resume commands;
  73 common checksum samples span 72 seconds and simulation advances 71.4375s.
  The Russian native observer notification is visible in both screenshots.
  **Full acceptance failed:** both copies crash during final application
  shutdown. Assembly confirms `MessageSystem` consumes its TGString format
  value (`137966 -> 21375`); the notice passed a borrowed localized string.
  The fix creates a separate owned format and also releases the suppressed
  stock notice's owned format. Later accepted repeated/four-peer runs include
  successful native shutdown; this old failing result is retained unchanged.
* `G:/PawHotJoinLab-20261106-return-unpaused-r1`: three-human return after the
  remaining players deliberately continued without the departed participant.
  Automatic resume, original kingdom ownership, AI retirement, native Russian
  notice and Sally/Recall all pass; 80 common samples span 79 seconds with no
  checksum mismatch. This copied the same pre-fix notice code as the observer
  run and fails final shutdown for that known string-ownership error. Retained
  as functional evidence, **not** complete acceptance.
* `G:/PawHotJoinLab-20261107-simultaneous-return-r1`: the second admission
  repeated native SetFrozen(true), adding a trace record absent on the first
  newcomer. The first native mismatch is 73742, followed by SyncFailure 73830.
  The fix freezes only the first member and extends the existing group barrier;
  checks remain enabled. The later r2 is accepted separately.
* `G:/PawHotJoinLab-20261107-simultaneous-observer-reuse-r1` and `-r3`:
  driver navigation failed on the native results screen, not staging. r1 tried
  LAN directly; r3 used StagingExit while Scoring was active. Native ScoringExit
  is used in r5. r2 instead failed on transient Windows EINVAL while reading an
  open native log; bounded retries preserve every file and report persistent
  unreadable logs as errors. These runs are retained and are not acceptance.
* `G:/PawHotJoinLab-20261107-simultaneous-observer-reuse-r4`: the returning
  owner reuses its original process, but native PlayerJoin rejects the fourth
  peer as full: room capacity counts observers. The subsequent live-role-only
  capacity wrapper does not change kingdom or initial staging slots. A recorded
  manual intervention stops the known-refused observer; r4 is not four-peer
  acceptance. The later r5 passes complete four-peer and normal shutdown checks.
* `G:/PawHotJoinLab-20261107-two-out-host-uncleared-r1`: former host's private
  credential resolves both stale peers through native backup recovery without
  driver Delete, and the first return completes paused. The second checkpoint
  has **224000 bytes, exactly divisible by the native 64-byte block**. Both
  receivers get the matching 223936-byte prefix and correctly refuse CRC-ready;
  `transfer-boundary-diagnosis.json` retains sizes/hashes/prefix evidence. Native
  FileTransfer.cpp sender and receiver both use zero remainder as the final
  block length. The candidate `transfer_runtime.h` retains the full block for
  zero remainder at both signature-checked instruction sites. No file padding,
  protocol/ACK changes, CRC bypass or post-transfer file repair. The executable
  `transfer_boundary_tests.c` runs original and patched x86 arithmetic over
  exact and partial block boundaries and reproduces the original regression.
* `G:/PawHotJoinLab-20261107-two-out-host-uncleared-fast-r2`: both checkpoints
  complete with a preliminary fast transport (2–3 seconds), but the driver
  mistakenly treats CSD's backup-only stop as an unpaused match. It expects
  auto-resume although recovery correctly retains the departure pause. The
  driver now recognises paused OR backup as a prior stop. This run has no minute
  stability acceptance. The preliminary pacing is replaced by the original
  lobby R2 core in r3 above; the native pause policy was not changed for this.
* `G:/PawHotJoinLab-20261107-exact-block-r2core-r1`: the new transfer-only
  driver tried to inspect the receiver's exclusively opened output before
  completion and stopped on Windows PermissionError. Native errors are absent;
  this is not transfer acceptance. The driver now waits for the final native
  sender acknowledgement and unlocked output before comparing bytes. Persistent
  locks, missing files or different bytes still fail by timeout; r2 passes.

## Reproduce

From the workspace root, use the bundled Windows Python:

```powershell
$python = 'C:/Users/Paw/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python work/launcher-104-release/game/hotjoin-test/experiment.py --out G:/PawHotJoinLab-FRESH --mode coordinated --scenario return --leave-mode menu --automatic --witness --control-orders --language ru --observe 65
& $python work/launcher-104-release/game/hotjoin-test/validate_run.py G:/PawHotJoinLab-FRESH
```

`--scenario visitor` tests a new observer. `return` starts two human players,
terminates only the owned client, lets the native AI take over, then reconnects
from a fresh game copy with the old private credential and a different nickname.
`impostor` repeats with the old nickname and no credential; that peer must remain
an observer while the AI keeps the original kingdom.

`--leave-mode menu` uses native `RequestLeaveGame` and waits for scoring with
released kingdom bindings. It does not kick the participant on the host. A
normal exit must retain the same return right as a lost connection.

`--automatic` enables `auto_runtime.h`: defer the verified native join, prepare
a unique fresh checkpoint in response to that connection, then admit it. The
module restores the **pre-admission pause state**, for both returning owners
and observers. If the players were already paused (including a departure
pause), the match remains paused until ordinary player Resume. If the players
had continued, joining adds only a temporary transfer/loading pause and the
shared successful completion automatically resumes. Native human departure
still pauses before AI creation and preserves pause after native cleanup.
There is no automatic resume on failed/incomplete admission.

The host sends the pause flag, native pause-owner player ID, previous owner ID
and pause timestamp through the authoritative Join decree and private session
view. Every peer maps IDs to its own native connections, restores pause before
unfreezing, and clears stale native Resume votes. This avoids an old peer
resuming immediately as pause owner while a new peer incorrectly waits for a
majority. The protocol magic changed: ordinary C/D, recovery E/F; older lab
layouts cannot silently connect.

QA uses `--scenario visitor --automatic` for an initially running observer
join, adds `--prepaused` for a pre-existing manual pause, or uses
`--scenario return --leave-mode menu --witness --continue-without --join-unpaused`
to test a returning owner after the remaining players chose to continue.
Paused runs assert unchanged world ticks before explicit native Resume votes.
Running joins assert automatic advancement without any test-player Resume.
Both then require at least one minute of matching simulation checksums.

`--repeat-plan client,client,witness,host --interval 60` adds four further
ordinary exits/returns in the **same match** after the first accepted load and
observation window. The same participant returns three times overall; the
other participant and current native host also return. Each uses a fresh owned
process with that participant's private credential and unchanged nickname.
There is no map restart or driver-supplied checkpoint. Paused and deliberately
resumed admissions alternate. Each cycle executes native militia controls and
observes at least 60 simulated seconds with all three native CRC streams.
The interval is active simulation between completed admissions; native file
transfer and loading take additional wall time. `repeat-progress.json` retains
partial results; `validate_repeats.py`, invoked by `validate_run.py`, checks
every cycle independently and includes final native shutdown errors.

`--simultaneous return --double-drop --witness` prepares both departed owners
before issuing their native Join commands in the same short window. Add
`--depart host --continue-without` to include host migration. The alternate
`--simultaneous observer --witness` sends a returning owner and a fresh visitor
together, while the other two original participants remain (four peers total).
The verifier checks both actual native connect timestamps, shared full-world
commit, ownership/observer roles, native notices on every peer, and a minute of
simulation. Accepted retained cases are listed above. Add `--reuse-client` to
the observer variant for a return in the original process: native `ScoringExit`
closes its results screen, then the same process reopens LAN and rejoins using
its own retained credential. Numerical phase 12 alone cannot distinguish the
scoring and staging screens.

The multiparty candidate retains up to eight additional already-authenticated
native Join orders while capture/transfer is pending, and admits them against
the same checkpoint before the host's load barrier. Native authentication,
version/content checks, file CRC and complete-world validation remain active.
The barrier waits for native role assignment of every admitted member and all
human CRC-ready acknowledgements. Its host-authoritative payload carries the
complete admission group and pause state; newcomers do not supply roles.
Staging peers receiving a second Join use that authoritative role instead of
stock automatic kingdom assignment. Native notices are deduplicated per ID.
Arrivals after the barrier starts remain outside this batch window; general
timeout/abort handling and production queue UI are still unfinished.

`--witness` selects the matching multiparty protocol and starts three human players
in three distinct kingdoms. Two stay in the match while the original participant
leaves and returns. `multi_runtime.h` sends the host's exact checkpoint to the
existing peer through native map transfer, collects CRC-ready acknowledgements
from all humans, then sends the host's authoritative load barrier. This is a
separate experiment; acceptance always names the exact retained source/run.

`--depart host` with `--witness --scenario return` leaves or terminates the
original host. The driver discovers the elected native host's owned UDP port,
reconnects there, and records logical peer directories for the validator.
Host election is native. A public SHA-256 credential-verifier manifest is
replicated through authoritative join decrees and private session views, so
the elected host can verify the former host's secret. Remote bearer secrets
are not replicated; sending a public verifier as a secret cannot authenticate.

`--uncleared --leave-mode crash --witness --automatic` selects the separate
recovery protocol experiment. The driver never sends Delete/kick votes.
The original native human slot must still exist at return. Only proof of that
owner's credential and a native timed-out connection can request ordinary
native majority votes to remove the stale connection, then the normal verified
checkpoint path takes over. A dead host's prefix proof requests cleanup only;
admission still retries through all native content/password/identity checks.
The owned fault process is suspended with its UDP socket still open, so native
timeout/CSD is genuinely exercised; this is not labelled a literal process crash.
Native backup already stalls simulation before the shared Pause order can run.
After resolution the shared leave handler preserves pause before AI takeover.
Accepted cases are the exact retained client-only and two-out/host runs above.

`--double-drop` with `--witness --automatic --scenario return` removes two of
the initial three humans, retains one, then returns the two owners sequentially
through two distinct native checkpoint cycles. Add `--depart host` to include
the original host in the two departures. `--continue-without` explicitly tests
player-controlled Resume while participants are still absent, then pauses again.
These flags are test scenarios, not assertions that the scenario has passed.

`--cached-snapshot` is only a development acceleration. A cold transfer must
pass separately. The default now reuses the unchanged lobby **R2** core from
`game/fast-transfer/FastTransfer.cs` (1200-byte file-stage budget, maximum 16
packets per peer/pass, stop when unsent metadata is drained, at most one fresh
receiver ACK per pass). Native block sizes, ACK processing/retries, bandwidth
buckets and CRC checks remain. `--stock-transfer` is an A/B measurement switch,
not a launcher option; it keeps native pacing and the exact-block boundary fix.

`prepare_r2.py` exports the original C# generator into `r2_payload.h`, checking
its relocation table against a second EXE/cave address pair byte for byte.
`r2_guards.h` comes from the original 15-region guard exporter. A preserved
`FastTransferR2Source.cs` is hash-checked against the repository's original
before each run. R2 code guards are checked at early owned-process startup;
live registry values 20/64/256 are required before hot admission. Ordinary
lobby and active checkpoint file transfers use that same R2 code. Production
R2 itself has not been edited, and loading a second R2 installer is rejected
by code guards rather than layered silently.

The accepted r3 cold transfers take 2–3 seconds including the CRC poll; older
stock-pacing runs take 109–114 seconds for similar 220–234 KB files. These are
local-process LAN measurements, not Internet guarantees. `measure_transfer.py`
extracts the timings. The original 8421 x86 R2 checks pass on these exported
payloads too; export metadata and test output are retained under
`G:/PawHotJoinAnalysis-20261106/r2-export`.

`--fixture-transfer <lab.RSG> --mode coordinated --scenario return` only selects
a preserved lab save via the native lobby order, transfers it, checks all bytes
and the native final acknowledgement, then closes the two owned copies. It
never launches the world and its acceptance is explicitly transfer-only. This
mode exercises the retained exact-64-byte boundary regression without padding
or modifying that save, or staging it on the receiving copy.

The source fixture is `D:/PawsMultiplayerRig/game`. Each run requires a **fresh**
output directory and creates two complete game copies and private Documents.
The installed game and existing saves are never a write target. The driver
owns suspended launches in a kill-on-close Windows job, checks the disk EXE
hash, redirects Documents, and closes only its retained process handles.

## Important limits / remaining work

* `snapshot` and `admission-only` are deliberately incomplete comparison modes.
  `coordinated` is the development candidate. There is no shipping installer.
* Automatic capture is available under the explicit test environment flag.
  Complete timeout/abort rollback and production UI integration remain required.
  A stale checkpoint must never silently rewind the match.
* Additional existing peers use opt-in revision 3; the accepted scope remains
  the explicitly recorded results, not every possible lobby composition.
* Credentials are host-issued 256-bit random values, private to the recipient.
  Request role claims are ignored; only the host creates the role decree. A
  display name never establishes ownership. The private lab caches its credential
  in its redirected profile; production storage and session lifetime need review.
* A rejoin may reclaim only a departed participant's kingdom currently held by
  an implicit AI. A current human owner, missing AI or departed observer must
  not grant a kingdom. Native version, depot, password and Steam auth checks
  remain in place. Matching lab protocol is mandatory even in staging.
* No real Steam Internet, full Arcane Wars component set, abort/timeout,
  large-map or full visual acceptance yet. Repeated return and host migration
  acceptance is limited to the explicitly retained stock-LAN cases above.
  Simultaneous admission and same-process menu return are limited to the exact
  accepted fixtures above. Host migration and
  unresolved disconnect recovery are explicitly named separate experiments.
* Hook installation currently assumes the marked stock-only fixture. Production
  integration needs complete preflight, atomic rollback and version negotiation.

## Reverse-engineering notes

Addresses are RVAs for the supported EXE, not runtime VAs. Native world/session
changes run under the simulation/network thread's existing admin lock.

| RVA / offset | Observed role |
| --- | --- |
| `150e19` | active-session rejection; other stock admission checks retained |
| `14cb6a -> 16203e` | maintenance inside the native AdminTick lock |
| `152b5a -> 16775c` | private session writer |
| `152b86 -> 16797a` | private session reader |
| `1524c3 -> 152926` | private header writer; serialize active sender context, restore live cursor |
| admin `+228/+2a4/+270` | previous-batch/current/incoming-continuation ordering player |
| `14b56c -> 16205a` | live-role-only connection capacity; stock lobby unchanged |
| `151936 / 1500f6 / 1501d1` | unchanged original lobby R2 budget / cadence / ACK hooks |
| `159524 / 1599bf` | exact-block final-length correction, sender / receiver |
| `14b77c -> 168042` | kingdom auto-assignment after native PlayerJoin |
| `14aed1 -> 162816` | shared task completion |
| `1626da` | native local launch / checkpoint restore |
| `5f3fe8` | Sim singleton (`+28` paused, `+29` frozen, `+3c` current world) |
| `5f3fc8` | SAI singleton (`+6c` controller array, `+70` count); **not** Sim |
| `16a6d4 -> 16a091` | restore human ownership before native SAI InitForGame |
| `1e04b4` | native SAI RemoveByKingdom; destroys the obsolete controller |
| `5f3ff0` / `5f3ff4` | separate network / world synchronizers |
| `16e788` | native balanced recording scope; private synchronous restore only |
| `297e9c` / `297548` | WorldCreatorLoad constructor / ApplyCreationSettings |
| session `+74` / `+7c` | WorldCreationSettings / WorldCreatorLoad pointers |
| bit stream `+0/+4/+8/+c` | vtable / shared byte buffer / byte cursor / bit cursor |
| byte buffer `-8/-4` | native refcount / byte capacity |
| `150fc8 -> 155a95` | native join request after all stock admission checks |
| `1531ed` / `153443` | native ConnectData copy / destructor for deferred join |
| `155e26/155793` | task-status request/decree extension writers |
| `1556d1/1547a2` | corresponding extension readers |
| `1557db/1547e9` | native task-status order processors, CRC-ready control |
| `16a919 -> 14c958` | local BeginTasks; preserve remote ready statuses |
| admin `+230` | outgoing sender-prefix cache; reset after coordinated commit |
| `15489c/156194 -> 156628` | native sender lookup diagnostics, unchanged checks |
| `168bff` | native request/select a saved map file for existing peers |
| `14d42b` | native ClientLeave; pause before replacement AI and after cleanup |
| `14fa4a/15180c -> 14f89c` | native backup-mode entry; queue shared Pause |
| `14d162` | native host state; **not** a game-full/player-count predicate |
| `150de6 -> 14d162` | guarded settled migrated-host admission |
| `14b09a -> 14d162` | guarded transfer of the admitted checkpoint after election |
| `14aab6` | native CSD backup-channel vote; distinct from per-player kick decree |
| `14abc4/14a9f9/14aa28` | native recovery quorum, history and lag checks |
| `1502c7/1502e1`, `1503a9/1503c3` | optional server/backup packet intent extension |
| `15c7bb -> 150343` | incoming packet dispatcher; cancel an uncommitted arrival before successor world orders |
| `d199b` | guarded five-byte native VoteToResign ProcessRequest entry; replay original trampoline outside admission |
| `14900a/172d54/14cf50` | native staging-exit ConnectData and async RequestLeave; returns to LAN/Internet lobby |

The native unaligned bit-array codec has field boundaries: one 36-byte write
must be read as one 36-byte field, not a 4-byte read and a 32-byte read. The
credential extension contains no checksummed world data and is never put in
the stock password/name log fields.

`KohanHotJoinExport.java` makes targeted read-only follow-up exports into
`G:/PawHotJoinAnalysis-20261106/targets`. It does not overwrite the preserved
Ghidra project or the initial export. These remain recovered pseudocode, not
original rebuildable engine sources.

The boundary regression can be reproduced independently of game UI with the
same x86 TinyCC used by the driver:

```powershell
& work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe -Wall -Werror work/launcher-104-release/game/hotjoin-test/transfer_boundary_tests.c -o G:/PawHotJoinAnalysis-20261106/transfer-boundary-tests.exe -lkernel32
& G:/PawHotJoinAnalysis-20261106/transfer-boundary-tests.exe
```

This tests actual executable x86 tail instructions, including the original
zero-length result for 224000/64. Complete native transfer/restore stability
must also pass separately; arithmetic checks alone do not establish hot join.

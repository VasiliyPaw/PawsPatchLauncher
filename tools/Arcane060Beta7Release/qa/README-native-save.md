# Native Mixed2 load comparison

Run only in the coordinated bounded native slot. Earlier invalid/default-map attempts are retained separately and are not passing evidence. It does not start games/helpers, compile, copy/swap DLLs, patch modules, bind QA APIs, change fog, use !sp, capture the screen or terminate processes.

Only these exact G: trees are supported: the existing `G:/PawsWork/QA/ArcaneFix-20261125` private game, this workspace's old QA tools, and `outputs/arcane060-beta7-release-20261126/native-save` for receipts. It never accesses the installed game or ordinary user saves. Both mounted private Mixed2 copies must match the original supplied input SHA. The no-fog derivative is never selected.

The historical beta.6 core ZIP is a read-only input and may resolve through its approved cold-storage junction to F:. It is never executed, changed or extracted there; the owner stages the selected DLL on physical G: before rebuilding the private helper. All executable test inputs and all new outputs remain on physical G:.

## Root-owned setup per run

1. Ensure the previous owned game/helper are closed. Archive old `network-*-api.txt`, observer and command files before `control.start`. The script records stale API files but never calls or rewrites them.
2. After generic release QA passes, stage_native_fixture.py copies and SHA-checks the real winning files/removals of the four verified beta.7 modules. It merges only their module records into the original camelCase private state, preserving unrelated records and Originals. This is an explicit native-fixture assembly, not a full upgrade of its retired 24-module cache. stage_save_pair.py then selects exact production baseline/final DLLs, helpers, markers and the matching metadata snapshot. No helper version guard is bypassed.
3. Baseline DLL SHA: `5BC48F3D6639A70F34CD7F1A01CE948804350E927A873B4FF52F70FDBD2D7792`. Its bytes are in the old retained beta.6 core ZIP. The script can verify that ZIP member without extracting it.
4. Final109 **production DLL** SHA: `B3C13E79390327E698E75C0BF380B78AEA73A3C9C9945091BF058B1B4CAD38E5`. Use the exact release module. The earlier private QA wrapper `64CA2F...` is retained separately for construction fixtures and is not used in this comparison.
5. Use the exact published/new production custom-color helper bytes through `stage_save_pair.py`, required by this save's `paws_light_indigo` color. A non-color helper rejects its header and can silently leave the default R6 selected. After the swap/pin, run `prepare --label baseline` or `final`; this writes metadata only.
6. Root starts through the existing `qa-tools/control.py start preview`, then activates only that owned window using AX. No script start/activation occurs automatically.

All Python invocations below are **future root commands after the grant**, using the already approved explicit interpreter, `-B`, and process-only G: TEMP/TMP. Do not run SDK, csc, TCC or Unicorn for this observation.

```powershell
$script = 'G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3/work/arcane060-beta7-release-20261126/qa/native_save.py'
$python = 'C:/Users/Paw/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:TEMP = 'G:/PawsWork/QA/ArcaneFix-20261125/Temp'
$env:TMP = $env:TEMP
& $python -B $script prepare --label baseline
# Root: existing control.start + own AX activation, after the grant.
& $python -B $script load-snapshot --label baseline
& $python -B $script resume-smoke --label baseline   # optional, AFTER the frozen snapshot
& $python -B $script quit --label baseline
# Root: preserve receipts, swap final109 private QA DLL/helper pin; repeat setup.
& $python -B $script prepare --label final
# Root: second existing control.start + own AX activation.
& $python -B $script load-snapshot --label final
& $python -B $script resume-smoke --label final      # optional
& $python -B $script quit --label final
& $python -B $script compare
```

## Snapshot contract

`load-snapshot` accepts a fresh menu only. It sends exactly RequestSinglePlayer → RequestCustom → SelectLaunchType LOAD_SAVED_GAME → Select save/mixed2.rsg → Commit → StagingLaunch and stops **before UserReady**. It waits for world+mode2 and for the asynchronous native actor registry to settle for at least five seconds with three matching counts, then takes three fresh observer/native-registry count samples and records native world time/tick, observer and native frozen byte, and count/read stability. No passing result is manufactured when time advances or frozen is unconfirmed. The evidence proves no ticks observed during the sampling interval; ticks before the first observed sample are explicitly not directly measured.

Raw direct lookups include requested/full actor ID and generation, actual slot occupant, vtable, flags/dead/dying bits, construction flags, body/HP, definition, position, owner and observer player/AI mapping for IDs126895,137800,164550 and player bridges68772,36003,168153,103335. No guessed ghost flag is used. All bridge definitions in the native actor registry, including dead/dying ones, are also counted. Existing `review.snap` is secondary because it filters dead/dying actors.

The read-only reader reuses the existing Memory read/u/f/name implementation without resolving bridge exports or requiring the final payload's roadState for a baseline process. It validates the exact owned executable/PID and uses the fresh observer's PE base. No Memory.constant (Unicorn), export call, API bind or process-memory write is used.

`resume-smoke` optionally sends UserReady, waits phase4, then GamePause1 / GameSpeed0 and records roughly one second of fresh observer plus a second raw snapshot. Differences after UserReady may be ordinary AI actions; they are not used to judge pre-load retention. An exit/timeout yields an incomplete receipt.

`compare` requires both eligible pre-UserReady records with the same save and initial world time. All four independently known ordinary bridge IDs must actually be present; this prevents a matching empty/default R6 map from passing. It checks the seven exact IDs and all-bridge counts. Even a passing comparison covers only this paused load; it does not prove bot planning, paid building or multiplayer behavior.

`quit` sends ordinary native ReallyQuit without a trailing newline, waits for the exact owned game/helper to exit, and records remaining owned processes. It never reads missing final-plugins.txt and has no force-kill fallback. Root remains responsible for plugin restoration and recorder/capture cleanup, including exceptional exits.

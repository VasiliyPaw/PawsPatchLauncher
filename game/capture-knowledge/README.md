# Observed capture knowledge

Local candidate, Kohan II 1.3.72 / Arcane Wars 0.6.0-beta.2. Not published.
Supersedes the all-known-participants candidate, which disclosed unseen captures.

The real owner continues to synchronize through native simulation on every
peer. A building's remembered owner changes only for the old owner, new owner,
and kingdoms seeing the building BEFORE GActor::ChangeKingdom (RVA 228B6C).
The native virtual visibility predicate (+70, with hierarchy enabled) determines
observers. Snapshot recipients on the stack before the original function can
remove sight; keep these locals separate during recursive city-child changes.

After the original call completes, validate the saved ID with native
GetThingByID (RVA 21117), honoring its installed extended-registry hook and
serial checks. Then invoke native UpdateGhostOwner(actor, recipient, true),
RVA 23BCC1, for entitled recipients only. The true argument changes ownership
without refreshing unseen health, position, name or observation time. It keeps
native AI unregister/register bookkeeping and creates no ghost records.

Other players retain the last owner they actually saw, even if they explored
the building earlier. Opening normal sight reveals the real owner, and normal
observation writes a fresh memory when sight is lost again. Loading a save
does not globally reconcile hidden memory against the real owner.

The callback is generic to Structure/Settlement components, including city
children and capturable special buildings. There are no race/building ID lists.
Capture permission, combat, terrain exploration and ordinary observation are
unchanged. The guarded trampoline preserves the relocated native prologue and
return value. Runtime exports only K2Plugin_Start and K2Plugin_Tick. Requires
the installed loader, paws_runtime.marker and an entry in Mods/plugins.txt.
Network peers must use the same build. Already-stale old saves are not repaired
by a global ownership scan; that would itself disclose unseen captures.

Build: build.py --cc <tcc.exe> --out <G:/candidate>. Add --tests only for QA.
Test: test_capture.py --runtime <native dump> --dll <test DLL>
--deps <dependencies> (repeatable) --report <G:/report.json>.
Pinned native dump SHA-256:
B865D8206990C4F055C51DE857F0B09B88AB5EE3B6AE74EE5232134001AA591C.

Callback tests execute original native visibility and ghost-update routines;
only the ownership-change boundary and heavy AI registration are controlled.
They include hidden observers, pre-change viewers losing sight during capture,
no-fog mode, later unseen recaptures, all 32 record indices, native generations,
and forwarding full IDs through the extended registry API. The superseded
all-participant DLL fails the hidden-observer regression. Real three-peer
capture, save/load, normal scout movement and CRC runs are checked separately.

# Minimap return-contract crash hotfix

The user authorized publishing this fix on 2026-11-09. Targets: Arcane Wars
0.5.1-beta.3 and Vanilla/Immortals 0.5.0-beta.4, Pure runtime
1.3.72-pure.19-beta.4. All are beta; launcher and stable/legacy feeds retained.

The native inverse-coordinate routine returns its output pointer in EAX.
The old void callback discarded it, allowing the native caller's immediate
MOVSS [EAX] to crash. Correct both the callback and function-pointer typedef
and return the original pointer after optional coordinate adjustment.

Commands from the repository root, using the configured Python environment:

```text
python tools/MinimapCrashRelease/prepare.py baseline
python tools/MinimapCrashRelease/prepare.py build
python tools/MinimapCrashRelease/prepare.py archives
python tools/MinimapCrashRelease/prepare.py catalogs
python tools/MinimapCrashRelease/verify.py native
python tools/MinimapCrashRelease/verify.py catalog
python tools/MinimapCrashRelease/verify.py installers
python tools/MinimapCrashRelease/publish.py bundle
python tools/MinimapCrashRelease/publish.py gate
python tools/MinimapCrashRelease/publish.py source
python tools/MinimapCrashRelease/publish.py release
python tools/MinimapCrashRelease/publish.py promote
python tools/MinimapCrashRelease/publish.py readback
```

F:/PawsMinimapCrashPublish-20261109 holds baseline, frozen compiler inputs,
fixed native DLLs, all 12 helpers, package audit, signed candidates, compiled
tests, real installer fixtures and publication receipts. Old accepted inputs
are immutable and verified by their existing manifests. Only native inverse,
embedded DLL integrity metadata and release identities change. The sources
for all unchanged functionality and native header dependencies are retained.

Publication follows the established LobbyColorsRelease gates. Only explicitly
listed source paths are committed, preserving unrelated staged/dirty changes.
Assets are published under new immutable tags before catalog promotion.
No game is launched and no installed game file or original save is written.
The wall-corner and bridge experiments are excluded.

Compiled native tests execute x86 callbacks in Unicorn with explicit stubs.
The old DLL reproduces the dump's exact EIP/EAX; the fixed callback is tested
at three image layouts, four scales, all branch combinations, four callers.
This is not a claim of live multiplayer acceptance.

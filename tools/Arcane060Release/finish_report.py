from release_context import *
def main():
 cases=[read(f)for f in sorted((R/'qa-evidence/arcane060-savebuild').glob('*-savebuild.json'))];assert len(cases)==12 and all(c['passed']and c['healthNeverEdited']for c in cases)
 assert read(O/'product-smoke.json')['passed']and read(O/'product-smoke.json')['savedBridgeDefinitions']>0
 assert read(O/'installer-result.json')['passed'];matrix=read(O/'catalog-qa/result.json')
 evidence=dict(passed=True,version=VERSION,naturalCases=[dict(race=c['race'],material='wood'if c['wood']else'stone',healthNeverEdited=c['healthNeverEdited'],goldCost=c['nativeModifiedGoldCost'],earlySaveHp=c['earlySave']['before']['hp'],lateSaveHp=c['lateSave']['before']['hp'],fullHp=c['completed']['hp'],lateFullProcessRestart=c['lateSave']['fullProcessRestart'])for c in cases],selection=matrix,product=read(O/'product-smoke.json'),installer=read(O/'installer-result.json'),finishModels=56,dayCycleSeconds=1440)
 write(O/'verification.json',evidence)
 pub=O/'source-public';write(pub/'docs/verification-arcane-060-20261115.json',evidence)
 report='''# Arcane Wars 0.6.0-beta.1 verification — 2026-11-15

Twelve native construction cases passed: Human, Gauri, Drauga, Haroun, Undead and Shadow, each in wood and stone. The fixture prepares an unpaid bridge site; original workers perform payment and all subsequent construction. No HP setter, memory HP editing or fabricated completion is used in these cases. Only native game speed is accelerated; elapsed construction uses simulation time.

For each bridge: actual modified construction cost and stock debit; worker interruption and resumption without a second payment; early native RSG save/load with exact HP, paid metadata, stock and builder target; late save followed by full game/helper process restart; automatic resumed construction to full HP; scaffolding/effect cleanup. Paid Haroun bridges retain their intended autonomous growth while the worker is away. Shadow bridges have alpha 0.55 during construction and 1.0 afterward. These are controlled native race fixtures, not twelve fresh campaigns.

Fixed a release-blocking Undead completion smoke loop: 56 completion-model emitter controllers use CLAMP (40→44 cycle flags), preserving original emission visibility keys and particle properties. Temporary completion lifetime is seven seconds. Both Undead materials passed the complete natural/save/restart sequence after the fix. Bridge geometry, footing width (the accepted original 7.2), costs and simulation hooks remain unchanged.

The ordinary eight launch helpers derive from the verified published 0.5.1-beta.5 inputs. All eight pass five offline self-tests. Public paths/profile behavior are retained; no private R24 launcher, QA window placement, profile shim, test save or QA DLL is shipped. The bridge simulation payload is byte-identical to the accepted R24 payload. Nine ordinary modules are activated through the installed runtime marker. The complete day cycle is 1,440 seconds, with previous beta cache/scout fixes preserved and experimental rendering paths disabled.

Launcher 1.0.18: 10,800 catalog selections, 159,901 assertions and all eight helper winners passed. New texture dependencies occur only for full Arcane beta: patch-off, file-only, Vanilla, Immortals and stable selections remain unchanged. All fourteen package archives are manifest/hash validated. Ten optional texture dependencies preserve approved raster bytes and keep each archive below 232 MB; their total texture payload is 2,081,518,844 bytes. Raster storage is lossless. Existing approved racial HUDs and icons are retained.

The real transactional installer was exercised on an independent clean stock copy on G:, first with published beta.5, then 0.6.0, patch-off rollback and 0.6.0 reapplication. Stock Data.rwd/Music.rwd are independent copies, verified against the preserved base. Startup mount ownership was corrected so localization cannot override the feature depot; native multilingual strings put the Default block last as required by the engine. Startup/cache preparation excludes installer staging and rollback resources. Ordinary packaged helpers reached the native menu, loaded an actual unfinished saved bridge, and exited normally. The warm launch served all 53,886 font calls from cache without fallback. The native observer/profile redirect used for this smoke is test-only and excluded from archives.

Existing network evidence is retained: R17 three-process native multiplayer, bridge orders/bot construction, unfinished restart and crossings, 360 common CRC checkpoints over 359 simulation seconds, no mismatches and native sync-error counters zero. A new long multiplayer campaign was not run in this release pass; requested checks were save/load and natural construction.

Detailed machine-readable results are in verification-arcane-060-20261115.json. User-installed games, stable/Pure packages, launcher version and shared checkout/staging are not changed by this release preparation. Publication uses scoped commits on current public main and immutable prerelease assets.
'''
 (pub/'docs/verification-arcane-060-20261115.md').write_text(report,encoding='utf-8');(O/'REPORT.md').write_text(report,encoding='utf-8')
 write(O/'source-scope.json',dict(files=[f.relative_to(pub).as_posix()for f in pub.rglob('*')if f.is_file()]));print('FINAL_VERIFICATION_REPORT_READY',flush=True)
if __name__=='__main__':main()

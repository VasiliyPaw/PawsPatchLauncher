"""Build all product helpers from the accepted snapshot, preserving every switch."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];VERSION='0.5.1-beta.1'
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
BASE=REPO/'outputs/arcane-051-release-20261109/stable/helpers'
EXTRA=dict(resourceCacheRevision=1,resourcePrewarmRevision=1,animationCacheRevision=1,bufferReuseRevision=0,perFindCacheRevision=1,presentationRuntimeRevision=1,minimapWheelZoomRevision=1,inGameDayClockRevision=1,airReconRevision=1,fortStatisticsRevision=1,resignDialogCenterRevision=1)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def replace(s,a,b):assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b)
def run(args):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
def main():
 p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);src=out/'source';src.mkdir()
 baseline=json.loads((BASE/'build-report.json').read_text());native=a.native.resolve();meta=json.loads((native/'runtime.json').read_text());graphics=json.loads((native/'graphics/product.json').read_text())
 assert graphics.get('nativeBufferOwnership') is True and graphics.get('bufferReuseRevision')==0, 'Retired buffer reuse must not be reintroduced'
 assert sha(native/'PawsPresentation1372.dll')==meta['sha256'] and sha(native/'graphics/d3d9.dll')==graphics['sha256']
 for row in baseline.values():
  for source,h in row['sources'].items():assert sha(source)==h,source
 for name in ['paws_patch_versions.ini','paws_player_colors.ini']:
  b=(BASE/name).read_bytes();(out/name).write_bytes(b.replace(b'PawPatch=0.5.0',('PawPatch='+VERSION).encode()) if 'versions' in name else b)
 for source in {Path(p) for r in baseline.values() for p in r['args'] if p.lower().endswith('.cs')}:
  s=source.read_text(encoding='utf-8-sig')
  if source.name.endswith('LargeMapsIdentity.cs'):s=replace(s,'PatchVersion="0.5.0"','PatchVersion="'+VERSION+'"')
  if source.name.endswith('ReleaseStartup.cs'):
   anchor='                RandomMapPatch.Verify(memory, address, map);';s=replace(s,anchor,anchor+'\n                ResourceCachePatch.Install(game,memory,address,log);')
  if source.name.endswith('.generated.cs'):
   anchor='            startupComplete = true;';s=replace(s,anchor,'            PresentationRuntimePatch.Install(game,imageBase,gameDirectory,delegate(string m) { AppendLog(logPath,m); });\n            PresentationRuntimePatch.Ready();\n'+anchor)
   anchor='                EngineCrashFixesPatch.Tick();';s=replace(s,anchor,anchor+'\n                ResourceCachePatch.Tick();')
  if source.name.endswith('BuildFeatures.cs'):
   anchor=' + largeMaps + uniformUi';fragment=','.join('\\"'+k+'\\":'+str(v) for k,v in EXTRA.items());s=replace(s,anchor,' + ",'+fragment+'"'+anchor)
  (src/source.name).write_text(s)
 # The accepted anonymous-widget resign-dialog guard, across every variant.
 hud=out/'hud-builder.py';s=(REPO/'game/widescreen-ui/build_hud_native.py').read_text();s=replace(s,' mov edx,[eax+4]',' lea edx,[{image+0x491788}]\n cmp [eax],edx\n je editor\n mov edx,[eax+4]');hud.write_text(s)
 print(run([sys.executable,hud,'--legacy',LEG,'--out',out/'hud','--update-source',src/'13-GamePresentation1372.cs']).strip(),flush=True)
 s=(REPO/'game/resource-cache/ResourceCachePatch.cs').read_text();s=replace(s,'    static uint state;','    internal static uint StateAddress {get{return state;}}\n    static uint state;');(src/'ResourceCachePatch.cs').write_text(s)
 shutil.copy2(native/'cache-build/ResourceCachePayload.cs',src/'ResourceCachePayload.cs');shutil.copy2(REPO/'game/presentation-runtime/PresentationRuntimePatch.cs',src/'PresentationRuntimePatch.cs')
 (src/'PresentationRuntimePayload.cs').write_text('internal static class PresentationRuntimePayload { internal const string Sha256="'+meta['sha256']+'",GraphicsSha256="'+graphics['sha256']+'";internal const uint QueuedRva='+str(meta['exports']['PawPresentationQueued'])+',FrameRva='+str(meta['exports']['PawPresentationFrame'])+';}\n')
 extra=[src/n for n in ['ResourceCachePatch.cs','ResourceCachePayload.cs','PresentationRuntimePatch.cs','PresentationRuntimePayload.cs']];report={}
 for name,row in baseline.items():
  args=[]
  for arg in row['args']:
   if arg.startswith('/out:'):arg='/out:'+str(out/name)
   elif arg.lower().endswith('.cs'):arg=str(src/Path(arg).name)
   args.append(arg)
  args+=list(map(str,extra))+['/resource:'+str(native/'PawsPresentation1372.dll')+',PawPresentationNative'];run(args)
  f=json.loads(run([out/name,'--features']));expected=dict(row['features'],patchVersion=VERSION,**EXTRA);assert f==expected,(name,f,expected)
  tests={flag:run([out/name,flag]).strip() for flag in ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']}
  paths=[Path(x) for x in args if x.lower().endswith('.cs')]+[Path(x[10:].rsplit(',',1)[0]) for x in args if x.startswith('/resource:')]
  assert not any('PawHotJoinNative' in x or 'PawMultiplayerSavesNative' in x for x in args)
  report[name]=dict(sha256=sha(out/name),features=f,args=args,sources={str(p):sha(p) for p in paths},selfTests=tests)
  print('BETA_PRODUCT_HELPER_PASS',name,flush=True)
 (out/'build-report.json').write_text(json.dumps(report,indent=2));print('PRODUCT_EIGHT_HELPERS_PASS',VERSION,flush=True)
if __name__=='__main__':main()

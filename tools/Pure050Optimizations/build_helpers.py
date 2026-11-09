"""Port generic presentation optimizations into the four existing Pure variants."""
import re,shutil,subprocess
from context import *
EXTRA=dict(resourceCacheRevision=1,resourcePrewarmRevision=1,animationCacheRevision=1,bufferReuseRevision=1,perFindCacheRevision=1,bufferReuseBudgetMiB=32,gpuPrewarm=False)
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def main():
 out=OUT/'helpers-r1';out.mkdir(exist_ok=False);src=out/'source';src.mkdir();native=OUT/'native-r1';frozen=OUT/'frozen';base=read(frozen/'pure-build-report.json');meta=read(native/'build.json')
 for row in base.values():
  for p,h in row['sources'].items():assert sha(p)==h,p
 for source in {Path(p)for r in base.values()for p in r['args']if p.lower().endswith('.cs')}:
  s=source.read_text('utf-8-sig')
  if source.name.endswith('PureChannel.cs'):s=once(s,'Version = "1.3.72-pure.17-beta.1", PatchVersion = "0.5.0-beta.1"','Version = "'+RUNTIME+'", PatchVersion = "'+PATCH+'"')
  if source.name.endswith('Program.cs'):s=s.replace('1.3.72.17','1.3.72.18')
  if source.name.endswith('PureBetaRuntime.cs'):
   s=once(s,'            NightmareDifficultyData.Validate(root,PawAiOptions.Read(root));','            NightmareDifficultyData.Validate(root,PawAiOptions.Read(root));\n            if(ReleaseStartup.Hash(Path.Combine(root,"d3d9.dll"))!=PurePresentationRuntimePayload.GraphicsSha256)throw new InvalidDataException("Apply the complete Pure graphics runtime in the launcher.");')
   anchor='            LargeMapsPatch.Validate(memory,image);';s=once(s,anchor,anchor+'\n            ResourceCachePatch.Validate(memory,image);')
   anchor='            PureWorldOptionsPatch.Install(memory,image,log);';s=once(s,anchor,anchor+'\n            ResourceCachePatch.Install(game,memory,image,log);')
   anchor='            EngineCrashFixesPatch.Tick();';s=once(s,anchor,anchor+'\n            ResourceCachePatch.Tick();')
   fragment=','.join('\\"'+k+'\\":'+str(v).lower()for k,v in EXTRA.items());anchor='                + ",\\\"automaticMilitia\\\":false';s=once(s,anchor,'                + ",'+fragment+'"\n'+anchor)
  (src/source.name).write_text(s,encoding='utf-8')
 rc=(frozen/'arcane-managed/ResourceCachePatch.cs').read_text();anchor='    internal static void Install(Process game,IMemory m,uint image,Action<string> log)'
 rc=once(rc,anchor,'    internal static void Validate(IMemory m,uint image){for(int i=0;i<ResourceCachePayload.Sites.Length;i++)TerrainPatch.Expect(m,image+ResourceCachePayload.Sites[i],ResourceCachePayload.Original(i,image));}\n'+anchor)
 (src/'ResourceCachePatch.cs').write_text(rc);shutil.copy2(frozen/'arcane-managed/ResourceCachePayload.cs',src/'ResourceCachePayload.cs')
 managed=(frozen/'arcane-managed/PresentationRuntimePatch.cs').read_text();managed=managed.replace('PresentationRuntimePatch','PurePresentationRuntimePatch').replace('PresentationRuntimePayload','PurePresentationRuntimePayload').replace('PawPresentationNative','PawPurePresentationNative').replace('PawsPresentation1372.dll','PawsPurePresentation1372.dll')
 managed=re.sub(r'static readonly uint\[\] CodeSites=\{[^}]+\};','static readonly uint[] CodeSites={0xd5000,0xd5785,0x2a4570,0x2a47ee,0x2a43fa,0x2a4430,0x2a4466,0x2a449c,0x2b1ae6,0x18e3c8};',managed)
 managed=re.sub(r'log\("PRESENTATION_READY[^\n]+','log("PURE_PRESENTATION_READY revision=2; minimapZoom=1..4; step=0.1; dayClock=true; noActorHooks=true; localFind=true; animationCache=80/100/100; resourcePreparation=bounded; bufferReuse=32MiB; gpuPreload=false");',managed)
 assert 'reconRevision'not in managed and '0x206917'not in managed
 (src/'PurePresentationRuntimePatch.cs').write_text(managed)
 (src/'PurePresentationRuntimePayload.cs').write_text('internal static class PurePresentationRuntimePayload {internal const string Sha256="'+meta['sha256']+'",GraphicsSha256="'+meta['graphicsSha256']+'";internal const uint QueuedRva='+str(meta['exports']['PawPresentationQueued'])+',FrameRva='+str(meta['exports']['PawPresentationFrame'])+';}\n')
 report={}
 for name,row in base.items():
  args=[]
  for arg in row['args']:
   if arg.startswith('/out:'):arg='/out:'+str(out/name)
   elif arg.lower().endswith('.cs'):arg=str(src/Path(arg).name)
   elif arg.endswith(',PawPurePresentationNative'):arg='/resource:'+str(native/'PawsPurePresentation1372.dll')+',PawPurePresentationNative'
   args.append(arg)
  args += [str(src/'ResourceCachePatch.cs'),str(src/'ResourceCachePayload.cs')];run(args)
  features=__import__('json').loads(run([out/name,'--features']));expected=dict(row['features'],version=RUNTIME,patchVersion=PATCH,**EXTRA);assert features==expected,(name,features,expected)
  assert not features['matchRecoveryEnabled'] and not any('PAW_PURE_RECOVERY'in a for a in args)
  paths=[Path(p)for p in args if p.lower().endswith('.cs')]+[Path(p[10:].rsplit(',',1)[0])for p in args if p.startswith('/resource:')]
  report[name]=dict(sha256=sha(out/name),features=features,args=args,sources={str(p):sha(p)for p in paths});print('PURE_OPTIMIZED_HELPER_BUILT',name,flush=True)
 write(out/'build-report.json',report)
if __name__=='__main__':main()

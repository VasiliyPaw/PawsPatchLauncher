"""Compose Pure0.5 beta without recovery or Arcane gameplay/performance modules."""
import re,shutil,subprocess
from context import *
PATCH='0.5.0-beta.1';RUNTIME='1.3.72-pure.17-beta.1'
def once(text,old,new):assert text.count(old)==1,old[:100];return text.replace(old,new)
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def main():
 out=OUT/'beta-helpers-r4';out.mkdir(exist_ok=True);assert not (out/'build-report.json').exists();src=out/'source';src.mkdir(exist_ok=True);baseline=read(OUT/'stable-helpers-r2/build-report.json');ui=OUT/'ui-native-r3';world=OUT/'world-native-r2/native';registry=OUT/'registry-native-r1';report={}
 extra={
 'dynamicDayCycleSeconds':600,'mixedBiomeSelectionRevision':1,'nativeBiomeCount':3,
 'largeMapMaximum':2048,'objectRegistryCapacity':262143,'primaryActorCapacity':65535,
 'minimapWheelZoomRevision':1,'inGameDayClockRevision':1,'resignDialogCenterRevision':1,
 'presentationRuntimeRevision':1}
 for row in baseline.values():
  for path,h in row['sources'].items():assert sha(path)==h,path
 for source in {Path(p)for r in baseline.values()for p in r['args']if p.lower().endswith('.cs')}:
  text=source.read_text(encoding='utf-8-sig')
  if source.name.endswith('PureChannel.cs'):
   text=once(text,'"stable", Version = "1.3.72-pure.16", PatchVersion = "0.4.1"','"beta", Version = "'+RUNTIME+'", PatchVersion = "'+PATCH+'"')
  if source.name.endswith('Program.cs'):text=text.replace('1.3.72.16','1.3.72.17')
  if source.name.endswith('PureBetaRuntime.cs'):
   anchor='            CameraZoomPatch.Validate(memory, image);';text=once(text,anchor,'            LargeMapsPatch.Validate(memory,image);\n            PureWorldOptionsPatch.Validate(memory,image);\n'+anchor)
   anchor='            PawLobbyCompatibility.Prepare(root);';text=once(text,anchor,anchor+'\n            LargeMapsPatch.ConfigureWarning(InstalledFrequency(root),PawGameText.LanguageId);')
   anchor='            if(ai)';assert anchor not in text
   anchor='            if (ImprovedAi) AiPolicyRuntime.Install(memory, image, game.Id, root, log);';text=once(text,anchor,anchor+'\n            LargeMapsPatch.Install(memory,image,log);\n            PureWorldOptionsPatch.Install(memory,image,log);')
   anchor='            GraphicsDiagnostics.Start(game, root, log);';text=once(text,anchor,'            PurePresentationRuntimePatch.Install(game,image,root,log);\n            PurePresentationRuntimePatch.Ready();\n'+anchor)
   anchor='        internal static void Prepare(string root)';method='''        static string InstalledFrequency(string root){
            var json=new JavaScriptSerializer {MaxJsonLength=16*1024*1024};
            var state=(Dictionary<string,object>)json.DeserializeObject(File.ReadAllText(Path.Combine(root,@".pawpatch\\state.json")));
            var settings=(Dictionary<string,object>)state["appliedSettings"];object value;
            return settings.TryGetValue("roamingSpawnMode",out value)?Convert.ToString(value):"standard";
        }
''';text=once(text,anchor,method+anchor)
   anchor='                + ",\\\"automaticMilitia\\\":false';fields=','.join('\\"'+k+'\\":'+str(v)for k,v in extra.items());text=once(text,anchor,'                + ",'+fields+'"\n'+anchor)
  (src/source.name).write_text(text,encoding='utf-8')
 for source in [world/'PureWorldOptionsPatch.cs',registry/'ExtendedRegistryPayload.cs',REPO/'game/large-maps/ExtendedRegistryPatch.cs',ui/'PurePresentationRuntimePatch.cs',ui/'PurePresentationRuntimePayload.cs']:
  target=src/('LargeMapsPatch.cs'if source.name=='ExtendedRegistryPatch.cs'else source.name);shutil.copy2(source,target)
 # Include the three extra native dialogs and the anonymous surrender window.
 generator=(REPO/'game/widescreen-ui/build_hud_native.py').read_text();generator=once(generator,"('ConnectionStatusDialog','dialog'),","('ConnectionStatusDialog','dialog'),('GameMenuDialog','editor'),('StagingFileSavedDialog','editor'),('StagingFileLoadSavedDialog','editor'),")
 generator=once(generator,' mov edx,[eax+4]',' lea edx,[{image+0x491788}]\n cmp [eax],edx\n je editor\n mov edx,[eax+4]\n test edx,edx\n jz template_name\n cmp word ptr[edx],0\n jne named\n template_name:\n mov edx,[eax+0x1c]\n named:');(out/'hud-builder.py').write_text(generator)
 print(run([sys.executable,out/'hud-builder.py','--legacy',LEG,'--out',out/'hud','--update-source',src/'13-GamePresentation1372.cs']).strip(),flush=True)
 extras=[src/n for n in ['PureWorldOptionsPatch.cs','ExtendedRegistryPayload.cs','LargeMapsPatch.cs','PurePresentationRuntimePatch.cs','PurePresentationRuntimePayload.cs']]
 for name,row in baseline.items():
  args=[]
  for arg in row['args']:
   if arg.startswith('/out:'):arg='/out:'+str(out/name)
   elif arg.lower().endswith('.cs'):arg=str(src/Path(arg).name)
   args.append(arg)
  assert not any('PAW_PURE_RECOVERY'in a for a in args)
  args+=list(map(str,extras))+['/resource:'+str(ui/'PawsPurePresentation1372.dll')+',PawPurePresentationNative'];run(args)
  features=json.loads(run([out/name,'--features']));expected=dict(row['features'],version=RUNTIME,patchVersion=PATCH,channel='beta',**extra);assert features==expected,(features,expected)
  assert features['matchRecoveryEnabled'] is False
  paths=[Path(x)for x in args if x.lower().endswith('.cs')]+[Path(x[10:].rsplit(',',1)[0])for x in args if x.startswith('/resource:')]
  report[name]=dict(sha256=sha(out/name),features=features,args=args,sources={str(p):sha(p)for p in paths});print('PURE_050_HELPER_BUILT',name,flush=True)
 write(out/'build-report.json',report)
if __name__=='__main__':main()

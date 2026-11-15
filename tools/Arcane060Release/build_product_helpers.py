"""Ordinary eight-variant helpers, from hash-verified beta.5 public inputs.

Keep production profiles and all variant switches; carry the accepted R24
payload changes and startup settings into a normal installation.
"""
from pathlib import Path
import sys,json,hashlib,subprocess,os,shutil,re
P=Path(__file__).resolve().parent;R24=P.parent/'r24-racial-build-beta-20261114';R=Path((P/'target.txt').read_text());VERSION='0.6.0-beta.1'
OUT=P.parents[1]/'outputs/arcane-060-beta-release-20261115';OUT.mkdir(exist_ok=True);D=OUT/'helpers/source';D.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update(TEMP=str(P/'Temp'),TMP=str(P/'Temp'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
reports=json.loads((P/'beta5-report.json').read_text())
for f in(P/'beta5-inputs').glob('*.cs'):shutil.copy2(f,D/f.name)
for name in ['21-BuildFeatures.cs','56-SelectionScrollPayload.cs','60-GroupMovementSpeedPatch.cs','61-GroupMovementSpeedPayload.cs','MixedBiomesPayload.cs','PresentationRuntimePayload.cs']:
 shutil.copy2(R24/'helper-source'/name,D/name)
f=D/'25-LargeMapsIdentity.cs';s=f.read_text();assert '0.5.1-beta.5'in s;f.write_text(s.replace('0.5.1-beta.5',VERSION))
# Explicit test paths remain opt-in; normal launches retain real user profiles.
(D/'PawRuntimePaths.cs').write_text('''using System;using System.IO;
internal static class PawRuntimePaths {
 static string Resolve(string variable,Environment.SpecialFolder fallback){string p=Environment.GetEnvironmentVariable(variable);return string.IsNullOrWhiteSpace(p)?Environment.GetFolderPath(fallback):Path.GetFullPath(p);}
 internal static string Documents {get{return Resolve("PAWS_TEST_DOCUMENTS",Environment.SpecialFolder.MyDocuments);}}
 internal static string AppData {get{return Resolve("PAWS_TEST_APPDATA",Environment.SpecialFolder.LocalApplicationData);}}
}
''')
for name,old,new in [('44-PawAssistantRuntime.cs','Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)','PawRuntimePaths.AppData'),('49-PawAssistantParties.cs','Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)','PawRuntimePaths.Documents')]:
 f=D/name;s=f.read_text();assert old in s;f.write_text(s.replace(old,new))
# Reuse the accepted font-key calculation, with production cache/profile roots.
wrapper=(P.parent/'r24-integration-20261113/Launcher.cs').read_text();body=wrapper[:wrapper.index(' [STAThread] static int Main(')]
body=body.replace('class PawsRiversTest {','internal static class PawRuntimeStartup {').replace('typeof(PawsRiversTest)','typeof(PawRuntimeStartup)').replace('"PawsInstalledRuntime.exe",','').replace('Path.Combine(root,"Documents/Kohan2/data/User/UVars.tgi")','Path.Combine(PawRuntimePaths.Documents,"Kohan2/data/User/UVars.tgi")')
body+='''
 internal static void Configure(ProcessStartInfo p,string game) {
  p.UseShellExecute=false;root=Path.GetFullPath(game);
  cache=Path.Combine(PawRuntimePaths.AppData,"PawsPatch","Startup",Digest(Encoding.UTF8.GetBytes(root.ToLowerInvariant())).Substring(0,16));
  foreach(string name in p.EnvironmentVariables.Keys.Cast<string>().ToArray())
   if(new[]{"PAWS_STARTUP_","PAWS_PROFILE_","PAWS_TGI_","PAWS_MAPGEN_","PAWS_FONT_"}.Any(prefix=>name.StartsWith(prefix,StringComparison.OrdinalIgnoreCase)))p.EnvironmentVariables.Remove(name);
  foreach(string k in new[]{"MEMORY_ESTIMATE","TRIM","TOKENS","FIELDS"})p.EnvironmentVariables["PAWS_STARTUP_"+k]="1";
  foreach(string k in new[]{"LOOKUP","TYPE_CACHE","LOOKUP_VALIDATE","LOOKUP_DIAG","LOOKUP_DIAGNOSTIC","TOKENS_VALIDATE","TOKEN_DIGEST","FIELDS_VALIDATE","TRIM_VALIDATE"})p.EnvironmentVariables["PAWS_STARTUP_"+k]="0";
  p.EnvironmentVariables["PAWS_PROFILE_REMAINING"]="0";p.EnvironmentVariables["PAWS_TGI_CACHE_MODE"]="off";p.EnvironmentVariables["PAWS_MAPGEN_INDEX"]="off";p.EnvironmentVariables["PAWS_FONT_CACHE_MODE"]="off";
  try {Directory.CreateDirectory(cache);p.EnvironmentVariables["PAWS_FONT_CACHE_KEY"]=FontKey(game);p.EnvironmentVariables["PAWS_FONT_CACHE_PATH"]=Path.Combine(cache,"font-metrics.bin");p.EnvironmentVariables["PAWS_FONT_CACHE_MODE"]="replay";}
  catch(Exception e){try{if(Directory.Exists(cache))File.WriteAllText(Path.Combine(cache,"font-preparation-error.txt"),e.ToString());}catch{}}
 }
}
'''
oldloop='foreach(string p in Directory.EnumerateFiles(game,"*",SearchOption.AllDirectories))'
newloop='foreach(string p in Directory.EnumerateFiles(game).Concat(Directory.EnumerateDirectories(game).Where(d=>!String.Equals(Path.GetFileName(d),".pawpatch",StringComparison.OrdinalIgnoreCase)&&!String.Equals(Path.GetFileName(d),"Logs",StringComparison.OrdinalIgnoreCase)).SelectMany(d=>Directory.EnumerateFiles(d,"*",SearchOption.AllDirectories))))'
assert oldloop in body;body=body.replace(oldloop,newloop)
(D/'PawRuntimeStartup.cs').write_text(body)
required=json.loads((OUT/'native/build-report.json').read_text())
validation='''
 static void Validate(string game) {
  if(!File.Exists(Path.Combine(game,"paws_runtime.marker")))throw new InvalidDataException("Paw's Patch 0.6.0 runtime data is missing. Apply the update in the launcher.");
  string[] names={NAMES};string[] hashes={HASHES};
  for(int i=0;i<names.Length;i++){string path=Path.Combine(game,"Mods",names[i]);if(!File.Exists(path))throw new FileNotFoundException("Missing Paw's Patch runtime module: "+names[i]);using(var stream=File.OpenRead(path))using(var h=SHA256.Create())if(!String.Equals(BitConverter.ToString(h.ComputeHash(stream)).Replace("-",""),hashes[i],StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Paw's Patch runtime module differs: "+names[i]);}
  string loader=Path.Combine(game,"avifil32.dll");if(!File.Exists(loader))throw new FileNotFoundException("Paw's Patch module loader is missing.");
  using(var stream=File.OpenRead(loader))using(var h=SHA256.Create())if(!String.Equals(BitConverter.ToString(h.ComputeHash(stream)).Replace("-",""),"LOADERHASH",StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Paw's Patch module loader differs.");
  string config=Path.Combine(game,"Mods/plugins.txt");if(!File.Exists(config))throw new FileNotFoundException("Paw's Patch module list is missing.");
  var active=File.ReadAllLines(config).Select(x=>x.Trim()).Where(x=>x.Length!=0&&!x.StartsWith("#")).ToArray();foreach(string name in names)if(!active.Contains(name,StringComparer.OrdinalIgnoreCase))throw new InvalidDataException("Required Paw's Patch module is disabled: "+name);
 }
'''
validation=validation.replace('{NAMES}',','.join('"'+n+'"'for n in required)).replace('{HASHES}',','.join('"'+v['sha256']+'"'for v in required.values())).replace('LOADERHASH',sha(R/'sandbox/avifil32.dll'))
# Array initializers need braces after substitution.
validation=validation.replace('string[] names=','string[] names={').replace(';string[] hashes=','};string[] hashes={').replace(';\n  for(int i=0','};\n  for(int i=0')
body=body.replace('  p.UseShellExecute=false;root=Path.GetFullPath(game);','  Validate(game);p.UseShellExecute=false;root=Path.GetFullPath(game);')
body=body[:-2]+validation+'}\n';(D/'PawRuntimeStartup.cs').write_text(body)
f=D/'21-BuildFeatures.cs';s=f.read_text();anchor=' + largeMaps + uniformUi';assert anchor in s
extra=r',\"roadsAndBridgesRevision\":1,\"racialBridgeConstructionRevision\":1,\"mapShapesAndRiversRevision\":1,\"wideBiomesRevision\":1,\"startupOptimizationsRevision\":1'
f.write_text(s.replace(anchor,' + "'+extra+'"'+anchor))
for f in D.glob('*.generated.cs'):
 s=f.read_text();old='Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)';s=s.replace(old,'PawRuntimePaths.Documents')
 anchor='game = Process.Start(start);'
 if anchor not in s:
  candidates=[line.strip()for line in s.splitlines()if'Process.Start(start)'in line];assert len(candidates)==1,candidates;anchor=candidates[0]
 s=s.replace(anchor,'PawRuntimeStartup.Configure(start,gameDirectory);\n                '+anchor);f.write_text(s)
results={}
for name,row in reports.items():
 target=OUT/'helpers'/name;args=[]
 for arg in row['args']:
  if arg.startswith('/out:'):arg='/out:'+str(target)
  elif arg.lower().endswith('.cs'):arg=str(D/Path(arg).name)
  elif arg.startswith('/resource:'):
   src,rname=arg[10:].rsplit(',',1);f=R24/'PawsPresentation1372.dll'if rname=='PawPresentationNative'else P/'beta5-inputs'/Path(src).name;assert f.is_file(),f;arg='/resource:'+str(f)+','+rname
  args.append(arg)
 args+=list(map(str,[D/'PawRuntimePaths.cs',D/'PawRuntimeStartup.cs']))
 cp=subprocess.run(args,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert cp.returncode==0,cp.stdout
 shutil.copy2(R/'sandbox/paws_player_colors.ini',target.parent/'paws_player_colors.ini')
 features=json.loads(subprocess.check_output([str(target),'--features'],env=env,text=True));assert features['patchVersion']==VERSION and features['dynamicDayCycleSeconds']==1440 and features['groupMovementSpeedRevision']==3 and features['resourceCacheRamPercent']==90 and features['aircraftFallRecoveryRevision']==1
 for k in ['resourcePrewarmRevision','perFindCacheRevision','bufferReuseRevision','hotJoinRevision']:assert features[k]==0
 # Variant flags are unchanged: color, sync, hostility and every other switch.
 expected=dict(row['features']);expected.update({k:features[k]for k in ['patchVersion','dynamicDayCycleSeconds','groupMovementSpeedRevision']})
 for k in features:
  if k in row['features']:assert features[k]==expected[k],(name,k,row['features'][k],features[k])
 tests={}
 for flag in ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']:
  cp=subprocess.run([str(target),flag],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert cp.returncode==0,(name,flag,cp.stdout);tests[flag]=cp.stdout.strip()
 sources=[Path(a)for a in args if a.lower().endswith('.cs')]+[Path(a[10:].rsplit(',',1)[0])for a in args if a.startswith('/resource:')]
 results[name]={'sha256':sha(target),'features':features,'args':args,'sources':{str(f):sha(f)for f in sources},'selfTests':tests}
 print('ORDINARY_060_HELPER_PASS',name,flush=True)
(OUT/'helpers/build-report.json').write_text(json.dumps(results,indent=2));print('EIGHT_PRODUCTION_HELPERS_READY',VERSION,flush=True)

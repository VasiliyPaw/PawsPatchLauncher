from context import *
import shutil,zipfile
Q=O/'catalog-qa';Q.mkdir(exist_ok=True)
for channel in ['stable','beta']:
 for label,folder in [('before','before'),('after','signed')]:write(Q/(label+'-'+channel+'.json'),verify(read(O/folder/'feed/v3'/f'{channel}.json'),key()))
shutil.copy2(O/'installer-qa/QA.csproj',Q/'QA.csproj')
text=(Q/'QA.csproj').read_text().replace(str(O/'installer-qa/launcher'),str(O/'installer-qa/launcher'));(Q/'QA.csproj').write_text(text)
write(Q/'helper-hashes.json',{n:r['sha256']for n,r in read(O/'helpers/build-report.json').items()})
files={}
for p in read(O/'packages.json'):
 if p['id'].startswith('arcane-biome'):continue
 with zipfile.ZipFile(O/'assets'/(p['id']+'-'+p['version']+'.zip'))as z:files[p['id']]={r['path'].lower():r['sha256']for r in json.loads(z.read('module.json'))['files']}
write(Q/'new-files.json',files)
(Q/'Program.cs').write_text(r'''using System.Text.Json;using PawsPatchLauncher;
var root=args[0];var opt=new JsonSerializerOptions{PropertyNameCaseInsensitive=true};
T Read<T>(string n)=>JsonSerializer.Deserialize<T>(File.ReadAllText(Path.Combine(root,n)),opt)!;
var helpers=Read<Dictionary<string,string>>("helper-hashes.json");var files=Read<Dictionary<string,Dictionary<string,string>>>("new-files.json");int selections=0,checks=0;var seen=new HashSet<string>();
void Check(bool b,string s){checks++;if(!b)throw new Exception(s);}
foreach(var channel in new[]{"stable","beta"}){
 var before=Read<ChannelManifest>("before-"+channel+".json");var after=Read<ChannelManifest>("after-"+channel+".json");
 foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})foreach(var patch in new[]{false,true})foreach(var data in new[]{false,true})foreach(var text in new[]{"en","ru","uk","cs","de","fr"})foreach(var voice in new[]{"en","ru","de","fr"})
 foreach(var spawn in new[]{"standard","x2","x4"})for(int bits=0;bits<(mod!=GameMod.ArcaneWars&&patch?64:1);bits++){
  bool B(int b)=>(bits&(1<<b))!=0;
  UserSettings Settings(){var ss=new UserSettings(){Mod=mod,Channel=channel,PawPatchEnabled=patch,VanillaPawPatchEnabled=patch,ImmortalsPawPatchEnabled=patch,DataOnly=data,GameTextLanguage=text,RussianLocalization=text=="ru",GameVoiceLanguage=voice,CustomPlayerColors=B(0),DesyncMode=B(1)?"continue":"official",IndependentHostility=B(2),AdditionalRoamingCompanies=B(3),SiegeBalance=B(4),DisablePowersAndShards=B(5),RoamingSpawnMode=spawn};var pp=GameMod.PureComponents(ss);pp.Colors=B(0);pp.IgnoreDesync=B(1);pp.WoundedLairDefenders=B(5);return ss;}
  var ps=GameMod.PureComponents(Settings());
  var a=EffectiveSettings.ForFeed(Settings(),before);var b=EffectiveSettings.ForFeed(Settings(),after);
  var x=GamePackageSelector.Select(before,a,a.RussianLocalization,a.CustomPlayerColors);var y=GamePackageSelector.Select(after,b,b.RussianLocalization,b.CustomPlayerColors);selections++;
  var full=channel=="beta"&&mod!=GameMod.ArcaneWars&&patch&&!data;var pure=channel=="beta"&&mod!=GameMod.ArcaneWars&&patch;
  Check(x.Select(p=>p.Id).Order().SequenceEqual(y.Select(p=>p.Id).Order()),"package selection changed");
  foreach(var p in y){var old=x.Single(q=>q.Id==p.Id);if(pure&&files.ContainsKey(p.Id))Check(p.Version==(p.Id=="pure-fixes-runtime"?"1.3.72-pure.21-beta.7":"0.5.0-beta.7"),"version");else Check(JsonSerializer.Serialize(p)==JsonSerializer.Serialize(old),"unrelated package changed "+p.Id);}
  var exe=GameExecutableSelector.Select(new LauncherConfiguration(),b,after);Check(exe==GameExecutableSelector.Select(new LauncherConfiguration(),a,before),"executable selection changed");
  if(full){Check(helpers.ContainsKey(exe),"unexpected helper "+exe);string? hash=null;foreach(var p in y.OrderBy(p=>p.Priority).ThenBy(p=>p.Id,StringComparer.OrdinalIgnoreCase))if(files.TryGetValue(p.Id,out var rows)&&rows.TryGetValue(exe.ToLowerInvariant(),out var h))hash=h;Check(hash==helpers[exe],"wrong helper winner");seen.Add(exe);}
 }
}
Check(seen.Count==4,"not all helpers covered");File.WriteAllText(Path.Combine(root,"result.json"),JsonSerializer.Serialize(new{passed=true,selections,checks,helpers=seen.Count,launcher=typeof(ModuleInstaller).Assembly.GetName().Version!.ToString()}));Console.WriteLine($"CATALOG_PASS {selections} selections; {checks} assertions; {seen.Count} helpers");
''')
print(run([SDK,'run','--project',Q/'QA.csproj','-c','Release','--',Q],O/'catalog-checks.log'),flush=True)


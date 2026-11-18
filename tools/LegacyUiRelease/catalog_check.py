from context import *
from qa import project
import zipfile
Q=O/'catalog-qa';project(Q)
for channel in['stable','beta']:
 for label,folder in[('before','before'),('after','signed')]:write(Q/(label+'-'+channel+'.json'),verify(read(O/folder/'feed/v3'/f'{channel}.json'),key()))
helpers={n:r['sha256']for group in['arcane','pure']for n,r in read(O/group/'helpers/build-report.json').items()};write(Q/'helper-hashes.json',helpers)
files={}
for p in read(O/'packages.json'):
 with zipfile.ZipFile(read(O/'package-audit.json')[p['id']]['path'])as z:files[p['id']]={r['path'].lower():r['sha256']for r in json.loads(z.read('module.json'))['files']}
write(Q/'new-files.json',files);write(Q/'versions.json',{p['id']:p['version']for p in read(O/'packages.json')})
(Q/'Program.cs').write_text(r'''using System.Text.Json;using PawsPatchLauncher;
var root=args[0];var opt=new JsonSerializerOptions{PropertyNameCaseInsensitive=true};
T Read<T>(string n)=>JsonSerializer.Deserialize<T>(File.ReadAllText(Path.Combine(root,n)),opt)!;
var helpers=Read<Dictionary<string,string>>("helper-hashes.json");var files=Read<Dictionary<string,Dictionary<string,string>>>("new-files.json");var versions=Read<Dictionary<string,string>>("versions.json");int selections=0,checks=0;var seen=new HashSet<string>();
void Check(bool b,string s){checks++;if(!b)throw new Exception(s);}
foreach(var channel in new[]{"stable","beta"}){
 var before=Read<ChannelManifest>("before-"+channel+".json");var after=Read<ChannelManifest>("after-"+channel+".json");
 foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})foreach(var patch in new[]{false,true})foreach(var data in new[]{false,true})foreach(var text in new[]{"en","ru","uk","cs","de","fr"})foreach(var voice in new[]{"en","ru","de","fr"})
 foreach(var spawn in new[]{"standard","x2","x4"})for(int bits=0;bits<(patch&&!data?64:1);bits++){
  bool B(int b)=>(bits&(1<<b))!=0;
  UserSettings Settings(){var ss=new UserSettings(){Mod=mod,Channel=channel,PawPatchEnabled=patch,VanillaPawPatchEnabled=patch,ImmortalsPawPatchEnabled=patch,DataOnly=data,GameTextLanguage=text,RussianLocalization=text=="ru",GameVoiceLanguage=voice,CustomPlayerColors=B(0),DesyncMode=B(1)?"continue":"official",IndependentHostility=B(2),AdditionalRoamingCompanies=B(3),SiegeBalance=B(4),DisablePowersAndShards=B(5),RoamingSpawnMode=spawn};var pp=GameMod.PureComponents(ss);pp.Colors=B(0);pp.IgnoreDesync=B(1);pp.WoundedLairDefenders=B(5);return ss;}
  var a=EffectiveSettings.ForFeed(Settings(),before);var b=EffectiveSettings.ForFeed(Settings(),after);
  var x=GamePackageSelector.Select(before,a,a.RussianLocalization,a.CustomPlayerColors);var y=GamePackageSelector.Select(after,b,b.RussianLocalization,b.CustomPlayerColors);selections++;
  bool full=channel=="beta"&&patch&&!data;
  Check(x.Select(p=>p.Id).Order().SequenceEqual(y.Select(p=>p.Id).Order()),"package selection changed");
  foreach(var p in y){var old=x.Single(q=>q.Id==p.Id);if(channel=="beta"&&files.ContainsKey(p.Id))Check(p.Version==versions[p.Id],"version");else Check(JsonSerializer.Serialize(p)==JsonSerializer.Serialize(old),"unrelated package changed "+p.Id);}
  var exe=GameExecutableSelector.Select(new LauncherConfiguration(),b,after);Check(exe==GameExecutableSelector.Select(new LauncherConfiguration(),a,before),"executable selection changed");
  if(full){Check(helpers.ContainsKey(exe),"unexpected helper "+exe);string? hash=null;foreach(var p in y.OrderBy(p=>p.Priority).ThenBy(p=>p.Id,StringComparer.OrdinalIgnoreCase))if(files.TryGetValue(p.Id,out var rows)&&rows.TryGetValue(exe.ToLowerInvariant(),out var h))hash=h;Check(hash==helpers[exe],"wrong helper winner");seen.Add(exe);
   var state=new InstallState{AppliedSettings=a,Modules=x.ToDictionary(p=>p.Id,p=>new InstalledModule{Enabled=true,Version=p.Version,ArchiveSha256=p.Sha256,Priority=p.Priority})};Check(UpdateDetector.HasRemoteUpdate(state,y,_=>false),"update not offered");
   var common=mod==GameMod.ArcaneWars?"common-ui":"pure-beta-common";Check(y.Any(p=>p.Id==common),"missing HD package");Check(!files[common].Keys.Any(n=>n.StartsWith("paws-hd-ui")),"HD payload retained");Check(files[common].Keys.Count(n=>n.Contains("pawuniform")&&n.EndsWith(".tga"))==63,"old frame paths missing");Check(files[common].Keys.Count(n=>n.StartsWith("skins/")&&n.EndsWith(".rwd"))==6,"stock skins missing");Check(files[common].ContainsKey("startup/autoexec.txt"),"priority depot not mounted");
  }
 }
}
Check(seen.Count==12,"not all helpers covered");File.WriteAllText(Path.Combine(root,"result.json"),JsonSerializer.Serialize(new{passed=true,selections,checks,helpers=seen.Count,launcher=typeof(ModuleInstaller).Assembly.GetName().Version!.ToString()}));Console.WriteLine($"CATALOG_PASS {selections} selections; {checks} assertions; {seen.Count} helpers");
''')
print(run([SDK,'run','--project',Q/'QA.csproj','-c','Release','--',Q],O/'catalog-checks.log'),flush=True)

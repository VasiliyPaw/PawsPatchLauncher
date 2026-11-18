from context import *
from qa import project
Q=O/'public-client-check';project(Q);write(Q/'before.json',verify(read(O/'before/feed/v3/beta.json'),key()));write(Q/'expected.json',verify(read(O/'signed/feed/v3/beta.json'),key()))
(Q/'Program.cs').write_text(r'''using System.Text.Json;using PawsPatchLauncher;
var root=args[0];var opt=new JsonSerializerOptions{PropertyNameCaseInsensitive=true};var cfg=JsonSerializer.Deserialize<LauncherConfiguration>(File.ReadAllText(args[1]),opt)!;cfg.CacheRoot=Path.Combine(root,"cache");var c=new FeedClient(cfg);var f=await c.GetChannelAsync("beta")??throw new Exception("Missing public feed");var expected=JsonSerializer.Deserialize<ChannelManifest>(File.ReadAllText(Path.Combine(root,"expected.json")),opt)!;
if(f.Packages.Single(p=>p.Id=="pawpatch-core").Version!="0.6.0-beta.6"||f.Packages.Single(p=>p.Id=="pure-fixes-data").Version!="0.5.0-beta.10"){Console.WriteLine("PUBLIC_CLIENT_PENDING");return;}
var before=JsonSerializer.Deserialize<ChannelManifest>(File.ReadAllText(Path.Combine(root,"before.json")),opt)!;var results=new List<object>();
foreach(var mod in new[]{GameMod.ArcaneWars,GameMod.Vanilla,GameMod.Immortals}){
 var s=new UserSettings{Mod=mod,Channel="beta",PawPatchEnabled=true,VanillaPawPatchEnabled=true,ImmortalsPawPatchEnabled=true,GameTextLanguage="en",RussianLocalization=false,GameVoiceLanguage="en"};s=EffectiveSettings.ForFeed(s,f);var selected=GamePackageSelector.Select(f,s,false,false);var old=GamePackageSelector.Select(before,s,false,false);
 var state=new InstallState{AppliedSettings=s,Modules=old.ToDictionary(p=>p.Id,p=>new InstalledModule{Enabled=true,Version=p.Version,ArchiveSha256=p.Sha256,Priority=p.Priority})};if(!UpdateDetector.HasRemoteUpdate(state,selected,_=>false)||!UpdateDetector.HasModuleChanges(state,selected))throw new Exception("No update for "+mod);
 foreach(var p in selected)if(JsonSerializer.Serialize(p)!=JsonSerializer.Serialize(expected.Packages.Single(q=>q.Id==p.Id)))throw new Exception("Unexpected public package "+p.Id);
 string v=PawPatchVersions.ForChannel(f,mod)!;if(v!=(mod==GameMod.ArcaneWars?"0.6.0-beta.6":"0.5.0-beta.10"))throw new Exception("Wrong displayed version");
 var changed=selected.Where(p=>!old.Any(q=>q.Id==p.Id&&q.Version==p.Version&&q.Sha256==p.Sha256)).Select(p=>p.Id).Order().ToArray();if(mod==GameMod.ArcaneWars&&(selected.Count(p=>p.Id=="arcane-biome-textures")!=1||selected.Any(p=>p.Id.StartsWith("arcane-biome-textures-"))))throw new Exception("Terrain not grouped");results.Add(new{mod,version=v,updateOffered=true,changedPackages=changed,executable=GameExecutableSelector.Select(cfg,s,f)});
}
File.WriteAllText(Path.Combine(root,"result.json"),JsonSerializer.Serialize(new{passed=true,results,launcher=typeof(ModuleInstaller).Assembly.GetName().Version!.ToString()}));Console.WriteLine("PUBLIC_CLIENT_ALL_BETAS_PASS");
''')
print(run([SDK,'run','--project',Q/'QA.csproj','-c','Release','--',Q,S/'src/PawsPatchLauncher/launcher.config.json'],O/'public-client-check.log'),flush=True)

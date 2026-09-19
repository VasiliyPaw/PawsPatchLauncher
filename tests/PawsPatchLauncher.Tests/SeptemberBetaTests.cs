using System.Diagnostics;
using System.Net.Http;
using System.Text.Json;
using PawsPatchLauncher;

// Actual installer acceptance for the paired beta publication. Never launches a game.
internal static class SeptemberBetaTests
{
    static void Check(bool ok,string why){if(!ok)throw new InvalidDataException(why);}
    static ChannelManifest Feed(string path,string key){
        var e=JsonSerializer.Deserialize(File.ReadAllBytes(path),LauncherJsonContext.Default.SignedFeedEnvelope)!;
        var bytes=Convert.FromBase64String(e.Payload);Check(CryptoAndIO.VerifySignature(bytes,e.Signature,key),"Feed signature");
        return JsonSerializer.Deserialize(bytes,LauncherJsonContext.Default.ChannelManifest)!;
    }
    static UserSettings Selection(string mod,int mask,bool enabled=true,bool data=false,string language="en"){
        var s=new UserSettings{Mod=mod,Channel="beta",RussianLocalization=language=="ru",GameTextLanguage=language,
            GameVoiceLanguage="en",DataOnly=data};
        GameMod.SetPawPatch(s,true);GameMod.SetColors(s,(mask&1)!=0);GameMod.SetDesync(s,(mask&2)!=0);
        if(mod==GameMod.ArcaneWars){s.DesyncMode=(mask&2)!=0?"continue":"official";s.IndependentHostility=(mask&4)!=0;}
        if(!enabled)GameMod.SetPawPatch(s,false);
        return s;
    }
    internal static async Task RunAsync(string repoArg,string stageArg,string gameRoot){
        string repo=Path.GetFullPath(repoArg),stage=Path.GetFullPath(stageArg),root=Path.Combine(stage,"install-fixture");
        Check(!Directory.Exists(root)&&!root.Equals(Path.GetFullPath(gameRoot),StringComparison.OrdinalIgnoreCase),"Fresh isolated fixture required");
        Directory.CreateDirectory(root);
        var config=JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(repo,"src/PawsPatchLauncher/launcher.config.json")),LauncherJsonContext.Default.LauncherConfiguration)!;
        var feed=Feed(Path.Combine(stage,"publication/test-feeds/beta.json"),config.PublicKeyPem);
        var old=Feed(Path.Combine(stage,"publication/previous/beta.json"),config.PublicKeyPem);
        Check(feed.PatchGuide!.Version=="0.3.2-beta.2"&&feed.PlayerColorCount==39,"Arcane identity");
        var updated=new HashSet<string>{"pawpatch-core","common-ui","player-colors","desync-continue","pure-fixes-data","pure-fixes-runtime","pure-player-colors"};
        Check(feed.Packages.Where(p=>!updated.Contains(p.Id)).Select(p=>p.Id+p.Sha256).SequenceEqual(old.Packages.Where(p=>!updated.Contains(p.Id)).Select(p=>p.Id+p.Sha256)),"Unrelated payload identity");
        int selections=0,transitions=0,frameChecks=0,preflights=0;var seen=new HashSet<string>();
        foreach(string mod in new[]{GameMod.ArcaneWars,GameMod.Vanilla,GameMod.Immortals})
        foreach(string language in new[]{"en","ru","de","fr","cs","uk"})foreach(bool data in new[]{false,true})foreach(bool enabled in new[]{false,true})
        for(int mask=0;mask<(mod==GameMod.ArcaneWars?8:4);mask++){
            var s=EffectiveSettings.ForFeed(Selection(mod,mask,enabled,data,language),feed);
            var ps=GamePackageSelector.Select(feed,s,s.RussianLocalization,s.CustomPlayerColors);
            if(data)Check(ps.All(p=>p.ExecutableIndependent),"Native package in file-only mode");
            if(!enabled)Check(!ps.Any(p=>updated.Contains(p.Id)),"Master-off retained patch package");
            string dataId=mod==GameMod.ArcaneWars?"common-ui":"pure-fixes-data";
            Check(ps.Any(p=>p.Id==dataId)==(enabled&&(mod!=GameMod.ArcaneWars||!data)),"Frame scope");
            selections++;
        }
        var installer=new ModuleInstaller(root);string cache=Path.Combine(stage,"test-cache");Directory.CreateDirectory(cache);
        var prepared=new Dictionary<string,InstalledModule>();using var http=new HttpClient{Timeout=TimeSpan.FromMinutes(4)};
        http.DefaultRequestHeaders.UserAgent.ParseAdd("PawsBetaAcceptance/1");
        async Task<InstalledModule> Prepare(PackageRelease p){
            string key=p.Id+p.Sha256;if(prepared.TryGetValue(key,out var found))return found;
            string path=p.Urls[0];
            if(Uri.TryCreate(path,UriKind.Absolute,out var u)&&u.Scheme=="https"){
                path=Path.Combine(cache,p.Sha256+".zip");
                if(!File.Exists(path))foreach(string folder in new[]{"release-arcane-032-beta1","release-arcane-031-beta2","release-084-arcane-031"}){
                    string known=Path.Combine(stage,"..",folder,"test-cache",p.Sha256+".zip");if(File.Exists(known)){File.Copy(known,path);break;}
                }
                if(!File.Exists(path))await File.WriteAllBytesAsync(path,await http.GetByteArrayAsync(u));
            }
            Check(await CryptoAndIO.Sha256Async(path)==p.Sha256,"Archive hash: "+p.Id);
            return prepared[key]=await installer.PrepareAsync(p,path);
        }
        async Task<Dictionary<string,InstalledModule>> Install(ChannelManifest f,UserSettings raw){
            var s=EffectiveSettings.ForFeed(raw,f);var desired=new Dictionary<string,InstalledModule>();
            foreach(var p in GamePackageSelector.Select(f,s,s.RussianLocalization,s.CustomPlayerColors))desired[p.Id]=await Prepare(p);
            await installer.ReconcileAsync(desired,settings:s);transitions++;
            Check((await installer.VerifyAsync()).Count==0,"Installer verification");return desired;
        }
        File.Copy(Path.Combine(gameRoot,"k2.exe"),Path.Combine(root,"k2.exe"));string stock=await CryptoAndIO.Sha256Async(Path.Combine(root,"k2.exe"));
        await File.WriteAllTextAsync(Path.Combine(root,"save-sentinel.rsg"),"preserved");
        foreach(string mod in new[]{GameMod.ArcaneWars,GameMod.Vanilla,GameMod.Immortals}){
            int count=mod==GameMod.ArcaneWars?8:4;
            await Install(old,Selection(mod,count-1));
            if(mod!=GameMod.ArcaneWars)Check(File.ReadLines(Path.Combine(root,"paws_player_colors.ini")).Count(x=>x.StartsWith("[paws_"))==48,"Pure upgrade baseline");
            for(int mask=0;mask<count;mask++){
                var s=EffectiveSettings.ForFeed(Selection(mod,mask),feed);var desired=await Install(feed,s);
                string exe=GameExecutableSelector.Select(config,s,feed);seen.Add(exe);
                string helpers=mod==GameMod.ArcaneWars?"helpers":"pure-final/beta";
                Check(await CryptoAndIO.Sha256Async(Path.Combine(root,exe))==await CryptoAndIO.Sha256Async(Path.Combine(stage,helpers,exe)),"Stale helper overlay");
                string id=mod==GameMod.ArcaneWars?"common-ui":"pure-fixes-data";
                var frames=desired[id].Files.Where(f=>f.Path.StartsWith("skins/",StringComparison.OrdinalIgnoreCase)&&f.Path.EndsWith("/Background.tga",StringComparison.OrdinalIgnoreCase)).ToArray();
                Check(frames.Length==18,"All race frames");
                foreach(var f in frames){Check(await CryptoAndIO.Sha256Async(Path.Combine(root,f.Path))==f.Sha256,"Frame hash");frameChecks++;}
                if(s.CustomPlayerColors)Check(await File.ReadAllTextAsync(Path.Combine(root,"paws_player_colors.ini"))==await File.ReadAllTextAsync(Path.Combine(repo,"game/beta7/paws_player_colors.ini")),"39-color payload");
                using var p=Process.Start(new ProcessStartInfo(Path.Combine(root,exe)){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,ArgumentList={"--preflight",root}})!;
                string stdout=await p.StandardOutput.ReadToEndAsync(),stderr=await p.StandardError.ReadToEndAsync();await p.WaitForExitAsync();
                Check(p.ExitCode==0&&stdout.Contains("PREFLIGHT_PASS"),"Explicit preflight: "+exe+" "+stderr);preflights++;
                if(mod==GameMod.ArcaneWars&&mask==7)File.Copy(Path.Combine(root,".pawpatch/state.json"),Path.Combine(stage,"installed-state.json"));
            }
            foreach(bool data in new[]{true,false}){
                var s=Selection(mod,3,enabled:data,data:data);var desired=await Install(feed,s);
                Check(!desired.ContainsKey(mod==GameMod.ArcaneWars?"common-ui":"pure-fixes-runtime"),"Native exclusion");
                Check(!File.Exists(Path.Combine(root,"paws_player_colors.ini")),"Disabled palette remains installed");
                Check(File.Exists(Path.Combine(root,"skins/Human/UI/Game/ControlPanel/Background.tga"))==(data&&mod!=GameMod.ArcaneWars),"Frame removal/file-only retention");
            }
            await Install(old,Selection(mod,count-1));
            if(mod!=GameMod.ArcaneWars){
                Check(File.ReadLines(Path.Combine(root,"paws_player_colors.ini")).Count(x=>x.StartsWith("[paws_"))==48,"Rollback palette");
                Check(!File.Exists(Path.Combine(root,"skins/Human/UI/Game/ControlPanel/Background.tga")),"Rollback removes added frames");
            }
        }
        await installer.UninstallAsync();transitions++;
        Check(seen.Count==12,"All 12 runtime variants");
        Check(await CryptoAndIO.Sha256Async(Path.Combine(root,"k2.exe"))==stock&&await File.ReadAllTextAsync(Path.Combine(root,"save-sentinel.rsg"))=="preserved","Stock/save preservation");
        var report=new{passed=true,selections,transitions,frameChecks,preflights,uniqueHelpers=seen.Count,gameLaunched=false,sourceGameReadOnly=true};
        await File.WriteAllTextAsync(Path.Combine(stage,"installation-verification.json"),JsonSerializer.Serialize(report));Console.WriteLine(JsonSerializer.Serialize(report));
    }
}

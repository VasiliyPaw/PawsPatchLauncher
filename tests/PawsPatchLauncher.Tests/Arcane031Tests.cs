using System.Diagnostics;
using System.Net.Http;
using System.Text.Json;
using PawsPatchLauncher;

// Only pure selection, isolated installation and explicit --preflight modes.
// Never invokes a helper's normal entry point or writes to the source game.
public static class Arcane031Tests
{
    static void Require(bool value,string message){if(!value)throw new InvalidDataException(message);}
    static ChannelManifest Feed(string path,string key)
    {
        var e=JsonSerializer.Deserialize(File.ReadAllBytes(path),LauncherJsonContext.Default.SignedFeedEnvelope)!;
        var b=Convert.FromBase64String(e.Payload);Require(CryptoAndIO.VerifySignature(b,e.Signature,key),"Invalid feed signature");
        return JsonSerializer.Deserialize(b,LauncherJsonContext.Default.ChannelManifest)!;
    }
    static UserSettings Selection(int mask,string channel="stable") => new(){Mod=GameMod.ArcaneWars,Channel=channel,PawPatchEnabled=true,
        CustomPlayerColors=(mask&1)!=0,DesyncMode=(mask&2)!=0?"continue":"official",IndependentHostility=(mask&4)!=0,
        RussianLocalization=false,GameTextLanguage="en",GameVoiceLanguage="en",RoamingSpawnMode="x4",AdditionalRoamingCompanies=true,
        SiegeBalance=true,DisablePowersAndShards=true,LargeMapSizes=true};
    public static async Task RunAsync(string repoRoot,string stageRoot,string gameRoot)
    {
        var repo=Path.GetFullPath(repoRoot);var stage=Path.GetFullPath(stageRoot);var root=Path.Combine(stage,"install-fixture");
        Require(!Directory.Exists(root),"Use a fresh fixture");
        Require(!root.Equals(Path.GetFullPath(gameRoot),StringComparison.OrdinalIgnoreCase),"Refusing the actual game");
        Directory.CreateDirectory(root);
        var config=JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(repo,"src/PawsPatchLauncher/launcher.config.json")),LauncherJsonContext.Default.LauncherConfiguration)!;
        var feed=Feed(Path.Combine(stage,"publication/test-feeds/stable.json"),config.PublicKeyPem);
        var old=Feed(Path.Combine(stage,"publication/previous/stable.json"),config.PublicKeyPem);
        var beta=Feed(Path.Combine(stage,"publication/previous/beta.json"),config.PublicKeyPem);
        Require(feed.Channel=="stable"&&feed.PatchGuide!.Version=="0.3.1","Wrong release identity");
        Require(feed.PatchGuide!.Entries.All(e=>e.Category!="beta"),"Promoted features still beta-only");
        var installer=new ModuleInstaller(root);var cache=Path.Combine(stage,"test-cache");Directory.CreateDirectory(cache);
        var localArchives=Directory.EnumerateFiles(Path.GetDirectoryName(stage)!,"*.zip",SearchOption.AllDirectories)
            .Select(p=>new FileInfo(p)).GroupBy(p=>p.Length).ToDictionary(g=>g.Key,g=>g.Select(p=>p.FullName).ToArray());
        var prepared=new Dictionary<string,InstalledModule>();using var http=new HttpClient{Timeout=TimeSpan.FromMinutes(5)};
        http.DefaultRequestHeaders.UserAgent.ParseAdd("PawsPatchArcane031Validation/1");
        async Task<InstalledModule> Prepare(PackageRelease p)
        {
            string key=p.Id+":"+p.Sha256;if(prepared.TryGetValue(key,out var found))return found;
            string path=p.Urls[0];
            if(Uri.TryCreate(path,UriKind.Absolute,out var u)&&u.Scheme=="https"){
                path=Path.Combine(cache,p.Sha256+".zip");
                if(!File.Exists(path)){
                    string? existing=null;
                    if(localArchives.TryGetValue(p.Size,out var candidates))foreach(var c in candidates)
                        if(await CryptoAndIO.Sha256Async(c)==p.Sha256){existing=c;break;}
                    if(existing is not null)path=existing;
                    else {await File.WriteAllBytesAsync(path,await http.GetByteArrayAsync(u));Console.WriteLine("DOWNLOADED "+p.Id);}
                }
            }
            Require(await CryptoAndIO.Sha256Async(path)==p.Sha256,"Wrong archive: "+p.Id);
            var m=await installer.PrepareAsync(p,path);prepared[key]=m;return m;
        }
        var scenarios=new Dictionary<string,(List<PackageRelease> Packages,UserSettings Settings,string Exe)>();int selections=0;
        foreach(var channel in new[]{feed,beta})foreach(var text in GameLanguages.Choices)foreach(var voice in GameLanguages.VoiceChoices)
        foreach(var roaming in new[]{"standard","x2","x4"})foreach(bool data in new[]{false,true})foreach(bool enabled in new[]{false,true})
        for(int mask=0;mask<8;mask++)for(int economy=0;economy<8;economy++){
            var raw=Selection(mask,channel.Channel);raw.DataOnly=data;raw.PawPatchEnabled=enabled;
            GameLanguages.SetText(raw,text);raw.GameVoiceLanguage=voice;raw.RoamingSpawnMode=roaming;
            raw.AdditionalRoamingCompanies=(economy&1)!=0;raw.SiegeBalance=(economy&2)!=0;raw.DisablePowersAndShards=(economy&4)!=0;
            var s=EffectiveSettings.ForFeed(raw,channel);var ps=GamePackageSelector.Select(channel,s,s.RussianLocalization,s.CustomPlayerColors);
            var ids=ps.Select(p=>p.Id).ToHashSet(StringComparer.OrdinalIgnoreCase);
            Require(ps.Count==ids.Count&&ps.All(p=>p.DependsOn.All(ids.Contains)),"Incomplete or duplicate selected dependencies");
            Require(ps.Any(p=>p.Id=="common-ui")==(!data&&enabled),"Native/static HUD scope");
            Require(ps.Any(p=>p.Id=="pawpatch-core")==(!data&&enabled),"Core scope");
            if(!enabled)Require(!s.CustomPlayerColors&&!s.IndependentHostility&&s.DesyncMode=="official"&&!s.AdditionalRoamingCompanies&&!s.SiegeBalance&&!s.DisablePowersAndShards,"Master-off leaked settings");
            if(data)Require(ps.All(p=>p.ExecutableIndependent),"Native module in data-only mode");
            string exe=GameExecutableSelector.Select(config,s,channel);
            if(data)Require(exe=="k2.exe","File-only mode uses a native helper");
            string key=string.Join("|",ps.Select(p=>p.Id+":"+p.Sha256).Order())+"/"+exe;
            scenarios.TryAdd(key,(ps,s,exe));selections++;
        }
        Console.WriteLine("SELECTIONS "+selections+" UNIQUE_PLANS "+scenarios.Count);
        // Validate each archive once, then resolve installed winners for every unique plan.
        var modules=new Dictionary<string,InstalledModule>();
        foreach(var scenario in scenarios.Values)foreach(var p in scenario.Packages)
            if(!modules.ContainsKey(p.Sha256))modules[p.Sha256]=await Prepare(p);
        foreach(var scenario in scenarios.Values){
            var winners=new Dictionary<string,ModuleFile>(StringComparer.OrdinalIgnoreCase);
            foreach(var p in scenario.Packages.OrderBy(p=>p.Priority).ThenBy(p=>p.Id,StringComparer.OrdinalIgnoreCase)){
                var m=modules[p.Sha256];foreach(var n in m.Remove)winners.Remove(CryptoAndIO.NormalizeRelativePath(n));
                foreach(var f in m.Files)winners[CryptoAndIO.NormalizeRelativePath(f.Path)]=f;
            }
            if(scenario.Exe!="k2.exe")Require(winners.ContainsKey(scenario.Exe),"Missing selected helper: "+scenario.Exe);
            if(scenario.Settings.DataOnly)GameCompatibilityPolicy.ValidateDataModules(scenario.Packages.Select(p=>modules[p.Sha256]));
            if(scenario.Settings.PawPatchEnabled&&!scenario.Settings.DataOnly){
                string source=Path.Combine(scenario.Settings.Channel=="stable"?stage:Path.Combine(Path.GetDirectoryName(stage)!,"release-arcane-031-beta1"),"helpers",scenario.Exe);
                Require(winners[scenario.Exe].Sha256==await CryptoAndIO.Sha256Async(source),"Stale helper wins an overlay");
                Require(winners.Keys.Count(n=>n.StartsWith("skins\\",StringComparison.OrdinalIgnoreCase)&&n.EndsWith("\\Background.tga",StringComparison.OrdinalIgnoreCase))==18,"Missing minimap frames");
            }
        }
        await File.WriteAllTextAsync(Path.Combine(root,"save-sentinel.rsg"),"preserve save and preferences");
        File.Copy(Path.Combine(gameRoot,"k2.exe"),Path.Combine(root,"k2.exe"));string stock=await CryptoAndIO.Sha256Async(Path.Combine(root,"k2.exe"));
        int transitions=0,preflights=0,frameChecks=0;
        async Task Apply(ChannelManifest channel,UserSettings raw,bool preflight){
            var s=EffectiveSettings.ForFeed(raw,channel);var desired=new Dictionary<string,InstalledModule>();
            foreach(var p in GamePackageSelector.Select(channel,s,s.RussianLocalization,s.CustomPlayerColors))desired[p.Id]=await Prepare(p);
            await installer.ReconcileAsync(desired,settings:s);Require((await installer.VerifyAsync()).Count==0,"Installed file verification failed");transitions++;
            if(s.PawPatchEnabled&&!s.DataOnly&&channel==feed){
                Require((await File.ReadAllLinesAsync(Path.Combine(root,"paws_patch_versions.ini"))).Contains("PawPatch=0.3.1"),"Wrong menu identity");
                var frames=desired["common-ui"].Files.Where(f=>f.Path.Replace('\\','/').StartsWith("skins/")&&f.Path.EndsWith("/Background.tga")).ToList();
                Require(frames.Count==18,"Missing installed frames");foreach(var f in frames){Require(await CryptoAndIO.Sha256Async(Path.Combine(root,f.Path))==f.Sha256,"Frame mismatch");frameChecks++;}
            }
            if(preflight){
                string exe=GameExecutableSelector.Select(config,s,channel);
                using var process=Process.Start(new ProcessStartInfo(Path.Combine(root,exe)){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,ArgumentList={"--preflight",root}})!;
                string output=await process.StandardOutput.ReadToEndAsync(),error=await process.StandardError.ReadToEndAsync();await process.WaitForExitAsync();
                Require(process.ExitCode==0&&output.Contains("PREFLIGHT_PASS"),"Preflight failed: "+exe+" "+error);preflights++;
            }
        }
        await Apply(old,Selection(7),false);
        for(int mask=0;mask<8;mask++)await Apply(feed,Selection(mask),true);
        File.Copy(Path.Combine(root,".pawpatch/state.json"),Path.Combine(stage,"installed-031-state.json"));
        for(int i=0;i<GameLanguages.Choices.Count;i++){
            var s=Selection(i%8);GameLanguages.SetText(s,GameLanguages.Choices[i]);s.GameVoiceLanguage=GameLanguages.VoiceChoices[i%4];
            s.RoamingSpawnMode=new[]{"standard","x2","x4"}[i%3];s.AdditionalRoamingCompanies=i%2==0;s.SiegeBalance=i%2!=0;s.DisablePowersAndShards=i%3==0;
            await Apply(feed,s,true);
            s.DataOnly=true;await Apply(feed,s,false);
            Require(!File.Exists(Path.Combine(root,"k2_paws_ui_1372.exe")),"Runtime survived file-only transition");
            s.DataOnly=false;s.PawPatchEnabled=false;await Apply(feed,s,false);
            Require(!File.Exists(Path.Combine(root,"d3d9.dll")),"Graphics runtime survived master-off");
        }
        await Apply(beta,Selection(7,"beta"),true);await Apply(feed,Selection(7),true);await Apply(old,Selection(7),false);
        Require(Directory.EnumerateFiles(Path.Combine(root,"skins"),"Background.tga",SearchOption.AllDirectories).Count()==18,"Accepted frames missing after rollback to 0.3.0");
        await installer.UninstallAsync();transitions++;
        Require(await File.ReadAllTextAsync(Path.Combine(root,"save-sentinel.rsg"))=="preserve save and preferences","Save changed");
        Require(await CryptoAndIO.Sha256Async(Path.Combine(root,"k2.exe"))==stock,"Stock executable changed");
        var report=new{passed=true,selections,uniquePlans=scenarios.Count,verifiedArchives=prepared.Count,uniqueHelpers=8,frameChecks,preflights,transitions,gameLaunched=false,sourceGameReadOnly=true};
        await File.WriteAllTextAsync(Path.Combine(stage,"installation-verification.json"),JsonSerializer.Serialize(report));Console.WriteLine(JsonSerializer.Serialize(report));
    }
}

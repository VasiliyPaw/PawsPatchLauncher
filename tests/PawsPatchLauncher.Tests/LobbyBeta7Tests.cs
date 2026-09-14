using System.Text.Json;
using PawsPatchLauncher;

public static class LobbyBeta7Tests
{
    static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
    static ChannelManifest Feed(string path){using var e=JsonDocument.Parse(File.ReadAllBytes(path));return JsonSerializer.Deserialize(Convert.FromBase64String(e.RootElement.GetProperty("payload").GetString()!),LauncherJsonContext.Default.ChannelManifest)!;}
    public static async Task RunAsync(string candidateRoot,string fixtureRoot,string helpers)
    {
        var candidate=Path.GetFullPath(candidateRoot);var root=Path.Combine(Path.GetFullPath(fixtureRoot),Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
        var beta=Feed(Path.Combine(candidate,"feeds/v2/beta.local.signed.json"));var stable=Feed(Path.Combine(candidate,"previous/v2/stable.signed.json"));int selections=0;
        foreach(var feed in new[]{beta,stable})foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals,GameMod.ArcaneWars})
        foreach(bool dataOnly in new[]{false,true})foreach(bool textRu in new[]{false,true})foreach(bool voiceRu in new[]{false,true})foreach(var roaming in new[]{"standard","x2","x4"})for(int mask=0;mask<128;mask++){
            var s=new UserSettings{Mod=mod,Channel=feed.Channel,DataOnly=dataOnly,PawPatchEnabled=(mask&1)!=0,RussianLocalization=textRu,GameVoiceLanguage=voiceRu?"ru":"en",CustomPlayerColors=(mask&2)!=0,DesyncMode=(mask&4)!=0?"continue":"official",IndependentHostility=(mask&8)!=0,AdditionalRoamingCompanies=(mask&16)!=0,SiegeBalance=(mask&32)!=0,DisablePowersAndShards=(mask&64)!=0,RoamingSpawnMode=roaming};
            var selected=GamePackageSelector.Select(feed,s,textRu,s.CustomPlayerColors);bool receives=selected.Any(p=>p.Id=="pawpatch-core"&&p.Version=="0.3.0-beta.7");
            Require(receives==(feed==beta&&mod==GameMod.ArcaneWars&&s.PawPatchEnabled&&!dataOnly),"Beta update escaped its scope");
            if(receives){Require(selected.Any(p=>p.Id=="common-ui"&&p.Version=="1.3.72-ui.6-beta.7"),"Missing required new helper module");if(s.CustomPlayerColors)Require(selected.Any(p=>p.Id=="player-colors"&&p.Version=="0.3.0-beta.7"),"Old color helpers selected");}selections++;
        }
        var installer=new ModuleInstaller(root);var prepared=new Dictionary<string,InstalledModule>();var seen=new HashSet<string>();int transitions=0;
        await File.WriteAllTextAsync(Path.Combine(root,"save-sentinel.rsg"),"preserve-save");
        for(int mask=0;mask<8;mask++){
            var s=new UserSettings{Mod=GameMod.ArcaneWars,Channel="beta",PawPatchEnabled=true,CustomPlayerColors=(mask&1)!=0,DesyncMode=(mask&2)!=0?"continue":"official",IndependentHostility=(mask&4)!=0,RoamingSpawnMode="x4",AdditionalRoamingCompanies=true,SiegeBalance=true,DisablePowersAndShards=true,LargeMapSizes=true,RussianLocalization=false,GameVoiceLanguage="en"};
            var selected=GamePackageSelector.Select(beta,s,false,s.CustomPlayerColors);var desired=new Dictionary<string,InstalledModule>();
            foreach(var p in selected){if(!prepared.TryGetValue(p.Id,out var module)){Require(await CryptoAndIO.Sha256Async(p.Urls[0])==p.Sha256,"Archive changed");module=await installer.PrepareAsync(p,p.Urls[0]);prepared[p.Id]=module;}desired[p.Id]=module;}
            await installer.ReconcileAsync(desired,settings:s);transitions++;
            var exe=GameExecutableSelector.Select(new LauncherConfiguration(),s,beta);seen.Add(exe);
            Require(await CryptoAndIO.Sha256Async(Path.Combine(root,exe))==await CryptoAndIO.Sha256Async(Path.Combine(helpers,exe)),"Old helper survived overlay: "+exe);
            Require((await File.ReadAllTextAsync(Path.Combine(root,"paws_patch_versions.ini"))).Contains("PawPatch=0.3.0-beta.7"),"Menu label stale");
            Require(installer.LoadState().AppliedSettings?.CustomPlayerColors==s.CustomPlayerColors,"Applied settings were not persisted");
        }
        Require(seen.Count==8,"Not all native variants were reached");
        await installer.UninstallAsync();transitions++;
        Require(await File.ReadAllTextAsync(Path.Combine(root,"save-sentinel.rsg"))=="preserve-save","Save changed");
        var report=new{passed=true,selections,transitions,uniqueHelpers=seen.Count,gameLaunched=false,fixture=root};
        await File.WriteAllTextAsync(Path.Combine(root,"results.json"),JsonSerializer.Serialize(report));Console.WriteLine(JsonSerializer.Serialize(report));
    }
    // Explicitly invoked only for the user's two released game folders after
    // games are closed. Reuses the real reversible installer, preserving settings.
    public static async Task StageReviewAsync(string gameRoot,string candidateRoot)
    {
        var game=Path.GetFullPath(gameRoot);Require(!System.Diagnostics.Process.GetProcessesByName("k2").Any(),"Close the game before staging this review");
        var installer=new ModuleInstaller(game);var state=installer.LoadState();var s=state.AppliedSettings;
        Require(s is {Mod:GameMod.ArcaneWars,PawPatchEnabled:true,DataOnly:false},"Only the existing Arcane Wars patch review is supported");
        var feed=Feed(Path.Combine(Path.GetFullPath(candidateRoot),"feeds/v2/beta.local.signed.json"));
        var desired=new Dictionary<string,InstalledModule>(state.Modules,StringComparer.OrdinalIgnoreCase);
        foreach(var id in new[]{"pawpatch-core","common-ui","player-colors"}){
            if(!desired.ContainsKey(id)&&id=="player-colors")continue;
            var p=feed.Packages.Single(p=>p.Id==id);
            var archive=Path.Combine(Path.GetFullPath(candidateRoot),"assets",Path.GetFileName(p.Urls[0]));
            Require(await CryptoAndIO.Sha256Async(archive)==p.Sha256,"Review archive changed");
            desired[id]=await installer.PrepareAsync(p,archive);
        }
        await installer.ReconcileAsync(desired,settings:s,releaseId:state.ReleaseId,gameRequirement:state.GameRequirement,baseGameSha256:state.BaseGameSha256);
        await GameMenuMetadata.WriteAsync(game,feed,s!);
        Console.WriteLine("STAGED_USER_REVIEW "+game+" patch=0.3.0-beta.7 settingsPreserved=true");
    }
}

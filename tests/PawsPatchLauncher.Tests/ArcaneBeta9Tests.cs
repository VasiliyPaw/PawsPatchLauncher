using System.Diagnostics;
using System.Net.Http;
using System.Text.Json;
using PawsPatchLauncher;

public static class ArcaneBeta9Tests
{
    static void Require(bool value,string message){if(!value)throw new InvalidDataException(message);}
    static ChannelManifest Feed(string path,string publicKey)
    {
        var envelope=JsonSerializer.Deserialize(File.ReadAllBytes(path),LauncherJsonContext.Default.SignedFeedEnvelope)!;
        var data=Convert.FromBase64String(envelope.Payload);
        Require(CryptoAndIO.VerifySignature(data,envelope.Signature,publicKey),"Invalid signed candidate");
        return JsonSerializer.Deserialize(data,LauncherJsonContext.Default.ChannelManifest)!;
    }
    static UserSettings Selection(int mask) => new(){Mod=GameMod.ArcaneWars,Channel="beta",PawPatchEnabled=true,
        CustomPlayerColors=(mask&1)!=0,DesyncMode=(mask&2)!=0?"continue":"official",IndependentHostility=(mask&4)!=0,
        RussianLocalization=false,GameTextLanguage="en",GameVoiceLanguage="en",RoamingSpawnMode="x4",AdditionalRoamingCompanies=true,
        SiegeBalance=true,DisablePowersAndShards=true,LargeMapSizes=true};
    public static async Task RunAsync(string repoRoot,string stageRoot,string gameRoot)
    {
        var repo=Path.GetFullPath(repoRoot);var stage=Path.GetFullPath(stageRoot);
        var root=Path.Combine(stage,"install-fixture");Require(!Directory.Exists(root),"Use a fresh fixture");
        Require(!root.Equals(Path.GetFullPath(gameRoot),StringComparison.OrdinalIgnoreCase),"Refusing the actual game");
        Directory.CreateDirectory(root);
        var config=JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(repo,"src/PawsPatchLauncher/launcher.config.json")),LauncherJsonContext.Default.LauncherConfiguration)!;
        var feed=Feed(Path.Combine(stage,"publication/test-feeds/beta.json"),config.PublicKeyPem);
        var old=Feed(Path.Combine(repo,"feed/v2/beta.json"),config.PublicKeyPem);
        var updated=new HashSet<string>{"pawpatch-core","common-ui","player-colors","desync-continue"};
        int selections=0;
        foreach(var language in new[]{"en","ru","de","fr","cs","uk"})foreach(bool data in new[]{false,true})foreach(bool enabled in new[]{false,true})for(int mask=0;mask<8;mask++) {
            var s=Selection(mask);s.GameTextLanguage=language;s.RussianLocalization=language=="ru";s.PawPatchEnabled=enabled;s.DataOnly=data;
            var packages=GamePackageSelector.Select(feed,s,s.RussianLocalization,s.CustomPlayerColors);
            Require(packages.Any(p=>p.Id=="common-ui"&&p.Version=="1.3.72-ui.8-beta.9")==(!data&&enabled),"Incorrect native/static HUD scope");
            if(data||!enabled)Require(!packages.Any(p=>updated.Contains(p.Id)),"Native update escaped file-only/master-off scope");
            selections++;
        }
        var installer=new ModuleInstaller(root);var cache=Path.Combine(stage,"test-cache");Directory.CreateDirectory(cache);
        var prepared=new Dictionary<string,InstalledModule>();using var http=new HttpClient{Timeout=TimeSpan.FromMinutes(3)};
        http.DefaultRequestHeaders.UserAgent.ParseAdd("PawsPatchBeta9Validation/1");
        async Task<InstalledModule> Prepare(PackageRelease p)
        {
            string key=p.Id+":"+p.Sha256;if(prepared.TryGetValue(key,out var found))return found;
            string path=p.Urls[0];
            if(Uri.TryCreate(path,UriKind.Absolute,out var u)&&u.Scheme=="https") {
                path=Path.Combine(cache,p.Sha256+".zip");
                if(!File.Exists(path)){await File.WriteAllBytesAsync(path,await http.GetByteArrayAsync(u));Console.WriteLine("CACHED "+p.Id);}
            }
            Require(await CryptoAndIO.Sha256Async(path)==p.Sha256,"Wrong archive: "+p.Id);
            return prepared[key]=await installer.PrepareAsync(p,path);
        }
        await File.WriteAllTextAsync(Path.Combine(root,"save-sentinel.rsg"),"preserve save and preferences");
        var baseline=Selection(7);var prior=new Dictionary<string,InstalledModule>();
        foreach(var p in GamePackageSelector.Select(old,baseline,false,true))prior[p.Id]=await Prepare(p);
        await installer.ReconcileAsync(prior,settings:baseline);
        // Only copy the original executable into an isolated fixture for hash-based preflight.
        File.Copy(Path.Combine(gameRoot,"k2.exe"),Path.Combine(root,"k2.exe"));
        string stock=await CryptoAndIO.Sha256Async(Path.Combine(root,"k2.exe"));
        var seen=new HashSet<string>();int frameChecks=0;
        for(int mask=0;mask<8;mask++) {
            var s=Selection(mask);var desired=new Dictionary<string,InstalledModule>();
            foreach(var p in GamePackageSelector.Select(feed,s,false,s.CustomPlayerColors))desired[p.Id]=await Prepare(p);
            await installer.ReconcileAsync(desired,settings:s);
            Require((await installer.VerifyAsync()).Count==0,"Installed file verification failed");
            string exe=GameExecutableSelector.Select(config,s,feed);seen.Add(exe);
            Require(await CryptoAndIO.Sha256Async(Path.Combine(root,exe))==await CryptoAndIO.Sha256Async(Path.Combine(stage,"helpers",exe)),"Stale helper overlay: "+exe);
            var frames=desired["common-ui"].Files.Where(f=>f.Path.StartsWith("skins/",StringComparison.OrdinalIgnoreCase)&&f.Path.EndsWith("/Background.tga",StringComparison.OrdinalIgnoreCase)).ToList();
            Require(frames.Count==18,"Missing racial frame resolution variants");
            foreach(var f in frames){Require(await CryptoAndIO.Sha256Async(Path.Combine(root,f.Path))==f.Sha256,"Wrong installed frame");frameChecks++;}
            Require((await File.ReadAllTextAsync(Path.Combine(root,"paws_patch_versions.ini"))).Contains("PawPatch=0.3.0-beta.9"),"Stale menu version");
        }
        Require(seen.Count==8,"Not all eight variants reached");
        // Run only the explicit hash/configuration preflight mode, never normal Main.
        foreach(string exe in seen) {
            using var process=Process.Start(new ProcessStartInfo(Path.Combine(root,exe)){
                UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,
                ArgumentList={"--preflight",root}})!;
            string output=await process.StandardOutput.ReadToEndAsync(),error=await process.StandardError.ReadToEndAsync();
            await process.WaitForExitAsync();Require(process.ExitCode==0&&output.Contains("PREFLIGHT_PASS"),"Preflight failed: "+exe+" "+error);
        }
        // Preserve fixture state for the in-process mismatch and compiled-hook audit.
        File.Copy(Path.Combine(root,".pawpatch/state.json"),Path.Combine(stage,"installed-beta9-state.json"));
        // Downgrading/uninstalling must remove all new frames and retain the base game/save.
        await installer.ReconcileAsync(prior,settings:baseline);
        Require(!Directory.EnumerateFiles(Path.Combine(root,"skins"),"Background.tga",SearchOption.AllDirectories).Any(),"Frames survived beta.8 rollback");
        await installer.UninstallAsync();
        Require(await File.ReadAllTextAsync(Path.Combine(root,"save-sentinel.rsg"))=="preserve save and preferences","Save changed");
        Require(await CryptoAndIO.Sha256Async(Path.Combine(root,"k2.exe"))==stock,"Stock executable changed");
        var report=new{passed=true,selections,uniqueHelpers=seen.Count,frameChecks,preflights=8,transitions=11,gameLaunched=false,sourceGameReadOnly=true,fixture=root};
        await File.WriteAllTextAsync(Path.Combine(stage,"installation-verification.json"),JsonSerializer.Serialize(report));
        Console.WriteLine(JsonSerializer.Serialize(report));
    }
}

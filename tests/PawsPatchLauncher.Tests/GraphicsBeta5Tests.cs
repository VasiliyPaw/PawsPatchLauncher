using System.Text.Json;
using PawsPatchLauncher;

// Runs against production 0.7.12 selector/installer, in new isolated fixtures.
public static class GraphicsBeta5Tests
{
    static readonly string[] Fixes = ["d3d9.dll", "data/Units/Human/Ranger/RangerDie1.KF"];
    static readonly string[] Digests = ["94A0EC76C89F2122712C04D8F276E853C20670A0EEC000BC55F67DCC1E464E2E", "990CF3DDADD764A12126768FDEC606C8469A7C0C19AD55252F94301475A8A781"];
    static void Require(bool ok, string reason) { if (!ok) throw new Exception(reason); }
    static ChannelManifest Feed(string path)
    {
        using var envelope = JsonDocument.Parse(File.ReadAllBytes(path));
        var bytes = Convert.FromBase64String(envelope.RootElement.GetProperty("payload").GetString()!);
        return JsonSerializer.Deserialize(bytes, LauncherJsonContext.Default.ChannelManifest)!;
    }
    public static async Task RunAsync(string candidateRoot, string previousAssets, string fixtureRoot)
    {
        var candidate = Path.GetFullPath(candidateRoot);
        var root = Path.Combine(Path.GetFullPath(fixtureRoot), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var beta = Feed(Path.Combine(candidate, "feeds/v2/beta.production.signed.json"));
        var old = Feed(Path.Combine(candidate, "previous/v2/beta.signed.json"));
        var stable = Feed(Path.Combine(candidate, "previous/v2/stable.signed.json"));
        var selectionCount = 0;
        foreach (var channel in new[] { beta, stable })
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (var dataOnly in new[] { false, true })
        foreach (var textRu in new[] { false, true })
        foreach (var voiceRu in new[] { false, true })
        foreach (var roaming in new[] { "standard", "x2", "x4" })
        for (var mask = 0; mask < 128; mask++)
        {
            var settings = new UserSettings { Mod=mod, Channel=channel.Channel, DataOnly=dataOnly,
                PawPatchEnabled=(mask&1)!=0, RussianLocalization=textRu, GameVoiceLanguage=voiceRu ? "ru" : "en",
                CustomPlayerColors=(mask&2)!=0, DesyncMode=(mask&4)!=0 ? "continue" : "official",
                IndependentHostility=(mask&8)!=0, AdditionalRoamingCompanies=(mask&16)!=0,
                SiegeBalance=(mask&32)!=0, DisablePowersAndShards=(mask&64)!=0, RoamingSpawnMode=roaming };
            var selected=GamePackageSelector.Select(channel, settings, textRu, settings.CustomPlayerColors);
            var receivesFixes=selected.Any(p => p.Id=="pawpatch-core" && p.Version=="0.3.0-beta.5");
            Require(receivesFixes==(channel==beta && mod==GameMod.ArcaneWars && settings.PawPatchEnabled && !dataOnly), "Fixes leaked or missing from selection");
            if (receivesFixes) Require(selected.Any(p => p.Id=="common-ui" && p.Version=="1.3.72-ui.5-beta.5"), "Version-label package missing");
            selectionCount++;
        }
        var transitions=0;
        foreach (var initial in new[] { "absent", "manual-fix", "foreign-original" })
        {
            var game=Path.Combine(root,initial);Directory.CreateDirectory(game);
            await File.WriteAllTextAsync(Path.Combine(game,"save-sentinel.rsg"),"preserve this save");
            var installer=new ModuleInstaller(game);
            async Task<Dictionary<string,InstalledModule>> Prepare(ChannelManifest feed, string assets)
            {
                var modules=new Dictionary<string,InstalledModule>();
                foreach (var id in new[] { "pawpatch-core", "common-ui" })
                {
                    var p=feed.Packages.Single(p=>p.Id==id);
                    var archive=Path.Combine(assets,Path.GetFileName(new Uri(p.Urls[0]).AbsolutePath));
                    Require(await CryptoAndIO.Sha256Async(archive)==p.Sha256, "Archive hash mismatch");
                    modules[id]=await installer.PrepareAsync(p,archive);
                }
                return modules;
            }
            var previous=await Prepare(old,previousAssets);
            var updated=await Prepare(beta,Path.Combine(candidate,"assets"));
            if(initial=="foreign-original")
                foreach(var path in Fixes) { var full=Path.Combine(game,path);Directory.CreateDirectory(Path.GetDirectoryName(full)!);await File.WriteAllTextAsync(full,"user original "+path); }
            if(initial=="manual-fix")
                foreach(var path in Fixes)
                {
                    var module=updated["pawpatch-core"];
                    var source=Path.Combine(game,".pawpatch/packages/pawpatch-core",module.Version,"payload",path);
                    var full=Path.Combine(game,path);Directory.CreateDirectory(Path.GetDirectoryName(full)!);File.Copy(source,full);
                }
            var settings=new UserSettings { Mod=GameMod.ArcaneWars,Channel="beta",PawPatchEnabled=true };
            async Task Apply(Dictionary<string,InstalledModule> modules)
            {
                await installer.ReconcileAsync(modules,settings:settings);
                Require((await installer.VerifyAsync()).Count==0,"Installed file verification");transitions++;
            }
            async Task CheckOriginals()
            {
                foreach(var path in Fixes)
                    if(initial=="foreign-original") Require(await File.ReadAllTextAsync(Path.Combine(game,path))=="user original "+path,"Original not restored");
                    else Require(!File.Exists(Path.Combine(game,path)),"Managed fix left active after rollback/off");
            }
            await Apply(previous); // beta.4 -> beta.5 update, including manual local fix adoption
            await Apply(updated);
            for(var i=0;i<Fixes.Length;i++) Require(await CryptoAndIO.Sha256Async(Path.Combine(game,Fixes[i]))==Digests[i],"Wrong deployed fix");
            Require((await File.ReadAllTextAsync(Path.Combine(game,"paws_patch_versions.ini"))).Contains("PawPatch=0.3.0-beta.5"),"Wrong in-game patch version");
            await Apply(updated); // repeat apply from cache
            await Apply(previous);await CheckOriginals(); // rollback to beta.4
            await Apply(updated);
            await Apply(new());await CheckOriginals(); // patch disabled / switch to a mode excluding core
            await Apply(updated);
            await installer.UninstallAsync();await CheckOriginals();transitions++;
            Require(await File.ReadAllTextAsync(Path.Combine(game,"save-sentinel.rsg"))=="preserve this save","Save was changed");
        }
        var report=new { passed=true,selectionCount,transitions,gameLaunched=false,launcherVersion="0.7.12",fixtures=root };
        await File.WriteAllTextAsync(Path.Combine(root,"results.json"),JsonSerializer.Serialize(report));
        Console.WriteLine(JsonSerializer.Serialize(report));
    }
}

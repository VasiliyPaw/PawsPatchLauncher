using System.Text.Json;
using PawsPatchLauncher;

// Actual released base/beta.5 and staged beta.6 ZIPs; isolated game folder only.
public static class ProphetBeta6Tests
{
    static void Require(bool value, string reason) { if (!value) throw new Exception(reason); }
    static ChannelManifest Feed(string path)
    {
        using var envelope = JsonDocument.Parse(File.ReadAllBytes(path));
        return JsonSerializer.Deserialize(Convert.FromBase64String(envelope.RootElement.GetProperty("payload").GetString()!), LauncherJsonContext.Default.ChannelManifest)!;
    }
    public static async Task RunAsync(string candidateRoot, string previousAssets, string baseArchive, string fixtureRoot)
    {
        var candidate = Path.GetFullPath(candidateRoot);
        var root = Path.Combine(Path.GetFullPath(fixtureRoot), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var beta = Feed(Path.Combine(candidate, "feeds/v2/beta.production.signed.json"));
        var old = Feed(Path.Combine(candidate, "previous/v2/beta.signed.json"));
        var stable = Feed(Path.Combine(candidate, "previous/v2/stable.signed.json"));
        var selections = 0;
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
            var selected = GamePackageSelector.Select(channel, settings, textRu, settings.CustomPlayerColors);
            var receives = selected.Any(p => p.Id == "pawpatch-core" && p.Version == "0.3.0-beta.6");
            Require(receives == (channel == beta && mod == GameMod.ArcaneWars && settings.PawPatchEnabled && !dataOnly), "Wrong update scope");
            if (receives) Require(selected.Any(p => p.Id == "common-ui" && p.Version == "1.3.72-ui.5-beta.6"), "Menu version missing");
            selections++;
        }
        var installer = new ModuleInstaller(root);
        await File.WriteAllTextAsync(Path.Combine(root, "save-sentinel.rsg"), "preserve-save");
        async Task<InstalledModule> Prepare(PackageRelease p, string path)
        {
            Require(await CryptoAndIO.Sha256Async(path) == p.Sha256, "Archive hash mismatch");
            return await installer.PrepareAsync(p, path);
        }
        var modPackage = beta.Packages.Single(p => p.Id == "arcane-wars");
        var originalMod = await Prepare(modPackage, baseArchive);
        async Task<Dictionary<string, InstalledModule>> PreparePatch(ChannelManifest feed, string dir)
        {
            var result = new Dictionary<string, InstalledModule> { ["arcane-wars"] = originalMod };
            foreach (var id in new[] { "pawpatch-core", "common-ui" })
            {
                var package = feed.Packages.Single(p => p.Id == id);
                result[id] = await Prepare(package, Path.Combine(dir, Path.GetFileName(new Uri(package.Urls[0]).AbsolutePath)));
            }
            return result;
        }
        var previous = await PreparePatch(old, previousAssets);
        var updated = await PreparePatch(beta, Path.Combine(candidate, "assets"));
        var fixes = updated["pawpatch-core"].Files.Where(f => f.Path.Contains("Units/Ceyah/Prophet/", StringComparison.OrdinalIgnoreCase)
            || f.Path.Contains("Units/Tech/Conjuror/", StringComparison.OrdinalIgnoreCase)).ToArray();
        Require(fixes.Length == 22 && fixes.All(f => f.Path.EndsWith(".kf", StringComparison.OrdinalIgnoreCase)), "Unexpected fix files");
        var custom = fixes.First(f => f.Path.Contains("Ceyah", StringComparison.Ordinal));
        var customPath = Path.Combine(root, custom.Path); Directory.CreateDirectory(Path.GetDirectoryName(customPath)!);
        await File.WriteAllTextAsync(customPath, "user-original-animation");
        var settingsAw = new UserSettings { Mod=GameMod.ArcaneWars, Channel="beta", PawPatchEnabled=true };
        var transitions = 0;
        async Task Apply(Dictionary<string, InstalledModule> modules)
        {
            await installer.ReconcileAsync(modules, settings: settingsAw);
            Require((await installer.VerifyAsync()).Count == 0, "Installer verification failed");
            transitions++;
        }
        async Task CheckFixes()
        {
            foreach (var file in fixes) Require(await CryptoAndIO.Sha256Async(Path.Combine(root, file.Path)) == file.Sha256, "Wrong deployed animation");
            Require((await File.ReadAllTextAsync(Path.Combine(root, "paws_patch_versions.ini"))).Contains("PawPatch=0.3.0-beta.6"), "Wrong menu patch version");
        }
        async Task CheckBase()
        {
            foreach (var file in fixes)
            {
                var source = originalMod.Files.SingleOrDefault(f => f.Path.Equals(file.Path, StringComparison.OrdinalIgnoreCase));
                var path = Path.Combine(root, file.Path);
                if (source != null) Require(await CryptoAndIO.Sha256Async(path) == source.Sha256, "Conjuror base animation was not restored");
                else if (file == custom) Require(await File.ReadAllTextAsync(path) == "user-original-animation", "User original was not restored");
                else Require(!File.Exists(path), "Prophet override left behind");
            }
        }
        await Apply(previous);
        await Apply(updated); await CheckFixes();
        await Apply(updated); await CheckFixes(); // Repeat apply from cache.
        await Apply(previous); await CheckBase(); // Downgrade to beta.5.
        // Same state as the manually installed local test on a beta.5 installation.
        foreach (var file in fixes)
        {
            var source = Path.Combine(root, ".pawpatch/packages/pawpatch-core", updated["pawpatch-core"].Version, "payload", file.Path);
            var target = Path.Combine(root, file.Path); Directory.CreateDirectory(Path.GetDirectoryName(target)!); File.Copy(source, target, true);
        }
        await Apply(updated); await CheckFixes();
        await Apply(new() { ["arcane-wars"] = originalMod }); await CheckBase(); // Paw's Patch off.
        await Apply(updated); await CheckFixes();
        await installer.UninstallAsync(); transitions++;
        Require(await File.ReadAllTextAsync(customPath) == "user-original-animation", "Uninstall lost user original");
        Require(await File.ReadAllTextAsync(Path.Combine(root, "save-sentinel.rsg")) == "preserve-save", "Saved game changed");
        Require(fixes.Where(f => f != custom).All(f => !File.Exists(Path.Combine(root, f.Path))), "Uninstall left game assets active");
        var report = new { passed=true, selections, transitions, fixedFiles=22, gameLaunched=false, fixture=root };
        await File.WriteAllTextAsync(Path.Combine(root, "results.json"), JsonSerializer.Serialize(report));
        Console.WriteLine(JsonSerializer.Serialize(report));
    }
}

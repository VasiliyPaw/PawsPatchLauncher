using System.Text.Json;
using System.Text.RegularExpressions;
using PawsPatchLauncher;

internal static class SplitLanguageTests
{
    internal static async Task RunAsync(string configPath, string output)
    {
        var root = Path.GetFullPath(output);
        if (Directory.Exists(root)) throw new IOException("Choose a new isolated test directory.");
        Directory.CreateDirectory(root);
        var config = JsonSerializer.Deserialize(File.ReadAllText(configPath), LauncherJsonContext.Default.LauncherConfiguration)!;
        config.CacheRoot = Path.Combine(root, "cache");
        var client = new FeedClient(config);
        var feed = (await client.GetChannelAsync())!;
        var count = 0;
        void Check(bool ok, string why) { if (!ok) throw new Exception("Split languages: " + why); count++; }
        ChannelManifest Clone() => JsonSerializer.Deserialize(JsonSerializer.Serialize(feed, LauncherJsonContext.Default.ChannelManifest), LauncherJsonContext.Default.ChannelManifest)!;
        UserSettings Settings(string mod, bool text, string voice) => new() { Mod = mod, RussianLocalization = text, GameVoiceLanguage = voice,
            PawPatchEnabled = false, RoamingSpawnMode = "standard", AdditionalRoamingCompanies = false, IndependentHostility = false,
            SiegeBalance = false, DisablePowersAndShards = false };
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (var text in new[] { false, true })
        foreach (var voice in new[] { "en", "ru" })
        {
            var settings = Settings(mod, text, voice);
            var selected = GamePackageSelector.Select(feed, settings, text, false);
            Check(selected.Any(p => p.Id == "game-voice-ru") == (voice == "ru"), "speech coupled to text");
            Check(selected.All(p => p.DependsOn.All(d => selected.Any(q => q.Id == d))), "missing dependency");
            Check(ModLibrary.Packages(feed, mod).All(p => !GameLanguages.IsLanguage(p)), "unselected language in installation");
            var imported = ConfigurationCode.Parse(ConfigurationCode.Create(settings));
            Check(imported.RussianLocalization == text && GameLanguages.Voice(imported) == voice, "code lost separate voice");
            ModChannelSelection.SelectMod(settings, mod == GameMod.Immortals ? GameMod.Vanilla : GameMod.Immortals);
            Check(settings.RussianLocalization == text && GameLanguages.Voice(settings) == voice, "mode switch changed language");
            var changed = Clone(); changed.Packages.Single(p => p.Id == "game-voice-ru").Version += ".new";
            settings = Settings(mod, text, voice);
            Check(!ModLibrary.HasUpdate(feed, changed, mod), "speech update marked the whole mod outdated");
            Check(GameLanguages.HasUpdate(feed, changed, settings) == (voice == "ru"), "unselected voice update was offered");
            changed = Clone(); changed.Packages.Single(p => p.Id == "immortals-localization-ru").Version += ".new";
            Check(GameLanguages.HasUpdate(feed, changed, settings) == (mod == GameMod.Immortals && text), "Immortals translation update leaked");
        }
        foreach (var text in new[] { false, true })
            Check(GameLanguages.Voice(new() { RussianLocalization = text }) == (text ? "ru" : "en"), "legacy language migration");

        var game = Path.Combine(root, "game"); Directory.CreateDirectory(game);
        var installer = new ModuleInstaller(game); var library = new ModLibrary(game);
        var voicePackage = feed.Packages.Single(p => p.Id == "game-voice-ru");
        async Task Apply(string mod, bool text, string voice, bool fixes = false)
        {
            var settings = Settings(mod, text, voice);
            settings.PawPatchEnabled = fixes;
            var selected = GamePackageSelector.Select(feed, settings, text, false);
            // This is a resources-only test; no EXE is launched or installed.
            selected.RemoveAll(p => !p.ExecutableIndependent);
            var modules = new Dictionary<string, InstalledModule>();
            foreach (var p in selected)
                modules[p.Id] = await installer.PrepareAsync(p, await client.DownloadVerifiedAsync(p, null));
            await installer.ReconcileAsync(modules, settings: settings, releaseId: ChannelFingerprint.Create(feed));
            await library.RememberLanguagesAsync(selected);
            Check((await installer.VerifyAsync()).Count == 0, "installed resources failed verification");
            Check(!UpdateDetector.HasSettingsChanges(installer.LoadState(), selected, settings), "applied settings stay pending");
            Check(installer.LoadState().Modules.ContainsKey("game-voice-ru") == (voice == "ru"), "wrong active speech package");
            Check(!File.Exists(Path.Combine(game, "Local_Ru.rwd")), "combined text/speech archive installed");
            if (mod == GameMod.Immortals)
            {
                var added = File.ReadAllText(Path.Combine(game, "data/Localization/strings_immortals_translation.tgi"));
                var keys = Regex.Matches(added, @"(?m)^\s*(immortals_\w+)\s*=").Select(m => m.Groups[1].Value).ToHashSet(StringComparer.OrdinalIgnoreCase);
                Check(keys.Count == 23, "translation does not own 23 unique keys");
                var otherTables = Directory.GetFiles(Path.Combine(game, "data/Localization"), "*.tgi").Where(p => !p.EndsWith("strings_immortals_translation.tgi"));
                Check(otherTables.All(p => Regex.Matches(File.ReadAllText(p), @"(?m)^\s*(\w+)\s*=").All(m => !keys.Contains(m.Groups[1].Value))), "duplicate translation key crashes the game");
            }
        }
        await Apply(GameMod.Immortals, true, "en");
        Check(!client.IsPackageCached(voicePackage) && !installer.IsPrepared(voicePackage), "Russian speech downloaded before being selected");
        Check(File.Exists(Path.Combine(game, "Local_immortals_ru/Localization/strings_immortals_translation.tgi")), "missing Immortals translations");
        await Apply(GameMod.Vanilla, false, "ru");
        Check(client.IsPackageCached(voicePackage), "selected speech was not cached");
        Check(!File.Exists(Path.Combine(game, "Local_immortals_ru/Localization/strings_immortals_translation.tgi")), "Immortals strings leaked into Vanilla");
        await Apply(GameMod.Vanilla, true, "ru");
        await Apply(GameMod.Immortals, false, "en");
        await Apply(GameMod.Immortals, true, "ru", true);
        await Apply(GameMod.Immortals, false, "en", true);
        // Remove all access to source archives; restart the client with the retained cache.
        var stamps = Directory.GetFiles(Path.Combine(config.CacheRoot, "downloads"), "*.zip", SearchOption.AllDirectories).ToDictionary(p => p, File.GetLastWriteTimeUtc);
        foreach (var p in feed.Packages) p.Urls = [Path.Combine(root, "unavailable-source", p.Id + ".zip")];
        client = new FeedClient(config);
        foreach (var mod in new[] { GameMod.Immortals, GameMod.Vanilla })
        foreach (var text in new[] { false, true })
        foreach (var voice in new[] { "ru", "en" }) await Apply(mod, text, voice);
        Check(stamps.All(p => File.GetLastWriteTimeUtc(p.Key) == p.Value), "cached language was downloaded again");
        var cleanup = StorageMaintenance.Scan(new(config.CacheRoot, game, null, [], []), DateTime.UtcNow.AddDays(30));
        Check(cleanup.Entries.Where(p => p.Kind == "packages" && p.Path.Contains("game-voice-ru")).All(p => !p.Cleanable), "inactive speech would be removed by cleanup");
        Console.WriteLine($"SPLIT LANGUAGES PASS {count}: 12 language/mode selections, scoped updates, actual packages, no unselected speech download, offline reuse, transactional cleanup, 23 Immortals strings.");
    }
}

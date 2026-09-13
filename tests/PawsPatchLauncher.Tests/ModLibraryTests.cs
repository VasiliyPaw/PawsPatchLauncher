using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class ModLibraryTests
{
    internal static async Task<int> RunAsync(string parent)
    {
        var root = Path.Combine(parent, "mod-library");
        var game = Path.Combine(root, "game");
        var cache = Path.Combine(root, "cache");
        var sources = Path.Combine(root, "sources");
        Directory.CreateDirectory(game); Directory.CreateDirectory(sources);
        await File.WriteAllTextAsync(Path.Combine(game, "k2.exe"), "untouched game executable");
        var count = 0;
        void Check(bool value, string message) { if (!value) throw new InvalidOperationException("Mod library: " + message); count++; }
        async Task MustFail(Func<Task> operation, string message)
        {
            try { await operation(); } catch (Exception ex) when (ex is IOException or InvalidDataException) { count++; return; }
            throw new InvalidOperationException("Mod library: " + message);
        }
        var originalExe = await CryptoAndIO.Sha256Async(Path.Combine(game, "k2.exe"));
        var channel = new ChannelManifest { PublishedAt = "2026-09-10", Game = new() { K2ExeSha256 = [] } };
        async Task<PackageRelease> Package(string id, int priority, Dictionary<string, string> files, bool required = false)
        {
            var archive = Path.Combine(sources, id + ".zip");
            var manifest = new ModuleArchiveManifest { Id = id, Version = "1.0.0" };
            using (var zip = ZipFile.Open(archive, ZipArchiveMode.Create))
            {
                foreach (var (name, body) in files)
                {
                    var bytes = Encoding.UTF8.GetBytes(body);
                    manifest.Files.Add(new() { Path = name, Size = bytes.Length, Sha256 = Convert.ToHexString(SHA256.HashData(bytes)) });
                    using var output = zip.CreateEntry("payload/" + name).Open(); output.Write(bytes);
                }
                using var writer = new StreamWriter(zip.CreateEntry("module.json").Open());
                writer.Write(JsonSerializer.Serialize(manifest, LauncherJsonContext.Default.ModuleArchiveManifest));
            }
            return new() { Id = id, Version = manifest.Version, Priority = priority, Required = required,
                ExecutableIndependent = true, Size = new FileInfo(archive).Length, Sha256 = await CryptoAndIO.Sha256Async(archive), Urls = [archive] };
        }
        channel.Packages.Add(await Package("arcane-wars", 10, new() { ["data/shared.txt"] = "AW", ["data/aw.txt"] = "AW base" }, true));
        channel.Packages.Add(await Package("startup-base", 20, new() { ["startup/base.txt"] = "base" }, true));
        channel.Packages.Add(await Package("pawpatch-core", 30, new() { ["data/shared.txt"] = "PAW" }, true));
        channel.Packages.Add(await Package("aw-siege-balance", 40, new() { ["data/cost.txt"] = "0.75" }));
        channel.Packages.Add(await Package("game-localization-en", 90, new() { ["startup/language.txt"] = "en" }));
        channel.Packages.Add(await Package("vanilla-localization-ru", 100, new() { ["startup/language.txt"] = "ru" }));
        channel.Packages.Add(await Package("aw-localization-ru", 110, new() { ["startup/language.txt"] = "ru" }));
        channel.Packages.Add(await Package("immortals", 10, new() { ["data/shared.txt"] = "IMM", ["data/imm.txt"] = "Immortals" }));
        channel.Packages.Add(await Package("immortals-localization-ru", 100, new() { ["startup/language.txt"] = "ru" }));
        channel.Packages.Add(await Package("pure-fixes-data", 900, new() { ["data/badge-fix.txt"] = "badge colors only" }));
        var runtime = await Package("pure-fixes-runtime", 910, new() { ["k2_paws_pure_fixes_1372.exe"] = "nonexecuted fixture runtime" });
        runtime.ExecutableIndependent = false; channel.Packages.Add(runtime);
        channel.Packages.Add(await Package("immortals-text-fixes", 920, new() { ["data/missing-labels.txt"] = "labels only" }));
        using var signing = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var payload = JsonSerializer.SerializeToUtf8Bytes(channel, LauncherJsonContext.Default.ChannelManifest);
        var signed = new SignedFeedEnvelope { KeyId = "local-unit-test", Payload = Convert.ToBase64String(payload),
            Signature = Convert.ToBase64String(signing.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation)) };
        var feedFile = Path.Combine(sources, "feed.json");
        await File.WriteAllTextAsync(feedFile, JsonSerializer.Serialize(signed, LauncherJsonContext.Default.SignedFeedEnvelope));
        var configuration = new LauncherConfiguration { FeedUrls = [feedFile], BetaFeedUrls = [], CacheRoot = cache, PublicKeyPem = signing.ExportSubjectPublicKeyInfoPem() };
        var client = new FeedClient(configuration);
        channel = (await client.GetChannelAsync())!;
        var installer = new ModuleInstaller(game);
        var library = new ModLibrary(game);
        foreach (var mod in new[] { GameMod.ArcaneWars, GameMod.Immortals, GameMod.Vanilla })
        {
            foreach (var package in ModLibrary.Packages(channel, mod))
                await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null));
            await library.RememberAsync(channel, mod);
        }
        Check(library.Load().Mods.Count == 3, "installing another mod removed a library entry");
        Check(ModLibrary.Packages(channel, GameMod.Immortals).Count == 5, "Immortals did not include all optional fixes without downloading languages");
        Check(ModLibrary.Packages(channel, GameMod.Immortals).All(p => !GameLanguages.IsLanguage(p)), "unselected languages were downloaded with the mod");
        // Simulate choosing each text language once, before testing reuse with no source.
        foreach (var language in channel.Packages.Where(GameLanguages.IsLanguage))
            await installer.PrepareAsync(language, await client.DownloadVerifiedAsync(language, null));
        await library.RememberLanguagesAsync(channel.Packages.Where(GameLanguages.IsLanguage));
        Check(ModLibrary.Packages(channel, GameMod.ArcaneWars).Any(p => p.Id == "aw-siege-balance"), "disabled component was omitted");
        Check(!ModLibrary.Packages(channel, GameMod.Immortals).Any(p => p.Id.Contains("pawpatch")), "AW packages leaked into Immortals");

        var legacy = new ChannelManifest { Packages = channel.Packages.Where(p => p.Id is "arcane-wars" or "startup-base" or "pawpatch-core").ToList() };
        var legacyRoot = Path.Combine(root, "legacy-game");
        var legacyLibrary = new ModLibrary(legacyRoot);
        await legacyLibrary.RememberAsync(legacy, GameMod.Vanilla);
        Check(legacyLibrary.Find(GameMod.Vanilla, "stable") is null && legacyLibrary.Load().Mods.Count == 0,
            "AW-only catalog created an installed Vanilla release");
        Directory.CreateDirectory(Path.Combine(legacyRoot, ".pawpatch"));
        var emptyEntry = new ModLibraryEntry { Mod = GameMod.Vanilla, Channel = "stable", ReleaseId = ChannelFingerprint.Create(legacy),
            ContentId = ModLibrary.ContentId(legacy, GameMod.Vanilla), Packages = [] };
        await File.WriteAllTextAsync(Path.Combine(legacyRoot, ".pawpatch", "mod-library.json"),
            JsonSerializer.Serialize(new ModLibraryDocument { Mods = [emptyEntry] }, LauncherJsonContext.Default.ModLibraryDocument));
        Check(legacyLibrary.Find(GameMod.Vanilla, "stable") is null, "0.7.0 empty Vanilla entry survived migration");
        await legacyLibrary.RememberAsync(channel, GameMod.Vanilla);
        var repairedVanilla = legacyLibrary.Find(GameMod.Vanilla, "stable");
        Check(repairedVanilla is not null && repairedVanilla.Packages.Any(p => p.Id == "pure-fixes-data"), "new Vanilla installation did not replace the empty entry");
        await legacyLibrary.RememberAsync(legacy, GameMod.Vanilla);
        Check(legacyLibrary.Find(GameMod.Vanilla, "stable")?.ReleaseId == repairedVanilla!.ReleaseId,
            "an old catalog replaced the real Vanilla component release");

        // Remove every download source and cached ZIP. Only the installed local library remains.
        foreach (var file in Directory.GetFiles(sources)) File.Delete(file);
        foreach (var file in Directory.GetFiles(Path.Combine(cache, "downloads"), "*", SearchOption.AllDirectories)) File.Delete(file);
        client = new FeedClient(configuration);
        Check(client.LoadArchived(ChannelFingerprint.Create(channel), "stable").Packages.Count == channel.Packages.Count, "signed release unavailable after restart");
        async Task Apply(string mod, bool russian, bool siege = false, bool fixes = false, bool dataOnly = false)
        {
            var entry = new ModLibrary(game).Find(mod, "stable")!;
            var local = client.LoadArchived(entry.ReleaseId, entry.Channel);
            var preferences = new UserSettings { Mod = mod, PawPatchEnabled = false, RussianLocalization = russian,
                VanillaPawPatchEnabled = fixes, ImmortalsPawPatchEnabled = fixes, DataOnly = dataOnly,
                SiegeBalance = siege, IndependentHostility = false, AdditionalRoamingCompanies = false, RoamingSpawnMode = "standard", DisablePowersAndShards = false };
            var active = EffectiveSettings.ForFeed(preferences, local);
            var selected = GamePackageSelector.Select(local, active, russian, false);
            var modules = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase);
            foreach (var package in selected) modules[package.Id] = await installer.ReadPreparedAsync(package);
            await installer.ReconcileAsync(modules, settings: active, releaseId: entry.ReleaseId);
            var state = installer.LoadState();
            Check(ModLibrary.IsActive(state, preferences), "switch did not activate " + mod);
            Check(!UpdateDetector.HasSettingsChanges(state, selected, active), "applied configuration stays pending");
            Check(await File.ReadAllTextAsync(Path.Combine(game, "startup/language.txt")) == (russian ? "ru" : "en"), "wrong language after switch");
            Check(File.Exists(Path.Combine(game, "data/aw.txt")) == (mod == GameMod.ArcaneWars), "inactive AW files leaked");
            Check(File.Exists(Path.Combine(game, "data/imm.txt")) == (mod == GameMod.Immortals), "inactive Immortals files leaked");
            Check(File.Exists(Path.Combine(game, "data/cost.txt")) == (mod == GameMod.ArcaneWars && siege), "disabled component leaked");
            Check(File.Exists(Path.Combine(game, "data/badge-fix.txt")) == (mod != GameMod.ArcaneWars && fixes), "badge fix leaked or disappeared");
            Check(File.Exists(Path.Combine(game, "k2_paws_pure_fixes_1372.exe")) == (mod != GameMod.ArcaneWars && fixes && !dataOnly), "native pure fix leaked into disabled/data-only profile");
            Check(File.Exists(Path.Combine(game, "data/missing-labels.txt")) == (mod == GameMod.Immortals && fixes), "Immortals strings leaked into another mod");
            Check((await installer.VerifyAsync()).Count == 0, "active file verification failed");
            Check(await CryptoAndIO.Sha256Async(Path.Combine(game, "k2.exe")) == originalExe, "original EXE changed");
            Check(library.Load().Mods.Count == 3, "switch forgot inactive mods");
        }
        foreach (var russian in new[] { false, true })
        {
            await Apply(GameMod.ArcaneWars, russian, true);
            await Apply(GameMod.Immortals, russian);
            await Apply(GameMod.Vanilla, russian);
            await Apply(GameMod.ArcaneWars, russian);
            await Apply(GameMod.Vanilla, russian, fixes: true);
            await Apply(GameMod.Immortals, russian, fixes: true);
            await Apply(GameMod.Vanilla, russian, fixes: true, dataOnly: true);
            await Apply(GameMod.Immortals, russian, fixes: true, dataOnly: true);
            await Apply(GameMod.ArcaneWars, russian);
        }
        var offered = JsonSerializer.Deserialize(JsonSerializer.Serialize(channel, LauncherJsonContext.Default.ChannelManifest), LauncherJsonContext.Default.ChannelManifest)!;
        offered.Packages.Single(p => p.Id == "pawpatch-core").Version = "2.0.0";
        Check(ModLibrary.HasUpdate(channel, offered, GameMod.ArcaneWars), "AW update was missed");
        Check(!ModLibrary.HasUpdate(channel, offered, GameMod.Immortals), "AW update was shown for Immortals");
        Check(!ModLibrary.HasUpdate(channel, offered, GameMod.Vanilla), "AW update was shown for Vanilla");
        await Apply(GameMod.Immortals, true);
        Check(!ModLibrary.IsActive(installer.LoadState(), new() { Mod = GameMod.ArcaneWars }), "selecting AW was treated as applying it");
        await Apply(GameMod.ArcaneWars, true);
        Check(ModLibrary.IsActive(installer.LoadState(), new() { Mod = GameMod.ArcaneWars }), "applied AW not eligible for its update");
        offered.PublishedAt = "2026-09-11"; offered.Packages = channel.Packages;
        offered.NewsTitle.Ru = "Metadata-only refresh";
        Check(!ModLibrary.HasUpdate(channel, offered, GameMod.ArcaneWars), "documentation caused a gameplay update");
        var plan = StorageMaintenance.Scan(new(cache, game, null, [], []), DateTime.UtcNow.AddDays(30));
        Check(plan.Entries.Where(e => e.Kind == "packages").All(e => !e.Cleanable), "cleanup would remove an inactive mod/component");
        Check(plan.Entries.Count(e => e.Kind == "packages") == channel.Packages.Count, "not all prepared components were retained");
        var corrupt = Path.Combine(game, ".pawpatch", "packages", "immortals", "1.0.0", "payload", "data", "imm.txt");
        await File.WriteAllTextAsync(corrupt, "tampered!");
        await MustFail(() => installer.ReadPreparedAsync(channel.Packages.Single(p => p.Id == "immortals")), "tampered component was trusted");
        Check(await CryptoAndIO.Sha256Async(Path.Combine(game, "k2.exe")) == originalExe, "failed validation changed game");
        Console.WriteLine($"MOD LIBRARY PASS {count}: offline switches, both languages, inactive retention, scoped updates, tamper detection");
        return count;
    }
}

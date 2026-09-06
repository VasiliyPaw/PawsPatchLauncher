using System.Text.Json;
using PawsPatchLauncher;

public static class CleanInstallTests
{
    public static async Task RunAsync(string stableFeed, string betaFeed, string publicKey, string stockExe, string fixtureRoot)
    {
        var root = Path.Combine(Path.GetFullPath(fixtureRoot), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var config = new LauncherConfiguration
        {
            FeedUrls = [Path.GetFullPath(stableFeed)], BetaFeedUrls = [Path.GetFullPath(betaFeed)],
            PublicKeyPem = await File.ReadAllTextAsync(publicKey), CacheRoot = Path.Combine(root, "cache")
        };
        var client = new FeedClient(config);
        var results = new List<string>();
        var commonUiProfiles = new List<string>();
        foreach (var name in new[] { "stable-en", "stable-ru", "beta-en", "beta-ru" })
        {
            var beta = name.StartsWith("beta"); var ru = name.EndsWith("ru");
            var game = Path.Combine(root, name, "Kohan II"); Directory.CreateDirectory(game);
            File.Copy(stockExe, Path.Combine(game, "k2.exe")); // Read-only source; game never launched.
            await File.WriteAllTextAsync(Path.Combine(game, "untouched-save.sav"), "user save sentinel");
            var settings = new UserSettings { Channel = beta ? "beta" : "stable", RussianLocalization = ru,
                CustomPlayerColors = beta, IndependentHostility = beta || ru, DesyncMode = !beta && !ru ? "continue" : "official",
                RoamingSpawnMode = ru ? "x4" : "standard", AdditionalRoamingCompanies = ru, SiegeBalance = ru };
            var channel = await client.GetChannelAsync(settings.Channel) ?? throw new Exception("No signed channel.");
            var installer = new ModuleInstaller(game);
            if (installer.LoadState().Modules.Count != 0 || Directory.Exists(Path.Combine(game, ".pawpatch"))) throw new Exception("Fixture is not clean.");
            // Same package selection and installer as the real UI; no old installation state or files.
            var selected = GamePackageSelector.Select(channel, settings, ru, beta);
            if (!selected.Any(p => p.Id == "startup-base" && p.Required)) throw new Exception("Required startup package missing.");
            var modules = new Dictionary<string, InstalledModule>();
            foreach (var package in selected.OrderBy(p => p.Priority))
                modules[package.Id] = await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null));
            await installer.ReconcileAsync(modules, settings: settings, releaseId: ChannelFingerprint.Create(channel));
            if ((await installer.VerifyAsync()).Count != 0) throw new Exception("Clean install hashes differ.");
            var startup = await File.ReadAllTextAsync(Path.Combine(game, "startup", "autoexec.txt"));
            if (!startup.Split('\n').Any(l => l.Trim().Equals("adddepot %USERDATA%/data/ 1", StringComparison.OrdinalIgnoreCase)))
                throw new Exception("Work depot not specified in active startup configuration.");
            var executable = Path.Combine(game, GameExecutableSelector.Select(config, beta, settings.DesyncMode == "continue", settings.IndependentHostility, GameExecutableSelector.HasCommonUi(channel)));
            var critical = await MultiplayerCheck.CriticalAsync(game, installer.LoadState(), executable, channel.Game);
            if (critical.Count != 0) throw new Exception("Preflight: " + string.Join("; ", critical));
            Console.WriteLine("CLEAN INSTALL PASS " + name + ": hashes, work depot, selected EXE, preflight; game NOT launched");
            if (name == "beta-ru" && GameExecutableSelector.HasCommonUi(channel))
            {
                var commonFiles = new[] { "paws_patch_versions.ini", Path.Combine("data", "UI", "Menus", "main.tgi") };
                var commonHashes = new Dictionary<string, string>();
                foreach (var file in commonFiles) commonHashes[file] = await CryptoAndIO.Sha256Async(Path.Combine(game, file));
                // All eight settings combinations, including all-off, must keep the same
                // mandatory UI data and select an installed helper with common hooks.
                foreach (var colors in new[] { false, true })
                foreach (var bypass in new[] { false, true })
                foreach (var hostility in new[] { false, true })
                {
                    settings.CustomPlayerColors = colors;
                    settings.DesyncMode = bypass ? "continue" : "official";
                    settings.IndependentHostility = hostility;
                    var profilePackages = GamePackageSelector.Select(channel, settings, ru, colors);
                    if (!profilePackages.Any(p => p.Id == "common-ui" && p.Required))
                        throw new Exception("Settings disabled the mandatory common UI package.");
                    var profileModules = new Dictionary<string, InstalledModule>();
                    foreach (var package in profilePackages.OrderBy(p => p.Priority))
                        profileModules[package.Id] = await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null));
                    await installer.ReconcileAsync(profileModules, settings: settings, releaseId: ChannelFingerprint.Create(channel));
                    if ((await installer.VerifyAsync()).Count != 0) throw new Exception("Profile transition hashes differ.");
                    foreach (var file in commonFiles)
                        if (commonHashes[file] != await CryptoAndIO.Sha256Async(Path.Combine(game, file)))
                            throw new Exception("Settings changed mandatory UI data: " + file);
                    var selectedExe = GameExecutableSelector.Select(config, colors, bypass, hostility, true);
                    if (selectedExe == "k2.exe") throw new Exception("Common UI was bypassed.");
                    var checks = await MultiplayerCheck.CriticalAsync(game, installer.LoadState(), Path.Combine(game, selectedExe), channel.Game);
                    if (checks.Count != 0) throw new Exception("Profile preflight: " + string.Join("; ", checks));
                    var profileName = $"colors={colors}, bypass={bypass}, hostility={hostility}";
                    commonUiProfiles.Add(profileName);
                    Console.WriteLine("COMMON UI PROFILE PASS " + profileName + ": " + selectedExe);
                }
            }
            await installer.UninstallAsync();
            var remaining = Directory.GetFiles(game, "*", SearchOption.AllDirectories)
                .Where(p => !p.StartsWith(Path.Combine(game, ".pawpatch") + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                .Select(p => Path.GetRelativePath(game, p)).Order().ToArray();
            if (!remaining.SequenceEqual(new[] { "k2.exe", "untouched-save.sav" })) throw new Exception("Uninstall left managed files or removed sentinel.");
            if (await CryptoAndIO.Sha256Async(Path.Combine(game, "k2.exe")) != await CryptoAndIO.Sha256Async(stockExe)) throw new Exception("Stock EXE changed.");
            Console.WriteLine("REAL-PACKAGE UNINSTALL PASS " + name + ": stock EXE and save preserved");
            results.Add(name);
        }
        await File.WriteAllTextAsync(Path.Combine(root, "results.json"), JsonSerializer.Serialize(new { passed = true, profiles = results, commonUiProfiles, gameLaunched = false, tempRoot = root }));
        Console.WriteLine("CLEAN INSTALL AUDIT " + root);
    }
}

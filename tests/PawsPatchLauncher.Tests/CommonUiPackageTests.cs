using System.Text.Json;
using PawsPatchLauncher;

public static class CommonUiPackageTests
{
    public static async Task RunAsync(string feedPath, string publicKey, string stockExe, string fixtureRoot)
    {
        var root = Path.Combine(Path.GetFullPath(fixtureRoot), Guid.NewGuid().ToString("N"));
        var game = Path.Combine(root, "Kohan II");
        Directory.CreateDirectory(game);
        File.Copy(stockExe, Path.Combine(game, "k2.exe"));
        var config = new LauncherConfiguration { BetaFeedUrls = [Path.GetFullPath(feedPath)],
            PublicKeyPem = await File.ReadAllTextAsync(publicKey), CacheRoot = Path.Combine(root, "cache") };
        var client = new FeedClient(config);
        var feed = await client.GetChannelAsync("beta") ?? throw new Exception("Candidate feed missing.");
        var installer = new ModuleInstaller(game);
        var prepared = new Dictionary<string, InstalledModule>();
        // Small, real packages only. Full Arcane Wars clean installation is tested separately.
        foreach (var package in feed.Packages.Where(p => p.Id is "common-ui" or "player-colors" or "desync-continue"))
            prepared[package.Id] = await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null));
        var profiles = new List<string>();
        var helperHashes = new Dictionary<string, string>();
        foreach (var colors in new[] { false, true })
        foreach (var bypass in new[] { false, true })
        foreach (var hostility in new[] { false, true })
        {
            var settings = new UserSettings { Channel = "beta", CustomPlayerColors = colors,
                DesyncMode = bypass ? "continue" : "official", IndependentHostility = hostility };
            var fullSelection = GamePackageSelector.Select(feed, settings, true, colors);
            if (!fullSelection.Any(p => p.Id == "common-ui" && p.Required)) throw new Exception("Common UI became optional.");
            var desired = fullSelection.Where(p => prepared.ContainsKey(p.Id)).ToDictionary(p => p.Id, p => prepared[p.Id]);
            await installer.ReconcileAsync(desired, settings: settings, releaseId: ChannelFingerprint.Create(feed));
            if ((await installer.VerifyAsync()).Count != 0) throw new Exception("Installed package hashes differ.");
            var selected = GameExecutableSelector.Select(config, colors, bypass, hostility, GameExecutableSelector.HasCommonUi(feed));
            if (selected == "k2.exe") throw new Exception("All-off bypassed UI helper.");
            var critical = await MultiplayerCheck.CriticalAsync(game, installer.LoadState(), Path.Combine(game, selected), feed.Game);
            if (critical.Count != 0) throw new Exception(string.Join("; ", critical));
            var expected = MultiplayerCheck.Expected(installer.LoadState());
            var versionFile = await File.ReadAllTextAsync(Path.Combine(game, "paws_patch_versions.ini"));
            if (!versionFile.Contains("PawPatch=1.3.72-data.8-r2+ui.1")) throw new Exception("Stale version metadata.");
            foreach (var file in prepared["common-ui"].Files)
                if (expected[CryptoAndIO.NormalizeRelativePath(file.Path)]?.Sha256 != file.Sha256)
                    throw new Exception("Older helper overrode common UI: " + file.Path);
            helperHashes[selected] = await CryptoAndIO.Sha256Async(Path.Combine(game, selected));
            var description = $"colors={colors}, bypass={bypass}, hostility={hostility}";
            profiles.Add(description);
            Console.WriteLine("COMMON UI PACKAGE PASS " + description + ": " + selected);
        }
        if (helperHashes.Count != 5) throw new Exception("Not all five active helpers covered.");
        await installer.UninstallAsync();
        if (!File.Exists(Path.Combine(game, "k2.exe")) || File.Exists(Path.Combine(game, "paws_patch_versions.ini")))
            throw new Exception("UI package uninstall failed.");
        await File.WriteAllTextAsync(Path.Combine(root, "results.json"), JsonSerializer.Serialize(new {
            passed = true, scope = "real UI/color/desync package overlays, not full game installation",
            profiles, helperHashes, uninstallPassed = true, gameLaunched = false }));
        Console.WriteLine("COMMON UI PACKAGE AUDIT " + root);
    }
}

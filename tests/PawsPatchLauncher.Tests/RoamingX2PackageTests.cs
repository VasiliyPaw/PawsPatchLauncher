using PawsPatchLauncher;

internal static class RoamingX2PackageTests
{
    internal static async Task RunAsync(string feedPath, string publicKeyPath, string fixtureRoot)
    {
        var root = Path.GetFullPath(Path.Combine(fixtureRoot, Guid.NewGuid().ToString("N")));
        Directory.CreateDirectory(root);
        var client = new FeedClient(new() { FeedUrls = [Path.GetFullPath(feedPath)], BetaFeedUrls = [],
            PublicKeyPem = await File.ReadAllTextAsync(publicKeyPath), CacheRoot = Path.Combine(root, "cache") });
        var feed = await client.GetChannelAsync("stable") ?? throw new Exception("Missing fixture feed");
        var installer = new ModuleInstaller(Path.Combine(root, "game"));
        var prepared = new Dictionary<string, InstalledModule>();
        foreach (var package in feed.Packages)
            prepared[package.Id] = await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null));
        var checks = 0;
        // Non-monotonic transitions exercise removal/restoration rather than just a clean final profile.
        foreach (var (mode, extra) in new[] { ("x4", true), ("x2", false), ("standard", true), ("x2", true), ("standard", false), ("x4", false), ("x2", false) })
        {
            var settings = new UserSettings { RoamingSpawnMode = mode, AdditionalRoamingCompanies = extra, CustomPlayerColors = true, DesyncMode = "continue", IndependentHostility = false };
            var selected = GamePackageSelector.Select(feed, settings, true, true);
            await installer.ReconcileAsync(selected.ToDictionary(p => p.Id, p => prepared[p.Id]), settings: settings, releaseId: ChannelFingerprint.Create(feed));
            var errors = await installer.VerifyAsync();
            if (errors.Count > 0) throw new Exception(string.Join("; ", errors));
            var state = installer.LoadState();
            if (UpdateDetector.HasSettingsChanges(state, selected, settings)) throw new Exception("Apply remains pending");
            var badges = state.Modules["common-ui"].Files.Count(f => f.Path.Contains("Organizations", StringComparison.OrdinalIgnoreCase) && (f.Path.EndsWith(".NIF", StringComparison.OrdinalIgnoreCase) || f.Path.EndsWith("PlayerColor.tga", StringComparison.OrdinalIgnoreCase)));
            if (badges != 14) throw new Exception("Seven badge models/textures were lost");
            checks++;
            Console.WriteLine($"X2 FILE TRANSITION PASS {mode} new={extra}: all installed hashes, translation-bearing overlays, seven badges and applied state");
        }
        Console.WriteLine($"X2 INSTALL PASS {checks}: {root}; no game launched or user installation changed");
    }
}

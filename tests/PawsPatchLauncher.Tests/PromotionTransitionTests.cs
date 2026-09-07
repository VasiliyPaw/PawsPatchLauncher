using PawsPatchLauncher;

public static class PromotionTransitionTests
{
    public static async Task RunAsync(string oldBeta, string release, string publicKey, string fixtureRoot)
    {
        var root = Path.Combine(Path.GetFullPath(fixtureRoot), Guid.NewGuid().ToString("N"));
        var game = Path.Combine(root, "Kohan II"); Directory.CreateDirectory(game);
        var original = Path.Combine(game, "data", "Organizations", "Banners", "Fallen", "FallenBanner.NIF");
        Directory.CreateDirectory(Path.GetDirectoryName(original)!);
        await File.WriteAllTextAsync(original, "preexisting model sentinel");
        await File.WriteAllTextAsync(Path.Combine(game, "user-save.sav"), "save sentinel");
        var config = new LauncherConfiguration { BetaFeedUrls = [Path.GetFullPath(oldBeta)], FeedUrls = [Path.GetFullPath(release)],
            PublicKeyPem = await File.ReadAllTextAsync(publicKey), CacheRoot = Path.Combine(root, "cache") };
        var client = new FeedClient(config); var installer = new ModuleInstaller(game);
        async Task Apply(string name, bool colors, bool bypass, bool hostility)
        {
            var feed = await client.GetChannelAsync(name) ?? throw new Exception("Missing feed.");
            var settings = new UserSettings { Channel = name, CustomPlayerColors = colors,
                DesyncMode = bypass ? "continue" : "official", IndependentHostility = hostility };
            var modules = new Dictionary<string, InstalledModule>();
            // The exact packages that change in this migration; full clean game installs are separate.
            foreach (var package in GamePackageSelector.Select(feed, settings, false, colors)
                .Where(p => p.Id is "common-ui" or "player-colors" or "desync-continue"))
                modules[package.Id] = await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null));
            await installer.ReconcileAsync(modules, settings: settings, releaseId: ChannelFingerprint.Create(feed));
            if ((await installer.VerifyAsync()).Count != 0) throw new Exception("Migration payload mismatch.");
        }
        const string newHelper = "k2_paws_lobby_colors_mp_nohostility_sync_1372.exe";
        await Apply("beta", true, true, true);
        if (await File.ReadAllTextAsync(original) != "preexisting model sentinel") throw new Exception("Beta 7 unexpectedly includes models.");
        await Apply("stable", true, true, false);
        var modelHash = await CryptoAndIO.Sha256Async(original);
        if (!File.Exists(Path.Combine(game, newHelper))) throw new Exception("New independent helper missing after promotion.");
        await Apply("stable", false, false, false);
        if (File.Exists(Path.Combine(game, newHelper)) || File.Exists(Path.Combine(game, "paws_player_colors.ini")))
            throw new Exception("All-off left optional color files.");
        if (await CryptoAndIO.Sha256Async(original) != modelHash) throw new Exception("Turning colors off removed shading.");
        await new PatchRecovery(game).RollbackAsync(installer.LoadState());
        if (!File.Exists(Path.Combine(game, newHelper)) || (await installer.VerifyAsync()).Count != 0)
            throw new Exception("Rollback lost independent color helper.");
        await Apply("beta", true, true, true);
        if (File.Exists(Path.Combine(game, newHelper)) || await File.ReadAllTextAsync(original) != "preexisting model sentinel")
            throw new Exception("Pinned Beta 7 downgrade left new files or lost preexisting model.");
        await Apply("stable", false, false, false);
        await installer.UninstallAsync();
        if (await File.ReadAllTextAsync(original) != "preexisting model sentinel"
            || await File.ReadAllTextAsync(Path.Combine(game, "user-save.sav")) != "save sentinel")
            throw new Exception("Uninstall failed to restore originals/preserve saves.");
        Console.WriteLine("PROMOTION TRANSITIONS PASS: Beta7 -> Release combined -> all off -> rollback -> pinned Beta7 -> Release -> uninstall; original model/save preserved. " + root);
    }
}

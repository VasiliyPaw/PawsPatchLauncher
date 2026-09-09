using PawsPatchLauncher;

public static class CityAssistantTransitionTests
{
    public static async Task RunAsync(string stable, string beta, string publicKey, string fixtureRoot)
    {
        var root = Path.Combine(Path.GetFullPath(fixtureRoot), Guid.NewGuid().ToString("N"));
        var game = Path.Combine(root, "Kohan II"); Directory.CreateDirectory(game);
        var layout = Path.Combine(game, "data", "UI", "Game", "paw_city_en.tgi");
        Directory.CreateDirectory(Path.GetDirectoryName(layout)!);
        await File.WriteAllTextAsync(layout, "preexisting user file");
        await File.WriteAllTextAsync(Path.Combine(game, "user-save.sav"), "save sentinel");
        var config = new LauncherConfiguration { FeedUrls = [Path.GetFullPath(stable)], BetaFeedUrls = [Path.GetFullPath(beta)],
            PublicKeyPem = await File.ReadAllTextAsync(publicKey), CacheRoot = Path.Combine(root, "cache") };
        var client = new FeedClient(config); var installer = new ModuleInstaller(game);
        async Task Apply(string name, bool colors, bool bypass, bool hostility)
        {
            var feed = await client.GetChannelAsync(name) ?? throw new Exception("Missing feed.");
            var settings = new UserSettings { Channel = name, CustomPlayerColors = colors,
                DesyncMode = bypass ? "continue" : "official", IndependentHostility = hostility };
            var modules = new Dictionary<string, InstalledModule>();
            foreach (var package in GamePackageSelector.Select(feed, settings, false, colors)
                .Where(p => p.Id is "pawpatch-core" or "common-ui" or "player-colors" or "desync-continue"))
                modules[package.Id] = await installer.PrepareAsync(package, await client.DownloadVerifiedAsync(package, null));
            await installer.ReconcileAsync(modules, settings: settings, releaseId: ChannelFingerprint.Create(feed));
            if ((await installer.VerifyAsync()).Count != 0) throw new Exception("Transition payload mismatch.");
            var state = installer.LoadState();
            if (state.AppliedSettings?.Channel != name || state.Modules["pawpatch-core"].Version != feed.Packages.Single(p => p.Id == "pawpatch-core").Version)
                throw new Exception("Installed patch label would report stale version/channel.");
            if ((await File.ReadAllTextAsync(layout) == "preexisting user file") != (name == "stable"))
                throw new Exception("Assistant layout not installed/restored at channel boundary.");
        }
        await Apply("stable", true, true, true);
        var stableHelper = await CryptoAndIO.Sha256Async(Path.Combine(game, "k2_paws_ui_1372.exe"));
        await Apply("beta", true, true, true);
        await Apply("beta", false, false, false);
        if (File.Exists(Path.Combine(game, "k2_paws_lobby_colors_mp_sync_1372.exe"))) throw new Exception("Optional colors not removed.");
        await Apply("stable", false, false, false);
        if (await CryptoAndIO.Sha256Async(Path.Combine(game, "k2_paws_ui_1372.exe")) != stableHelper) throw new Exception("Stable helper not restored.");
        await new PatchRecovery(game).RollbackAsync(installer.LoadState());
        if (installer.LoadState().AppliedSettings?.Channel != "beta" || (await installer.VerifyAsync()).Count != 0
            || await File.ReadAllTextAsync(layout) == "preexisting user file") throw new Exception("Beta rollback failed.");
        await Apply("stable", false, false, false);
        await installer.UninstallAsync();
        if (await File.ReadAllTextAsync(layout) != "preexisting user file" || await File.ReadAllTextAsync(Path.Combine(game, "user-save.sav")) != "save sentinel")
            throw new Exception("Uninstall failed to restore originals/preserve saves.");
        Console.WriteLine("CITY TRANSITIONS PASS: Release -> Beta -> all off -> Release -> Beta rollback -> Release -> uninstall; installed label, originals/save preserved. " + root);
    }
}

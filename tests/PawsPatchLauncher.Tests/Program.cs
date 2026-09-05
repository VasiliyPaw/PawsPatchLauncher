using PawsPatchLauncher;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

if ((args.Length == 3 || args.Length == 4) && args[0] == "--verify-release")
{
    await VerifyReleaseAsync(args[1], args[2], args.Length == 4 ? args[3] : "stable");
    return;
}

if (args.Length == 4 && args[0] == "--verify-transition")
{
    await VerifyTransitionAsync(args[1], args[2], args[3]);
    return;
}

if (args.Length == 3 && args[0] == "--verify-gameplay-profiles")
{
    await VerifyGameplayProfilesAsync(args[1], args[2]);
    return;
}

var root = Path.Combine(Path.GetTempPath(), "PawsPatchLauncherTests", Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
var passed = 0;

try
{
    ExpectThrows<InvalidDataException>(() => CryptoAndIO.SafeChildPath(root, "..\\escape.txt"));
    passed++;

    var stableFeedPath = Path.Combine(root, "stable.json");
    var betaFeedPath = Path.Combine(root, "beta.json");
    await File.WriteAllTextAsync(stableFeedPath, JsonSerializer.Serialize(new ChannelManifest { Channel = "stable" }, LauncherJsonContext.Default.ChannelManifest));
    await File.WriteAllTextAsync(betaFeedPath, JsonSerializer.Serialize(new ChannelManifest { Channel = "beta" }, LauncherJsonContext.Default.ChannelManifest));
    var channelClient = new FeedClient(new LauncherConfiguration
    {
        FeedUrls = [stableFeedPath],
        BetaFeedUrls = [betaFeedPath],
        CacheRoot = Path.Combine(root, "channel-cache")
    });
    AssertEqual("stable", (await channelClient.GetChannelAsync("stable"))?.Channel);
    AssertEqual("beta", (await channelClient.GetChannelAsync("beta"))?.Channel);
    passed += 2;

    var currentRelease = new PackageRelease { Id = "core", Version = "1.0", Priority = 100, Sha256 = "ABC" };
    var currentState = new InstallState
    {
        Modules = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase)
        {
            ["core"] = new InstalledModule { Version = "1.0", Priority = 100, ArchiveSha256 = "ABC", Enabled = true }
        }
    };
    AssertTrue(!UpdateDetector.HasModuleChanges(currentState, [currentRelease]), "Current packages were reported as outdated.");
    AssertTrue(UpdateDetector.HasModuleChanges(currentState, [new PackageRelease { Id = "core", Version = "1.1", Priority = 100, Sha256 = "DEF" }]), "A newer package was not detected.");
    AssertTrue(UpdateDetector.HasModuleChanges(currentState, []), "A module removed from the selected channel was not detected.");
    passed += 3;

    var configurationCode = ConfigurationCode.Create(new UserSettings
    {
        Channel = "beta",
        IndependentHostility = true,
        RoamingSpawnMode = "standard",
        AdditionalRoamingCompanies = false,
        SiegeBalance = true,
        LargeMapSizes = false,
        RussianLocalization = true,
        CustomPlayerColors = false,
        DesyncMode = "continue"
    });
    AssertEqual("PAW-BETA-IW1-SP1-RM0-SG1-LM0-RU1-CL0-OOS1", configurationCode);
    passed++;

    var fingerprintFeed = new ChannelManifest
    {
        Channel = "stable",
        Game = new GameRequirement { Version = "1.3.72", SteamBuild = "25068126", K2ExeSha256 = ["GAME"] },
        Packages = [new PackageRelease { Id = "core", Version = "1.0", Priority = 100, Size = 10, Sha256 = "HASH" }]
    };
    var stableFingerprint = ChannelFingerprint.Create(fingerprintFeed);
    AssertEqual(stableFingerprint, ChannelFingerprint.Create(fingerprintFeed));
    fingerprintFeed.Channel = "beta";
    AssertTrue(stableFingerprint != ChannelFingerprint.Create(fingerprintFeed), "Changing the channel did not change its fingerprint.");
    fingerprintFeed.Channel = "stable";
    fingerprintFeed.Packages[0].Sha256 = "NEW-HASH";
    AssertTrue(stableFingerprint != ChannelFingerprint.Create(fingerprintFeed), "Changing a package did not change the channel fingerprint.");
    passed += 3;

    var game = Path.Combine(root, "game");
    Directory.CreateDirectory(game);
    await File.WriteAllTextAsync(Path.Combine(game, "shared.txt"), "original");

    var basePackage = await CreatePackageAsync(root, "arcane-wars", "1.0.0", 0,
        new Dictionary<string, string> { ["shared.txt"] = "arcane", ["base-only.txt"] = "base" });
    var patchPackage = await CreatePackageAsync(root, "pawpatch-core", "2.0.0", 100,
        new Dictionary<string, string> { ["shared.txt"] = "patched", ["patch-only.txt"] = "patch" });

    var cacheClient = new FeedClient(new LauncherConfiguration { CacheRoot = Path.Combine(root, "cache-check") });
    AssertTrue(!cacheClient.IsPackageCached(basePackage.Release), "A package was reported cached before download.");
    await cacheClient.DownloadVerifiedAsync(basePackage.Release, null);
    AssertTrue(cacheClient.IsPackageCached(basePackage.Release), "A downloaded package was not reported cached.");
    passed += 2;

    var installer = new ModuleInstaller(game);
    var baseInstalled = await installer.PrepareAsync(basePackage.Release, basePackage.Archive);
    var patchInstalled = await installer.PrepareAsync(patchPackage.Release, patchPackage.Archive);
    await installer.ReconcileAsync(new Dictionary<string, InstalledModule>
    {
        [basePackage.Release.Id] = baseInstalled,
        [patchPackage.Release.Id] = patchInstalled
    });
    AssertEqual("patched", await File.ReadAllTextAsync(Path.Combine(game, "shared.txt")));
    AssertEqual("patch", await File.ReadAllTextAsync(Path.Combine(game, "patch-only.txt")));
    passed += 2;

    await installer.ReconcileAsync(new Dictionary<string, InstalledModule>
    {
        [basePackage.Release.Id] = baseInstalled
    });
    AssertEqual("arcane", await File.ReadAllTextAsync(Path.Combine(game, "shared.txt")));
    AssertTrue(!File.Exists(Path.Combine(game, "patch-only.txt")), "Disabled overlay file was not removed.");
    passed += 2;

    var verifyErrors = await installer.VerifyAsync();
    AssertEqual(0, verifyErrors.Count);
    passed++;

    await File.WriteAllTextAsync(Path.Combine(game, "shared.txt"), "tampered");
    verifyErrors = await installer.VerifyAsync();
    AssertTrue(verifyErrors.Any(x => x.Contains("shared.txt", StringComparison.OrdinalIgnoreCase)), "Tampering was not detected.");
    passed++;

    var adoptedGame = Path.Combine(root, "adopted-game");
    Directory.CreateDirectory(adoptedGame);
    await File.WriteAllTextAsync(Path.Combine(adoptedGame, "shared.txt"), "patched");
    var adoptedInstaller = new ModuleInstaller(adoptedGame);
    var adoptedBase = await adoptedInstaller.PrepareAsync(basePackage.Release, basePackage.Archive);
    var adoptedPatch = await adoptedInstaller.PrepareAsync(patchPackage.Release, patchPackage.Archive);
    await adoptedInstaller.ReconcileAsync(new Dictionary<string, InstalledModule>
    {
        [basePackage.Release.Id] = adoptedBase,
        [patchPackage.Release.Id] = adoptedPatch
    });
    await adoptedInstaller.ReconcileAsync(new Dictionary<string, InstalledModule> { [basePackage.Release.Id] = adoptedBase });
    AssertEqual("arcane", await File.ReadAllTextAsync(Path.Combine(adoptedGame, "shared.txt")));
    passed++;

    var cleanupGame = Path.Combine(root, "cleanup-game");
    Directory.CreateDirectory(cleanupGame);
    await File.WriteAllTextAsync(Path.Combine(cleanupGame, "obsolete.txt"), "manual legacy file");
    var cleanupPackage = await CreatePackageAsync(root, "cleanup", "1.0.0", 500,
        new Dictionary<string, string>(), ["obsolete.txt"]);
    var cleanupInstaller = new ModuleInstaller(cleanupGame);
    var cleanupInstalled = await cleanupInstaller.PrepareAsync(cleanupPackage.Release, cleanupPackage.Archive);
    await cleanupInstaller.ReconcileAsync(new Dictionary<string, InstalledModule> { [cleanupPackage.Release.Id] = cleanupInstalled });
    AssertTrue(!File.Exists(Path.Combine(cleanupGame, "obsolete.txt")), "A declared obsolete file was not removed.");
    AssertEqual(0, (await cleanupInstaller.VerifyAsync()).Count);
    await cleanupInstaller.ReconcileAsync(new Dictionary<string, InstalledModule>());
    AssertEqual("manual legacy file", await File.ReadAllTextAsync(Path.Combine(cleanupGame, "obsolete.txt")));
    passed += 3;

    Console.WriteLine($"PASS {passed}");
}
finally
{
    try { Directory.Delete(root, true); } catch { }
}

static async Task<(PackageRelease Release, string Archive)> CreatePackageAsync(string root, string id, string version, int priority,
    Dictionary<string, string> files, IEnumerable<string>? remove = null)
{
    var source = Path.Combine(root, "source-" + id);
    var payload = Path.Combine(source, "payload");
    Directory.CreateDirectory(payload);
    var manifest = new ModuleArchiveManifest { Id = id, Version = version, Remove = remove?.ToList() ?? [] };
    foreach (var pair in files)
    {
        var path = Path.Combine(payload, pair.Key);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        await File.WriteAllTextAsync(path, pair.Value);
        var bytes = await File.ReadAllBytesAsync(path);
        manifest.Files.Add(new ModuleFile { Path = pair.Key, Size = bytes.Length, Sha256 = Convert.ToHexString(SHA256.HashData(bytes)) });
    }
    await File.WriteAllTextAsync(Path.Combine(source, "module.json"), JsonSerializer.Serialize(manifest, LauncherJsonContext.Default.ModuleArchiveManifest));
    var archive = Path.Combine(root, id + ".zip");
    ZipFile.CreateFromDirectory(source, archive, CompressionLevel.SmallestSize, false);
    var hash = await CryptoAndIO.Sha256Async(archive);
    return (new PackageRelease { Id = id, Version = version, Priority = priority, Sha256 = hash, Size = new FileInfo(archive).Length, Urls = [archive] }, archive);
}

static void AssertEqual<T>(T expected, T actual)
{
    if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new Exception($"Expected {expected}, got {actual}.");
}

static void AssertTrue(bool value, string message)
{
    if (!value) throw new Exception(message);
}

static void ExpectThrows<T>(Action action) where T : Exception
{
    try { action(); }
    catch (T) { return; }
    throw new Exception($"Expected {typeof(T).Name}.");
}

static async Task VerifyReleaseAsync(string feedPath, string publicKeyPath, string channelName)
{
    var root = Path.Combine(Path.GetTempPath(), "PawsPatchLauncherReleaseTests", Guid.NewGuid().ToString("N"));
    var game = Path.Combine(root, "Kohan II");
    Directory.CreateDirectory(game);
    try
    {
        await File.WriteAllTextAsync(Path.Combine(game, "k2.exe"), "test sentinel; never distributed");
        var configuration = new LauncherConfiguration
        {
            FeedUrls = [Path.GetFullPath(feedPath)],
            PublicKeyPem = await File.ReadAllTextAsync(Path.GetFullPath(publicKeyPath)),
            RequireSignedRemoteFeed = true,
            CacheRoot = Path.Combine(root, "cache")
        };
        var client = new FeedClient(configuration);
        if (channelName.Equals("beta", StringComparison.OrdinalIgnoreCase)) configuration.BetaFeedUrls = [Path.GetFullPath(feedPath)];
        var channel = await client.GetChannelAsync(channelName) ?? throw new Exception("Release feed was not loaded.");
        var installer = new ModuleInstaller(game);
        var modules = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase);
        foreach (var package in channel.Packages.OrderBy(x => x.Priority))
        {
            var archive = await client.DownloadVerifiedAsync(package, null);
            modules[package.Id] = await installer.PrepareAsync(package, archive);
        }
        await installer.ReconcileAsync(modules);
        var errors = await installer.VerifyAsync();
        if (errors.Count != 0) throw new Exception("Release verification failed: " + string.Join("; ", errors.Take(10)));
        var state = installer.LoadState();
        var declared = state.Modules.Sum(x => x.Value.Files.Count);
        var installed = Directory.EnumerateFiles(game, "*", SearchOption.AllDirectories)
            .Count(x => !x.Contains(Path.DirectorySeparatorChar + ".pawpatch" + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase));
        Console.WriteLine($"RELEASE PASS modules={state.Modules.Count} declaredFiles={declared} gameFiles={installed}");
    }
    finally
    {
        var full = Path.GetFullPath(root);
        var safeParent = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "PawsPatchLauncherReleaseTests")) + Path.DirectorySeparatorChar;
        if (full.StartsWith(safeParent, StringComparison.OrdinalIgnoreCase) && Directory.Exists(full)) Directory.Delete(full, true);
    }
}

static async Task VerifyTransitionAsync(string betaFeedPath, string stableFeedPath, string publicKeyPath)
{
    var root = Path.Combine(Path.GetTempPath(), "PawsPatchLauncherTransitionTests", Guid.NewGuid().ToString("N"));
    var game = Path.Combine(root, "Kohan II");
    var cache = Path.Combine(root, "cache");
    Directory.CreateDirectory(game);
    try
    {
        await File.WriteAllTextAsync(Path.Combine(game, "k2.exe"), "test sentinel; never distributed");
        var configuration = new LauncherConfiguration
        {
            FeedUrls = [Path.GetFullPath(stableFeedPath)],
            BetaFeedUrls = [Path.GetFullPath(betaFeedPath)],
            PublicKeyPem = await File.ReadAllTextAsync(Path.GetFullPath(publicKeyPath)),
            RequireSignedRemoteFeed = true,
            CacheRoot = cache
        };
        var client = new FeedClient(configuration);
        var installer = new ModuleInstaller(game);

        async Task ApplyAsync(string channelName)
        {
            var channel = await client.GetChannelAsync(channelName) ?? throw new Exception($"{channelName} feed was not loaded.");
            var modules = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase);
            foreach (var package in channel.Packages.OrderBy(x => x.Priority))
            {
                var archive = await client.DownloadVerifiedAsync(package, null);
                modules[package.Id] = await installer.PrepareAsync(package, archive);
            }
            await installer.ReconcileAsync(modules);
            var errors = await installer.VerifyAsync();
            if (errors.Count != 0) throw new Exception($"{channelName} verification failed: " + string.Join("; ", errors.Take(10)));
        }

        var colorFiles = new[]
        {
            "k2_paws_lobby_colors_mp_1372_experimental.exe",
            "paws_player_colors.ini",
            Path.Combine("Data", "UI", "Menus", "pcolors.tgi")
        };
        await ApplyAsync("beta");
        foreach (var relative in colorFiles) AssertTrue(File.Exists(Path.Combine(game, relative)), $"Beta color file is missing: {relative}");
        await ApplyAsync("stable");
        foreach (var relative in colorFiles) AssertTrue(!File.Exists(Path.Combine(game, relative)), $"Stable rollback left a beta color file: {relative}");
        Console.WriteLine("TRANSITION PASS beta->stable removed 3 beta color files");
    }
    finally
    {
        var full = Path.GetFullPath(root);
        var safeParent = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "PawsPatchLauncherTransitionTests")) + Path.DirectorySeparatorChar;
        if (full.StartsWith(safeParent, StringComparison.OrdinalIgnoreCase) && Directory.Exists(full)) Directory.Delete(full, true);
    }
}

static async Task VerifyGameplayProfilesAsync(string feedPath, string publicKeyPath)
{
    var root = Path.Combine(Path.GetTempPath(), "PawsPatchLauncherProfileTests", Guid.NewGuid().ToString("N"));
    var game = Path.Combine(root, "Kohan II");
    Directory.CreateDirectory(game);
    try
    {
        await File.WriteAllTextAsync(Path.Combine(game, "k2.exe"), "test sentinel; never distributed");
        var configuration = new LauncherConfiguration
        {
            FeedUrls = [Path.GetFullPath(feedPath)],
            PublicKeyPem = await File.ReadAllTextAsync(Path.GetFullPath(publicKeyPath)),
            RequireSignedRemoteFeed = true,
            CacheRoot = Path.Combine(root, "cache")
        };
        var client = new FeedClient(configuration);
        var channel = await client.GetChannelAsync("stable") ?? throw new Exception("Profile feed was not loaded.");
        var installer = new ModuleInstaller(game);
        var prepared = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase);
        foreach (var package in channel.Packages.Where(package =>
                     package.Required
                     || package.Id.StartsWith("roaming-profile-", StringComparison.OrdinalIgnoreCase)
                     || package.Id is "siege-balance-standard" or "large-map-sizes-standard"))
        {
            var archive = await client.DownloadVerifiedAsync(package, null);
            prepared[package.Id] = await installer.PrepareAsync(package, archive);
        }

        var required = channel.Packages.Where(package => package.Required).Select(package => package.Id).ToArray();
        var profiles = new[]
        {
            new[] { "default-x4-with-new" },
            new[] { "standard-with-new", "roaming-profile-standard-with-new", "siege-balance-standard", "large-map-sizes-standard" },
            new[] { "x4-no-new", "roaming-profile-x4-no-new" },
            new[] { "standard-no-new", "roaming-profile-standard-no-new", "siege-balance-standard", "large-map-sizes-standard" }
        };
        foreach (var profile in profiles)
        {
            var selected = required.Concat(profile.Skip(1)).ToHashSet(StringComparer.OrdinalIgnoreCase);
            var desired = prepared.Where(pair => selected.Contains(pair.Key))
                .ToDictionary(pair => pair.Key, pair => pair.Value, StringComparer.OrdinalIgnoreCase);
            await installer.ReconcileAsync(desired);
            var errors = await installer.VerifyAsync();
            if (errors.Count != 0) throw new Exception($"Profile {profile[0]} failed: " + string.Join("; ", errors.Take(10)));
            Console.WriteLine($"PROFILE PASS {profile[0]} modules={desired.Count}");
        }
    }
    finally
    {
        var full = Path.GetFullPath(root);
        var safeParent = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "PawsPatchLauncherProfileTests")) + Path.DirectorySeparatorChar;
        if (full.StartsWith(safeParent, StringComparison.OrdinalIgnoreCase) && Directory.Exists(full)) Directory.Delete(full, true);
    }
}

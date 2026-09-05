using PawsPatchLauncher;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

if (args.Length == 3 && args[0] == "--verify-release")
{
    await VerifyReleaseAsync(args[1], args[2]);
    return;
}

var root = Path.Combine(Path.GetTempPath(), "PawsPatchLauncherTests", Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
var passed = 0;

try
{
    ExpectThrows<InvalidDataException>(() => CryptoAndIO.SafeChildPath(root, "..\\escape.txt"));
    passed++;

    var game = Path.Combine(root, "game");
    Directory.CreateDirectory(game);
    await File.WriteAllTextAsync(Path.Combine(game, "shared.txt"), "original");

    var basePackage = await CreatePackageAsync(root, "arcane-wars", "1.0.0", 0,
        new Dictionary<string, string> { ["shared.txt"] = "arcane", ["base-only.txt"] = "base" });
    var patchPackage = await CreatePackageAsync(root, "pawpatch-core", "2.0.0", 100,
        new Dictionary<string, string> { ["shared.txt"] = "patched", ["patch-only.txt"] = "patch" });

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

    Console.WriteLine($"PASS {passed}");
}
finally
{
    try { Directory.Delete(root, true); } catch { }
}

static async Task<(PackageRelease Release, string Archive)> CreatePackageAsync(string root, string id, string version, int priority,
    Dictionary<string, string> files)
{
    var source = Path.Combine(root, "source-" + id);
    var payload = Path.Combine(source, "payload");
    Directory.CreateDirectory(payload);
    var manifest = new ModuleArchiveManifest { Id = id, Version = version };
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

static async Task VerifyReleaseAsync(string feedPath, string publicKeyPath)
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
        var channel = await client.GetChannelAsync() ?? throw new Exception("Release feed was not loaded.");
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

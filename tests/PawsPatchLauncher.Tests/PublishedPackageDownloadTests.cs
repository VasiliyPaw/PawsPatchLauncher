using System.Text.Json;
using PawsPatchLauncher;

internal static class PublishedPackageDownloadTests
{
    internal static async Task RunAsync(string source, string cache, string version, string? oldArchive)
    {
        cache = Path.GetFullPath(cache);
        if (Directory.Exists(cache)) throw new IOException("Use a new isolated download cache.");
        Directory.CreateDirectory(cache);
        var config = JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "launcher.config.json")),
            LauncherJsonContext.Default.LauncherConfiguration)!;
        config.CacheRoot = cache;
        config.BetaFeedUrls = [source];
        var client = new FeedClient(config);
        var manifest = await client.GetChannelAsync("beta") ?? throw new Exception("Missing beta catalog.");
        var packages = manifest.Packages.Where(p => p.Mods.SequenceEqual(new[] { GameMod.ArcaneWars }) && p.Version == version).ToArray();
        if (packages.Length < 10 || !new[] { "pawpatch-core", "common-ui", "player-colors", "desync-continue" }
            .All(id => packages.Any(p => p.Id == id))) throw new Exception("Expected the complete Arcane patch package set.");
        if (oldArchive is not null)
        {
            var core = packages.Single(p => p.Id == "pawpatch-core");
            var part = Path.Combine(cache, "downloads", core.Id, core.Version, core.Sha256.ToUpperInvariant() + ".zip.download");
            Directory.CreateDirectory(Path.GetDirectoryName(part)!);
            File.Copy(oldArchive, part);
        }
        var results = new List<object>();
        foreach (var package in packages)
        {
            var path = await client.DownloadVerifiedAsync(package, null);
            var hash = await CryptoAndIO.Sha256Async(path);
            if (hash != package.Sha256.ToUpperInvariant() || new FileInfo(path).Length != package.Size)
                throw new Exception("Wrong downloaded bytes: " + package.Id);
            results.Add(new { package.Id, package.Version, package.Size, Sha256 = hash, package.Urls });
            Console.WriteLine("NATIVE_DOWNLOAD_PASS " + package.Id + " " + package.Version);
        }
        await File.WriteAllTextAsync(Path.Combine(cache, "acceptance.json"), JsonSerializer.Serialize(new
        { accepted = true, packages = results, oldIncorrectPartialSeeded = oldArchive is not null }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("NATIVE_DOWNLOAD_TOTAL_PASS " + packages.Length);
    }
}

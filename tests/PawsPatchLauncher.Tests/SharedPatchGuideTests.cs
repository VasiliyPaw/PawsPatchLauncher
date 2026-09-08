using System.Text.Json;
using PawsPatchLauncher;

public static class SharedPatchGuideTests
{
    public static async Task RunAsync(string repository, string staging)
    {
        var repo = Path.GetFullPath(repository);
        var output = Path.GetFullPath(staging);
        var config = new LauncherConfiguration {
            FeedUrls = [Path.Combine(output, "stable.signed.json")],
            BetaFeedUrls = [Path.Combine(output, "beta.signed.json")],
            PublicKeyPem = await File.ReadAllTextAsync(Path.Combine(repo, ".local/signing/pawpatch-signing-public.pem")),
            CacheRoot = Path.Combine(output, "guide-test-cache")
        };
        var previous = new FeedClient(new LauncherConfiguration {
            FeedUrls = [Path.Combine(output, "stable.before.signed.json")],
            BetaFeedUrls = [Path.Combine(output, "beta.before.signed.json")],
            PublicKeyPem = config.PublicKeyPem, CacheRoot = Path.Combine(output, "guide-before-cache")
        });
        var client = new FeedClient(config);
        var documents = new List<PatchGuideDocument>();
        var checks = 0;
        void Check(bool valid, string message) { if (!valid) throw new Exception(message); checks++; }
        string Json<T>(T value) => JsonSerializer.Serialize(value);
        foreach (var channel in new[] { "stable", "beta" })
        {
            var old = await previous.GetChannelAsync(channel) ?? throw new Exception("Missing original channel.");
            var current = await client.GetChannelAsync(channel) ?? throw new Exception("Missing current channel.");
            Check(Json(current.Packages) == Json(old.Packages), "Guide update changed game packages.");
            Check(Json(current.Game) == Json(old.Game) && Json(current.Launcher) == Json(old.Launcher), "Guide update changed game/launcher release.");
            Check(ChannelFingerprint.Create(current) == ChannelFingerprint.Create(old), "Guide-only update changed installed release identity.");
            Check(PatchGuide.IsValid(current.PatchGuide), "Shared guide rejected by launcher.");
            var guide = PatchGuide.Resolve(current);
            Check(guide.Entries.Single(e => e.Id == "city-assistant").Category == "beta", "Beta-only features leaked into Always included.");
            documents.Add(guide);
            var restarted = new FeedClient(config);
            Check(Json(PatchGuide.Resolve(restarted.CachedGuideChannel(channel, null))) == Json(guide), "Shared guide lost on offline restart.");
            Check(Json(PatchGuide.Resolve(restarted.CachedGuideChannel(channel, ChannelFingerprint.Create(old)))) == Json(guide), "Existing installed release lost refreshed documentation.");
        }
        Check(Json(documents[0]) == Json(documents[1]), "Current channel guides differ.");
        foreach (var language in new[] { "ru", "en" })
        foreach (var category in new[] { "always", "optional", "beta" })
        {
            string Text(PatchGuideDocument guide) => string.Join("\n", guide.Entries.Where(e => e.Category == category)
                .Select(e => e.Title(language) + "\n" + e.Body(language)));
            Check(Text(documents[0]) == Text(documents[1]), "Visible guide text depends on selected channel.");
        }
        Console.WriteLine($"SHARED GUIDE PASS {checks}: signed Release/Beta, RU/EN categories, offline restart, unchanged packages and installed identity.");
    }
}

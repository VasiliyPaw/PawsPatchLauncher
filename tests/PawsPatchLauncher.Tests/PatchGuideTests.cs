using System.Security.Cryptography;
using System.Text.Json;
using PawsPatchLauncher;

public static class PatchGuideTests
{
    public static async Task<int> RunAsync(string root)
    {
        int checks = 0;
        void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var path = Path.Combine(root, "guide-feed.json");
        var config = new LauncherConfiguration { BetaFeedUrls = [path], PublicKeyPem = key.ExportSubjectPublicKeyInfoPem(),
            CacheRoot = Path.Combine(root, "guide-cache") };
        var feed = new ChannelManifest { Channel = "beta", ColorDesyncContinue = true, PublishedAt = "2026-09-07",
            PatchGuide = PatchGuide.Current(), Packages = [new() { Id = "player-colors", Sha256 = "A" }] };
        async Task Write()
        {
            var payload = JsonSerializer.SerializeToUtf8Bytes(feed, LauncherJsonContext.Default.ChannelManifest);
            var signed = new SignedFeedEnvelope { Payload = Convert.ToBase64String(payload),
                Signature = Convert.ToBase64String(key.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation)) };
            await File.WriteAllTextAsync(path, JsonSerializer.Serialize(signed, LauncherJsonContext.Default.SignedFeedEnvelope));
        }
        Check(PatchGuide.IsValid(PatchGuide.Current()), "Built-in current guide invalid.");
        Check(PatchGuide.Resolve(new ChannelManifest()).Entries.Count == 13, "Old feed borrowed new Beta features.");
        var code = ConfigurationCode.Create(new UserSettings { Channel = "beta", CustomPlayerColors = true, DesyncMode = "continue" });
        Check(ConfigurationCode.Parse(code) is { CustomPlayerColors: true, DesyncMode: "continue" }, "Combined friend-code roundtrip failed.");
        Check(GameExecutableSelector.SupportsColorDesyncContinue(feed), "New feed capability ignored.");
        Check(!GameExecutableSelector.SupportsColorDesyncContinue(new ChannelManifest { Channel = "beta" }), "Old feed enabled missing helper.");
        await Write();
        var client = new FeedClient(config);
        var first = await client.GetChannelAsync("beta") ?? throw new Exception("No signed feed.");
        var firstId = ChannelFingerprint.Create(first);
        Check(PatchGuide.Resolve(first).Entries.Count == PatchGuide.Current().Entries.Count, "Signed guide not deserialized.");
        Check(first.ColorDesyncContinue, "Capability not deserialized.");
        var initialTitle = first.PatchGuide!.Entries[0].TitleRu;
        feed.PatchGuide!.Entries[0] = feed.PatchGuide.Entries[0] with { TitleRu = "Обновлённое описание без нового EXE" };
        await Write();
        var refreshed = await client.GetChannelAsync("beta") ?? throw new Exception();
        Check(PatchGuide.Resolve(refreshed).Entries[0].TitleRu != initialTitle, "Guide did not refresh.");
        Check(ChannelFingerprint.Create(refreshed) == firstId, "Documentation triggered a game update.");
        File.Delete(path); // Only the unique test fixture, to simulate offline startup.
        var restarted = new FeedClient(config);
        Check(restarted.CachedGuideChannel("beta", null)?.PatchGuide?.Entries[0].TitleRu == feed.PatchGuide.Entries[0].TitleRu,
            "Restarted offline reader lost latest signed guide.");
        Check(restarted.CachedGuideChannel("stable", null) is null, "Beta documentation leaked into another channel.");
        Check(restarted.CachedGuideChannel("beta", firstId)?.PatchGuide?.Entries[0].TitleRu == feed.PatchGuide.Entries[0].TitleRu,
            "Pinned guide did not load its own release.");
        feed.Packages[0].Sha256 = "B"; feed.PublishedAt = "2026-09-08";
        feed.PatchGuide.Entries[0] = feed.PatchGuide.Entries[0] with { TitleRu = "Другая версия патча" };
        await Write(); await restarted.GetChannelAsync("beta");
        Check(restarted.CachedGuideChannel("beta", firstId)?.PatchGuide?.Entries[0].TitleRu != "Другая версия патча",
            "Pinned old release borrowed newer guide.");
        var invalid = new PatchGuideDocument { Version = "1", Entries = [new("../bad", "always", "a", "a", "b", "b")] };
        Check(!PatchGuide.IsValid(invalid), "Unsafe UI identifier accepted.");
        invalid.Entries = [new("ok", "unknown", "a", "a", "b", "b")];
        Check(!PatchGuide.IsValid(invalid), "Unknown category accepted.");
        invalid.Entries = [new("ok", "always", "a", "a", "b", "b"), new("ok", "always", "a", "a", "b", "b")];
        Check(!PatchGuide.IsValid(invalid), "Duplicate guide IDs accepted.");
        invalid.Entries = [new("ok", "always", "a", "a", new string('x', 12001), "b")];
        Check(!PatchGuide.IsValid(invalid), "Unbounded guide accepted.");
        Check(PatchGuide.Resolve(new() { PatchGuide = invalid }).Entries.Count == 13, "Malformed guide broke fallback.");
        var archive = Path.Combine(config.CacheRoot, "releases", firstId + ".json");
        var envelope = JsonSerializer.Deserialize(await File.ReadAllTextAsync(archive), LauncherJsonContext.Default.SignedFeedEnvelope)!;
        var tampered = Convert.FromBase64String(envelope.Payload); tampered[^2] ^= 1;
        envelope.Payload = Convert.ToBase64String(tampered);
        await File.WriteAllTextAsync(archive, JsonSerializer.Serialize(envelope, LauncherJsonContext.Default.SignedFeedEnvelope));
        Check(restarted.CachedGuideChannel("beta", firstId) is null, "Tampered cached guide accepted.");
        Console.WriteLine($"SIGNED GUIDE PASS {checks}: refresh, offline restart, pinned release, validation, tamper rejection, combined colors code");
        return checks;
    }
}

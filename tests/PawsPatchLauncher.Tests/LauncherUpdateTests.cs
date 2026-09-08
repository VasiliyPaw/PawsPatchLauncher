using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using PawsPatchLauncher;

public static class LauncherUpdateTests
{
    public static async Task<int> RunAsync(string root)
    {
        var checks = 0;
        void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        byte[] Signed(string channel, string version, bool tamper = false, string? hash = null)
        {
            var manifest = new ChannelManifest { Channel = channel, Launcher = Release(version, hash) };
            var payload = JsonSerializer.SerializeToUtf8Bytes(manifest, LauncherJsonContext.Default.ChannelManifest);
            var signature = key.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
            if (tamper) signature[0] ^= 1;
            return JsonSerializer.SerializeToUtf8Bytes(new SignedFeedEnvelope { Payload = Convert.ToBase64String(payload), Signature = Convert.ToBase64String(signature) },
                LauncherJsonContext.Default.SignedFeedEnvelope);
        }
        const string stable = "https://updates.invalid/stable.json";
        const string beta = "https://updates.invalid/beta.json";
        const string mirror = "https://mirror.invalid/stable.json?preserve=signature";
        var bytes = new Dictionary<string, byte[]> { [stable] = Signed("stable", "9.2.0"), [beta] = Signed("beta", "9.1.0") };
        var slow = new HashSet<string>();
        var requests = new List<string>();
        using var handler = new Handler(async (request, token) => {
            var url = request.RequestUri!.AbsoluteUri;
            Check(request.Headers.CacheControl is { NoCache: true, MaxAge: var age } && age == TimeSpan.Zero,
                "Manifest request does not ask caches to revalidate.");
            requests.Add(url);
            if (slow.Contains(url)) await Task.Delay(Timeout.Infinite, token);
            return bytes.TryGetValue(url, out var body)
                ? new(HttpStatusCode.OK) { Content = new ByteArrayContent(body) }
                : new(HttpStatusCode.NotFound);
        });
        using var http = new HttpClient(handler);
        var config = new LauncherConfiguration { FeedUrls = [stable], BetaFeedUrls = [beta],
            PublicKeyPem = key.ExportSubjectPublicKeyInfoPem(), CacheRoot = Path.Combine(root, "launcher-only-check") };
        var client = new FeedClient(config, http);
        Check((await client.GetLauncherUpdateAsync())?.Version == "9.2.0", "New Release hidden by old Beta.");
        bytes[beta] = Signed("beta", "9.3.0");
        Check((await client.GetLauncherUpdateAsync())?.Version == "9.3.0", "New Beta hidden by old Release.");
        bytes.Remove(stable);
        Check((await client.GetLauncherUpdateAsync())?.Version == "9.3.0", "404 on one source hid the other.");
        bytes[stable] = Signed("stable", "99.0.0", tamper: true);
        Check((await client.GetLauncherUpdateAsync())?.Version == "9.3.0", "Unsigned/tampered higher version won.");
        bytes[stable] = Signed("beta", "99.0.0");
        Check((await client.GetLauncherUpdateAsync())?.Version == "9.3.0", "Wrong-channel source won.");
        bytes[stable] = Signed("stable", "99.0.0", hash: "bad hash");
        Check((await client.GetLauncherUpdateAsync())?.Version == "9.3.0", "Malformed high version won.");
        bytes[stable] = Signed("stable", "9.1.0"); bytes[mirror] = Signed("stable", "9.4.0");
        config.FeedUrls.Add(mirror);
        Check((await client.GetLauncherUpdateAsync())?.Version == "9.4.0", "First stale mirror shadowed newer mirror.");
        Check(requests.Contains(mirror), "Feed URL/query was rewritten.");
        config.FeedUrls.Remove(mirror);
        slow.Add(stable);
        using (var timeout = new CancellationTokenSource(TimeSpan.FromMilliseconds(50)))
            Check((await client.GetLauncherUpdateAsync(timeout.Token))?.Version == "9.3.0", "Timed-out peer source hid healthy source.");
        slow.Add(beta);
        using (var timeout = new CancellationTokenSource(TimeSpan.FromMilliseconds(50)))
        {
            try { await client.GetLauncherUpdateAsync(timeout.Token); throw new Exception("Expected cancellation."); }
            catch (OperationCanceledException) { checks++; }
        }
        slow.Clear(); bytes.Remove(stable); bytes.Remove(beta);
        try { await client.GetLauncherUpdateAsync(); throw new Exception("Expected all-source failure."); }
        catch (AggregateException error) { Check(error.InnerExceptions.Count == 2, "Lost source failures."); }
        Check(!Directory.Exists(config.CacheRoot), "Launcher check wrote patch archives or installed data.");
        config.FeedUrls.Clear(); bytes[beta] = Signed("beta", "9.5.0");
        Check((await client.GetLauncherUpdateAsync())?.Version == "9.5.0", "Beta-only configuration failed.");
        config.BetaFeedUrls.Clear();
        Check(await client.GetLauncherUpdateAsync() is null, "Empty configuration invents a release.");

        var state = new LauncherUpdateState();
        var original = Release("9.5.0"); state.Observe(original);
        original.Version = "99.0.0"; original.Urls.Clear();
        Check(state.Latest?.Version == "9.5.0" && state.Latest.Urls.Count == 1, "Stored result aliases mutable feed.");
        foreach (var stale in new LauncherRelease?[] { Release("9.4.0"), null, new(), Release("invalid"), Release("99.0.0", "bad") })
        { state.Observe(stale); Check(state.Latest?.Version == "9.5.0", "Stale/failed check removed update."); }
        state.Observe(Release("9.5.0", new string('B', 64)));
        Check(state.Latest!.Sha256 == new string('A', 64), "Same-version asset was silently replaced.");
        state.Observe(Release("9.6.0"));
        Check(state.Latest!.Version == "9.6.0", "Newer update did not supersede previous.");
        Console.WriteLine($"GLOBAL LAUNCHER UPDATE PASS {checks}: signed channels/mirrors, stale data, failures, timeout, invalid metadata, no patch writes, retained update and cache revalidation");
        return checks;
    }

    private static LauncherRelease Release(string version, string? hash = null) => new() {
        Version = version, Size = 123, Sha256 = hash ?? new string('A', 64), Urls = ["https://updates.invalid/launcher.exe"] };

    private sealed class Handler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
            => send(request, cancellationToken);
    }
}

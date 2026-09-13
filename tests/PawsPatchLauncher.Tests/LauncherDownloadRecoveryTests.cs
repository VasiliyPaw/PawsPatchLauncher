using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using PawsPatchLauncher;

internal static class LauncherDownloadRecoveryTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var data = Enumerable.Range(0, 240000).Select(i => (byte)(i % 251)).ToArray();
        var release = new LauncherRelease { Version = "99.0.0", Size = data.Length,
            Sha256 = Convert.ToHexString(SHA256.HashData(data)), Urls = ["https://fixture.invalid/update.exe"] };
        var n = 0; void Check(bool ok, string why) { if (!ok) throw new Exception("Launcher download: " + why); n++; }
        foreach (var mode in new[] { "resume", "ignore-range", "disconnect", "corrupt" })
        {
            var cache = Path.Combine(root, "launcher-transfer-" + mode);
            var calls = 0; long requestedOffset = 0;
            using var http = new HttpClient(new Handler(request =>
            {
                calls++;
                var offset = request.Headers.Range?.Ranges.Single().From ?? 0;
                requestedOffset = Math.Max(requestedOffset, offset);
                if (mode == "disconnect" && calls == 1)
                    return new(HttpStatusCode.OK) { Content = new StreamContent(new DisconnectingStream(data)) };
                var append = offset > 0 && mode != "ignore-range";
                var bytes = (mode == "corrupt" ? data.Select(b => (byte)(b ^ 1)).ToArray() : data)[(append ? (int)offset : 0)..];
                var response = new HttpResponseMessage(append ? HttpStatusCode.PartialContent : HttpStatusCode.OK) { Content = new ByteArrayContent(bytes) };
                if (append) response.Content.Headers.ContentRange = new ContentRangeHeaderValue(offset, data.Length - 1, data.Length);
                return response;
            }));
            var feed = new FeedClient(new LauncherConfiguration { CacheRoot = cache, FeedUrls = [], BetaFeedUrls = [] }, http);
            var destination = Path.Combine(cache, "launcher", $"PawsPatchLauncher-{release.Version}-{release.Sha256}.exe");
            if (mode is "resume" or "ignore-range")
            {
                using var cancel = new CancellationTokenSource();
                var cancelled = false;
                try { await feed.DownloadLauncherAsync(release, new ImmediateProgress(p => { if (p.Received > 0) cancel.Cancel(); }), cancel.Token); }
                catch (OperationCanceledException) { cancelled = true; }
                Check(cancelled && !File.Exists(destination), "Cancellation accepted a partial executable.");
                Check(new FileInfo(destination + ".download").Length is > 0 and < 240000, "Cancellation lost partial bytes.");
            }
            if (mode == "corrupt")
            {
                var rejected = false;
                try { await feed.DownloadLauncherAsync(release, null); }
                catch (AggregateException error) { rejected = error.InnerExceptions.All(e => e is InvalidDataException); }
                Check(rejected && !File.Exists(destination) && !File.Exists(destination + ".download"), "Hash mismatch accepted an executable or retained corrupt bytes.");
                continue;
            }
            var downloaded = await feed.DownloadLauncherAsync(release, null);
            Check(downloaded == destination && (await File.ReadAllBytesAsync(downloaded)).SequenceEqual(data), "Recovery produced the wrong launcher bytes.");
            Check(requestedOffset > 0 && calls == 2, "Download did not reuse the interrupted transfer.");
            var oldCalls = calls; await feed.DownloadLauncherAsync(release, null);
            Check(calls == oldCalls, "Verified cached launcher was downloaded again.");
        }
        Console.WriteLine($"LAUNCHER DOWNLOAD RECOVERY PASS {n}: mid-transfer cancel, dropped stream, Range resume, Range ignored, SHA-256 rejection and verified cache.");
        return n;
    }
    private sealed class ImmediateProgress(Action<(long Received, long? Total)> report) : IProgress<(long Received, long? Total)>
    { public void Report((long Received, long? Total) value) => report(value); }
    private sealed class Handler(Func<HttpRequestMessage, HttpResponseMessage> reply) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        { ct.ThrowIfCancellationRequested(); return Task.FromResult(reply(request)); }
    }
    private sealed class DisconnectingStream(byte[] bytes) : MemoryStream(bytes, false)
    {
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken ct = default)
            => Position > 0 ? ValueTask.FromException<int>(new IOException("Simulated connection loss after the first chunk.")) : base.ReadAsync(buffer, ct);
    }
}

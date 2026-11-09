using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using PawsPatchLauncher;

internal static class UsabilityTests
{
    internal static async Task<int> RunAsync(string root)
    {
        int checks = 0; void Check(bool ok, string why) { if (!ok) throw new Exception("Usability: " + why); checks++; }
        var bytes = Enumerable.Range(0, 262144).Select(i => (byte)(i % 251)).ToArray();
        var controller = new DownloadControl(); controller.Pause();
        long offset = 0; int requests = 0;
        using var http = new HttpClient(new Handler(request =>
        {
            requests++; offset = request.Headers.Range?.Ranges.Single().From ?? 0;
            var response = new HttpResponseMessage(offset > 0 ? HttpStatusCode.PartialContent : HttpStatusCode.OK) { Content = new ByteArrayContent(bytes[(int)offset..]) };
            if (offset > 0) response.Content.Headers.ContentRange = new ContentRangeHeaderValue(offset, bytes.Length - 1, bytes.Length);
            return response;
        }));
        var path = Path.Combine(root, "controlled-download.part");
        var reached = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        long received = 0;
        using var cancel = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var downloading = ResumableDownload.DownloadAsync(http, "https://fixture.invalid/file", path, bytes.Length,
            new ImmediateProgress(p => { received = p.Received; if (p.Received > 0) { controller.Pause(); reached.TrySetResult(true); } }), cancel.Token, controller);
        await Task.Delay(50); Check(requests == 0 && !downloading.IsCompleted, "initial pause sends no network request");
        controller.Resume(); await reached.Task.WaitAsync(TimeSpan.FromSeconds(3));
        var atPause = received; await Task.Delay(100);
        Check(received == atPause && !downloading.IsCompleted, "pause stops progress without completing or discarding transfer");
        cancel.Cancel(); var wasCancelled = false;
        try { await downloading; } catch (OperationCanceledException) { wasCancelled = true; }
        Check(wasCancelled && new FileInfo(path).Length is > 0 and < 262144, "cancellation while paused preserves complete written chunks");
        await ResumableDownload.DownloadAsync(http, "https://fixture.invalid/file", path, bytes.Length, null, CancellationToken.None, new DownloadControl());
        Check(offset == atPause && (await File.ReadAllBytesAsync(path)).SequenceEqual(bytes), "fresh transport resumes persisted bytes with Range and identical result");
        var limited = new DownloadControl { LimitKiB = 256 }; var watch = Stopwatch.StartNew();
        await ResumableDownload.DownloadAsync(http, "https://fixture.invalid/file", Path.Combine(root, "limited.part"), bytes.Length, null, CancellationToken.None, limited);
        Check(watch.Elapsed >= TimeSpan.FromMilliseconds(850), "speed cap paces actual file bytes");
        limited.Pause(); using var waitCancel = new CancellationTokenSource(); var gate = limited.WaitAsync(waitCancel.Token); waitCancel.Cancel();
        try { await gate; } catch (OperationCanceledException) { }
        Check(gate.IsCanceled, "a paused waiter can always be cancelled");
        var feed = new FeedClient(new LauncherConfiguration { CacheRoot = Path.Combine(root, "managed-cache"), FeedUrls = [], BetaFeedUrls = [] }, http);
        var package = new PackageRelease { Id = "fixture", Version = "1", Size = bytes.Length, Sha256 = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)), Urls = ["https://fixture.invalid/file"] };
        var cached = await feed.DownloadVerifiedAsync(package, null); var beforeCache = requests;
        feed.Downloads.Pause(); var cachedWait = feed.DownloadVerifiedAsync(package, null); await Task.Delay(70);
        Check(!cachedWait.IsCompleted, "pause also gates verified cache returns before installation can proceed");
        feed.Downloads.Resume(); Check(await cachedWait == cached && requests == beforeCache, "resuming a verified package does not download it again");
        var storeRoot = Path.Combine(root, "pending-profile"); var pendingStore = new PendingInstallationStore(storeRoot);
        var selection = new UserSettings { Channel = "stable", OnlineDirectorySeen = true, DownloadLimitKiB = 1024 };
        var pending = new PendingInstallation(Path.GetFullPath(Path.Combine(root, "game")), ConfigurationCode.Create(selection), "stable", new string('A', 64), DateTimeOffset.UtcNow);
        pendingStore.Save(pending); Check(new PendingInstallationStore(storeRoot).Load() == pending, "unfinished operation survives a new store instance without inventing a version pin");
        File.WriteAllText(Path.Combine(storeRoot, "pending-installation.json"), "{broken"); Check(pendingStore.Load() is null, "damaged pending state is ignored");
        pendingStore.Save(pending with { Configuration = "invalid" }); Check(pendingStore.Load() is null, "invalid configuration cannot be resumed");
        pendingStore.Clear(); Check(pendingStore.Load() is null, "dismissal clears only pending intent");
        var settingsCopy = JsonSerializer.Deserialize<UserSettings>(JsonSerializer.Serialize(selection))!;
        Check(settingsCopy.DownloadLimitKiB == 1024 && settingsCopy.OnlineDirectorySeen, "speed preference preserves permanent discovery flag");
        var peer = ConfigurationCode.Parse(FriendConfiguration.Create(selection)); peer.RussianLocalization = !selection.RussianLocalization; peer.GameVoiceLanguage = "ru";
        Check(FriendConfiguration.Matches(selection, peer), "personal text and speech languages do not create gameplay mismatches");
        peer.RoamingSpawnMode = "x2"; peer.IgnoreZeroMorale = !selection.IgnoreZeroMorale;
        Check(!FriendConfiguration.Matches(selection, peer), "only differing gameplay settings are shown");
        foreach (var language in new[] { "uk", "cs", "de", "fr" })
            Check(ConfigurationChanges.Compare(selection, peer, language).All(c => c.Name != "Ignore zero morale"), "inherited comparison labels are localized in " + language);
        Check(FriendlyErrors.Describe(new DirectoryNotFoundException()).Code == "missing-path", "missing folder has a concrete recovery action");
        Check(FriendlyErrors.Describe(new HttpRequestException("503", null, HttpStatusCode.ServiceUnavailable)).Code == "server-unavailable", "server outage is distinguished from local internet failure");
        var context = new ManualContext(); var previous = SynchronizationContext.Current; SynchronizationContext.SetSynchronizationContext(context);
        int callbacks = 0, latest = 0;
        var progress = new CoalescingProgress<int>(x => { callbacks++; latest = x; }, TimeSpan.FromMilliseconds(120));
        SynchronizationContext.SetSynchronizationContext(previous);
        for (int i = 0; i < 10000; i++) progress.Report(i); context.Drain();
        Check(callbacks == 1 && latest == 9999, "ten thousand chunks share one UI callback");
        for (int i = 10000; i < 20000; i++) progress.Report(i);
        context.Drain(); Check(callbacks == 1, "progress cannot flood the dispatcher before its minimum interval");
        await Task.Delay(180); context.Drain(); Check(callbacks == 2 && latest == 19999, "throttled dispatcher retains the final sample");
        var accountId = Guid.NewGuid(); var privacy = new ProfileVisibility(); bool malformed = false;
        using var account = new AccountService(new AccountSessionStore(Path.Combine(root, "privacy-account")), new AsyncHandler(async request =>
        {
            object response;
            var route = request.RequestUri!.AbsolutePath;
            if (route.EndsWith("/token")) response = new { access_token = "fixture", refresh_token = "fixture-refresh", expires_in = 3600, user = new { id = accountId, email = "fixture@example.invalid" } };
            else if (route.EndsWith("/paw_launcher_session")) response = new { status = "ok" };
            else if (route.EndsWith("/paw_profiles")) response = new[] { new { id = accountId, nickname = "fixture" } };
            else if (route.EndsWith("/paw_profile_visibility"))
            {
                using var body = JsonDocument.Parse(await request.Content!.ReadAsStringAsync());
                if (body.RootElement.GetProperty("configuration_visibility").GetString() is { } setting)
                    privacy = new(setting, body.RootElement.GetProperty("activity_visibility").GetString()!);
                response = new { status = "ok", configuration_visibility = malformed ? "invalid" : privacy.Configuration, activity_visibility = privacy.Activity };
            }
            else if (route.EndsWith("/paw_profile_card")) response = new { status = "ok", player = new { id = accountId, nickname = "fixture", relation = "friend", is_friend = false, presence = "playing", channel = "stable", configuration = FriendConfiguration.Create(selection), components = new { core = true }, activity = new { phase = "match", multiplayer = false }, configuration_hidden = true, activity_hidden = true } };
            else throw new InvalidOperationException("Unexpected privacy transport route: " + route);
            return new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(JsonSerializer.Serialize(response)) };
        }));
        await account.SignInAsync("fixture@example.invalid", "fixture-password", remember: false);
        Check(await account.ReadProfileVisibilityAsync() == new ProfileVisibility(), "account privacy read accepts validated server defaults");
        Check(await account.SaveProfileVisibilityAsync(new("friends", "nobody")) == new ProfileVisibility("friends", "nobody"), "privacy transport sends both selections and validates acknowledgement");
        var hiddenCard = await account.GetPublicPlayerProfileAsync(accountId);
        Check(hiddenCard.ConfigurationHidden && hiddenCard.ActivityHidden && hiddenCard.Configuration is null && hiddenCard.Components == "{}" && hiddenCard.Activity is null && hiddenCard.Channel == "unknown", "hidden flags prevent retaining fallback settings or activity in the client model");
        malformed = true; bool rejected = false;
        try { await account.ReadProfileVisibilityAsync(); } catch (AccountException error) { rejected = error.Code == "invalid_response"; }
        Check(rejected, "invalid server privacy values cannot become a successful UI selection");
        Console.WriteLine($"USABILITY PASS {checks}: pause, cancellation, persisted Range recovery, pacing, resume intent, meaningful comparison and bounded UI dispatch");
        return checks;
    }
    private sealed class ImmediateProgress(Action<(long Received, long? Total)> action) : IProgress<(long Received, long? Total)>
    { public void Report((long Received, long? Total) value) => action(value); }
    private sealed class Handler(Func<HttpRequestMessage, HttpResponseMessage> respond) : HttpMessageHandler
    { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token) => Task.FromResult(respond(request)); }
    private sealed class AsyncHandler(Func<HttpRequestMessage, Task<HttpResponseMessage>> respond) : HttpMessageHandler
    { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token) => respond(request); }
    private sealed class ManualContext : SynchronizationContext
    {
        private readonly ConcurrentQueue<(SendOrPostCallback Callback, object? Value)> _queue = new();
        public override void Post(SendOrPostCallback callback, object? value) => _queue.Enqueue((callback, value));
        internal void Drain() { while (_queue.TryDequeue(out var work)) work.Callback(work.Value); }
    }
}

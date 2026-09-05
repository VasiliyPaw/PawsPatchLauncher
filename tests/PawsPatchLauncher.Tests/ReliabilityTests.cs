using PawsPatchLauncher;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;

public static class ReliabilityTests
{
    public static async Task<int> RunAsync(string root)
    {
        var count = 0;
        void Check(bool value, string message) { if (!value) throw new Exception(message); count++; }
        var reader = new UserSettings();
        var history = new ChannelManifest { Channel = "stable", Changelog = [
            new() { Category = "patch", Version = "1", PublishedAt = "2026-09-05" },
            new() { Category = "launcher", Version = "1", PublishedAt = "2026-09-05" }
        ] };
        Check(ChangelogReadState.IsUnread(reader, history, "patch"), "New patch history was not unread.");
        Check(!ChangelogReadState.MarkViewed(reader, history, "patch", false), "Hidden history was marked as read.");
        Check(ChangelogReadState.MarkViewed(reader, history, "patch", true), "Automatically displayed patch history was not marked as read.");
        Check(!ChangelogReadState.IsUnread(reader, history, "patch"), "Visible patch badge remained unread.");
        Check(ChangelogReadState.IsUnread(reader, history, "launcher"), "Opening patch cleared the unopened launcher badge.");
        Check(!ChangelogReadState.MarkViewed(reader, history, "patch", true), "Unchanged history caused another settings write.");
        Check(ChangelogReadState.MarkViewed(reader, history, "launcher", true), "Opening launcher history did not clear its badge.");
        history.Changelog.Add(new() { Category = "launcher", Version = "2", PublishedAt = "2026-09-05" });
        Check(ChangelogReadState.IsUnread(reader, history, "launcher"), "A later launcher release did not restore its badge.");
        var savedReader = JsonSerializer.Deserialize(JsonSerializer.Serialize(reader, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!;
        Check(!ChangelogReadState.IsUnread(savedReader, history, "patch"), "Read history was lost after saving/reloading settings.");
        history.Channel = "beta";
        Check(ChangelogReadState.IsUnread(reader, history, "patch"), "Stable and Beta patch badges shared read state.");
        Check(ChangelogReadState.MarkViewed(reader, history, "PATCH", true), "Displayed Beta history did not use its own channel.");
        Check(reader.ReadChangelogs.ContainsKey("patch:beta") && reader.ReadChangelogs.ContainsKey("patch:stable"), "Patch history overwrote another channel.");
        Check(!ChangelogReadState.MarkViewed(reader, null, "patch", true), "A missing feed was marked as read.");
        Check(!ChangelogReadState.MarkViewed(reader, new ChannelManifest(), "patch", true), "Empty history was marked as read.");
        for (var bits = 0; bits < 64; bits++)
        {
            var settings = new UserSettings { Channel = (bits & 1) > 0 ? "beta" : "stable", RussianLocalization = (bits & 2) > 0,
                IndependentHostility = (bits & 4) > 0, AdditionalRoamingCompanies = (bits & 8) > 0, SiegeBalance = (bits & 16) > 0,
                RoamingSpawnMode = (bits & 32) > 0 ? "x4" : "standard" };
            var code = ConfigurationCode.Create(settings);
            Check(ConfigurationCode.Create(ConfigurationCode.Parse(" " + code.ToLowerInvariant() + " ")) == code, "Configuration did not round trip.");
        }
        foreach (var code in new[] { "PAW-BETA", "PAW-STABLE-IW1-SP3-RM1-SG1-LM1-RU1-CL0-OOS0", "PAW-STABLE-IW1-SP4-RM1-SG1-LM1-RU1-CL1-OOS0", "PAW-BETA-IW1-SP4-RM1-SG1-LM1-RU1-CL1-OOS1", "PAW-STABLE-IW1-SP4-RM1-SG1-LM0-RU1-CL0-OOS0" })
        {
            var rejected = false; try { ConfigurationCode.Parse(code); } catch (FormatException) { rejected = true; }
            Check(rejected, "Invalid configuration was accepted: " + code);
        }
        var target = new UserSettings { Language = "en", GamePath = "existing-path", PreparedChannel = "stable" };
        ConfigurationCode.Apply(new UserSettings { Channel = "beta" }, target);
        Check(target.Language == "en" && target.GamePath == "existing-path", "Import replaced local paths/language.");

        var game = Path.Combine(root, "durable-recovery");
        Directory.CreateDirectory(game);
        await File.WriteAllTextAsync(Path.Combine(game, "changed.txt"), "old");
        await File.WriteAllTextAsync(Path.Combine(game, "deleted.txt"), "restore-me");
        var prior = new InstallState { LastSuccessfulUpdate = "prior", AppliedSettings = new UserSettings { Channel = "beta" }, ReleaseId = new string('A',64) };
        var recovery = new PatchRecovery(game);
        var snapshot = await recovery.CaptureAsync(["changed.txt", "deleted.txt", "added.txt"], prior);
        await File.WriteAllTextAsync(Path.Combine(game, "changed.txt"), "new");
        File.Delete(Path.Combine(game, "deleted.txt"));
        await File.WriteAllTextAsync(Path.Combine(game, "added.txt"), "new-file");
        Check(await new PatchRecovery(game).RecoverInterruptedAsync() == 1, "Interrupted transaction was not found.");
        Check(File.ReadAllText(Path.Combine(game, "changed.txt")) == "old" && File.ReadAllText(Path.Combine(game, "deleted.txt")) == "restore-me" && !File.Exists(Path.Combine(game, "added.txt")), "Recovery did not restore added/deleted/changed files.");
        Check(new ModuleInstaller(game).LoadState().ReleaseId == prior.ReleaseId, "Recovery lost the prior release selection.");
        snapshot = await recovery.CaptureAsync(["changed.txt", "deleted.txt", "added.txt"], prior);
        await File.WriteAllTextAsync(Path.Combine(game, "changed.txt"), "update2");
        File.Delete(Path.Combine(game, "deleted.txt"));
        await recovery.CommitAsync(snapshot.Directory, snapshot.Journal);
        Check(recovery.CanRollback, "Successful update did not keep its backup.");
        var reverted = await recovery.RollbackAsync(new InstallState { LastSuccessfulUpdate = "new" });
        Check(reverted.LastSuccessfulUpdate == "prior" && File.ReadAllText(Path.Combine(game, "deleted.txt")) == "restore-me" && !recovery.CanRollback, "Explicit rollback failed.");

        snapshot = await recovery.CaptureAsync(["changed.txt"], prior);
        await File.WriteAllTextAsync(Path.Combine(game, "changed.txt"), "current-intact");
        await recovery.CommitAsync(snapshot.Directory, snapshot.Journal);
        await File.WriteAllTextAsync(Path.Combine(snapshot.Directory, "files", "changed.txt"), "corrupted-backup");
        var failed = false;
        try { await recovery.RollbackAsync(prior); } catch (IOException) { failed = true; }
        Check(failed && File.ReadAllText(Path.Combine(game, "changed.txt")) == "current-intact", "Damaged backup changed live files.");
        Check(await recovery.RecoverInterruptedAsync() == 0, "Failed rollback left an active recovery journal.");
        var reserved = false;
        try { PatchRecovery.GamePath(game, ".pawpatch/state.json"); } catch (InvalidDataException) { reserved = true; }
        Check(reserved, "Packages can overwrite recovery metadata.");

        var bytes = Enumerable.Range(0, 12000).Select(x => (byte)(x % 251)).ToArray();
        var download = Path.Combine(root, "resume.download");
        await File.WriteAllBytesAsync(download, bytes[..3000]);
        long? seenRange = null;
        using var rangeHttp = new HttpClient(new FakeHandler(request =>
        {
            seenRange = request.Headers.Range?.Ranges.First().From;
            var response = new HttpResponseMessage(HttpStatusCode.PartialContent) { Content = new ByteArrayContent(bytes[3000..]) };
            response.Content.Headers.ContentRange = new ContentRangeHeaderValue(3000, bytes.Length - 1, bytes.Length);
            return response;
        }));
        await ResumableDownload.DownloadAsync(rangeHttp, "https://unit.test/archive", download, bytes.Length, null, default);
        Check(seenRange == 3000 && (await File.ReadAllBytesAsync(download)).SequenceEqual(bytes), "HTTP Range did not resume.");
        await File.WriteAllBytesAsync(download, bytes[..1000]);
        using var ignoreRange = new HttpClient(new FakeHandler(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = new ByteArrayContent(bytes) }));
        await ResumableDownload.DownloadAsync(ignoreRange, "https://unit.test/archive", download, bytes.Length, null, default);
        Check((await File.ReadAllBytesAsync(download)).SequenceEqual(bytes), "A server ignoring Range appended a duplicate file.");
        await File.WriteAllBytesAsync(download, bytes[..1000]);
        using var badRange = new HttpClient(new FakeHandler(_ =>
        {
            var response = new HttpResponseMessage(HttpStatusCode.PartialContent) { Content = new ByteArrayContent(bytes) };
            response.Content.Headers.ContentRange = new ContentRangeHeaderValue(0, bytes.Length-1, bytes.Length);
            return response;
        }));
        failed = false;
        try { await ResumableDownload.DownloadAsync(badRange, "https://unit.test/archive", download, bytes.Length, null, default); } catch (InvalidDataException) { failed = true; }
        Check(failed && new FileInfo(download).Length == 1000, "Incorrect Range was accepted.");
        using var cts = new CancellationTokenSource(); cts.Cancel();
        failed = false;
        try { await ResumableDownload.DownloadAsync(ignoreRange, "https://unit.test/archive", download, bytes.Length, null, cts.Token); } catch (OperationCanceledException) { failed = true; }
        Check(failed && new FileInfo(download).Length == 1000, "Cancellation discarded partial bytes.");

        var cache = Path.Combine(root, "signed-archive-test");
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var manifest = new ChannelManifest { Channel = "beta", Packages = [new PackageRelease { Id = "core", Sha256 = new string('B',64) }] };
        var payload = JsonSerializer.SerializeToUtf8Bytes(manifest, LauncherJsonContext.Default.ChannelManifest);
        var envelope = new SignedFeedEnvelope { Payload = Convert.ToBase64String(payload), Signature = Convert.ToBase64String(key.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation)) };
        var feed = Path.Combine(root, "signed-beta.json");
        await File.WriteAllTextAsync(feed, JsonSerializer.Serialize(envelope, LauncherJsonContext.Default.SignedFeedEnvelope));
        var client = new FeedClient(new LauncherConfiguration { BetaFeedUrls = [feed], PublicKeyPem = key.ExportSubjectPublicKeyInfoPem(), CacheRoot = cache });
        var loaded = await client.GetChannelAsync("beta");
        var id = ChannelFingerprint.Create(loaded!);
        Check(client.LoadArchived(id,"beta").Packages[0].Id == "core", "Signed release could not be restored offline.");
        failed = false; try { client.LoadArchived(id,"stable"); } catch (InvalidDataException) { failed = true; }
        Check(failed, "Wrong-channel archive was accepted.");
        await File.WriteAllTextAsync(Path.Combine(cache,"releases",id+".json"), JsonSerializer.Serialize(manifest, LauncherJsonContext.Default.ChannelManifest));
        failed = false; try { client.LoadArchived(id,"beta"); } catch (CryptographicException) { failed = true; }
        Check(failed, "An unsigned archived release was accepted.");

        var mpGame = Path.Combine(root,"mp-check"); Directory.CreateDirectory(mpGame);
        await File.WriteAllTextAsync(Path.Combine(mpGame,"k2.exe"),"game");
        var state = new InstallState();
        var first = await MultiplayerCheck.CreateAsync(mpGame,state,new UserSettings(),"k2.exe","1");
        var again = await MultiplayerCheck.CreateAsync(mpGame,state,new UserSettings(),"k2.exe","1");
        Check(first.Fingerprint == again.Fingerprint, "Same files produced different MP fingerprints.");
        await File.WriteAllTextAsync(Path.Combine(mpGame,"foreign.tgi"),"old mod");
        var foreign = await MultiplayerCheck.CreateAsync(mpGame,state,new UserSettings(),"k2.exe","1");
        Check(first.Fingerprint != foreign.Fingerprint, "An extra manual mod did not alter the MP fingerprint.");
        Directory.CreateDirectory(Path.Combine(mpGame,"startup"));
        await File.WriteAllTextAsync(Path.Combine(mpGame,"startup","autoexec.txt"),"broken");
        state.Modules["startup"] = new InstalledModule { Enabled = true, Files = [new ModuleFile { Path = "startup/autoexec.txt", Sha256 = "BAD" }] };
        Check((await MultiplayerCheck.CriticalAsync(mpGame,state,Path.Combine(mpGame,"k2.exe"),new GameRequirement())).Count == 1, "Quick check missed autoexec corruption.");
        return count;
    }

    private sealed class FakeHandler(Func<HttpRequestMessage,HttpResponseMessage> response) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return Task.FromResult(response(request));
        }
    }
}

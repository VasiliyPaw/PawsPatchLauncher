using System.Diagnostics;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class StartupCompatibilityTests
{
    internal static async Task<int> RunAsync(string root)
    {
        int n = 0; void Check(bool ok, string why) { n++; if (!ok) throw new Exception(why); }
        var restartToken = Guid.NewGuid().ToString("N");
        var restartProfile = Path.Combine(root, "Local test & friend's profile");
        var restart = SelfUpdater.BuildRestartStartInfo(Path.Combine(root, "Paw's launcher & test.exe"), 123, 456, restartToken, restartProfile);
        Check(!restart.UseShellExecute && restart.CreateNoWindow && restart.ArgumentList.Contains("--test-profile=" + restartProfile),
            "Manual restart lost the isolated profile or used shell interpretation.");
        Check(restart.ArgumentList.Contains("--restart-parent=123:456") && restart.ArgumentList.Contains("--restart-token=" + restartToken)
            && !restart.ArgumentList.Any(a => a.Contains("--skip-startup-update") || a.Contains("--update-health")),
            "Manual update bypassed the startup window or retained old update health arguments.");
        Check(await SelfUpdater.WaitForRestartHandoffAsync([]), "Normal startup was treated as a restart waiter.");
        bool badRestartRejected = false;
        try { await SelfUpdater.WaitForRestartHandoffAsync(["--restart-parent=0:1", "--restart-token=invalid"]); }
        catch (InvalidDataException) { badRestartRejected = true; }
        Check(badRestartRejected, "Malformed restart handoff was accepted.");
        var release = new LauncherRelease { Version = "99.0.0", Size = 123, Sha256 = new('A', 64), Urls = ["https://test.invalid/update.exe"] };
        Check(StartupUpdateCheck.OfflineBudget == TimeSpan.FromSeconds(30), "Offline startup budget must be 30 seconds");
        Check(!StartupUpdateCheck.CanOpenInstalled(TimeSpan.FromSeconds(9.99), true, true), "Manual opening appeared before 10 seconds");
        Check(StartupUpdateCheck.CanOpenInstalled(TimeSpan.FromSeconds(10), true, true), "Manual opening missing at 10 seconds");
        Check(!StartupUpdateCheck.CanOpenInstalled(TimeSpan.FromSeconds(20), false, true)
            && !StartupUpdateCheck.CanOpenInstalled(TimeSpan.FromSeconds(20), true, false), "Manual opening remains after successful connection");
        var current = await StartupUpdateCheck.RunAsync(_ => Task.FromResult<LauncherRelease?>(null));
        Check(current.Online && current.Attempts == 1 && current.Release is null, "No update must open immediately");
        int tries = 0;
        var recovered = await StartupUpdateCheck.RunAsync(_ => ++tries == 1 ? Task.FromException<LauncherRelease?>(new IOException()) : Task.FromResult<LauncherRelease?>(release),
            budget: TimeSpan.FromSeconds(1), retryInterval: TimeSpan.FromMilliseconds(10));
        Check(recovered.Online && recovered.Attempts == 2 && recovered.Release == release, "Transient connectivity not retried");
        var watch = Stopwatch.StartNew();
        var offline = await StartupUpdateCheck.RunAsync(_ => new TaskCompletionSource<LauncherRelease?>().Task,
            budget: TimeSpan.FromMilliseconds(180), attemptLimit: TimeSpan.FromMilliseconds(40), retryInterval: TimeSpan.FromMilliseconds(5));
        Check(!offline.Online && offline.Attempts >= 2 && watch.Elapsed < TimeSpan.FromSeconds(2), "Uncooperative provider blocked startup");
        using (var cancel = new CancellationTokenSource(30))
        {
            bool cancelled = false;
            try { await StartupUpdateCheck.RunAsync(_ => new TaskCompletionSource<LauncherRelease?>().Task, cancellationToken: cancel.Token); }
            catch (OperationCanceledException) { cancelled = true; }
            Check(cancelled, "Open installed launcher did not cancel startup");
        }
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var payload = JsonSerializer.SerializeToUtf8Bytes(new ChannelManifest { Launcher = release }, LauncherJsonContext.Default.ChannelManifest);
        var signed = JsonSerializer.SerializeToUtf8Bytes(new SignedFeedEnvelope { Payload = Convert.ToBase64String(payload),
            Signature = Convert.ToBase64String(key.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation)) }, LauncherJsonContext.Default.SignedFeedEnvelope);
        using var http = new HttpClient(new Handler(async (r, ct) =>
        {
            if (r.RequestUri!.Host == "slow.invalid") await Task.Delay(10000, ct);
            return new(HttpStatusCode.OK) { Content = new ByteArrayContent(signed) };
        }));
        var feed = new FeedClient(new LauncherConfiguration { FeedUrls = ["https://ok.invalid/stable.json", "https://slow.invalid/stable.json"], BetaFeedUrls = [],
            PublicKeyPem = key.ExportSubjectPublicKeyInfoPem(), CacheRoot = Path.Combine(root, "startup-feed") }, http);
        var mixed = await StartupUpdateCheck.RunAsync(ct => feed.GetLauncherUpdateAsync(ct, TimeSpan.FromMilliseconds(50)), budget: TimeSpan.FromSeconds(2));
        Check(mixed.Online && mixed.Release?.Version == "99.0.0" && mixed.Attempts == 1, "Healthy signed source lost to hanging mirror");
        var bytes = Encoding.Unicode.GetBytes("\0Kohan II\0\00.0.0\0\01.3.72\0end\0");
        var fixture = Path.Combine(root, "version.fixture"); await File.WriteAllBytesAsync(fixture, bytes);
        Check(InstalledGameVersion.Read(fixture) == "1.3.72", "Kohan embedded version not detected");
        await File.WriteAllBytesAsync(fixture, bytes.Concat(Encoding.Unicode.GetBytes("\01.3.68\0")).ToArray());
        Check(InstalledGameVersion.Read(fixture) is null, "Ambiguous versions guessed");
        var requirement = new GameRequirement { Version = "1.3.72", SteamBuild = "25068126", K2ExeSha256 = [new('A', 64)] };
        Check(InstalledGameVersion.Compare("1.3.68", null, requirement, GameCompatibilityState.Unsupported) == GameVersionRelation.Older, "Older game direction");
        Check(InstalledGameVersion.Compare("1.3.73", null, requirement, GameCompatibilityState.Unsupported) == GameVersionRelation.Newer, "Newer game direction");
        Check(InstalledGameVersion.Compare("1.3.72", "25068126", requirement, GameCompatibilityState.Unsupported) == GameVersionRelation.Different, "Modified same-version executable misidentified");
        Check(InstalledGameVersion.Compare("1.3.72.0", "25068126", requirement, GameCompatibilityState.Unsupported) == GameVersionRelation.Different, "Trailing zero classified as newer version");
        Check(InstalledGameVersion.Compare("1.3.68", "1", requirement, GameCompatibilityState.Supported) == GameVersionRelation.Supported, "Metadata overrode verified hash");
        var raw = new UserSettings { DataOnly = true, CustomPlayerColors = true, IndependentHostility = true, DesyncMode = "continue" };
        var active = EffectiveSettings.ForChannel(raw);
        Check(!active.CustomPlayerColors && !active.IndependentHostility && active.DesyncMode == "official" && raw.CustomPlayerColors && raw.IndependentHostility && raw.DesyncMode == "continue", "Native preferences lost or not masked");
        Check(ConfigurationCode.Parse(ConfigurationCode.Create(active)).DataOnly, "Limited configuration lost its identity");
        Check(GameExecutableSelector.Select(new(), raw, new()) == "k2.exe", "Limited mode selected patched executable");
        var native = new InstallState { BaseGameSha256 = new('A', 64), Modules = new() { ["core"] = new() { Enabled = true, Files = [new() { Path = "helper.exe" }] } } };
        Check(GameCompatibilityPolicy.InstalledRuntimeNeedsUpdate(native, new('B', 64), requirement), "New feed hid obsolete installed runtime");
        Check(!GameCompatibilityPolicy.InstalledRuntimeNeedsUpdate(native, new('A', 64), requirement), "Current runtime rejected");
        native.Modules.Clear(); native.AppliedSettings = active;
        Check(!GameCompatibilityPolicy.InstalledRuntimeNeedsUpdate(native, new('B', 64), requirement), "Data-only installation classified as native");
        foreach (var path in new[] { "evil.EXE", "data/native.Dll", "hook.asi", "startup/run.cmd" })
        {
            bool rejected = false;
            try { GameCompatibilityPolicy.ValidateDataModules([new() { Files = [new() { Path = path }] }]); } catch (InvalidDataException) { rejected = true; }
            Check(rejected, "Executable-independent package accepted native payload: " + path);
        }
        Console.WriteLine($"STARTUP / COMPATIBILITY PASS {n}: retries, timeout, cancellation, signed mirrors, versions, remembered preferences, runtime identity");
        return n;
    }

    internal static async Task PackagesAsync(string feedPath, string keyPath, string fixtureRoot, string baseExe)
    {
        fixtureRoot = Path.GetFullPath(fixtureRoot);
        if (Directory.Exists(fixtureRoot)) throw new IOException("Choose a fresh fixture root.");
        Directory.CreateDirectory(fixtureRoot);
        var client = new FeedClient(new() { FeedUrls = [Path.GetFullPath(feedPath)], BetaFeedUrls = [], PublicKeyPem = File.ReadAllText(keyPath), CacheRoot = Path.Combine(fixtureRoot, "cache") });
        var feed = (await client.GetChannelAsync())!;
        int n = 0; void Check(bool ok, string why) { n++; if (!ok) throw new Exception(why); }
        var game = Path.Combine(fixtureRoot, "game"); Directory.CreateDirectory(game);
        File.Copy(baseExe, Path.Combine(game, "k2.exe")); var hash = await CryptoAndIO.Sha256Async(baseExe);
        var installer = new ModuleInstaller(game); var modules = new Dictionary<string, InstalledModule>();
        foreach (var p in feed.Packages)
            modules[p.Id] = await installer.PrepareAsync(p, await client.DownloadVerifiedAsync(p, null));
        foreach (var spawn in new[] { "standard", "x2", "x4" })
        for (int bits = 0; bits < 256; bits++)
        {
            bool On(int bit) => (bits & (1 << bit)) != 0;
            var s = new UserSettings { DataOnly = true, PawPatchEnabled = On(0), RussianLocalization = On(1), SiegeBalance = On(2),
                AdditionalRoamingCompanies = On(3), DisablePowersAndShards = On(4), CustomPlayerColors = On(5), IndependentHostility = On(6), DesyncMode = On(7) ? "continue" : "official", RoamingSpawnMode = spawn };
            var selected = GamePackageSelector.Select(feed, s, s.RussianLocalization, s.CustomPlayerColors);
            Check(selected.All(p => p.ExecutableIndependent), "Unreviewed package selected");
            GameCompatibilityPolicy.ValidateDataModules(selected.Select(p => modules[p.Id])); n++;
            Check(selected.Any(p => p.Id.StartsWith("pawpatch-data")) == s.PawPatchEnabled, "Paw toggle ignored");
            Check(selected.Any(p => p.Id == "aw-runtime" || p.Id == "aw-hostility" || p.Id == "aw-player-colors") == false, "Native dependency leaked");
        }
        async Task Apply(UserSettings s)
        {
            s = EffectiveSettings.ForFeed(s, feed);
            var selected = GamePackageSelector.Select(feed, s, s.RussianLocalization, s.CustomPlayerColors);
            await installer.ReconcileAsync(selected.ToDictionary(p => p.Id, p => modules[p.Id]), settings: s, releaseId: ChannelFingerprint.Create(feed), gameRequirement: feed.Game, baseGameSha256: hash);
            Check((await installer.VerifyAsync()).Count == 0, "Applied files failed verification");
            Check(await CryptoAndIO.Sha256Async(Path.Combine(game, "k2.exe")) == hash, "Original executable changed");
            Check(!UpdateDetector.HasSettingsChanges(installer.LoadState(), selected, s), "Apply still pending");
        }
        await Apply(new() { CustomPlayerColors = true, DesyncMode = "continue" });
        Check(GameCompatibilityPolicy.HasNativeModules(installer.LoadState()), "Full fixture has no native modules");
        foreach (var ru in new[] { false, true })
        {
            await Apply(new() { DataOnly = true, RussianLocalization = ru, CustomPlayerColors = true, DesyncMode = "continue" });
            Check(!GameCompatibilityPolicy.HasNativeModules(installer.LoadState()), "Old native modules not removed");
            Check(!Directory.EnumerateFiles(game, "k2_paws*.exe").Any(), "Old executable left in game root");
            var template = File.ReadAllText(Path.Combine(game, "data/templates/template_rmc_k2.tgi"));
            Check(template.Contains("width = 1152") && template.Contains("IDS = kingdom16") && template.Contains("IDS = team08") && !template.Contains("paws_war_"), "Limited base features incomplete");
        }
        await Apply(new() { DataOnly = true, PawPatchEnabled = false, RussianLocalization = false, IndependentHostility = false, RoamingSpawnMode = "standard", AdditionalRoamingCompanies = false, SiegeBalance = false, DisablePowersAndShards = false });
        Check(installer.LoadState().Modules.Keys.Order().SequenceEqual(new[] { "arcane-wars", "game-localization-en", "startup-base" }), "All off is not pure Arcane Wars with the selected English language");
        await Apply(new() { CustomPlayerColors = true, DesyncMode = "continue" });
        Check(GameCompatibilityPolicy.HasNativeModules(installer.LoadState()) && installer.LoadState().AppliedSettings?.DataOnly == false, "Compatible patch did not restore native mode");
        Console.WriteLine($"DATA-ONLY INTEGRATION PASS {n}: 768 selections, full → limited EN → limited RU → pure AW → full, unchanged base EXE");
    }
    private sealed class Handler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send) : HttpMessageHandler
    { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct) => send(request, ct); }
}

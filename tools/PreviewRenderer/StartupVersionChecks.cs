using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using System.Collections.Concurrent;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class StartupVersionChecks
{
    internal static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest || !ActivityStore.Root.StartsWith("G:", StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Isolated G: fixture required");
        Directory.CreateDirectory(output);
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        var checks = 0; void Check(bool ok, string why) { if (!ok) throw new Exception("Startup version: " + why); checks++; }
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var requests = new ConcurrentQueue<string>();
        LauncherRelease Release(string version) => new() { Version = version, Size = 123, Sha256 = new('A', 64), Urls = ["https://versions.invalid/" + version + ".exe"] };
        byte[] Signed(string channel, string version)
        {
            var payload = JsonSerializer.SerializeToUtf8Bytes(new ChannelManifest { Channel = channel, Launcher = Release(version) }, LauncherJsonContext.Default.ChannelManifest);
            return JsonSerializer.SerializeToUtf8Bytes(new SignedFeedEnvelope { Payload = Convert.ToBase64String(payload),
                Signature = Convert.ToBase64String(key.SignData(payload, HashAlgorithmName.SHA256, DSASignatureFormat.IeeeP1363FixedFieldConcatenation)) }, LauncherJsonContext.Default.SignedFeedEnvelope);
        }
        // Deliberately provide an intermediate release on the first source.
        using var http = new HttpClient(new Handler(async (request, token) =>
        {
            var path = request.RequestUri!.AbsolutePath; requests.Enqueue(path);
            if (path == "/stable.json") return new(HttpStatusCode.OK) { Content = new ByteArrayContent(Signed("stable", "99.0.6")) };
            if (path == "/beta.json") return new(HttpStatusCode.OK) { Content = new ByteArrayContent(Signed("beta", "99.0.7")) };
            if (path == "/99.0.7.exe")
            {
                await Task.Delay(Timeout.Infinite, token);
                throw new HttpRequestException("Fixture transfer deliberately stopped");
            }
            throw new InvalidOperationException("Unexpected request: " + path);
        }));
        var cache = Path.Combine(ActivityStore.Root, "version-cache");
        var feed = new FeedClient(new LauncherConfiguration { FeedUrls = ["https://versions.invalid/stable.json"], BetaFeedUrls = ["https://versions.invalid/beta.json"],
            PublicKeyPem = key.ExportSubjectPublicKeyInfoPem(), CacheRoot = cache }, http);
        var window = new StartupWindow(feed, language) { Left = -30000, Top = -30000, ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        typeof(StartupWindow).GetField("_started", flags)!.SetValue(window, true);
        async Task Scenario()
        {
            var task = (Task)typeof(StartupWindow).GetMethod("RunAsync", flags)!.Invoke(window, null)!;
            for (var i = 0; i < 200 && !requests.Contains("/99.0.7.exe"); i++) await Task.Delay(10);
            Check(requests.Contains("/99.0.7.exe") && !requests.Contains("/99.0.6.exe"), "transfer chose the intermediate release");
            Check(((TextBlock)window.FindName("VersionText")).Text == SelfUpdater.CurrentVersion.ToString(3) + " → 99.0.7", "header does not show the actual version transition");
            Check(((TextBlock)window.FindName("DetailText")).Text.Contains("99.0.7"), "download label differs from the requested EXE");
            window.UpdateLayout();
            var root = (FrameworkElement)window.Content; var visual = new DrawingVisual();
            using (var dc = visual.RenderOpen()) dc.DrawRectangle(new VisualBrush(root), null, new Rect(root.RenderSize));
            var bmp = new RenderTargetBitmap((int)root.ActualWidth, (int)root.ActualHeight, 96, 96, PixelFormats.Pbgra32); bmp.Render(visual);
            var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(bmp)); using (var file = File.Create(Path.Combine(output, "download-versions-" + language + ".png"))) png.Save(file);
            ((Button)window.FindName("CancelUpdateButton")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            await task; Check(!await window.Completion && !Directory.EnumerateFiles(cache, "*.exe", SearchOption.AllDirectories).Any(), "fixture installed an update");

            var main = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(ActivityStore.Root, "handoff-cache") }, null);
            try
            {
                void Set(string name, object value) => typeof(MainWindow).GetField(name, flags)!.SetValue(main, value);
                ((PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text", flags)!.GetValue(main)!).SetLanguage(language);
                Set("_pendingLauncherUpdate", Release("99.0.6"));
                var restarted = false; var finished = false;
                Set("_restartLauncher", (Func<Task>)(() =>
                {
                    restarted = true;
                    var feedback = (OperationFeedback)typeof(MainWindow).GetField("_feedback", flags)!.GetValue(main)!;
                    Check(feedback.Message == UiLanguages.Text(language, "Ищем последнюю версию лаунчера…", "Looking for the latest launcher version…"), "handoff promises the previously discovered stale version");
                    return Task.CompletedTask;
                }));
                Set("_finishLauncherRestart", (Action)(() => finished = true));
                var handedOff = await (Task<bool>)typeof(MainWindow).GetMethod("InstallPendingLauncherUpdateAsync", flags)!.Invoke(main, [true])!;
                Check(handedOff && restarted && finished, "version display change broke startup handoff");
            }
            finally { main.Close(); }
            Console.WriteLine($"STARTUP VERSION PASS {checks} {language}: skipped intermediate release, signed sources, actual requested version and stale handoff; no real replacement");
        }
        try
        {
            window.Show(); var task = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame = new DispatcherFrame();
            _ = task.ContinueWith(_ => window.Dispatcher.BeginInvoke(() => frame.Continue = false));
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(20) }; timer.Tick += (_, _) => frame.Continue = false;
            timer.Start(); Dispatcher.PushFrame(frame); timer.Stop(); if (!task.IsCompleted) throw new TimeoutException("Startup versions"); task.GetAwaiter().GetResult();
        }
        finally { typeof(StartupWindow).GetField("_finished", flags)!.SetValue(window, true); window.Close(); }
    }

    private sealed class Handler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) => send(request, cancellationToken);
    }
}

using System.Reflection;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class LauncherUpdateChecks
{
    internal static void Run()
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Requires isolated smoke mode.");
        var root = Path.Combine(ActivityStore.Root, "global-launcher-update", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var config = new LauncherConfiguration { FeedUrls = [Path.Combine(root, "stable.json")],
            BetaFeedUrls = [Path.Combine(root, "beta.json")], CacheRoot = Path.Combine(root, "cache") };
        void Feed(string channel, string version) => File.WriteAllText(Path.Combine(root, channel + ".json"),
            JsonSerializer.Serialize(new ChannelManifest { Channel = channel, Launcher = new() {
                Version = version, Sha256 = new string('A', 64), Size = 123, Urls = [Path.Combine(root, "never-download.exe")] } }, LauncherJsonContext.Default.ChannelManifest));
        Feed("stable", "99.2.0"); Feed("beta", "99.1.0");
        var window = new MainWindow(config, null);
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(window, args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(window)!;
        var settings = Field<UserSettings>("_settings"); settings.Channel = "beta"; settings.PinnedRelease = null;
        var button = (Button)window.FindName("LauncherUpdateButton");
        var checks = 0;
        void Visible(string version) { checks++; if (button.Visibility != Visibility.Visible || !button.Content.ToString()!.Contains(version))
            throw new Exception("Launcher update vanished or changed: expected " + version); }
        async Task Check() => await (Task<bool>)Invoke("CheckFeedAsync", false)!;
        async Task Scenario()
        {
            await Check(); Visible("99.2.0");
            if (Field<ChannelManifest>("_channel").Channel != "beta") throw new Exception("Launcher check changed patch selection.");
            for (var i = 0; i < 4; i++)
            {
                var change = (Task)Invoke("ChangeChannelAsync", i % 2 != 0)!;
                Visible("99.2.0"); // includes the cleared patch-channel state while checking
                await change; Visible("99.2.0");
            }
            Feed("stable", "99.0.0"); Feed("beta", "99.0.0");
            await Check(); Visible("99.2.0");
            File.Delete(config.FeedUrls[0]); File.Delete(config.BetaFeedUrls[0]);
            await Check(); Visible("99.2.0");
            if (!Field<bool>("_launcherCheckFailed")) throw new Exception("Failed common check reported success.");
            Feed("stable", "99.3.0"); Feed("beta", "99.1.0");
            settings.PinnedRelease = new string('B', 64); // deliberately missing pinned patch
            await Check(); Visible("99.3.0");
            if (Field<bool>("_launcherCheckFailed")) throw new Exception("Pinned patch failure prevented launcher check.");
            // Fresh startup in Beta must also find a launcher when the Beta endpoint is broken.
            File.Delete(config.BetaFeedUrls[0]); settings.PinnedRelease = null;
            typeof(MainWindow).GetField("_launcherUpdates", flags)!.SetValue(window, new LauncherUpdateState());
            await Check(); Visible("99.3.0");
            Console.WriteLine($"GLOBAL LAUNCHER UI PASS {checks}: Beta startup, 4 channel switches, stale feeds, both endpoints failed, missing pinned patch, broken active channel; no launch/download/install");
        }
        try
        {
            var task = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame(); var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) };
            timer.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => window.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("Global launcher UI checks timed out.");
            task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}

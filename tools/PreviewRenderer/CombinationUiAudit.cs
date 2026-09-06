using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class CombinationUiAudit
{
    internal static void Run()
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Combination audit requires isolated smoke mode.");
        var root = Path.Combine(ActivityStore.Root, "combination-audit", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var release = new ChannelManifest { Channel = "stable", Packages = [new() { Id = "pawpatch-core", Required = true }] };
        var beta = new ChannelManifest { Channel = "beta", Packages = [new() { Id = "pawpatch-core", Required = true }, new() { Id = "player-colors" }] };
        var config = new LauncherConfiguration { FeedUrls = [Path.Combine(root,"stable.json")], BetaFeedUrls = [Path.Combine(root,"beta.json")], CacheRoot = Path.Combine(root,"cache") };
        File.WriteAllText(config.FeedUrls[0], JsonSerializer.Serialize(release, LauncherJsonContext.Default.ChannelManifest));
        File.WriteAllText(config.BetaFeedUrls[0], JsonSerializer.Serialize(beta, LauncherJsonContext.Default.ChannelManifest));
        var window = new MainWindow(config, null);
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(window, args);
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(window, value);
        var settings = (UserSettings)typeof(MainWindow).GetField("_settings", flags)!.GetValue(window)!;
        settings.Channel = "beta"; settings.CustomPlayerColors = false; settings.DesyncMode = "official";
        Set("_channel", beta); Set("_latestChannel", beta); Set("_game", null);
        Invoke("RefreshModuleAvailability");
        var colors = (CheckBox)window.FindName("ColorsToggle");
        colors.IsChecked = true; Invoke("OptionChanged", colors, new RoutedEventArgs());
        async Task Scenario()
        {
            await (Task)Invoke("ChangeChannelAsync", false)!;
            var code = ((TextBlock)window.FindName("ConfigurationCodeText")).Text;
            bool importable;
            try { _ = ConfigurationCode.Parse(code); importable = true; }
            catch (FormatException) { importable = false; }
            var finding = colors.IsChecked == false && settings.CustomPlayerColors && !importable;
            Console.WriteLine($"COMBINATION UI AUDIT Beta(colors on)->Release: displayedColors={colors.IsChecked}, savedColors={settings.CustomPlayerColors}, friendCodeImportable={importable}, code={code}");
            if (finding || !importable || !settings.CustomPlayerColors || colors.IsChecked != false)
                throw new InvalidOperationException("Release code/display or remembered Beta colors regressed.");
            var active = (UserSettings)Invoke("GetEffectiveSettings")!;
            if (active.CustomPlayerColors || active.Channel != "stable") throw new InvalidOperationException("Applied/report/observation configuration still contains inactive colors.");
            var russian = (CheckBox)window.FindName("RussianToggle");
            foreach (var enabled in new[] { false, true })
            {
                russian.IsChecked = enabled;
                Invoke("OptionChanged", russian, new RoutedEventArgs());
                var shared = ConfigurationCode.Parse(((TextBlock)window.FindName("ConfigurationCodeText")).Text);
                if (!settings.CustomPlayerColors || shared.CustomPlayerColors || shared.RussianLocalization != enabled)
                    throw new InvalidOperationException("Changing Release localization erased Beta preference or broke the shared code.");
            }
            Invoke("RestoreSettings", new UserSettings { Channel = "stable", CustomPlayerColors = false }, null);
            if (!settings.CustomPlayerColors) throw new InvalidOperationException("Release recovery/import erased remembered Beta colors.");
            Console.WriteLine("COMBINATION UI FIX PASS: Release code is importable, active snapshot excludes colors, localization changes and recovery/import retain Beta preference");
            await (Task)Invoke("ChangeChannelAsync", true)!;
            if (colors.IsChecked != true) throw new InvalidOperationException("Remembered Beta color selection did not return.");
            colors.IsChecked = false; Invoke("OptionChanged", colors, new RoutedEventArgs());
            if (settings.CustomPlayerColors || ((UserSettings)Invoke("GetEffectiveSettings")!).CustomPlayerColors)
                throw new InvalidOperationException("Explicit Beta color OFF was not saved.");
            Console.WriteLine("RETURN TO BETA: remembered selection restored; no packages installed or game launched");
        }
        try
        {
            var task = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(20) };
            timer.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => window.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("Combination UI audit timed out.");
            task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}

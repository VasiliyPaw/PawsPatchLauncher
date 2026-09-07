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
        var beta = new ChannelManifest { Channel = "beta", ColorDesyncContinue = true, Packages = [new() { Id = "pawpatch-core", Required = true }, new() { Id = "player-colors" }] };
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
            var bypass = (RadioButton)window.FindName("ContinueOosRadio");
            Invoke("RefreshReliabilityStatus");
            if (!bypass.IsEnabled) throw new InvalidOperationException("New Beta disables colors plus bypass.");
            bypass.IsChecked = true;
            Invoke("OptionChanged", colors, new RoutedEventArgs());
            if (settings.DesyncMode != "continue" || !ConfigurationCode.Parse(((TextBlock)window.FindName("ConfigurationCodeText")).Text).CustomPlayerColors)
                throw new InvalidOperationException("Combined colors/bypass state or friend code lost.");
            Invoke("RefreshModuleAvailability");
            if (settings.DesyncMode != "continue") throw new InvalidOperationException("Feed refresh reverted combined mode.");
            beta.ColorDesyncContinue = false;
            Invoke("RefreshModuleAvailability");
            if (settings.DesyncMode != "official" || bypass.IsEnabled) throw new InvalidOperationException("Older Beta can select a missing combined helper.");
            beta.ColorDesyncContinue = true;
            Invoke("RefreshModuleAvailability");
            Console.WriteLine("COLORS + BYPASS UI PASS: new feed, radio, code, refresh, old-feed guard");
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
            if (settings.CustomPlayerColors) throw new InvalidOperationException("Explicit import of colors OFF ignored.");
            Console.WriteLine("COMBINATION UI FIX PASS: old Release masks unavailable colors; explicit imported preference wins");
            await (Task)Invoke("ChangeChannelAsync", true)!;
            if (colors.IsChecked != false) throw new InvalidOperationException("Explicit imported color selection did not persist.");
            colors.IsChecked = false; Invoke("OptionChanged", colors, new RoutedEventArgs());
            if (settings.CustomPlayerColors || ((UserSettings)Invoke("GetEffectiveSettings")!).CustomPlayerColors)
                throw new InvalidOperationException("Explicit Beta color OFF was not saved.");
            Console.WriteLine("RETURN TO BETA: remembered selection restored; no packages installed or game launched");
            var hostilityToggle = (CheckBox)window.FindName("IndependentHostilityToggle");
            foreach (var channel in new[] { release, beta })
            {
                channel.IndependentColorHostility = true; channel.ColorDesyncContinue = true;
                if (!channel.Packages.Any(p => p.Id == "player-colors")) channel.Packages.Add(new() { Id = "player-colors" });
                settings.Channel = channel.Channel; Set("_channel", channel); Set("_latestChannel", channel);
                for (var bits = 0; bits < 8; bits++)
                {
                    settings.CustomPlayerColors = (bits & 1) != 0;
                    settings.DesyncMode = (bits & 2) != 0 ? "continue" : "official";
                    settings.IndependentHostility = (bits & 4) != 0;
                    Invoke("RefreshModuleAvailability"); Invoke("RefreshReliabilityStatus");
                    if (!colors.IsEnabled || !hostilityToggle.IsEnabled || !bypass.IsEnabled)
                        throw new InvalidOperationException("Promoted release disables an independent switch.");
                    Invoke("OptionChanged", colors, new RoutedEventArgs());
                    var parsed = ConfigurationCode.Parse(((TextBlock)window.FindName("ConfigurationCodeText")).Text);
                    if (parsed.CustomPlayerColors != ((bits & 1) != 0) || parsed.IndependentHostility != ((bits & 4) != 0)
                        || parsed.DesyncMode != ((bits & 2) != 0 ? "continue" : "official"))
                        throw new InvalidOperationException("Promoted release changed an independent switch.");
                }
            }
            Console.WriteLine("PROMOTED UI PASS: 16 native toggle combinations in Release/Beta, controls enabled, no forced settings");
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

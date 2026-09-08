using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class ComponentSettingsChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new Exception("Isolated smoke mode required.");
        var root = Path.Combine(ActivityStore.Root, "component-settings", Guid.NewGuid().ToString("N"));
        var game = Path.Combine(root, "игра & тест"); Directory.CreateDirectory(game);
        var exe = Path.Combine(game, "k2.exe"); File.WriteAllText(exe, "inert fixture, never launched");
        var config = new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(root, "cache") };
        var feed = new ChannelManifest { ColorDesyncContinue = true, IndependentColorHostility = true };
        var ids = new[] { "arcane-wars", "pawpatch-core", "desync-continue", "roaming-profile-x2-with-new", "roaming-profile-x2-no-new",
            "roaming-profile-standard-with-new", "roaming-profile-standard-no-new", "roaming-profile-x4-no-new" };
        foreach (var id in ids)
        {
            var data = Encoding.UTF8.GetBytes(id); var file = "data/" + id + ".txt";
            var module = new ModuleArchiveManifest { Id = id, Version = "1",
                Files = [new() { Path = file, Size = data.Length, Sha256 = Convert.ToHexString(SHA256.HashData(data)) }] };
            var zip = Path.Combine(root, id + ".zip");
            using (var archive = ZipFile.Open(zip, ZipArchiveMode.Create))
            {
                using (var output = archive.CreateEntry("module.json").Open())
                    JsonSerializer.Serialize(output, module, LauncherJsonContext.Default.ModuleArchiveManifest);
                using (var output = archive.CreateEntry("payload/" + file).Open()) output.Write(data);
            }
            feed.Packages.Add(new() { Id = id, Version = "1", Required = id is "arcane-wars" or "pawpatch-core",
                Urls = [zip], Size = new FileInfo(zip).Length, Sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(zip))) });
        }
        var window = new MainWindow(config, null) { Width = 1100, Height = 750, Left = -30000, Top = -30000,
            ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(window, args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(window)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(window, value);
        T Control<T>(string name) => (T)window.FindName(name);
        var settings = Field<UserSettings>("_settings");
        ConfigurationCode.Apply(new UserSettings { RussianLocalization = false }, settings);
        Set("_game", new GameInstallation(game, exe, "test", "test")); Set("_channel", feed); Set("_latestChannel", feed);
        Set("_lastChecked", DateTimeOffset.Now); Set("_gameRunningProbe", (Func<bool>)(() => false));
        // Earlier fixtures may have left another radio selected in the loaded smoke settings.
        Set("_initializing",true); Invoke("SelectSpawnMode",settings.RoamingSpawnMode); Set("_initializing",false);
        Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language);
        Invoke("ApplyLanguage"); Invoke("SetActivePage", "modules"); window.Show(); window.UpdateLayout();
        var checks = 0;
        void Check(bool ok, string reason) { checks++; if (!ok) throw new Exception(reason); }
        var apply = Control<Button>("ApplySettingsButton");
        async Task Apply() => await (Task)Invoke("ApplySettingsAsync")!;
        async Task Hidden(string reason)
        {
            await Task.Delay(200);
            Check(apply.Visibility == Visibility.Collapsed && !apply.IsHitTestVisible && !apply.IsTabStop && !apply.IsEnabled, reason);
        }
        async Task Scenario()
        {
            await Apply();
            Check(File.Exists(Path.Combine(game, "data", "pawpatch-core.txt")), "Apply failed to install fixture files");
            Check(!apply.IsEnabled && !Field<bool>("_settingsPending"), "Applied state remains pending");
            await Hidden("Apply did not hide after installation on Components");
            var stack = (Panel)Control<Border>("CoreModuleCard").Parent;
            Check(stack.Children.IndexOf(Control<Border>("OosModuleCard")) == stack.Children.IndexOf(Control<Border>("CoreModuleCard")) + 1, "Ignore desync not second");
            var cards = stack.Children.OfType<Border>().Where(c => c.Visibility == Visibility.Visible).ToArray();
            Check(cards.Last() == Control<Border>("RoamingSpawnCard"), "Frequency not last");
            var toggle = Control<CheckBox>("IgnoreDesyncToggle");
            toggle.IsChecked = true; Invoke("OosToggle_Click", toggle, new RoutedEventArgs());
            Check(settings.DesyncMode == "continue" && apply.IsEnabled, "Toggle did not enable Apply");
            Check(apply.Visibility == Visibility.Visible && apply.IsHitTestVisible && apply.IsTabStop, "Changed settings did not reveal Apply");
            foreach (var page in new[] { "home", "settings", "multiplayer", "about", "modules" })
            {
                Invoke("SetActivePage", page); Invoke("RefreshStatus"); await Task.Delay(180);
                Check(apply.Visibility == Visibility.Visible && apply.IsEnabled && apply.IsHitTestVisible && apply.IsTabStop && apply.Opacity > 0.99,
                    "Pending Apply hidden/unusable on " + page);
            }
            toggle.IsChecked = false; Invoke("OosToggle_Click", toggle, new RoutedEventArgs());
            Check(settings.DesyncMode == "official" && !apply.IsEnabled, "Reverting toggle still pending");
            // Reverse an in-flight hide, then return to the applied state again.
            toggle.IsChecked = true; Invoke("OosToggle_Click", toggle, new RoutedEventArgs());
            Invoke("SetActivePage", "home"); Invoke("RefreshStatus"); await Task.Delay(200);
            Check(apply.Visibility == Visibility.Visible && apply.IsEnabled && apply.Opacity > 0.99, "Interrupted fade hid a new pending change");
            toggle.IsChecked = false; Invoke("OosToggle_Click", toggle, new RoutedEventArgs());
            await Hidden("Reverted settings did not hide Apply outside Components");
            Invoke("SetActivePage", "modules");
            settings.IndependentHostility = false; Invoke("RefreshStatus");
            Check(apply.IsEnabled, "Native-only change not detected");
            await Apply();
            Check(new ModuleInstaller(game).LoadState().AppliedSettings?.IndependentHostility == false && !apply.IsEnabled, "Native-only apply not persisted");
            await Hidden("Native-only apply did not hide on Components");
            var x2 = Control<RadioButton>("X2SpawnRadio"); x2.IsChecked = true;
            Check(settings.RoamingSpawnMode == "x2" && apply.IsEnabled, "x2 selection not pending");
            Check(!Control<Button>("UpdateButton").IsEnabled, "New option was mislabelled as a patch update");
            await Apply();
            Check(File.Exists(Path.Combine(game, "data", "roaming-profile-x2-with-new.txt")) && !apply.IsEnabled, "x2 apply failed");
            await Hidden("x2 apply did not hide on Components");
            var appliedBytes = File.ReadAllBytes(Path.Combine(game, ".pawpatch", "state.json"));
            var runningCalls = 0;
            Set("_gameRunningProbe", (Func<bool>)(() => { runningCalls++; return true; }));
            settings.IndependentHostility = true; Invoke("RefreshStatus");
            await Apply();
            Check(runningCalls > 0, "Apply did not check game running");
            var afterApply=runningCalls;
            Invoke("UpdateButton_Click", Control<Button>("UpdateButton"), new RoutedEventArgs());
            Check(runningCalls > afterApply, "Update did not check game running");
            var afterUpdate=runningCalls;
            Invoke("LaunchButton_Click", Control<Button>("LaunchButton"), new RoutedEventArgs());
            Check(runningCalls > afterUpdate, "Launch did not check game running");
            Check(appliedBytes.SequenceEqual(File.ReadAllBytes(Path.Combine(game, ".pawpatch", "state.json"))), "Running game changed installation");
            Check(Field<object?>("_presentedError") is null, "Running game opened generic error/diagnostics");
            Check(!Field<bool>("_busy"), "Running guard left launcher busy");
            await Task.Delay(180);
            Check(apply.Visibility == Visibility.Visible && apply.IsEnabled && Field<bool>("_settingsPending"), "Blocked application discarded pending Apply");
            // Also block a game started during the download/prepare phase.
            bool InLaunchGuard() => new System.Diagnostics.StackTrace().GetFrames().Any(frame=>frame.GetMethod()?.Name=="EnsureGameClosed");
            var probes = 0; Set("_gameRunningProbe", (Func<bool>)(() => { if(InLaunchGuard())probes++; return probes>=3; }));
            await Apply(); // entry + apply entry + pre-reconcile
            Check(probes == 3 && appliedBytes.SequenceEqual(File.ReadAllBytes(Path.Combine(game, ".pawpatch", "state.json"))), "Late game start allowed reconciliation");
            Set("_gameRunningProbe", (Func<bool>)(() => false));
            settings.IndependentHostility = false;
            settings.Channel = feed.Channel = "beta"; Invoke("RefreshStatus");
            Check(!Control<Button>("UpdateButton").IsEnabled && !apply.IsEnabled, "Identical channel asks for update/application");
            settings.AdditionalRoamingCompanies = false; Invoke("RefreshStatus");
            Check(!Control<Button>("UpdateButton").IsEnabled && apply.IsEnabled, "Cached profile requires redownload");
            Invoke("SetActivePage", "home");
            await Apply();
            Check(!File.Exists(Path.Combine(game, "data", "roaming-profile-x2-with-new.txt")) && File.Exists(Path.Combine(game, "data", "roaming-profile-x2-no-new.txt")), "Profile switch left previous files");
            Check(!apply.IsEnabled, "Apply still active after profile switch");
            await Hidden("Apply outside Components did not hide after success");
            var x2Packages = feed.Packages.Where(p => p.Id.StartsWith("roaming-profile-x2")).ToArray();
            feed.Packages.RemoveAll(p => x2Packages.Contains(p));
            Invoke("RefreshStatus"); await Apply();
            Check(!x2.IsEnabled && Field<object?>("_presentedError") is null, "Older feed did not explain missing x2 safely");
            Check(new ModuleInstaller(game).LoadState().AppliedSettings?.RoamingSpawnMode == "x2", "Older feed silently replaced applied x2");
            feed.Packages.AddRange(x2Packages); Invoke("RefreshStatus");
            var saves = Path.Combine(root, "сейвы"); string? opened = null;
            Set("_savesDirectory", (Func<string>)(() => saves));
            Set("_openGameFolder", (Func<string, Task>)(path => { opened = path; return Task.CompletedTask; }));
            await (Task)Invoke("OpenSavesFolderAsync")!;
            Check(opened is null && !Directory.Exists(saves), "Missing saves folder created/opened unexpectedly");
            Directory.CreateDirectory(saves); await (Task)Invoke("OpenSavesFolderAsync")!;
            Check(opened == saves, "Wrong saves folder opened");
            foreach (var page in new[] { "home", "modules", "multiplayer", "settings", "about" })
            {
                Invoke("SetActivePage", page); Invoke("RefreshStatus");
                await Hidden("Applied settings revealed Apply on " + page);
            }
            settings.IndependentHostility = true; Invoke("RefreshStatus"); await Task.Delay(200);
            Check(apply.Visibility == Visibility.Visible && apply.IsEnabled, "Pending settings on About did not reveal Apply");
            Set("_checkingFeed", true); Invoke("RefreshStatus");
            Check(apply.Visibility == Visibility.Visible && !apply.IsEnabled, "Feed check discarded pending action instead of temporarily disabling it");
            Set("_checkingFeed", false); Invoke("RefreshStatus");
            foreach (var width in new[] { 1050, 1440 })
            {
                window.Width = width; Invoke("RefreshActionLayout"); window.UpdateLayout();
                foreach (var name in new[] { "UpdateButton", "CheckUpdatesButton", "ApplySettingsButton", "LaunchButton" })
                {
                    var button = Control<Button>(name);
                    var bounds = button.TransformToAncestor(window).TransformBounds(new Rect(button.RenderSize));
                    Check(bounds.Left >= 0 && bounds.Right <= window.ActualWidth && bounds.Bottom <= window.ActualHeight, "Footer clipped at " + width + ": " + name);
                }
                Check(Grid.GetRow(apply) == (width < 1250 ? 0 : 1), "Wrong compact Apply placement");
            }
            // Use the actual launch preparation path with inert local files. The final
            // running-game guard stops it before Process.Start; no real game is opened.
            settings.AdditionalRoamingCompanies = true; Invoke("RefreshStatus");
            var launchExe = (string)Invoke("ResolveLaunchExecutable", game)!;
            File.WriteAllText(launchExe, "inert pre-launch fixture, never launched");
            var launchProbes = 0;
            Set("_gameRunningProbe", (Func<bool>)(() => { if(InLaunchGuard())launchProbes++; return launchProbes>=4; }));
            await (Task)Invoke("LaunchGameAsync")!;
            Check(launchProbes == 4, "Launch test did not reach the final pre-process guard");
            Check(new ModuleInstaller(game).LoadState().AppliedSettings?.IndependentHostility == true && !Field<bool>("_settingsPending"), "Launch did not apply pending settings");
            Check(File.Exists(Path.Combine(game, "data", "roaming-profile-x2-with-new.txt")) && !File.Exists(Path.Combine(game, "data", "roaming-profile-x2-no-new.txt")), "Launch did not reconcile selected component packages");
            await Hidden("Apply remained visible after launch applied settings");
            Invoke("SetActivePage", "modules"); Invoke("RefreshStatus");
            await Hidden("Returning to Components revealed already-applied launch settings");
            Check(Field<object?>("_presentedError") is null && !Field<bool>("_busy"), "Launch guard opened diagnostics or stayed busy");
            Check(new SettingsStore().Load().RoamingSpawnMode == "x2", "SP2 selection not saved");
            Console.WriteLine($"COMPONENT UI PASS {checks} {language}: isolated install/apply/revert, cached profiles, native settings, running guards, folder navigation, cross-tab pending action and launch-path application; no game started");
        }
        try
        {
            var task = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(15) };
            var deadline = DateTime.UtcNow.AddSeconds(50);
            timer.Tick += (_, _) => { if (task.IsCompleted || DateTime.UtcNow > deadline) frame.Continue = false; };
            timer.Start(); Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Component UI fixture timed out");
            task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}

using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class MissingExecutableChecks
{
    internal static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest || !ActivityStore.Root.StartsWith("G:", StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Isolated G: profile required");
        Directory.CreateDirectory(output);
        var game = Path.Combine(ActivityStore.Root, Guid.NewGuid().ToString("N")[..8], "Kohan II"); Directory.CreateDirectory(game);
        File.WriteAllText(Path.Combine(game, "Data.rwd"), "UI fixture only, never loaded by a game");
        new SettingsStore().Save(new UserSettings { Language = language, Mod = GameMod.Vanilla, GamePath = game, GameTextLanguage = "en", ModNoticeSeen = true });
        var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(ActivityStore.Root, "cache") }, null)
        { Width = 1440, Height = 1000, Left = -30000, Top = -30000, ShowInTaskbar = false, ShowActivated = false, WindowStartupLocation = WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        T C<T>(string name) => (T)w.FindName(name);
        var checks = 0; void Check(bool ok, string why) { if (!ok) throw new Exception("Missing executable UI: " + why); checks++; }
        void Snap(string name, FrameworkElement element)
        {
            element.UpdateLayout(); var visual = new DrawingVisual();
            using (var dc = visual.RenderOpen()) dc.DrawRectangle(new VisualBrush(element), null, new Rect(element.RenderSize));
            var image = new RenderTargetBitmap((int)Math.Ceiling(element.ActualWidth), (int)Math.Ceiling(element.ActualHeight), 96, 96, PixelFormats.Pbgra32); image.Render(visual);
            var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(image)); using var file = File.Create(Path.Combine(output, name + "-" + language + ".png")); encoder.Save(file);
        }
        async Task Dialog(string name)
        {
            var dialog = (Window)Call("CreateMissingExecutableDialog")!;
            dialog.WindowStartupLocation = WindowStartupLocation.Manual; dialog.Left = dialog.Top = -30000; dialog.ShowActivated = false;
            dialog.Show(); await Task.Delay(100);
            Check(dialog.WindowStyle == WindowStyle.None, "system title bar remains");
            Snap(name, (FrameworkElement)dialog.Content); dialog.Close();
        }
        async Task Scenario()
        {
            Set("_gameRunningProbe", (Func<bool>)(() => false));
            Call("LocateGame"); Call("RefreshStatus"); Call("SetActivePage", "home");
            await Task.Delay(80); w.UpdateLayout();
            Check(Field<GameInstallation?>("_game") is null, "missing saved game silently switched to Steam copy");
            Check(Field<UserSettings>("_settings").GamePath == game && C<TextBlock>("GamePathText").Text == game, "saved recovery path was lost");
            Check(C<Border>("MissingExecutableCard").IsVisible && C<TextBlock>("MissingExecutableName").Text == "k2.exe", "base warning missing");
            Check(!C<Button>("LaunchButton").IsEnabled, "missing base EXE can launch");
            Snap("home-missing-exe", (FrameworkElement)w.Content); Snap("warning-card", C<Border>("MissingExecutableCard"));
            await Dialog("restore-game-exe");
            File.WriteAllText(Path.Combine(game, "k2.exe"), "UI detector fixture only; never executed");
            Call("MissingExecutableRecheck_Click", w, new RoutedEventArgs()); await Task.Delay(50);
            Check(!C<Border>("MissingExecutableCard").IsVisible && Field<GameInstallation?>("_game")?.Directory == game, "recheck did not recover restored EXE");
            File.Delete(Path.Combine(game, "k2.exe"));
            Call("RefreshStatus");
            Check(C<Border>("MissingExecutableCard").IsVisible, "file loss after initial discovery is ignored");
            Call("ApplyGameLaunchState", false);
            Check(!C<Button>("LaunchButton").IsEnabled, "game-status timer re-enabled launch for a missing EXE");
            File.WriteAllText(Path.Combine(game, "k2.exe"), "UI detector fixture only; never executed");
            Call("MissingExecutableRecheck_Click", w, new RoutedEventArgs());
            var settings = Field<UserSettings>("_settings"); settings.VanillaPawPatchEnabled = true;
            var channel = new ChannelManifest { Channel = "stable", Packages = [new PackageRelease { Id = "pure-fixes-data" }, new PackageRelease { Id = "pure-fixes-runtime" }] };
            Set("_channel", channel);
            var helper = (string)Call("ResolveLaunchExecutable", game)!;
            var state = new InstallState { AppliedSettings = settings };
            state.Modules["pure-fixes-runtime"] = new InstalledModule { Enabled = true, Files = [new ModuleFile { Path = Path.GetFileName(helper) }] };
            Call("RefreshMissingExecutable", state);
            Check(Field<MissingGameExecutable?>("_missingExecutable")?.IsPatchHelper == true, "managed helper warning missing");
            await Dialog("restore-patch-exe");
            Console.WriteLine($"MISSING EXECUTABLE UI PASS {checks} {language}: persistent warning, saved path, no Steam fallback, themed base/helper guidance and successful recheck; no game/security app launched");
        }
        try
        {
            w.Show(); var task = w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame = new DispatcherFrame();
            _ = task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false));
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(45) }; timer.Tick += (_, _) => frame.Continue = false;
            timer.Start(); Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Missing executable UI"); task.GetAwaiter().GetResult();
        }
        finally { w.Close(); }
    }
}

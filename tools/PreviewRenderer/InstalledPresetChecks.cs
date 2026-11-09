using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class InstalledPresetChecks
{
    internal static void Run(string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Read-only preset fixture required");
        Directory.CreateDirectory(output); var settings = new SettingsStore().Load();
        var config = SettingsStore.LoadConfiguration(); config.CacheRoot = Path.Combine(ActivityStore.Root, "cache"); config.FeedUrls = []; config.BetaFeedUrls = [];
        var channel = new FeedClient(config).LoadArchived(settings.PinnedRelease!, settings.Channel);
        var w = new MainWindow(config, new FeedClient(config)) { Width = 1440, Height = 960, Left = -30000, Top = -30000, ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        T C<T>(string name) => (T)w.FindName(name);
        var checks = 0; void Check(bool ok, string why) { if (!ok) throw new Exception("Installed preset: " + why); checks++; }
        void Snap(string name, FrameworkElement element)
        {
            element.UpdateLayout(); var drawing = new DrawingVisual();
            using (var dc = drawing.RenderOpen()) dc.DrawRectangle(new VisualBrush(element), null, new Rect(element.RenderSize));
            var image = new RenderTargetBitmap((int)Math.Ceiling(element.ActualWidth), (int)Math.Ceiling(element.ActualHeight), 96, 96, PixelFormats.Pbgra32); image.Render(drawing);
            var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(image)); using var file = File.Create(Path.Combine(output, name + ".png")); encoder.Save(file);
        }
        async Task Scenario()
        {
            Check(settings.Mod == GameMod.ArcaneWars && settings.Channel == "beta" && settings.GameVoiceLanguage == "custom", "wrong installed mode");
            Check(CustomVoices.Groups.Select(g => CustomVoices.Language(settings, g)).SequenceEqual(new[] { "fr", "en", "de", "ru", "en", "ru" }), "wrong user preset");
            var game = GameLocator.Validate(settings.GamePath!, config.SteamAppId) ?? throw new Exception("Prepared game was not detected");
            Set("_gameRunningProbe", (Func<bool>)(() => false)); // Only the running-game interlock is controlled; another user-owned QA game is open.
            Set("_game", game); Set("_channel", channel); Set("_offeredModChannel", channel); Set("_lastChecked", DateTimeOffset.UtcNow);
            Check(await (Task<bool>)Call("CheckGameCompatibilityAsync", true)!, "prepared game is not supported");
            Call("RefreshStatus"); Call("SetActivePage", "home"); await Task.Delay(100); w.UpdateLayout();
            Check(Field<bool>("_patchInstalled") && Field<bool>("_selectedModStored"), "installed mod is not retained locally");
            Check(!Field<bool>("_settingsPending"), "preset requires manual Apply settings");
            Check(C<Button>("LaunchButton").IsEnabled, "ready preset cannot be launched");
            Check(!C<Button>("ApplySettingsButton").IsEnabled && !C<Button>("UpdateButton").IsEnabled, "preset still requests installation/apply/update");
            Snap("ready-to-launch", (FrameworkElement)w.Content);
            var dialog = (Window)Call("CreateCustomVoicesDialog")!; dialog.WindowStartupLocation = WindowStartupLocation.Manual; dialog.Left = -30000; dialog.Top = -30000; dialog.ShowActivated = false;
            dialog.Show(); await Task.Delay(100); Snap("selected-faction-languages", (FrameworkElement)dialog.Content); dialog.Close();
            Console.WriteLine($"INSTALLED PRESET UI PASS {checks}: actual copied mod, exact user voices, supported game, enabled Launch, no installation/update/apply required");
        }
        try
        {
            w.Show(); var task = w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(60) }; timer.Tick += (_, _) => frame.Continue = false;
            _ = task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false)); timer.Start(); Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Installed preset UI"); task.GetAwaiter().GetResult();
        }
        finally { w.Close(); }
    }
}

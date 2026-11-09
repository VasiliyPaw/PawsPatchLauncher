using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class FactionVoiceChecks
{
    internal static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated profile required");
        Directory.CreateDirectory(output);
        new SettingsStore().Save(new UserSettings { Language = language, Mod = GameMod.Vanilla, GameVoiceLanguage = "en", ModNoticeSeen = true });
        var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(ActivityStore.Root, "cache") }, null)
            { Width = 1440, Height = 960, Left = -30000, Top = -30000, ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        T C<T>(string name) => (T)w.FindName(name);
        var checks = 0;
        void Check(bool ok, string why) { if (!ok) throw new Exception("Faction voices UI: " + why); checks++; }
        IEnumerable<T> Descendants<T>(DependencyObject node) where T : DependencyObject
        {
            if (node is T item) yield return item;
            for (var i = 0; i < VisualTreeHelper.GetChildrenCount(node); i++)
                foreach (var child in Descendants<T>(VisualTreeHelper.GetChild(node, i))) yield return child;
        }
        object Choice(ComboBox combo, string code) => combo.Items.Cast<object>().First(x => x.GetType().GetProperty("Code")!.GetValue(x)?.ToString() == code);
        void Snap(string name, FrameworkElement element)
        {
            element.UpdateLayout();
            var visual = new DrawingVisual(); using (var dc = visual.RenderOpen()) dc.DrawRectangle(new VisualBrush(element), null, new Rect(element.RenderSize));
            var bitmap = new RenderTargetBitmap((int)Math.Ceiling(element.ActualWidth), (int)Math.Ceiling(element.ActualHeight), 96, 96, PixelFormats.Pbgra32); bitmap.Render(visual);
            var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(bitmap)); using var file = File.Create(Path.Combine(output, name + "-" + language + ".png")); png.Save(file);
        }
        async Task Scenario()
        {
            var channel = new ChannelManifest { Packages = [new PackageRelease { Id = "game-voice-ru" }] };
            Set("_channel", channel); Call("SetActivePage", "modules"); Call("SyncLanguageChoices");
            Check(w.FindName("CompareProfileButton") is null && typeof(MainWindow).GetMethod("CreateGameplayComparisonDialog", flags) is null, "separate comparison remains");
            var combo = C<ComboBox>("GameVoiceCombo"); var settings = Field<UserSettings>("_settings");
            Check(combo.Items.Count == 5, "custom is absent from speech choices");
            combo.SelectedItem = Choice(combo, "ru"); Set("_channel", channel);
            combo.SelectedItem = Choice(combo, "custom"); Set("_channel", channel); Call("SyncLanguageChoices");
            Check(CustomVoices.Groups.All(g => CustomVoices.Language(settings, g) == "ru"), "initial setup did not use the previous regular language");
            Check(C<Button>("CustomVoicesButton").IsVisible && C<Button>("CustomVoicesButton").IsEnabled, "gear is not available beside custom speech");
            Snap("custom-voice-choice", C<Border>("RussianModuleCard"));
            var window = (Window)Call("CreateCustomVoicesDialog")!;
            window.WindowStartupLocation = WindowStartupLocation.Manual; window.Left = -30000; window.Top = -30000; window.ShowActivated = false;
            window.Show(); await Task.Delay(120); window.UpdateLayout();
            Check(window.WindowStyle == WindowStyle.None, "dialog has the system title bar");
            var picks = Descendants<ComboBox>((DependencyObject)window.Content).ToArray();
            Check(picks.Length == 6 && picks.All(c => c.Items.Count == 4), "missing groups or unavailable languages");
            foreach (var (pick, code) in picks.Zip(new[] { "ru", "fr", "de", "en", "fr", "ru" })) pick.SelectedItem = Choice(pick, code);
            Snap("custom-voices", (FrameworkElement)window.Content);
            var save = Descendants<Button>((DependencyObject)window.Content).Single(b => b.Name == "SaveCustomVoices");
            Check(save.Content.ToString() == UiLanguages.Text(language, "Сохранить", "Save"), "untranslated Save");
            save.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(!window.IsVisible && settings.FactionVoiceLanguages["council"] == "fr", "saving did not commit the setup");
            var signature = CustomVoices.Signature(settings);
            Set("_channel", channel); combo.SelectedItem = Choice(combo, "en"); Set("_channel", channel); Call("SyncLanguageChoices");
            Check(!C<Button>("CustomVoicesButton").IsVisible, "gear remains on a regular voice choice");
            var loaded = new SettingsStore().Load(); loaded.GameVoiceLanguage = "custom";
            Check(CustomVoices.Signature(loaded) == signature, "saved inactive choices did not survive reloading");
            Set("_channel", channel); combo.SelectedItem = Choice(combo, "custom"); Set("_channel", channel); Call("SyncLanguageChoices");
            Check(CustomVoices.Signature(settings) == signature, "returning to custom reset choices");
            var cancelled = (Window)Call("CreateCustomVoicesDialog")!;
            cancelled.WindowStartupLocation = WindowStartupLocation.Manual; cancelled.Left = -30000; cancelled.Top = -30000; cancelled.ShowActivated = false; cancelled.Show();
            await Task.Delay(50); var draft = Descendants<ComboBox>((DependencyObject)cancelled.Content).First(); draft.SelectedItem = Choice(draft, "de"); cancelled.Close();
            Check(CustomVoices.Signature(settings) == signature, "closing a draft changed the setup");
            w.Width = 1050; w.Height = 680; await Task.Delay(50); w.UpdateLayout();
            var root = (FrameworkElement)w.Content; var gear = C<Button>("CustomVoicesButton");
            var bounds = gear.TransformToAncestor(root).TransformBounds(new Rect(gear.RenderSize));
            Check(bounds.Left >= 0 && bounds.Right <= w.ActualWidth && bounds.Bottom <= w.ActualHeight, "gear clipped at minimum launcher size");
            var selectedLabel = combo.SelectedItem.GetType().GetProperty("Label")!.GetValue(combo.SelectedItem)!.ToString();
            var labelMeasure = new TextBlock { Text = selectedLabel, FontFamily = combo.FontFamily, FontSize = combo.FontSize };
            labelMeasure.Measure(new Size(double.PositiveInfinity, double.PositiveInfinity));
            Check(combo.ActualWidth >= labelMeasure.DesiredSize.Width + 30, "selected custom label is clipped at minimum size");
            Snap("custom-voice-choice-min", C<Border>("RussianModuleCard"));
            Console.WriteLine($"FACTION VOICE UI PASS {checks} {language}: choice, themed dialog, draft/save, normal/custom switching and restart persistence");
        }
        try
        {
            w.Show(); var task = w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) }; timer.Tick += (_, _) => frame.Continue = false;
            _ = task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false)); timer.Start(); Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Faction voices UI"); task.GetAwaiter().GetResult();
        }
        finally { w.Close(); }
    }
}

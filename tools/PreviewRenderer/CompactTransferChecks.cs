using System.IO;
using System.Reflection;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class CompactTransferChecks
{
    internal static void Run(string language, string output)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated fixtures required.");
        new SettingsStore().Save(new UserSettings { ModNoticeSeen = true, Language = language });
        var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [] }, null)
            { Left = -32000, Top = -32000, Width = 1050, Height = 680, ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        T C<T>(string name) => (T)w.FindName(name);
        var count = 0;
        void Check(bool ok, string why) { count++; if (!ok) throw new Exception("Compact transfer: " + why); }
        async Task Layout(int delay = 280) { await Task.Delay(delay); await w.Dispatcher.InvokeAsync(() => { }, DispatcherPriority.ContextIdle); w.UpdateLayout(); }
        void Save(string name)
        {
            Directory.CreateDirectory(output); w.UpdateLayout();
            var bitmap = new RenderTargetBitmap((int)w.ActualWidth, (int)w.ActualHeight, 96, 96, PixelFormats.Pbgra32); bitmap.Render(w);
            var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(bitmap));
            using var stream = File.Create(Path.Combine(output, name + "-" + language + ".png")); png.Save(stream);
        }
        async Task Scenario()
        {
            Set("_gameRunningProbe", new Func<bool>(() => false));
            var detailsButton = C<Button>("OperationDetailsButton"); var expanded = C<Border>("OperationExpandedDetails");
            foreach (var width in new[] { 1050d, 1600d })
            foreach (var page in new[] { "home", "modules" })
            {
                w.Width = width; Call("SetActivePage", page); Call("SetBusy", true, "Загрузка компонента / Downloading component");
                var transfer = (IProgress<(long Received, long? Total)>)Call("TransferProgress", "Русская локализация — большой файл / Russian localization package")!;
                transfer.Report((50 * 1048576, 100 * 1048576)); await Layout();
                var card = C<Border>("OperationStatusPanel"); var compact = card.ActualHeight;
                Check(compact is > 40 and <= 68 && expanded.Visibility == Visibility.Collapsed, "initial card is not compact");
                Check(C<TextBlock>("TransferSummaryText").Text.Contains("50%") && C<TextBlock>("TransferSummaryText").Text.Contains(" / "), "compact size/percentage missing");
                Check(detailsButton.IsVisible && detailsButton.ActualWidth >= 22, "details button is not reachable");
                foreach (var caption in new[] { "Проверка", new string('W', 160), "Установка файлов" })
                {
                    Call("ShowWorking", new Func<string>(() => caption));
                    Call("SetTransferDetails", caption, true); C<Button>("CancelDownloadButton").Visibility = caption.Length > 30 ? Visibility.Visible : Visibility.Collapsed;
                    await Layout(30); Check(Math.Abs(card.ActualHeight - compact) < .5, "phase or cancel availability moves collapsed card");
                }
                Call("ShowWorking", new Func<string>(() => language == "ru" ? "Загружаем русскую локализацию" : "Downloading Russian localization"));
                Call("SetTransferDetails", language == "ru" ? "50,0 MB / 100,0 MB\n8,2 MB/с · осталось 00:06" : "50.0 MB / 100.0 MB\n8.2 MB/s · remaining 00:06", false);
                C<Button>("CancelDownloadButton").Visibility = Visibility.Visible;
                Save($"transfer-{page}-{width}-compact");
                detailsButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); await Layout();
                Check(expanded.Visibility == Visibility.Visible && Math.Abs(card.ActualHeight - compact - 84) < 1, "expanded panel has wrong height");
                Check(C<TextBlock>("TransferText").IsVisible && C<Button>("CancelDownloadButton").IsVisible, "expanded details/actions missing");
                Save($"transfer-{page}-{width}-expanded");
                for (var i = 0; i < 3; i++) { detailsButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent)); await Layout(35); }
                await Layout(); Check(expanded.Visibility == Visibility.Collapsed && Math.Abs(card.ActualHeight - compact) < .5, "rapid expand/collapse leaves a stale animation");
                Call("FinishTransfer"); await Layout(30);
                Check(C<TextBlock>("TransferSummaryText").Text.Contains("50%") && Math.Abs(card.ActualHeight - compact) < .5, "verification shifts layout or discards last measurement");
                Call("SetBusy", false, null); await Layout(30);
                Check(!detailsButton.IsVisible && C<ProgressBar>("OperationProgress").Visibility == Visibility.Collapsed, "idle card retains download controls");
            }
            var settings = Field<UserSettings>("_settings");
            var channel = new ChannelManifest { Packages = [new() { Id = "pure-fixes-data" }, new() { Id = "pure-fixes-runtime" }] };
            Set("_channel", channel); Set("_offeredModChannel", channel);
            Set("_compatibilityState", GameCompatibilityState.Unsupported); Set("_installedGameVersion", "1.3.71");
            foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
            {
                Call("CloseCompatibilityPopup"); settings.Mod = mod; GameMod.SetPawPatch(settings, false);
                Set("_compatibilityNoticeKey", mod); Set("_compatibilityPopupKey", mod);
                Call("SetActivePage", "modules"); Call("RenderCompatibility"); await Layout(30);
                Check(C<Border>("CompatibilityBanner").Visibility == Visibility.Visible, "disabled Paw's Patch removed the incompatible-game banner: " + mod);
                Check(C<Button>("PawCompatibilityButton").Visibility == Visibility.Visible && C<Button>("CoreHelpButton").Visibility == Visibility.Collapsed, "duplicate help or missing partial details: " + mod);
                C<Button>("PawCompatibilityButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                var popup = Field<Border>("_compatibilityPopup");
                for (var i = 0; i < 3; i++) { Call("RefreshGameLaunchState"); await Layout(70); }
                Check(ReferenceEquals(popup, Field<Border?>("_compatibilityPopup")), "details dialog closes on refresh: " + mod);
                Set("_compatibilityNoticeKey", mod + "|verified"); Call("RenderCompatibility");
                Check(ReferenceEquals(popup, Field<Border?>("_compatibilityPopup")), "fresh verification replaces the user's details dialog");
                if (mod == GameMod.Immortals) Save("immortals-partial-details");
                Call("CloseCompatibilityPopup"); Call("RenderCompatibility");
                Check(Field<Border?>("_compatibilityPopup") is null, "dismissed dialog reopens on the next tick");
            }
            Set("_compatibilityState", GameCompatibilityState.Supported); Call("RenderCompatibility");
            Check(C<Border>("CompatibilityBanner").Visibility == Visibility.Collapsed && C<Button>("CoreHelpButton").Visibility == Visibility.Visible, "supported game retained warning / lost normal help");
            Console.WriteLine($"COMPACT TRANSFER / COMPATIBILITY PASS {count} {language}");
        }
        try
        {
            w.Show(); var task = w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap(); var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) }; timer.Tick += (_, _) => frame.Continue = false;
            _ = task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false));
            timer.Start(); Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Compact transfer checks"); task.GetAwaiter().GetResult();
        }
        finally { w.Close(); }
    }
}

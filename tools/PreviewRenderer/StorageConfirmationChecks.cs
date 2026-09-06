using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class StorageConfirmationChecks
{
    internal static StoragePlan PreviewPlan => new([
        new("downloads", "preview-cache", 256L * 1024 * 1024, true, "preview"),
        new("backups", "preview-backups", 80L * 1024 * 1024, true, "preview"),
        new("originals", "protected-originals", 400L * 1024 * 1024, false, "preview")]);

    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Storage UI checks require --smoke-test.");
        var cacheRoot = Path.Combine(ActivityStore.Root, "cleanup-confirmation", Guid.NewGuid().ToString("N"));
        RemovalSafety.CheckNoLinks(cacheRoot);
        var configuration = new LauncherConfiguration { CacheRoot = cacheRoot, FeedUrls = [], BetaFeedUrls = [] };
        var w = new MainWindow(configuration, new FeedClient(configuration)) { Width = 1050, Height = 680,
            Left = -30000, Top = -30000, WindowStartupLocation = WindowStartupLocation.Manual, ShowActivated = false, ShowInTaskbar = false };
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Invoke(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T Element<T>(string name) => (T)w.FindName(name);
        Task<bool> Confirm(bool cache, bool backups) => (Task<bool>)Invoke("ConfirmStorageCleanupAsync", PreviewPlan, cache, backups)!;
        void Click(string name) => Element<Button>(name).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        var checks = 0;
        void Check(bool value, string message) { if (!value) throw new InvalidOperationException(message); checks++; }
        Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Invoke("ApplyLanguage"); Invoke("SetActivePage", "settings");
        w.Show(); w.UpdateLayout();
        async Task Scenario()
        {
            var before = Element<TextBlock>("OperationText").Text;
            var pending = Confirm(true, true); w.UpdateLayout();
            Check(!pending.IsCompleted && !Field<bool>("_busy"), "Cleanup prompt started an operation.");
            Check(!Element<Grid>("MainBody").IsEnabled && !Element<Grid>("TitleBar").IsEnabled, "Cleanup background is interactive.");
            Check(Element<Button>("ConfirmationCancelButton").IsDefault && !Element<Button>("ConfirmationDeleteButton").IsDefault, "Cleanup is the default action.");
            Check(Element<TextBlock>("ConfirmationTitleText").Text == (language == "ru" ? "Очистить устаревшие данные?" : "Clean up obsolete data?"), "Wrong cleanup title.");
            Check(Element<TextBlock>("ConfirmationPathText").Text.Split('\n').Length == 3, "Selected categories/total not shown.");
            Check(!Element<TextBlock>("ConfirmationPathText").Text.Contains("400"), "Protected data included in cleanup summary.");
            Check(Element<TextBlock>("ConfirmationPathText").Text.Contains("336"), "Wrong approved total.");
            Check(!await (Task<bool>)Invoke("CheckFeedAsync", true)!, "Feed check ran during cleanup confirmation.");
            Check(!await Confirm(true, false) && !pending.IsCompleted, "Duplicate prompt replaced active confirmation.");
            Click("ConfirmationCancelButton"); Check(!await pending, "Cancel accepted cleanup.");
            Check(Element<Grid>("MainBody").IsEnabled && Element<Border>("ConfirmationOverlay").Visibility == Visibility.Collapsed, "Cleanup cancellation left background locked.");
            Check(Element<TextBlock>("OperationText").Text == before, "Presentation-only confirmation changed operation status.");
            pending = Confirm(true, false);
            Check(Element<TextBlock>("ConfirmationPathText").Text.Split('\n').Length == 2 && !Element<TextBlock>("ConfirmationPathText").Text.Contains("80"), "Unselected backups included.");
            Check(!Element<TextBlock>("ConfirmationBodyText").Text.Contains(language == "ru" ? "нельзя восстановить" : "cannot be restored"), "Cache-only prompt warns about deleting unselected backups.");
            var escape = new KeyEventArgs(Keyboard.PrimaryDevice, PresentationSource.FromVisual(w), 0, Key.Escape) { RoutedEvent = Keyboard.PreviewKeyDownEvent };
            w.RaiseEvent(escape); Check(!await pending && escape.Handled, "Escape did not cancel cleanup.");
            pending = Confirm(false, true);
            Check(!Element<TextBlock>("ConfirmationPathText").Text.Contains("256"), "Unselected cache included.");
            Check(Element<TextBlock>("ConfirmationBodyText").Text.Contains(language == "ru" ? "нельзя восстановить" : "cannot be restored"), "Backup loss warning missing.");
            Click("ConfirmationCloseButton"); Check(!await pending, "X accepted cleanup.");
            pending = Confirm(true, true); w.Close(); Check(!await pending && w.IsLoaded, "Window close did not cancel cleanup safely.");
            pending = Confirm(true, true); Click("ConfirmationDeleteButton"); Check(await pending && !Field<bool>("_busy"), "Explicit presentation confirmation failed or executed cleanup.");
            Check(!await Confirm(false, false) && Element<Border>("ConfirmationOverlay").Visibility == Visibility.Collapsed, "Empty selection opened confirmation.");
            Set("_busy", true); Check(!await Confirm(true, true), "Busy operation admitted a prompt."); Set("_busy", false);

            // Exercise the real async handler against disposable cache files only.
            // Never close the user's game to enable this additional integration check.
            if ((bool)typeof(MainWindow).GetMethod("IsGameRunning", BindingFlags.Static | BindingFlags.NonPublic)!.Invoke(null, null)!)
            {
                Console.WriteLine("STORAGE HANDLER SKIPPED: user's game is running; presentation checks completed without touching it.");
                return;
            }
            string Write(string id, char hash)
            {
                var path = Path.Combine(cacheRoot, "downloads", id, "1", new string(hash, 64) + ".zip");
                RemovalSafety.CheckNoLinks(path); Directory.CreateDirectory(Path.GetDirectoryName(path)!);
                File.WriteAllText(path, "disposable cache fixture"); File.SetLastWriteTimeUtc(path, DateTime.UtcNow.AddDays(-20));
                return path;
            }
            var obsolete = Write("old", 'A'); var changed = Write("old", 'B'); var protectedLater = Write("protected", 'C');
            var unrelated = Path.Combine(cacheRoot, "user-note.txt"); File.WriteAllText(unrelated, "keep test sentinel");
            Set("_storagePlan", StorageMaintenance.Scan((StorageOptions)Invoke("GetStorageOptions")!));
            Field<CheckBox>("_cleanCache").IsChecked = true; Field<CheckBox>("_cleanBackups").IsChecked = false;
            async Task AwaitPrompt(Task operation)
            {
                while (Field<TaskCompletionSource<bool>?>("_confirmation") is null && !operation.IsCompleted) await Task.Delay(10);
                Check(!operation.IsCompleted && Field<TaskCompletionSource<bool>?>("_confirmation") is not null, "Real cleanup did not open themed confirmation.");
            }
            var cleaning = (Task)Invoke("CleanStorageAsync")!; await AwaitPrompt(cleaning);
            Check(!Field<bool>("_busy") && !Element<ProgressBar>("OperationProgress").IsIndeterminate, "Cleanup prompt left scan progress running.");
            Check(((Task)Invoke("CleanStorageAsync")!).IsCompleted, "Second cleanup started behind prompt.");
            Click("ConfirmationCancelButton"); await cleaning;
            Check(File.Exists(obsolete) && File.Exists(changed) && File.Exists(protectedLater), "Cancelled handler deleted files.");
            Check(!Field<bool>("_busy") && Element<TextBlock>("OperationText").Text.Contains(language == "ru" ? "Ничего не удалено" : "Nothing was deleted"), "Cancelled cleanup left wrong status.");
            cleaning = (Task)Invoke("CleanStorageAsync")!; await AwaitPrompt(cleaning);
            File.AppendAllText(changed, " modified after confirmation opened");
            Set("_channel", new ChannelManifest { Packages = [new PackageRelease { Id = "protected", Version = "1", Sha256 = new string('C', 64) }] });
            Click("ConfirmationDeleteButton"); await cleaning;
            Check(!File.Exists(obsolete), "Explicit cleanup did not remove approved disposable cache.");
            Check(File.Exists(changed) && File.Exists(protectedLater) && File.ReadAllText(unrelated) == "keep test sentinel", "Changed/protected/unrelated files were removed.");
            Check(!Field<bool>("_busy") && Element<Border>("ConfirmationOverlay").Visibility == Visibility.Collapsed, "Completed cleanup left busy/modal state.");
            Check(Element<TextBlock>("OperationText").Text.StartsWith(language == "ru" ? "Освобождено:" : "Reclaimed:"), "Successful cleanup status missing.");
            Field<CheckBox>("_cleanCache").IsChecked = false; Field<CheckBox>("_cleanBackups").IsChecked = true;
            await (Task)Invoke("CleanStorageAsync")!;
            Check(Element<Border>("ConfirmationOverlay").Visibility == Visibility.Collapsed && !Field<bool>("_busy"), "Empty category opened a prompt or stayed busy.");
            Check(Element<TextBlock>("OperationText").Text.Contains(language == "ru" ? "нет устаревших данных" : "No obsolete data"), "Empty category status missing.");
        }
        try
        {
            var task = w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame(); var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(20) };
            timer.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("Storage confirmation checks did not finish.");
            task.GetAwaiter().GetResult();
            Console.WriteLine($"STORAGE CONFIRMATION PASS {checks} {language}");
        }
        finally { w.Close(); }
    }
}

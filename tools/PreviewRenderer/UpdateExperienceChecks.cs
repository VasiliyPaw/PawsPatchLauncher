using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class UpdateExperienceChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated profile required.");
        var config = new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(ActivityStore.Root, "update-experience") };
        new SettingsStore().Save(new UserSettings { Language = language, ModNoticeSeen = true });
        var window = new MainWindow(config, new FeedClient(config));
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(window, value);
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(window, args);
        T C<T>(string name) => (T)window.FindName(name);
        var n = 0; void Check(bool ok, string why) { if (!ok) throw new Exception("Update experience: " + why); n++; }
        int Notices() => C<StackPanel>("ToastStack").Children.OfType<Border>().Count(p => p.Visibility == Visibility.Visible && !Motion.IsHiding(p));
        async Task Scenario()
        {
            var release = new LauncherRelease { Version = "99.0.0", Size = 123, Sha256 = new('A', 64), Urls = ["https://fixture.invalid/never-requested"] };
            var shutdowns = 0;
            Set("_finishLauncherRestart", (Action)(() => shutdowns++));
            foreach (var page in new[] { "home", "modules", "settings", "friends" })
            {
                Call("SetActivePage", page); Set("_pendingLauncherUpdate", release);
                var ready = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
                Set("_restartLauncher", (Func<Task>)(() => ready.Task));
                var restart = (Task<bool>)Call("InstallPendingLauncherUpdateAsync", true)!;
                for (var i = 0; i < 3; i++)
                {
                    Call("RefreshStatus");
                    Check(C<Border>("OperationStatusPanel").Visibility == Visibility.Collapsed
                        && C<ProgressBar>("OperationProgress").Visibility == Visibility.Collapsed,
                        "Main-window download strip flashed during restart handoff.");
                    await Task.Delay(25);
                }
                ready.SetResult(); Check(await restart, "Successful handoff did not finish.");
                Set("_launcherRestarting", false); Call("SetBusy", false, null);
            }
            Check(shutdowns == 4, "Handoff completion ran more than once.");
            Call("ClearToastStack"); Set("_pendingLauncherUpdate", release);
            Set("_restartLauncher", (Func<Task>)(() => Task.FromException(new IOException("Synthetic handoff failure."))));
            Check(!await (Task<bool>)Call("InstallPendingLauncherUpdateAsync", true)!, "Failed handoff claimed success.");
            Check(shutdowns == 4 && C<Border>("OperationStatusPanel").Visibility == Visibility.Visible && Notices() == 1,
                "Failed handoff closed the launcher, hid the error, or duplicated it.");
            Call("ClearToastStack");
            var denied = new UnauthorizedAccessException("Synthetic state-file contention.");
            Call("ShowError", denied);
            Check(Notices() == 1 && C<TextBlock>("ToastText").Text == (language == "ru" ? "Нет доступа к папке" : "Folder access denied"),
                "One install error produced duplicate notifications.");
            Call("ShowError", denied); Check(Notices() == 1, "Repeated error stacked a duplicate.");
            Call("ShowToast", (Func<string>)(() => "Independent notice"), false);
            Check(Notices() == 2, "Distinct notifications were merged.");
            Call("ShowError", denied); Check(Notices() == 2, "An archived identical error was duplicated.");
            var exceptionTypes = new[] { "GameAlreadyRunningException", "FrequencyUnavailableException" };
            foreach (var typeName in exceptionTypes)
            {
                Call("ClearToastStack");
                var type = typeof(MainWindow).GetNestedType(typeName, BindingFlags.NonPublic)!;
                var error = (Exception)Activator.CreateInstance(type, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                    null, typeName == "FrequencyUnavailableException" ? ["Synthetic unavailable frequency"] : [], null)!;
                Call("ShowError", error); Check(Notices() == 1, "Special-case error still notifies twice.");
            }
            Console.WriteLine($"UPDATE EXPERIENCE PASS {n} {language}: four pages, silent handoff, failed restart recovery, one error/one toast, archived duplicate coalescing.");
        }
        try
        {
            var dispatcher = window.Dispatcher; var task = dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame(); var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(15) };
            timer.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("Update experience fixture timed out.");
            task.GetAwaiter().GetResult();
        }
        finally { Set("_launcherRestarting", false); Set("_busy", false); window.Close(); }
    }
}

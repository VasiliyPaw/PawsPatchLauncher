using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class GameExitRecoveryChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest || ActivityStore.LocalTestProfile is not null)
            throw new InvalidOperationException("Disposable smoke profile required.");
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        var root = Path.Combine(ActivityStore.Root, "game-exit-fixture", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var recordPath = Path.Combine(ActivityStore.Root, "game-run.json");
        var settingsPath = Path.Combine(ActivityStore.Root, "settings.json");
        var oldRecord = File.Exists(recordPath) ? File.ReadAllText(recordPath) : null;
        var oldSettings = File.Exists(settingsPath) ? File.ReadAllText(settingsPath) : null;
        var windows = new List<MainWindow>();
        MainWindow Window(string name)
        {
            var game = Path.Combine(root, name); Directory.CreateDirectory(game);
            var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [], CacheRoot = Path.Combine(root, "cache") }, null);
            Set(w, "_game", new GameInstallation(game, Path.Combine(game, "k2.exe"), "fixture", "fixture"));
            ((PawsPatchLauncher.Localization)Field(w, "_text")!).SetLanguage(language);
            windows.Add(w); return w; // Deliberately never Show: exercise the real controller without a native window.
        }
        object? Field(MainWindow w, string name) => typeof(MainWindow).GetField(name, flags)!.GetValue(w);
        void Set(MainWindow w, string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        object? Call(MainWindow w, string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        int count = 0;
        void Check(bool ok, string why) { if (!ok) throw new InvalidOperationException("Game exit recovery: " + why); count++; }
        async Task Scenario()
        {
            foreach (var (code, reached) in new[] { (0, false), (0, true), (7, false), (unchecked((int)0xC0000005), true) })
            {
                var w = Window($"exit-{code}-{reached}");
                var start = new ProcessStartInfo("powershell.exe") { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden, RedirectStandardInput = true };
                start.ArgumentList.Add("-NoProfile"); start.ArgumentList.Add("-NonInteractive"); start.ArgumentList.Add("-Command");
                start.ArgumentList.Add("[Environment]::Exit([int][Console]::ReadLine())");
                using var process = Process.Start(start)!;
                Call(w, "BeginGameObservation", process, new InstallState());
                var run = (RunRecord)Field(w, "_observedRun")!;
                run.Started = DateTimeOffset.UtcNow.AddSeconds(-31); // Existing child-adoption grace period, without waiting 30 seconds.
                run.ReachedWindow = reached;
                await process.StandardInput.WriteLineAsync(code.ToString()); process.StandardInput.Close();
                await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10));
                await (Task)Call(w, "ObserveGameAsync")!;
                var recorded = ActivityStore.Read("game-run")!;
                Check(recorded.ExitCode == code && recorded.CleanExit == (code == 0), "Actual process code was classified using window duration.");
                Check(recorded.ReachedWindow == reached, "Exit handling fabricated readiness.");
                Check(((Border)Field(w, "_incidentCard")!).Visibility == (code == 0 ? Visibility.Collapsed : Visibility.Visible),
                    "Normal close shows recovery or a real failing exit is hidden.");
                Check(Field(w, "_observedRun") is null && !((DispatcherTimer)Field(w, "_gameTimer")!).IsEnabled, "Exited process remains observed.");
                Check(!File.Exists(Path.Combine(run.GameRoot, ".pawpatch", "last-working.json")), "Quick exit promoted an unverified working configuration.");
            }
            foreach (var code in new int?[] { 0, 7, null })
            {
                var w = Window("legacy-" + (code?.ToString() ?? "unknown"));
                var game = (GameInstallation)Field(w, "_game")!;
                ActivityStore.Save("game-run", new RunRecord { ProcessId = int.MaxValue, StartTicks = 1, CleanExit = false, ReachedWindow = false, ExitCode = code, GameRoot = game.Directory });
                await (Task)Call(w, "RecoverAndCheckRunsAsync")!;
                Check((Field(w, "_incident") is not null) == (code != 0), "Restart misclassified an old zero-code record.");
                Check(ActivityStore.Read("game-run")?.CleanExit == true, "Old processed exit was not acknowledged.");
                var again = Window("reopen-" + (code?.ToString() ?? "unknown"));
                await (Task)Call(again, "RecoverAndCheckRunsAsync")!;
                Check(Field(again, "_incident") is null, "Old processed exit reports repeatedly.");
            }
            Console.WriteLine($"GAME EXIT UI CONTROLLER PASS {count} {language}: real Windows exit codes, short window, legacy record, last-working guard, recovery presentation; no launcher/game window displayed");
        }
        try
        {
            var task = Dispatcher.CurrentDispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) };
            timer.Tick += (_, _) => frame.Continue = false;
            // A dispatcher captured from the UI thread also makes completion reliable after an asynchronous process wait.
            var dispatcher = Dispatcher.CurrentDispatcher;
            task.ContinueWith(_ => dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            timer.Start(); try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
            if (!task.IsCompleted) throw new TimeoutException("Game exit controller checks timed out.");
            task.GetAwaiter().GetResult();
        }
        finally
        {
            foreach (var w in windows) { Set(w, "_busy", false); w.Close(); }
            if (oldRecord is null) File.Delete(recordPath); else File.WriteAllText(recordPath, oldRecord);
            if (oldSettings is null) File.Delete(settingsPath); else File.WriteAllText(settingsPath, oldSettings);
        }
    }
}

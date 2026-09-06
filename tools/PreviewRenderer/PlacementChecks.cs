using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class PlacementChecks
{
    internal static void Run()
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Placement checks require --smoke-test.");
        var monitors = WindowPlacementPersistence.ReadMonitors();
        var target = monitors.First(m => m.Primary);
        var root = Path.Combine(ActivityStore.Root, "placement-fixture", Guid.NewGuid().ToString("N"));
        var store = new WindowPlacementStore(root);
        var windows = new List<MainWindow>();
        int checks = 0;
        void Check(bool value, string message) { if (!value) throw new InvalidOperationException(message); checks++; }
        MainWindow NewWindow()
        {
            var window = new MainWindow(null, null, store)
            { ShowActivated = false, ShowInTaskbar = false, Opacity = 0, IsHitTestVisible = false };
            windows.Add(window); return window;
        }
        void Pump(int ms = 180)
        {
            var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(ms) };
            timer.Tick += (_, _) => frame.Continue = false; timer.Start();
            try { Dispatcher.PushFrame(frame); } finally { timer.Stop(); }
        }
        try
        {
            Check(monitors.Count > 0 && monitors.All(m => m.WorkArea.IsValid), "Native monitor enumeration failed.");
            Check(monitors.Where(m => m.Id.Length > 0).Select(m => m.Id).Distinct(StringComparer.OrdinalIgnoreCase).Count() == monitors.Count(m => m.Id.Length > 0), "Active extended monitors have duplicate interface IDs.");
            Console.WriteLine($"PLACEMENT MONITORS: {monitors.Count}, interface IDs available for {monitors.Count(m => m.Id.Length > 0)}; model names are not used");
            var first = NewWindow();
            Check(first.WindowStartupLocation == WindowStartupLocation.CenterScreen, "Fresh install no longer uses normal centered default.");
            first.Show(); Pump();
            var baseline = WindowPlacementPersistence.Capture(first);
            Check(baseline.IsValid, "Native captured placement invalid.");
            first.Close();
            var saved = store.Read();
            Check(saved is not null && saved.NormalBounds == baseline.NormalBounds, "Accepted close did not persist exact native normal bounds.");
            var second = NewWindow();
            Check(second.WindowStartupLocation == WindowStartupLocation.Manual, "Saved placement still has random centering.");
            new WindowInteropHelper(second).EnsureHandle();
            Check(!second.IsVisible, "SourceInitialized restore displayed the window prematurely.");
            second.Show(); Pump();
            var restored = WindowPlacementPersistence.Capture(second);
            Check(restored.NormalBounds == baseline.NormalBounds && restored.MonitorId == baseline.MonitorId, $"Reopen moved/resized the window: {baseline.NormalBounds} -> {restored.NormalBounds}.");
            var previous = File.ReadAllText(Path.Combine(root, "window-placement.json"));
            System.ComponentModel.CancelEventHandler cancel = (_, e) => e.Cancel = true;
            second.Closing += cancel; second.Close();
            Check(second.IsLoaded && File.ReadAllText(Path.Combine(root, "window-placement.json")) == previous, "Cancelled close persisted placement.");
            second.Closing -= cancel;
            second.WindowState = WindowState.Maximized; Pump();
            Check(WindowPlacementPersistence.Capture(second).Maximized, "Maximized native state not captured.");
            second.Close();
            var third = NewWindow(); third.Show(); Pump();
            Check(third.WindowState == WindowState.Maximized, "Maximized window did not reopen maximized.");
            third.WindowState = WindowState.Normal; Pump();
            Check(WindowPlacementPersistence.Capture(third).NormalBounds == baseline.NormalBounds, "Maximize/reopen/restore lost previous normal size.");
            third.WindowState = WindowState.Minimized; Pump(); third.Close();
            var fourth = NewWindow(); fourth.Show(); Pump();
            Check(fourth.WindowState == WindowState.Normal, "Closed minimized-normal window reopened minimized.");
            fourth.WindowState = WindowState.Maximized; Pump(); fourth.WindowState = WindowState.Minimized; Pump(); fourth.Close();
            var fifth = NewWindow(); fifth.Show(); Pump();
            Check(fifth.WindowState == WindowState.Maximized, "Minimizing a maximized window lost its prior state.");
            fifth.Close();
            foreach (var screen in monitors)
            {
                store.Save(new SavedWindowPlacement
                {
                    MonitorId = screen.Id, DeviceName = screen.DeviceName, MonitorBounds = screen.Bounds,
                    WorkArea = screen.WorkArea, Dpi = 96,
                    NormalBounds = new(screen.WorkArea.Left + 16, screen.WorkArea.Top + 16,
                        screen.WorkArea.Left + (int)Math.Min(screen.WorkArea.Width - 16, 1250),
                        screen.WorkArea.Top + (int)Math.Min(screen.WorkArea.Height - 16, 850))
                });
                var probe = NewWindow(); probe.Show(); Pump();
                var placed = WindowPlacementPersistence.Capture(probe);
                Check(placed.DeviceName == screen.DeviceName && placed.MonitorId == screen.Id, "Native restore selected a different monitor.");
                probe.Close();
                var reopened = NewWindow(); reopened.Show(); Pump();
                var repeated = WindowPlacementPersistence.Capture(reopened);
                Check(repeated.NormalBounds == placed.NormalBounds && repeated.DeviceName == screen.DeviceName, "Repeated restore creeps or switches monitor.");
                reopened.WindowState = WindowState.Maximized; Pump(); reopened.Close();
                var maximized = NewWindow(); maximized.Show(); Pump();
                Check(maximized.WindowState == WindowState.Maximized && WindowPlacementPersistence.Capture(maximized).MonitorId == screen.Id,
                    "Maximized reopen lost its chosen monitor.");
                maximized.Close();
            }
            Check(store.Read()?.IsValid == true, "Final persisted state is invalid.");
            Console.WriteLine($"WINDOW PLACEMENT UI PASS {checks}: native save/reopen, hidden initialization, accepted/cancelled close, normal/maximized/minimized roundtrips; invisible isolated windows only");
        }
        finally { foreach (var window in windows.Where(w => w.IsLoaded)) window.Close(); }
    }
}

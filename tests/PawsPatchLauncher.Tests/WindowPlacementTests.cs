using System.Text.Json;
using PawsPatchLauncher;

internal static class WindowPlacementTests
{
    internal static int Run(string root)
    {
        int checks = 0;
        void Check(bool condition, string message) { if (!condition) throw new Exception(message); checks++; }
        var primary = new WindowMonitor("port-A", "DISPLAY1", new(0, 0, 2560, 1440), new(0, 0, 2560, 1400), true);
        var left = new WindowMonitor("same-model-port-B", "DISPLAY2", new(-1920, 0, 0, 1080), new(-1920, 0, 0, 1040), false);
        var above = new WindowMonitor("same-model-port-C", "DISPLAY3", new(0, -1440, 2560, 0), new(0, -1440, 2560, -40), false);
        WindowMonitor[] monitors = [primary, left, above];
        SavedWindowPlacement Saved(WindowMonitor m, WindowPixelRect rect) => new()
        { MonitorId = m.Id, DeviceName = m.DeviceName, MonitorBounds = m.Bounds, WorkArea = m.WorkArea, NormalBounds = rect };
        var saved = Saved(left, new(-1850, 45, -650, 845));
        var original = saved.NormalBounds;
        Check(saved.IsValid, "Valid negative coordinates rejected.");
        Check(WindowPlacementPolicy.FindMonitor(saved, monitors) == left, "Wrong screen for identical-model ports.");
        Check(WindowPlacementPolicy.RestoreBounds(saved, left, monitors, 96) == original, "Normal bounds changed on unchanged topology.");
        var reordered = new[] { above with { DeviceName = "DISPLAY2" }, primary, left with { DeviceName = "DISPLAY3" } };
        Check(WindowPlacementPolicy.FindMonitor(saved, reordered)?.Id == left.Id, "DISPLAY renumbering overrode monitor identity.");
        var moved = left with { Bounds = new(2560, 0, 4480, 1080), WorkArea = new(2560, 0, 4480, 1040) };
        var relocated = WindowPlacementPolicy.RestoreBounds(saved, moved, [primary, moved, above], 96);
        Check(relocated.Left == 2630 && relocated.Top == 45 && relocated.Width == 1200, "Same screen moved in desktop: relative placement lost.");
        Check(WindowPlacementPolicy.FindMonitor(saved, [primary, above]) == primary, "Disconnected screen fallback is wrong.");
        var fallback = WindowPlacementPolicy.RestoreBounds(saved, primary, [primary], 96);
        Check(fallback.Left >= 0 && fallback.Right <= primary.WorkArea.Right && fallback.Top >= 0 && fallback.Bottom <= 1400, "Disconnected screen leaves hidden controls.");
        var tiny = primary with { Bounds = new(0, 0, 800, 600), WorkArea = new(0, 40, 800, 600) };
        var compact = WindowPlacementPolicy.RestoreBounds(saved, tiny, [tiny], 96);
        Check(compact.Width == 800 && compact.Height == 560 && compact.Top == 40, "Small-screen fallback exceeds work area.");
        var topSaved = Saved(above, new(100, -1350, 1300, -550));
        Check(WindowPlacementPolicy.RestoreBounds(topSaved, above, monitors, 96) == topSaved.NormalBounds, "Screen above primary lost negative Y.");
        var large = primary with { Bounds = new(0, 0, 3840, 2160), WorkArea = new(0, 0, 3840, 2100) };
        var normal = Saved(primary, new(100, 100, 1300, 900));
        var scaled = WindowPlacementPolicy.RestoreBounds(normal, large, [large], 144);
        Check(scaled.Width == 1800 && scaled.Height == 1200, "150% scaling did not preserve logical size.");
        normal.Dpi = 144; normal.NormalBounds = scaled; normal.WorkArea = large.WorkArea; normal.MonitorBounds = large.Bounds;
        var downscaled = WindowPlacementPolicy.RestoreBounds(normal, primary, monitors, 96);
        Check(downscaled.Width == 1200 && downscaled.Height == 800, "Returning to 100% scaling changed logical size.");
        var spanning = Saved(primary, new(-500, 100, 1200, 950));
        Check(WindowPlacementPolicy.RestoreBounds(spanning, primary, monitors, 96) == spanning.NormalBounds, "Deliberate monitor-spanning window was moved.");
        var movedMaximized = Saved(left, new(100, 100, 1300, 900)); movedMaximized.Maximized = true;
        var movedRestore = WindowPlacementPolicy.RestoreBounds(movedMaximized, left, monitors, 96);
        Check(movedRestore.Right <= 0 && movedRestore.Left >= -1920, "Old normal bounds overrode maximized monitor identity.");
        var lost = Saved(primary, new(50000, 50000, 51200, 50800));
        var rescued = WindowPlacementPolicy.RestoreBounds(lost, primary, monitors, 96);
        Check(rescued.Right <= 2560 && rescued.Bottom <= 1400, "Off-screen saved caption was not rescued.");
        var taskbar = primary with { WorkArea = new(80, 48, 2560, 1440) };
        var barBounds = WindowPlacementPolicy.RestoreBounds(Saved(primary, new(0, 0, 1200, 800)), taskbar, [taskbar], 96);
        Check(barBounds.Left == 80 && barBounds.Top == 48, "Left/top taskbar not respected.");
        saved.MonitorId = "";
        Check(WindowPlacementPolicy.FindMonitor(saved, monitors) == left, "Missing interface ID broke GDI fallback.");
        Check(WindowPlacementPolicy.FindMonitor(saved, []) is null, "Empty monitor list did not fall back cleanly.");

        var directory = Path.Combine(root, "Окно лаунчера");
        var store = new WindowPlacementStore(directory);
        Check(store.Read() is null, "Fresh install has fabricated placement.");
        saved = Saved(left, original); saved.Maximized = true;
        store.Save(saved);
        var read = new WindowPlacementStore(directory).Read();
        Check(read is { Maximized: true } && read.NormalBounds == original && read.MonitorId == left.Id, "Persistence roundtrip lost monitor, size or state.");
        var path = Path.Combine(directory, "window-placement.json");
        var previous = File.ReadAllText(path);
        saved.Dpi = 0;
        try { store.Save(saved); throw new Exception("Invalid DPI was saved."); } catch (InvalidDataException) { checks++; }
        Check(File.ReadAllText(path) == previous, "Invalid write replaced last good placement.");
        saved.Dpi = 96;
        foreach (var bad in new[] { "{", "null", previous.Replace("\"schemaVersion\": 1", "\"schemaVersion\": 99"), new string('x', 16385) })
        {
            // JSON casing follows the shared source-generated options; use explicit future schema below as well.
            if (bad == previous) continue;
            File.WriteAllText(path, bad); Check(store.Read() is null, "Malformed/future/oversized placement accepted.");
        }
        saved.SchemaVersion = 99;
        File.WriteAllText(path, JsonSerializer.Serialize(saved, LauncherJsonContext.Default.SavedWindowPlacement));
        Check(store.Read() is null, "Future schema not ignored.");
        saved.SchemaVersion = 1; saved.NormalBounds = new(int.MinValue, 0, int.MaxValue, 800);
        Check(!saved.IsValid, "Overflow geometry accepted.");
        saved.NormalBounds = new(0, 0, 0, 800); Check(!saved.IsValid, "Zero width accepted.");
        saved.NormalBounds = original; saved.WorkArea = new(-2000, 0, 0, 1040); Check(!saved.IsValid, "Work area outside screen accepted.");
        var gameSettings = JsonSerializer.Serialize(new UserSettings(), LauncherJsonContext.Default.UserSettings);
        Check(!gameSettings.Contains("Monitor", StringComparison.OrdinalIgnoreCase) && !gameSettings.Contains("WindowPlacement", StringComparison.OrdinalIgnoreCase), "Placement leaked into game configuration.");
        Check(!Directory.GetFiles(directory).Any(f => f.EndsWith(".tmp")), "Atomic placement write left temporary file.");
        Console.WriteLine($"WINDOW PLACEMENT POLICY PASS {checks}: identical models/unique ports, renumbering, topology, negative/spanning bounds, DPI, taskbar, small screen, local persistence/corruption");
        return checks;
    }
}

using System.Text.Json;
using System.Text.Json.Serialization;

namespace PawsPatchLauncher;

public readonly record struct WindowPixelRect(int Left, int Top, int Right, int Bottom)
{
    [JsonIgnore] public long Width => (long)Right - Left;
    [JsonIgnore] public long Height => (long)Bottom - Top;
    [JsonIgnore] public bool IsValid => Width is > 0 and <= 100000 && Height is > 0 and <= 100000
        && Math.Abs((long)Left) <= 1000000 && Math.Abs((long)Top) <= 1000000;
}

public sealed class SavedWindowPlacement
{
    public int SchemaVersion { get; set; } = 1;
    public string MonitorId { get; set; } = "";
    public string DeviceName { get; set; } = "";
    public WindowPixelRect NormalBounds { get; set; }
    public WindowPixelRect MonitorBounds { get; set; }
    public WindowPixelRect WorkArea { get; set; }
    public uint Dpi { get; set; } = 96;
    public bool Maximized { get; set; }

    [JsonIgnore] public bool IsValid => SchemaVersion == 1 && NormalBounds.IsValid
        && MonitorBounds.IsValid && WorkArea.IsValid && Dpi is >= 48 and <= 768
        && MonitorId is { Length: <= 2048 } && DeviceName is { Length: <= 128 }
        && WorkArea.Left >= MonitorBounds.Left && WorkArea.Top >= MonitorBounds.Top
        && WorkArea.Right <= MonitorBounds.Right && WorkArea.Bottom <= MonitorBounds.Bottom;
}

public sealed record WindowMonitor(string Id, string DeviceName, WindowPixelRect Bounds, WindowPixelRect WorkArea, bool Primary);

/// <summary>Local UI state, independent of game settings, executable location and patch channel.</summary>
public sealed class WindowPlacementStore(string directory)
{
    private readonly string _path = Path.Combine(directory, "window-placement.json");

    public SavedWindowPlacement? Read()
    {
        try
        {
            var file = new FileInfo(_path);
            if (!file.Exists || file.Length > 16384) return null;
            var saved = JsonSerializer.Deserialize(File.ReadAllText(_path), LauncherJsonContext.Default.SavedWindowPlacement);
            return saved?.IsValid == true ? saved : null;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or JsonException or ArgumentException) { return null; }
    }

    public void Save(SavedWindowPlacement saved)
    {
        if (!saved.IsValid) throw new InvalidDataException("Invalid launcher window placement.");
        Directory.CreateDirectory(directory);
        var temporary = _path + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(saved, LauncherJsonContext.Default.SavedWindowPlacement));
        File.Move(temporary, _path, true);
    }
}

public static class WindowPlacementPolicy
{
    public static WindowMonitor? FindMonitor(SavedWindowPlacement saved, IReadOnlyList<WindowMonitor> monitors)
    {
        // Interface IDs distinguish even identical monitor models and survive DISPLAY1/2 renumbering.
        var identity = monitors.FirstOrDefault(m => !string.IsNullOrEmpty(saved.MonitorId)
            ? m.Id.Equals(saved.MonitorId, StringComparison.OrdinalIgnoreCase)
            : m.DeviceName.Equals(saved.DeviceName, StringComparison.OrdinalIgnoreCase));
        if (identity is not null) return identity;
        // Disconnected/reconnected topology: nearest remaining work area, with a deterministic primary tie-break.
        return monitors.OrderBy(m => DistanceSquared(saved.NormalBounds, m.WorkArea)).ThenByDescending(m => m.Primary).FirstOrDefault();
    }

    public static WindowPixelRect RestoreBounds(SavedWindowPlacement saved, WindowMonitor target,
        IReadOnlyList<WindowMonitor> monitors, uint dpi)
    {
        if (!saved.IsValid || dpi is < 48 or > 768 || !target.WorkArea.IsValid)
            throw new InvalidDataException("Invalid launcher window placement geometry.");
        var previous = saved.NormalBounds;
        if (saved.MonitorBounds == target.Bounds && saved.WorkArea == target.WorkArea && saved.Dpi == dpi
            && previous.Left < target.Bounds.Right && previous.Right > target.Bounds.Left
            && previous.Top < target.Bounds.Bottom && previous.Bottom > target.Bounds.Top
            && monitors.Any(m => CaptionVisible(previous, m.WorkArea, dpi)))
            return previous; // Preserve deliberate spanning and negative desktop coordinates exactly.

        var scale = dpi / (double)saved.Dpi;
        var width = (int)Math.Min(target.WorkArea.Width, Math.Max(1050 * dpi / 96d, previous.Width * scale));
        var height = (int)Math.Min(target.WorkArea.Height, Math.Max(680 * dpi / 96d, previous.Height * scale));
        var x = Relocate(previous.Left, previous.Width, saved.WorkArea.Left, saved.WorkArea.Width,
            target.WorkArea.Left, target.WorkArea.Width, width);
        var y = Relocate(previous.Top, previous.Height, saved.WorkArea.Top, saved.WorkArea.Height,
            target.WorkArea.Top, target.WorkArea.Height, height);
        return new(x, y, x + width, y + height);
    }

    private static int Relocate(int oldPosition, long oldSize, int oldStart, long oldSpace, int start, long space, int size)
    {
        var fraction = oldSpace > oldSize ? Math.Clamp((oldPosition - (double)oldStart) / (oldSpace - oldSize), 0, 1) : 0.5;
        return start + (int)Math.Round(fraction * (space - size));
    }

    private static bool CaptionVisible(WindowPixelRect bounds, WindowPixelRect work, uint dpi)
        => bounds.Top >= work.Top && bounds.Top + 32 * dpi / 96d <= work.Bottom
            && Math.Min(bounds.Right, work.Right) - (double)Math.Max(bounds.Left, work.Left) >= 160 * dpi / 96d;

    private static double DistanceSquared(WindowPixelRect rectangle, WindowPixelRect work)
    {
        double x = rectangle.Left + rectangle.Width / 2d, y = rectangle.Top + rectangle.Height / 2d;
        var dx = Math.Max(work.Left - x, Math.Max(0, x - work.Right));
        var dy = Math.Max(work.Top - y, Math.Max(0, y - work.Bottom));
        return dx * dx + dy * dy;
    }
}

using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace PawsPatchLauncher;

/// <summary>Uses native placement for restored bounds, including a maximized/minimized window.</summary>
public sealed class WindowPlacementPersistence
{
    private readonly Window _window;
    private readonly WindowPlacementStore _store;
    private readonly SavedWindowPlacement? _saved;
    private bool _shown;

    public WindowPlacementPersistence(Window window, WindowPlacementStore store)
    {
        _window = window; _store = store; _saved = store.Read();
        if (_saved is not null) window.WindowStartupLocation = WindowStartupLocation.Manual;
        window.SourceInitialized += (_, _) => Restore();
        window.ContentRendered += (_, _) => _shown = true;
    }

    public void SaveOnAcceptedClose()
    {
        if (!_shown) return;
        try { _store.Save(Capture(_window)); }
        catch (Exception error) { ActivityStore.Log(error); } // UI persistence must never prevent closing.
    }

    private void Restore()
    {
        if (_saved is null) return;
        try
        {
            var handle = new WindowInteropHelper(_window).Handle;
            var monitors = ReadMonitors();
            var target = WindowPlacementPolicy.FindMonitor(_saved, monitors);
            if (target is null) return;
            // Move the still-hidden HWND to the target first. Then ask that HWND for its effective DPI;
            // do not guess monitor scaling or mix WPF DIPs with native desktop coordinates.
            ApplyBounds(handle, target, WindowPlacementPolicy.RestoreBounds(_saved, target, monitors, _saved.Dpi));
            var dpi = GetDpiForWindow(handle);
            if (dpi == 0) dpi = 96;
            _window.MinWidth = Math.Min(1050, target.WorkArea.Width * 96d / dpi);
            _window.MinHeight = Math.Min(680, target.WorkArea.Height * 96d / dpi);
            ApplyBounds(handle, target, WindowPlacementPolicy.RestoreBounds(_saved, target, monitors, dpi));
            if (_saved.Maximized) _window.WindowState = WindowState.Maximized;
        }
        catch (Exception error) { ActivityStore.Log(error); } // Corrupt/unavailable geometry falls back to a normal window.
    }

    private static void ApplyBounds(IntPtr handle, WindowMonitor monitor, WindowPixelRect screen)
    {
        // WINDOWPLACEMENT is in workspace coordinates, not screen coordinates. Convert exactly once;
        // otherwise a top/left taskbar makes the window creep on every restart.
        int offsetX = monitor.WorkArea.Left - monitor.Bounds.Left, offsetY = monitor.WorkArea.Top - monitor.Bounds.Top;
        var placement = new NativePlacement
        {
            Length = Marshal.SizeOf<NativePlacement>(), ShowCommand = 0, // SW_HIDE: SourceInitialized precedes Show.
            MinPosition = new(-1, -1), MaxPosition = new(-1, -1),
            NormalPosition = new(screen.Left - offsetX, screen.Top - offsetY, screen.Right - offsetX, screen.Bottom - offsetY)
        };
        if (!SetWindowPlacement(handle, ref placement)) throw new Win32Exception(Marshal.GetLastWin32Error());
    }

    public static SavedWindowPlacement Capture(Window window)
    {
        var handle = new WindowInteropHelper(window).Handle;
        var placement = new NativePlacement { Length = Marshal.SizeOf<NativePlacement>() };
        if (!GetWindowPlacement(handle, ref placement)) throw new Win32Exception(Marshal.GetLastWin32Error());
        var monitor = ReadMonitor(MonitorFromWindow(handle, 2));
        int offsetX = monitor.WorkArea.Left - monitor.Bounds.Left, offsetY = monitor.WorkArea.Top - monitor.Bounds.Top;
        var bounds = placement.NormalPosition;
        var dpi = GetDpiForWindow(handle);
        return new()
        {
            MonitorId = monitor.Id, DeviceName = monitor.DeviceName, MonitorBounds = monitor.Bounds,
            WorkArea = monitor.WorkArea, Dpi = dpi == 0 ? 96 : dpi,
            NormalBounds = new(bounds.Left + offsetX, bounds.Top + offsetY, bounds.Right + offsetX, bounds.Bottom + offsetY),
            // WPF_RESTORETOMAXIMIZED preserves the normal/maximized state from before minimizing.
            Maximized = placement.ShowCommand == 3 || (placement.ShowCommand == 2 && (placement.Flags & 2) != 0)
        };
    }

    public static IReadOnlyList<WindowMonitor> ReadMonitors()
    {
        var result = new List<WindowMonitor>();
        MonitorEnum callback = (IntPtr monitor, IntPtr _, ref NativeRect bounds, IntPtr data) =>
        {
            result.Add(ReadMonitor(monitor)); return true;
        };
        if (!EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero, callback, IntPtr.Zero)) throw new Win32Exception(Marshal.GetLastWin32Error());
        return result;
    }

    private static WindowMonitor ReadMonitor(IntPtr handle)
    {
        var info = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
        if (!GetMonitorInfo(handle, ref info)) throw new Win32Exception(Marshal.GetLastWin32Error());
        string id = "";
        for (uint index = 0; index < 32; index++)
        {
            var device = new DisplayDevice { Size = Marshal.SizeOf<DisplayDevice>() };
            if (!EnumDisplayDevices(info.DeviceName, index, ref device, 1)) break;
            if ((device.Flags & 1) != 0 && !string.IsNullOrWhiteSpace(device.DeviceId)) { id = device.DeviceId; break; }
        }
        return new(id, info.DeviceName, info.Bounds.ToPixels(), info.WorkArea.ToPixels(), (info.Flags & 1) != 0);
    }

    [StructLayout(LayoutKind.Sequential)] private struct NativePoint(int x, int y) { public int X = x, Y = y; }
    [StructLayout(LayoutKind.Sequential)] private struct NativeRect(int left, int top, int right, int bottom)
    {
        public int Left = left, Top = top, Right = right, Bottom = bottom;
        public readonly WindowPixelRect ToPixels() => new(Left, Top, Right, Bottom);
    }
    [StructLayout(LayoutKind.Sequential)] private struct NativePlacement
    {
        public int Length, Flags, ShowCommand;
        public NativePoint MinPosition, MaxPosition;
        public NativeRect NormalPosition;
    }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] private struct MonitorInfo
    {
        public int Size; public NativeRect Bounds, WorkArea; public uint Flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string DeviceName;
    }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] private struct DisplayDevice
    {
        public int Size;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string DeviceName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string Description;
        public uint Flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceId;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceKey;
    }
    private delegate bool MonitorEnum(IntPtr monitor, IntPtr hdc, ref NativeRect bounds, IntPtr data);
    [DllImport("user32.dll", SetLastError = true)] private static extern bool EnumDisplayMonitors(IntPtr hdc, IntPtr clip, MonitorEnum callback, IntPtr data);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern bool EnumDisplayDevices(string adapter, uint index, ref DisplayDevice device, uint flags);
    [DllImport("user32.dll")] private static extern IntPtr MonitorFromWindow(IntPtr window, uint flags);
    [DllImport("user32.dll")] private static extern uint GetDpiForWindow(IntPtr window);
    [DllImport("user32.dll", SetLastError = true)] private static extern bool GetWindowPlacement(IntPtr window, ref NativePlacement placement);
    [DllImport("user32.dll", SetLastError = true)] private static extern bool SetWindowPlacement(IntPtr window, ref NativePlacement placement);
}

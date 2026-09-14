using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace PawsPatchLauncher;

// A borderless maximized HWND otherwise includes the taskbar area in its client layout.
internal sealed class WindowWorkArea
{
    private readonly Window _window;
    private HwndSource? _source;

    public WindowWorkArea(Window window)
    {
        _window = window;
        window.SourceInitialized += (_, _) =>
        {
            _source = HwndSource.FromHwnd(new WindowInteropHelper(window).Handle);
            _source?.AddHook(WindowProc);
        };
        window.Closed += (_, _) => { _source?.RemoveHook(WindowProc); _source = null; };
    }

    private IntPtr WindowProc(IntPtr hwnd, int message, IntPtr wparam, IntPtr lparam, ref bool handled)
    {
        if (message != 0x0024 || lparam == IntPtr.Zero) return IntPtr.Zero; // WM_GETMINMAXINFO
        var monitor = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
        if (!GetMonitorInfo(MonitorFromWindow(hwnd, 2), ref monitor)) return IntPtr.Zero;
        var limits = Marshal.PtrToStructure<MinMaxInfo>(lparam);
        limits.MaxPosition = new(monitor.Work.Left - monitor.Bounds.Left, monitor.Work.Top - monitor.Bounds.Top);
        limits.MaxSize = new(monitor.Work.Right - monitor.Work.Left, monitor.Work.Bottom - monitor.Work.Top);
        var scale = Math.Max(96u, GetDpiForWindow(hwnd)) / 96d;
        limits.MinTrackSize = new(Math.Min(limits.MaxSize.X, (int)Math.Ceiling(_window.MinWidth * scale)),
            Math.Min(limits.MaxSize.Y, (int)Math.Ceiling(_window.MinHeight * scale)));
        Marshal.StructureToPtr(limits, lparam, false);
        handled = true;
        return IntPtr.Zero;
    }

    [StructLayout(LayoutKind.Sequential)] private struct Point(int x, int y) { public int X = x, Y = y; }
    [StructLayout(LayoutKind.Sequential)] private struct Rect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] private struct MonitorInfo { public int Size; public Rect Bounds, Work; public uint Flags; }
    [StructLayout(LayoutKind.Sequential)] private struct MinMaxInfo { public Point Reserved, MaxSize, MaxPosition, MinTrackSize, MaxTrackSize; }
    [DllImport("user32.dll")] private static extern IntPtr MonitorFromWindow(IntPtr hwnd, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);
    [DllImport("user32.dll")] private static extern uint GetDpiForWindow(IntPtr hwnd);
}

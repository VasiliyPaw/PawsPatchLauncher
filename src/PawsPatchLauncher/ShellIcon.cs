using System.Runtime.InteropServices;

namespace PawsPatchLauncher;

internal static class ShellIcon
{
    // Notify only our executable after it may have been replaced by the updater.
    // Do not invalidate the system-wide icon cache or touch pinned shortcuts.
    public static void RefreshExecutable()
    {
        var path = Environment.ProcessPath;
        if (string.IsNullOrEmpty(path) || path.Length >= 260 || !path.EndsWith(".exe", StringComparison.OrdinalIgnoreCase)) return;
        SHChangeNotify(0x00002000, 0x00002005, path, IntPtr.Zero); // UPDATEITEM, PATHW | FLUSHNOWAIT
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, ExactSpelling = true)]
    private static extern void SHChangeNotify(int eventId, uint flags, string item, IntPtr unused);
}

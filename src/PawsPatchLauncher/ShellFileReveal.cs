using System.Runtime.InteropServices;

namespace PawsPatchLauncher;

public static class ShellFileReveal
{
    // Native item selection handles Unicode, spaces and commas without command-line parsing.
    // Parsing runs off the UI thread (it may involve a slow disk or Shell extension).
    public static Task ShowAsync(string archive) => Task.Run(() =>
    {
        var path = DiagnosticArchiveHistory.NormalizePath(archive) ?? throw new IOException("Invalid archive path.");
        if (!File.Exists(path)) throw new FileNotFoundException("Diagnostic archive not found.", path);
        Marshal.ThrowExceptionForHR(CoInitializeEx(IntPtr.Zero, 0));
        IntPtr item = IntPtr.Zero;
        try
        {
            Marshal.ThrowExceptionForHR(SHParseDisplayName(path, IntPtr.Zero, out item, 0, out _));
            Marshal.ThrowExceptionForHR(SHOpenFolderAndSelectItems(item, 0, IntPtr.Zero, 0));
        }
        finally
        {
            if (item != IntPtr.Zero) Marshal.FreeCoTaskMem(item);
            CoUninitialize();
        }
    });

    [DllImport("ole32.dll")] private static extern int CoInitializeEx(IntPtr reserved, uint mode);
    [DllImport("ole32.dll")] private static extern void CoUninitialize();
    [DllImport("shell32.dll", CharSet = CharSet.Unicode)] private static extern int SHParseDisplayName(string name, IntPtr bindingContext, out IntPtr item, uint attributes, out uint returnedAttributes);
    [DllImport("shell32.dll")] private static extern int SHOpenFolderAndSelectItems(IntPtr item, uint count, IntPtr children, uint flags);
}

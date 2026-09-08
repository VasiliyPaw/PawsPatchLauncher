using System.ComponentModel;
using System.Diagnostics;

namespace PawsPatchLauncher;

public static class GameProcessExit
{
    // Keep a handle while an adopted (helper-launched) game is alive. Otherwise
    // Process.ExitCode may be unavailable once Windows removes the process.
    public static void RetainHandle(Process process)
    {
        try { _ = process.Handle; }
        catch (Exception error) when (error is InvalidOperationException or Win32Exception or NotSupportedException) { }
    }

    public static int? ReadCode(Process process) => ReadCode(() => process.ExitCode);

    public static int? ReadCode(Func<int> read)
    {
        try { return read(); }
        catch (Exception error) when (error is InvalidOperationException or Win32Exception or NotSupportedException) { return null; }
    }
}

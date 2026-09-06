using System.Runtime.InteropServices;

namespace PawsPatchLauncher;

/// <summary>Opt-in for automation processes only; never a global Windows setting.</summary>
public static class TestProcessErrorMode
{
    private const uint FailCriticalErrors = 0x0001;
    private const uint NoFaultErrorBox = 0x0002;

    public static void Enable()
    {
        if (!OperatingSystem.IsWindows()) return;
        // Preserve inherited flags. Do not suppress exceptions or repair memory faults.
        // The runner must retain the process exit code/log instead of a WER popup.
        var required = GetErrorMode() | FailCriticalErrors | NoFaultErrorBox;
        SetErrorMode(required);
        if ((GetErrorMode() & required) != required)
            throw new InvalidOperationException("Cannot enable noninteractive test error reporting.");
    }

    [DllImport("kernel32.dll", ExactSpelling = true)]
    private static extern uint GetErrorMode();

    [DllImport("kernel32.dll", ExactSpelling = true)]
    private static extern uint SetErrorMode(uint mode);
}

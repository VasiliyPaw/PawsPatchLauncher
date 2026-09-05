using System.Diagnostics;
using System.Reflection;
using System.Text;

namespace PawsPatchLauncher;

public static class SelfUpdater
{
    public static Version CurrentVersion
        => Assembly.GetExecutingAssembly().GetName().Version ?? new Version(0, 0, 0);

    public static bool IsNewer(string candidate)
        => Version.TryParse(candidate, out var parsed) && parsed > CurrentVersion;

    public static void ScheduleReplacement(string downloadedExecutable)
    {
        var current = Environment.ProcessPath ?? throw new InvalidOperationException("The launcher executable path is unavailable.");
        if (!File.Exists(downloadedExecutable)) throw new FileNotFoundException("The downloaded launcher is missing.", downloadedExecutable);
        var currentDirectory = Path.GetDirectoryName(current) ?? throw new InvalidOperationException("The launcher directory is unavailable.");
        var staged = Path.Combine(currentDirectory, Path.GetFileName(current) + ".new");
        File.Copy(downloadedExecutable, staged, true);

        var pid = Environment.ProcessId;
        var script = Path.Combine(Path.GetTempPath(), $"PawsPatchLauncher-Update-{Guid.NewGuid():N}.cmd");
        var lines = new[]
        {
            "@echo off",
            "setlocal",
            ":wait_for_launcher",
            $"tasklist /FI \"PID eq {pid}\" 2>NUL | find \"{pid}\" >NUL",
            "if not errorlevel 1 (",
            "  timeout /t 1 /nobreak >NUL",
            "  goto wait_for_launcher",
            ")",
            $"move /Y \"{staged}\" \"{current}\" >NUL",
            "if errorlevel 1 exit /b 1",
            $"start \"\" \"{current}\"",
            "del \"%~f0\""
        };
        File.WriteAllLines(script, lines, new UTF8Encoding(false));
        Process.Start(new ProcessStartInfo("cmd.exe", $"/d /c \"{script}\"")
        {
            CreateNoWindow = true,
            UseShellExecute = false,
            WindowStyle = ProcessWindowStyle.Hidden
        });
    }
}


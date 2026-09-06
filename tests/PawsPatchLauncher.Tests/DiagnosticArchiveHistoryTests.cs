using System.IO.Compression;
using System.Text.Json;
using PawsPatchLauncher;

internal static class DiagnosticArchiveHistoryTests
{
    internal static int Run(string root)
    {
        var directory = Path.Combine(root, "archive-history"); Directory.CreateDirectory(directory);
        var history = new DiagnosticArchiveHistory(directory);
        var metadata = Path.Combine(directory, "last-diagnostic-archive.json");
        int count = 0;
        void Check(bool value, string message) { if (!value) throw new Exception(message); count++; }
        Check(history.Read() is null && !DiagnosticArchiveHistory.Exists(null), "Empty history is available.");
        foreach (var bad in new[] { "relative.zip", "https://example.invalid/file.zip", @"C:\fake.exe", "C:\\bad\0.zip", @"\\.\device.zip", @"C:\file.zip:stream.zip" })
            Check(DiagnosticArchiveHistory.NormalizePath(bad) is null, "Unsafe archive reference accepted: " + bad);
        var first = Path.Combine(directory, "Архив друга, проверка 1.zip");
        using (var zip = ZipFile.Open(first, ZipArchiveMode.Create)) zip.CreateEntry("synthetic.txt");
        var reference = history.RecordCompleted(first);
        Check(DiagnosticArchiveHistory.Exists(reference) && reference.CreatedAtUtc > DateTimeOffset.UtcNow.AddMinutes(-1), "Completed archive not recorded.");
        var reloaded = new DiagnosticArchiveHistory(directory).Read();
        Check(reloaded?.Path == first && reloaded.CreatedAtUtc == reference.CreatedAtUtc, "History did not survive reload / Unicode path lost.");
        var second = Path.Combine(directory, "latest.zip");
        using (var zip = ZipFile.Open(second, ZipArchiveMode.Create)) zip.CreateEntry("second.txt");
        history.RecordCompleted(second);
        Check(new DiagnosticArchiveHistory(directory).Read()?.Path == second, "New archive did not replace previous reference.");
        var saved = File.ReadAllText(metadata);
        try { history.RecordCompleted(Path.Combine(directory, "partial-missing.zip")); throw new Exception("Expected missing archive failure."); }
        catch (FileNotFoundException) { Check(File.ReadAllText(metadata) == saved, "Failed creation replaced successful reference."); }
        using (var locked = new FileStream(metadata, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            try { history.RecordCompleted(first); throw new Exception("Expected persistence failure."); }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException) { count++; }
        }
        Check(File.ReadAllText(metadata) == saved && !Directory.EnumerateFiles(directory, "*.tmp").Any(), "Failed save damaged previous reference or left temp files.");
        var moved = second + ".moved"; File.Move(second, moved);
        Check(!DiagnosticArchiveHistory.Exists(history.Read()), "Moved archive is still available.");
        File.Move(moved, second);
        Check(DiagnosticArchiveHistory.Exists(history.Read()), "Restored archive did not become available.");
        Check(!JsonSerializer.Serialize(new UserSettings()).Contains("DiagnosticArchive", StringComparison.OrdinalIgnoreCase), "Archive path leaked into game/shared settings.");
        File.WriteAllText(metadata, "{ broken"); Check(history.Read() is null, "Corrupt history crashed or was accepted.");
        File.WriteAllText(metadata, JsonSerializer.Serialize(new DiagnosticArchiveReference { SchemaVersion = 99, Path = first }, LauncherJsonContext.Default.DiagnosticArchiveReference));
        Check(history.Read() is null, "Unknown history schema accepted.");
        File.WriteAllText(metadata, new string('x', 40000)); Check(history.Read() is null, "Oversized history accepted.");
        Console.WriteLine($"DIAGNOSTICS HISTORY PASS {count}: persistence, Unicode, latest success, failed write, moved/restored files, malformed references, isolated settings");
        return count;
    }
}

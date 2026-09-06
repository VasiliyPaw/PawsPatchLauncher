using System.Text.Json;

namespace PawsPatchLauncher;

public sealed class DiagnosticArchiveReference
{
    public int SchemaVersion { get; set; } = 1;
    public string Path { get; set; } = "";
    public DateTimeOffset CreatedAtUtc { get; set; }
}

/// <summary>Local launcher history, deliberately separate from game/shared configuration.</summary>
public sealed class DiagnosticArchiveHistory(string directory)
{
    private readonly string _path = System.IO.Path.Combine(directory, "last-diagnostic-archive.json");

    public DiagnosticArchiveReference? Read()
    {
        try
        {
            var file = new FileInfo(_path);
            if (!file.Exists || file.Length > 32768) return null;
            var record = JsonSerializer.Deserialize(File.ReadAllText(_path), LauncherJsonContext.Default.DiagnosticArchiveReference);
            if (record is not { SchemaVersion: 1 } || NormalizePath(record.Path) is null) return null;
            return record;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or JsonException or ArgumentException) { return null; }
    }

    public DiagnosticArchiveReference RecordCompleted(string archive)
    {
        var record = CreateReference(archive);
        Save(record);
        return record;
    }

    public static DiagnosticArchiveReference CreateReference(string archive)
    {
        var path = NormalizePath(archive) ?? throw new IOException("Invalid diagnostic archive path.");
        if (!File.Exists(path)) throw new FileNotFoundException("Diagnostic archive was not created.", path);
        return new DiagnosticArchiveReference { Path = path, CreatedAtUtc = DateTimeOffset.UtcNow };
    }

    public void Save(DiagnosticArchiveReference record)
    {
        if (!Exists(record)) throw new FileNotFoundException("Diagnostic archive was not created.", record.Path);
        Directory.CreateDirectory(directory);
        var temporary = _path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            File.WriteAllText(temporary, JsonSerializer.Serialize(record, LauncherJsonContext.Default.DiagnosticArchiveReference));
            File.Move(temporary, _path, true);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    public static bool Exists(DiagnosticArchiveReference? record)
        => record is not null && NormalizePath(record.Path) is { } path && File.Exists(path);

    public static string? NormalizePath(string? path)
    {
        if (string.IsNullOrWhiteSpace(path) || path.IndexOfAny(['\0', '\r', '\n', '"']) >= 0) return null;
        try
        {
            if (!System.IO.Path.IsPathFullyQualified(path) || !System.IO.Path.GetExtension(path).Equals(".zip", StringComparison.OrdinalIgnoreCase)) return null;
            // A file reference only, never a URL, Shell namespace command or NT device path.
            if (path.StartsWith(@"\\?\", StringComparison.Ordinal) || path.StartsWith(@"\\.\", StringComparison.Ordinal)) return null;
            var full = System.IO.Path.GetFullPath(path);
            return full.IndexOf(':', full.StartsWith(@"\\", StringComparison.Ordinal) ? 0 : 2) >= 0 ? null : full;
        }
        catch (Exception e) when (e is ArgumentException or NotSupportedException or PathTooLongException) { return null; }
    }
}

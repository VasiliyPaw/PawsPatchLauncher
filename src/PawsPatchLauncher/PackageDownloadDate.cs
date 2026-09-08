using System.Globalization;

namespace PawsPatchLauncher;

/// <summary>Local provenance of a verified archive, never inferred from release or file timestamps.</summary>
public static class PackageDownloadDate
{
    public static Task RecordAsync(string archive, CancellationToken ct = default) =>
        CryptoAndIO.AtomicWriteTextAsync(archive + ".downloaded-at", DateTimeOffset.UtcNow.ToString("O"), ct);

    public static DateTimeOffset? Read(string archive)
    {
        try
        {
            var path = archive + ".downloaded-at";
            if (!File.Exists(path) || new FileInfo(path).Length > 128) return null;
            return DateTimeOffset.TryParseExact(File.ReadAllText(path), "O", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var timestamp) && timestamp <= DateTimeOffset.UtcNow ? timestamp : null;
        }
        catch (IOException) { return null; }
        catch (UnauthorizedAccessException) { return null; }
    }
}

using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Text.Json;

namespace PawsPatchLauncher;

public static class DiagnosticsCollector
{
    private static void CopyLauncherDiagnostics(string staging)
    {
        var copied = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var name in new[] { "launcher-errors.log", "self-update.log", "launcher-run.json", "game-run.json", "failed-launcher-sha256.txt", "update-rollback.txt" })
        {
            var file = Path.Combine(ActivityStore.Root, name);
            if (File.Exists(file)) CopyOne(file, Path.Combine(staging, "launcher", name), copied);
        }
    }

    public static Task<string> CreateLauncherOnlyAsync(string destination)
    {
        var staging = Path.Combine(Path.GetTempPath(), "PawsPatchDiagnostics", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try
        {
            CopyLauncherDiagnostics(staging);
            ZipFile.CreateFromDirectory(staging, destination, CompressionLevel.SmallestSize, false);
            return Task.FromResult(destination);
        }
        finally { Directory.Delete(staging, true); }
    }
    private static readonly string[] RootPatterns =
    [
        "log*.log", "ART_log*.log", "SAI_log*.log", "*.dmp", "paws_sync_continue_status.txt"
    ];

    public static async Task<string> CreateAsync(
        string destination,
        GameInstallation game,
        UserSettings settings,
        InstallState state,
        IReadOnlyCollection<string> verificationErrors,
        CancellationToken cancellationToken = default)
    {
        var staging = Path.Combine(Path.GetTempPath(), "PawsPatchDiagnostics", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try
        {
            var report = BuildReport(game, settings, state, verificationErrors);
            await WriteTextAsync(staging, "launcher-report.txt", report, cancellationToken);
            await WriteTextAsync(staging, "install-state.json",
                JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState), cancellationToken);

            var copied = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            CopyLauncherDiagnostics(staging);
            foreach (var name in new[] { "state.json", "last-working.json", "rollback.txt" })
            {
                var file = Path.Combine(game.Directory, ".pawpatch", name);
                if (File.Exists(file)) CopyOne(file, Path.Combine(staging, "launcher", name), copied);
            }
            foreach (var pattern in RootPatterns)
                CopyMatches(game.Directory, pattern, Path.Combine(staging, "logs", "game-root"), copied);

            CopyTree(Path.Combine(game.Directory, "data", "synclogs"), Path.Combine(staging, "logs", "game-synclogs"), copied);

            var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
            CopyDiagnosticsTree(Path.Combine(documents, "Kohan2"), Path.Combine(staging, "logs", "documents-kohan2"), copied);
            CopyDiagnosticsTree(Path.Combine(documents, "Kohan II"), Path.Combine(staging, "logs", "documents-kohan-ii"), copied);

            await WriteHashManifestAsync(staging, cancellationToken);
            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            if (File.Exists(destination)) File.Delete(destination);
            ZipFile.CreateFromDirectory(staging, destination, CompressionLevel.SmallestSize, false);
            return destination;
        }
        finally
        {
            try { if (Directory.Exists(staging)) Directory.Delete(staging, true); } catch { }
        }
    }

    private static string BuildReport(GameInstallation game, UserSettings settings, InstallState state, IReadOnlyCollection<string> errors)
    {
        var version = Assembly.GetExecutingAssembly().GetName().Version ?? new Version(0, 0, 0);
        var builder = new StringBuilder();
        builder.AppendLine("Paw's Patch diagnostic archive");
        builder.AppendLine($"Created UTC: {DateTimeOffset.UtcNow:O}");
        builder.AppendLine($"Launcher: {version.Major}.{version.Minor}.{version.Build}");
        builder.AppendLine($"Configuration: {ConfigurationCode.Create(settings)}");
        builder.AppendLine($"Game directory: {game.Directory}");
        builder.AppendLine($"Game branch: {game.Branch ?? "unknown"}");
        builder.AppendLine($"Steam build: {game.SteamBuild ?? "unknown"}");
        builder.AppendLine($"Verification: {(errors.Count == 0 ? "OK" : "FAILED")}");
        foreach (var error in errors) builder.AppendLine($"  {error}");
        builder.AppendLine();
        builder.AppendLine("Installed modules:");
        foreach (var module in state.Modules.OrderBy(x => x.Value.Priority).ThenBy(x => x.Key, StringComparer.OrdinalIgnoreCase))
            builder.AppendLine($"  {module.Key} {module.Value.Version} priority={module.Value.Priority} archive-sha256={module.Value.ArchiveSha256} files={module.Value.Files.Count}");
        builder.AppendLine();
        builder.AppendLine("Privacy note: crash dumps can contain fragments of process memory. Review the archive before sharing it publicly.");
        return builder.ToString();
    }

    private static void CopyMatches(string source, string pattern, string destination, HashSet<string> copied)
    {
        if (!Directory.Exists(source)) return;
        foreach (var file in Directory.EnumerateFiles(source, pattern, SearchOption.TopDirectoryOnly))
            CopyOne(file, Path.Combine(destination, Path.GetFileName(file)), copied);
    }

    private static void CopyTree(string source, string destination, HashSet<string> copied)
    {
        if (!Directory.Exists(source)) return;
        foreach (var file in Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories))
        {
            var relative = Path.GetRelativePath(source, file);
            CopyOne(file, Path.Combine(destination, relative), copied);
        }
    }

    private static void CopyDiagnosticsTree(string source, string destination, HashSet<string> copied)
    {
        if (!Directory.Exists(source)) return;
        foreach (var file in Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories))
        {
            var name = Path.GetFileName(file);
            if (!name.EndsWith(".log", StringComparison.OrdinalIgnoreCase)
                && !name.EndsWith(".txt", StringComparison.OrdinalIgnoreCase)
                && !name.EndsWith(".dmp", StringComparison.OrdinalIgnoreCase)) continue;
            var relative = Path.GetRelativePath(source, file);
            CopyOne(file, Path.Combine(destination, relative), copied);
        }
    }

    private static void CopyOne(string source, string destination, HashSet<string> copied)
    {
        var full = Path.GetFullPath(source);
        if (!copied.Add(full)) return;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            File.Copy(full, destination, true);
        }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    private static async Task WriteHashManifestAsync(string root, CancellationToken cancellationToken)
    {
        var lines = new List<string> { "SHA-256  SIZE  PATH" };
        foreach (var file in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
        {
            cancellationToken.ThrowIfCancellationRequested();
            var hash = await CryptoAndIO.Sha256Async(file, cancellationToken);
            lines.Add($"{hash}  {new FileInfo(file).Length}  {Path.GetRelativePath(root, file)}");
        }
        await WriteTextAsync(root, "files-sha256.txt", string.Join(Environment.NewLine, lines), cancellationToken);
    }

    private static async Task WriteTextAsync(string root, string relative, string text, CancellationToken cancellationToken)
    {
        var path = Path.Combine(root, relative);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        await File.WriteAllTextAsync(path, text, new UTF8Encoding(false), cancellationToken);
    }
}

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
        foreach (var name in new[] { "launcher-errors.log", "self-update.log", "launcher-run.json", "previous-launcher-run.json", "game-run.json", "failed-launcher-sha256.txt", "update-rollback.txt", "user-actions.jsonl", "user-actions.1.jsonl", "user-actions.2.jsonl" })
        {
            var file = Path.Combine(ActivityStore.Root, name);
            if (File.Exists(file)) CopyOne(file, Path.Combine(staging, "launcher", name), copied);
        }
    }

    public static async Task<string> CreateLauncherOnlyAsync(string destination)
    {
        var staging = Path.Combine(Path.GetTempPath(), "PawsPatchDiagnostics", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try
        {
            ActionJournal.Record("diagnostics.create", "launcher-only");
            await ActionJournal.FlushAsync();
            CopyLauncherDiagnostics(staging);
            await WriteTextAsync(staging, "system-information.json", await SystemDiagnostics.CollectAsync(null), default);
            await WriteTextAsync(staging, "launcher-report.txt", "Paw's Launcher diagnostics (game not selected).\nUser action history contains control names and game settings, not typed text or chat messages.\nHardware query failures are listed in system-information.json.\n", default);
            await WriteHashManifestAsync(staging, default);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(destination))!);
            if (File.Exists(destination)) File.Delete(destination);
            ZipFile.CreateFromDirectory(staging, destination, CompressionLevel.SmallestSize, false);
            ActionJournal.Record("diagnostics.created", "launcher-only");
            return destination;
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
            ActionJournal.Record("diagnostics.create", "game");
            await ActionJournal.FlushAsync();
            await WriteTextAsync(staging, "system-information.json", await SystemDiagnostics.CollectAsync(game.Directory, cancellationToken), cancellationToken);
            var report = BuildReport(game, settings, state, verificationErrors);
            await WriteTextAsync(staging, "launcher-report.txt", report, cancellationToken);
            await WriteTextAsync(staging, "install-state.json",
                JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState), cancellationToken);
            await WriteRuntimeInventoryAsync(staging, game, state, cancellationToken);

            var copied = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            CopyLauncherDiagnostics(staging);
            foreach (var name in new[] { "state.json", "last-working.json", "rollback.txt", "mod-library.json" })
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
            ActionJournal.Record("diagnostics.created", "game");
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
        builder.AppendLine("Paw's Launcher diagnostic archive");
        builder.AppendLine($"Created UTC: {DateTimeOffset.UtcNow:O}");
        builder.AppendLine($"Launcher: {version.Major}.{version.Minor}.{version.Build}");
        builder.AppendLine($"Configuration: {ConfigurationCode.Create(settings)}");
        builder.AppendLine($"Selected mod/channel: {settings.Mod}/{settings.Channel}; text: {(settings.RussianLocalization ? "ru" : "en")}; speech: {GameLanguages.Voice(settings)}");
        builder.AppendLine($"Applied configuration: {(state.AppliedSettings is null ? "none" : ConfigurationCode.Create(state.AppliedSettings))}");
        builder.AppendLine($"Applied release: {state.ReleaseId ?? "none"}; applied base EXE SHA256: {state.BaseGameSha256 ?? "unknown"}");
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
        builder.AppendLine("User actions: last three logs (2 MiB each). Static control/action names, configuration changes and outcomes only; no typed text, passwords, codes or message contents. History begins with installation of this launcher build.");
        return builder.ToString();
    }

    private static async Task WriteRuntimeInventoryAsync(string staging, GameInstallation game, InstallState state, CancellationToken token)
    {
        var names = new[] { "k2.exe", "steam_api.dll", "steam_api64.dll" }.Concat(state.Modules.Values.Where(m => m.Enabled)
            .SelectMany(m => m.Files).Where(f => GameCompatibilityPolicy.NativePath(f.Path)).Select(f => f.Path)).Distinct(StringComparer.OrdinalIgnoreCase);
        var lines = new List<string> { "Actual runtime files: SHA-256  SIZE  MODIFIED-UTC  RELATIVE-PATH" };
        foreach (var name in names.Order(StringComparer.OrdinalIgnoreCase))
        {
            try
            {
                var path = CryptoAndIO.SafeChildPath(game.Directory, name);
                if (!File.Exists(path)) { lines.Add("MISSING  " + name); continue; }
                var info = new FileInfo(path);
                lines.Add($"{await CryptoAndIO.Sha256Async(path, token)}  {info.Length}  {info.LastWriteTimeUtc:O}  {name}");
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException or InvalidDataException) { lines.Add("UNREADABLE " + error.GetType().Name + "  " + name); }
        }
        await WriteTextAsync(staging, "runtime-files.txt", string.Join(Environment.NewLine, lines), token);
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

using Microsoft.Win32;
using System.Security;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public sealed record DiagnosticLocations(string GameRoot, string Documents, string LocalAppData,
    string ProgramData, IReadOnlyList<string> CustomDumpFolders)
{
    public static DiagnosticLocations Current(string gameRoot)
    {
        var folders = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        // Read existing Windows settings only. Do not enable dumps or change retention.
        // https://learn.microsoft.com/windows/win32/wer/collecting-user-mode-dumps
        foreach (var view in new[] { RegistryView.Registry32, RegistryView.Registry64 })
        foreach (var suffix in new[] { "", @"\k2.exe" })
        {
            try
            {
                using var machine = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view);
                using var key = machine.OpenSubKey(@"SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps" + suffix);
                if (key?.GetValue("DumpFolder") is string path && !string.IsNullOrWhiteSpace(path))
                    folders.Add(Environment.ExpandEnvironmentVariables(path));
            }
            catch (Exception e) when (e is SecurityException or UnauthorizedAccessException or IOException) { }
        }
        return new(gameRoot, Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), folders.ToArray());
    }

    public string? VirtualGameRoot()
    {
        var full = Path.GetFullPath(GameRoot);
        if (full.StartsWith(@"\\", StringComparison.Ordinal)) return null;
        return Path.Combine(LocalAppData, "VirtualStore", full[Path.GetPathRoot(full)!.Length..]);
    }
}

public sealed class DiagnosticCollectionReport
{
    public int SchemaVersion { get; } = 1;
    public int RecentGroupsPerCategory { get; set; } = GameDiagnosticFiles.RecentCount;
    public bool IncludeCrashDumps { get; set; } = true;
    public long EstimatedArchiveBytes { get; set; }
    public List<DiagnosticSearchResult> Searches { get; } = [];
    public List<DiagnosticCopyResult> Files { get; } = [];
    public string Note { get; } = "The selected number of newest readable log/report sets is collected per category. When crash dumps are selected, one newest full graphics/crash memory dump and crash companion logs are also included. Current patch status is always included. Large text files retain their first 64 KiB and last 4 MiB; truncation and original size are recorded. AI action logs, backups, saves, chat text and other applications' Windows dumps are excluded. Sources are never modified; missing sources and copy failures are listed. Preview compression is estimated from bounded samples, not an exact ZIP size.";
}
public sealed record DiagnosticSearchResult(string Source, string Path, string Status, string? Error = null);
public sealed record DiagnosticCopyResult(string Source, string ArchivePath, string Category, string Status,
    long Bytes, DateTime? ModifiedUtc, string? Error = null, long? SourceBytes = null, bool Truncated = false);
public sealed record DiagnosticOptions(int RecentCount = GameDiagnosticFiles.RecentCount, bool IncludeCrashDumps = true)
{
    public void Validate() { if (RecentCount < 0 || RecentCount > 10000 && RecentCount != int.MaxValue) throw new ArgumentOutOfRangeException(nameof(RecentCount)); }
}

public static class GameDiagnosticFiles
{
    public const int RecentCount = 3;
    public const int TextHeadBytes = 64 * 1024;
    public const int TextTailBytes = 4 * 1024 * 1024;
    private static readonly StringComparer Paths = StringComparer.OrdinalIgnoreCase;
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    private static readonly Regex LogName = new(@"^(?:ART_)?(?<session>log[^/\\]*)\.log$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    private static readonly Regex GameExe = new(@"^k2(?:_paws_[a-z0-9_]+)?\.exe$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    private static readonly Regex WindowsDump = new(@"^k2(?:_paws_[a-z0-9_]+)?\.exe(?:\.[0-9]+)?\.(?:dmp|mdmp|hdmp)$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    private static readonly HashSet<string> Excluded = new([".pawpatch", "PawsPatchBackups", "paws_ai_diagnostics", "backups", "backup", "originals", "data orig", "save", "saves", "screenshots", "cache", "test-profile"], Paths);
    private sealed record Candidate(string Path, string ArchivePath, string Category, string Group, DateTime ModifiedUtc);
    private sealed record Group(string Key, string Category, DateTime ModifiedUtc, Candidate[] Files);

    public static Task<DiagnosticCollectionReport> CollectAsync(string staging, DiagnosticLocations locations,
        CancellationToken token = default, DiagnosticCollectionReport? report = null, DiagnosticOptions? options = null)
        => CollectCoreAsync(staging,locations,token,report,options ?? new(),false);
    public static Task<DiagnosticCollectionReport> PreviewAsync(DiagnosticLocations locations, DiagnosticOptions options, CancellationToken token = default)
        => Task.Run(() => CollectCoreAsync("",locations,token,null,options,true),token);
    private static async Task<DiagnosticCollectionReport> CollectCoreAsync(string staging, DiagnosticLocations locations,
        CancellationToken token, DiagnosticCollectionReport? report, DiagnosticOptions options, bool preview)
    {
        options.Validate();
        report ??= new();
        report.RecentGroupsPerCategory = options.RecentCount;
        report.IncludeCrashDumps = options.IncludeCrashDumps && options.RecentCount > 0;
        var candidates = new Dictionary<string, Candidate>(Paths);
        var visited = new HashSet<string>(Paths);
        void Add(string path, string sourceRoot, string label, string category, string group)
        {
            try
            {
                if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) return;
                var full = Path.GetFullPath(path);
                var relative = CryptoAndIO.NormalizeRelativePath(Path.GetRelativePath(sourceRoot, full));
                candidates.TryAdd(full, new(full, "logs/" + label + "/" + relative, category, group, File.GetLastWriteTimeUtc(full)));
            }
            catch (Exception e) when (FileError(e)) { report.Searches.Add(new(label, path, "unreadable", e.GetType().Name)); }
        }
        void Scan(string sourceRoot, string label, bool recursive, bool windowsOnly = false)
        {
            if (string.IsNullOrWhiteSpace(sourceRoot)) return;
            if (sourceRoot.StartsWith(@"\\", StringComparison.Ordinal)) { report.Searches.Add(new(label, sourceRoot, "remote-path-skipped")); return; }
            var pending = new Stack<string>(); pending.Push(sourceRoot);
            while (pending.Count != 0)
            {
                token.ThrowIfCancellationRequested();
                var directory = pending.Pop();
                try
                {
                    if (!visited.Add(Path.GetFullPath(directory))) continue;
                    if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0)
                    { report.Searches.Add(new(label, directory, "link-skipped")); continue; }
                    var files = Directory.GetFiles(directory);
                    report.Searches.Add(new(label, directory, "searched"));
                    foreach (var path in files)
                    {
                        var name = Path.GetFileName(path);
                        if (windowsOnly)
                        {
                            if (WindowsDump.IsMatch(name)) Add(path, sourceRoot, label, "windows-dumps", path);
                            continue;
                        }
                        var log = LogName.Match(name);
                        if (log.Success) Add(path, sourceRoot, label, "game-logs", Path.Combine(directory, log.Groups["session"].Value));
                        else if (Path.GetExtension(name).Equals(".dmp", StringComparison.OrdinalIgnoreCase))
                            Add(path, sourceRoot, label, name.StartsWith("log-graphics-", StringComparison.OrdinalIgnoreCase) ? "full-memory-dumps" : "game-dumps", path);
                        else if (name.StartsWith("synclog", StringComparison.OrdinalIgnoreCase) && name.EndsWith(".txt", StringComparison.OrdinalIgnoreCase))
                            Add(path, sourceRoot, label, "sync-logs", path);
                        else if (name.Equals("paws_graphics_guard.log", StringComparison.OrdinalIgnoreCase)
                            || name.Equals("paws_recovery.log", StringComparison.OrdinalIgnoreCase)
                            || name.StartsWith("paws_", StringComparison.OrdinalIgnoreCase) && name.EndsWith("status.txt", StringComparison.OrdinalIgnoreCase))
                            Add(path, sourceRoot, label, "status:" + name.ToLowerInvariant(), path);
                    }
                    if (recursive)
                        foreach (var child in Directory.GetDirectories(directory))
                            if (!Excluded.Contains(Path.GetFileName(child)) && !Path.GetFileName(child).StartsWith("Before-", StringComparison.OrdinalIgnoreCase)) pending.Push(child);
                }
                catch (DirectoryNotFoundException) { report.Searches.Add(new(label, directory, "missing")); }
                catch (FileNotFoundException) { report.Searches.Add(new(label, directory, "missing")); }
                catch (Exception e) when (FileError(e)) { report.Searches.Add(new(label, directory, "unreadable", e.GetType().Name)); }
            }
        }
        void ScanGameRoot(string root, string label)
        {
            Scan(root, label, false);
            foreach (var sub in new[] { "logs", "log", "crash", "crashes", "data/logs", "data/synclogs" })
                Scan(Path.Combine(root, sub), label + "/" + sub, true);
        }
        ScanGameRoot(locations.GameRoot, "game-root");
        Scan(Path.Combine(locations.Documents, "Kohan2"), "documents-kohan2", true);
        Scan(Path.Combine(locations.Documents, "Kohan II"), "documents-kohan-ii", true);
        if (locations.VirtualGameRoot() is { } virtualRoot) ScanGameRoot(virtualRoot, "virtualstore-game");
        Scan(Path.Combine(locations.LocalAppData, "CrashDumps"), "windows-crashdumps", false, true);
        for (var i = 0; i < locations.CustomDumpFolders.Count; i++) Scan(locations.CustomDumpFolders[i], "windows-custom-" + i, false, true);

        void ScanWer(string root, string label)
        {
            try
            {
                if ((File.GetAttributes(root) & FileAttributes.ReparsePoint) != 0) { report.Searches.Add(new(label, root, "link-skipped")); return; }
                var folders = Directory.GetDirectories(root);
                report.Searches.Add(new(label, root, "searched"));
                foreach (var folder in folders)
                {
                    token.ThrowIfCancellationRequested();
                    // Do not inspect other applications' report bodies.
                    if (!Regex.IsMatch(Path.GetFileName(folder), @"^(?:AppCrash|AppHang)_k2(?:\.exe_|_paws_)", RegexOptions.IgnoreCase)) continue;
                    try
                    {
                        if ((File.GetAttributes(folder) & FileAttributes.ReparsePoint) != 0) continue;
                        var wer = Path.Combine(folder, "Report.wer");
                        if (!File.Exists(wer) || new FileInfo(wer).Length > 256 * 1024) { report.Searches.Add(new(label, folder, "unverified-game-report")); continue; }
                        if ((File.GetAttributes(wer) & FileAttributes.ReparsePoint) != 0) continue;
                        var body = File.ReadAllText(wer);
                        var identity = body.Split('\n').Select(s => s.Trim()).Any(s =>
                            (s.StartsWith("AppName=", StringComparison.OrdinalIgnoreCase) || s.StartsWith("AppPath=", StringComparison.OrdinalIgnoreCase) || s.StartsWith("NsAppName=", StringComparison.OrdinalIgnoreCase))
                            && GameExe.IsMatch(Path.GetFileName(s[(s.IndexOf('=') + 1)..])));
                        if (!identity) { report.Searches.Add(new(label, folder, "unrelated-report-skipped")); continue; }
                        foreach (var path in Directory.GetFiles(folder))
                            if (Path.GetFileName(path).Equals("Report.wer", StringComparison.OrdinalIgnoreCase)
                                || new[] { ".dmp", ".mdmp", ".hdmp" }.Contains(Path.GetExtension(path), StringComparer.OrdinalIgnoreCase))
                                Add(path, root, label, "windows-reports", folder);
                    }
                    catch (Exception e) when (FileError(e)) { report.Searches.Add(new(label, folder, "unreadable", e.GetType().Name)); }
                }
            }
            catch (DirectoryNotFoundException) { report.Searches.Add(new(label, root, "missing")); }
            catch (FileNotFoundException) { report.Searches.Add(new(label, root, "missing")); }
            catch (Exception e) when (FileError(e)) { report.Searches.Add(new(label, root, "unreadable", e.GetType().Name)); }
        }
        foreach (var (directory, label) in new[] { (locations.LocalAppData, "user-wer"), (locations.ProgramData, "system-wer") })
        foreach (var area in new[] { "ReportArchive", "ReportQueue" })
            ScanWer(Path.Combine(directory, "Microsoft/Windows/WER", area), label + "/" + area);

        var copied = new HashSet<string>(Paths);
        var groups = candidates.Values.GroupBy(c => c.Category + "\0" + c.Group, Paths)
            .Select(g => new Group(g.First().Group, g.First().Category, g.Max(c => c.ModifiedUtc), g.OrderBy(c => c.Path, Paths).ToArray())).ToArray();
        async Task<bool> Copy(Candidate file)
        {
            if (copied.Contains(file.Path)) return true;
            var success = preview ? await EstimateFileAsync(file.Path,file.ArchivePath,file.Category,report,token)
                : await CopyFileAsync(file.Path, staging, file.ArchivePath, file.Category, report, token);
            if (success) copied.Add(file.Path);
            return success;
        }
        foreach (var bucket in groups.GroupBy(g => g.Category))
        {
            if (!report.IncludeCrashDumps && bucket.Key is "game-dumps" or "full-memory-dumps" or "windows-dumps" or "windows-reports") continue;
            var successes = 0;
            var limit = bucket.Key.StartsWith("status:", StringComparison.Ordinal) || bucket.Key == "full-memory-dumps" ? 1 : options.RecentCount;
            foreach (var group in bucket.OrderByDescending(g => g.ModifiedUtc).ThenBy(g => g.Key, Paths))
            {
                if (successes >= limit) break;
                var complete = true;
                foreach (var file in group.Files) complete &= await Copy(file);
                if (complete) successes++;
            }
        }
        // Keep main/ART companions of retained crashes even below the ordinary log cutoff.
        foreach (var dump in candidates.Values.Where(c => (c.Category == "game-dumps" || c.Category == "full-memory-dumps") && copied.Contains(c.Path)))
        {
            var key = Path.Combine(Path.GetDirectoryName(dump.Path)!, Path.GetFileNameWithoutExtension(dump.Path));
            foreach (var companion in candidates.Values.Where(c => c.Category == "game-logs" && Paths.Equals(c.Group, key))) await Copy(companion);
        }
        if (!preview) await WriteReportAsync(staging, report, token);
        return report;
    }

    internal static async Task<bool> EstimateFileAsync(string source,string relative,string category,DiagnosticCollectionReport report,CancellationToken token)
    {
        try
        {
            token.ThrowIfCancellationRequested();
            if ((File.GetAttributes(source) & FileAttributes.ReparsePoint) != 0) throw new IOException("LinkSkipped");
            using var input = new FileStream(source,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete,65536,FileOptions.Asynchronous|FileOptions.RandomAccess);
            var length = input.Length;
            var text = new[] { ".log", ".txt", ".jsonl" }.Contains(Path.GetExtension(source),StringComparer.OrdinalIgnoreCase);
            var truncated = text && length > TextHeadBytes+TextTailBytes;
            var included = truncated ? TextHeadBytes+TextTailBytes+160L : length;
            // Sample both ends without copying full logs or multi-gigabyte dumps for a preview.
            var sample = new byte[(int)Math.Min(length,131072)];
            var head = Math.Min(sample.Length,65536);
            await input.ReadExactlyAsync(sample.AsMemory(0,head),token);
            var tail = sample.Length-head;
            if (tail > 0) { input.Position = length-tail; await input.ReadExactlyAsync(sample.AsMemory(head,tail),token); }
            using var compressed = new MemoryStream();
            using (var deflate = new System.IO.Compression.DeflateStream(compressed,System.IO.Compression.CompressionLevel.Optimal,true)) await deflate.WriteAsync(sample,token);
            var ratio = sample.Length == 0 ? 1 : Math.Clamp((compressed.Length+16d)/sample.Length,0.002,1.02);
            report.EstimatedArchiveBytes += (long)Math.Ceiling(included*ratio)+256+Encoding.UTF8.GetByteCount(relative);
            report.Files.Add(new(source,relative,category,"estimated",included,File.GetLastWriteTimeUtc(source),SourceBytes:length,Truncated:truncated));
            return true;
        }
        catch (Exception error) when (FileError(error))
        { report.Files.Add(new(source,relative,category,"failed",0,null,error.GetType().Name)); return false; }
    }

    public static async Task<bool> CopyFileAsync(string source, string staging, string relative, string category,
        DiagnosticCollectionReport report, CancellationToken token)
    {
        var target = CryptoAndIO.SafeChildPath(staging, relative);
        long bytes = 0; DateTime? modified = null; var created = false;
        try
        {
            token.ThrowIfCancellationRequested();
            if ((File.GetAttributes(source) & FileAttributes.ReparsePoint) != 0) throw new IOException("LinkSkipped");
            modified = File.GetLastWriteTimeUtc(source);
            // Snapshot the current length: don't chase a growing log or alter the original.
            using var input = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete, 65536, FileOptions.Asynchronous | FileOptions.SequentialScan);
            var remaining = input.Length;
            var sourceBytes = remaining;
            var textFile = new[] { ".log", ".txt", ".jsonl" }.Contains(Path.GetExtension(source), StringComparer.OrdinalIgnoreCase);
            var truncated = textFile && sourceBytes > TextHeadBytes + TextTailBytes;
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            using (var output = new FileStream(target, FileMode.CreateNew, FileAccess.Write, FileShare.None, 65536, FileOptions.Asynchronous))
            {
                created = true;
                var buffer = new byte[65536];
                if (truncated) remaining = TextHeadBytes;
                while (remaining > 0)
                {
                    var read = await input.ReadAsync(buffer.AsMemory(0, (int)Math.Min(buffer.Length, remaining)), token);
                    if (read == 0) throw new EndOfStreamException("SourceTruncated");
                    await output.WriteAsync(buffer.AsMemory(0, read), token); bytes += read; remaining -= read;
                    if (truncated && input.Position == TextHeadBytes)
                    {
                        var marker = Encoding.UTF8.GetBytes("\n[Diagnostics: middle of oversized text omitted; source was " + sourceBytes + " bytes. Last 4 MiB follow.]\n");
                        await output.WriteAsync(marker, token); bytes += marker.Length;
                        input.Position = sourceBytes - TextTailBytes;
                        remaining = TextTailBytes;
                    }
                }
            }
            File.SetLastWriteTimeUtc(target, modified.Value);
            report.Files.Add(new(source, relative.Replace('\\', '/'), category, "copied", bytes, modified, SourceBytes: sourceBytes, Truncated: truncated));
            return true;
        }
        catch (Exception e) when (FileError(e) || e is OperationCanceledException)
        {
            // Only remove our partial staging file, never the source.
            try { if (created && File.Exists(target)) File.Delete(target); } catch (Exception cleanup) when (FileError(cleanup)) { }
            if (e is OperationCanceledException) throw;
            report.Files.Add(new(source, relative.Replace('\\', '/'), category, "failed", bytes, modified, e.GetType().Name));
            return false;
        }
    }
    private static bool FileError(Exception e) => e is IOException or UnauthorizedAccessException or SecurityException or ArgumentException or NotSupportedException;
    public static Task WriteReportAsync(string staging, DiagnosticCollectionReport report, CancellationToken token) =>
        File.WriteAllTextAsync(Path.Combine(staging, "collection-report.json"), JsonSerializer.Serialize(report, JsonOptions), new UTF8Encoding(false), token);
}

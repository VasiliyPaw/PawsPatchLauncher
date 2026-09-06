using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed record StorageOptions(string CacheRoot, string? GameRoot, string? LauncherExe,
    IReadOnlyList<PackageRelease> KeepPackages, IReadOnlyList<LauncherRelease> KeepLaunchers);
public sealed record StorageEntry(string Kind, string Path, long Bytes, bool Cleanable, string Stamp);
public sealed record StoragePlan(IReadOnlyList<StorageEntry> Entries)
{
    public long TotalBytes => Entries.Sum(x => x.Bytes);
    public long CleanableBytes => Entries.Where(x => x.Cleanable).Sum(x => x.Bytes);
}
public sealed record StorageCleanResult(int Removed, long Bytes, int Skipped);

public static class StorageMaintenance
{
    public const int RetainDays = 7;
    private sealed record Tree(long Bytes, DateTime Latest, string Stamp, List<string> Files, List<string> Directories);
    private static bool Segment(string name) => name.Length is > 0 and < 150 && name is not "." and not ".."
        && name.All(x => char.IsAsciiLetterOrDigit(x) || x is '-' or '_' or '.');
    private static bool Hash(string hash) => hash.Length == 64 && hash.All(Uri.IsHexDigit);
    private static string Key(string id, string version) => id.ToUpperInvariant() + "|" + version;
    private static bool RecognizedPackage(string path, string id, string version)
    {
        var marker = CryptoAndIO.SafeChildPath(path, ".verified");
        var manifestPath = CryptoAndIO.SafeChildPath(path, "module.json");
        RemovalSafety.CheckNoLinks(marker); RemovalSafety.CheckNoLinks(manifestPath);
        if (!Segment(id) || !Segment(version) || !File.Exists(marker) || new FileInfo(marker).Length > 128
            || !Hash(File.ReadAllText(marker).Trim()) || !File.Exists(manifestPath) || new FileInfo(manifestPath).Length > 16 * 1024 * 1024) return false;
        ModuleArchiveManifest? manifest;
        try { manifest = JsonSerializer.Deserialize(File.ReadAllText(manifestPath), LauncherJsonContext.Default.ModuleArchiveManifest); }
        catch (JsonException) { return false; }
        if (manifest is null || manifest.SchemaVersion != 1 || manifest.Id != id || manifest.Version != version || manifest.Files is null) return false;
        var allowed = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { marker, manifestPath };
        foreach (var file in manifest.Files)
        {
            if (file is null) return false;
            allowed.Add(CryptoAndIO.SafeChildPath(Path.Combine(path, "payload"), file.Path));
        }
        return Inspect(path).Files.All(allowed.Contains);
    }

    // No recursive Delete: inspect every entry, reject links, then delete only inspected leaves.
    private static Tree Inspect(string path)
    {
        RemovalSafety.CheckNoLinks(path);
        var files = new List<string>(); var dirs = new List<string>();
        if (File.Exists(path)) files.Add(Path.GetFullPath(path));
        else if (Directory.Exists(path))
        {
            var pending = new Stack<string>(); pending.Push(Path.GetFullPath(path));
            while (pending.TryPop(out var folder))
            {
                RemovalSafety.CheckNoLinks(folder); dirs.Add(folder);
                foreach (var entry in Directory.EnumerateFileSystemEntries(folder))
                {
                    if ((File.GetAttributes(entry) & FileAttributes.ReparsePoint) != 0) throw new IOException("A storage link was blocked: " + entry);
                    if (Directory.Exists(entry)) pending.Push(entry); else files.Add(entry);
                }
            }
        }
        long bytes = 0; var latest = DateTime.MinValue; var inventory = new StringBuilder();
        foreach (var file in files.OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
        {
            RemovalSafety.CheckNoLinks(file);
            var info = new FileInfo(file); bytes = checked(bytes + info.Length);
            if (info.LastWriteTimeUtc > latest) latest = info.LastWriteTimeUtc;
            inventory.Append(file).Append('|').Append(info.Length).Append('|').Append(info.LastWriteTimeUtc.Ticks).Append('\n');
        }
        foreach (var dir in dirs.OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
        {
            var modified = Directory.GetLastWriteTimeUtc(dir); if (modified > latest) latest = modified;
            inventory.Append(dir).Append('|').Append(modified.Ticks).Append('\n');
        }
        return new(bytes, latest, Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(inventory.ToString()))), files, dirs);
    }

    public static StoragePlan Scan(StorageOptions options, DateTime? utcNow = null)
    {
        var cutoff = (utcNow ?? DateTime.UtcNow).AddDays(-RetainDays);
        var entries = new List<StorageEntry>();
        var protectedVersions = options.KeepPackages.Select(x => Key(x.Id, x.Version)).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var protectedLaunchers = options.KeepLaunchers.Select(x => x.Sha256).ToHashSet(StringComparer.OrdinalIgnoreCase);
        void Protect(InstallState state) { foreach (var module in state.Modules) protectedVersions.Add(Key(module.Key, module.Value.Version)); }
        void Add(string kind, string path, bool candidate)
        {
            var tree = Inspect(path);
            var fullPath = Path.GetFullPath(path);
            var currentExe = options.LauncherExe is null ? null : Path.GetFullPath(options.LauncherExe);
            var containsRunningLauncher = currentExe is not null && (currentExe.Equals(fullPath, StringComparison.OrdinalIgnoreCase)
                || currentExe.StartsWith(fullPath.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase));
            entries.Add(new(kind, fullPath, tree.Bytes, candidate && !containsRunningLauncher && tree.Latest < cutoff, tree.Stamp));
        }
        if (options.GameRoot is not null)
        {
            var game = Path.GetFullPath(options.GameRoot);
            var control = CryptoAndIO.SafeChildPath(game, ".pawpatch");
            RemovalSafety.CheckNoLinks(control);
            Protect(new ModuleInstaller(game).LoadState());
            var transactions = CryptoAndIO.SafeChildPath(control, "transactions");
            var pointerPath = CryptoAndIO.SafeChildPath(control, "rollback.txt");
            RemovalSafety.CheckNoLinks(pointerPath);
            var keep = File.Exists(pointerPath) ? File.ReadAllText(pointerPath).Trim() : null;
            if (keep is not null && !Guid.TryParseExact(keep, "N", out _)) throw new InvalidDataException("Invalid rollback pointer; cleanup is blocked.");
            if (keep is not null && !Directory.Exists(CryptoAndIO.SafeChildPath(transactions, keep))) throw new InvalidDataException("Rollback backup is missing; cleanup is blocked.");
            if (Directory.Exists(transactions))
            {
                RemovalSafety.CheckNoLinks(transactions);
                var directories = Directory.GetDirectories(transactions);
                var snapshots = new List<(string Directory, Tree Tree, PatchTransaction? Journal)>();
                foreach (var dir in directories)
                {
                    var tree = Inspect(dir);
                    var journalPath = CryptoAndIO.SafeChildPath(dir, "journal.json");
                    PatchTransaction? journal = null;
                    if (Guid.TryParseExact(Path.GetFileName(dir), "N", out _) && File.Exists(journalPath))
                    {
                        if (new FileInfo(journalPath).Length > 64 * 1024 * 1024) throw new InvalidDataException("Recovery journal is too large; cleanup is blocked.");
                        journal = JsonSerializer.Deserialize(File.ReadAllText(journalPath), LauncherJsonContext.Default.PatchTransaction)
                            ?? throw new InvalidDataException("Invalid recovery journal; cleanup is blocked.");
                        Protect(journal.Before);
                    }
                    snapshots.Add((dir, tree, journal));
                }
                // A newer pending/unknown folder must not displace the latest usable backup.
                var latestComplete = snapshots.Where(x => x.Journal?.Phase is "complete" or "recovered")
                    .OrderByDescending(x => Directory.GetCreationTimeUtc(x.Directory)).Select(x => x.Directory).FirstOrDefault();
                foreach (var snapshot in snapshots)
                {
                    var eligible = snapshot.Journal?.Phase is "complete" or "recovered"
                        && Path.GetFileName(snapshot.Directory) != keep && snapshot.Directory != latestComplete && snapshot.Tree.Latest < cutoff;
                    entries.Add(new("backups", snapshot.Directory, snapshot.Tree.Bytes, eligible, snapshot.Tree.Stamp));
                }
            }
            var originals = CryptoAndIO.SafeChildPath(control, "originals");
            if (Directory.Exists(originals)) Add("originals", originals, false);
            var packages = CryptoAndIO.SafeChildPath(control, "packages");
            if (Directory.Exists(packages))
            {
                RemovalSafety.CheckNoLinks(packages);
                foreach (var idDir in Directory.EnumerateDirectories(packages))
                {
                    RemovalSafety.CheckNoLinks(idDir);
                    foreach (var dir in Directory.EnumerateDirectories(idDir))
                    {
                        var id = Path.GetFileName(idDir); var version = Path.GetFileName(dir);
                        var recognized = RecognizedPackage(dir, id, version);
                        Add("packages", dir, recognized && !protectedVersions.Contains(Key(id, version)));
                    }
                }
            }
        }
        var downloads = CryptoAndIO.SafeChildPath(options.CacheRoot, "downloads");
        if (Directory.Exists(downloads))
        {
            RemovalSafety.CheckNoLinks(downloads);
            foreach (var idDir in Directory.EnumerateDirectories(downloads))
            {
                RemovalSafety.CheckNoLinks(idDir);
                foreach (var versionDir in Directory.EnumerateDirectories(idDir))
                {
                    RemovalSafety.CheckNoLinks(versionDir);
                    var id = Path.GetFileName(idDir); var version = Path.GetFileName(versionDir);
                    foreach (var file in Directory.EnumerateFiles(versionDir))
                    {
                        var name = Path.GetFileName(file);
                        var hash = name.EndsWith(".zip.download", StringComparison.OrdinalIgnoreCase) ? name[..^13]
                            : name.EndsWith(".zip", StringComparison.OrdinalIgnoreCase) ? name[..^4] : "";
                        Add("downloads", file, Segment(id) && Segment(version) && Hash(hash) && !protectedVersions.Contains(Key(id, version)));
                    }
                }
            }
        }
        var launchers = CryptoAndIO.SafeChildPath(options.CacheRoot, "launcher");
        if (Directory.Exists(launchers))
        {
            RemovalSafety.CheckNoLinks(launchers);
            foreach (var file in Directory.EnumerateFiles(launchers))
            {
                var name = Path.GetFileName(file); var baseName = name.EndsWith(".download", StringComparison.OrdinalIgnoreCase) ? name[..^9] : name;
                var dash = baseName.LastIndexOf('-');
                var hash = dash >= 0 && baseName.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) ? baseName[(dash + 1)..^4] : "";
                var versionText = dash > 18 && baseName.StartsWith("PawsPatchLauncher-", StringComparison.Ordinal) ? baseName[18..dash] : "";
                var recognized = Version.TryParse(versionText, out var version) && Hash(hash);
                Add("launcher-cache", file, recognized && version! < SelfUpdater.CurrentVersion && !protectedLaunchers.Contains(hash));
            }
        }
        if (options.LauncherExe is not null)
            foreach (var suffix in new[] { ".previous", ".failed", ".new" })
            {
                var path = Path.GetFullPath(options.LauncherExe) + suffix;
                if (File.Exists(path)) Add("launcher-backup", path, false);
            }
        return new(entries);
    }

    public static StorageCleanResult Clean(StorageOptions options, StoragePlan approved, bool cache, bool backups)
    {
        // Re-evaluate installed/pinned versions and rollback pointers at action time.
        var fresh = Scan(options).Entries.ToDictionary(x => x.Path, StringComparer.OrdinalIgnoreCase);
        var removed = 0; long bytes = 0; var skipped = 0;
        foreach (var item in approved.Entries.Where(x => x.Cleanable && (x.Kind == "backups" ? backups : cache)))
        {
            if (!fresh.TryGetValue(item.Path, out var current) || !current.Cleanable || current.Stamp != item.Stamp) { skipped++; continue; }
            var tree = Inspect(current.Path);
            if (tree.Stamp != item.Stamp) { skipped++; continue; }
            try
            {
                foreach (var file in tree.Files) { RemovalSafety.CheckNoLinks(file); File.Delete(file); }
                foreach (var dir in tree.Directories.OrderByDescending(x => x.Length)) { RemovalSafety.CheckNoLinks(dir); Directory.Delete(dir, false); }
                bytes += current.Bytes; removed++;
            }
            catch (IOException) { skipped++; }
            catch (UnauthorizedAccessException) { skipped++; }
        }
        return new(removed, bytes, skipped);
    }
}

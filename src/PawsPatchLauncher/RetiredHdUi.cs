using System.Security.Cryptography;
using System.Text.Json;

namespace PawsPatchLauncher;

public static partial class StorageMaintenance
{
    // Only the four official, superseded artwork packages are eligible. Recovery
    // snapshots contain their own file copies and are never part of this cleanup.
    private sealed record RetiredArtwork(string Id, string Version, string Archive, string Manifest, long Size);
    private static readonly RetiredArtwork[] RetiredArtworkPackages =
    [
        new("common-ui", "0.6.0-beta.4", "DBB2D28405B8DCF00CAD345168DBC5938D7AA9CDE26DBD197FE2B1768379E809", "83A77787447904DC213997816D58CD0439FF99AD499593A5651AF54A2FEDB01A", 1454124155),
        new("pure-beta-common", "0.5.0-beta.8", "CF925BA75BCF05A7D8CB31B4B4CA5E48BCA87CACD9277B28E05B63291203625B", "56C7663BC0502B21549F55A2A280CF8904C69D25B694EF1E34E540A224558BB9", 1448217357),
        new("common-ui", "0.6.0-beta.5", "460DAA645667FEB6B903230C7AD3579175987D84511D6E02A687F44761D69DF4", "BEBF1B201547BB69AD6DC76792C867FD60FC2E85EAE782F5E0A3F0753E7AD427", 124032632),
        new("pure-beta-common", "0.5.0-beta.9", "96262D2BAE5AFA56E3E7DB9D289A727D4F1E67A60DAE6EF1C9D8F90850897A96", "54BDA61CFBD1ACF7A0DEB2D736ED98CE1A2A8AB3541104D9DC1182562ABC542D", 118125767)
    ];

    public static StorageCleanResult RetireHdUi(StorageOptions options, Action ensureGameClosed)
    {
        var removed = 0; long bytes = 0; var skipped = 0;
        if (options.GameRoot is null) return new(0, 0, 0);
        var game = Path.GetFullPath(options.GameRoot);
        var control = CryptoAndIO.SafeChildPath(game, ".pawpatch");
        RemovalSafety.CheckNoLinks(control);
        RemovalSafety.CheckNoLinks(Path.Combine(control, "state.json"));
        var state = new ModuleInstaller(game).LoadState();
        if (!state.Modules.Any(m => m.Key is "common-ui" or "pure-beta-common" && m.Value.Enabled
                && m.Value.Remove.Contains("paws-hd-ui.rwd", StringComparer.OrdinalIgnoreCase))) return new(0, 0, 0);
        var protect = options.KeepPackages.Select(p => Key(p.Id, p.Version)).ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var m in state.Modules) protect.Add(Key(m.Key, m.Value.Version));
        var library = new ModLibrary(game).Load();
        foreach (var p in library.Mods.SelectMany(m => m.Packages).Concat(library.Languages)) protect.Add(Key(p.Id, p.Version));
        var transactions = CryptoAndIO.SafeChildPath(control, "transactions");
        if (Directory.Exists(transactions))
        {
            RemovalSafety.CheckNoLinks(transactions);
            foreach (var dir in Directory.EnumerateDirectories(transactions))
            {
                RemovalSafety.CheckNoLinks(dir);
                var journal = CryptoAndIO.SafeChildPath(dir, "journal.json");
                RemovalSafety.CheckNoLinks(journal);
                if (!Guid.TryParseExact(Path.GetFileName(dir), "N", out _) || !File.Exists(journal)
                    || new FileInfo(journal).Length > 64 * 1024 * 1024) return new(0, 0, 1);
                var transaction = JsonSerializer.Deserialize(File.ReadAllText(journal), LauncherJsonContext.Default.PatchTransaction);
                if (transaction?.Phase is not ("complete" or "recovered")) return new(0, 0, 1);
            }
        }
        foreach (var old in RetiredArtworkPackages.Where(p => !protect.Contains(Key(p.Id, p.Version))))
        {
            var prepared = CryptoAndIO.SafeChildPath(control, $"packages/{old.Id}/{old.Version}");
            var archive = CryptoAndIO.SafeChildPath(options.CacheRoot, $"downloads/{old.Id}/{old.Version}/{old.Archive}.zip");
            foreach (var path in new[] { prepared, archive })
            {
                if (!File.Exists(path) && !Directory.Exists(path)) continue;
                try
                {
                    var tree = Inspect(path);
                    if (path == prepared)
                    {
                        if (!RecognizedPackage(path, old.Id, old.Version)
                            || File.ReadAllText(Path.Combine(path, ".verified")).Trim() != old.Archive
                            || Digest(Path.Combine(path, "module.json")) != old.Manifest) { skipped++; continue; }
                    }
                    else if (tree.Bytes != old.Size || Digest(path) != old.Archive) { skipped++; continue; }
                    ensureGameClosed();
                    if (Inspect(path).Stamp != tree.Stamp) { skipped++; continue; }
                    foreach (var file in tree.Files) { RemovalSafety.CheckNoLinks(file); File.Delete(file); }
                    foreach (var dir in tree.Directories.OrderByDescending(d => d.Length)) { RemovalSafety.CheckNoLinks(dir); Directory.Delete(dir, false); }
                    removed++; bytes += tree.Bytes;
                    if (path == archive)
                    {
                        var timestamp = path + ".downloaded-at";
                        RemovalSafety.CheckNoLinks(timestamp);
                        if (File.Exists(timestamp) && new FileInfo(timestamp).Length < 128
                            && DateTimeOffset.TryParse(File.ReadAllText(timestamp), out _)) File.Delete(timestamp);
                    }
                }
                catch (IOException) { skipped++; }
                catch (UnauthorizedAccessException) { skipped++; }
            }
        }
        return new(removed, bytes, skipped);
    }

    private static string Digest(string path)
    {
        RemovalSafety.CheckNoLinks(path);
        using var stream = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(stream));
    }
}

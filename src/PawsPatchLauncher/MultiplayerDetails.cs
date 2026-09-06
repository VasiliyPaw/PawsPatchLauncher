using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed class MultiplayerManifest
{
    public int SchemaVersion { get; set; } = 1;
    public string Configuration { get; set; } = "";
    public string GameBuild { get; set; } = "";
    public string Executable { get; set; } = "";
    public string Fingerprint { get; set; } = "";
    public List<MultiplayerModule> Modules { get; set; } = [];
    public List<MultiplayerFile> Files { get; set; } = [];
    public List<string> IntegrityErrors { get; set; } = [];
}
public sealed class MultiplayerModule
{
    public string Id { get; set; } = "";
    public string Version { get; set; } = "";
    public string Sha256 { get; set; } = "";
    public bool Enabled { get; set; }
    public int Priority { get; set; }
}
public sealed class MultiplayerFile
{
    public string Path { get; set; } = "";
    public string Sha256 { get; set; } = "";
}
public sealed record MultiplayerDifference(string Kind, string Name, string Local, string Peer);
public sealed record MultiplayerComparison(bool Matches, IReadOnlyList<MultiplayerDifference> Differences);

public static class MultiplayerDetails
{
    public const int MaxBytes = 16 * 1024 * 1024;
    public const int MaxFiles = 50000;
    public static string Fingerprint(MultiplayerManifest report)
    {
        using var digest = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        void Add(string value) => digest.AppendData(Encoding.UTF8.GetBytes(value + "\n"));
        Add("PAW-MP1"); Add(report.Configuration); Add(report.GameBuild); Add(report.Executable.ToLowerInvariant());
        foreach (var module in report.Modules.OrderBy(x => x.Id, StringComparer.OrdinalIgnoreCase))
            Add($"{module.Id.ToLowerInvariant()}|{module.Version}|{module.Sha256.ToUpperInvariant()}");
        foreach (var file in report.Files.OrderBy(x => x.Path, StringComparer.OrdinalIgnoreCase))
            Add(file.Path.ToLowerInvariant() + "|" + file.Sha256.ToUpperInvariant());
        return "PAW-MP1-" + Convert.ToHexString(digest.GetHashAndReset());
    }

    public static async Task SaveAsync(string path, MultiplayerManifest report)
    {
        Validate(report);
        var data = JsonSerializer.SerializeToUtf8Bytes(report, LauncherJsonContext.Default.MultiplayerManifest);
        if (data.Length > MaxBytes) throw new InvalidDataException("Multiplayer report exceeds the supported size.");
        await File.WriteAllBytesAsync(path, data);
    }

    public static async Task<MultiplayerManifest> LoadAsync(string path)
    {
        await using var input = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (input.Length > MaxBytes) throw new InvalidDataException("Multiplayer report exceeds the supported size.");
        var data = new byte[(int)input.Length];
        await input.ReadExactlyAsync(data);
        var report = JsonSerializer.Deserialize(data, LauncherJsonContext.Default.MultiplayerManifest)
            ?? throw new InvalidDataException("Empty multiplayer report.");
        Validate(report);
        return report;
    }

    public static void Validate(MultiplayerManifest report)
    {
        static void Text(string? text, int limit)
        {
            if (string.IsNullOrWhiteSpace(text) || text.Length > limit || text.Any(char.IsControl))
                throw new InvalidDataException("Invalid text in multiplayer report.");
        }
        static void Relative(string? value)
        {
            Text(value, 700);
            if (value != CryptoAndIO.NormalizeRelativePath(value!) || Path.IsPathRooted(value)
                || value!.Contains(':') || value.Split('\\').Any(x => x is "" or "." or ".."))
                throw new InvalidDataException("Only relative game paths are allowed in multiplayer reports.");
        }
        static void Hash(string? value, bool missing = false)
        {
            if (missing && value == "MISSING") return;
            if (value is null || value.Length != 64 || !value.All(Uri.IsHexDigit)) throw new InvalidDataException("Invalid report hash.");
        }
        if (report.SchemaVersion != 1 || report.Modules is null || report.Files is null || report.IntegrityErrors is null
            || report.Modules.Count > 256 || report.Files.Count > MaxFiles || report.IntegrityErrors.Count > MaxFiles)
            throw new InvalidDataException("Unsupported multiplayer report.");
        Text(report.Configuration, 150); _ = ConfigurationCode.Parse(report.Configuration);
        Text(report.GameBuild, 40); Relative(report.Executable);
        if (report.Executable.Contains('\\')) throw new InvalidDataException("Invalid game executable name.");
        var ids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var module in report.Modules)
        {
            if (module is null) throw new InvalidDataException("Null module.");
            Text(module.Id, 100); Text(module.Version, 100); Hash(module.Sha256);
            if (!ids.Add(module.Id) || module.Id.Any(x => !char.IsAsciiLetterOrDigit(x) && x is not '-' and not '_' and not '.'))
                throw new InvalidDataException("Invalid or duplicate module.");
        }
        var paths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var file in report.Files)
        {
            if (file is null) throw new InvalidDataException("Null file.");
            Relative(file.Path); Hash(file.Sha256, true);
            if (!paths.Add(file.Path)) throw new InvalidDataException("Duplicate report file.");
        }
        foreach (var error in report.IntegrityErrors) Text(error, 1000);
        if (!paths.Contains("k2.exe") || !paths.Contains(report.Executable)) throw new InvalidDataException("Required executable is missing from report.");
        if (!string.Equals(report.Fingerprint, Fingerprint(report), StringComparison.Ordinal)) throw new InvalidDataException("Report fingerprint does not match its contents.");
    }

    public static MultiplayerComparison Compare(MultiplayerManifest local, MultiplayerManifest peer)
    {
        Validate(local); Validate(peer);
        var rows = new List<MultiplayerDifference>();
        void Field(string name, string a, string b) { if (a != b) rows.Add(new("setting", name, a, b)); }
        Field("Steam build", local.GameBuild, peer.GameBuild);
        Field("EXE", local.Executable, peer.Executable);
        var aConfig = local.Configuration.Split('-'); var bConfig = peer.Configuration.Split('-');
        string[] names = ["", "Channel", "Independent hostility", "Roaming spawn", "New roaming companies", "Siege balance", "Large maps", "Russian localization", "Player colors", "Desync handling", "Disable Powers and Shards"];
        for (var i = 1; i < names.Length; i++) Field(names[i], i < aConfig.Length ? aConfig[i] : "PS1", i < bConfig.Length ? bConfig[i] : "PS1");
        var aModules = local.Modules.ToDictionary(x => x.Id, StringComparer.OrdinalIgnoreCase);
        var bModules = peer.Modules.ToDictionary(x => x.Id, StringComparer.OrdinalIgnoreCase);
        string Module(MultiplayerModule? m) => m is null ? "-" : $"{m.Version} | {(m.Enabled ? "ON" : "OFF")} | {m.Priority} | {m.Sha256.ToUpperInvariant()}";
        foreach (var id in aModules.Keys.Union(bModules.Keys, StringComparer.OrdinalIgnoreCase).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
        {
            var a = Module(aModules.GetValueOrDefault(id)); var b = Module(bModules.GetValueOrDefault(id));
            if (a != b) rows.Add(new("module", id, a, b));
        }
        var aFiles = local.Files.ToDictionary(x => x.Path, StringComparer.OrdinalIgnoreCase);
        var bFiles = peer.Files.ToDictionary(x => x.Path, StringComparer.OrdinalIgnoreCase);
        foreach (var path in aFiles.Keys.Union(bFiles.Keys, StringComparer.OrdinalIgnoreCase).OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
        {
            var a = aFiles.GetValueOrDefault(path)?.Sha256.ToUpperInvariant() ?? "NOT_LISTED";
            var b = bFiles.GetValueOrDefault(path)?.Sha256.ToUpperInvariant() ?? "NOT_LISTED";
            if (a != b) rows.Add(new("file", path, a, b));
        }
        foreach (var error in local.IntegrityErrors) rows.Add(new("integrity", error, "ERROR", "-"));
        foreach (var error in peer.IntegrityErrors) rows.Add(new("integrity", error, "-", "ERROR"));
        return new(rows.Count == 0 && local.Fingerprint == peer.Fingerprint, rows);
    }
}

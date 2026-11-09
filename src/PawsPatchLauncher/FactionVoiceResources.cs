using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using PawsPatchLauncher.Rwd;

namespace PawsPatchLauncher;

public static class FactionVoiceResources
{
    static readonly Regex AudioBlocks = new(@"\[Audio\s+[^\]]*\]\s*\{(?<body>.*?)^\s*\}", RegexOptions.IgnoreCase | RegexOptions.Multiline | RegexOptions.Singleline);
    static readonly Regex IdField = new(@"^(\s*IDS\s*=\s*)([A-Za-z0-9_]+)", RegexOptions.IgnoreCase | RegexOptions.Multiline);
    static readonly Regex FilesField = new(@"^(\s*files\s*=\s*)([^\r\n]+)", RegexOptions.IgnoreCase | RegexOptions.Multiline);
    public static string NamespacePath(string language, string audioPath)
        => CryptoAndIO.NormalizeRelativePath("data/Audio/PawVoices/" + language + "/" + audioPath);
    static string AudioPath(string file)
    {
        var path = file.Replace('\\', '/');
        if (!path.StartsWith("data/Audio/", StringComparison.OrdinalIgnoreCase)
            || !(path.EndsWith(".wav", StringComparison.OrdinalIgnoreCase) || path.EndsWith(".mp3", StringComparison.OrdinalIgnoreCase)))
            throw new InvalidDataException("Unexpected speech package resource: " + file);
        return CryptoAndIO.NormalizeRelativePath(path[11..]).Replace('\\', '/');
    }
    static string Decode(byte[] bytes) => bytes.AsSpan().StartsWith(new byte[] { 0xff, 0xfe })
        ? Encoding.Unicode.GetString(bytes).TrimStart('\ufeff') : Encoding.UTF8.GetString(bytes).TrimStart('\ufeff');

    public static async Task<IReadOnlyDictionary<string, InstalledModule>> ComposeAsync(string game,
        IReadOnlyDictionary<string, InstalledModule> desired, UserSettings? settings, CancellationToken ct)
    {
        var result = desired.Where(p => !CustomVoices.IsGenerated(p.Key)).ToDictionary(p => p.Key, p => p.Value, StringComparer.OrdinalIgnoreCase);
        if (settings is null || GameLanguages.Voice(settings) != "custom") return result;
        CustomVoices.Validate(settings);
        var voices = result.Where(p => p.Key.StartsWith("game-voice-", StringComparison.OrdinalIgnoreCase)).ToDictionary(p => p.Key[11..], p => p.Value, StringComparer.Ordinal);
        if (new[] { "ru", "de", "fr" }.Any(l => !voices.ContainsKey(l))) throw new InvalidDataException("Custom faction speech requires all speech packages.");
        var basePath = Path.Combine(game, "Data.rwd");
        using var archive = RwdArchive.Open(basePath);
        var baseHash = await CryptoAndIO.Sha256Async(basePath, ct);
        var tables = archive.Entries.Where(e => e.Name.Replace('\\', '/').StartsWith("Audio/", StringComparison.OrdinalIgnoreCase)
            && e.Name.EndsWith(".tgi", StringComparison.OrdinalIgnoreCase)).ToDictionary(e => "data/" + e.Name.Replace('\\', '/'), e => archive.Read(e), StringComparer.OrdinalIgnoreCase);
        foreach (var (id, module) in result.OrderBy(p => p.Value.Priority).ThenBy(p => p.Key, StringComparer.OrdinalIgnoreCase))
        foreach (var file in module.Files)
        {
            var path = file.Path.Replace('\\', '/');
            if (!path.StartsWith("data/Audio/", StringComparison.OrdinalIgnoreCase) || !path.EndsWith(".tgi", StringComparison.OrdinalIgnoreCase)) continue;
            var source = CryptoAndIO.SafeChildPath(Path.Combine(game, ".pawpatch/packages", id, module.Version, "payload"), file.Path);
            tables[path] = await File.ReadAllBytesAsync(source, ct);
        }
        var identity = "faction-voices-2|" + baseHash + "|" + string.Join('|', voices.OrderBy(p => p.Key).Select(p => p.Key + ":" + p.Value.Version + ":" + p.Value.ArchiveSha256))
            + "|" + string.Join('|', tables.OrderBy(p => p.Key).Select(p => p.Key + ":" + Convert.ToHexString(SHA256.HashData(p.Value))));
        var version = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(identity)));
        var directory = Path.Combine(game, ".pawpatch/packages", CustomVoices.ModuleId, version);
        RemovalSafety.CheckNoLinks(directory); Directory.CreateDirectory(directory);
        var payload = Path.Combine(directory, "payload"); var manifestPath = Path.Combine(directory, "module.json");
        InstalledModule? generated = null;
        if (File.Exists(manifestPath))
        {
            try
            {
                var manifest = JsonSerializer.Deserialize(await File.ReadAllTextAsync(manifestPath, ct), LauncherJsonContext.Default.ModuleArchiveManifest)!;
                if (manifest.Id == CustomVoices.ModuleId && manifest.Version == version && manifest.Remove.Count == 0 && manifest.Files.Count is > 0 and < 20000 && manifest.Files.Count(f => f.Path.Replace('\\', '/').Equals("data/Audio/paws_faction_voices.tgi", StringComparison.OrdinalIgnoreCase)) == 1
                    && manifest.Files.All(f => f.Path.Replace('\\', '/').Equals("data/Audio/paws_faction_voices.tgi", StringComparison.OrdinalIgnoreCase)
                        || f.Path.Replace('\\', '/').StartsWith("data/Audio/PawVoices/", StringComparison.OrdinalIgnoreCase)
                            && (f.Path.EndsWith(".wav", StringComparison.OrdinalIgnoreCase) || f.Path.EndsWith(".mp3", StringComparison.OrdinalIgnoreCase))))
                {
                    var valid = true;
                    foreach (var file in manifest.Files)
                    {
                        var source = CryptoAndIO.SafeChildPath(payload, file.Path);
                        if (!File.Exists(source) || new FileInfo(source).Length != file.Size || !string.Equals(await CryptoAndIO.Sha256Async(source, ct), file.Sha256, StringComparison.OrdinalIgnoreCase)) { valid = false; break; }
                    }
                    if (valid) generated = new InstalledModule { Version = version, ArchiveSha256 = version, Enabled = true, Priority = 240, Files = manifest.Files };
                }
            }
            catch (Exception error) when (error is JsonException or InvalidDataException or IOException) { }
        }
        if (generated is null)
        {
            var files = new Dictionary<string, ModuleFile>(StringComparer.OrdinalIgnoreCase);
            async Task Write(string relative, byte[] bytes)
            {
                ct.ThrowIfCancellationRequested();
                relative = CryptoAndIO.NormalizeRelativePath(relative); var target = CryptoAndIO.SafeChildPath(payload, relative);
                RemovalSafety.CheckNoLinks(target); Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                await File.WriteAllBytesAsync(target, bytes, ct);
                files[relative] = new ModuleFile { Path = relative, Size = bytes.Length, Sha256 = Convert.ToHexString(SHA256.HashData(bytes)) };
            }
            var paths = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
            foreach (var (language, module) in voices)
            {
                paths[language] = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var file in module.Files)
                {
                    var relative = AudioPath(file.Path); paths[language].Add(relative);
                    var source = CryptoAndIO.SafeChildPath(Path.Combine(game, ".pawpatch/packages", "game-voice-" + language, module.Version, "payload"), file.Path);
                    await Write(NamespacePath(language, relative), await File.ReadAllBytesAsync(source, ct));
                }
            }
            paths["en"] = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var path in paths.Values.SelectMany(p => p).Distinct(StringComparer.OrdinalIgnoreCase).ToArray())
            {
                var entry = archive.Find("Audio/" + path); if (entry is null) continue;
                paths["en"].Add(path); await Write(NamespacePath("en", path), archive.Read(entry));
            }
            var definitions = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var table in tables.Values)
            foreach (Match block in AudioBlocks.Matches(Decode(table)))
            {
                var id = IdField.Match(block.Value); var list = FilesField.Match(block.Value);
                if (!id.Success || !list.Success) continue;
                var refs = list.Groups[2].Value.Split(',').Select(p => p.Trim().Trim('"').Replace('\\', '/')).ToArray();
                if (!refs.Any(p => paths.Values.Any(set => set.Contains(p)))) continue;
                if (refs.Any(p => !paths["en"].Contains(p))) continue; // A mod's unavailable recording keeps its original definition.
                definitions[id.Groups[2].Value] = block.Value;
            }
            if (definitions.Count == 0) throw new InvalidDataException("No faction speech definitions were found in this game.");
            // Kohan's TGI parser does not accept C-style line comments.
            var text = new StringBuilder();
            foreach (var (id, block) in definitions.OrderBy(p => p.Key))
            foreach (var language in GameLanguages.VoiceChoices)
            {
                var clone = IdField.Replace(block, m => m.Groups[1].Value + "paws_voice_" + language + "_" + id, 1);
                clone = FilesField.Replace(clone, m => m.Groups[1].Value + string.Join(", ", m.Groups[2].Value.Split(',').Select(p =>
                {
                    var path = p.Trim().Trim('"').Replace('\\', '/'); var actual = paths[language].Contains(path) ? language : "en";
                    return "PawVoices/" + actual + "/" + path;
                })), 1);
                text.AppendLine(clone);
            }
            await Write("data/Audio/paws_faction_voices.tgi", Encoding.Unicode.GetPreamble().Concat(Encoding.Unicode.GetBytes(text.ToString())).ToArray());
            generated = new InstalledModule { Version = version, ArchiveSha256 = version, Enabled = true, Priority = 240, Files = files.Values.OrderBy(f => f.Path).ToList() };
            var manifest = new ModuleArchiveManifest { Id = CustomVoices.ModuleId, Version = version, Files = generated.Files };
            await File.WriteAllTextAsync(manifestPath, JsonSerializer.Serialize(manifest, LauncherJsonContext.Default.ModuleArchiveManifest), ct);
        }
        result[CustomVoices.ModuleId] = generated;
        var common = CustomVoices.Language(settings, "other");
        foreach (var (language, module) in voices)
            result["game-voice-" + language] = new InstalledModule { Version = module.Version, ArchiveSha256 = module.ArchiveSha256, DownloadedAt = module.DownloadedAt,
                Priority = module.Priority, Enabled = module.Enabled, Files = language == common ? module.Files : [] };
        return result;
    }
}

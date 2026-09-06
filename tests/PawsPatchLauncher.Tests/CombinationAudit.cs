using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using PawsPatchLauncher;

// Read-only package audit: never extracts, installs, launches, uploads or changes a feed.
public static class CombinationAudit
{
    private sealed record PackageData(ModuleArchiveManifest Manifest, Dictionary<string, string?> Files, Dictionary<string, string> Text);
    private sealed record Collision(string A, string B, string Path, bool SameBytes, string Policy);
    private sealed record TranslationLoss(string Module, string Path, string[] MissingKeys);
    private static string N(string path) => CryptoAndIO.NormalizeRelativePath(path).ToLowerInvariant();
    private static readonly HashSet<string> Profiles = ["roaming-profile-standard-with-new", "roaming-profile-x4-no-new", "roaming-profile-standard-no-new"];
    private static readonly HashSet<string> DataOverlays = [..Profiles, "siege-balance-standard", "large-map-sizes-standard", "powers-shards-original"];
    private static string Policy(string a, string b, string path)
    {
        var pair = new HashSet<string> { a, b };
        if (pair.SetEquals(["arcane-wars", "pawpatch-core"])) return "reviewed-base";
        if ((a is "arcane-wars" or "pawpatch-core") && DataOverlays.Contains(b)
            || (b is "arcane-wars" or "pawpatch-core") && DataOverlays.Contains(a)) return "reviewed-data-profile";
        if (pair.SetEquals(["startup-base", "localization-ru"]) && path == "startup\\autoexec.txt") return "localized-startup";
        if (pair.Contains("common-ui") && (pair.Contains("pawpatch-core") && path == "k2_paws_family_herd_relations_1372.exe"
            || pair.Contains("desync-continue") && path is "k2_paws_sync_continue_1372.exe" or "k2_paws_sync_family_herd_relations_1372.exe")) return "combined-ui-executable";
        return "UNREVIEWED";
    }
    private static void Require(bool valid, string message) { if (!valid) throw new InvalidDataException(message); }

    public static async Task RunAsync(string repository, string reportRoot)
    {
        var repo = Path.GetFullPath(repository);
        var output = Path.GetFullPath(reportRoot);
        Require(output.StartsWith(repo + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase), "Report must remain inside the workspace.");
        Directory.CreateDirectory(output);
        var publicKey = await File.ReadAllTextAsync(Path.Combine(repo, ".local/signing/pawpatch-signing-public.pem"));
        var cache = new Dictionary<string, PackageData>(StringComparer.OrdinalIgnoreCase);
        var archiveEvidence = new List<object>();
        var feedEvidence = new List<object>();
        var rows = new List<object>();
        var sets = new List<object>();
        var allCollisions = new List<object>();
        var allLosses = new List<object>();
        var total = 0;
        foreach (var source in new[] { "published", "candidate", "fixed" })
        foreach (var name in new[] { "stable", "beta" })
        {
            var feedPath = Path.Combine(repo, source == "published" ? $"feed/{name}.json" : $"release_workspace_056/{(source == "fixed" ? "combination-fix" : "powers-shards")}/feed/{name}.signed.json");
            var bytes = await File.ReadAllBytesAsync(feedPath);
            var envelope = JsonSerializer.Deserialize(bytes, LauncherJsonContext.Default.SignedFeedEnvelope)!;
            var payload = Convert.FromBase64String(envelope.Payload);
            Require(CryptoAndIO.VerifySignature(payload, envelope.Signature, publicKey), "Invalid signature: " + feedPath);
            var feed = JsonSerializer.Deserialize(payload, LauncherJsonContext.Default.ChannelManifest)!;
            Require(feed.Channel == name, "Wrong channel.");
            feedEvidence.Add(new { source, channel = name, path = feedPath, sha256 = Convert.ToHexString(SHA256.HashData(bytes)) });
            var modules = new Dictionary<string, PackageData>();
            foreach (var package in feed.Packages)
            {
                var key = package.Id + ":" + package.Sha256;
                if (!cache.TryGetValue(key, out var data))
                {
                    var url = package.Urls[0];
                    var filename = Uri.TryCreate(url, UriKind.Absolute, out var uri) && uri.Scheme is "https" or "http" ? Path.GetFileName(uri.AbsolutePath) : Path.GetFileName(url);
                    var candidates = new[] { Path.Combine(repo, "packages", filename), Path.Combine(repo, "release_workspace_20260905/packages", filename), Path.Combine(repo, "release_workspace_056/powers-shards/packages", filename), Path.Combine(repo, "release_workspace_056/combination-fix/packages", filename) };
                    var archivePath = candidates.FirstOrDefault(File.Exists) ?? throw new FileNotFoundException("No local package: " + filename);
                    Require(new FileInfo(archivePath).Length == package.Size && (await CryptoAndIO.Sha256Async(archivePath)).Equals(package.Sha256, StringComparison.OrdinalIgnoreCase), "Wrong local archive bytes: " + filename);
                    using var archive = ZipFile.OpenRead(archivePath);
                    var entries = archive.Entries.ToDictionary(e => N(e.FullName), StringComparer.OrdinalIgnoreCase);
                    using var manifestStream = entries["module.json"].Open();
                    var manifest = await JsonSerializer.DeserializeAsync(manifestStream, LauncherJsonContext.Default.ModuleArchiveManifest) ?? throw new InvalidDataException("No module manifest.");
                    Require(manifest.Id == package.Id && manifest.Version == package.Version, "Wrong module identity.");
                    data = new PackageData(manifest, new(StringComparer.OrdinalIgnoreCase), new(StringComparer.OrdinalIgnoreCase));
                    foreach (var file in manifest.Files)
                    {
                        var path = N(file.Path);
                        CryptoAndIO.SafeChildPath(Path.Combine(output, "virtual-root"), path);
                        var entry = entries["payload\\" + path];
                        await using var stream = entry.Open();
                        Require(entry.Length == file.Size && Convert.ToHexString(await SHA256.HashDataAsync(stream)).Equals(file.Sha256, StringComparison.OrdinalIgnoreCase), "Wrong payload hash: " + package.Id + "/" + path);
                        data.Files.Add(path, file.Sha256.ToUpperInvariant());
                        if (path.EndsWith(".tgi") || path == "startup\\autoexec.txt")
                        { using var reader = new StreamReader(entry.Open()); data.Text.Add(path, await reader.ReadToEndAsync()); }
                    }
                    foreach (var path in manifest.Remove) { CryptoAndIO.SafeChildPath(Path.Combine(output, "virtual-root"), path); data.Files.Add(N(path), null); }
                    cache.Add(key, data);
                    archiveEvidence.Add(new { package.Id, package.Version, package.Sha256, package.Size, files = manifest.Files.Count, removals = manifest.Remove.Count });
                    Console.WriteLine($"VERIFIED {package.Id} {manifest.Files.Count} payloads");
                }
                modules.Add(package.Id, data);
            }
            // The combined roaming profile must include BOTH changes, not just whichever loads last.
            var joint = new Dictionary<string, string?>(modules["roaming-profile-standard-with-new"].Files);
            foreach (var file in modules["roaming-profile-x4-no-new"].Files) joint[file.Key] = file.Value;
            Require(joint.Count == modules["roaming-profile-standard-no-new"].Files.Count && joint.All(p => modules["roaming-profile-standard-no-new"].Files.GetValueOrDefault(p.Key) == p.Value), "Combined roaming package lost one option.");

            var core = modules["pawpatch-core"];
            var losses = new List<TranslationLoss>();
            foreach (var package in modules.Where(p => DataOverlays.Contains(p.Key)))
            foreach (var file in package.Value.Text.Where(f => core.Text.ContainsKey(f.Key)))
            {
                HashSet<string> Keys(string text) => Regex.Matches(text, @"#awloc_[A-Za-z0-9_]+").Select(m => m.Value).ToHashSet();
                var lost = Keys(core.Text[file.Key]); lost.ExceptWith(Keys(file.Value));
                if (lost.Count > 0) losses.Add(new(package.Key, file.Key, lost.Order().ToArray()));
            }
            allLosses.Add(new { source, channel = name, losses });
            var collisions = new Dictionary<string, Collision>();
            var accepted = 0; var unsupported = 0; var untranslated = 0; var missingOptional = 0;
            // Eight binary options. The real code parser determines supported color combinations.
            for (var bits = 0; bits < 256; bits++)
            {
                bool Bit(int bit) => (bits & (1 << bit)) != 0;
                var settings = new UserSettings { Channel = name, RussianLocalization = Bit(0), CustomPlayerColors = Bit(1), DesyncMode = Bit(2) ? "continue" : "official",
                    IndependentHostility = Bit(3), RoamingSpawnMode = Bit(4) ? "x4" : "standard", AdditionalRoamingCompanies = Bit(5), SiegeBalance = Bit(6), DisablePowersAndShards = Bit(7) };
                if (settings.CustomPlayerColors && (name != "beta" || !settings.IndependentHostility || settings.DesyncMode != "official")) { unsupported++; continue; }
                var code = ConfigurationCode.Create(settings);
                try { _ = ConfigurationCode.Parse(code); } catch (FormatException) { unsupported++; continue; }
                if (!settings.DisablePowersAndShards && !modules.ContainsKey("powers-shards-original")) { missingOptional++; continue; }
                var selected = GamePackageSelector.Select(feed, settings, settings.RussianLocalization, settings.CustomPlayerColors);
                Require(selected.Count(p => Profiles.Contains(p.Id)) == (settings.RoamingSpawnMode == "x4" && settings.AdditionalRoamingCompanies ? 0 : 1), "Multiple roaming variants selected: " + code);
                Require(!selected.Any(p => p.Id == "large-map-sizes-standard"), "Always-on large maps were reverted.");
                foreach (var package in selected) Require(package.DependsOn.All(d => selected.Any(p => p.Id == d)), "Unresolved dependency.");
                var winners = new Dictionary<string, (string Id, string? Hash)>(StringComparer.OrdinalIgnoreCase);
                var providers = new Dictionary<string, List<(string Id, string? Hash)>>(StringComparer.OrdinalIgnoreCase);
                foreach (var package in selected.OrderBy(p => p.Priority).ThenBy(p => p.Id, StringComparer.OrdinalIgnoreCase))
                foreach (var file in modules[package.Id].Files)
                {
                    if (!providers.TryGetValue(file.Key, out var prior)) providers[file.Key] = prior = [];
                    foreach (var other in prior)
                    {
                        var policy = other.Hash == file.Value ? "identical-bytes" : Policy(other.Id, package.Id, file.Key);
                        var collision = new Collision(other.Id, package.Id, file.Key, other.Hash == file.Value, policy);
                        collisions[other.Id + "|" + package.Id + "|" + file.Key] = collision;
                        Require(policy != "UNREVIEWED", "Unreviewed co-selected file collision: " + collision);
                    }
                    prior.Add((package.Id, file.Value)); winners[file.Key] = (package.Id, file.Value);
                }
                // Match the installer's actual per-file precedence, including removals.
                var state = new InstallState { Modules = selected.ToDictionary(p => p.Id, p => new InstalledModule { Enabled = true, Priority = p.Priority, Files = modules[p.Id].Manifest.Files, Remove = modules[p.Id].Manifest.Remove }) };
                var installed = MultiplayerCheck.Expected(state);
                Require(installed.Count == winners.Count && installed.All(p => winners[N(p.Key)].Hash == p.Value?.Sha256.ToUpperInvariant()), "Audit disagrees with installer precedence.");
                var exe = GameExecutableSelector.Select(new(), settings.CustomPlayerColors, settings.DesyncMode == "continue", settings.IndependentHostility, GameExecutableSelector.HasCommonUi(feed));
                Require(exe == "k2.exe" || winners.TryGetValue(N(exe), out var binary) && binary.Hash is not null, "Selected EXE is absent: " + code);
                if (GameExecutableSelector.HasCommonUi(feed) && !settings.CustomPlayerColors) Require(winners[N(exe)].Id == "common-ui", "Common UI helper was overwritten.");
                var startup = modules[winners["startup\\autoexec.txt"].Id].Text["startup\\autoexec.txt"];
                Require(startup.Contains("adddepot %USERDATA%/data/ 1", StringComparison.OrdinalIgnoreCase), "Writable work depot missing.");
                Require(Regex.IsMatch(startup, @"(?m)^[ \t]*addlocaledepot[ \t]+localized/RU/Local_ru\.rwd") == settings.RussianLocalization, "Startup localization differs from setting.");
                var damaged = settings.RussianLocalization ? losses.Where(l => winners.GetValueOrDefault(l.Path).Id == l.Module).ToArray() : [];
                if (damaged.Length > 0) untranslated++;
                rows.Add(new { source, channel = name, code, modules = selected.Select(p => p.Id).ToArray(), executable = exe, translationKeyLossFiles = damaged.Select(d => d.Path).ToArray() });
                accepted++; total++;
            }
            if (source == "fixed") Require(untranslated == 0, "Fixed candidate still loses translation keys.");
            allCollisions.Add(new { source, channel = name, collisions = collisions.Values });
            sets.Add(new { source, channel = name, accepted, unsupported, unavailableRestoration = missingOptional, configurationsWithTranslationKeyLoss = untranslated, uniqueCoSelectedCollisions = collisions.Count, roamingCompositionFiles = joint.Count });
            Console.WriteLine($"COMBINATIONS {source}/{name}: {accepted} supported, {unsupported} rejected, {missingOptional} unavailable; {untranslated} lose translation keys; roaming composition {joint.Count} files matches");
        }
        // A future second balance toggle sharing a siege file must NOT pass by priority alone.
        Require(Policy("siege-balance-standard", "future-balance", "data\\units\\royalistaw\\aw_dragonfire_balistae.tgi") == "UNREVIEWED", "Future overlaps are silently allowed.");
        var report = new { generatedUtc = DateTimeOffset.UtcNow, scope = "Signed local package bytes and all supported selection/precedence combinations. No game launched or installed. Translation-loss findings are not waived.", totalConfigurations = total, newOverlapGuardProbePassed = true, feeds = feedEvidence, archives = archiveEvidence, sets, collisions = allCollisions, translationLoss = allLosses, configurations = rows };
        var reportPath = Path.Combine(output, "combinations.json");
        await File.WriteAllTextAsync(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("AUDIT COMPLETE " + reportPath + "; fixed candidate has no translation-key losses; historical findings retained; not a gameplay pass");
    }
}

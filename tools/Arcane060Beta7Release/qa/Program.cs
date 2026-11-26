using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class Program
{
    private static readonly JsonSerializerOptions Json = new() { PropertyNameCaseInsensitive = true, WriteIndented = true };
    private static readonly string[] Changed = ["pawpatch-core", "common-ui", "player-colors", "desync-continue"];
    private static readonly string[] Texts = ["en", "ru", "de", "fr", "cs", "uk"];
    private static readonly string[] Voices = ["en", "ru", "de", "fr"];
    private const long FixtureBudgetBytes = 3L * 1024 * 1024 * 1024;
    private static long Checks, Selections, FeatureCases, InstalledFiles;
    private static long PeakObservedFixtureBytes;
    private static readonly List<object> Stages = [];
    private static readonly Dictionary<string, object> PackageAssets = new(StringComparer.OrdinalIgnoreCase);
    private static readonly HashSet<string> InstalledHelpersSeen = new(StringComparer.OrdinalIgnoreCase);
    private static Inputs Input = null!;
    private static string Fixture = "";

    private static void Check(bool value, string label)
    {
        Checks++;
        if (!value) throw new InvalidDataException(label);
    }
    private static string N(string path) => path.Replace('\\', '/').ToLowerInvariant();
    private static string HelperOwner(string exe, IReadOnlyDictionary<string, ModuleArchiveManifest> manifests)
        => manifests["common-ui"].Files.Any(f => N(f.Path) == N(exe)) ? "common-ui" : "player-colors";
    private static T Read<T>(string path) => JsonSerializer.Deserialize<T>(File.ReadAllText(path), Json)!;
    private static string Identity<T>(T value) => JsonSerializer.Serialize(value, Json);
    private static string FileHash(string path)
    {
        using var s = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(s));
    }
    private static void PhysicalG(string path)
    {
        path = Path.GetFullPath(path);
        Check(Path.GetPathRoot(path)!.Equals("G:\\", StringComparison.OrdinalIgnoreCase), "Fixture/output must be G: " + path);
        for (var p = path; p is not null; p = Path.GetDirectoryName(p))
            if (Directory.Exists(p)) Check((File.GetAttributes(p) & FileAttributes.ReparsePoint) == 0, "Physical G required: " + p);
    }
    private static ChannelManifest Signed(string path, LauncherConfiguration configuration)
    {
        var envelope = Read<SignedFeedEnvelope>(path);
        var payload = Convert.FromBase64String(envelope.Payload);
        using var key = ECDsa.Create();
        key.ImportFromPem(configuration.PublicKeyPem);
        Check(key.VerifyData(payload, Convert.FromBase64String(envelope.Signature), HashAlgorithmName.SHA256,
            DSASignatureFormat.IeeeP1363FixedFieldConcatenation), "Feed signature " + path);
        return JsonSerializer.Deserialize(payload, LauncherJsonContext.Default.ChannelManifest)!;
    }
    private static InstallState State(IEnumerable<PackageRelease> selected, UserSettings settings) => new()
    {
        AppliedSettings = settings,
        Modules = selected.ToDictionary(p => p.Id, p => new InstalledModule { Enabled = true, Version = p.Version, ArchiveSha256 = p.Sha256, Priority = p.Priority }, StringComparer.OrdinalIgnoreCase)
    };
    private static UserSettings Preferences(string mod, string channel, bool patch, bool data, string text, string voice, string spawn, int bits)
    {
        bool B(int b) => (bits & (1 << b)) != 0;
        var s = new UserSettings { Mod = mod, Channel = channel, PawPatchEnabled = patch, VanillaPawPatchEnabled = patch,
            ImmortalsPawPatchEnabled = patch, DataOnly = data, GameTextLanguage = text, RussianLocalization = text == "ru", GameVoiceLanguage = voice,
            CustomPlayerColors = B(0), DesyncMode = B(1) ? "continue" : "official", IndependentHostility = B(2),
            AdditionalRoamingCompanies = B(3), SiegeBalance = B(4), DisablePowersAndShards = B(5), ImprovedAi = B(6), IgnoreZeroMorale = B(7),
            RoamingSpawnMode = spawn };
        var pure = GameMod.PureComponents(s);
        pure.Colors = B(0); pure.IgnoreDesync = B(1); pure.IndependentHostility = B(2); pure.AdditionalRoamingCompanies = B(3);
        pure.WoundedLairDefenders = B(5); pure.ImprovedAi = B(6); pure.RoamingSpawnMode = spawn;
        return s;
    }
    private static void CatalogMatrix(Dictionary<string, ChannelManifest> before, Dictionary<string, ChannelManifest> after, LauncherConfiguration configuration,
        Dictionary<string, ModuleArchiveManifest> newManifests)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var channel in new[] { "stable", "beta" })
        {
            if (channel == "stable") Check(File.ReadAllBytes(Input.Feeds["before"][channel]).AsSpan()
                .SequenceEqual(File.ReadAllBytes(Input.Feeds["after"][channel])), "Signed stable feed bytes changed");
            Check(Identity(before[channel].Launcher) == Identity(after[channel].Launcher)
                && Identity(before[channel].Game) == Identity(after[channel].Game)
                && Identity(before[channel].ModGames) == Identity(after[channel].ModGames)
                && Identity(before[channel].ModGuides) == Identity(after[channel].ModGuides), "Launcher/game/mod guide metadata changed");
            var old = before[channel].Packages.ToDictionary(p => p.Id);
            var next = after[channel].Packages.ToDictionary(p => p.Id);
            Check(old.Keys.Order().SequenceEqual(next.Keys.Order()), "Catalog package IDs changed");
            var changed = old.Keys.Where(id => Identity(old[id]) != Identity(next[id])).Order().ToArray();
            Check(changed.SequenceEqual(channel == "beta" ? Changed.Order() : Enumerable.Empty<string>()), "Only four Arcane beta identities may change");
            foreach (var id in changed)
            {
                Check(old[id].Version == "0.6.0-beta.6" && next[id].Version == "0.6.0-beta.7", "Release lineage " + id);
                Check(next[id].Mods.Contains(GameMod.ArcaneWars) && !next[id].Mods.Contains(GameMod.Vanilla) && !next[id].Mods.Contains(GameMod.Immortals), "Changed package mod scope " + id);
            }
            foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
            foreach (var patch in new[] { false, true }) foreach (var data in new[] { false, true })
            foreach (var text in Texts) foreach (var voice in Voices) foreach (var spawn in new[] { "standard", "x2", "x4" })
            for (var bits = 0; bits < (patch && !data ? 64 : 1); bits++)
            {
                // Full 64-way Cartesian runtime options. Additional AI/morale
                // values vary independently over spawn/voice dimensions.
                var featureBits = bits | (spawn == "x2" ? 64 : 0) | (voice == "ru" ? 128 : 0);
                var pref = Preferences(mod, channel, patch, data, text, voice, spawn, featureBits);
                var remembered = Identity(pref);
                var a = EffectiveSettings.ForFeed(pref, before[channel]);
                var b = EffectiveSettings.ForFeed(pref, after[channel]);
                Check(Identity(pref) == remembered, "Preferences mutated");
                Check(Identity(a) == Identity(b), "Effective settings changed");
                var x = GamePackageSelector.Select(before[channel], a, a.RussianLocalization, a.CustomPlayerColors);
                var y = GamePackageSelector.Select(after[channel], b, b.RussianLocalization, b.CustomPlayerColors);
                Selections++;
                Check(x.Select(p => p.Id).Order().SequenceEqual(y.Select(p => p.Id).Order()), "Selection IDs changed");
                Check(y.All(p => ReferenceEquals(p, next[p.Id])), "Selector invented package metadata");
                var exe = GameExecutableSelector.Select(configuration, b, after[channel]);
                Check(exe == GameExecutableSelector.Select(configuration, a, before[channel]), "Executable choice changed");
                var previous = State(x, a);
                var expected = y.Any(p => old[p.Id].Version != p.Version || old[p.Id].Sha256 != p.Sha256 || old[p.Id].Priority != p.Priority);
                Check(UpdateDetector.HasModuleChanges(previous, y) == expected, "Update module detection");
                Check(UpdateDetector.HasRemoteUpdate(previous, y, _ => false) == expected, "Beta6 remote update offer");
                Check(UpdateDetector.NeedsDownload(previous, y, _ => false) == expected, "Download detection");
                Check(!UpdateDetector.NeedsDownload(previous, y, _ => true), "Cached update still downloading");
                Check(UpdateDetector.HasSettingsChanges(previous, y, b) == expected, "Settings update detection");
                var current = State(y, b);
                Check(!UpdateDetector.HasModuleChanges(current, y) && !UpdateDetector.HasRemoteUpdate(current, y, _ => false)
                    && !UpdateDetector.NeedsDownload(current, y, _ => false) && !UpdateDetector.HasSettingsChanges(current, y, b), "Beta7 not satisfied");
                if (mod != GameMod.ArcaneWars || channel == "stable") Check(!expected, "Unrelated mod/stable changed");
                if (mod == GameMod.ArcaneWars && channel == "beta" && patch && !data)
                {
                    Check(Input.Helpers.ContainsKey(exe), "Unexpected Arcane helper " + exe);
                    var providers = y.Where(p => newManifests.ContainsKey(p.Id)).OrderBy(p => p.Priority).ThenBy(p => p.Id, StringComparer.OrdinalIgnoreCase)
                        .SelectMany(p => newManifests[p.Id].Files.Where(f => N(f.Path) == N(exe)).Select(f => (p.Id, f.Sha256))).ToArray();
                    Check(providers.Length != 0 && providers[^1].Id == HelperOwner(exe, newManifests), "Wrong helper package priority " + exe);
                    Check(providers[^1].Sha256.Equals(Input.Helpers[exe], StringComparison.OrdinalIgnoreCase), "Wrong production helper hash");
                    seen.Add(exe);
                }
            }
        }
        Check(Selections == 28944, "Matrix dimensions incomplete");
        Check(seen.SetEquals(Input.Helpers.Keys), "Not all eight production helpers covered");
        Stages.Add(new { stage = "catalog-matrix", selections = Selections, helpers = seen.Order().ToArray() });
        Console.WriteLine($"CATALOG_MATRIX_PASS {Selections} profiles; {Checks} assertions; {seen.Count} Arcane helpers");
    }
    private static void FeatureBoundaries(Dictionary<string, ChannelManifest> before, Dictionary<string, ChannelManifest> after, LauncherConfiguration configuration)
    {
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (var channel in new[] { "stable", "beta" }) foreach (var patch in new[] { false, true }) foreach (var data in new[] { false, true })
        for (var flags = 0; flags < 4; flags++)
        {
            var preference = Preferences(mod, channel, patch, data, "en", "en", "standard", 3 | ((flags & 1) != 0 ? 64 : 0) | ((flags & 2) != 0 ? 128 : 0));
            var a = EffectiveSettings.ForFeed(preference, before[channel]);
            var b = EffectiveSettings.ForFeed(preference, after[channel]);
            var x = GamePackageSelector.Select(before[channel], a, false, a.CustomPlayerColors);
            var y = GamePackageSelector.Select(after[channel], b, false, b.CustomPlayerColors);
            Check(Identity(a) == Identity(b), "AI/morale boundary effective settings changed");
            Check(x.Select(p => p.Id).Order().SequenceEqual(y.Select(p => p.Id).Order()), "AI/morale boundary package selection changed");
            Check(GameExecutableSelector.Select(configuration, a, before[channel]) == GameExecutableSelector.Select(configuration, b, after[channel]), "AI/morale boundary helper changed");
            Check((flags & 1) != 0 || !b.ImprovedAi, "Disabled AI activated");
            Check((flags & 2) != 0 || !b.IgnoreZeroMorale, "Disabled zero morale activated");
            if (mod != GameMod.ArcaneWars || !patch || data) Check(!b.IgnoreZeroMorale, "Inactive zero morale escaped its mode");
            if (data || !patch) Check(!b.ImprovedAi, "Inactive AI escaped its mode");
            FeatureCases++;
        }
        Check(FeatureCases == 96, "AI/morale boundary dimensions incomplete");
        Stages.Add(new { stage = "ai-morale-boundaries", cases = FeatureCases });
    }
    private static ModuleArchiveManifest Manifest(string path)
    {
        using var z = ZipFile.OpenRead(path);
        using var s = z.GetEntry("module.json")!.Open();
        return JsonSerializer.Deserialize(s, LauncherJsonContext.Default.ModuleArchiveManifest)!;
    }
    private static Dictionary<string, (string Id, ModuleFile? File)> Winners(IReadOnlyDictionary<string, InstalledModule> modules)
    {
        var winners = new Dictionary<string, (string, ModuleFile?)>(StringComparer.OrdinalIgnoreCase);
        foreach (var pair in modules.Where(p => p.Value.Enabled).OrderBy(p => p.Value.Priority).ThenBy(p => p.Key, StringComparer.OrdinalIgnoreCase))
        {
            foreach (var path in pair.Value.Remove) winners[N(path)] = (pair.Key, null);
            foreach (var file in pair.Value.Files) winners[N(file.Path)] = (pair.Key, file);
        }
        return winners;
    }
    private static void Budget()
    {
        var bytes = Directory.EnumerateFiles(Fixture, "*", SearchOption.AllDirectories).Sum(p => new FileInfo(p).Length);
        PeakObservedFixtureBytes = Math.Max(PeakObservedFixtureBytes, bytes);
        Check(bytes < FixtureBudgetBytes, "Private real-package fixture exceeded 3 GiB cloning budget: " + bytes);
    }
    private static async Task VerifyInstalled(ModuleInstaller installer, IReadOnlyDictionary<string, InstalledModule> desired, string stage, bool pins)
    {
        var errors = await installer.VerifyAsync();
        Check(errors.Count == 0, stage + " installer Verify: " + string.Join(", ", errors.Take(3)));
        var actual = installer.LoadState();
        Check(actual.Modules.Keys.Order().SequenceEqual(desired.Keys.Order()), stage + " actual module list");
        foreach (var (id, m) in desired) Check(actual.Modules[id].Enabled && actual.Modules[id].Version == m.Version
            && actual.Modules[id].ArchiveSha256 == m.ArchiveSha256 && actual.Modules[id].Priority == m.Priority, stage + " state " + id);
        foreach (var (path, row) in Winners(desired))
        {
            var target = Path.Combine(Fixture, path);
            Check(row.File is null ? !File.Exists(target) : File.Exists(target) && FileHash(target).Equals(row.File.Sha256, StringComparison.OrdinalIgnoreCase), stage + " payload " + path);
            InstalledFiles++;
        }
        foreach (var path in Input.HdRemovals) Check(!File.Exists(Path.Combine(Fixture, path)), stage + " HD removal " + path);
        if (pins)
        {
            var winners = Winners(desired);
            var helpers = Input.Helpers.Keys.Select(N).ToHashSet(StringComparer.OrdinalIgnoreCase);
            foreach (var (path, hash) in Input.Pins)
            {
                var target = Path.Combine(Fixture, path);
                if (helpers.Contains(N(path)) && (!winners.TryGetValue(N(path), out var selected) || selected.File is null))
                {
                    // Disabled color helpers are normally removed. If this
                    // exact path existed before installation, its original
                    // bytes are restored instead of an installed helper.
                    var original = actual.Originals.FirstOrDefault(p => N(p.Key) == N(path)).Value;
                    Check(original is { Existed: true }
                        ? File.Exists(target) && FileHash(target).Equals(original.Sha256, StringComparison.OrdinalIgnoreCase)
                        : !File.Exists(target), stage + " unselected helper absent/original " + path);
                    continue;
                }
                Check(File.Exists(target) && FileHash(target).Equals(hash, StringComparison.OrdinalIgnoreCase), stage + " accepted production pin " + path);
                if (helpers.Contains(N(path))) InstalledHelpersSeen.Add(N(path));
            }
            // Full upgrade/reapply stages must really install all eight;
            // conditional helper checks cannot make this assertion vacuous.
            if (desired.ContainsKey("player-colors")) Check(Input.Helpers.Keys.All(p => winners.TryGetValue(N(p), out var row) && row.File is not null), stage + " full eight-helper coverage");
        }
        Budget();
        Stages.Add(new { stage, modules = desired.Count, verifiedFiles = Winners(desired).Count, pins });
        Console.WriteLine("INSTALLER_STAGE_PASS " + stage);
    }
    private static async Task Installer(ChannelManifest oldFeed, ChannelManifest newFeed, Dictionary<string, ModuleArchiveManifest> oldManifests,
        Dictionary<string, ModuleArchiveManifest> newManifests, LauncherConfiguration configuration)
    {
        Fixture = Path.Combine(Input.Output, "fixtures", Guid.NewGuid().ToString("N"));
        PhysicalG(Fixture); Check(!Directory.Exists(Fixture), "Fixture must be new and private"); Directory.CreateDirectory(Fixture);
        var oldPackages = oldFeed.Packages.Where(p => Changed.Contains(p.Id)).ToArray();
        var newPackages = newFeed.Packages.Where(p => Changed.Contains(p.Id)).ToArray();
        Check(oldPackages.Length == 4 && newPackages.Length == 4, "Four real packages required");
        foreach (var id in Changed) Check(oldManifests[id].Remove.Select(N).ToHashSet().SetEquals(newManifests[id].Remove.Select(N)), "Removal rules changed " + id);
        Check(Input.HdRemovals.Select(N).Distinct().Count() == 1132 && Input.HdRemovals.All(p => newManifests["common-ui"].Remove.Any(n => N(n) == N(p))), "1132 HD removals preserved");
        var original = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        void Sentinel(string relative)
        {
            var path = Path.Combine(Fixture, relative); Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(path, "PRIVATE-QA-ORIGINAL:" + relative, new UTF8Encoding(false)); original[N(relative)] = FileHash(path);
        }
        foreach (var path in Input.HdRemovals) Sentinel(path);
        Sentinel(Input.Helpers.Keys.Order().First()); Sentinel("qa-user-unmanaged-sentinel.txt");
        var installer = new ModuleInstaller(Fixture);
        async Task<Dictionary<string, InstalledModule>> Prepare(PackageRelease[] packages, string which)
        {
            var result = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase);
            foreach (var p in packages)
            {
                var archive = which == "old" ? Input.Archives[p.Id].Old : Input.Archives[p.Id].New;
                var actualSha256 = FileHash(archive);
                Check(new FileInfo(archive).Length == p.Size && actualSha256.Equals(p.Sha256, StringComparison.OrdinalIgnoreCase), "Signed archive hash " + p.Id);
                PackageAssets[which + ":" + p.Id] = new { id = p.Id, version = p.Version, path = archive,
                    sha256 = actualSha256, signedSha256 = p.Sha256, size = new FileInfo(archive).Length };
                result[p.Id] = await installer.PrepareAsync(p, archive);
                Check(installer.IsPrepared(p), "Prepare marker " + p.Id);
            }
            return result;
        }
        var old = await Prepare(oldPackages, "old");
        await installer.ReconcileAsync(old); await VerifyInstalled(installer, old, "beta6-real-install", false);
        var next = await Prepare(newPackages, "new");
        Check(UpdateDetector.HasRemoteUpdate(installer.LoadState(), newPackages, _ => false), "Actual beta6 installation update not offered");
        await installer.ReconcileAsync(next); await VerifyInstalled(installer, next, "beta7-real-upgrade", true);
        Check(!UpdateDetector.HasModuleChanges(installer.LoadState(), newPackages) && !UpdateDetector.HasRemoteUpdate(installer.LoadState(), newPackages, _ => false), "Actual beta7 not satisfied");
        foreach (var bits in Enumerable.Range(0, 4))
        {
            var active = EffectiveSettings.ForFeed(Preferences(GameMod.ArcaneWars, "beta", true, false, "en", "en", "standard", bits), newFeed);
            var desired = next.Where(p => p.Key is "pawpatch-core" or "common-ui" || p.Key == "player-colors" && (bits & 1) != 0
                || p.Key == "desync-continue" && (bits & 2) != 0).ToDictionary(p => p.Key, p => p.Value, StringComparer.OrdinalIgnoreCase);
            await installer.ReconcileAsync(desired, settings: active, releaseId: "0.6.0-beta.7");
            await VerifyInstalled(installer, desired, "helper-config-" + bits, true);
            var exe = GameExecutableSelector.Select(configuration, active, newFeed);
            var winner = Winners(desired)[N(exe)];
            Check(winner.Id == HelperOwner(exe, newManifests) && winner.File!.Sha256.Equals(Input.Helpers[exe], StringComparison.OrdinalIgnoreCase), "Live helper package priority " + exe);
            Check(FileHash(Path.Combine(Fixture, exe)).Equals(Input.Helpers[exe], StringComparison.OrdinalIgnoreCase), "Live selected helper " + exe);
        }
        void Originals(string stage)
        {
            foreach (var (path, hash) in original) Check(File.Exists(Path.Combine(Fixture, path)) && FileHash(Path.Combine(Fixture, path)) == hash, stage + " original sentinel " + path);
            var live = Directory.EnumerateFiles(Fixture, "*", SearchOption.AllDirectories).Select(p => N(Path.GetRelativePath(Fixture, p)))
                .Where(p => !p.StartsWith(".pawpatch/")).ToHashSet(StringComparer.OrdinalIgnoreCase);
            Check(live.SetEquals(original.Keys), stage + " exact original file set");
            Check(installer.LoadState().Modules.Count == 0, stage + " modules not disabled"); Budget();
            Stages.Add(new { stage, originalFiles = original.Count });
        }
        var empty = new Dictionary<string, InstalledModule>(StringComparer.OrdinalIgnoreCase);
        await installer.ReconcileAsync(empty); Originals("all-off-originals-exact");
        await new PatchRecovery(Fixture).RollbackAsync(installer.LoadState());
        await VerifyInstalled(installer, next, "rollback-disable-transaction", true);
        Check(FileHash(Path.Combine(Fixture, "qa-user-unmanaged-sentinel.txt")) == original["qa-user-unmanaged-sentinel.txt"], "Rollback altered unmanaged sentinel");
        await installer.ReconcileAsync(empty); Originals("all-off-again-originals-exact");
        await installer.ReconcileAsync(next); await VerifyInstalled(installer, next, "reapply", true);
        Check(InstalledHelpersSeen.SetEquals(Input.Helpers.Keys.Select(N)), "Not all eight helpers SHA-checked in real installation");
    }
    private static async Task UpgradeExistingPrivate(ChannelManifest after)
    {
        const string root = "G:/PawsWork/QA/ArcaneFix-20261125/game";
        PhysicalG(root);
        void Closed()
        {
            foreach (var p in System.Diagnostics.Process.GetProcessesByName("k2"))
                using (p) if (string.Equals(p.MainModule?.FileName, Path.Combine(root, "k2.exe").Replace('/', '\\'), StringComparison.OrdinalIgnoreCase))
                    throw new IOException("Owned private game is running");
        }
        Closed();
        var installer = new ModuleInstaller(root);
        var before = installer.LoadState();
        Check(before.Modules["pawpatch-core"].Version == "0.6.0-beta.6", "Private upgrade baseline");
        File.WriteAllText(Path.Combine(Input.Output, "private-state-before.json"), Identity(before));
        var desired = before.Modules.ToDictionary(p => p.Key, p => p.Value, StringComparer.OrdinalIgnoreCase);
        foreach (var p in after.Packages.Where(p => Changed.Contains(p.Id)))
        {
            var prepared = await installer.PrepareAsync(p, Input.Archives[p.Id].New);
            prepared.Enabled = before.Modules.TryGetValue(p.Id, out var old) ? old.Enabled : p.Required;
            desired[p.Id] = prepared;
        }
        await installer.ReconcileAsync(desired, settings: before.AppliedSettings, releaseId: "0.6.0-beta.7", ensureGameClosed: Closed);
        var errors = await installer.VerifyAsync();
        Check(errors.Count == 0, "Private upgraded fixture integrity: " + string.Join(", ", errors.Take(3)));
        var current = installer.LoadState();
        Check(current.Modules["pawpatch-core"].Version == "0.6.0-beta.7", "Private state version not upgraded");
        File.WriteAllText(Path.Combine(Input.Output, "private-upgrade.json"), Identity(new { passed = true, root, version = current.Modules["pawpatch-core"].Version,
            modules = current.Modules.Count, realModuleInstaller = true, nativeGameLaunched = false }));
        Console.WriteLine("PRIVATE_NATIVE_FIXTURE_UPGRADED");
    }
    public static async Task<int> Main(string[] args)
    {
        Input = Read<Inputs>(Path.GetFullPath(args.Length == 0 ? "inputs.json" : args[0]));
        PhysicalG(Input.Output); Directory.CreateDirectory(Input.Output);
        File.WriteAllText(Path.Combine(Input.Output, "result.json"), Identity(new { passed = false, status = "running" }));
        try
        {
            var configuration = Read<LauncherConfiguration>(Input.Configuration);
            var before = Input.Feeds["before"].ToDictionary(p => p.Key, p => Signed(p.Value, configuration));
            var after = Input.Feeds["after"].ToDictionary(p => p.Key, p => Signed(p.Value, configuration));
            var oldManifests = Input.Archives.ToDictionary(p => p.Key, p => Manifest(p.Value.Old));
            var newManifests = Input.Archives.ToDictionary(p => p.Key, p => Manifest(p.Value.New));
            Check(Input.Helpers.Count == 8 && Input.Counts["water"] == 952 && Input.Counts["shadow"] == 56 && Input.Counts["ao"] == 672 && Input.Counts["hd"] == 1132, "Expected independent evidence counts");
            var commonHelpers = newManifests["common-ui"].Files.Select(f => N(f.Path)).Where(p => Input.Helpers.Keys.Any(h => N(h) == p)).ToHashSet();
            var colorHelpers = newManifests["player-colors"].Files.Select(f => N(f.Path)).Where(p => Input.Helpers.Keys.Any(h => N(h) == p)).ToHashSet();
            Check(commonHelpers.Count == 4 && colorHelpers.Count == 4 && !commonHelpers.Overlaps(colorHelpers)
                && commonHelpers.Concat(colorHelpers).ToHashSet().SetEquals(Input.Helpers.Keys.Select(N)), "Actual helper package masks must be disjoint 4+4");
            var payload = newManifests.Values.SelectMany(m => m.Files).GroupBy(f => N(f.Path)).ToDictionary(g => g.Key, g => g.Select(f => f.Sha256).ToHashSet(StringComparer.OrdinalIgnoreCase));
            foreach (var (path, hash) in Input.Pins) Check(payload.TryGetValue(N(path), out var hashes) && hashes.Contains(hash), "Accepted artifact pin missing from real module " + path);
            CatalogMatrix(before, after, configuration, newManifests);
            FeatureBoundaries(before, after, configuration);
            await Installer(before["beta"], after["beta"], oldManifests, newManifests, configuration);
            if (args.Contains("--upgrade-private")) await UpgradeExistingPrivate(after["beta"]);
            File.WriteAllText(Path.Combine(Input.Output, "result.json"), Identity(new { passed = true, selections = Selections, featureCases = FeatureCases, checks = Checks, installedFileChecks = InstalledFiles,
                counts = Input.Counts, fixture = Fixture, stages = Stages, packageAssets = PackageAssets, helperHashes = Input.Helpers,
                fixtureBudgetBytes = FixtureBudgetBytes, peakObservedFixtureBytes = PeakObservedFixtureBytes,
                installedHelpersSeen = InstalledHelpersSeen.Order().ToArray(), helperPackageMasks = new { commonUi = commonHelpers.Order().ToArray(), playerColors = colorHelpers.Order().ToArray() },
                nativeGameLaunched = false, realLauncherAssembly = typeof(ModuleInstaller).Assembly.Location,
                launcher = typeof(ModuleInstaller).Assembly.GetName().Version!.ToString() }));
            Console.WriteLine($"ARCANE_BETA7_RELEASE_QA_PASS {Selections} profiles; {Checks} assertions; real four-package install/upgrade/priority/off/rollback/reapply");
            return 0;
        }
        catch (Exception e)
        {
            var failure = Identity(new { passed = false, error = e.ToString(), checks = Checks, selections = Selections, fixture = Fixture, stages = Stages });
            File.WriteAllText(Path.Combine(Input.Output, "failure.json"), failure);
            File.WriteAllText(Path.Combine(Input.Output, "result.json"), failure);
            Console.Error.WriteLine(e); return 1;
        }
    }
    public sealed class Inputs
    {
        public string Output { get; set; } = "";
        public string Configuration { get; set; } = "";
        public Dictionary<string, Dictionary<string, string>> Feeds { get; set; } = [];
        public Dictionary<string, ArchivePair> Archives { get; set; } = [];
        public Dictionary<string, string> Helpers { get; set; } = [];
        public Dictionary<string, string> Pins { get; set; } = [];
        public List<string> HdRemovals { get; set; } = [];
        public Dictionary<string, int> Counts { get; set; } = [];
    }
    public sealed class ArchivePair { public string Old { get; set; } = ""; public string New { get; set; } = ""; }
}

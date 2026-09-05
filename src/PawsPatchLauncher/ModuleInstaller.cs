using System.Text.Json;

namespace PawsPatchLauncher;

public sealed class ModuleInstaller
{
    private readonly string _gameRoot;
    private readonly string _controlRoot;
    private readonly string _statePath;
    private readonly string _backupRoot;
    private readonly string _packageRoot;

    public ModuleInstaller(string gameRoot)
    {
        _gameRoot = Path.GetFullPath(gameRoot);
        _controlRoot = Path.Combine(_gameRoot, ".pawpatch");
        _statePath = Path.Combine(_controlRoot, "state.json");
        _backupRoot = Path.Combine(_controlRoot, "originals");
        _packageRoot = Path.Combine(_controlRoot, "packages");
    }

    public InstallState LoadState()
    {
        if (File.Exists(_statePath))
            return JsonSerializer.Deserialize(File.ReadAllText(_statePath), LauncherJsonContext.Default.InstallState)
                ?? throw new InvalidDataException("The patch installation state is damaged.");
        return new InstallState();
    }

    public async Task RememberLegacyConfigurationAsync(UserSettings settings, string releaseId)
    {
        var state = LoadState();
        if (state.AppliedSettings is not null || state.Modules.Count == 0) return;
        state.AppliedSettings = JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings);
        state.ReleaseId = releaseId;
        await CryptoAndIO.AtomicWriteTextAsync(_statePath, JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState));
    }

    public async Task<InstalledModule> PrepareAsync(PackageRelease package, string archivePath, CancellationToken cancellationToken = default)
    {
        var directory = Path.Combine(_packageRoot, Sanitize(package.Id), Sanitize(package.Version));
        var readyMarker = Path.Combine(directory, ".verified");
        if (!File.Exists(readyMarker))
        {
            if (Directory.Exists(directory)) Directory.Delete(directory, true);
            Directory.CreateDirectory(directory);
            CryptoAndIO.ExtractZipSafely(archivePath, directory);
        }

        var manifestPath = Path.Combine(directory, "module.json");
        if (!File.Exists(manifestPath)) throw new InvalidDataException($"Package {package.Id} has no module.json.");
        var module = JsonSerializer.Deserialize(await File.ReadAllTextAsync(manifestPath, cancellationToken), LauncherJsonContext.Default.ModuleArchiveManifest)
                     ?? throw new InvalidDataException($"Package {package.Id} has an empty module.json.");
        if (!string.Equals(module.Id, package.Id, StringComparison.OrdinalIgnoreCase) || module.Version != package.Version)
            throw new InvalidDataException($"Package identity mismatch for {package.Id}.");

        foreach (var file in module.Files)
        {
            var source = CryptoAndIO.SafeChildPath(Path.Combine(directory, "payload"), file.Path);
            if (!File.Exists(source)) throw new InvalidDataException($"Package file is missing: {file.Path}");
            if (new FileInfo(source).Length != file.Size) throw new InvalidDataException($"Package file size mismatch: {file.Path}");
            var hash = await CryptoAndIO.Sha256Async(source, cancellationToken);
            if (!hash.Equals(file.Sha256, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException($"Package file hash mismatch: {file.Path}");
        }
        var normalizedFiles = module.Files.Select(file => CryptoAndIO.NormalizeRelativePath(file.Path))
            .ToHashSet(StringComparer.OrdinalIgnoreCase);
        var removals = module.Remove.Select(CryptoAndIO.NormalizeRelativePath)
            .Distinct(StringComparer.OrdinalIgnoreCase).ToList();
        foreach (var relative in removals)
        {
            PatchRecovery.GamePath(_gameRoot, relative);
            if (normalizedFiles.Contains(relative))
                throw new InvalidDataException($"Package {package.Id} both installs and removes: {relative}");
        }
        await File.WriteAllTextAsync(readyMarker, package.Sha256, cancellationToken);
        return new InstalledModule
        {
            Version = module.Version,
            Priority = package.Priority,
            Enabled = true,
            ArchiveSha256 = package.Sha256,
            Files = module.Files,
            Remove = removals
        };
    }

    public async Task ReconcileAsync(IReadOnlyDictionary<string, InstalledModule> desired, CancellationToken cancellationToken = default,
        UserSettings? settings = null, string? releaseId = null)
    {
        Directory.CreateDirectory(_controlRoot);
        var recovery = new PatchRecovery(_gameRoot);
        await recovery.RecoverInterruptedAsync();
        var state = LoadState();
        var previous = JsonSerializer.Deserialize(JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState), LauncherJsonContext.Default.InstallState)!;
        var winners = new Dictionary<string, (string Id, InstalledModule Module, ModuleFile? File)>(StringComparer.OrdinalIgnoreCase);
        foreach (var pair in desired.Where(x => x.Value.Enabled).OrderBy(x => x.Value.Priority).ThenBy(x => x.Key, StringComparer.OrdinalIgnoreCase))
        {
            foreach (var relative in pair.Value.Remove) winners[CryptoAndIO.NormalizeRelativePath(relative)] = (pair.Key, pair.Value, null);
            foreach (var file in pair.Value.Files) winners[CryptoAndIO.NormalizeRelativePath(file.Path)] = (pair.Key, pair.Value, file);
        }
        var recognized = desired.Values.SelectMany(x => x.Files).GroupBy(x => CryptoAndIO.NormalizeRelativePath(x.Path), StringComparer.OrdinalIgnoreCase)
            .ToDictionary(g => g.Key, g => g.Select(x => x.Sha256).ToHashSet(StringComparer.OrdinalIgnoreCase), StringComparer.OrdinalIgnoreCase);
        var allPaths = state.Modules.Values.SelectMany(x => x.Files).Select(x => CryptoAndIO.NormalizeRelativePath(x.Path))
            .Concat(desired.Values.SelectMany(x => x.Files).Select(x => CryptoAndIO.NormalizeRelativePath(x.Path)))
            .Concat(state.Modules.Values.SelectMany(x => x.Remove).Select(CryptoAndIO.NormalizeRelativePath))
            .Concat(desired.Values.SelectMany(x => x.Remove).Select(CryptoAndIO.NormalizeRelativePath))
            .Distinct(StringComparer.OrdinalIgnoreCase).ToList();

        foreach (var relative in allPaths)
        {
            if (state.Originals.ContainsKey(relative)) continue;
            var target = PatchRecovery.GamePath(_gameRoot, relative);
            var original = new OriginalFile { Existed = File.Exists(target) };
            if (original.Existed)
            {
                var actualHash = await CryptoAndIO.Sha256Async(target, cancellationToken);
                if (recognized.TryGetValue(relative, out var hashes) && hashes.Contains(actualHash))
                {
                    // A previous manual/archive installation already placed this exact managed file.
                    // Do not preserve it as a user original, otherwise disabling its module would restore the mod again.
                    original.Existed = false;
                    state.Originals[relative] = original;
                    continue;
                }
                var backupRelative = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(relative.ToUpperInvariant()))) + ".bin";
                var backup = CryptoAndIO.SafeChildPath(_backupRoot, backupRelative);
                Directory.CreateDirectory(Path.GetDirectoryName(backup)!);
                File.Copy(target, backup, true);
                original.BackupRelativePath = backupRelative;
                original.Sha256 = actualHash;
            }
            state.Originals[relative] = original;
        }

        var changes = new List<string>();
        foreach (var relative in allPaths)
        {
            var target = PatchRecovery.GamePath(_gameRoot, relative);
            var expected = winners.TryGetValue(relative, out var winner) ? winner.File?.Sha256 : state.Originals.GetValueOrDefault(relative)?.Sha256;
            if (!File.Exists(target) ? expected is not null : expected is null || !(await CryptoAndIO.Sha256Async(target, cancellationToken)).Equals(expected, StringComparison.OrdinalIgnoreCase))
                changes.Add(relative);
        }
        var snapshot = await recovery.CaptureAsync(changes, previous, ct: cancellationToken);
        try
        {
            foreach (var relative in changes)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var target = PatchRecovery.GamePath(_gameRoot, relative);

                if (winners.TryGetValue(relative, out var winner))
                {
                    var suppliedFile = winner.File;
                    if (suppliedFile is not null)
                    {
                        var source = CryptoAndIO.SafeChildPath(Path.Combine(_packageRoot, Sanitize(winner.Id), Sanitize(winner.Module.Version), "payload"), relative);
                        Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                        var temporary = target + ".pawpatch.tmp";
                        File.Copy(source, temporary, true);
                        File.Move(temporary, target, true);
                    }
                    else if (File.Exists(target)) File.Delete(target);
                }
                else if (state.Originals.TryGetValue(relative, out var original) && original.Existed && original.BackupRelativePath is not null)
                {
                    var source = CryptoAndIO.SafeChildPath(_backupRoot, original.BackupRelativePath);
                    Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                    File.Copy(source, target, true);
                }
                else if (File.Exists(target)) File.Delete(target);
            }

            state.Modules = desired.ToDictionary(pair => pair.Key, pair => pair.Value, StringComparer.OrdinalIgnoreCase);
            state.LastSuccessfulUpdate = DateTimeOffset.UtcNow.ToString("O");
            state.AppliedSettings = settings is null ? null : JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings);
            state.ReleaseId = releaseId;
            await CryptoAndIO.AtomicWriteTextAsync(_statePath, JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState), cancellationToken);
            var errors = await VerifyAsync(cancellationToken);
            if (errors.Count > 0) throw new IOException("Installation verification failed: " + string.Join("; ", errors.Take(5)));
            await recovery.CommitAsync(snapshot.Directory, snapshot.Journal);
        }
        catch
        {
            if (snapshot.Journal.Phase == "prepared")
            {
                await recovery.RestoreAsync(snapshot.Directory, snapshot.Journal);
                snapshot.Journal.Phase = "recovered";
                await PatchRecovery.SaveAsync(snapshot.Directory, snapshot.Journal);
            }
            throw;
        }
    }

    public async Task<IReadOnlyList<string>> VerifyAsync(CancellationToken cancellationToken = default)
    {
        var state = LoadState();
        var errors = new List<string>();
        foreach (var entry in MultiplayerCheck.Expected(state))
        {
            var relative = entry.Key;
            var expected = entry.Value;
            var target = PatchRecovery.GamePath(_gameRoot, relative);
            if (expected is null)
            {
                if (File.Exists(target)) errors.Add($"Should be removed: {relative}");
                continue;
            }
            if (!File.Exists(target)) { errors.Add($"Missing: {relative}"); continue; }
            var actual = await CryptoAndIO.Sha256Async(target, cancellationToken);
            if (!actual.Equals(expected.Sha256, StringComparison.OrdinalIgnoreCase)) errors.Add($"Changed: {relative}");
        }
        return errors;
    }

    private static ModuleFile? Provides(InstalledModule module, string relative)
        => module.Files.FirstOrDefault(file => CryptoAndIO.NormalizeRelativePath(file.Path).Equals(relative, StringComparison.OrdinalIgnoreCase));

    private static bool Removes(InstalledModule module, string relative)
        => module.Remove.Any(path => CryptoAndIO.NormalizeRelativePath(path).Equals(relative, StringComparison.OrdinalIgnoreCase));

    private static string Sanitize(string value)
    {
        if (value.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || value.Contains("..", StringComparison.Ordinal))
            throw new InvalidDataException($"Invalid package identifier: {value}");
        return value;
    }
}

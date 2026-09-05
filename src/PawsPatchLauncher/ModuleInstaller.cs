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
        try
        {
            if (File.Exists(_statePath))
                return JsonSerializer.Deserialize(File.ReadAllText(_statePath), LauncherJsonContext.Default.InstallState) ?? new InstallState();
        }
        catch { }
        return new InstallState();
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
            CryptoAndIO.SafeChildPath(_gameRoot, relative);
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

    public async Task ReconcileAsync(IReadOnlyDictionary<string, InstalledModule> desired, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(_controlRoot);
        var state = LoadState();
        var allPaths = state.Modules.Values.SelectMany(x => x.Files).Select(x => CryptoAndIO.NormalizeRelativePath(x.Path))
            .Concat(desired.Values.SelectMany(x => x.Files).Select(x => CryptoAndIO.NormalizeRelativePath(x.Path)))
            .Concat(state.Modules.Values.SelectMany(x => x.Remove).Select(CryptoAndIO.NormalizeRelativePath))
            .Concat(desired.Values.SelectMany(x => x.Remove).Select(CryptoAndIO.NormalizeRelativePath))
            .Distinct(StringComparer.OrdinalIgnoreCase).ToList();

        foreach (var relative in allPaths)
        {
            if (state.Originals.ContainsKey(relative)) continue;
            var target = CryptoAndIO.SafeChildPath(_gameRoot, relative);
            var original = new OriginalFile { Existed = File.Exists(target) };
            if (original.Existed)
            {
                var actualHash = await CryptoAndIO.Sha256Async(target, cancellationToken);
                var recognizedManagedHashes = desired.Values
                    .SelectMany(module => module.Files)
                    .Where(file => CryptoAndIO.NormalizeRelativePath(file.Path).Equals(relative, StringComparison.OrdinalIgnoreCase))
                    .Select(file => file.Sha256)
                    .ToHashSet(StringComparer.OrdinalIgnoreCase);
                if (recognizedManagedHashes.Contains(actualHash))
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

        var transaction = Path.Combine(_controlRoot, "transactions", DateTime.UtcNow.ToString("yyyyMMddHHmmssfff"));
        Directory.CreateDirectory(transaction);
        var applied = new List<(string Target, string Rollback, bool Existed)>();
        try
        {
            foreach (var relative in allPaths)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var target = CryptoAndIO.SafeChildPath(_gameRoot, relative);
                var rollback = CryptoAndIO.SafeChildPath(transaction, relative);
                var existed = File.Exists(target);
                if (existed)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(rollback)!);
                    File.Copy(target, rollback, true);
                }
                applied.Add((target, rollback, existed));

                var winner = desired
                    .Where(pair => pair.Value.Enabled && (Provides(pair.Value, relative) is not null || Removes(pair.Value, relative)))
                    .OrderBy(pair => pair.Value.Priority)
                    .LastOrDefault();

                if (!string.IsNullOrEmpty(winner.Key))
                {
                    var suppliedFile = Provides(winner.Value, relative);
                    if (suppliedFile is not null)
                    {
                        var source = CryptoAndIO.SafeChildPath(Path.Combine(_packageRoot, Sanitize(winner.Key), Sanitize(winner.Value.Version), "payload"), relative);
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
            await CryptoAndIO.AtomicWriteTextAsync(_statePath, JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState), cancellationToken);
            Directory.Delete(transaction, true);
        }
        catch
        {
            foreach (var item in applied.AsEnumerable().Reverse())
            {
                try
                {
                    if (item.Existed) { Directory.CreateDirectory(Path.GetDirectoryName(item.Target)!); File.Copy(item.Rollback, item.Target, true); }
                    else if (File.Exists(item.Target)) File.Delete(item.Target);
                }
                catch { }
            }
            throw;
        }
    }

    public async Task<IReadOnlyList<string>> VerifyAsync(CancellationToken cancellationToken = default)
    {
        var state = LoadState();
        var errors = new List<string>();
        var paths = state.Modules.Values.Where(module => module.Enabled)
            .SelectMany(module => module.Files.Select(file => CryptoAndIO.NormalizeRelativePath(file.Path)).Concat(module.Remove.Select(CryptoAndIO.NormalizeRelativePath)))
            .Distinct(StringComparer.OrdinalIgnoreCase);
        foreach (var relative in paths)
        {
            var winner = state.Modules.Where(pair => pair.Value.Enabled && (Provides(pair.Value, relative) is not null || Removes(pair.Value, relative)))
                .OrderBy(pair => pair.Value.Priority).Last();
            var expected = Provides(winner.Value, relative);
            var target = CryptoAndIO.SafeChildPath(_gameRoot, relative);
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

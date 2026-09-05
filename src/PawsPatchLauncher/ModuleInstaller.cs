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
        await File.WriteAllTextAsync(readyMarker, package.Sha256, cancellationToken);
        return new InstalledModule
        {
            Version = module.Version,
            Priority = package.Priority,
            Enabled = true,
            ArchiveSha256 = package.Sha256,
            Files = module.Files
        };
    }

    public async Task ReconcileAsync(IReadOnlyDictionary<string, InstalledModule> desired, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(_controlRoot);
        var state = LoadState();
        var allPaths = state.Modules.Values.SelectMany(x => x.Files).Select(x => CryptoAndIO.NormalizeRelativePath(x.Path))
            .Concat(desired.Values.SelectMany(x => x.Files).Select(x => CryptoAndIO.NormalizeRelativePath(x.Path)))
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
                    .Where(pair => pair.Value.Enabled && pair.Value.Files.Any(file => CryptoAndIO.NormalizeRelativePath(file.Path).Equals(relative, StringComparison.OrdinalIgnoreCase)))
                    .OrderBy(pair => pair.Value.Priority)
                    .LastOrDefault();

                if (!string.IsNullOrEmpty(winner.Key))
                {
                    var source = CryptoAndIO.SafeChildPath(Path.Combine(_packageRoot, Sanitize(winner.Key), Sanitize(winner.Value.Version), "payload"), relative);
                    Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                    var temporary = target + ".pawpatch.tmp";
                    File.Copy(source, temporary, true);
                    File.Move(temporary, target, true);
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
        foreach (var module in state.Modules.Where(pair => pair.Value.Enabled))
        {
            foreach (var file in module.Value.Files)
            {
                var target = CryptoAndIO.SafeChildPath(_gameRoot, file.Path);
                if (!File.Exists(target)) { errors.Add($"Missing: {file.Path}"); continue; }
                var winner = state.Modules.Where(pair => pair.Value.Enabled && pair.Value.Files.Any(x => CryptoAndIO.NormalizeRelativePath(x.Path).Equals(CryptoAndIO.NormalizeRelativePath(file.Path), StringComparison.OrdinalIgnoreCase)))
                    .OrderBy(pair => pair.Value.Priority).Last();
                if (!winner.Key.Equals(module.Key, StringComparison.OrdinalIgnoreCase)) continue;
                var actual = await CryptoAndIO.Sha256Async(target, cancellationToken);
                if (!actual.Equals(file.Sha256, StringComparison.OrdinalIgnoreCase)) errors.Add($"Changed: {file.Path}");
            }
        }
        return errors;
    }

    private static string Sanitize(string value)
    {
        if (value.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || value.Contains("..", StringComparison.Ordinal))
            throw new InvalidDataException($"Invalid package identifier: {value}");
        return value;
    }
}

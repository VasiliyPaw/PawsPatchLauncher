using System.Diagnostics;
using System.IO.Compression;
using System.Text.Json;
using PawsPatchLauncher;

internal static class AtomicStateWriteTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var folder = Path.Combine(root, "atomic-state"); Directory.CreateDirectory(folder);
        var path = Path.Combine(folder, "state.json");
        var n = 0; void Check(bool ok, string why) { if (!ok) throw new Exception("Atomic state: " + why); n++; }
        await File.WriteAllTextAsync(path, "before");
        // Windows readers that omit FileShare.Delete reproduce MoveFile's transient
        // access/sharing denial without changing ACLs or any real game file.
        using (var reader = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            var saving = CryptoAndIO.AtomicWriteTextAsync(path, "after");
            await Task.Delay(160);
            Check(!saving.IsCompleted && File.ReadAllText(path) == "before", "Temporary lock was not retried atomically.");
            reader.Dispose(); await saving;
        }
        Check(File.ReadAllText(path) == "after", "Released lock did not complete the original save.");
        using (var reader = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (var cancel = new CancellationTokenSource(130))
        {
            var cancelled = false;
            try { await CryptoAndIO.AtomicWriteTextAsync(path, "cancelled", cancel.Token); }
            catch (OperationCanceledException) { cancelled = true; }
            Check(cancelled && File.ReadAllText(path) == "after", "Cancellation changed the previous state.");
        }
        File.SetAttributes(path, FileAttributes.ReadOnly);
        try
        {
            var denied = false; var watch = Stopwatch.StartNew();
            try { await CryptoAndIO.AtomicWriteTextAsync(path, "denied"); }
            catch (UnauthorizedAccessException error) { denied = error.Message.Contains(path); }
            Check(denied && watch.Elapsed < TimeSpan.FromSeconds(4), "Permanent denial was hidden or retries were unbounded.");
            Check(File.ReadAllText(path) == "after" && File.GetAttributes(path).HasFlag(FileAttributes.ReadOnly), "Writer changed permissions or lost the previous state.");
        }
        finally { File.SetAttributes(path, FileAttributes.Normal); }
        var documents = Enumerable.Range(0, 12).Select(i => JsonSerializer.Serialize(new { id = i, text = new string((char)('A' + i), 12000) })).ToArray();
        await Task.WhenAll(documents.Select(text => CryptoAndIO.AtomicWriteTextAsync(path, text)));
        Check(documents.Contains(File.ReadAllText(path)), "Concurrent saves mixed or truncated documents.");
        Check(Directory.GetFiles(folder, "*.tmp").Length == 0, "A completed or failed save leaked staging files.");

        var game = Path.Combine(folder, "game"); Directory.CreateDirectory(game);
        var target = Path.Combine(game, "data.txt"); await File.WriteAllTextAsync(target, "original");
        var archive = Path.Combine(folder, "component.zip");
        var payload = Path.Combine(folder, "payload.txt"); await File.WriteAllTextAsync(payload, "component");
        var manifest = new ModuleArchiveManifest { Id = "fixture", Version = "1.0.0", Files = [new() {
            Path = "data.txt", Sha256 = await CryptoAndIO.Sha256Async(payload), Size = new FileInfo(payload).Length }] };
        using (var zip = ZipFile.Open(archive, ZipArchiveMode.Create))
        {
            zip.CreateEntryFromFile(payload, "payload/data.txt");
            using var writer = new StreamWriter(zip.CreateEntry("module.json").Open());
            writer.Write(JsonSerializer.Serialize(manifest, LauncherJsonContext.Default.ModuleArchiveManifest));
        }
        var installer = new ModuleInstaller(game);
        await installer.ReconcileAsync(new Dictionary<string, InstalledModule>());
        var statePath = Path.Combine(game, ".pawpatch", "state.json"); var before = File.ReadAllText(statePath);
        var package = new PackageRelease { Id = "fixture", Version = "1.0.0", Sha256 = await CryptoAndIO.Sha256Async(archive), Size = new FileInfo(archive).Length };
        var module = await installer.PrepareAsync(package, archive);
        File.SetAttributes(statePath, FileAttributes.ReadOnly);
        try
        {
            var denied = false;
            try { await installer.ReconcileAsync(new Dictionary<string, InstalledModule> { [package.Id] = module }); }
            catch (UnauthorizedAccessException) { denied = true; }
            Check(denied && File.ReadAllText(target) == "original" && File.ReadAllText(statePath) == before,
                "Failed final state commit left partially applied game files.");
        }
        finally { File.SetAttributes(statePath, FileAttributes.Normal); }
        Check(await new PatchRecovery(game).RecoverInterruptedAsync() == 1, "Pending rollback was not recoverable after releasing the state file.");
        await installer.ReconcileAsync(new Dictionary<string, InstalledModule> { [package.Id] = module });
        Check(File.ReadAllText(target) == "component" && (await installer.VerifyAsync()).Count == 0, "Retry after recovery did not apply the complete component.");
        Console.WriteLine($"ATOMIC STATE PASS {n}: transient Windows lock, cancellation, permanent denial, concurrent saves, cleanup and transaction recovery.");
        return n;
    }
}

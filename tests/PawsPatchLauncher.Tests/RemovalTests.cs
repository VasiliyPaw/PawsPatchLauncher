using System.Diagnostics;
using System.Text;
using PawsPatchLauncher;

public static class RemovalTests
{
    public static async Task<int> RunAsync(string fixtureRoot)
    {
        var count = 0;
        void Check(bool value, string message) { if (!value) throw new Exception(message); count++; }
        async Task Fails(Func<Task> action)
        {
            try { await action(); } catch (IOException) { count++; return; }
            throw new Exception("Expected removal refusal.");
        }
        var root = Path.Combine(fixtureRoot, "uninstall"); Directory.CreateDirectory(root);
        var shared = Path.Combine(root, "shared.txt");
        await File.WriteAllTextAsync(shared, "original");
        await File.WriteAllTextAsync(Path.Combine(root, "save.sav"), "save untouched");
        await File.WriteAllTextAsync(Path.Combine(root, "k2.exe"), "stock untouched");
        await File.WriteAllTextAsync(Path.Combine(root, "obsolete.txt"), "deleted by patch");
        var installer = new ModuleInstaller(root);
        var module = new InstalledModule { Version = "1", Priority = 100, Enabled = true, Remove = ["obsolete.txt"] };
        var payload = Path.Combine(root, ".pawpatch", "packages", "fixture", "1", "payload");
        Directory.CreateDirectory(payload);
        foreach (var name in new[] { "shared.txt", "added.txt" })
        {
            var path = Path.Combine(payload, name); await File.WriteAllTextAsync(path, "patched " + name);
            module.Files.Add(new ModuleFile { Path = name, Size = new FileInfo(path).Length, Sha256 = await CryptoAndIO.Sha256Async(path) });
        }
        var desired = new Dictionary<string, InstalledModule> { ["fixture"] = module };
        await installer.ReconcileAsync(desired);
        var original = installer.LoadState().Originals["shared.txt"];
        var backup = Path.Combine(root, ".pawpatch", "originals", original.BackupRelativePath!);
        var backupBytes = await File.ReadAllBytesAsync(backup);
        await File.WriteAllTextAsync(backup, "damaged");
        await Fails(() => installer.UninstallAsync());
        Check(File.Exists(Path.Combine(root, "added.txt")) && File.ReadAllText(shared) == "patched shared.txt", "Damaged backup changed live files.");
        await File.WriteAllBytesAsync(backup, backupBytes);
        await File.WriteAllTextAsync(shared, "external mod edit");
        await Fails(() => installer.UninstallAsync());
        Check(File.ReadAllText(shared) == "external mod edit" && File.Exists(Path.Combine(root, "added.txt")), "External edits were not protected.");
        await File.WriteAllTextAsync(shared, "patched shared.txt");
        await installer.UninstallAsync();
        Check(File.ReadAllText(shared) == "original", "Original not restored.");
        Check(!File.Exists(Path.Combine(root, "added.txt")), "Added patch file survived.");
        Check(File.ReadAllText(Path.Combine(root, "obsolete.txt")) == "deleted by patch", "Deleted original not restored.");
        Check(File.ReadAllText(Path.Combine(root, "save.sav")) == "save untouched", "Save was changed.");
        Check(File.ReadAllText(Path.Combine(root, "k2.exe")) == "stock untouched", "Stock EXE was changed.");
        Check(installer.LoadState().Modules.Count == 0 && installer.LoadState().Originals.Count == 0, "Uninstall metadata is not reset.");
        Check(new PatchRecovery(root).CanRollback, "Uninstall rollback unavailable.");
        await new PatchRecovery(root).RollbackAsync(installer.LoadState());
        Check(File.ReadAllText(shared) == "patched shared.txt" && File.Exists(Path.Combine(root, "added.txt")), "Uninstall rollback failed.");
        Check((await installer.VerifyAsync()).Count == 0, "Rollback hashes differ.");
        await installer.UninstallAsync();
        await installer.UninstallAsync();
        Check(File.ReadAllText(shared) == "original", "Second uninstall is not harmless.");
        await File.WriteAllTextAsync(shared, "new original after uninstall");
        await installer.ReconcileAsync(desired);
        await installer.UninstallAsync();
        Check(File.ReadAllText(shared) == "new original after uninstall", "Reinstall restored an outdated original.");
        using var cancelled = new CancellationTokenSource(); cancelled.Cancel();
        await installer.ReconcileAsync(desired);
        try { await installer.UninstallAsync(cancelled.Token); throw new Exception("Cancellation ignored."); }
        catch (OperationCanceledException) { count++; }
        Check(File.Exists(Path.Combine(root, "added.txt")), "Cancelled uninstall changed files.");
        return count;
    }

    public static async Task RunHelperAsync(string fixtureRoot)
    {
        foreach (var scenario in new[] { "success", "changed-exe", "changed-companion", "other-instance" })
        {
            var root = Path.Combine(Path.GetFullPath(fixtureRoot), Guid.NewGuid().ToString("N"), "Пример & user's [folder]");
            var data = Path.Combine(root, "PawsPatchLauncher"); var cache = Path.Combine(data, "downloads", "module", "1");
            Directory.CreateDirectory(cache);
            var exe = Path.Combine(root, "Renamed launcher.exe");
            await File.WriteAllTextAsync(exe, "fixture only");
            await File.WriteAllTextAsync(exe + ".previous", "previous fixture");
            await File.WriteAllTextAsync(Path.Combine(root, "other.exe"), "unrelated");
            await File.WriteAllTextAsync(Path.Combine(data, "user-note.txt"), "unrelated note");
            await File.WriteAllTextAsync(Path.Combine(data, "settings.json"), "{}");
            await File.WriteAllTextAsync(Path.Combine(cache, "test.zip"), "cache fixture");
            var script = await LauncherUninstaller.BuildScriptAsync(exe, data, int.MaxValue, 0, showErrors: false);
            var mutexName = "Local\\PawsPatchLauncher-Test-" + Guid.NewGuid().ToString("N");
            script = script.Replace("Local\\PawsPatchLauncher-Reliability", mutexName);
            if (scenario == "changed-exe") await File.WriteAllTextAsync(exe, "replaced after plan");
            if (scenario == "changed-companion") await File.WriteAllTextAsync(exe + ".previous", "replaced after plan");
            // Own on this thread; launch and wait synchronously to keep ownership.
            using var mutex = new Mutex(scenario == "other-instance", mutexName);
            var start = new ProcessStartInfo("powershell.exe") { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden,
                RedirectStandardError = true, RedirectStandardOutput = true };
            start.ArgumentList.Add("-NoProfile"); start.ArgumentList.Add("-NonInteractive"); start.ArgumentList.Add("-EncodedCommand");
            start.ArgumentList.Add(Convert.ToBase64String(Encoding.Unicode.GetBytes(script)));
            using var process = Process.Start(start)!;
            var output = process.StandardOutput.ReadToEndAsync(); var error = process.StandardError.ReadToEndAsync();
            if (!process.WaitForExit(20000)) { process.Kill(); throw new Exception("Fixture helper timed out."); }
            if (scenario == "other-instance") mutex.ReleaseMutex();
            if (scenario == "success")
            {
                if (process.ExitCode != 0) throw new Exception("Removal helper failed: " + await error + await output);
                if (File.Exists(exe) || File.Exists(exe + ".previous") || File.Exists(Path.Combine(data, "settings.json")) || Directory.Exists(Path.Combine(data, "downloads")))
                    throw new Exception("Owned fixture files survived.");
            }
            else if (process.ExitCode == 0 || !File.Exists(exe) || !File.Exists(Path.Combine(cache, "test.zip")))
                throw new Exception("Unsafe helper failed to stop before deletion: " + scenario);
            if (!File.Exists(Path.Combine(root, "other.exe")) || !File.Exists(Path.Combine(data, "user-note.txt")))
                throw new Exception("Unrelated fixture files were removed.");
            Console.WriteLine("SELF-UNINSTALL PASS " + scenario);
        }
    }
}

using System.Diagnostics;
using System.Text;
using PawsPatchLauncher;

public static class SelfUpdateTests
{
    // Copies real releases into a fixture. --smoke-test isolates settings, timers
    // and mutexes; production replacement, hashing and acknowledgement stay intact.
    public static async Task RunRealAsync(string fixtureRoot, string baseline, string candidate)
    {
        var root = Path.Combine(Path.GetFullPath(fixtureRoot), Guid.NewGuid().ToString("N"), "Русская папка & user's [folder]");
        Directory.CreateDirectory(root);
        var target = Path.Combine(root, "Мой лаунчер.exe");
        File.Copy(baseline, target); File.Copy(candidate, target + ".new");
        var oldHash = await CryptoAndIO.Sha256Async(baseline);
        var newHash = await CryptoAndIO.Sha256Async(candidate);
        var oldInfo = new ProcessStartInfo(target) { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden };
        oldInfo.ArgumentList.Add("--smoke-test");
        using var old = Process.Start(oldInfo)!;
        Process? updated = null;
        static void CloseFixture(Process process)
        {
            if (process.HasExited) return;
            process.CloseMainWindow();
            if (!process.WaitForExit(5000)) { process.Kill(); process.WaitForExit(); }
        }
        try
        {
            var marker = Path.Combine(Path.GetTempPath(), "PawsPatchLauncherSmoke", old.Id.ToString(), "window-ready.txt");
            var until = DateTimeOffset.UtcNow.AddSeconds(30);
            while (!File.Exists(marker) && !old.HasExited && DateTimeOffset.UtcNow < until) await Task.Delay(100);
            if (old.HasExited || !File.Exists(marker)) throw new Exception("Baseline launcher did not open its window.");
            var script = SelfUpdater.BuildScript(target, target + ".new", old.Id, newHash, root, Guid.NewGuid().ToString("N"));
            script = script.Replace("$info.Arguments = $arguments", "$info.Arguments = $arguments + ' --smoke-test'")
                .Replace("$until = [DateTime]::UtcNow.AddSeconds(", "[IO.File]::WriteAllText([IO.Path]::Combine($folder, 'candidate.pid'), $candidate.Id.ToString())\n$until = [DateTime]::UtcNow.AddSeconds(");
            var helperInfo = new ProcessStartInfo("powershell.exe") { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden };
            helperInfo.ArgumentList.Add("-NoProfile"); helperInfo.ArgumentList.Add("-NonInteractive"); helperInfo.ArgumentList.Add("-EncodedCommand");
            helperInfo.ArgumentList.Add(Convert.ToBase64String(Encoding.Unicode.GetBytes(script)));
            using var helper = Process.Start(helperInfo)!;
            CloseFixture(old);
            await helper.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(90));
            if (helper.ExitCode != 0 || !File.ReadAllText(Path.Combine(root, "self-update.log")).StartsWith("Update confirmed:"))
                throw new Exception("Real launcher update was not confirmed.");
            if (await CryptoAndIO.Sha256Async(target) != newHash || await CryptoAndIO.Sha256Async(target + ".previous") != oldHash)
                throw new Exception("Real launcher update produced incorrect files.");
            updated = Process.GetProcessById(int.Parse(File.ReadAllText(Path.Combine(root, "candidate.pid"))));
            if (updated.HasExited || !string.Equals(updated.MainModule?.FileName, target, StringComparison.OrdinalIgnoreCase))
                throw new Exception("Updated launcher is not running from the fixture.");
            var ready = Path.Combine(Path.GetTempPath(), "PawsPatchLauncherSmoke", updated.Id.ToString(), "window-ready.txt");
            Console.WriteLine("REAL SELF-UPDATE PASS: " + File.ReadAllText(marker) + " -> " + File.ReadAllText(ready) + "; Unicode path, replacement, backup and window acknowledgement");
            Console.WriteLine("UPDATE FIXTURE " + root);
        }
        finally
        {
            CloseFixture(old);
            if (updated is null && File.Exists(Path.Combine(root, "candidate.pid")))
            {
                try { updated = Process.GetProcessById(int.Parse(File.ReadAllText(Path.Combine(root, "candidate.pid")))); } catch (ArgumentException) { }
            }
            if (updated is not null)
            {
                if (!updated.HasExited && string.Equals(updated.MainModule?.FileName, target, StringComparison.OrdinalIgnoreCase)) CloseFixture(updated);
                updated.Dispose();
            }
        }
    }

    public static async Task RunAsync(string fixtureRoot, string baseline, string candidate)
    {
        var oldHash = await CryptoAndIO.Sha256Async(baseline);
        var newHash = await CryptoAndIO.Sha256Async(candidate);
        foreach (var mode in new[] { "healthy", "crash", "timeout" })
        {
            var root = Path.Combine(Path.GetFullPath(fixtureRoot), "test-" + mode + "-" + Guid.NewGuid().ToString("N"), "Пример & user's folder");
            Directory.CreateDirectory(root);
            var target = Path.Combine(root,"Launcher.exe");
            File.Copy(baseline,target); File.Copy(candidate,target+".new");
            await File.WriteAllTextAsync(Path.Combine(root,"mode.txt"),mode);
            var script = SelfUpdater.BuildScript(target,target+".new", int.MaxValue,newHash,root,Guid.NewGuid().ToString("N"),2);
            var start = new ProcessStartInfo("powershell.exe") { UseShellExecute = false, CreateNoWindow = true };
            start.ArgumentList.Add("-NoProfile"); start.ArgumentList.Add("-NonInteractive"); start.ArgumentList.Add("-EncodedCommand");
            start.ArgumentList.Add(Convert.ToBase64String(Encoding.Unicode.GetBytes(script)));
            using var process = Process.Start(start)!;
            await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(20));
            if (process.ExitCode != 0) throw new Exception("Update helper failed: " + mode);
            var actual = await CryptoAndIO.Sha256Async(target);
            if (actual != (mode == "healthy" ? newHash : oldHash)) throw new Exception("Incorrect resulting EXE: " + mode);
            if (mode == "healthy" && await CryptoAndIO.Sha256Async(target+".previous") != oldHash) throw new Exception("Old EXE was not retained.");
            if (mode != "healthy")
            {
                if (File.ReadAllText(Path.Combine(root,"failed-launcher-sha256.txt")) != newHash) throw new Exception("Failed update was not blocked.");
                for (var attempt=0; attempt<20 && !File.Exists(Path.Combine(root,"restored.ok"));attempt++) await Task.Delay(100);
                if (!File.Exists(Path.Combine(root,"restored.ok"))) throw new Exception("The restored launcher did not restart.");
            }
            Console.WriteLine("SELF-UPDATE PASS " + mode);
        }
    }
}

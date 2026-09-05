using System.Diagnostics;
using System.Text;
using PawsPatchLauncher;

public static class SelfUpdateTests
{
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

using System;
using System.IO;
using System.Threading;

internal static class UpdateFixture
{
    private static void Main(string[] args)
    {
        var root = AppDomain.CurrentDomain.BaseDirectory;
#if BASELINE
        File.WriteAllText(Path.Combine(root, "restored.ok"), "baseline");
#else
        var mode = File.ReadAllText(Path.Combine(root, "mode.txt"));
        if (mode == "crash") Environment.Exit(17);
        if (mode == "healthy" && args.Length == 2)
            File.WriteAllText(Path.Combine(root, ".paw-update-" + args[1] + ".ok"), args[1]);
        Thread.Sleep(4000);
#endif
    }
}

using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;

// Runs the compiled helper's --preflight entry branch in-process. Failures are
// caught here so tests never display a WinForms/runtime error window.
internal static class InstalledStartupTests
{
    private static int Main(string[] args)
    {
        int checks = 0;
        try
        {
            string root = Path.GetFullPath(args[0]);
            string expected = Regex.Match(File.ReadAllText(Path.Combine(root, "paws_patch_versions.ini")), @"(?m)^PawPatch=([^\r\n]+)").Groups[1].Value;
            string state = File.ReadAllText(Path.Combine(root, @".pawpatch\state.json"));
            if (expected.Length == 0) throw new Exception("Missing installed patch version.");
            // The game folder can also contain older, unrelated test helpers.
            // Use the current build's eight file names when checking installation.
            string namesRoot = Path.GetFullPath(args.Length > 2 ? args[2] : args[1]);
            foreach (string name in Directory.GetFiles(namesRoot, "k2_paws*.exe").Select(Path.GetFileName).OrderBy(p => p))
            {
                string helper = Path.Combine(Path.GetFullPath(args[1]), name);
                Assembly assembly = Assembly.LoadFile(helper);
                Type lobby = assembly.GetType("PawLobbyCompatibility", true);
                string version = (string)lobby.GetField("Version", BindingFlags.Static | BindingFlags.NonPublic).GetRawConstantValue();
                if (version != expected) throw new Exception("Installed version mismatch: " + Path.GetFileName(helper));
                checks++;
                int result = (int)assembly.EntryPoint.Invoke(null, new object[] { new[] { "--preflight", root } });
                if (result != 0) throw new Exception("Preflight failed: " + Path.GetFileName(helper));
                checks++;
                // Keep rejection of actually incompatible packages. Change only
                // in-memory JSON; the real installation is never written here.
                string incompatible = state.Replace(expected, "0.0.0-incompatible");
                if (incompatible == state) throw new Exception("Expected version missing from installed state.");
                var identity = lobby.GetMethod("Identity", BindingFlags.Static | BindingFlags.NonPublic);
                bool rejected = false;
                try { identity.Invoke(null, new object[] { incompatible, new string('A', 64), Path.GetFileName(helper), new string('B', 64), false }); }
                catch (TargetInvocationException e) { if (e.InnerException is InvalidDataException) rejected = true; else throw; }
                if (!rejected) throw new Exception("Incompatible version accepted.");
                checks++;
            }
            if (checks != 24) throw new Exception("Expected eight helpers, got " + checks + " checks.");
            Console.WriteLine("INSTALLED_STARTUP_PASS " + checks + "; all eight helpers; real installed configuration; no game launched; no files written");
            return 0;
        }
        catch (Exception e)
        {
            Console.Error.WriteLine(e is TargetInvocationException ? e.InnerException.ToString() : e.ToString());
            return 1;
        }
    }
}

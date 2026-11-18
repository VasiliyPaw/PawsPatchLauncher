using System.Text.Json;
using PawsPatchLauncher;

internal static class RetiredHdUiTests
{
    public static int Run(string root)
    {
        var count = 0;
        void Check(bool value, string name) { if (!value) throw new Exception("HD retirement: " + name); count++; }
        var cases = new[] { ("common-ui", "0.6.0-beta.4", "DBB2D28405B8DCF00CAD345168DBC5938D7AA9CDE26DBD197FE2B1768379E809"),
            ("common-ui", "0.6.0-beta.5", "460DAA645667FEB6B903230C7AD3579175987D84511D6E02A687F44761D69DF4"),
            ("pure-beta-common", "0.5.0-beta.8", "CF925BA75BCF05A7D8CB31B4B4CA5E48BCA87CACD9277B28E05B63291203625B"),
            ("pure-beta-common", "0.5.0-beta.9", "96262D2BAE5AFA56E3E7DB9D289A727D4F1E67A60DAE6EF1C9D8F90850897A96") };
        foreach (var (id, version, hash) in cases)
        foreach (var scenario in new[] { "obsolete", "no-retirement", "pinned", "inactive", "extra", "marker", "pending", "running" })
        {
            var game = Path.Combine(root, "retired-hd", id, version, scenario);
            var control = Path.Combine(game, ".pawpatch"); var path = Path.Combine(control, "packages", id, version);
            Directory.CreateDirectory(path);
            var fixture = typeof(RetiredHdUiTests).Assembly.GetManifestResourceStream("RetiredHd." + id + "-" + version + ".json")!;
            using (fixture) using (var output = File.Create(Path.Combine(path, "module.json"))) fixture.CopyTo(output);
            var manifest = JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(path, "module.json")), LauncherJsonContext.Default.ModuleArchiveManifest)!;
            // Payload bytes are irrelevant to ownership recognition; all paths must
            // belong to the exact published manifest, with no extra user content.
            foreach (var file in manifest.Files) { var p = CryptoAndIO.SafeChildPath(Path.Combine(path, "payload"), file.Path); Directory.CreateDirectory(Path.GetDirectoryName(p)!); File.WriteAllBytes(p, []); }
            File.WriteAllText(Path.Combine(path, ".verified"), scenario == "marker" ? new string('A', 64) : hash);
            var state = new InstallState();
            state.Modules[id] = new InstalledModule { Enabled = true, Version = "new", Remove = scenario == "no-retirement" ? [] : ["paws-hd-ui.rwd"] };
            File.WriteAllText(Path.Combine(control, "state.json"), JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState));
            var keep = scenario == "pinned" ? new List<PackageRelease> { new() { Id = id, Version = version } } : [];
            if (scenario == "inactive")
            {
                var library = new ModLibraryDocument { Mods = [new() { Mod = GameMod.Immortals, Channel = "beta", ReleaseId = new string('B', 64), Packages = [new() { Id = id, Version = version }] }] };
                File.WriteAllText(Path.Combine(control, "mod-library.json"), JsonSerializer.Serialize(library, LauncherJsonContext.Default.ModLibraryDocument));
            }
            if (scenario == "extra") File.WriteAllText(Path.Combine(path, "user.txt"), "keep");
            var txn = Guid.NewGuid().ToString("N"); var backup = Path.Combine(control, "transactions", txn); Directory.CreateDirectory(backup);
            File.WriteAllText(Path.Combine(control, "rollback.txt"), txn);
            var journal = new PatchTransaction { Phase = scenario == "pending" ? "applying" : "complete" };
            File.WriteAllText(Path.Combine(backup, "journal.json"), JsonSerializer.Serialize(journal, LauncherJsonContext.Default.PatchTransaction));
            File.WriteAllText(Path.Combine(backup, "saved-original"), "restore me");
            Directory.CreateDirectory(Path.Combine(control, "originals")); File.WriteAllText(Path.Combine(control, "originals", "retail"), "original");
            var cache = Path.Combine(game, "cache"); var zip = Path.Combine(cache, "downloads", id, version, hash + ".zip");
            Directory.CreateDirectory(Path.GetDirectoryName(zip)!); File.WriteAllText(zip, "wrong bytes must survive");
            var options = new StorageOptions(cache, game, null, keep, []);
            var result = StorageMaintenance.RetireHdUi(options, () => { if (scenario == "running") throw new IOException("Game running"); });
            Check(Directory.Exists(path) == (scenario != "obsolete"), id + version + scenario);
            Check(result.Removed == (scenario == "obsolete" ? 1 : 0), "count " + scenario);
            Check(File.ReadAllText(Path.Combine(backup, "saved-original")) == "restore me" && File.Exists(Path.Combine(control, "originals", "retail")), "recovery preserved");
            Check(File.Exists(zip), "unrecognized download preserved");
        }
        Console.WriteLine($"RETIRED HD UI PASS {count}"); return count;
    }
}

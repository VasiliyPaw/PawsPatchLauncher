using PawsPatchLauncher;
using System.Text.Json;

internal static class VanillaBootstrapTests
{
    public static async Task RunSteamAsync(string executable)
    {
        var root = Path.Combine(Path.GetTempPath(), "PawsSteamBaseline", Guid.NewGuid().ToString("N"));
        var checks = 0;
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.ArcaneWars })
        {
            var game = Path.Combine(root, mod); Directory.CreateDirectory(game);
            File.Copy(executable, Path.Combine(game, "k2.exe"));
            var files = new Dictionary<string, string> {
                ["startup/autoexec.txt"] = "628D30D3D0D8E9F4E1DD33604F6B9869FFC9B92BCA0ABC5D6B80CF5FB644666F",
                ["data/UI/Shared/options_dialog.tgi"] = "D3B4C57F5C013A995AD52772E18E71757BBFDA3118B893E3647DFD0CBA41E0EA"
            };
            foreach (var race in new[] { "Drauga", "Gauri", "Haroun", "Human", "Shadow", "Undead" })
                files["skins/" + race + ".rwd"] = await CryptoAndIO.Sha256Async(Path.Combine(Path.GetDirectoryName(executable)!, "skins", race + ".rwd"));
            var state = new InstallState();
            var module = new InstalledModule { Version = "fixture", Enabled = true };
            foreach (var path in files.Keys)
            {
                var live = Path.Combine(game, path); Directory.CreateDirectory(Path.GetDirectoryName(live)!);
                if (path.EndsWith(".rwd")) File.Copy(Path.Combine(Path.GetDirectoryName(executable)!, path), live);
                else File.WriteAllText(live, "legacy patched data: " + path);
                state.Originals[path] = new() { Existed = false };
                module.Files.Add(new() { Path = path, Size = new FileInfo(live).Length, Sha256 = await CryptoAndIO.Sha256Async(live) });
                var cached = Path.Combine(game, ".pawpatch/packages/pawpatch-core/fixture/payload", path);
                Directory.CreateDirectory(Path.GetDirectoryName(cached)!); File.Copy(live, cached);
                if (path == "skins/Shadow.rwd") File.Delete(live);
            }
            state.Modules["pawpatch-core"] = module;
            Directory.CreateDirectory(Path.Combine(game, ".pawpatch"));
            File.WriteAllText(Path.Combine(game, ".pawpatch/state.json"), JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState));
            var installer = new ModuleInstaller(game);
            var settings = new UserSettings { Mod = mod, PawPatchEnabled = false };
            if (mod == GameMod.Vanilla) await installer.UninstallAsync(settings: settings);
            else await installer.ReconcileAsync(new Dictionary<string, InstalledModule>(), settings: settings);
            foreach (var (path, hash) in files)
            {
                if (!File.Exists(Path.Combine(game, path)) || await CryptoAndIO.Sha256Async(Path.Combine(game, path)) != hash)
                    throw new Exception("Steam baseline not restored: " + mod + " " + path);
                checks++;
            }
            if (installer.LoadState().Modules.Count != 0) throw new Exception("Core remained enabled");
            checks++;
            // A fresh install must capture the shared stock archives as originals,
            // even though the same bytes are provided by its mod package.
            var empty = new InstallState();
            File.WriteAllText(Path.Combine(game, ".pawpatch/state.json"), JsonSerializer.Serialize(empty, LauncherJsonContext.Default.InstallState));
            await installer.ReconcileAsync(state.Modules, settings: new UserSettings());
            foreach (var race in new[] { "Drauga", "Gauri", "Haroun", "Human", "Shadow", "Undead" })
            {
                if (!installer.LoadState().Originals[CryptoAndIO.NormalizeRelativePath("skins/" + race + ".rwd")].Existed)
                    throw new Exception("Stock archive adopted as removable mod data: " + race);
                checks++;
            }
        }
        Console.WriteLine($"STEAM VANILLA BASELINE PASS {checks}: legacy and fresh installs, Vanilla and Arcane Wars; Steam startup, autosave UI and six skin archives; missing archive recovered from verified cache. Isolated copies only.");
    }

    public static async Task RunAsync()
    {
        var root = Path.Combine(Path.GetTempPath(), "PawsVanillaBootstrap", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        var checks = 0;
        void Check(bool condition, string message) { if (!condition) throw new Exception(message); checks++; }
        foreach (var scenario in new[] { "legacy", "real-original", "changed-live", "damaged-cache" })
        {
            var game = Path.Combine(root, scenario);
            var cached = Path.Combine(game, ".pawpatch/packages/startup-base/1/payload/startup/autoexec.txt");
            var live = Path.Combine(game, "startup/autoexec.txt");
            Directory.CreateDirectory(Path.GetDirectoryName(cached)!);
            Directory.CreateDirectory(Path.GetDirectoryName(live)!);
            File.WriteAllText(cached, "adddepot data.rwd\r\nadddepot %USERDATA%/data/ 1\r\n");
            File.Copy(cached, live);
            var hash = await CryptoAndIO.Sha256Async(cached);
            var original = new OriginalFile { Existed = false };
            if (scenario == "real-original")
            {
                var backup = Path.Combine(game, ".pawpatch/originals/original.bin");
                Directory.CreateDirectory(Path.GetDirectoryName(backup)!);
                File.WriteAllText(backup, "user's original bootstrap");
                original = new() { Existed = true, BackupRelativePath = "original.bin", Sha256 = await CryptoAndIO.Sha256Async(backup) };
            }
            var state = new InstallState {
                Originals = new() { ["startup/autoexec.txt"] = original },
                Modules = new() { ["startup-base"] = new() { Version = "1", Enabled = true,
                    Files = [new() { Path = "startup/autoexec.txt", Size = new FileInfo(cached).Length, Sha256 = hash }] } }
            };
            var statePath = Path.Combine(game, ".pawpatch/state.json");
            File.WriteAllText(statePath, JsonSerializer.Serialize(state, LauncherJsonContext.Default.InstallState));
            if (scenario == "changed-live") File.WriteAllText(live, "user edit");
            if (scenario == "damaged-cache") File.WriteAllText(cached, "damaged");
            var before = File.ReadAllBytes(live);
            var previousState = File.ReadAllText(statePath);
            var installer = new ModuleInstaller(game);
            try
            {
                await installer.UninstallAsync(settings: new UserSettings { Mod = GameMod.Vanilla });
                Check(scenario is "legacy" or "real-original", "Unsafe bootstrap restoration was accepted");
                Check(File.Exists(live), "Vanilla lost its startup file");
                Check(scenario == "legacy" ? await CryptoAndIO.Sha256Async(live) == hash : File.ReadAllText(live) == "user's original bootstrap", "Wrong startup restored");
                Check(installer.LoadState().Modules.Count == 0 && installer.LoadState().Originals.Count == 0, "Vanilla retained managed modules or stale originals");
            }
            catch (IOException)
            {
                Check(scenario is "changed-live" or "damaged-cache", "Valid bootstrap restoration failed");
                Check(File.ReadAllBytes(live).SequenceEqual(before) && File.ReadAllText(statePath) == previousState, "Failed restoration changed live files/state");
            }
        }
        Console.WriteLine($"VANILLA BOOTSTRAP PASS {checks}: legacy adoption, original backup priority, external edits and damaged cache; isolated files only.");
    }
}

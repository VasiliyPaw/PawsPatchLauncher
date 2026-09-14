using System.Text.Json;
using PawsPatchLauncher;

internal static class ModChannelTests
{
    public static async Task<int> RunAsync(string root)
    {
        int count = 0;
        void Check(bool ok, string why) { count++; if (!ok) throw new Exception("Mod channels: " + why); }
        var settings = JsonSerializer.Deserialize("{\"mod\":\"arcane-wars\",\"channel\":\"beta\",\"russianLocalization\":true,\"pinnedRelease\":\"legacy-pin\"}", LauncherJsonContext.Default.UserSettings)!;
        ModChannelSelection.Remember(settings);
        ModChannelSelection.SelectMod(settings, GameMod.Vanilla);
        Check(settings.Channel == "stable" && settings.PinnedRelease is null, "AW beta leaked into fresh Vanilla choice");
        ModChannelSelection.SelectMod(settings, GameMod.Immortals);
        ModChannelSelection.SelectChannel(settings, "beta"); settings.PinnedRelease = "immortal-pin";
        ModChannelSelection.SelectMod(settings, GameMod.ArcaneWars);
        Check(settings.Channel == "beta" && settings.PinnedRelease == "legacy-pin", "Legacy AW selection/pin was lost");
        ModChannelSelection.SelectChannel(settings, "stable");
        Check(settings.PinnedRelease is null, "Switching channel retained an incompatible pin");
        settings = JsonSerializer.Deserialize(JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings), LauncherJsonContext.Default.UserSettings)!;
        ModChannelSelection.SelectMod(settings, GameMod.Immortals);
        Check(settings.Channel == "beta" && settings.PinnedRelease == "immortal-pin", "Independent choice failed after restart");
        ModChannelSelection.SelectMod(settings, GameMod.Vanilla);
        Check(settings.Channel == "stable" && settings.RussianLocalization, "Vanilla channel/language changed");

        ChannelManifest Feed(string channel, string version) => new()
        {
            Channel = channel, ModGuides = [new() { Id = GameMod.Immortals, Version = "2.1", PatchGuide = new() { Version = "1.2.3" } }],
            Packages = [new() { Id = "arcane-wars", Version = "0.82", Sha256 = new string('A',64), ExecutableIndependent = true },
                new() { Id = "immortals", Version = "2.1", Sha256 = new string('B',64), ExecutableIndependent = true },
                new() { Id = "startup-base", Sha256 = new string('C',64), ExecutableIndependent = true },
                new() { Id = "pure-fixes-data", Version = version, Sha256 = new string('D',64), ExecutableIndependent = true },
                new() { Id = "pure-fixes-runtime", Version = version, Sha256 = new string('E',64) },
                new() { Id = "pawpatch-core", Version = channel == "beta" ? "2-beta.1" : "1", Sha256 = new string('F',64) },
                new() { Id = "menu-runtime", Sha256 = new string('A',64), Mods = ["vanilla","immortals","arcane-wars"] }]
        };
        var stable = Feed("stable","1"); var beta = Feed("beta","1");
        Check(!ModChannelSelection.HasDistinctBeta(GameMod.Immortals, stable, beta), "AW beta made an Immortals beta");
        Check(!ModChannelSelection.HasDistinctBeta(GameMod.Vanilla, stable, beta), "AW beta made a Vanilla beta");
        Check(ModChannelSelection.HasDistinctBeta(GameMod.ArcaneWars, stable, beta), "Actual AW beta unavailable");
        stable.Packages.First(p => p.Id == "pure-fixes-data").Version = "1.1";
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals })
        {
            Check(!ModChannelSelection.HasDistinctBeta(mod, stable, beta), "New stable exposed a cached old stable copy as Beta for " + mod);
            Check(!ModChannelSelection.HasDistinctBeta(mod, null, beta), "Missing stable made a non-beta patch selectable for " + mod);
        }
        stable.Packages.First(p => p.Id == "pure-fixes-data").Version = "1";
        beta.Packages.First(p => p.Id == "pure-fixes-runtime").Version = "2-beta.1";
        Check(ModChannelSelection.HasDistinctBeta(GameMod.Immortals, stable, beta), "Separate pure beta unavailable");
        Check(ModChannelSelection.HasDistinctBeta(GameMod.Vanilla, stable, beta), "Separate Vanilla beta unavailable");
        Check(ModChannelSelection.HasDistinctBeta(GameMod.Vanilla, null, beta), "Real beta unavailable before stable was downloaded");
        var library = new ModLibrary(Path.Combine(root, "per-mod-channels"));
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        {
            await library.RememberAsync(stable, mod); await library.RememberAsync(beta, mod);
            Check(library.Find(mod,"stable")!.ReleaseId != library.Find(mod,"beta")!.ReleaseId, "Branch overwrote stored files for " + mod);
            var applied = new InstallState { AppliedSettings = new() { Mod = mod, Channel = "stable" } };
            Check(!ModLibrary.IsActive(applied,new() { Mod = mod, Channel = "beta" }), "Unapplied branch receives active updates");
            Check(UpdateDetector.HasSettingsChanges(applied, [], new() { Mod = mod, Channel = "beta" }), "Identical branch switch needs no Apply");
        }
        Check(library.Load().Mods.Count == 6, "A mod or channel was evicted");

        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (bool patch in new[] { false,true })
        foreach (bool unsupported in new[] { false,true })
        {
            var preference = new UserSettings { Mod = mod, PawPatchEnabled = patch, VanillaPawPatchEnabled = patch,
                ImmortalsPawPatchEnabled = patch, DataOnly = unsupported, IndependentHostility = false,
                RoamingSpawnMode = "standard", AdditionalRoamingCompanies = false, SiegeBalance = false,
                DisablePowersAndShards = false, RussianLocalization = false };
            var active = EffectiveSettings.ForFeed(preference,stable);
            var exe = GameExecutableSelector.Select(new(),active,stable);
            Check(!unsupported || exe == "k2.exe", "Unsupported version starts custom EXE for " + mod);
            if (!unsupported && mod != GameMod.Vanilla && !patch)
                Check(exe == "k2_paws_menu_1372.exe", "Unpatched mod omitted the menu-only helper");
            if (mod != GameMod.ArcaneWars || !patch)
            {
                var packages = GamePackageSelector.Select(stable, active, false, false);
                Check(packages.Any(p => p.Id == "menu-runtime") == (!unsupported && (mod != GameMod.Vanilla || patch)), "Wrong menu package selection");
                Check(!unsupported || packages.All(p => p.ExecutableIndependent), "Native payload in fallback");
            }
            var metadata = GameMenuMetadata.Create(stable,active);
            Check(metadata.Contains("PawPatch=") == patch, "Menu claims a disabled Paw patch");
            Check(metadata.Contains("Mod=" + mod), "Menu has wrong mode");
        }
        Console.WriteLine($"MOD CHANNEL / MENU PASS {count}: migration, restart, pins, six stored branches, scoped beta, apply, metadata and incompatible EXE fallback");
        return count;
    }
}

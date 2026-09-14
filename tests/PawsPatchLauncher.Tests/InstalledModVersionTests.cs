using PawsPatchLauncher;

internal static class InstalledModVersionTests
{
    internal static int Run()
    {
        var count = 0;
        void Check(bool ok, string why) { count++; if (!ok) throw new Exception("Installed mod version: " + why); }
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (var branch in new[] { "stable", "beta" })
        foreach (var enabled in new[] { false, true })
        {
            var packageVersion = mod == GameMod.Immortals ? "2.1.0" : "0.82.1.8-clean.1";
            var expected = mod == GameMod.Vanilla ? "1.3.72" : mod == GameMod.Immortals ? "2.1" : "0.82.1.8";
            var state = new InstallState { AppliedSettings = new() { Mod = mod, Channel = branch },
                Modules = new() { [mod] = new() { Enabled = true, Version = packageVersion } } };
            GameMod.SetPawPatch(state.AppliedSettings, enabled);
            Check(InstalledModVersions.Mod(state) == mod, "applied mode remains independent of patch and channel");
            Check(InstalledModVersions.Version(mod, state, null, "1.3.72") == expected, "offline author version");
            var archive = new ChannelManifest { Packages = [new() { Id = mod, Version = packageVersion }],
                ModGuides = [new() { Id = mod, Version = mod == GameMod.ArcaneWars ? "0.82.1.8 beta" : "2.1" }] };
            Check(InstalledModVersions.Version(mod, state, archive, "1.3.72") == expected, "archived author version");
            archive.Packages[0].Version = "99.0"; archive.ModGuides[0].Version = "99.0";
            Check(InstalledModVersions.Version(mod, state, archive, "1.3.72") == expected, "new offer cannot replace installed version");
            if (mod != GameMod.Vanilla)
            {
                state.Modules[mod].Version = "3.2-package.4";
                archive.Packages[0].Version = "3.2-package.4"; archive.ModGuides[0].Version = "3.2";
                Check(InstalledModVersions.Version(mod, state, archive, null) == "3.2", "future installed author metadata");
                Check(InstalledModVersions.Version(mod, state, null, null) == "3.2-package.4", "unknown package version is not invented");
                state.Modules[mod].Enabled = false;
                Check(InstalledModVersions.Version(mod, state, archive, null) is null, "disabled cached mod not advertised as installed");
                state.AppliedSettings = null;
                Check(InstalledModVersions.Mod(state) is null, "inactive cached module cannot select the footer mode");
                state.Modules[mod].Enabled = true;
                Check(InstalledModVersions.Mod(state) == mod, "legacy active module supplies the mode");
            }
        }
        Check(InstalledModVersions.Version(GameMod.Vanilla, new() { GameRequirement = new() { Version = "1.3.72" } }, null, "1.3.73") == "1.3.73", "Vanilla shows actual game, not patch requirement");
        Check(InstalledModVersions.Version(GameMod.Vanilla, new() { GameRequirement = new() { Version = "1.3.72" } }, null, "") is null, "unknown game version is not assumed supported");
        Check(InstalledModVersions.Mod(null) is null, "no installation is not Arcane Wars");
        Check(InstalledModVersions.Mod(new() { Modules = new() { ["pawpatch-core"] = new() { Enabled = true } } }) == GameMod.ArcaneWars, "legacy core identity");
        Console.WriteLine($"INSTALLED MOD VERSION PASS {count}: offline, archived, future, disabled, legacy and actual Vanilla versions");
        return count;
    }
}

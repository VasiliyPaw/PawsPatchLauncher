namespace PawsPatchLauncher;

public static class InstalledModVersions
{
    public static string? Mod(InstallState? state)
    {
        if (state?.AppliedSettings?.Mod is GameMod.Vanilla or GameMod.Immortals or GameMod.ArcaneWars)
            return state.AppliedSettings.Mod;
        if (state?.Modules.GetValueOrDefault(GameMod.Immortals)?.Enabled == true) return GameMod.Immortals;
        if (state?.Modules.GetValueOrDefault(GameMod.ArcaneWars)?.Enabled == true
            || PawPatchVersions.InstalledCore(state)?.Enabled == true) return GameMod.ArcaneWars;
        return null;
    }

    // Use only the applied installation and its archived catalog, never the selected update offer.
    // Vanilla follows the actual executable version already read by the compatibility check.
    public static string? Version(string mod, InstallState? state, ChannelManifest? installedRelease, string? gameVersion)
    {
        if (mod == GameMod.Vanilla) return Clean(gameVersion);
        if (state?.Modules.GetValueOrDefault(mod) is not { Enabled: true } module) return null;
        var package = installedRelease?.Packages.FirstOrDefault(p => p.Id == mod);
        var authorVersion = package?.Version == module.Version
            ? Clean(installedRelease?.ModGuides.FirstOrDefault(g => g.Id == mod)?.Version) : null;
        var version = authorVersion ?? Clean(module.Version);
        // Known packaging identifiers refer to these exact author releases, including offline installs.
        return (mod, version) switch
        {
            (GameMod.Immortals, "2.1.0") => "2.1",
            (GameMod.ArcaneWars, "0.82.1.8-clean.1" or "0.82.1.8 beta") => "0.82.1.8",
            _ => version
        };
    }

    private static string? Clean(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
}

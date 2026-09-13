namespace PawsPatchLauncher;

public static class PawPatchVersions
{
    // These unpublished build identifiers all belong to the initial release.
    // Keep package identities intact so cached files do not need downloading again.
    public static string? Display(string mod, string? version)
        => mod is GameMod.Vanilla or GameMod.Immortals
            && version is "1.0.0-local.1" or "1.0.0-local.2" or "1.0.0-pure.1"
                ? "0.1.0" : version;

    public static string? ForChannel(ChannelManifest? channel, string mod)
        => Display(mod, mod == GameMod.ArcaneWars
            ? channel?.Packages.FirstOrDefault(p => p.Id == "pawpatch-core")?.Version
            : channel?.ModGuides.FirstOrDefault(g => g.Id == mod)?.PatchGuide?.Version
                ?? channel?.Packages.FirstOrDefault(p => p.Id == "pure-fixes-data")?.Version);

    public static InstalledModule? InstalledCore(InstallState? state)
        => state?.AppliedSettings?.Mod is GameMod.Vanilla or GameMod.Immortals
            ? state.Modules.GetValueOrDefault("pure-fixes-data")
            : state?.Modules.GetValueOrDefault("pawpatch-core") ?? state?.Modules.GetValueOrDefault("pawpatch-data")
                ?? state?.Modules.GetValueOrDefault("pawpatch-data-ru");

    // The caller supplies the archived installed release, never the latest offer.
    public static string? Installed(InstallState? state, ChannelManifest? installedRelease)
    {
        var core = InstalledCore(state);
        if (core?.Enabled != true || state?.AppliedSettings is { } settings && !GameMod.PawPatchSelected(settings)) return null;
        var mod = state?.AppliedSettings?.Mod ?? GameMod.ArcaneWars;
        return mod == GameMod.ArcaneWars ? core.Version : ForChannel(installedRelease, mod) ?? Display(mod, core.Version);
    }
}

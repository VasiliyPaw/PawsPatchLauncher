namespace PawsPatchLauncher;

public static class GameMod
{
    public const string ArcaneWars = "arcane-wars";
    public const string Vanilla = "vanilla";
    public const string Immortals = "immortals";
    public static bool IsVanilla(UserSettings settings) => settings.Mod == Vanilla;
    public static bool IsArcaneWars(UserSettings settings) => settings.Mod == ArcaneWars;
    public static bool PawPatchSelected(UserSettings settings) => settings.Mod switch
    {
        Vanilla => settings.VanillaPawPatchEnabled,
        Immortals => settings.ImmortalsPawPatchEnabled,
        _ => settings.PawPatchEnabled
    };
    public static void SetPawPatch(UserSettings settings, bool enabled)
    {
        if (settings.Mod == Vanilla) settings.VanillaPawPatchEnabled = enabled;
        else if (settings.Mod == Immortals) settings.ImmortalsPawPatchEnabled = enabled;
        else
        {
            if (!enabled && settings.PawPatchEnabled)
                settings.SuspendedArcaneComponents = ArcaneComponentSelection.Capture(settings);
            if (enabled && !settings.PawPatchEnabled)
            {
                settings.SuspendedArcaneComponents?.Restore(settings);
                settings.SuspendedArcaneComponents = null;
            }
            settings.PawPatchEnabled = enabled;
            settings.LargeMapSizes = enabled;
            if (!enabled) DisableArcaneComponents(settings);
        }
    }
    public static void NormalizeRememberedComponents(UserSettings settings)
    {
        if (settings.PawPatchEnabled) return;
        settings.SuspendedArcaneComponents ??= ArcaneComponentSelection.Capture(settings);
        DisableArcaneComponents(settings);
    }
    public static void DisableArcaneComponents(UserSettings settings)
    {
        settings.CustomPlayerColors = settings.IndependentHostility = settings.AdditionalRoamingCompanies = false;
        settings.SiegeBalance = settings.DisablePowersAndShards = settings.LargeMapSizes = false;
        settings.DesyncMode = "official";
        settings.RoamingSpawnMode = "standard";
    }
    public static bool HasPureFixes(ChannelManifest? channel)
        => channel is not null && channel.Packages.Any(p => p.Id == "pure-fixes-data")
            && channel.Packages.Any(p => p.Id == "pure-fixes-runtime");
    public static GameRequirement Requirement(ChannelManifest channel, string mod)
        => channel.ModGames.TryGetValue(mod, out var requirement) ? requirement : channel.Game;
    public static bool UsesExecutableFeatures(UserSettings settings, ChannelManifest? channel)
        => IsArcaneWars(settings) || PawPatchSelected(settings) && HasPureFixes(channel)
            || settings.Mod == Immortals && GameExecutableSelector.HasMenuRuntime(channel);
    public static string Name(string mod, bool russian = false) => mod switch
    {
        Vanilla => "Vanilla",
        Immortals => "Immortals",
        _ => "Arcane Wars"
    };
    public static void Validate(UserSettings settings)
    {
        if (settings.Mod is not (ArcaneWars or Vanilla or Immortals))
            throw new InvalidDataException("This game mode is not available yet.");
        if (settings.GameTextLanguage is not null && !GameLanguages.Choices.Contains(settings.GameTextLanguage))
            throw new InvalidDataException("This text language is not available yet.");
        if (settings.GameVoiceLanguage is not (null or "en" or "ru" or "de" or "fr"))
            throw new InvalidDataException("This speech language is not available yet.");
    }
}
